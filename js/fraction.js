// js/fraction.js - Lightweight rational number support for units and exact arithmetic
(function (root, factory) {
    if (typeof exports === 'object' && typeof module !== 'undefined') {
        module.exports = factory();
    } else {
        root.Fraction = factory();
    }
}(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    function gcd(a, b) {
        a = Math.abs(a);
        b = Math.abs(b);
        while (b) {
            var t = b;
            b = a % b;
            a = t;
        }
        return a;
    }

    function Fraction(numerator, denominator) {
        if (!(this instanceof Fraction)) {
            return new Fraction(numerator, denominator);
        }
        if (numerator instanceof Fraction) {
            this.numerator = numerator.numerator;
            this.denominator = numerator.denominator;
            return;
        }
        if (typeof denominator === 'undefined') {
            denominator = 1;
        }
        if (denominator === 0) {
            throw new RangeError("Division by zero in Fraction");
        }
        if (typeof numerator === 'number' && !Number.isInteger(numerator)) {
            // Convert float to fraction approximation
            var frac = Fraction.fromFloat(numerator);
            this.numerator = frac.numerator;
            this.denominator = frac.denominator;
            return;
        }

        var n = Math.round(numerator);
        var d = Math.round(denominator);
        if (d < 0) {
            n = -n;
            d = -d;
        }
        var g = gcd(n, d);
        this.numerator = n / g;
        this.denominator = d / g;
    }

    Fraction.prototype.add = function (other) {
        var o = other instanceof Fraction ? other : new Fraction(other);
        return new Fraction(
            this.numerator * o.denominator + o.numerator * this.denominator,
            this.denominator * o.denominator
        );
    };

    Fraction.prototype.sub = function (other) {
        var o = other instanceof Fraction ? other : new Fraction(other);
        return new Fraction(
            this.numerator * o.denominator - o.numerator * this.denominator,
            this.denominator * o.denominator
        );
    };

    Fraction.prototype.mul = function (other) {
        var o = other instanceof Fraction ? other : new Fraction(other);
        return new Fraction(
            this.numerator * o.numerator,
            this.denominator * o.denominator
        );
    };

    Fraction.prototype.div = function (other) {
        var o = other instanceof Fraction ? other : new Fraction(other);
        if (o.numerator === 0) {
            throw new RangeError("Division by zero in Fraction");
        }
        return new Fraction(
            this.numerator * o.denominator,
            this.denominator * o.numerator
        );
    };

    Fraction.prototype.equals = function (other) {
        var o = other instanceof Fraction ? other : new Fraction(other);
        return this.numerator === o.numerator && this.denominator === o.denominator;
    };

    Fraction.prototype.toNumber = function () {
        return this.numerator / this.denominator;
    };

    Fraction.prototype.valueOf = function () {
        return this.toNumber();
    };

    Fraction.prototype.toString = function () {
        if (this.denominator === 1) return '' + this.numerator;
        return '(' + this.numerator + ' / ' + this.denominator + ')';
    };

    Fraction.fromFloat = function (val, maxDenom) {
        maxDenom = maxDenom || 1000000;
        if (Number.isInteger(val)) return new Fraction(val, 1);
        var sign = val < 0 ? -1 : 1;
        val = Math.abs(val);

        // Continued fraction expansion (similar to Python Fraction(val).limit_denominator())
        var p0 = 0, q0 = 1, p1 = 1, q1 = 0;
        var a = Math.floor(val);
        var rem = val - a;

        while (true) {
            var p2 = a * p1 + p0;
            var q2 = a * q1 + q0;
            if (q2 > maxDenom) break;
            p0 = p1; q0 = q1;
            p1 = p2; q1 = q2;
            if (rem === 0 || Math.abs(val - p1 / q1) < 1e-12) break;
            val = 1 / rem;
            a = Math.floor(val);
            rem = val - a;
        }
        return new Fraction(sign * p1, q1);
    };

    return Fraction;
}));
