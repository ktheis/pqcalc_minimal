// js/chemistry.js - Chemical elements, molar mass calculations, equation balancing, and physical naming conventions
(function (root, factory) {
    if (typeof exports === 'object' && typeof module !== 'undefined') {
        var Quantities = require('./quantities');
        var Fraction = require('./fraction');
        module.exports = factory(Quantities, Fraction);
    } else {
        root.Chemistry = factory(root.Quantities, root.Fraction);
        // Expose symbols on root
        root.PSE = root.Chemistry.PSE;
        root.molar_mass = root.Chemistry.molar_mass;
        root.Species = root.Chemistry.Species;
        root.interpret_equation = root.Chemistry.interpret_equation;
        root.balancing_issues = root.Chemistry.balancing_issues;
        root.compare_reactions = root.Chemistry.compare_reactions;
        root.pronounce = root.Chemistry.pronounce;
        root.chemname = root.Chemistry.chemname;
        root.naming_conventions = root.Chemistry.naming_conventions;
    }
}(typeof self !== 'undefined' ? self : this, function (Quantities, Fraction) {
    'use strict';

    var Q = Quantities.Q;
    var Units = Quantities.Units;
    var unitquant = Quantities.unitquant;

    // Exact classroom periodic table (PSE) with atomic weights & uncertainties
    var PSE = {
        'H': ['1.008', 'Hydrogen'],
        'He': ['4.002602(2)', 'Helium'],
        'Li': ['6.94', 'Lithium'],
        'Be': ['9.0121831(5)', 'Beryllium'],
        'B': ['10.81', 'Boron'],
        'C': ['12.011', 'Carbon'],
        'N': ['14.007', 'Nitrogen'],
        'O': ['15.999', 'Oxygen'],
        'F': ['18.998403163(6)', 'Fluorine'],
        'Ne': ['20.1797(6)', 'Neon'],
        'Na': ['22.98976928(2)', 'Sodium'],
        'Mg': ['24.305', 'Magnesium'],
        'Al': ['26.9815385(7)', 'Aluminium'],
        'Si': ['28.085', 'Silicon'],
        'P': ['30.973761998(5)', 'Phosphorus'],
        'S': ['32.06', 'Sulfur'],
        'Cl': ['35.45', 'Chlorine'],
        'Ar': ['39.948(1)', 'Argon'],
        'K': ['39.0983(1)', 'Potassium'],
        'Ca': ['40.078(4)', 'Calcium'],
        'Sc': ['44.955908(5)', 'Scandium'],
        'Ti': ['47.867(1)', 'Titanium'],
        'V': ['50.9415(1)', 'Vanadium'],
        'Cr': ['51.9961(6)', 'Chromium'],
        'Mn': ['54.938044(3)', 'Manganese'],
        'Fe': ['55.845(2)', 'Iron'],
        'Co': ['58.933194(4)', 'Cobalt'],
        'Ni': ['58.6934(4)', 'Nickel'],
        'Cu': ['63.546(3)', 'Copper'],
        'Zn': ['65.38(2)', 'Zinc'],
        'Ga': ['69.723(1)', 'Gallium'],
        'Ge': ['72.630(8)', 'Germanium'],
        'As': ['74.921595(6)', 'Arsenic'],
        'Se': ['78.971(8)', 'Selenium'],
        'Br': ['79.904', 'Bromine'],
        'Kr': ['83.798(2)', 'Krypton'],
        'Rb': ['85.4678(3)', 'Rubidium'],
        'Sr': ['87.62(1)', 'Strontium'],
        'Y': ['88.90584(2)', 'Yttrium'],
        'Zr': ['91.224(2)', 'Zirconium'],
        'Nb': ['92.90637(2)', 'Niobium'],
        'Mo': ['95.95(1)', 'Molybdenum'],
        'Tc': ['97.', 'Technetium'],
        'Ru': ['101.07(2)', 'Ruthenium'],
        'Rh': ['102.90550(2)', 'Rhodium'],
        'Pd': ['106.42(1)', 'Palladium'],
        'Ag': ['107.8682(2)', 'Silver'],
        'Cd': ['112.414(4)', 'Cadmium'],
        'In': ['114.818(1)', 'Indium'],
        'Sn': ['118.710(7)', 'Tin'],
        'Sb': ['121.760(1)', 'Antimony'],
        'Te': ['127.60(3)', 'Tellurium'],
        'I': ['126.90447(3)', 'Iodine'],
        'Xe': ['131.293(6)', 'Xenon'],
        'Cs': ['132.90545196(6)', 'Caesium'],
        'Ba': ['137.327(7)', 'Barium'],
        'La': ['138.90547(7)', 'Lanthanum'],
        'Ce': ['140.116(1)', 'Cerium'],
        'Pr': ['140.90766(2)', 'Praseodymium'],
        'Nd': ['144.242(3)', 'Neodymium'],
        'Pm': ['145.', 'Promethium'],
        'Sm': ['150.36(2)', 'Samarium'],
        'Eu': ['151.964(1)', 'Europium'],
        'Gd': ['157.25(3)', 'Gadolinium'],
        'Tb': ['158.92535(2)', 'Terbium'],
        'Dy': ['162.500(1)', 'Dysprosium'],
        'Ho': ['164.93033(2)', 'Holmium'],
        'Er': ['167.259(3)', 'Erbium'],
        'Tm': ['168.93422(2)', 'Thulium'],
        'Yb': ['173.045(10)', 'Ytterbium'],
        'Lu': ['174.9668(1)', 'Lutetium'],
        'Hf': ['178.49(2)', 'Hafnium'],
        'Ta': ['180.94788(2)', 'Tantalum'],
        'W': ['183.84(1)', 'Tungsten'],
        'Re': ['186.207(1)', 'Rhenium'],
        'Os': ['190.23(3)', 'Osmium'],
        'Ir': ['192.217(3)', 'Iridium'],
        'Pt': ['195.084(9)', 'Platinum'],
        'Au': ['196.966569(5)', 'Gold'],
        'Hg': ['200.592(3)', 'Mercury'],
        'Tl': ['204.38', 'Thallium'],
        'Pb': ['207.2(1)', 'Lead'],
        'Bi': ['208.98040(1)', 'Bismuth'],
        'Po': ['209.', 'Polonium'],
        'At': ['210.', 'Astatine'],
        'Rn': ['222.', 'Radon'],
        'Fr': ['223.', 'Francium'],
        'Ra': ['226.', 'Radium'],
        'Ac': ['227.', 'Actinium'],
        'Th': ['232.0377(4)', 'Thorium'],
        'Pa': ['231.03588(2)', 'Protactinium'],
        'U': ['238.02891(3)', 'Uranium'],
        'Np': ['237.', 'Neptunium'],
        'Pu': ['244.', 'Plutonium'],
        'Am': ['243.', 'Americium'],
        'Cm': ['247.', 'Curium'],
        'Bk': ['247.', 'Berkelium'],
        'Cf': ['251.', 'Californium'],
        'Es': ['252.', 'Einsteinium'],
        'Fm': ['257.', 'Fermium'],
        'Md': ['258.', 'Mendelevium'],
        'No': ['259.', 'Nobelium'],
        'Lr': ['262.', 'Lawrencium'],
        'Rf': ['267.', 'Rutherfordium'],
        'Db': ['270.', 'Dubnium'],
        'Sg': ['269.', 'Seaborgium'],
        'Bh': ['270.', 'Bohrium'],
        'Hs': ['270.', 'Hassium'],
        'Mt': ['278.', 'Meitnerium'],
        'Ds': ['281.', 'Darmstadtium'],
        'Rg': ['281.', 'Roentgenium'],
        'Cn': ['285.', 'Copernicium'],
        'Nh': ['286.', 'Nihonium'],
        'Fl': ['289.', 'Flerovium'],
        'Mc': ['289.', 'Moscovium'],
        'Lv': ['293.', 'Livermorium'],
        'Ts': ['293.', 'Tennessine'],
        'Og': ['294.', 'Oganesson']
    };

    function findMatchingClosingParen(text) {
        var p = 0;
        var openCh = text[0];
        var closeCh = (openCh === '(') ? ')' : (openCh === '[' ? ']' : '}');
        for (var i = 0; i < text.length; i++) {
            if (text[i] === openCh) p++;
            else if (text[i] === closeCh) {
                p--;
                if (p === 0) return i;
            }
        }
        return -1;
    }

    // Formula chunker for molar mass calculation
    function chunks(text) {
        var tx = text;
        var result = [];
        while (tx.length > 0) {
            var e;
            if (tx.length >= 2 && tx.slice(0, 2) in PSE) {
                e = tx.slice(0, 2);
                tx = tx.slice(2);
            } else if (tx.slice(0, 1) in PSE) {
                e = tx.slice(0, 1);
                tx = tx.slice(1);
            } else if (tx[0] === '(') {
                var p = findMatchingClosingParen(tx);
                if (p === -1) throw new Error("Unclosed parenthesis in formula: " + text);
                e = tx.slice(0, p + 1);
                tx = tx.slice(p + 1);
            } else {
                throw new Error("Unknown element or symbol in formula: " + tx);
            }

            var nr = 1;
            if (tx.length > 0 && tx[0] >= '0' && tx[0] <= '9') {
                var digs = '';
                while (tx.length > 0 && tx[0] >= '0' && tx[0] <= '9') {
                    digs += tx[0];
                    tx = tx.slice(1);
                }
                nr = parseInt(digs, 10);
            }
            result.push([e, nr]);
        }
        return result;
    }

    // Calculates molar mass as a Q quantity
    function molar_mass(text) {
        var M = new Q(0.0);
        var tx = text.replace(/\(aq\)/g, '').replace(/\(s\)/g, '').replace(/\(l\)/g, '').replace(/\(g\)/g, '');
        var chList = chunks(tx);

        for (var i = 0; i < chList.length; i++) {
            var element = chList[i][0];
            var nr = chList[i][1];
            if (element.startsWith('(')) {
                var inner = element.slice(1, -1);
                M = M.add(new Q(nr).mul(molar_mass(inner)));
            } else {
                var elemWeightQ = new Q(PSE[element][0]);
                var term = new Q(nr).mul(elemWeightQ).mul(unitquant['g']).div(unitquant['mol']);
                M = M.add(term);
            }
        }
        M.provenance = null;
        M.name = 'M[' + text + ']';
        return M;
    }

    // Chunks chemical species for stoichiometry and reaction balancing
    function chunk_species(text) {
        var tx = text;
        var result = [];
        while (tx.length > 0) {
            var e;
            if (tx[0] === '(' || tx[0] === '[') {
                var p = findMatchingClosingParen(tx);
                if (p === -1) p = tx.length - 1;
                e = tx.slice(0, p + 1);
                tx = tx.slice(p + 1);
            } else {
                if (tx.length > 1 && tx[1] >= 'a' && tx[1] <= 'z') {
                    e = tx.slice(0, 2);
                    tx = tx.slice(2);
                } else {
                    e = tx.slice(0, 1);
                    tx = tx.slice(1);
                }
            }

            var nr = 1;
            if (tx.length > 0 && tx[0] >= '0' && tx[0] <= '9') {
                var digs = '';
                while (tx.length > 0 && tx[0] >= '0' && tx[0] <= '9') {
                    digs += tx[0];
                    tx = tx.slice(1);
                }
                nr = parseInt(digs, 10);
            }
            result.push([e, nr]);
        }
        return result;
    }

    function element_counter(text) {
        var c = {};
        var spList = chunk_species(text);
        for (var i = 0; i < spList.length; i++) {
            var element = spList[i][0];
            var nr = spList[i][1];
            if (element[0] === '(' || element[0] === '[') {
                var c2 = element_counter(element.slice(1, -1));
                for (var e2 in c2) {
                    c[e2] = (c[e2] || 0) + nr * c2[e2];
                }
            } else {
                c[element] = (c[element] || 0) + nr;
            }
        }
        return c;
    }

    // Species representation (elements, charge, phase)
    function Species(text) {
        if (!(this instanceof Species)) return new Species(text);
        text = text.split('!')[0].trim();
        this.text = text;
        this.phase = null;
        this.elements = {};

        var phases = ['(s)', '(l)', '(g)', '(aq)'];
        for (var i = 0; i < phases.length; i++) {
            if (text.endsWith(phases[i])) {
                this.phase = phases[i];
                text = text.slice(0, -phases[i].length).trim();
                break;
            }
        }

        var charge = 0;
        if (text.endsWith('+') || text.endsWith('-')) {
            var sign = text.endsWith('+') ? 1 : -1;
            text = text.slice(0, -1);
            if (text.indexOf('^') !== -1) {
                var parts = text.split('^');
                text = parts[0];
                charge = sign * parseInt(parts[1], 10);
            } else if (text.length > 0 && text[text.length - 1] >= '0' && text[text.length - 1] <= '9') {
                var cdigs = '';
                while (text.length > 0 && text[text.length - 1] >= '0' && text[text.length - 1] <= '9') {
                    cdigs = text[text.length - 1] + cdigs;
                    text = text.slice(0, -1);
                }
                charge = sign * parseInt(cdigs, 10);
            } else {
                charge = sign;
            }
        }

        var counted = element_counter(text);
        for (var el in counted) {
            this.elements[el] = counted[el];
        }
        if (charge !== 0) {
            this.elements['charge'] = charge;
        }
    }

    // Interprets chemical equation (e.g. "2 H2 + O2 -> 2 H2O")
    function interpret_equation(text) {
        var eq = [];
        var comment = null;
        var numbering = null;

        if (text.indexOf('!') !== -1) {
            var bangParts = text.split('!');
            text = bangParts[0];
            comment = bangParts.slice(1).join('!');
        }
        if (text.startsWith('[')) {
            var numParts = text.split(']');
            numbering = numParts[0].slice(1);
            text = numParts.slice(1).join(']');
        }

        var tokens = text.split(/(->(?:\[[^\]]+\])?|<=>(?:\[[^\]]+\])?|\s\+\s)/);
        tokens.push('');

        var sign = -1;
        for (var i = 0; i < tokens.length; i += 2) {
            var s = tokens[i].trim();
            var sep = (i + 1 < tokens.length) ? tokens[i + 1] : '';
            if (!s) continue;

            var stoich = 1;
            var name = s;
            for (var c = 0; c < s.length; c++) {
                var ch = s[c];
                if (!((ch >= '0' && ch <= '9') || ch === '.' || ch === '/')) {
                    name = s.slice(c).trim();
                    var numText = s.slice(0, c).trim();
                    if (numText.indexOf('/') !== -1) {
                        var fParts = numText.split('/');
                        stoich = new Fraction(parseInt(fParts[0], 10), parseInt(fParts[1], 10)).toNumber();
                    } else if (numText.length > 0) {
                        stoich = parseFloat(numText);
                    }
                    break;
                }
            }

            eq.push([new Species(name), stoich * sign]);

            if (sep.startsWith('->') || sep.startsWith('<=>')) {
                sign = 1;
            }
        }
        return [eq, comment, numbering];
    }

    // Checks whether an equation is balanced
    function balancing_issues(eq1) {
        var d = {};
        for (var i = 0; i < eq1.length; i++) {
            var sp = eq1[i][0];
            var coeff = eq1[i][1];
            for (var elem in sp.elements) {
                var sub = sp.elements[elem];
                d[elem] = (d[elem] || 0) + sub * coeff;
            }
        }
        var issues = [];
        for (var k in d) {
            if (Math.abs(d[k]) > 1e-9) {
                issues.push(k);
            }
        }
        return issues.length > 0 ? issues : false;
    }

    // Compares student attempt to model reaction
    function compare_reactions(req1, req2) {
        var eq1 = req1[0];
        var eq2 = req2[0];

        function speciesKey(sp) {
            var keys = Object.keys(sp.elements).sort();
            return keys.map(function (k) { return k + ':' + sp.elements[k]; }).join(',');
        }

        var set1 = {};
        var set2 = {};
        var deq1 = {};
        var deq2 = {};

        for (var i = 0; i < eq1.length; i++) {
            var k1 = speciesKey(eq1[i][0]);
            set1[k1] = true;
            deq1[k1] = eq1[i][0].text;
        }
        for (var j = 0; j < eq2.length; j++) {
            var k2 = speciesKey(eq2[j][0]);
            set2[k2] = true;
            deq2[k2] = eq2[j][0].text;
        }

        var keys1 = Object.keys(set1);
        var keys2 = Object.keys(set2);
        var sameSpecies = (keys1.length === keys2.length) && keys1.every(function (k) { return set2[k]; });

        if (sameSpecies) {
            var bal1 = balancing_issues(eq1);
            var bal2 = balancing_issues(eq2);
            if (!bal1 && bal2) {
                return [50, null, null, 'not balanced: ' + bal2.join(' and '), null];
            } else {
                var ratios = [];
                for (var r = 0; r < eq1.length; r++) {
                    var spKey = speciesKey(eq1[r][0]);
                    var match2 = null;
                    for (var m = 0; m < eq2.length; m++) {
                        if (speciesKey(eq2[m][0]) === spKey) {
                            match2 = eq2[m];
                            break;
                        }
                    }
                    if (match2) {
                        ratios.push(new Fraction(eq1[r][1], match2[1]));
                    }
                }
                var allSameRatio = ratios.length > 0 && ratios.every(function (rt) { return rt.equals(ratios[0]); });
                if (allSameRatio) {
                    if (ratios[0].toNumber() === 1) {
                        return [100, null, null, null, null];
                    } else {
                        return [90, null, null, null, 'same stoichiometry except for common factor'];
                    }
                } else {
                    return [60, null, null, null, 'trouble with stoichiometry ratios'];
                }
            }
        } else {
            var missing = keys1.filter(function (k) { return !set2[k]; }).map(function (k) { return chemname(deq1[k]); });
            var spurious = keys2.filter(function (k) { return !set1[k]; }).map(function (k) { return deq2[k]; });
            var misStr = missing.length ? 'missing: ' + missing.join(', ') : '';
            var spurStr = spurious.length ? 'spurious: ' + spurious.join(', ') : '';
            return [(misStr && spurStr) ? 20 : 30, spurStr || null, misStr || null, null, null];
        }
    }

    // Common chemical substances database
    var chemdatabase = [
        ['H2(g)', 'hydrogen gas'],
        ['H2O(g)', 'water vapor'],
        ['H2O(l)', 'liquid water'],
        ['CO2(g)', 'carbon dioxide gas'],
        ['N2(g)', 'nitrogen gas'],
        ['O2(g)', 'oxygen gas'],
        ['NO(g)', 'nitrogen oxide gas'],
        ['H2O', 'water'],
        ['H3O+(aq)', 'hydronium ion'],
        ['NH3(g)', 'ammonia gas'],
        ['SO2(g)', 'sulfur dioxide gas'],
        ['H+(aq)', 'aqueous hydrogen ion'],
        ['CO(g)', 'carbon monoxide gas'],
        ['Cl2(g)', 'chlorine gas'],
        ['Ag+(aq)', 'silver ion'],
        ['Fe(s)', 'solid iron'],
        ['HCl', 'hydrogen chloride'],
        ['NH3', 'ammonia'],
        ['NO2(g)', 'nitrogen dioxide gas'],
        ['OH-(aq)', 'hydroxide ion'],
        ['Cl-(aq)', 'chloride ion'],
        ['Cu(s)', 'elemental copper'],
        ['K+(aq)', 'potassium ion'],
        ['Na+(aq)', 'sodium ion'],
        ['NO3-(aq)', 'nitrate ion'],
        ['Mg2+(aq)', 'magnesium ion'],
        ['CaO(s)', 'calcium oxide'],
        ['CaCl2', 'calcium chloride'],
        ['CH4(g)', 'methane gas'],
        ['CH4', 'methane'],
        ['Zn(s)', 'elemental zinc'],
        ['Hg(l)', 'liquid mercury'],
        ['SO3(g)', 'sulfur trioxide gas'],
        ['PO43-', 'phosphate ion'],
        ['Ag(s)', 'elemental silver'],
        ['Ca2+(aq)', 'calcium ion'],
        ['C2H5OH', 'ethanol'],
        ['Al(s)', 'elemental aluminum'],
        ['NaOH', 'sodium hydroxide'],
        ['CO2', 'carbon dioxide'],
        ['Ca(OH)2(aq)', 'calcium hydroxide'],
        ['Fe2O3(s)', 'iron(III)oxide'],
        ['NH3(aq)', 'aqueous ammonia'],
        ['H2S', 'hydrogen sulfide'],
        ['NO2', 'nitrogen dioxide'],
        ['H3PO4', 'phosphoric acid'],
        ['Ca(OH)2', 'calcium hydroxide'],
        ['NaCl', 'sodium chloride']
    ];

    var chemdict = {};
    for (var cdIdx = 0; cdIdx < chemdatabase.length; cdIdx++) {
        chemdict[chemdatabase[cdIdx][0]] = chemdatabase[cdIdx][1];
    }

    function chemname(name) {
        if (name in PSE) return PSE[name][1].toLowerCase();
        if (name in chemdict) return chemdict[name];
        return name;
    }

    // Physical naming conventions & tooltips
    var naming_conventions = {
        'c': [[new Units({ m: -3, mol: 1 }), 'concentration', 0]],
        'E': [[new Units({ kg: 1, m: 2, s: -2 }), 'energy', 0], [new Units({ A: -1, kg: 1, m: 2, s: -3 }), 'electrical potential', 0]],
        'S': [[new Units({ kg: 1, m: 2, s: -2, mol: -1, K: -1 }), 'molar entropy', 0]],
        'H': [[new Units({ kg: 1, m: 2, s: -2, mol: -1 }), 'molar enthalpy', 0]],
        'G': [[new Units({ kg: 1, m: 2, s: -2, mol: -1 }), 'molar Gibbs energy', 0]],
        'V': [[new Units({ m: 3 }), 'volume', 0]],
        'v': [[new Units({ m: 1, s: -1 }), 'velocity', 0]],
        'm': [[new Units({ kg: 1 }), 'mass', 0]],
        'P': [[new Units({ kg: 1, m: -1, s: -2 }), 'pressure', 0]],
        'T': [[new Units({ K: 1 }), 'absolute temperature', 0]],
        't': [[new Units({ s: 1 }), 'time', 0]],
        'n': [[new Units({ mol: 1 }), 'chemical amount', 0]],
        'M': [[new Units({ kg: 1, mol: -1 }), 'molar mass', 0]],
        '[': [[new Units(), 'activity', 0]],
        'f': [[new Units(), 'fraction', 0], [new Units({ s: -1 }), 'frequency', 0]],
        'ρ': [[new Units({ kg: 1, m: -3 }), 'density', 0]],
        'ν': [[new Units(), 'stoichiometric coefficient', 0], [new Units({ s: -1 }), 'frequency', 0]],
        'λ': [[new Units({ m: 1 }), 'wavelength', 0]],
        'q': [[new Units({ kg: 1, m: 2, s: -2 }), 'heat', 0]],
        'w': [[new Units({ kg: 1, m: 2, s: -2 }), 'work', 0]],
        'K': [[new Units(), 'equilibrium constant', 0]],
        'F': [[new Units({ kg: 1, s: -2 }), 'force', 0]],
        'N': [[new Units(), 'number of particles', 0]],
        'pH': [[new Units(), 'pH', 1]],
        'pOH': [[new Units(), 'pOH', 1]],
        'R': [[new Units({ kg: 1, m: 2, s: -2, mol: -1, K: -1 }), 'universal gas constant', 2]],
        'N_A': [[new Units({ mol: -1 }), "Avogadro's constant", 2]],
        'c0': [[new Units({ m: 1, s: -1 }), 'speed of light', 2]],
        'g0': [[new Units({ m: 1, s: -2 }), 'gravitational acceleration', 2]]
    };

    var SuperSpecials = {
        'R': 'universal gas constant',
        'N_A': "Avogadro's constant",
        'c0': 'speed of light',
        'g0': 'gravitational acceleration'
    };

    var Specials = {
        'pH': 'pH',
        'pOH': 'pOH',
        'pKa': 'pKa',
        'E_red': 'reduction potential',
        'E_cell': 'cell potential',
        'ΔHf°': 'standard heat of formation',
        'P_vapor': 'vapor pressure'
    };

    function pronounce(qname, units) {
        if (!qname) return 'quantity';
        if (qname.startsWith('!')) return 'Chemical formula or equation: ' + qname.slice(1);
        if (qname.startsWith('@')) return 'Mathematical expression: ' + qname.slice(1);
        if (qname in SuperSpecials) return SuperSpecials[qname];
        if (qname in Specials) return Specials[qname];
        if (qname in naming_conventions) return naming_conventions[qname][0][1];

        if (qname.indexOf('[') !== -1) {
            var parts = qname.split('[');
            var head = parts[0];
            var inside = parts[1].split(']')[0];
            var subName = chemname(inside);
            if (head === 'M') return 'molar mass of ' + subName;
            if (head === 'c' || head === '') return 'concentration of ' + subName;
            if (head === 'n') return 'chemical amount of ' + subName;
            if (head === 'm') return 'mass of ' + subName;
            if (head === 'ν') return 'stoichiometric coefficient of ' + subName;
            return head + ' of ' + subName;
        }

        var base = qname.split('_')[0];
        if (base in naming_conventions) {
            return naming_conventions[base][0][1];
        }
        return 'quantity ' + qname;
    }

    return {
        PSE: PSE,
        chunks: chunks,
        molar_mass: molar_mass,
        chunk_species: chunk_species,
        element_counter: element_counter,
        Species: Species,
        interpret_equation: interpret_equation,
        balancing_issues: balancing_issues,
        compare_reactions: compare_reactions,
        chemdatabase: chemdatabase,
        chemdict: chemdict,
        chemname: chemname,
        naming_conventions: naming_conventions,
        pronounce: pronounce
    };
}));
