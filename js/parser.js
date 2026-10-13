// js/parser.js - Mathematical tokenizer, N-U clustering, and expression evaluator for PQcalc
(function (root, factory) {
    if (typeof exports === 'object' && typeof module !== 'undefined') {
        var Quantities = require('./quantities');
        module.exports = factory(Quantities, typeof global !== 'undefined' ? global : root);
    } else {
        root.MathParser = factory(root.Quantities, root);
        // Expose symbols on root
        root.CalcError = root.MathParser.CalcError;
        root.scan = root.MathParser.scan;
        root.scan_it = root.MathParser.scan_it;
        root.make_paired_tokens = root.MathParser.make_paired_tokens;
        root.interpret = root.MathParser.interpret;
        root.check_name = root.MathParser.check_name;
        root.extract_identifier = root.MathParser.extract_identifier;
    }
}(typeof self !== 'undefined' ? self : this, function (Quantities, root) {
    'use strict';

    var Q = Quantities.Q;
    var X = Quantities.X;
    var Units = Quantities.Units;
    var unity = Quantities.unity;
    var QuantError = Quantities.QuantError;
    var unitquant = Quantities.unitquant;
    var functions = Quantities.functions;
    var qfunc = Quantities.qfunc;

    function CalcError(message) {
        var err = new Error(message);
        err.name = 'CalcError';
        Object.setPrototypeOf(err, CalcError.prototype);
        return err;
    }
    CalcError.prototype = Object.create(Error.prototype);
    CalcError.prototype.constructor = CalcError;

    var re_comment = /^[#!].*/;
    var re_operator = /^[ ,()/*^+-]+/;
    var re_float = /^(?:(?:\d*\.\d+)|(?:\d+\.?))(?:\(\d\d?\))?(?:[Ee][+-]?\d+)?/;
    var re_identifier = /^(?:[^\[ ,()/*\^+\-=]+(?:\[[^\]]+\])?[^\[ ,()/*\^+\-=]*|\[[^\]]+\][^\[ ,()/*\^+\-=]*)/;

    function scan_it(text) {
        var answer = [];
        while (text.length > 0) {
            var m = null;
            var p = null;
            if ((m = re_comment.exec(text))) {
                p = 'C';
            } else if ((m = re_operator.exec(text))) {
                p = 'O';
            } else if ((m = re_float.exec(text))) {
                p = 'N';
            } else if ((m = re_identifier.exec(text))) {
                p = 'I';
            } else {
                break;
            }
            var matchedText = m[0];
            answer.push([p, matchedText.trim()]);
            text = text.slice(matchedText.length);
        }
        return [answer, text];
    }

    function scan(t, count_paren) {
        if (typeof count_paren === 'undefined') count_paren = true;
        var res = scan_it(t + " ");
        var tokens = res[0];
        var remainder = res[1];
        if (remainder && remainder.trim()) {
            throw CalcError("got stuck on |" + remainder + "|");
        }

        var paren = 0;
        for (var i = 0; i < tokens.length; i++) {
            if (tokens[i][0] === 'O') {
                var opText = tokens[i][1];
                for (var c = 0; c < opText.length; c++) {
                    if (opText[c] === '(') {
                        paren++;
                    } else if (opText[c] === ')') {
                        if (!paren && count_paren) {
                            throw CalcError("Closing parenthesis ')' is missing a matching opening one '(' to the left of it");
                        }
                        paren--;
                    }
                }
            }
        }
        if (paren && count_paren) {
            throw CalcError("Parentheses don't match: need " + paren + " more ')'");
        }

        tokens.push(["Z", ""]);

        for (var j = 0; j < tokens.length; j++) {
            if (tokens[j][0] === "I") {
                var ttext = tokens[j][1];
                if (ttext.endsWith("Ohm")) {
                    ttext = ttext.replace(/Ohm$/, "Ω");
                    tokens[j][1] = ttext;
                }
                if (ttext in unitquant) {
                    if (ttext.startsWith("u")) {
                        ttext = "μ" + ttext.slice(1);
                        tokens[j][1] = ttext;
                    }
                    tokens[j] = ["U", ttext];
                    if (ttext === 'min' && tokens.length > j + 1 && tokens[j + 1][1].indexOf('(') !== -1) {
                        var hasComma = false;
                        for (var k = j + 1; k < tokens.length; k++) {
                            if (tokens[k][1].indexOf(',') !== -1) { hasComma = true; break; }
                        }
                        if (hasComma) {
                            tokens[j] = ["F", ttext];
                        }
                    }
                } else if (ttext === '°aC' || ttext === '°ΔC') {
                    tokens[j] = ["U", ttext];
                } else if (ttext in functions) {
                    tokens[j] = ["F", ttext];
                }
            }
        }
        return tokens;
    }

    function extract_identifier(a) {
        var m = re_identifier.exec(a);
        return m ? m[0] : null;
    }

    function fixoperator(operator, tokens) {
        if (tokens.length && tokens[tokens.length - 1][0] === "F") {
            return operator;
        }
        if (operator.indexOf('(') !== -1) {
            var parts = operator.split('(');
            return parts[0] + "*(" + parts.slice(1).join('(');
        }
        return operator + '*';
    }

    function fixfractions(tokens) {
        var newtokens = [];
        var idx = 0;
        while (idx < tokens.length) {
            if (idx + 2 < tokens.length &&
                tokens[idx][0] === 'N' && tokens[idx + 1][0] === 'N' &&
                tokens[idx][1].endsWith('(') && tokens[idx + 2][1].startsWith(')') &&
                tokens[idx + 1][1] === '/' &&
                tokens[idx][2].indexOf('.') === -1 && tokens[idx + 1][2].indexOf('.') === -1 &&
                parseInt(tokens[idx + 1][2], 10) !== 0) {
                var fractoken = ['N', tokens[idx][1], tokens[idx][2] + ' / ' + tokens[idx + 1][2]];
                newtokens.push(fractoken);
                idx += 2;
            } else {
                newtokens.push(tokens[idx]);
                idx++;
            }
        }
        return newtokens;
    }

    function make_paired_tokens(raw_tokens, comma_error) {
        if (typeof comma_error === 'undefined') comma_error = true;
        var tokens = [];
        var comment = '';
        var i = 0;

        while (i < raw_tokens.length) {
            var ttype = raw_tokens[i][0];
            var ttext = raw_tokens[i][1];
            var operator = "*";

            if (ttype === "O") {
                operator = ttext ? ttext : "*";
                var hasMathOp = false;
                for (var c = 0; c < operator.length; c++) {
                    if ("+-*/^,".indexOf(operator[c]) !== -1) {
                        hasMathOp = true;
                        break;
                    }
                }
                if (!hasMathOp) {
                    operator = fixoperator(operator, tokens);
                }
                if (operator.indexOf(',') !== -1 && comma_error) {
                    var hasF = false;
                    for (var fi = 0; fi < tokens.length; fi++) {
                        if (tokens[fi][0] === 'F') { hasF = true; break; }
                    }
                    if (tokens.length < 1 || !hasF) {
                        throw CalcError("commas are only allowed to separate arguments of functions; didn't find any function preceeding the comma");
                    }
                }
                i++;
                if (i < raw_tokens.length) {
                    ttype = raw_tokens[i][0];
                    ttext = raw_tokens[i][1];
                } else {
                    break;
                }
            } else {
                operator = "*";
            }

            if (ttype === "C") {
                tokens.push(["Z", operator, ""]);
                comment = '<span style="color:black">&nbsp;&nbsp;&nbsp; ' + ttext.slice(1) + '</span>';
                break;
            }
            tokens.push([ttype, operator.replace(/\^/g, "**"), ttext]);
            i++;
        }
        return [fixfractions(tokens), comment];
    }

    // Evaluates a Number-Unit cluster (e.g. "3 mol/L", "30 s", "3.5 J/(mol K)")
    function interpret_N_U_cluster(firstQuant, orig_paired, operator) {
        var paired = orig_paired.slice();
        var notyetclosed = null;
        var openp = 0;
        var end = 0;

        for (var i = 0; i < paired.length; i++) {
            var op = paired[i][1];
            var ttype = paired[i][0];
            var oCount = (op.match(/\(/g) || []).length;
            var cCount = (op.match(/\)/g) || []).length;
            if (oCount) {
                openp += oCount;
                if (!notyetclosed) notyetclosed = i;
            }
            if (cCount) {
                openp -= cCount;
                if (openp < 0) break;
                notyetclosed = null;
            }
            if (!(ttype === "U" || (ttype === "N" && op.indexOf("**") !== -1))) {
                break;
            }
            end = i + 1;
        }

        if (notyetclosed) {
            end = notyetclosed;
        }

        var special = '';
        if (end === 1 && paired[0][2] === '°aC') {
            special = '°aC';
            paired[0][2] = 'K';
        }
        for (var j = 0; j < end; j++) {
            if (paired[j][2] === '°ΔC') {
                paired[j][2] = 'K';
                special = '°ΔC';
            }
        }

        // Evaluate the cluster expression: firstQuant followed by paired[0..end-1]
        var clusterTokens = [];
        clusterTokens.push({ type: 'VAL', value: firstQuant });

        for (var k = 0; k < end; k++) {
            var itemOp = paired[k][1].replace(/\*\*/g, '^');
            var itemType = paired[k][0];
            var itemText = paired[k][2];
            var itemVal = (itemType === 'U') ? unitquant[itemText] : new Q(itemText);

            // Unpack operator characters in itemOp
            for (var cIdx = 0; cIdx < itemOp.length; cIdx++) {
                var ch = itemOp[cIdx];
                if ('+-*/^()'.indexOf(ch) !== -1) {
                    clusterTokens.push({ type: 'OP', value: ch });
                }
            }
            clusterTokens.push({ type: 'VAL', value: itemVal });
        }

        // Check if there are open parens closing in paired[end][1]
        var openParens = 0;
        for (var ct = 0; ct < clusterTokens.length; ct++) {
            if (clusterTokens[ct].type === 'OP' && clusterTokens[ct].value === '(') openParens++;
            if (clusterTokens[ct].type === 'OP' && clusterTokens[ct].value === ')') openParens--;
        }
        if (openParens > 0 && end < paired.length) {
            var closeOp = paired[end][1];
            var consumedClose = 0;
            for (var ci = 0; ci < closeOp.length; ci++) {
                if (closeOp[ci] === ')') {
                    clusterTokens.push({ type: 'OP', value: ')' });
                    openParens--;
                    consumedClose = ci + 1;
                    if (openParens === 0) break;
                }
            }
            paired[end][1] = closeOp.slice(consumedClose);
        }

        var q = evaluateTokenStream(clusterTokens, null);
        if (special) {
            q.prefu.add(special);
            if (special === '°aC' && q.units.equals(unitquant['K'].units)) {
                if ((operator === '-' && !result) || (operator.length > 1 && operator.endsWith('-'))) {
                    q.number = 273.15 - q.number;
                    operator = operator.slice(0, -1);
                } else {
                    q.number += 273.15;
                }
            }
        }

        q.name = "";
        q.provenance = null;
        return {
            q: q,
            remaining: paired.slice(end),
            operator: operator
        };
    }

    // Shunting-Yard evaluator for token stream
    var PRECEDENCE = {
        '+': 2,
        '-': 2,
        '*': 3,
        '/': 3,
        '^': 4,
        'u-': 3.5,
        'u+': 3.5
    };

    function applyOperator(op, operandStack) {
        if (op === 'u-') {
            if (operandStack.length < 1) throw CalcError("Missing operand for unary minus");
            var a = operandStack.pop();
            operandStack.push(a.neg());
            return;
        }
        if (op === 'u+') {
            return; // no-op
        }
        if (operandStack.length < 2) {
            throw CalcError("Missing operand for operator " + op);
        }
        var right = operandStack.pop();
        var left = operandStack.pop();
        var res;
        switch (op) {
            case '+': res = left.add(right); break;
            case '-': res = left.sub(right); break;
            case '*': res = left.mul(right); break;
            case '/': res = left.div(right); break;
            case '^': res = left.pow(right); break;
            default: throw CalcError("Unknown operator " + op);
        }
        operandStack.push(res);
    }

    function evaluateTokenStream(tokens, state) {
        var operandStack = [];
        var opStack = [];
        var argCountStack = [];
        var expectOperand = true;

        for (var i = 0; i < tokens.length; i++) {
            var tok = tokens[i];
            if (tok.type === 'VAL') {
                operandStack.push(tok.value);
                expectOperand = false;
            } else if (tok.type === 'FUNC') {
                opStack.push({ type: 'FUNC', name: tok.name });
                argCountStack.push(0);
                expectOperand = false;
            } else if (tok.type === 'OP') {
                var ch = tok.value;
                if (ch === '(') {
                    opStack.push({ type: 'PAREN', value: '(' });
                    if (argCountStack.length > 0 && opStack.length >= 2 && opStack[opStack.length - 2].type === 'FUNC') {
                        argCountStack[argCountStack.length - 1] = 1;
                    }
                    expectOperand = true;
                } else if (ch === ')') {
                    while (opStack.length > 0 && opStack[opStack.length - 1].value !== '(') {
                        applyOperator(opStack.pop().value, operandStack);
                    }
                    if (opStack.length === 0) throw CalcError("Unmatched closing parenthesis ')'");
                    opStack.pop(); // remove '('
                    if (opStack.length > 0 && opStack[opStack.length - 1].type === 'FUNC') {
                        var fnObj = opStack.pop();
                        var count = argCountStack.pop();
                        var args = [];
                        for (var aIdx = 0; aIdx < count; aIdx++) {
                            args.unshift(operandStack.pop());
                        }
                        var fnRes = qfunc.apply(null, [fnObj.name].concat(args));
                        operandStack.push(fnRes);
                    }
                    expectOperand = false;
                } else if (ch === ',') {
                    while (opStack.length > 0 && opStack[opStack.length - 1].value !== '(') {
                        applyOperator(opStack.pop().value, operandStack);
                    }
                    if (argCountStack.length > 0) {
                        argCountStack[argCountStack.length - 1]++;
                    }
                    expectOperand = true;
                } else {
                    // Operator (+, -, *, /, ^)
                    var actualOp = ch;
                    if (expectOperand) {
                        if (ch === '-') actualOp = 'u-';
                        else if (ch === '+') actualOp = 'u+';
                        else throw CalcError("Unexpected operator '" + ch + "' without left operand");
                    }
                    var curPrio = PRECEDENCE[actualOp] || 0;
                    var rightAssoc = (actualOp === '^' || actualOp === 'u-' || actualOp === 'u+');

                    while (opStack.length > 0 && opStack[opStack.length - 1].type === 'OP') {
                        var topOp = opStack[opStack.length - 1].value;
                        var topPrio = PRECEDENCE[topOp] || 0;
                        if ((!rightAssoc && topPrio >= curPrio) || (rightAssoc && topPrio > curPrio)) {
                            applyOperator(opStack.pop().value, operandStack);
                        } else {
                            break;
                        }
                    }
                    opStack.push({ type: 'OP', value: actualOp });
                    expectOperand = true;
                }
            }
        }

        while (opStack.length > 0) {
            var top = opStack.pop();
            if (top.value === '(') throw CalcError("Unmatched opening parenthesis '('");
            applyOperator(top.value, operandStack);
        }

        if (operandStack.length !== 1) {
            throw CalcError("Invalid expression structure; operands remaining");
        }
        return operandStack[0];
    }

    function interpret(t, state, warning, keep_onthefly) {
        if (typeof warning === 'undefined') warning = true;
        if (typeof keep_onthefly === 'undefined') keep_onthefly = false;

        var scanned = scan(t);
        var pairedRes = make_paired_tokens(scanned);
        var paired = pairedRes[0];
        var comment = pairedRes[1];

        var identity = null;
        if (paired.length === 2 && paired[0][0] === 'I' && paired[0][1] === '*') {
            identity = paired[0][2];
        }

        var linearTokens = [];

        while (paired.length > 0) {
            var item = paired.shift();
            var ttype = item[0];
            var op = item[1].replace(/\*\*/g, '^');
            var text = item[2];

            if (ttype === 'Z') {
                // Unpack any closing parens in Z's op
                for (var zc = 0; zc < op.length; zc++) {
                    if (op[zc] === ')') {
                        linearTokens.push({ type: 'OP', value: ')' });
                    }
                }
                break;
            }

            if (ttype === 'F') {
                // Unpack operator before function
                for (var fc = 0; fc < op.length; fc++) {
                    var chf = op[fc];
                    if ('+-*/^(),'.indexOf(chf) !== -1) linearTokens.push({ type: 'OP', value: chf });
                }
                linearTokens.push({ type: 'FUNC', name: text });
                continue;
            }

            if (ttype === 'I') {
                for (var ic = 0; ic < op.length; ic++) {
                    var chi = op[ic];
                    if ('+-*/^(),'.indexOf(chi) !== -1) linearTokens.push({ type: 'OP', value: chi });
                }
                var valI;
                if (state && (text in state.variables || (state.has && state.has(text)))) {
                    valI = state.get ? state.get(text) : state.variables[text];
                } else if (text.startsWith('M[') && text.endsWith(']')) {
                    var chemMod = root.Chemistry || (typeof require !== 'undefined' ? require('./chemistry') : null);
                    if (chemMod && chemMod.molar_mass) {
                        valI = chemMod.molar_mass(text.slice(2, -1));
                    } else {
                        throw CalcError("Chemistry module required for molar mass calculation: " + text);
                    }
                } else {
                    throw CalcError("unknown symbol |" + text + "| encountered (check spelling and capitalization)");
                }
                linearTokens.push({ type: 'VAL', value: valI });
                continue;
            }

            // ttype in "UN"
            var startQuant = (ttype === 'N') ? new Q(text) : unitquant[text];
            var isCluster = (ttype === 'U') || (ttype === 'N' && paired.length > 0 && paired[0][0] === 'U');

            if (!isCluster) {
                // Plain number
                for (var nc = 0; nc < op.length; nc++) {
                    var chn = op[nc];
                    if ('+-*/^(),'.indexOf(chn) !== -1) linearTokens.push({ type: 'OP', value: chn });
                }
                linearTokens.push({ type: 'VAL', value: startQuant });
            } else {
                // Number-Unit cluster
                var clusterRes = interpret_N_U_cluster(startQuant, paired, op);
                paired = clusterRes.remaining;
                var clusterOp = clusterRes.operator;
                for (var cc = 0; cc < clusterOp.length; cc++) {
                    var chc = clusterOp[cc];
                    if ('+-*/^(),'.indexOf(chc) !== -1) linearTokens.push({ type: 'OP', value: chc });
                }
                linearTokens.push({ type: 'VAL', value: clusterRes.q });
            }
        }

        // Clean any leading artifact '*'
        if (linearTokens.length > 0 && linearTokens[0].type === 'OP' && linearTokens[0].value === '*') {
            linearTokens.shift();
        }

        var resultQ = evaluateTokenStream(linearTokens, state);
        resultQ.comment = comment;

        if (identity && state && (identity in state.variables || (state.has && state.has(identity)))) {
            resultQ.name = '%s';
            var idVar = state.get ? state.get(identity) : state.variables[identity];
            resultQ.provenance = [idVar];
        }

        return resultQ;
    }

    var rules_for_symbol_name = "Rules for names: Start with a letter, then letters or numbers or underscores.\n" +
        "  Examples: m0, y, s_15\n" +
        "Special rule #1: You can add anything in brackets, [...], or just have something in brackets\n" +
        "  Examples: [NaCl], [Na+], c[Na+], M[Na+]\n" +
        "Special rule #2: You can't use names already used for units or functions. If you do, the program will add an underscore.\n" +
        "  Examples: mm, s, V, and log are not allowed, and will be used as mm_, s_, V_, and log_";

    function check_name(sym, state) {
        var res = scan_it(sym);
        var tokens = res[0];
        if (tokens.length !== 1 || tokens[0][0] !== "I") {
            throw CalcError("Please don't use " + sym + " as a name for a quantity<br><pre>" + rules_for_symbol_name + "</pre>");
        }
        if (sym in unitquant || sym in functions) {
            var conf = (sym in functions) ? "function" : "unit";
            throw CalcError("You can't use " + sym + " as a name for a quantity because it is already the name of a " + conf + "<br>" +
                "You can use " + sym + "_ though, and the underscore will not show in the formatted output.");
        }
        return sym;
    }

    return {
        CalcError: CalcError,
        scan_it: scan_it,
        scan: scan,
        make_paired_tokens: make_paired_tokens,
        extract_identifier: extract_identifier,
        interpret: interpret,
        check_name: check_name,
        rules_for_symbol_name: rules_for_symbol_name
    };
}));
