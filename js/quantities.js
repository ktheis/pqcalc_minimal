// js/quantities.js - Arithmetic with physical quantities, units, and uncertainty estimates
(function (root, factory) {
    if (typeof exports === 'object' && typeof module !== 'undefined') {
        var Fraction = require('./fraction');
        module.exports = factory(Fraction);
    } else {
        root.Quantities = factory(root.Fraction);
        // Expose primary symbols on root for convenience
        root.Units = root.Quantities.Units;
        root.unity = root.Quantities.unity;
        root.Q = root.Quantities.Q;
        root.X = root.Quantities.X;
        root.QuantError = root.Quantities.QuantError;
        root.unitquant = root.Quantities.unitquant;
        root.known_units = root.Quantities.known_units;
        root.functions = root.Quantities.functions;
        root.qfunc = root.Quantities.qfunc;
        root.latex_name = root.Quantities.latex_name;
        root.latex_number = root.Quantities.latex_number;
        root.latex_writer = root.Quantities.latex_writer;
        root.ascii_writer = root.Quantities.ascii_writer;
        root.ascii_number = root.Quantities.ascii_number;
        root.ascii_qvalue = root.Quantities.ascii_qvalue;
        root.number2quantity = root.Quantities.number2quantity;
        root.sigfig = root.Quantities.sigfig;
        root.unit_string = root.Quantities.unit_string;
    }
}(typeof self !== 'undefined' ? self : this, function (Fraction) {
    'use strict';

    var SIunit_symbols = ["A", "kg", "m", "s", "mol", "K", "Cd", "$"];

    function isFraction(v) {
        return v && typeof v === 'object' && ('numerator' in v) && ('denominator' in v);
    }

    function toNum(v) {
        if (isFraction(v)) return v.numerator / v.denominator;
        return Number(v);
    }

    function addExp(a, b) {
        if (isFraction(a) || isFraction(b)) {
            var fa = isFraction(a) ? a : new Fraction(a);
            var fb = isFraction(b) ? b : new Fraction(b);
            var res = fa.add(fb);
            return res.denominator === 1 ? res.numerator : res;
        }
        return a + b;
    }

    function subExp(a, b) {
        if (isFraction(a) || isFraction(b)) {
            var fa = isFraction(a) ? a : new Fraction(a);
            var fb = isFraction(b) ? b : new Fraction(b);
            var res = fa.sub(fb);
            return res.denominator === 1 ? res.numerator : res;
        }
        return a - b;
    }

    function mulExp(a, factor) {
        var numFactor = toNum(factor);
        if (isFraction(a) || isFraction(factor) || !Number.isInteger(numFactor)) {
            var fa = isFraction(a) ? a : new Fraction(a);
            var ff = isFraction(factor) ? factor : Fraction.fromFloat(numFactor);
            var res = fa.mul(ff);
            return res.denominator === 1 ? res.numerator : res;
        }
        var r = a * numFactor;
        return Number.isInteger(r) ? r : Fraction.fromFloat(r);
    }

    function Units(A, kg, m, s, mol, K, Cd, dollar) {
        if (!(this instanceof Units)) {
            return new Units(A, kg, m, s, mol, K, Cd, dollar);
        }
        if (typeof A === 'object' && A !== null && !isFraction(A)) {
            if (Array.isArray(A)) {
                this.exponents = A.slice();
            } else if (A instanceof Units) {
                this.exponents = A.exponents.slice();
            } else {
                this.exponents = [
                    A.A || 0,
                    A.kg || 0,
                    A.m || 0,
                    A.s || 0,
                    A.mol || 0,
                    A.K || 0,
                    A.Cd || 0,
                    A.dollar || A['$'] || 0
                ];
            }
        } else {
            this.exponents = [
                A || 0, kg || 0, m || 0, s || 0,
                mol || 0, K || 0, Cd || 0, dollar || 0
            ];
        }

        for (var i = 0; i < 8; i++) {
            var val = this.exponents[i];
            if (typeof val === 'number') {
                if (!Number.isInteger(val)) {
                    this.exponents[i] = Fraction.fromFloat(val);
                }
            }
        }
    }

    Units.prototype.copy = function () {
        return new Units(this.exponents.slice());
    };

    Units.prototype.equals = function (other) {
        if (!(other instanceof Units)) return false;
        for (var i = 0; i < 8; i++) {
            var a = this.exponents[i];
            var b = other.exponents[i];
            if (isFraction(a) || isFraction(b)) {
                var fa = isFraction(a) ? a : new Fraction(a);
                var fb = isFraction(b) ? b : new Fraction(b);
                if (!fa.equals(fb)) return false;
            } else if (a !== b) {
                return false;
            }
        }
        return true;
    };

    Units.prototype.isUnity = function () {
        for (var i = 0; i < 8; i++) {
            var a = this.exponents[i];
            if (isFraction(a)) {
                if (a.numerator !== 0) return false;
            } else if (a !== 0) {
                return false;
            }
        }
        return true;
    };

    Units.prototype.toString = function () {
        var parts = [];
        for (var i = 0; i < 8; i++) {
            var exp = this.exponents[i];
            var nonzero = isFraction(exp) ? exp.numerator !== 0 : exp !== 0;
            if (nonzero) {
                parts.push(SIunit_symbols[i] + '=' + exp.toString());
            }
        }
        return "Units(" + parts.join(",") + ")";
    };

    var unity = new Units();

    function QuantError(complaint, q) {
        var message = Array.isArray(complaint) ? complaint[0] : (typeof complaint === 'string' ? complaint : 'QuantError');
        var err = new Error(message);
        err.name = 'QuantError';
        err.complaint = complaint;
        err.q = q;
        Object.setPrototypeOf(err, QuantError.prototype);
        return err;
    }
    QuantError.prototype = Object.create(Error.prototype);
    QuantError.prototype.constructor = QuantError;

    function raise_QuantError(complaint, name, provenance) {
        throw QuantError([complaint, new Q(0, name, unity, 0.0, new Set(), provenance)]);
    }

    var opprio = {
        "%s ^ %s": 5,
        "%s * %s": 3,
        "%s / %s": 3,
        "%s + %s": 2,
        "-%s": 3,
        "%s - %s": 2
    };

    // Q class
    function Q(number, name, units, uncert, prefu, provenance) {
        if (!(this instanceof Q)) {
            return new Q(number, name, units, uncert, prefu, provenance);
        }
        if (typeof number === 'undefined') {
            number = 0.0;
        }

        if (typeof number === 'string') {
            var trimmed = number.trim();
            if (unitquant && trimmed in unitquant) {
                var uq = unitquant[trimmed];
                this.number = uq.number;
                this.units = uq.units.copy();
                this.name = uq.name;
                this.uncert = uq.uncert;
                this.prefu = new Set(uq.prefu);
                this.provenance = null;
                this.comment = '';
                return;
            } else {
                var parsed = number2quantity(number);
                this.number = parsed.number;
                this.units = parsed.units.copy();
                this.name = parsed.name || '';
                this.uncert = parsed.uncert;
                this.prefu = new Set(parsed.prefu);
                this.provenance = null;
                this.comment = '';
                return;
            }
        }

        if (number instanceof Q) {
            this.number = number.number;
            this.units = number.units.copy();
            this.name = (typeof name !== 'undefined') ? name : number.name;
            this.uncert = (typeof uncert !== 'undefined') ? uncert : number.uncert;
            this.prefu = (typeof prefu !== 'undefined') ? new Set(prefu) : new Set(number.prefu);
            this.provenance = (typeof provenance !== 'undefined') ? provenance : number.provenance;
            this.comment = number.comment || '';
            return;
        }

        this.number = isFraction(number) ? number : Number(number);
        this.name = name ? '' + name : '';
        this.units = units instanceof Units ? units.copy() : (units ? new Units(units) : unity.copy());
        this.uncert = uncert ? Number(uncert) : 0.0;
        this.prefu = prefu ? new Set(prefu) : new Set();
        if (this.prefu.has('M')) {
            this.prefu.add('L');
        }
        this.provenance = provenance || null;
        this.comment = '';
    }

    Q.prototype.copy = function () {
        return new Q(this.number, this.name, this.units, this.uncert, new Set(this.prefu),
            this.provenance ? this.provenance.slice() : null);
    };

    Q.prototype.setdepth = function () {
        if (typeof this.depth === 'undefined') {
            if (!this.provenance || this.provenance.length === 0) {
                this.depth = 0;
            } else {
                var maxD = 0;
                for (var i = 0; i < this.provenance.length; i++) {
                    var cd = this.provenance[i].setdepth();
                    if (cd > maxD) maxD = cd;
                }
                this.depth = 1 + maxD;
                if (this.name === "-%s") {
                    this.depth -= 1;
                }
            }
        }
        return this.depth;
    };

    Q.prototype.steps = function (level, writer, subs, flags) {
        flags = flags || new Set();
        if (level < 0 && !this.provenance) {
            return writer(this, false, 0, flags);
        }
        if (level === 0 || (this.depth && level > this.depth)) {
            var guard = (level <= 1 || !this.provenance) ? 0 : 1;
            return writer(this, true, guard, flags);
        }
        if (!this.provenance) {
            return writer(this, false, 0, flags);
        }

        var name = this.name;
        var ll = -1;
        for (var i = 0; i < this.provenance.length; i++) {
            if (typeof this.provenance[i].depth !== 'undefined' && this.provenance[i].depth > ll) {
                ll = this.provenance[i].depth;
            }
        }

        var children = [];
        for (var j = 0; j < this.provenance.length; j++) {
            children.push(child(j, level, name, this.provenance[j], subs, writer, flags, ll));
        }

        if (subs && subs[name]) {
            name = subs[name];
        }
        if (subs && name.length > 6) {
            var prefix6 = name.slice(0, 6);
            if (prefix6 === 'sum(%s' || prefix6 === 'avg(%s' || prefix6 === 'min(%s' || prefix6 === 'max(%s') {
                if (subs[prefix6]) {
                    name = name.replace(prefix6, subs[prefix6]);
                }
            }
        }

        // Format placeholder string like "%s * %s" or "\dfrac{%s}{%s}"
        var parts = name.split('%s');
        var res = parts[0];
        for (var k = 0; k < children.length; k++) {
            res += children[k] + (parts[k + 1] !== undefined ? parts[k + 1] : '');
        }
        return res;
    };

    function child(index, level, name, q, subs, writer, flags, ll) {
        var ch = q.steps(level, writer, subs, flags);
        if (q.prefu.has('°aC') && level >= 1 && ll < level && (name.indexOf('/') !== -1 || name.indexOf('*') !== -1)) {
            q.prefu.delete('°aC');
            ch = q.steps(level, writer, subs, flags);
        }
        var needParen = false;
        var curPrio = opprio[name] || 0;
        var childPrio = opprio[q.name] || 0;

        if (q.provenance && level <= q.depth && curPrio > childPrio && curPrio && childPrio && !(subs && name.indexOf('/') !== -1)) {
            needParen = true;
        } else if (name.startsWith('-') && ch.startsWith('-')) {
            needParen = true;
        } else if (name.indexOf('-') !== -1 && index === 1 && ch.startsWith('-')) {
            needParen = true;
        } else if (name.indexOf('*') !== -1 && index === 1 && ch.startsWith('-')) {
            needParen = true;
        } else if (name.indexOf('^') !== -1 && level >= 0 && !q.units.isUnity()) {
            needParen = true;
        } else if (name.indexOf('^') !== -1 && ch.startsWith('-') && index === 0) {
            needParen = true;
        } else if (name.indexOf('^') !== -1 && (ch.indexOf('times') !== -1 || ch.indexOf('frac') !== -1)) {
            needParen = true;
        }

        if (needParen) {
            return "(" + ch + ")";
        }
        return ch;
    }

    function inherit_binary(q1, q2) {
        var prefu = new Set(q1.prefu);
        q2.prefu.forEach(function (u) { prefu.add(u); });
        var provenance = [q1, q2];
        return { prefu: prefu, provenance: provenance };
    }

    // Arithmetic methods on Q
    Q.prototype.mul = function (other) {
        if (!(other instanceof Q)) other = new Q(other);
        var newExps = [];
        for (var i = 0; i < 8; i++) {
            newExps.push(addExp(this.units.exponents[i], other.units.exponents[i]));
        }
        var newUnits = new Units(newExps);
        var n1 = toNum(this.number);
        var n2 = toNum(other.number);
        var prod = n1 * n2;
        return muldiv(prod, '%s * %s', newUnits, this, other);
    };

    Q.prototype.div = function (other) {
        if (!(other instanceof Q)) other = new Q(other);
        var n2 = toNum(other.number);
        if (n2 === 0) {
            raise_QuantError("denominator is zero", "%s / %s", [this, other]);
        }
        var newExps = [];
        for (var i = 0; i < 8; i++) {
            newExps.push(subExp(this.units.exponents[i], other.units.exponents[i]));
        }
        var newUnits = new Units(newExps);
        var n1 = toNum(this.number);
        var quot = n1 / n2;
        return muldiv(quot, '%s / %s', newUnits, this, other);
    };

    Q.prototype.add = function (other) {
        if (!(other instanceof Q)) other = new Q(other);
        var n1 = toNum(this.number);
        var n2 = toNum(other.number);
        return addsub(n1 + n2, '%s + %s', this, other);
    };

    Q.prototype.sub = function (other) {
        if (!(other instanceof Q)) other = new Q(other);
        var n1 = toNum(this.number);
        var n2 = toNum(other.number);
        return addsub(n1 - n2, '%s - %s', this, other);
    };

    Q.prototype.neg = function () {
        if (this.name === "-%s" && this.provenance) {
            return this.provenance[0];
        }
        return new Q(-toNum(this.number), "-%s", this.units.copy(), this.uncert, new Set(this.prefu), [this]);
    };

    Q.prototype.pos = function () {
        return this;
    };

    Q.prototype.pow = function (other) {
        if (!(other instanceof Q)) other = new Q(other);
        if (!other.units.isUnity()) {
            raise_QuantError("the exponent can't have units", "%s ^ %s", [this, other]);
        }
        var expVal = other.number;
        var expNum = toNum(expVal);
        var newUnits;
        if (this.units.isUnity()) {
            newUnits = this.units.copy();
        } else {
            if (!Number.isInteger(expNum) && !isFraction(expVal)) {
                raise_QuantError("can't raise units to irrational exponent", "%s ^ %s", [this, other]);
            }
            var newExps = [];
            for (var i = 0; i < 8; i++) {
                newExps.push(mulExp(this.units.exponents[i], expVal));
            }
            newUnits = new Units(newExps);
        }

        var baseNum = toNum(this.number);
        if (baseNum < 0 && !Number.isInteger(expNum)) {
            raise_QuantError("complex numbers not implemented", "%s ^ %s", [this, other]);
        }
        var val = Math.pow(baseNum, expNum);
        if (!isFinite(val)) {
            raise_QuantError("overflow: value too high", "%s ^ %s", [this, other]);
        }

        var uncert1 = 0.0;
        if (baseNum !== 0) {
            uncert1 = Math.abs((this.uncert / baseNum) * val * expNum);
        }
        var uncert2 = 0.0;
        if (baseNum !== 0) {
            uncert2 = Math.abs(other.uncert * Math.log(Math.abs(baseNum)) * val);
        }
        var totalUncert = uncert1 + uncert2;
        return new Q(val, '%s ^ %s', newUnits, totalUncert, new Set(this.prefu), [this, other]);
    };

    function addsub(number, name, left, right) {
        var n1 = toNum(left.number);
        var n2 = toNum(right.number);
        if (!left.units.equals(right.units) && n1 !== 0 && n2 !== 0) {
            raise_QuantError("Units in sum/difference not compatible", name, [left, right]);
        }
        var bin = inherit_binary(left, right);
        var prefu = bin.prefu;
        var provenance = bin.provenance;
        var units = (n1 !== 0) ? left.units.copy() : right.units.copy();
        var uncert = Math.sqrt(Math.pow(left.uncert, 2) + Math.pow(right.uncert, 2));

        if (prefu.has('°aC')) {
            if (!units.equals(unitquant['K'].units)) {
                raise_QuantError("Units °aC in sum/difference can't have compound units", name, [left, right]);
            }
            if (left.prefu.has('°aC') && right.prefu.has('°ΔC')) {
                prefu.delete('°ΔC');
            } else if (right.prefu.has('°aC') && left.prefu.has('°ΔC') && name === '%s + %s') {
                prefu.delete('°ΔC');
            } else if (left.prefu.has('°aC') && right.prefu.has('°aC') && name === '%s - %s') {
                prefu.delete('°aC');
                prefu.add('°ΔC');
            } else if (n1 !== 0 && n2 !== 0) {
                prefu.delete('°aC');
            }
        }
        return new Q(number, name, units, uncert, prefu, provenance);
    }

    function muldiv(number, name, units, self, other) {
        var n1 = toNum(self.number);
        var n2 = toNum(other.number);
        var uncert;
        if (number !== 0) {
            uncert = Math.sqrt(Math.pow(self.uncert / n1, 2) + Math.pow(other.uncert / n2, 2)) * Math.abs(number);
        } else if (!other.uncert) {
            uncert = self.uncert;
        } else if (!self.uncert) {
            uncert = other.uncert;
        } else {
            uncert = 0.0;
        }
        var bin = inherit_binary(self, other);
        var prefu = bin.prefu;
        var provenance = bin.provenance;
        if (prefu.has('°aC')) {
            prefu.delete('°aC');
        }
        return new Q(number, name, units, uncert, prefu, provenance);
    }

    // Significant figures and number formatting
    function sigfig(number, uncert) {
        if (!uncert) return 100;
        var numVal = toNum(number);
        var uncVal = toNum(uncert);
        if (!numVal) {
            return 1 - Math.floor(Math.log10(uncVal * 1.05));
        }
        var most = Math.floor(Math.log10(Math.abs(numVal)));
        var sig = Math.floor(Math.log10(uncVal * 1.05));
        var sf = most - sig + 1;
        return sf > 0 ? sf : 1;
    }

    function mostsig(number, ope) {
        ope = ope || 1.00000000001;
        return Math.floor(Math.log10(Math.abs(number) * ope));
    }

    function format_uncert(number, sigfig, uncert) {
        var least, uStr;
        if (uncert) {
            var u = Number(uncert).toPrecision(1).toUpperCase();
            if (u.indexOf('.') !== -1 && u.indexOf('E') === -1) {
                least = -u.split('.')[1].length;
            } else if (u.indexOf('E') === -1) {
                least = u.length;
            }
            var cleanU = u.replace('.', '').replace(/^0+/, '');
            if (cleanU.indexOf('E') !== -1) {
                var uparts = cleanU.split('E');
                cleanU = uparts[0];
                least = parseInt(uparts[1], 10) - 1;
            }
            uStr = "(" + cleanU + ")";
        } else {
            uStr = "";
            least = mostsig(number) - sigfig + 1;
        }
        return { least: least, uStr: uStr };
    }

    function exact_number(number, delta) {
        delta = delta || 1e-10;
        if (isFraction(number)) {
            if (number.denominator === 1) return '' + number.numerator;
            if (number.numerator > 0) return "(" + number.numerator + " / " + number.denominator + ")";
            return "-(" + (-number.numerator) + " / " + number.denominator + ")";
        }
        var n = Number(number);
        if (Math.abs(n - Math.round(n)) < delta) {
            return '' + Math.round(n);
        }
        var frac = Fraction.fromFloat(n, 10000);
        if (frac.numerator && frac.denominator < 10000) {
            var discr = (n * frac.denominator) / frac.numerator;
            if (discr > 0.99999999 && discr < 1.00000001) {
                if (frac.numerator > 0) return "(" + frac.numerator + " / " + frac.denominator + ")";
                return "-(" + (-frac.numerator) + " / " + frac.denominator + ")";
            }
        }
        return ascii_number(number, 17, 0.0, delta);
    }

    function ascii_number(number, sf, uncert, delta) {
        delta = delta || 1e-10;
        var num = toNum(number);
        if (!uncert && sf >= 100) {
            return exact_number(number, delta);
        }
        if (num === 0.0) {
            if (sf && sf > 1) {
                var zeros = '';
                for (var i = 0; i < sf - 1; i++) zeros += '0';
                return '0.' + zeros;
            }
            return "0";
        }
        var fu = format_uncert(num, sf, uncert);
        var least = fu.least;
        var uncert_str = fu.uStr;

        if (least < 0 && -2 < (least + sf) && (least + sf) < 5) {
            var decPlaces = -least;
            return num.toFixed(decPlaces) + uncert_str;
        }
        if (least === 0) {
            return num.toFixed(0) + uncert_str + ".";
        }
        if (sf) {
            var expDigits = sf - 1;
            var t = num.toExponential(expDigits);
            // match python's format: e+01 -> e1, e-01 -> e-1
            t = t.replace(/e\+0?/i, 'e').replace(/e-0/i, 'e-');
            var m_e = t.split('e');
            return m_e[0] + uncert_str + 'e' + m_e[1];
        }
        return num.toFixed(0) + "(?)";
    }

    function number2quantity(text) {
        text = ('' + text).trim();
        var mult = 1;
        if (text.indexOf('(') !== -1 && text.indexOf(')') !== -1) {
            var p1 = text.indexOf('(');
            var p2 = text.indexOf(')');
            var before = text.slice(0, p1);
            var uncPart = text.slice(p1 + 1, p2);
            var after = text.slice(p2 + 1);
            text = before + after;
            mult = parseFloat(uncPart);
        }
        if (text.indexOf('/') !== -1) {
            var fparts = text.split('/');
            return new Q(new Fraction(parseInt(fparts[0], 10), parseInt(fparts[1], 10)), "", unity, 0);
        }
        var f = parseFloat(text);
        var textClean = text.toLowerCase().replace(/^-?0+/, '');
        var expo = 0;
        if (textClean.indexOf('e') !== -1) {
            var eparts = textClean.split('e');
            textClean = eparts[0];
            expo = parseInt(eparts[1], 10);
        }
        if (textClean.indexOf('.') !== -1 || mult !== 1) {
            if (textClean.indexOf('.') !== -1) {
                var dparts = textClean.split('.');
                expo -= dparts[1].length;
            }
            var uncert = Math.pow(10, expo) * mult;
            return new Q(f, "", unity, uncert);
        }
        return new Q(f, "", unity, 0.0);
    }

    function latex_number(ascii) {
        if (ascii.indexOf('e') !== -1) {
            return ascii.replace('e', '\\times 10^{') + '}';
        }
        if (ascii.indexOf('/') !== -1 && ascii.indexOf('(') !== -1) {
            var sign = ascii.split('(')[0];
            var rest = ascii.split('(')[1];
            var fparts = rest.split('/');
            var den = fparts[1].replace(/\)$/, '').trim();
            return sign + "\\frac{" + fparts[0].trim() + "}{" + den + "}";
        }
        return ascii;
    }

    function latex_name(name) {
        name = name + '_';
        var head, tail;
        if (name.startsWith('[') || name.startsWith('Δ[')) {
            if (name[0] !== 'Δ') {
                var lastIdx = name.lastIndexOf(']');
                head = name.slice(1, lastIdx);
                tail = name.slice(lastIdx + 1);
                head = '[\\ce{' + head + '}]';
            } else {
                var lastIdxD = name.lastIndexOf(']');
                head = name.slice(2, lastIdxD);
                tail = name.slice(lastIdxD + 1);
                head = 'Δ[\\ce{' + head + '}]';
            }
        } else {
            if (name.indexOf('[') !== -1) {
                var m = name.match(/^([^[]+)\[(.*)\]([^]]*)$/);
                if (m) {
                    name = m[1] + '_\\ce{' + m[2] + '}_' + m[3];
                }
            }
            var splitPos = name.indexOf('_');
            head = name.slice(0, splitPos);
            tail = name.slice(splitPos + 1);
            if (head.length > 1) {
                if (/^.[0-9]+$/.test(head)) {
                    head = name.slice(0, 1);
                    tail = name.slice(1);
                } else if (/^Δ.[0-9]+$/.test(head)) {
                    head = name.slice(0, 2);
                    tail = name.slice(2);
                } else {
                    var asciiLetterCount = 0;
                    for (var c = 0; c < head.length; c++) {
                        var code = head.charCodeAt(c);
                        if ((code >= 65 && code <= 90) || (code >= 97 && code <= 122)) asciiLetterCount++;
                    }
                    if (asciiLetterCount > 1) {
                        head = '\\mathrm{' + head.replace(/&/g, '\\&').replace(/%/g, '\\%').replace(/\$/g, '\\$') + '}';
                    }
                }
            }
        }

        // Subscripts
        var subscripts = [];
        var rx = /(\\ce\{.*\}|[^_]+)_/g;
        var match;
        while ((match = rx.exec(tail)) !== null) {
            subscripts.push(match[1]);
        }
        head = head.replace(/ᵣ/g, '_r');
        if (subscripts.length > 0) {
            if (subscripts.length === 2 && subscripts[1] && (subscripts[0].length === 1 || subscripts[0].indexOf('\\ce{') !== -1)) {
                return head + '_{\\mathrm{' + subscripts.join(',') + '}}';
            }
            return head + '_{\\mathrm{' + subscripts.join('\\ ') + '}}';
        }
        return head;
    }

    function ascii_units(list1) {
        var list2 = [];
        for (var i = 0; i < list1.length; i++) {
            if (list1[i][1] === 1) {
                list2.push(list1[i][0]);
            } else {
                list2.push(list1[i][0] + '^' + list1[i][1]);
            }
        }
        return list2.join(' ');
    }

    function latex_units(list1) {
        var list2 = [];
        for (var i = 0; i < list1.length; i++) {
            var uName = list1[i][0];
            var uExp = list1[i][1];
            if (uExp === 1) {
                list2.push("\\mathrm{" + uName + "}");
            } else {
                list2.push("\\mathrm{" + uName + "}^{" + uExp + "}");
            }
        }
        return list2.join('\\ ');
    }

    function try_all_derived(SIunits, derived) {
        var bestImprovement = -Infinity;
        var bestD = null;
        var bestSign = 0;

        for (var d in derived) {
            for (var sIdx = 0; sIdx < 2; sIdx++) {
                var sign = (sIdx === 0) ? -1 : 1;
                if (derived[d] * sign < 0) continue;
                var improvement = -30;
                var dUnits = unitquant[d].units.exponents;
                for (var i = 0; i < 8; i++) {
                    var oldVal = toNum(SIunits[i]);
                    var usedVal = toNum(dUnits[i]);
                    improvement += 20 * (Math.abs(oldVal) - Math.abs(oldVal - sign * usedVal));
                    if (oldVal !== 0 && (oldVal - sign * usedVal) === 0) {
                        improvement += 6;
                    }
                }
                if (improvement > bestImprovement) {
                    bestImprovement = improvement;
                    bestD = d;
                    bestSign = sign;
                }
            }
        }
        return { improvement: bestImprovement, d: bestD, sign: bestSign };
    }

    function unit_string(value, units, prefu) {
        prefu = prefu ? new Set(prefu) : new Set(['L', 'J', 'C', 'V', 'N', 'W', 'Pa']);
        value = toNum(value);
        if (units.isUnity() || value === 0) {
            if (value !== 0 && prefu.has('％')) {
                return { value: value * 100, poslist: [['％', 1]], neglist: [] };
            }
            return { value: value, poslist: [], neglist: [] };
        }

        var SIunits = units.exponents.slice();
        var derived = {};
        prefu.forEach(function (pu) {
            if (unitquant && unitquant[pu]) {
                var sumAbs = 0;
                for (var i = 0; i < 8; i++) sumAbs += Math.abs(toNum(unitquant[pu].units.exponents[i]));
                if (sumAbs > 1) {
                    derived[pu] = 0;
                }
            }
        });

        while (Object.keys(derived).length > 0) {
            var step = try_all_derived(SIunits, derived);
            if (step.improvement <= 0 || !step.d) break;
            derived[step.d] += step.sign;
            var dUnits = unitquant[step.d].units.exponents;
            for (var j = 0; j < 8; j++) {
                SIunits[j] = subExp(SIunits[j], mulExp(dUnits[j], step.sign));
            }
            value /= Math.pow(toNum(unitquant[step.d].number), step.sign);
        }

        var allunits = {};
        for (var dName in derived) {
            if (derived[dName]) allunits[dName] = derived[dName];
        }

        // Choose between equal dimensions in derived (e.g. atm vs mmHg)
        for (var DU in allunits) {
            if (!(DU in derived)) continue;
            var choices = [];
            for (var puName in derived) {
                if (unitquant[puName].units.equals(unitquant[DU].units)) {
                    choices.push(puName);
                }
            }
            if (choices.length === 0) break;
            var bestChoice = DU;
            var bestQuality = Infinity;
            for (var c = 0; c < choices.length; c++) {
                var ch = choices[c];
                var ratio = toNum(unitquant[ch].number) / toNum(unitquant[DU].number);
                var qual = Math.abs(Math.log10(Math.abs(value) / Math.pow(ratio, allunits[DU])) - 1.0);
                if (qual < bestQuality) {
                    bestQuality = qual;
                    bestChoice = ch;
                }
            }
            if (bestChoice !== DU) {
                allunits[bestChoice] = allunits[DU];
                var scaleRatio = toNum(unitquant[bestChoice].number) / toNum(unitquant[DU].number);
                value /= Math.pow(scaleRatio, allunits[bestChoice]);
                allunits[DU] = 0;
            }
        }

        // Choose between base unit prefixes (m, cm, mm, etc.)
        for (var si = 0; si < 8; si++) {
            if (!SIunits[si] || toNum(SIunits[si]) === 0) continue;
            var baseChoices = [];
            prefu.forEach(function (pu) {
                if (!(pu in derived) && (pu in unitquant) && toNum(unitquant[pu].units.exponents[si]) !== 0) {
                    baseChoices.push(pu);
                }
            });
            if (baseChoices.length === 0) continue;
            var bestBaseChoice = baseChoices[0];
            var bestBaseQuality = Infinity;
            for (var b = 0; b < baseChoices.length; b++) {
                var bName = baseChoices[b];
                var expFraction = toNum(SIunits[si]) / toNum(unitquant[bName].units.exponents[si]);
                var bQual = Math.abs(Math.log10(Math.abs(value) / Math.pow(toNum(unitquant[bName].number), expFraction)) - 1.0);
                if (bQual < bestBaseQuality) {
                    bestBaseQuality = bQual;
                    bestBaseChoice = bName;
                }
            }
            var assignedExp = Fraction.fromFloat(toNum(SIunits[si]) / toNum(unitquant[bestBaseChoice].units.exponents[si]));
            allunits[bestBaseChoice] = assignedExp.denominator === 1 ? assignedExp.numerator : assignedExp;
            SIunits[si] = 0;
            value /= Math.pow(toNum(unitquant[bestBaseChoice].number), toNum(allunits[bestBaseChoice]));
        }

        for (var uIdx = 0; uIdx < 8; uIdx++) {
            var leftoverExp = SIunits[uIdx];
            if (leftoverExp && toNum(leftoverExp) !== 0) {
                allunits[SIunit_symbols[uIdx]] = leftoverExp;
            }
        }

        if (prefu.has('°ΔC') && allunits['K']) {
            allunits['°ΔC'] = allunits['K'];
            delete allunits['K'];
        } else if (prefu.has('°aC') && allunits['K'] === 1 && Object.keys(allunits).length === 1) {
            allunits = { '°aC': 1 };
            value -= 273.15;
        }

        var poslist = [];
        var neglist = [];
        for (var uKey in allunits) {
            var expVal = toNum(allunits[uKey]);
            if (expVal > 0) {
                poslist.push([uKey, isFraction(allunits[uKey]) ? allunits[uKey] : expVal]);
            } else if (expVal < 0) {
                neglist.push([uKey, isFraction(allunits[uKey]) ? allunits[uKey].mul(-1) : -expVal]);
            }
        }

        return { value: value, poslist: poslist, neglist: neglist };
    }

    function ascii_qvalue(q, guard) {
        guard = guard || 0;
        var us = unit_string(q.number, q.units, q.prefu);
        var sf = sigfig(q.number, q.uncert) + guard;
        var numbertext = ascii_number(us.value, sf);
        var negtext = "";
        if (us.neglist.length === 1 && us.neglist[0][1] === 1) {
            negtext = "/" + us.neglist[0][0];
        } else if (us.neglist.length > 0) {
            negtext = "/(" + ascii_units(us.neglist) + ")";
        }
        if (us.poslist.length === 0) {
            if (us.neglist.length === 0) return numbertext;
            return numbertext + " 1" + negtext;
        }
        return numbertext + " " + ascii_units(us.poslist) + negtext;
    }

    function latex_qvalue(q, guard, flags) {
        guard = guard || 0;
        flags = flags || new Set();
        var us = unit_string(q.number, q.units, q.prefu);
        var value = us.value;
        var poslist = us.poslist;
        var neglist = us.neglist;

        var uc;
        if (poslist.length === 1 && poslist[0][0] === '°aC' && poslist[0][1] === 1) {
            uc = q.uncert;
        } else {
            var qnum = toNum(q.number);
            uc = qnum !== 0 ? q.uncert * value / qnum : q.uncert;
        }
        var sf = sigfig(value, uc);
        var numbertext;
        if (flags.has('__showuncert__')) {
            numbertext = latex_number(ascii_number(value, sf, uc));
        } else if (flags.has('__hidenumbers__')) {
            numbertext = "\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_\\_";
        } else {
            numbertext = latex_number(ascii_number(value, sf + guard));
        }

        if (flags.has('__hideunits__')) {
            return numbertext + (!q.units.isUnity() ? "\\phantom{\\frac{km mol}{kg mol}}" : "");
        }

        var unittext;
        if (neglist.length > 0) {
            unittext = "\\frac{%s}{" + latex_units(neglist) + "}";
        } else {
            unittext = "%s";
        }

        if (poslist.length === 0) {
            if (neglist.length === 0) return numbertext;
            return numbertext + unittext.replace('%s', '1');
        }
        return numbertext + "\\  " + unittext.replace('%s', latex_units(poslist));
    }

    function ascii_writer(q, showvalue, guard, flags) {
        if (!showvalue && q.name) return q.name;
        return ascii_qvalue(q, guard);
    }

    function latex_writer(q, showvalue, guard, flags) {
        if (!showvalue && q.name) return latex_name(q.name);
        return latex_qvalue(q, guard, flags);
    }

    // Known units definition
    var known_units = {
        A: [1, new Units({ A: 1 })],
        g: [new Fraction(1, 1000), new Units({ kg: 1 })],
        Da: [1.660539040E-27, new Units({ kg: 1 })],
        m: [1, new Units({ m: 1 })],
        cm: [new Fraction(1, 100), new Units({ m: 1 })],
        s: [1, new Units({ s: 1 })],
        mol: [1, new Units({ mol: 1 })],
        K: [1, new Units({ K: 1 })],
        Cd: [1, new Units({ Cd: 1 })],
        N: [1, new Units({ kg: 1, m: 1, s: -2 })],
        J: [1, new Units({ kg: 1, m: 2, s: -2 })],
        eV: [1.602176565e-19, new Units({ kg: 1, m: 2, s: -2 })],
        V: [1, new Units({ A: -1, kg: 1, m: 2, s: -3 })],
        C: [1, new Units({ A: 1, s: 1 })],
        L: [new Fraction(1, 1000), new Units({ m: 3 })],
        M: [1000, new Units({ mol: 1, m: -3 })],
        Pa: [1, new Units({ kg: 1, m: -1, s: -2 })],
        Hz: [1, new Units({ s: -1 })],
        atm: [101325, new Units({ kg: 1, m: -1, s: -2 })],
        mmHg: [133.322368421, new Units({ kg: 1, m: -1, s: -2 })],
        torr: [133.322368421, new Units({ kg: 1, m: -1, s: -2 })],
        min: [60, new Units({ s: 1 })],
        h: [3600, new Units({ s: 1 })],
        W: [1, new Units({ kg: 1, m: 2, s: -3 })],
        parsec: [3.085677581e16, new Units({ m: 1 })],
        "Ω": [1.0, new Units({ A: -2, kg: 1, m: 2, s: -3 })],
        "$": [1.0, new Units({ dollar: 1 })],
        "Å": [new Fraction(1, 10000000000), new Units({ m: 1 })],
        "％": [new Fraction(1, 100), unity]
    };

    var metric_prefices = {
        f: new Fraction(1, 1000000000000000),
        p: new Fraction(1, 1000000000000),
        n: new Fraction(1, 1000000000),
        u: new Fraction(1, 1000000),
        'μ': new Fraction(1, 1000000),
        m: new Fraction(1, 1000),
        k: 1000,
        M: 1000000,
        G: 1000000000,
        T: 1000000000000
    };

    var unitquant = {};
    for (var uKey in known_units) {
        var meaning = known_units[uKey];
        unitquant[uKey] = new Q(meaning[0], uKey, meaning[1], 0, [uKey]);
        if (["cm", "h", "d", "atm", "kg", "min", "mmHg", "$", "％"].indexOf(uKey) !== -1) {
            continue;
        }
        for (var prefix in metric_prefices) {
            var punit = prefix + uKey;
            var pfactor = metric_prefices[prefix];
            var pVal;
            if (isFraction(meaning[0]) || isFraction(pfactor)) {
                var fm = isFraction(meaning[0]) ? meaning[0] : Fraction.fromFloat(meaning[0]);
                var fp = isFraction(pfactor) ? pfactor : Fraction.fromFloat(pfactor);
                pVal = fm.mul(fp);
            } else {
                pVal = meaning[0] * pfactor;
            }
            unitquant[punit] = new Q(pVal, punit, meaning[1], 0, [punit]);
        }
    }

    // Special temperature units in unitquant
    unitquant['°ΔC'] = new Q(1, '°ΔC', unitquant['K'].units.copy(), 0, ['°ΔC']);
    unitquant['°aC'] = new Q(1, '°aC', unitquant['K'].units.copy(), 0, ['°aC']);

    // Functions on Q
    function check_argument(fn, name) {
        return function (a) {
            if (arguments.length > 1) {
                raise_QuantError("This function cannot have more than one argument", name + "(%s,%s ...)", [arguments[0], arguments[1]]);
            }
            if (!(a instanceof Q)) a = new Q(a);
            if (!a.units.isUnity()) {
                raise_QuantError("Can't apply function to quantity with units", name + "(%s)", [a]);
            }
            return fn(a);
        };
    }

    function unit_mismatch(arr) {
        var u = arr[0].units;
        for (var i = 0; i < arr.length; i++) {
            if (!u.equals(arr[i].units)) return arr[i];
        }
        if (arr[0].prefu.has('°aC')) {
            for (var j = 0; j < arr.length; j++) {
                if (!arr[j].prefu.has('°aC')) {
                    raise_QuantError("If one temperature is in absolute degC, all others have to be as well", "average(%s...%s)", [arr[0], arr[j]]);
                }
            }
        } else {
            for (var k = 0; k < arr.length; k++) {
                if (arr[k].prefu.has('°aC')) {
                    raise_QuantError("If one temperature is in absolute degC, all others have to be as well", "average(%s...%s)", [arr[0], arr[k]]);
                }
            }
        }
        return null;
    }

    var qexp = check_argument(function (a) {
        var num = Math.exp(toNum(a.number));
        return new Q(num, "exp0(%s)", a.units, Math.abs(a.uncert * num), new Set(a.prefu), [a]);
    }, "exp");

    function qsqrt(a) {
        if (!(a instanceof Q)) a = new Q(a);
        var ans = a.pow(new Q(new Fraction(1, 2)));
        ans.name = "sqrt(%s)";
        ans.provenance = [a];
        return ans;
    }

    var qlog = check_argument(function (a) {
        var n = toNum(a.number);
        if (n <= 0) raise_QuantError("The argument of the function is outside of the allowed range (negative?)", "log(%s)", [a]);
        return new Q(Math.log10(n), "log(%s)", a.units, Math.abs(a.uncert / n), new Set(a.prefu), [a]);
    }, "log");

    var qln = check_argument(function (a) {
        var n = toNum(a.number);
        if (n <= 0) raise_QuantError("The argument of the function is outside of the allowed range (negative?)", "ln(%s)", [a]);
        return new Q(Math.log(n), "ln(%s)", a.units, Math.abs(a.uncert / n), new Set(a.prefu), [a]);
    }, "ln");

    var qsin = check_argument(function (a) {
        var n = toNum(a.number);
        return new Q(Math.sin(n), "sin(%s)", a.units, Math.abs(a.uncert * Math.cos(n)), new Set(a.prefu), [a]);
    }, "sin");

    var qcos = check_argument(function (a) {
        var n = toNum(a.number);
        return new Q(Math.cos(n), "cos(%s)", a.units, Math.abs(a.uncert * Math.sin(n)), new Set(a.prefu), [a]);
    }, "cos");

    var qtan = check_argument(function (a) {
        var n = toNum(a.number);
        var num = Math.tan(n);
        return new Q(num, "tan(%s)", a.units, a.uncert * (1 + num * num), new Set(a.prefu), [a]);
    }, "tan");

    var qasin = check_argument(function (a) {
        var n = toNum(a.number);
        if (n < -1 || n > 1) raise_QuantError("The argument of the function is outside of the allowed range", "asin(%s)", [a]);
        return new Q(Math.asin(n), "asin(%s)", a.units, a.uncert, new Set(a.prefu), [a]);
    }, "asin");

    var qacos = check_argument(function (a) {
        var n = toNum(a.number);
        if (n < -1 || n > 1) raise_QuantError("The argument of the function is outside of the allowed range", "acos(%s)", [a]);
        return new Q(Math.acos(n), "acos(%s)", a.units, a.uncert, new Set(a.prefu), [a]);
    }, "acos");

    var qatan = check_argument(function (a) {
        var n = toNum(a.number);
        return new Q(Math.atan(n), "atan(%s)", a.units, a.uncert, new Set(a.prefu), [a]);
    }, "atan");

    function qabs(m) {
        if (!(m instanceof Q)) m = new Q(m);
        return new Q(Math.abs(toNum(m.number)), "abs(%s)", m.units, m.uncert, new Set(m.prefu), [m]);
    }

    function qmin() {
        var args = Array.prototype.slice.call(arguments).map(function (x) { return x instanceof Q ? x : new Q(x); });
        var q = unit_mismatch(args);
        if (q) raise_QuantError("Can't compare quantities with different dimensions", "min(%s, ... %s)", [args[0], q]);
        if (args.length < 2) raise_QuantError("min take at least two arguments", "min(%s)", args);
        var best = args[0];
        for (var i = 1; i < args.length; i++) {
            if (toNum(args[i].number) < toNum(best.number)) best = args[i];
        }
        var placeholders = args.map(function () { return "%s"; }).join(", ");
        return new Q(best.number, "min(" + placeholders + ")", best.units, best.uncert, new Set(best.prefu), args);
    }

    function qmax() {
        var args = Array.prototype.slice.call(arguments).map(function (x) { return x instanceof Q ? x : new Q(x); });
        var q = unit_mismatch(args);
        if (q) raise_QuantError("Can't compare quantities with different dimensions", "max(%s, ... %s)", [args[0], q]);
        if (args.length < 2) raise_QuantError("max take at least two arguments", "max(%s)", args);
        var best = args[0];
        for (var i = 1; i < args.length; i++) {
            if (toNum(args[i].number) > toNum(best.number)) best = args[i];
        }
        var placeholders = args.map(function () { return "%s"; }).join(", ");
        return new Q(best.number, "max(" + placeholders + ")", best.units, best.uncert, new Set(best.prefu), args);
    }

    function qsum() {
        var args = Array.prototype.slice.call(arguments).map(function (x) { return x instanceof Q ? x : new Q(x); });
        var q = unit_mismatch(args);
        if (q) raise_QuantError("Can't add quantities with different dimensions", "sum(%s, ... %s)", [args[0], q]);
        var res = args[0];
        for (var i = 1; i < args.length; i++) {
            res = res.add(args[i]);
        }
        var placeholders = args.map(function () { return "%s"; }).join(", ");
        return new Q(res.number, "sum(" + placeholders + ")", res.units, res.uncert, new Set(res.prefu), args);
    }

    function qaverage() {
        var args = Array.prototype.slice.call(arguments).map(function (x) { return x instanceof Q ? x : new Q(x); });
        var q = unit_mismatch(args);
        if (q) raise_QuantError("Can't average quantities with different dimensions", "average(%s, ... %s)", [args[0], q]);
        var sumQ = qsum.apply(null, args);
        var avgQ = sumQ.div(new Q(args.length));
        var placeholders = args.map(function () { return "%s"; }).join(", ");
        var prefu = new Set(avgQ.prefu);
        if (args[0].prefu.has('°aC')) prefu.add('°aC');
        return new Q(avgQ.number, "avg(" + placeholders + ")", avgQ.units, avgQ.uncert, prefu, args);
    }

    function quad(A, B, C) {
        if (!(A instanceof Q)) A = new Q(A);
        if (!(B instanceof Q)) B = new Q(B);
        if (!(C instanceof Q)) C = new Q(C);

        var BB = B.pow(new Q(2));
        var AC4 = new Q(4).mul(A).mul(C);
        if (!BB.units.equals(AC4.units)) {
            raise_QuantError("B * B has to have the same units as 4 * A * C", "quad(%s, %s, %s)", [A, B, C]);
        }
        var discriminant = BB.sub(AC4);
        if (toNum(discriminant.number) < 0) {
            raise_QuantError("discriminant " + toNum(discriminant.number) + " is negative, can't take its root", "quad(%s, %s, %s)", [A, B, C]);
        }
        var root = qsqrt(discriminant);
        var sol_big = B.neg().add(root).div(new Q(2).mul(A));
        var sol_small = B.neg().sub(root).div(new Q(2).mul(A));
        if (toNum(B.number) > 0) {
            var temp = sol_big;
            sol_big = sol_small;
            sol_small = temp;
        }
        if (Math.abs(Math.abs(toNum(B.number)) - toNum(root.number)) < 0.000001) {
            var sol_big_temp = new Q(sol_big.number, "(quadp(%s, %s, %s))", sol_big.units, sol_big.uncert, sol_big.prefu, [A, B, C]);
            sol_small = C.div(A).div(sol_big_temp);
        }
        return [sol_big, sol_small];
    }

    function qquadp(A, B, C) { return quad(A, B, C)[0]; }
    function qquadn(A, B, C) { return quad(A, B, C)[1]; }

    function qmoredigits(a) {
        if (!(a instanceof Q)) a = new Q(a);
        return new Q(a.number, "moredigits(%s)", a.units, a.uncert / 100000.0, new Set(a.prefu), [a]);
    }

    function quncertainty(a) {
        if (!(a instanceof Q)) a = new Q(a);
        return new Q(a.uncert, "uncertainty(%s)", a.units, a.uncert / 100000.0, new Set(a.prefu), [a]);
    }

    var Kelvin = unitquant['K'];
    var Kelvinshift = new Q(273.15).mul(Kelvin);

    function qFtoKscale(a) {
        if (!(a instanceof Q)) a = new Q(a);
        if (a.units.isUnity() && !a.provenance) {
            var Kscale = a.sub(new Q(32)).mul(new Q(new Fraction(5, 9))).mul(Kelvin).add(Kelvinshift);
            Kscale.provenance = [a];
            Kscale.name = "\\mathrm{FtoKscale}(%s)";
            if (toNum(Kscale.number) < 0) {
                raise_QuantError("Input temperature is lower than absolute zero", "\\mathrm{FtoKscale}(%s)", [a]);
            }
            return Kscale;
        }
        raise_QuantError("Input temperature has to be a unit-less number", "\\mathrm{FtoKscale}(%s)", [a]);
    }

    function qCtoKscale(a) {
        if (!(a instanceof Q)) a = new Q(a);
        if (a.units.isUnity() && !a.provenance) {
            var Kscale = a.mul(Kelvin).add(Kelvinshift);
            if (toNum(Kscale.number) < 0) {
                raise_QuantError("Input temperature is lower than absolute zero", "\\mathrm{CtoKscale}(%s)", [a]);
            }
            Kscale.name = "\\mathrm{CtoKscale}(%s)";
            Kscale.provenance = [a];
            return Kscale;
        }
        raise_QuantError("Input temperature has to be a unit-less number", "\\mathrm{CtoKscale}(%s)", [a]);
    }

    var functions = {
        sin: qsin,
        cos: qcos,
        tan: qtan,
        asin: qasin,
        acos: qacos,
        atan: qatan,
        exp: qexp,
        sqrt: qsqrt,
        log: qlog,
        ln: qln,
        quadp: qquadp,
        quadn: qquadn,
        min: qmin,
        max: qmax,
        abs: qabs,
        CtoKscale: qCtoKscale,
        FtoKscale: qFtoKscale,
        moredigits: qmoredigits,
        uncertainty: quncertainty,
        avg: qaverage,
        sum: qsum
    };

    function qfunc(name) {
        var args = Array.prototype.slice.call(arguments, 1);
        if (!functions[name]) {
            throw new Error("Unknown function " + name);
        }
        return functions[name].apply(null, args);
    }

    // Symbolic placeholder X class
    function X(name, provenance) {
        if (!(this instanceof X)) return new X(name, provenance);
        this.name = name || '';
        this.provenance = provenance || null;
    }
    X.prototype.setdepth = function () {
        if (typeof this.depth === 'undefined') {
            if (!this.provenance || this.provenance.length === 0) {
                this.depth = 0;
            } else {
                var maxD = 0;
                for (var i = 0; i < this.provenance.length; i++) {
                    var cd = this.provenance[i].setdepth();
                    if (cd > maxD) maxD = cd;
                }
                this.depth = 1 + maxD;
            }
        }
        return this.depth;
    };
    X.prototype.add = function (o) { return new X('%s + %s', [this, o]); };
    X.prototype.sub = function (o) { return new X('%s - %s', [this, o]); };
    X.prototype.mul = function (o) { return new X('%s * %s', [this, o]); };
    X.prototype.div = function (o) { return new X('%s / %s', [this, o]); };
    X.prototype.neg = function () { return new X('-%s', [this]); };
    X.prototype.pow = function (o) { return new X('%s ^ %s', [this, o]); };

    return {
        SIunit_symbols: SIunit_symbols,
        Units: Units,
        unity: unity,
        QuantError: QuantError,
        raise_QuantError: raise_QuantError,
        Q: Q,
        X: X,
        opprio: opprio,
        sigfig: sigfig,
        mostsig: mostsig,
        format_uncert: format_uncert,
        exact_number: exact_number,
        ascii_number: ascii_number,
        number2quantity: number2quantity,
        latex_number: latex_number,
        latex_name: latex_name,
        ascii_units: ascii_units,
        latex_units: latex_units,
        unit_string: unit_string,
        ascii_qvalue: ascii_qvalue,
        latex_qvalue: latex_qvalue,
        ascii_writer: ascii_writer,
        latex_writer: latex_writer,
        known_units: known_units,
        metric_prefices: metric_prefices,
        unitquant: unitquant,
        functions: functions,
        qfunc: qfunc
    };
}));
