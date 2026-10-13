// js/calculator.js - State management, input classification, multi-step work presentation, and calculation loop
(function (root, factory) {
    if (typeof exports === 'object' && typeof module !== 'undefined') {
        var Quantities = require('./quantities');
        var MathParser = require('./parser');
        module.exports = factory(Quantities, MathParser, typeof global !== 'undefined' ? global : root);
    } else {
        root.Calculator = factory(root.Quantities, root.MathParser, root);
        // Expose symbols on root
        root.State = root.Calculator.State;
        root.calc = root.Calculator.calc;
        root.classify_input = root.Calculator.classify_input;
        root.show_work = root.Calculator.show_work;
        root.register_result = root.Calculator.register_result;
        root.convert_units = root.Calculator.convert_units;
    }
}(typeof self !== 'undefined' ? self : this, function (Quantities, MathParser, root) {
    'use strict';

    var Q = Quantities.Q;
    var Units = Quantities.Units;
    var unity = Quantities.unity;
    var QuantError = Quantities.QuantError;
    var unitquant = Quantities.unitquant;
    var latex_name = Quantities.latex_name;
    var latex_writer = Quantities.latex_writer;
    var ascii_writer = Quantities.ascii_writer;
    var ascii_qvalue = Quantities.ascii_qvalue;

    var CalcError = MathParser.CalcError;
    var interpret = MathParser.interpret;
    var check_name = MathParser.check_name;
    var scan_it = MathParser.scan_it;
    var extract_identifier = MathParser.extract_identifier;

    // Input types enumeration
    var Empty = 0;
    var Calculation = 1;
    var ConversionIn = 2;
    var ConversionUsing = 3;
    var Comment = 4;
    var Flags = 5;
    var Unknown = 6;
    var CalcUsing = 7;

    function State(memory, mob) {
        this.flags = new Set();
        this.output = [];
        this.logput = [];
        this.good_input = [];
        this.mob = mob || null;
        this.snuck = 0;
        this.variables = {};

        if (mob === 'ipud') {
            this.flags.add('plain math');
        }

        if (memory instanceof State) {
            for (var k in memory.variables) {
                if (Object.prototype.hasOwnProperty.call(memory.variables, k)) {
                    this.variables[k] = memory.variables[k];
                }
            }
            var self = this;
            memory.flags.forEach(function (f) {
                self.flags.add(f);
            });
        } else if (memory && typeof memory === 'string') {
            var lines = memory.replace(/\r/g, '').split('\n');
            for (var i = 0; i < lines.length; i++) {
                var line = lines[i].trim();
                if (!line) continue;
                if (line.startsWith('__') || line === 'plain math') {
                    this.flags.add(line);
                }
            }
        }
    }

    State.prototype.get = function (name) {
        return this.variables[name];
    };

    State.prototype.set = function (name, q) {
        this.variables[name] = q;
    };

    State.prototype.has = function (name) {
        return Object.prototype.hasOwnProperty.call(this.variables, name);
    };

    State.prototype.delete = function (name) {
        delete this.variables[name];
    };

    State.prototype.keys = function () {
        return Object.keys(this.variables);
    };

    State.prototype.printit = function (str) {
        this.output.push(str);
    };

    State.prototype.logit = function (str) {
        this.logput.push(str);
    };

    State.prototype.printnlog = function (str) {
        this.printit(str);
        this.logit(str);
    };

    State.prototype.printwork = function (outlog) {
        var cond1 = this.output.length >= 2;
        var cond2 = cond1 && !this.output[this.output.length - 2].endsWith('>');
        if (cond1 && cond2) {
            this.printnlog('<br>');
        }
        this.output = this.output.concat(outlog[0]);
        this.logput = this.logput.concat(outlog[1]);
    };

    State.prototype.log_input = function (inp) {
        this.good_input.push(inp);
    };

    State.prototype.export = function () {
        if (this.output.length && !this.output[this.output.length - 1].endsWith("<hr>")) {
            this.output.unshift("<hr>");
        }
        var known = [];
        for (var k in this.variables) {
            known.push(k + " = " + ascii_qvalue(this.variables[k]));
        }
        var input_log = this.good_input.join("\n");
        if (!input_log.endsWith("\n")) input_log += "\n";
        var verbose_work = this.output.join("\n");
        var brief_work = this.logput.join("\n");
        var linespace = this.flags.has('__scrunch__') ? '60%' : '120%';
        return {
            verbose_work: verbose_work,
            brief_work: brief_work,
            known: known,
            input_log: input_log,
            linespace: linespace,
            state: this
        };
    };

    function pronounce(sym, units) {
        var chemMod = root.Chemistry || (typeof require !== 'undefined' ? require('./chemistry') : null);
        if (chemMod && chemMod.pronounce) {
            return chemMod.pronounce(sym, units);
        }
        if (sym.startsWith('!')) return 'Chemical formula or equation: ' + sym.slice(1);
        if (sym.startsWith('@')) return 'Mathematical expression: ' + sym.slice(1);
        return 'quantity ' + sym;
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
        "asin(%s)": "\\mathrm{asin}(%s)",
        "acos(%s)": "\\mathrm{acos}(%s)",
        "atan(%s)": "\\mathrm{atan}(%s)",
        "sqrt(%s)": "\\sqrt{%s}",
        "quadn(%s": "\\mathrm{quadn}(%s",
        "quadp(%s": "\\mathrm{quadp}(%s",
        "avg(%s": "\\mathrm{avg}(%s",
        "min(%s": "\\mathrm{min}(%s",
        "sum(%s": "\\sum (%s",
        "max(%s": "\\mathrm{max}(%s",
        "abs(%s)": "\\mathrm{abs}(%s)",
        "moredigits(%s)": "\\mathrm{moredigits}(%s)",
        "uncertainty(%s)": "\\mathrm{uncertainty}(%s)"
    };

    function show_work(result, sym, flags, error, addon, skipsteps) {
        flags = flags || new Set();
        error = error || false;
        addon = addon || "";
        skipsteps = skipsteps || false;
        var output = [];
        var logput = [];
        var math = !flags.has('plain math');
        var writer = math ? latex_writer : ascii_writer;
        var subs = math ? latex_subs : null;
        var d = result.setdepth();

        var clickPrefix = "<span style=\"color:navy; cursor:pointer; font-size:12pt;\" onclick=\"insertAtCaret('commands','" + sym + " ', 0)\">";
        if (math && !flags.has('__latex__')) {
            logput.push(clickPrefix);
            output.push(clickPrefix);
        }

        var task = result.steps(-1, writer, subs, new Set());
        var title = pronounce(sym, result.units);
        var name = math ? "<span title=\"" + title + "\">\\(" + latex_name(sym) + "\\)</span>" : sym;
        var commentMarkup = result.comment || '';

        var line1 = name + " \\(= " + task + addon + "\\)" + commentMarkup + "<br>";
        output.push(line1);
        logput.push(line1);

        if (!skipsteps) {
            for (var dd = 1; dd <= d; dd++) {
                if (dd === 1) {
                    var first = result.steps(dd, writer, subs, flags);
                    if (first !== task) {
                        output.push("<br><span title=\"\">\\(\\ \\ \\ =" + first + addon + "\\)</span><br>");
                    }
                } else {
                    output.push("<br><span title=\"\">\\(\\ \\ \\ =" + result.steps(dd, writer, subs, flags) + addon + "\\)</span><br>");
                }
            }
        }

        var result_str = result.steps(0, writer, subs, flags);
        if (result_str !== task && !error) {
            var resLine = "<br><span title=\"" + title + "\">\\(\\ \\ \\ =" + result_str + addon + "\\)</span><br>";
            logput.push(resLine);
            output.push(resLine);
        }

        if (math && !flags.has('__latex__')) {
            logput.push("<br></span>");
            output.push("<br></span>");
        }

        return [output, logput];
    }

    function register_result(result0, sym, state, keep_provenance) {
        var result = result0.copy();
        if (!keep_provenance) {
            result.provenance = null;
            result.name = sym;
        }
        delete result.depth;
        if (state.has(sym) && !state.flags.has('__allowupdate__')) {
            state.printit('<div style="color: green;">Warning: Updated value of \\(' + latex_name(sym) + '\\)</div><br>');
        }
        state.set(sym, result);
    }

    function classify_input(a, state) {
        if (!a || !a.trim()) {
            return [Empty, null, null];
        }
        if (state.flags.has('__newby__') && !a.startsWith('__')) {
            state.printit('<pre style="color:maroon"><b>>>>> ' + a.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</b></pre>');
        }

        var trimmed = a.trim();
        if ("!#@".indexOf(trimmed[0]) !== -1) {
            return [Comment, a, null];
        }
        if (trimmed.startsWith('__')) {
            if (trimmed.indexOf('=') === -1) {
                return [Comment, a, null];
            }
            var flagParts = trimmed.split('=');
            return [Flags, flagParts[0].trim(), flagParts.slice(1).join('=').trim()];
        }

        var m = extract_identifier(trimmed);
        var start = m ? m.length : 0;
        var rest = trimmed.slice(start).trim();

        if (m && rest.startsWith('=')) {
            var r2 = rest.slice(1).trim();
            if (!r2) return [Empty, null, null];
            if (r2[0] === '?') return [Unknown, trimmed.slice(0, start), null];
            var scanRes = scan_it(rest.slice(1));
            var remainder = scanRes[1];
            if (remainder && remainder.startsWith('=')) {
                return [Comment, '@' + a, null];
            }
            if (rest.slice(2).indexOf(' using') !== -1) {
                return [CalcUsing, trimmed.slice(0, start), rest.slice(1)];
            }
            return [Calculation, trimmed.slice(0, start), rest.slice(1)];
        } else if (m && trimmed.slice(start).startsWith(' using') && state.has(trimmed.slice(0, start).trim())) {
            return [ConversionUsing, trimmed.slice(0, start).trim(), rest.slice('using'.length).trim()];
        } else if (m && trimmed.slice(start).startsWith(' in ') && state.has(trimmed.slice(0, start).trim())) {
            return [ConversionIn, trimmed.slice(0, start).trim(), rest.slice('in'.length).trim()];
        }

        try {
            interpret(trimmed, state, false);
            if (!state.flags.has('__names__') && !state.flags.has('__newby__')) {
                return [Calculation, "result", trimmed];
            }
        } catch (e) {
            return [Comment, a, null];
        }

        return [Comment, a, null];
    }

    function convert_units(input_type, quant, units, state) {
        var flags2 = new Set();
        state.flags.forEach(function (f) {
            if (f !== '__hideunits__') flags2.add(f);
        });
        var sym = quant.trim();

        if (input_type === ConversionUsing) {
            var prefu;
            if (units === '°ΔC' || units === '°aC') {
                prefu = [units];
                var qTemp = state.get(sym).add(new Q(0.0));
                if (units === '°aC' && !unitquant['K'].units.equals(qTemp.units)) {
                    throw CalcError("Only quantities in kelvin may be converted to celsius");
                }
            } else {
                prefu = units.trim().split(/\s+/);
                for (var pi = 0; pi < prefu.length; pi++) {
                    if (!(prefu[pi] in unitquant)) {
                        throw CalcError("PQCalc does not recognize the unit '" + prefu[pi] + "', so 'using' does not work. Try 'in' instead.");
                    }
                }
            }
            if (!state.has(sym)) {
                throw CalcError("The quantity '" + sym + "' is not defined yet. Check for typos.");
            }
            var targetQ = state.get(sym);
            targetQ.prefu = new Set(prefu);

            var qShow = targetQ.add(new Q(0.0));
            qShow.name = "";
            qShow.provenance = null;
            qShow.comment = "";
            var work = show_work(qShow, sym, flags2);
            state.printit(work[0].join('\n'));
            state.logit(work[1].join('\n'));
        } else {
            // ConversionIn
            var tmp = interpret(units, state, false);
            if (!state.has(sym)) {
                throw CalcError("The quantity '" + sym + "' is not defined yet. Check for typos.");
            }
            var qq = state.get(sym).div(tmp);
            var addon = "\\mathrm{\\ " + latex_name(units) + "}";
            var inWork = show_work(qq, sym, flags2, false, addon);
            state.printwork(inWork);
        }
    }

    function create_unknown(sym, state) {
        state.printnlog("<span title=\"" + pronounce(sym) + "\" style=\"color:navy; font-size:12pt; cursor:pointer\" onclick=\"insertAtCaret('commands','" + sym + " = ', 0)\">");
        state.printnlog("\\(" + latex_name(sym) + "\\) = ?<br>");
        state.printnlog("<br></span>");
    }

    function change_flag(flags, name, expression) {
        if (expression.trim() !== '0') {
            flags.add(name);
        } else {
            flags.delete(name);
        }
    }

    function deal_with_errors(err, command, state) {
        state.printit('<div style="color: red;"><pre>' + command + '</pre>');
        if (err.name === 'QuantError') {
            state.printit('Calculation failed: ' + err.message + '<br><br></div>');
            if (err.q) {
                var errWork = show_work(err.q, "problem", state.flags, true);
                state.printit(errWork[0].join('\n'));
            }
        } else {
            state.printit(err.message + '<br><br></div>');
        }
    }

    function calc(memory, commands, browser) {
        var state = new State(memory);
        var command_list = commands.replace(/\r/g, '').split("\n");

        for (var i = 0; i < command_list.length; i++) {
            var command = command_list[i];
            if (!command) continue;
            try {
                var classification = classify_input(command, state);
                var input_type = classification[0];
                var name = classification[1];
                var expression = classification[2];

                if (input_type === Calculation) {
                    name = check_name(name, state);
                    var quantity = interpret(expression, state);
                    state.printwork(show_work(quantity, name, state.flags));
                    register_result(quantity, name, state);
                } else if (input_type === CalcUsing) {
                    name = check_name(name, state);
                    var cuParts = expression.split(' using');
                    var exprPart = cuParts[0];
                    var prefUnits = cuParts.slice(1).join(' using').trim();
                    var qCalc = interpret(exprPart, state);
                    if (qCalc.provenance) {
                        throw CalcError("Please don't calculate and convert in a single statement");
                    }
                    register_result(qCalc, name, state);
                    convert_units(ConversionUsing, name, prefUnits, state);
                } else if (input_type === Comment) {
                    var commMod = root.Comments || (typeof require !== 'undefined' ? require('./comments') : null);
                    if (commMod && commMod.create_comment) {
                        commMod.create_comment(name, state);
                    } else {
                        state.printnlog('<span style="color:gray">' + name + '</span><br>');
                    }
                } else if (input_type === Unknown) {
                    create_unknown(name, state);
                } else if (input_type === ConversionUsing || input_type === ConversionIn) {
                    convert_units(input_type, name, expression, state);
                } else if (input_type === Flags) {
                    change_flag(state.flags, name, expression);
                }
                state.log_input(command);
            } catch (err) {
                deal_with_errors(err, command, state);
            }
        }
        return state.export();
    }

    return {
        State: State,
        calc: calc,
        classify_input: classify_input,
        show_work: show_work,
        register_result: register_result,
        convert_units: convert_units,
        latex_subs: latex_subs,
        InputTypes: {
            Empty: Empty,
            Calculation: Calculation,
            ConversionIn: ConversionIn,
            ConversionUsing: ConversionUsing,
            Comment: Comment,
            Flags: Flags,
            Unknown: Unknown,
            CalcUsing: CalcUsing
        }
    };
}));
