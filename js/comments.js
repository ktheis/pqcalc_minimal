// js/comments.js - Formatting comments, detecting embedded chemical equations and math, and clickable insertions
(function (root, factory) {
    if (typeof exports === 'object' && typeof module !== 'undefined') {
        var Quantities = require('./quantities');
        var MathParser = require('./parser');
        var Chemistry = require('./chemistry');
        module.exports = factory(Quantities, MathParser, Chemistry);
    } else {
        root.Comments = factory(root.Quantities, root.MathParser, root.Chemistry);
        // Expose symbols on root
        root.create_comment = root.Comments.create_comment;
        root.markup_comment = root.Comments.markup_comment;
        root.chemeq_addlinks = root.Comments.chemeq_addlinks;
        root.clickable = root.Comments.clickable;
    }
}(typeof self !== 'undefined' ? self : this, function (Quantities, MathParser, Chemistry) {
    'use strict';

    var latex_writer = Quantities.latex_writer;
    var latex_name = Quantities.latex_name;
    var unitquant = Quantities.unitquant;
    var PSE = Chemistry.PSE;
    var chemname = Chemistry.chemname;

    function clickable(paste, text) {
        var escapedPaste = ('' + paste).replace(/'/g, "\\'").replace(/\n/g, '\\n');
        return '<span onclick="insertAtCaret(\'commands\',\'' + escapedPaste + '\', \'0\')">' + text + '</span>';
    }

    var latex_subs = {
        "%s / %s": "\\dfrac{%s}{%s}",
        "%s * %s": "%s \\cdot %s",
        "%s ^ %s": "{%s}^{%s}",
        "exp0(%s)": "e^{%s}",
        "exp(%s)": "\\mathrm{exp}(%s)",
        "log(%s)": "\\mathrm{log}(%s)",
        "ln(%s)": "\\mathrm{ln}(%s)",
        "sin(%s)": "\\mathrm{sin}(%s)",
        "cos(%s)": "\\mathrm{cos}(%s)",
        "tan(%s)": "\\mathrm{tan}(%s)",
        "sqrt(%s)": "\\sqrt{%s}",
        "abs(%s)": "\\mathrm{abs}(%s)"
    };

    function chemeq_addlinks(text, neg_react) {
        if (text.indexOf('->') === -1 && text.indexOf('<=>') === -1) {
            return clickable('!' + text, '\\(\\ce{' + text + '}\\)');
        }
        var species = text.split(/(->(?:\[[^\]]+\])?|<=>(?:\[[^\]]+\])?|\s\+\s)/);
        species.push('');
        var answer = [];
        var sign = neg_react ? -1 : 1;

        for (var i = 0; i < species.length; i += 2) {
            var s = species[i].trim();
            var sep = (i + 1 < species.length) ? species[i + 1] : '';
            var stoich = 1;
            var name = s;

            for (var c = 0; c < s.length; c++) {
                var ch = s[c];
                if (ch < '0' || ch > '9') {
                    name = s.slice(c).trim();
                    var digitText = s.slice(0, c).trim();
                    if (digitText.length > 0) stoich = parseInt(digitText, 10);
                    break;
                }
            }

            stoich *= sign;
            var sepClickable;
            if (sep.startsWith('->') || sep.startsWith('<=>')) {
                sepClickable = '&nbsp;&nbsp;' + clickable('!' + text + '\n', '\\(\\ce{ ' + sep + ' }\\)') + '&nbsp;&nbsp;';
                sign = 1;
            } else if (sep.trim()) {
                sepClickable = '&nbsp;\\(\\ce{ ' + sep.trim() + ' }\\)&nbsp;';
            } else {
                sepClickable = '';
            }

            var insertCmd = 'ν[' + name + '] = ' + stoich + '\n';
            answer.push(clickable(insertCmd, '\\(\\ce{' + s + '}\\)') + sepClickable);
        }
        return answer.join('');
    }

    function displayed_chemical_equation(a, state) {
        var cond = state.output.length < 2 || !state.output[state.output.length - 2].endsWith('>');
        if (cond) {
            state.printnlog('<br>');
        }
        var add = '';
        var app = '';
        var content = a.slice(1);

        if (content.indexOf('!') !== -1) {
            var parts = content.split('!');
            content = parts[0];
            app = '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;' + markup_comment(parts.slice(1).join('!'));
        }

        var result = chemeq_addlinks(content, state.flags.has('__negreact__'));
        return '<div style="font-size:12pt; display: flex; justify-content: space-between;"><div>' + add + '</div><div>' + result + ' ' + app + '</div><div></div></div>';
    }

    function displayed_algebra(a, state) {
        if (state.output.length < 2 || !state.output[state.output.length - 2].endsWith('>')) {
            state.printnlog('<br>');
        }
        var expr = a.slice(1);
        var comment = '';
        if (expr.indexOf('@') !== -1) {
            var parts = expr.split('@');
            expr = parts[0];
            comment = parts.slice(1).join('@');
        }

        var raw = a.slice(1) + '\n';
        var cl = clickable(raw, ' \\(' + expr + '\\)');
        var commentMarkup = comment ? markup_comment(comment) : '';
        return '<div style="font-size:12pt; display: flex; justify-content: space-between;"><div></div><div>' + cl + ' &nbsp;&nbsp;&nbsp;&nbsp; ' + commentMarkup + '</div><div></div></div>';
    }

    function split_at_blank(text) {
        return text.split(/\s+/).filter(Boolean);
    }

    function parseWordPunctuation(word) {
        var lead = '';
        var trail = '';
        var core = word;

        // Strip leading punctuation: opening quotes, inverted punctuation
        while (core.length > 0 && /^[“"‘'¿¡]/.test(core)) {
            lead += core[0];
            core = core.slice(1);
        }

        // Strip trailing punctuation: periods, commas, colons, semicolons, question marks, exclamation marks, closing quotes
        while (core.length > 0 && /[.,;:?!’”"']$/.test(core)) {
            trail = core[core.length - 1] + trail;
            core = core.slice(0, -1);
        }

        // Check for unmatched closing parenthesis e.g. "H2SO4)" in "(in solution with H2SO4)"
        var openCount = (core.match(/\(/g) || []).length;
        var closeCount = (core.match(/\)/g) || []).length;
        while (core.length > 0 && core.endsWith(')') && closeCount > openCount) {
            trail = ')' + trail;
            core = core.slice(0, -1);
            closeCount--;
        }

        // Check for unmatched opening parenthesis e.g. "(H2SO4" in "(H2SO4 and HCl)"
        while (core.length > 0 && core.startsWith('(') && openCount > closeCount) {
            lead += '(';
            core = core.slice(1);
            openCount--;
        }

        // Check for fully enclosing parentheses around a formula e.g. "(H2SO4)" or "(NaCl)"
        if (core.length >= 2 && core.startsWith('(') && core.endsWith(')')) {
            var inner = core.slice(1, -1);
            var innerOpen = (inner.match(/\(/g) || []).length;
            var innerClose = (inner.match(/\)/g) || []).length;
            if (innerOpen === innerClose && isChemicalFormula(inner)) {
                lead += '(';
                trail = ')' + trail;
                core = inner;
            }
        }

        return {
            lead: lead,
            core: core,
            trail: trail
        };
    }

    function isChemicalFormula(word) {
        if (!word || word.length === 0) return false;
        if (word === '->' || word === '<=>' || ['(s)', '(l)', '(g)', '(aq)'].indexOf(word) !== -1) return true;
        if (word.indexOf('http://') === 0 || word.indexOf('https://') === 0) return false;

        var lower = word.toLowerCase();
        var commonWords = ['in', 'no', 'at', 'as', 'he', 'be', 'on', 'or', 'so', 'if', 'is', 'it', 'to', 'do', 'am', 'an', 'by', 'my', 'up', 'we', 'us', 'the'];
        if (commonWords.indexOf(lower) !== -1 && !/[0-9+\-]/.test(word)) {
            return false;
        }

        if (!/^[A-Z(\[]/.test(word)) {
            return false;
        }

        // Remove all structural chars: parentheses, brackets, digits, charges, superscripts, dots
        var clean = word.replace(/[()\[\]+\-0-9^·*]/g, '');
        if (clean.length === 0) return false;

        var upperCount = (clean.match(/[A-Z]/g) || []).length;
        var hasDigits = /[0-9]/.test(word);
        var hasCharge = /[+\-]/.test(word);

        // A single element without digits or charges (e.g. "I", "He", "In") is rejected to avoid false positives
        if (upperCount === 1 && !hasDigits && !hasCharge) {
            return false;
        }

        // Verify all parts of clean are valid elements in PSE
        var tx = clean;
        var matched = 0;
        while (tx.length > 0) {
            if (tx.length >= 2 && tx.slice(0, 2) in PSE) {
                matched++;
                tx = tx.slice(2);
            } else if (tx.slice(0, 1) in PSE) {
                matched++;
                tx = tx.slice(1);
            } else {
                return false;
            }
        }
        return matched >= 1 && (hasDigits || upperCount >= 2 || hasCharge);
    }

    function markup_comment(b) {
        if (!b) return '';
        var words = b.split(' ');
        var result = [];

        for (var i = 0; i < words.length; i++) {
            var w = words[i];
            if (!w) {
                result.push('');
            } else if (w.startsWith('http://') || w.startsWith('https://')) {
                result.push('<a href="' + w + '" target="_blank">' + w + '</a>');
            } else {
                var parsed = parseWordPunctuation(w);
                if (isChemicalFormula(parsed.core)) {
                    var formatted = clickable('[' + parsed.core + ']', '\\(\\ce{' + parsed.core + '}\\)');
                    result.push(parsed.lead + formatted + parsed.trail);
                } else {
                    result.push(w);
                }
            }
            if (i < words.length - 1) result.push(' ');
        }
        return result.join('');
    }

    function create_comment(a, state) {
        if (state.flags.has('plain math')) {
            state.printnlog(a);
            return;
        }
        var result;
        if (a.startsWith('!')) {
            result = displayed_chemical_equation(a, state);
        } else if (a.startsWith('#')) {
            result = '<span style="font-size:12pt;">' + a.slice(1) + '</span>';
        } else if (a.startsWith('@')) {
            result = displayed_algebra(a, state);
        } else {
            result = markup_comment(a);
        }
        state.printnlog(result);
    }

    return {
        create_comment: create_comment,
        markup_comment: markup_comment,
        chemeq_addlinks: chemeq_addlinks,
        clickable: clickable,
        displayed_chemical_equation: displayed_chemical_equation,
        displayed_algebra: displayed_algebra
    };
}));
