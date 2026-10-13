import re
from collections import defaultdict as ddict
from fractions import Fraction
from quantities import Units, Q, unitquant


def prettyeq(eq, arrow=' -> '):
    LHS = ' + '.join('%s%s' % ((str(-c) + ' ' if c != -1 else ''), s.text) for s, c in eq if c<0)
    RHS = ' + '.join('%s%s' % ((str(c) + ' ' if c != 1 else ''), s.text) for s, c in eq if c>0)
    return LHS + arrow + RHS


def matching_closing(text):
    p = 0
    open = text[0]
    close = ')' if open == '(' else ']'
    for i, c in enumerate(text):
        if c == open:
             p += 1
        if c == close:
            p -= 1
            if not p:
                return i
    return None


def chunk_species(text):
    print("chunking")
    print(text)
    tx = text[:]
    while tx:
        if tx[0] in '([':
            p = matching_closing(tx)
            e, tx = tx[:p], tx[p+1:]
        else:
            if len(tx) > 1 and tx[1].islower():
                e, tx = tx[:2], tx[2:]
            else:
                e, tx = tx[:1], tx[1:]
        if not tx or not tx[0].isdigit():
            yield e, 1
        else:
            digs = ''
            while tx and tx[0].isdigit():
                digs += tx[0]
                tx = tx[1:]
            yield e, int(digs)


def element_counter(text):
    c = ddict(int)
    for element, nr in chunk_species(text):
        if element[0] in '[(':
            c2 = element_counter(element[1:])
            for e in c2:
                c[e] += nr * c2[e]
        else:
            c[element] += nr
    return c


class Species(set):
    """
    Chemical species represented as set of (atom, coefficient) tuple.
    Species.text is the input text, and Species.phase the phase, if any.
    """
    def __init__(self, text):
        text = text.split('!')[0].strip()
        self.text = text
        for phase in '(s) (l) (g) (aq)'.split():
            if text.endswith(phase):
                self.phase = phase
                text = text[:-len(phase)]
                break
        else:
            self.phase = None
        if text[-1] in '+-':
            charge = 1 if text[-1] == '+' else -1
            text = text[:-1]
            if '^' in text:
                text, ctext = text.split('^', maxsplit=1)
                charge *= int(ctext)
            self.add(('charge', charge))
        self.update(set(element_counter(text).items()))


def interpret_equation(text):
    """
    Interpret chemical equation, extracting quantitative information
    :param text: Equation in PQcalc format (LaTeX mhchem)
    :return: list of (Species, stoichiometric factor)
    """
    try:
        eq = []
        comment = numbering = None
        if '!' in text:
            text, comment = text.split('!', maxsplit=1)
        if text[0] == '[':
            numbering, text = text.split(']', maxsplit=1)
        species = re.split(r'(->(?:\[[^]]+\])?|<=>(?:\[[^]]+\])?| \+)', text)
        species.append('')
        sign = -1
        for s, sep in zip(species[0::2], species[1::2]):
            s = s.strip()
            stoich = 1
            for i, c in enumerate(s):
                if not (c.isdigit() or c in './'):
                    name = s[i:].strip()
                    numbertext = s[:i]
                    if '/' in numbertext:
                        stoich = Fraction(numbertext)
                    elif '.' in numbertext:
                        stoich = float(numbertext)
                    elif numbertext:
                        stoich = int(numbertext)
                    break
            eq.append((Species(name), stoich * sign))
            if sep.startswith('->') or sep.startswith('<=>'):
                sign = 1
        return eq, comment, numbering
    except:
        print("returning fake equation")
        return [(Species("H2O2"), 1), (Species("H2"), -1), (Species("O2"), -1)], None, None


def balancing_issues(eq1):
    """
    Checks whether a chemical equation is balanced.
    Results are not valid if the equation contains non-elements'
    :param eq1: chemical equation, in format returned by interpret_equation()
    :return: list of elements that are not balanced
    """
    d = ddict(int)
    for sp, coeff in eq1:
        for element, subscript in sp:
            d[element] += subscript * coeff
    if any(d[a] for a in d):
        return list(a for a in d if d[a])
    return False


def compare_reactions(req1, req2):
    """
    Compares two chemical reaction equations. First compares the species irrespective
    of coefficients. If they are the same, proceeds to check whether equations are
    balanced and whether coefficients match. If species occur multiple times in equation,
    results will be invalid.
    :param eq1: the model
    :param eq2: the attempt
    :return: None
    """
    eq1, com1, num1 = req1
    eq2, com2, num2 = req2
    seq1 = {frozenset(s[0]) for s in eq1}
    seq2 = {frozenset(s[0]) for s in eq2}
    deq1 = {frozenset(s[0]):s[0].text for s in eq1}
    deq2 = {frozenset(s[0]):s[0].text for s in eq2}
    #rint('\nComparing two equations...')
    #rint('model', prettyeq(eq1))
    #rint('trial', prettyeq(eq2))
    if not seq1 ^ seq2:
        #rint('same species')
        if not balancing_issues(eq1) and balancing_issues(eq2):
            return 50, None, None, 'not balanced: ' + ' and '.join(balancing_issues(eq2)), None
        else:
            ratios = []
            for sp1, nr1 in eq1:
                for sp2, nr2 in eq2:
                    if sp2 == sp1:
                        ratios.append(Fraction(nr1,nr2))
            #rint(ratios)
            if all(r == ratios[0] for r in ratios):
                if ratios[0] == 1:
                    return 100, None, None, None, None
                else:
                    return 90, None, None, None, 'same stoichiometry except for common factor'
            else:
                tr = []
                for sp, r in zip(eq1, ratios):
                    if r != ratios[0]:
                        tr.append(deq1[frozenset(sp[0])])
                return 60, None, None, None, 'trouble with' + ' and '.join(tr)
    else:
        if seq1 - seq2:
            mis = 'missing: '+ ', '.join(chemname(deq1[s]) for s in seq1-seq2)
        else:
            mis = ''
        if seq2 - seq1:
            spur = 'spurious: '+ ', '.join(deq2[s] for s in seq2-seq1)
        else:
            spur = ''
        return 20 if mis and spur else 30, spur, mis, None, None


formulae = ddict(list) # contains formulae by chapter, with priority
quantities = ddict(list)
raw_formulae = '''
Chapter 1
<hr>
@ρ_sample = m_sample/V_sample #Definition of density
#@! Priority 2
m_sample = 5.4343 g
V_sample = 24.2 mL
ρ_sample = m_sample/V_sample
<hr>
Chapter 2
<hr>
@N_charge = N[p+] - N[e-] # protons and electrons have opposite charges
#@! Priority 2
N[p+] = 8 # e.g. oxygen atom has atomic number of 8, i.e. 8 protons
N[n^0] = 10 # there is an ion with a total of 10 electrons (2 inner and 8 valence)
N_charge = N[p+] - N[e-] # charge of this ion is negative two
<hr>
@N_mass = N[p+] + N[n^0] # mass number of an isotope depends on number of protons and neutrons
#@! Priority 5
N[p+] = 6 # e.g. carbon atom has atomic number of 6, i.e. 6 protons
N[n^0] = 7 # there is an isotope of carbon with 7 neutrons
N_mass = N[p+] + N[n^0] # mass number of this isotope is 13, i.e. 13-C isotope
<hr>
@m_element = sum(fraction_isotope m_isotope) # definition of average mass
#@! Priority 5
m[^12C] = 12 Da # mass of one atom of carbon-12 (by definition)
m[^13C] = 13.0033548378 Da # mass of one atom of carbon-13 (measured)
abundance[^12C]rel = 0.9893 # fractional abundance of the carbon-12 isotope
abundance[^13C]rel = 1 - abundance[^12C]rel # fractional abundance of the carbon-13 isotope
m_carbon = abundance[^12C]rel m[^12C] + abundance[^13C]rel m[^13C] # average mass of carbon atoms in a sample with natural (terrestial) abundance
<hr>
Chapter 3
<hr>
@N_A = N_particle / n_particle  # definition Avogadro's constant
#@! Priority 3
n[CO2] = 2.0 mol
N_A = 6.022e23 /mol
N[CO2] = N_A n[CO2]
<hr>
@n[compound] = m[compound] / M[compound] # chemical amount from mass of a pure substance
#@! Priority 1
You can use this if: you know the chemical formula of the compound
M[MgCl2] = M[MgCl2] # molar mass (one formula unit of MgCl2 contains one magnesium atom and two chloride atoms)
m[MgCl2] = 4.0 g # about a teaspoon of MgCl2
n[MgCl2] = m[MgCl2] / M[MgCl2]
<hr>
@m_molecule = M_compound / N_A # mass of a molecule
#@! Priority 5
M[CO2] = M[CO2]
N_A = 6.022e23 /mol
m[CO2]molecule = M[CO2] / N_A
<hr>
@X_element = m_element / m_compound # composition by mass
#@! Priority 4
m_element = 4.1241 g # mass of element occuring in a compound
m_compound = 56.1334 g
X_element = m_element / m_compound
<hr>
@X_element = m_element / m_compound 100％ # composition by mass in percent
#@! Priority 4
m_element = 4.1241 g # mass of element occuring in a compound
m_compound = 56.1334 g
X_element = m_element / m_compound 100％
<hr>
@molecule/formulaunit = M_molecule/M_empiricalformula = m_molecule/m_empiricalformula # empirical vs molecular formula
#@! Priority 5
M[CH2] = M[CH2] # molar mass calculated from empirical formula
M[C2H4] = M[C2H4] # molar mass measured (or calculated from molecular formula)
ratio_formulaunits_to_molecule = M[C2H4] / M[CH2]
! (A_$x$ B_$y$)_$n$ = A_$nx$ B_$yn$
<hr>
@n_solute = c_solute V_solution # chemical amount of a solute
#@! Priority 1
You can use this if: there is a solution (homogeneous mixture)
n_solute = 0.513 mol
V_solution = 0.750 L
c_solute = n_solute / V_solution
<hr>
@c1 V1 = c2 V2 # Dilution law
#@! Priority 2
You can use this if: the only thing that happened was adding solvent to a solution
c1 = 2.00 M
V1 = 5.00 mL
V2 = 50.0 mL
c2 = c1 (V1 / V2)
<hr>
@fraction_bymass = m_solute / m_solution # definition concentration as mass fraction
#@! Priority 4
m_solute = 0.741 g
m_solution  = 100. g
fraction_bymass = m_solute / m_solution
<hr>
@fraction_bymass = m_solute / m_solution 100 ％ # definition concentration as mass fraction in percent
#@! Priority 3
m_solute = 0.741 g
m_solution  = 100. g
fraction_bymass = m_solute / m_solution 100 ％
<hr>
@fraction_byvolume = V_solute / V_solution 100 ％ # definition concentration as volume fraction
#@! Priority 4
V_solute = 0.741 L
V_solution  = 100. L
fraction_byvolume = V_solute / V_solution 100 ％
<hr>
@fraction_byvolume = V_solute / V_solution # definition concentration as volume fraction in percent
#@! Priority 3
V_solute = 0.741 L
V_solution  = 100. L
fraction_byvolume = V_solute / V_solution
<hr>
@ppm = 1/1000000 # definition ppm
#@! Priority 3
<hr>
@ppb = 1.e-9 # definition ppb
#@! Priority 3
<hr>
Chapter 4
<hr>
@ n1 = ν n2 # stoichiometric ratio (shortcut)
#@! Priority 2
You can use this if: you have a balanced chemical equation describing the reaction at hand
You can use this if: n1 and n2 refer to chemical amounts that reacted
n1 = 1.73 mol
ν = 2
n2 = n1 ν
<hr>
@ n1/ν1 = n2/ν2 # chemical amounts in a chemical reaction (stoichiometry)
#@! Priority 1
You can use this if: you have a balanced chemical equation describing the reaction at hand
You can use this if: n1 and n2 refer to chemical amounts that reacted
n1 = 1.43 mol
ν1 = 2
ν2 = 3
n2 = n1/ν1 ν2
<hr>
@ n1 = ν1 n[->] # using chemical amount of reaction
#@! Priority 2
You can use this if: you already calculated n[->] (e.g. in a limiting reactant problem)
n[->] = 0.43 mol
ν1 = 2
n1 = ν1 n[->]
<hr>
@N_atoms = coeff subscript # Counting atoms in formula or chemical equation
#@! Priority 3
! 2 NH3
coeff = 2
subscript = 2
N_H = coeff subscript
<hr>
@Charge_species = sum(N_atom * Ox_atom) #Sum of oxidation number
#@! Priority 2
! SO4^2-
Ox[S] = +6
N[S] = 1
Ox[O] = -2
N[O] = 4
Charge[SO4^2-] = N[S] Ox[S] +  N[O] Ox[O]
<hr>
@ n[->] = min(n_reactant/ν_reactant, ...) # finding the limiting reactant
#@! Priority 1
You can use this if: you know the amount of all the reactants and you have a balanced chemical equation
! 2 H2 + O2 -> 2H2O
n[H2] = 3.18 mol # chemical amount of hydrogen molecules (dihydrogen)
ν[H2] = 2 # stoichiometric coefficent of hydrogen molecules
n[O2] = 0.53 mol # chemical amount of oxygen molecules (dioxygen)
ν[O2] = 1 # stoichiometric coefficent of oxygen molecules
n[->] = min(n[H2] / ν[H2], n[O2] / ν[O2]) # chemical amount of reaction
<hr>
@n_theoretical_yield = n[->] ν[product] # calculating theoretical yield (based on chemical amount)
#@! Priority 2
n[->] = 0.53 mol # maximal chemical amount of reaction
ν[H2O] = 2 # stoichiometric coefficient of water
n[H2O]theoretical = n[->] ν[H2O] # mass of product that theoretically can be obtained
<hr>
@m_theoretical_yield = n[->] ν[product] M[product] # calculating theoretical yield (by mass)
#@! Priority 2
n[->] = 0.53 mol # maximal chemical amount of reaction
ν[H2O] = 2 # stoichiometric coefficient of water
M[H2O] = M[H2O] # molar mass of water
m[H2O]theoretical = n[->] ν[H2O] M[H2O] # mass of product that theoretically can be obtained
<hr>
@yield_rel = n_actual / n_theoretical * 100％ # Calculating percent yield from amounts
#@! Priority 2
n[H2O]theoretical = 1.06 mol
n[H2O]actual = 0.95 mol
yield_rel = n[H2O]actual / n[H2O]theoretical * 100％
<hr>
@yield_rel = m_actual / m_theoretical * 100％ # Calculating percent yield from masses
#@! Priority 2
m[H2O]theoretical = 19.57 g
m[H2O]actual = 18.35 g
yield_rel = m[H2O]actual / m[H2O]theoretical * 100％
<hr>
Chapter 5
<hr>
@ q = c_p_sample m_sample ΔT  # heat from temperature change
#@! Priority 4
c_P[H2O] = 4.104 J / (g K)
m[H2O] = 451. g
ΔT = 3.15 K
q = c_P[H2O] m[H2O] ΔT
<hr>
@ q =  c_p_sample m_sample (T_final - T_initial) # heat from temperature change 2
#@! Priority 4
c_P[H2O] = 4.104 J / (g K)
m[H2O] = 451.g
T_final = 298.15 K
T_initial = 273.15 K
q = c_P[H2O] m[H2O] (T_final - T_initial)
<hr>
@ ΔU = q + w # First law of thermodynamics
#@! Priority 3
q_black_box = 2.43 kJ
w_black_box = -5.15 kJ
ΔU_black_box = q_black_box + w_black_box
<hr>
@ ΔH_reaction = sum(n_prod ΔH_f_prod) - sum(n_react ΔH_f_react) # Enthalpy from heats of formation
#@! Priority 3
!3NO2(g) +H2O(l) -> 2HNO3(aq) +NO(g)
ΔHf°[HNO3(aq)] = -207.4kJ/mol
ΔHf°[NO(g)] = 90.2 kJ/mol
ΔHf°[NO2(g)] = 33.2 kJ/mol
ΔHf°[H2O(l)] = -285.8kJ/mol
ν[HNO3(aq)] = 2
ν[NO(g)] = 1
ν[NO2(g)] = 3
ν[H2O(l)] = 1
ΔH°_rxn = sum(ΔHf°[HNO3(aq)] ν[HNO3(aq)], ΔHf°[NO(g)] ν[NO(g)]) - sum(ν[NO2(g)] ΔHf°[NO2(g)], ν[H2O(l)]  ΔHf°[H2O(l)])
<hr>
Chapter 6
<hr>
@c0 = λ ν # Relationship of wavelength and frequency of light
#@! Priority 4
λ[Na] = 589. nm
c0 = 2.998e8 m/s
ν[Na] = c0 / λ[Na]
<hr>
@E_photon = h_Planck ν # Photon: Energy vs frequency
#@! Priority 3
ν_neon = 4.684e14 /s
h_Planck = 6.626e-34 J s
E_photon = h_Planck ν_neon
<hr>
@E_photon = h_Planck λ / c0 # Photon: Energy vs wavelength
#@! Priority 5
λ[Na] = 589. nm
c0 = 2.998e8 m/s
h_Planck = 6.626e-34 J s
E_photon = h_Planck c0 / λ[Na]
<hr>
@ 1/λ = R_∞ (1/n1^2 - 1/n2^2) # wave number of light associated with bound electron changing state
#@! Priority 4
n1 = 1 # low energy quantum state
n2 = 3 # high energy quantum state
R_∞ = 1.0973731534e7 /m # Rydberg constant of wave number
λ = 1 / (R_∞ (1/n1^2 - 1/n2^2)) # wave length
<hr>
@E_n = -k Z^2/n^2 # energy of bound electron
#@! Priority 5
k = 2.179e-18 J
Z = 1 # charge of nucleus
n = 3 # principal quantum number
E_n = -k Z^2/n^2
<hr>
@ΔE = k Z^2 (1/n1^2 - 1/n2^2) # change of energy of bound electron
#@! Priority 4
k = 2.179e-18 J
Z = 1 # charge of nucleus
n1 = 1 # initial quantum number
n2 = 4 # final quantum number
ΔE = k Z^2 (1/n1^2 - 1/n2^2)
<hr>
@λ_deBroglie = h_Planck / (m_particle v_particle) # deBroglie wavelength of particles
#@! Priority 5
h_Planck = 6.626e-34 J s
m_particle = 5.0 g
v_particle = 104. m/s
λ_deBroglie = h_Planck / (m_particle v_particle)
<hr>
Chapter 7
<hr>
@charge_formal = ⋕e_outer_freeatom - ⋕e_lonepairs - 1/2 ⋕e_bonding # Definition of formal charge
#@! Priority 3
For the carbon in carbondioxide with the following Lewis structure
!O=C=O
⋕e_outer_freeatom = 4
⋕e_lonepairs = 0
⋕e_bonding = 8
charge_formal = ⋕e_outer_freeatom - ⋕e_lonepairs - 1/2 ⋕e_bonding
<hr>
@D[X-Y] = ΔH_bonddissociation # Definition of bond energy
#@! Priority 3
! XY(g) -> X(g) + Y(g) !ΔH_bonddissociation = 331.2 kJ/mol
ΔH_bonddissociation = 331.2 kJ/mol
D[X-Y] = ΔH_bonddissociation
<hr>
@ΔH_reaction_estimate = sum(D_bonds_broken) - sum(D_bonds_formed) # Estimating reaction enthalpy from bond energies
#@! Priority 5
! 2H2 + O2 -> 2H2O
D[H-H] = 436. kJ/mol
D[O=O] = 498. kJ/mol
D[O-H] = 464. kJ/mol
ΔH_reaction_estimate = 2 D[H-H] + D[O=O] - 4 D[O-H]
<hr>
@ΔH_lattice = C_ ((Z⁺))((Z⁻))/ R0 # lattice energy
#@! Priority 5
describes the reaction
!MX(s) -> M^{n+}(g) + X^{n-}(g)
<hr>
Chapter 8:
<hr>
@order_bond = (⋕e_bonding - ⋕e_antibonding)/2 # definition bond order
#@! Priority 3
⋕e[O2]_bonding = 6
⋕e[O2]_antibonding = 2
order_bond[O2] = (⋕e[O2]_bonding - ⋕e[O2]_antibonding)/2
<hr>
Chapter 9:
<hr>
@P = F/A_ # Definition of pressure
#@! Priority 5
A_ = 1.0 cm^2
F = 0.32 N
P = F/A_
<hr>
@P_hydrostatic = h_ ρ_fluid g0 # Hydrostatic pressure
#@! Priority 5
g0 = 9.81 m/s^2
ρ_fluid = 0.998 g/mL
h_ = 10.0 m
P_hydrostatic = h_ ρ_fluid g0 + 0 atm
<hr>
@P V_gas = n R T # chemical amount of a pure gas (ideal gas law)
#@! Priority 1
You can use this if: the sample is a gas (and the pressure is low and the temperature high)
R = 8.314 J/(mol K)
n = 0.53 mol
T = 298.15 K
P = 1.00 atm
V_gas = n R T / P
<hr>
@P_component V_gas = n_component R T # chemical amount of a gas component
#@! Priority 2
You can use this if: the sample is a gas mixture such as air
R = 8.314 J/(mol K)
T = 298.15 K # room temperature
P[O2] = 0.19 atm # partial pressure of oxygen at sea level
V_gas = 25.0 L #
n[O2] = P[O2] V_gas / (R T)
<hr>
@P_total = sum(P_partial) # Additivity of partial pressure
#@! Priority 3
P[N2] = 4.7 atm # partial pressure of dinitrogen
P[O2] = 1.3 atm # partial pressure of dioxygen
P_total = P[N2] + P[O2]
<hr>
@X_A = n_A / n_total # definition of mole fraction
#@! Priority 3
n[N2] = 4.0 mol
n_total = 5.0 mol
X[N2] = n[N2] / n_total
<hr>
@P_A = X_a P_total # partial pressure from mole fraction
#@! Priority 4
P_total = 1.0 atm
X[N2] = 0.79
P[N2] = X[N2] P_total
<hr>
@rate_diffusion = n_gas_area / Δt # definition of rate of diffusion
#@! Priority 5
Δt = 1.0 min
n_gas = 2.3 mol
rate_diffusion = n_gas / Δt
<hr>
@rate_effusion_A / rate_effusion_B = sqrt(m_B / m_A) = sqrt(M_B / M_A) # molar mass dependence of rate of effusion
#@! Priority 5
rate_effusion[N2] = 3.9 mol/min
M[N2] = M[N2]
M[He] = M[He]
rate_effusion[He]  = sqrt(M[N2] / M[He]) rate_effusion[N2]
<hr>
@u_rms = sqrt((u1^2 + u2^2 + u3^2 + u4^2 ...)/n) # definition of rms particle speed
#@! Priority 5
<hr>
@E_kin_avg = 3/2 R T # average molar kinetic energy of particle at given temperature
#@! Priority 3
R = 8.314 J/(mol K)
T = 298.15 K
E_kin_avg = 3/2 R T
<hr>
@u_rms = sqrt(2 E_kin_avg N_A / m_particle) = sqrt(3 R T / M_particle) # velocity of gas particle
#@! Priority 5
M[N2] = M[N2]
R = 8.314 J/(mol K)
T = 298.15 K
u_rms = sqrt(3 R T / M[N2])
<hr>
@Z = V_molar_measured/V_molar_ideal = P V_molar_measured / (R T) # non-ideality of gas
#@! Priority 5
<hr>
@(P + n^2 a /V_gas^2) (V_gas - n b) = n R T # non-ideal gas law
#@! Priority 5

<hr>
Chapter 10:
<hr>
@h_liq = 2 T_surface cos(θ) / (r_tube ρ_liq g0) # surface tension
#@! Priority 5
h_liq = 2.0 mm
θ = 0.02
r_tube = 3.00 mm
ρ_liq = 0.988 g/mL
g0 = 9.81 m/s^2
T_surface = h_liq r_tube ρ_liq g0 / (2 cos(θ))
<hr>
@P_vapor = A_ exp(-ΔH_vap /(R T)) # temperature dependence of vapor pressure
#@! Priority 4
R = 8.314 J/(mol K)
T = 298.15 K
A_ = 0.152 atm
ΔH_vap = 3.24 kJ/mol
P_vapor = A_ exp(-ΔH_vap /(R T))
<hr>
@ln(P_vapor) = -ΔH_vap /(R T) + ln(A_) # temperature dependence of vapor pressure (log)
#@! Priority 5
R = 8.314 J/(mol K)
T = 298.15 K
A_ = 0.152 atm
ΔH_vap = 3.24 kJ/mol
P_vapor = A_ exp(-ΔH_vap /(R T))
<hr>
@ln(P_vapor_2 / P_vapor_1) = -ΔH_vap /R (1/T1 - 1/T2) # temperature dependence of vapor pressure (two point)
#@! Priority 4
<hr>
@n λ = 2d_ sin(θ) # Braggs law
#@! Priority 5
θ = 0.01
d_ = 1.00e-10 m
λ = 2d_ sin(θ)
<hr>
Chapter 11:
<hr>
@C_g = k P_g # dunno
#@! Priority 5
<hr>
@P_A = X_A P°_A # Raoult's law
#@! Priority 4
X_A = 0.20
P°_A = 0.142 atm
P_A = X_A P°_A
<hr>
@P_vapor_solution = sum(P_vapor_i) = sum(X_i P°_i) # additivity of vapor pressure
#@! Priority 5
X_EtOH = 0.20
X_MeOH = 0.80
P°_EtOH = 0.3 atm
P°_MeOH = 0.4 atm
P_vapor_solution = X_EtOH P°_EtOH + X_MeOH P°_MeOH
<hr>
@P_vapor_solution = X_solvent P°_solvent # solvent vapor pressure
#@! Priority 5
X_solvent = 0.954
P°_solvent = 0.1342 atm
P_vapor_solution = X_solvent P°_solvent
<hr>
@ΔT_boil_solution = K_boil b_solute # boiling point elevation
#@! Priority 4
ΔT_boil_solution = 0.412 K
b_solute = 0.31 mol/kg
K_boil = ΔT_boil_solution / b_solute
<hr>
@ΔT_freeze_solution = K_freeze b_solute # freezing point depression
#@! Priority 4
ΔT_freeze_solution = 0.612 K
b_solute = 0.31 mol/kg
K_freeze = ΔT_freeze_solution / b_solute
<hr>
@Π_solution = c_solute R T # osmotic pressure
#@! Priority 5
R = 8.314 J/(mol K)
T = 298.15 K
c_solute = 24.3 mM
Π_solution = c_solute R T
<hr>
Chapter 12:
<hr>
@ Δc1 = ν Δc2 # stoichiometric ratio of concentration changes
#@! Priority 2
You can use this: if both species are in the same solution (e.g. homogeneous equilibrium)
Δc1 = 1.73 M
ν = 2
Δc2 = Δc1 ν
<hr>
@ Δc_1/ν1 = Δc_2/ν2 # stoichiometric ratio of concentration changes
#@! Priority 1
You can use this: if both species are in the same solution (e.g. homogeneous equilibrium)
Δc_1 = 1.43 mol
ν1 = 2
ν2 = 3
Δc_2 = (ν2 / ν1) Δc_1
<hr>
@rate = -(1/a) (Δc[A]/Δt) = (1/b) (Δc[B]/Δt) #Definition of reaction rate
#@! Priority 4
!2 NO2 -> 1 N2O4
ν[NO2] = 2
ν[N2O4] = 1
Δc[NO2] = -0.34 mM
Δt = 1s
Δc[N2O4] = -ν[N2O4]/ν[NO2] Δc[NO2]
<hr>
@rate = k c[A]^m_ c[B]^n ... # Definition of rate constant (not in book)
#@! Priority 4
m_ = 1
n = 0
c[A] = 0.423 M
c[B] = 1.02 M
k = 1.42 /(M s)
rate = k c[A]^m_ c[B]^n
<hr>
@[A] = -k_zero t + [A]0 # Zero order integrated rate law
#@! Priority 4
[A]0 = 5.4 mM
t = 1.0 s
k_zero = 0.45 mM / s
[A] = -k_zero t + [A]0
<hr>
@t_½ = [A]0 / (2 k_zero) # half life zero order reaction
#@! Priority 5
[A]0 = 5.4 mM
k_zero = 0.45 mM / s
t_½ = [A]0 / (2 k_zero)
<hr>
@[A] = [A]0 exp(- k_first t) # First order integrated rate law
#@! Priority 3
[A]0 = 5.4 mM
t = 1.0 s
k_first = 0.45 / s
[A] = [A]0 exp(- k_first t)
<hr>
@ln([A]/[A]0) = - k_first t # First order integrated rate law (ln)
#@! Priority 4
[A]0 = 5.4 mM
t = 1.0 s
k_first = 0.45 / s
[A] = [A]0 exp(- k_first t)
<hr>
@t_½ = 0.693/k_first # half life first order reaction
#@! Priority 5
k_first = 0.45 / s
t_½ = 0.693/k_first
<hr>
@1/[A] = k_second t + 1/[A]0 # second order integrated rate law
#@! Priority 5
k_second = 0.102 /(M s)
t = 1.0 s
[A]0 = 5.4 mM
[A] = 1 / (k_second t + 1/[A]0)
<hr>
@t_½ = 1 / ([A]0 k_second) # half life second order reaction
#@! Priority 5
k_second = 0.102 /(M s)
[A]0 = 5.4 mM
t_½ = 1 / ([A]0 k_second)
<hr>
@k = A_ exp(- E_a / (R T)) # Arrhenius equation
#@! Priority 4
E_a = 51.3 kJ/mol
R = 8.314 J/(mol K)
T = 298.15 K
A_ = 4.5e9 /(s M)
k = A_ exp(- E_a / (R T))
<hr>
@ln(k1 / k2) = E_a/R (1/T2 - 1/T1) #Arrhenius equation, two point
#@! Priority 3
R = 8.314 J/(mol K)
T1 = 298.15 K
k1 = 3.11 /s
T2 = 308.15 K
k2 = 6.11 /s
E_a = ln(k1 / k2) R / (1/T2 - 1/T1)
<hr>
Chapter 13:
<hr>
@[solute] = c[solute] / c°[solute] # thermodynamic concentration of solutes (~ activity)
#@! Priority 1
You can use this if: you want to do equilibrium (e.g. pH) calculations
c[solute] = 0.251 M
c°[solute] =  1 M  # standard concentration for solutes
[solute] = c[solute] / c°[solute]
<hr>
@[pure] = 1 # thermodynamic concentration of pure substances
#@! Priority 3
[pure] = 1
<hr>
@K_c = [C]^ν[C] [D]^ν[D] ... /([A]^ν[A] [B]^ν[B] ...) #Definition of equilibrium constant based on [solute]
#@! Priority 1
You can use this: if you have a balanced chemical equation of the reaction at hand
!H3PO4(aq) + 3 H2O(l) <=> 3 H3O+(aq) + PO4^3-(aq)
[H3PO4(aq)]eq = 0.50
ν[H3PO4(aq)] = 1
[H2O(l)]eq = 1
ν[H2O(l)] = 3
[H3O+]eq = 0.5e-5
ν[H3O+] = 3
[PO4^3-]eq = 0.70
ν[PO4^3-] = 1
Q =  [H3O+]^ν[H3O+] [PO4^3-]^ν[PO4^3-] /([H3PO4(aq)]^ν[H3PO4(aq)] [H2O(l)]^ν[H2O(l)] )
<hr>
@Q_c = [C]^ν[C] [D]^ν[D] ... /([A]^ν[A] [B]^ν[B] ...) #Definition of reaction quotient based on [solute]
#@! Priority 2
You can use this: if you have a balanced chemical equation of the reaction at hand
!H3PO4(aq) + 3 H2O(l) <=> 3 H3O+(aq) + PO4^3-(aq)
[H3PO4(aq)] = 0.50
ν[H3PO4(aq)] = 1
[H2O(l)] = 1
ν[H2O(l)] = 3
[H3O+] = 0.5e-5
ν[H3O+] = 3
[PO4^3-] = 0.70
ν[PO4^3-] = 1
Q =  [H3O+]^ν[H3O+] [PO4^3-]^ν[PO4^3-] /([H3PO4(aq)]^ν[H3PO4(aq)] [H2O(l)]^ν[H2O(l)] )
<hr>
@Q_P = P[C]^x P[D]^y /(P[A]^m_ P[B]^n) #Definition of reaction quotient based on partial pressures
#@! Priority 4
P[A] = 0.50 atm
m_ = 1
P[B] = 0.30 atm
n = 2
P[C] = 0.15 atm
x = 2
P[D] = 0.55 atm
y = 1
Q_P = P[C]^x P[D]^y /(P[A]^m_ P[B]^n)
<hr>
@P_gas = c R T #converting pressure to concentration
#@! Priority 5
R = 8.314 J/(mol K)
T = 298.15 K
c = 45.3 mM
P_gas = c R T
<hr>
@K_P = K_c (R T)^Δ⋕species #converting K_P to K_c
#@! Priority 5
R = 8.314 J/(mol K)
T = 298.15 K
K_c = 104.1
Δ⋕species = 2
K_P = K_c (R T)^Δ⋕species
<hr>
Chapter 14:
<hr>
@K_w_25°C = [H3O+][OH-] = 1.0e-14 # equilibrium constant for the auto-dissociation of water
#@! Priority 1
You can use this: if the system is at room temperature
K_w_25°C = 1.0e-14
[H3O+] = 1.e-7
[OH-] = K_w_25°C / [H3O+]
<hr>
@pH = -log([H3O+]) #definition of pH
#@! Priority 1
[H3O+] = 1.0e-7
pH = -log([H3O+])
<hr>
@pOH = -log([OH-]) #definition of pOH
#@! Priority 4
[OH-] = 1.e-7
pOH = -log([OH-])
<hr>
@[H3O+] = 10^-pH #[H+] from pH
#@! Priority 1
pH = 7.0
[H3O+] = 10^-pH
<hr>
@[OH-] = 10^-pOH #[OH-] from pOH
#@! Priority 4
pOH = 7.0
[OH-] = 10^-pOH
<hr>
@pH + pOH = pK_w_25°C = 14.00 # Sum of pH and pOH
#@! Priority 4
pK_w_25°C = 14.00
pH = 5.0
pOH = pK_w_25°C - pH
<hr>
@K_a = [H3O+][A-]/[HA] # Definition of acid dissociation constant
#@! Priority 2
[H3O+] = 1.5e-5
[A-] = 1.5e-5
[HA] = 3.5e-5
K_a = [H3O+][A-]/[HA]
<hr>
@K_b = [HB+][OH-]/[B] # Definition of base "dissociation" constant
#@! Priority 4
[HB+] = 1.5e-5
[OH-] = 1.5e-5
[B] = 3.5e-5
K_b = [HB+][OH-]/[B]
<hr>
@ionized_rel = [H3O+]eq/[HA]0 100％ # Definition of degree of ionization
#@! Priority 5
[H3O+]eq = 1.5e-5
[HA]0 = 2.0e-4
[H3O+]eq/[HA]0 100％
<hr>
@pK_a = -log(K_a) # Definition of pK_a
#@! Priority 2
K_a = 5.2e-9
pK_a = -log(K_a)
<hr>
@pK_b = -log(K_b)# Definition of pK_b
#@! Priority 4
K_b = 2.2e-6
pK_b = -log(K_b)
<hr>
@pH = pK_a + log([A-]/[HA]) #Buffer equation (Henderson Hasselbalch)
#@! Priority 3
pK_a = 8.75
[A-] = 3.0mM
[HA] = 30. mM
pH = pK_a + log([A-]/[HA])
<hr>
Chapter 15:
<hr>
@K_sp = [M^{m+}]^p [X^{n-}]^q # definition solubility product
#@! Priority 5
!M_{P}X_{Q}(s) <=> pM^{m+}(aq) + qX^{n-}(aq)
<hr>
Chapter 16:
#@! 5
<hr>
@ΔS = q_rev / T #Definition of entropy (macroscopic, classical thermodynamics)
#@! Priority 4
T = 298.15 K
q_rev = -45.3 kJ
ΔS = q_rev / T
<hr>
@S = k ln(W_) # Definition of entropy (microscopic, statistical thermodynamics)
#@! Priority 4
k = 1.38064852e-23 J/K
W_ = 1e34
S = k ln(W_)
<hr>
@ΔS = k ln(W_final/W_initial) # Definition of entropy (microscopic, statistical thermodynamics), two point
#@! Priority 5
k = 1.38064852e-23 J/K
W_final = 1e34
W_initial = 1e25
ΔS = k ln(W_final/W_initial)
<hr>
@ΔS° = ΔS°_298 = sum(ν_prod S°_298_prod) - sum(ν_react S°_298_react) # Entropy of formation
#@! Priority 2
! N2O4 -> 2 NO2
S°[NO2] = 34.5 J/(mol K)
ν[NO2] = 2
S°[N2O4] = 64.5 J/(mol K)
ν[NO2] = 1
ΔS° = S°[NO2] ν[NO2] - S°[N2O4] ν[NO2]
<hr>
@ΔS_univ = ΔS_sys + ΔS_surr = ΔS_sys + q_surr/T # Second law of thermodynamics elaborated
#@! Priority 4
ΔS_sys = 45.2 J/(mol K)
ΔS_surr = -65.3 J/(mol K)
ΔS_univ = ΔS_sys + ΔS_surr
<hr>
@ΔG = ΔH - T ΔS # Definition of Gibbs free energy (written for constant temperature)
#@! Priority 4
ΔH = -52.4 kJ/mol
T = 298.15 K
ΔS = 12.1 J/(mol K)
ΔG = ΔH - T ΔS
<hr>
@ΔG = ΔG° + R T ln(Q) # concentration dependence of Gibbs free energy
#@! Priority 3
ΔG° = 13.1 kJ/mol
R = 8.314 J/(mol K)
T = 298.15 K
Q = 1.75e-40
ΔG = ΔG° + R T ln(Q)
<hr>
@ΔG° = - R T ln(K_eq) # Gibbs energy from equilibrium constant
#@! Priority 2
K_eq = 4.2e17
R = 8.314 J/(mol K)
T = 298.15 K
ΔG° = - R T ln(K_eq)
<hr>
@ΔᵣG° =  sum(ν_prod ΔGf°_prod) - sum(ν_react ΔGf°_react) # Gibbs energy from ΔGf°
#@! Priority 2
! N2O4 -> 2 NO2
ΔGf°[NO2] = 51.30 kJ/mol
ν[NO2] = 2
ΔGf°[N2O4] = 99.8 kJ/mol
ν[NO2] = 1
ΔᵣG° = ΔGf°[NO2] ν[NO2] - ΔGf°[N2O4] ν[NO2]
<hr>
Chapter 17:
<hr>
@E°_cell = E°_cathode - E°_anode # Standard cell potential from half cell potentials
#@! Priority 4
E°_cathode = 1.34 V
E°_anode = 0.98 V
E°_cell = E°_cathode - E°_anode
<hr>
@E°_cell = R T/(z F) ln(K_) # Standard cell potential from equilibrium constant
#@! Priority 4
K_eq = 4.2e17
R = 8.314 J/(mol K)
T = 298.15 K
F = 96485.3329 s A / mol
z = 2
E°_cell = R T/(z F) ln(K_eq)
<hr>
@E°_cell_298 = 0.0257 V/z ln(K_) = 0.0592 V/z log(K_) # Standard cell potential from equilibrium constant, room temp version
#@! Priority 5
z = 2
K_eq = 4.2e17
E°_cell_298 = 0.0592 V/z log(K_eq)
<hr>
@E_cell = E°_cell - R T/(z F) ln(Q) # Nernst equation
#@! Priority 4
Q = 152.3 # empty battery, mostly products
R = 8.314 J/(mol K)
T = 298.15 K
F = 96485.3329 s A / mol
z = 2
E°_cell =  1.32 V
E_cell = E°_cell - R T/(z F) ln(Q)
<hr>
@E_cell_298 = E°_cell -  0.0257 V/z ln(Q) = E°_cell -  0.0592 V/z log(Q) # Nernst equation, room temp
#@! Priority 5
Q = 152.3
E°_cell =  1.32 V
z = 2
E_cell_298 = E°_cell -  0.0592 V/z log(Q)
<hr>
@ΔG = -z F E_cell #Gibbs free energy from cell potential
#@! Priority 4
F = 96485.3329 s A / mol
z = 2
E_cell =  1.32 V
ΔG = -z F E_cell
<hr>
@ΔG° = -z F E°_cell # Standard Gibbs free energy from standard cell potential
#@! Priority 3
F = 96485.3329 s A / mol
z = 2
E°_cell =  1.32 V
ΔG° = -z F E°_cell
<hr>
@w_ele = w_max = -n F E_cell # Relationship between maximal work and cell potential
#@! Priority 4
F = 96485.3329 s A / mol
n = 2.0 mol
E_cell =  1.32 V
w_ele = -n F E_cell
<hr>
@Q = I t = n F # Charge vs electrical current vs amount of electrons
#@! Priority 5
n = 2.0 mol
F = 96485.3329 s A / mol
Q = n F
Chapter 18: representative elements main group

Chapter 19: transition metals

Chapter 20: orgo

<hr>
Chapter 21:
<hr>
@E = m0 c0^2 # Einstein's mass vs energy
#@! Priority 5
m_electron = 9.109e-31 kg
c0 = 2.998e8 m/s
E_electron = m_electron c0^2
<hr>
@rate_decay = λ N_ # definition of decay rate
#@! Priority 4
N_ = 3.5e12
λ = 2.3e13 / s
rate_decay = λ N_
<hr>
@t_½ = ln(2)/λ = 0.693/λ # half life of radioactive decay
#@! Priority 4
λ = 2.3e13 / s
t_½ = ln(2)/λ
<hr>
@rem = RBE rad # definition of rem
#@! Priority 5
<hr>
@Sv = RBE Gy # definition of sievert
#@! Priority 5
'''


def prep_formulae():
    for ch in raw_formulae.split('\nChapter ')[1:]:
        try:
            chnr = int(ch.split('\n')[0].split(':')[0])
        except:
            chnr = 1
        #rint('Chapter', chnr)
        for form in ch.split('<hr>')[1:]:
            if form:
                formu = form.splitlines()
                formuheader = formu[1]
                formubody = '\n'.join(formu[3:])
                #rint('Formula', formuheader)
                p = int(formu[2][13])
                #rint('  Priority', p)
                formulae[chnr].append((formuheader, p, formubody))


def show_formulae(chapter, cutoff = 3):
    out = []
    out.append('<h3>New from this chapter</h3>')
    collection = ddict(list)
    for ID, formula in enumerate(formulae[chapter]):
        collection[formula[1]].append((formula[0], ID))
    for priority in range(1,5+1):
        for f in collection[priority]:
            if not '#' in f[0]:
                math, descr = f[0], 'unnamed'
            else:
                math, descr = f[0].split('#', maxsplit=1)
            out.append('%s@<a href="formulae%d.%d">%s</a>' % (math, chapter, f[1], descr))
    collection = ddict(list)
    for chap in range(1,chapter):
        for ID, f in enumerate(formulae[chap]):
            if f[1] <= cutoff:
                collection[f[1]].append((f[0], chap, ID))
    out.append('<h3>From previous chapters</h3>' )
    for priority in range(1,cutoff+1):
        out.append('<h4>%s</h4>' % assessment[priority])
        for f in collection[priority]:
            math, descr = f[0].split('#', maxsplit=1)
            if priority == 1:
                out.append('<a href="formulae%d.%d">%s</a>' % (f[1], f[2], descr))
            else:
                out.append('%s@<a href="formulae%d.%d">%s</a>' % (math, f[1], f[2], descr))
    return '\n'.join(out)


def formula_details(chapter, ID):
    out = formulae[int(chapter)][int(ID)]
    form, descr = out[0].split('#', maxsplit=1)
    title = '<h3>Formula from Chapter %d:%s</h3>\n' % (int(chapter), descr)
    return title + form + '\n' + out[2]


quant_table = \
[['1', 'mass', 'm', 'gram', 'g', 'extensive', 'mass (basic unit)', '1', ''],
 ['1', 'volume', 'V', 'milliliter', 'mL', 'extensive', 'length ^ 3', '1', ''],
 ['1', 'length', 's', 'meter', 'm', '', 'length (basic unit)', '3', ''],
 ['1', 'density', 'ρ', 'gram per milliliter', 'g/mL', '', 'mass / volume', '2', 'm_sample / V_sample'],
 ['1', 'temperature', 'T', 'kelvin', 'K', '', 'temperature (basic unit)', '1', ''],
 ['2', 'particle number', 'N', 'unitless', '', '', 'dimensionless', '2', ''],
 ['3', 'chemical amount', 'n', 'mole', 'mol', 'extensive', 'chemical amount (basic unit)', '1', ''],
 ['3', 'concentration', 'c', 'molar = mole per liter', 'M = mol/L', '', 'chemical amount / volume', '1', 'n_solute / V_solution'],
 ['3', 'molar mass', 'M', 'gram per mole', 'g/mol', '', 'mass / chemical amount', '1', 'm_sample / n_sample'],
 ['4', 'stoichiometric coefficient', 'ν', 'unitless', '', '', 'dimensionless', '1', ''],
 ['5', 'heat', 'q', 'joule', 'J', 'extensive', 'energy = mass * length / time^2', '3', ''],
 ['5', 'molar enthalpy', 'H', 'joule per mole', 'J/mol', '', 'energy / chemical amount', '3', ''],
 ['5', 'specific heat capacity', 'c_p', 'unitless', '', '', 'energy / (mass temperature)', '4', 'q / (m_sample ΔT)'],
 ['5', 'heat capacity', 'C', 'joule per kelvin', 'J/K', '', 'energy / temperature', '5', 'q / ΔT'],
 ['6', 'frequency', 'ν', 'hertz', 'Hz = 1/s', '', '1 / time', '3', ''],
 ['6', 'wavelength', 'λ', 'nanometer', 'nm', '', 'length', '2', ''],
 ['6', 'time', 't', 'seconds', 's', '', 'time (basic unit)', '1', ''],
 ['9', 'force', 'F', 'newton', 'N = kg m/s^2', '', 'mass / time^2', '4', ''],
 ['9', 'pressure', 'P', 'atmospheres', 'atm', '', 'force / length^2 = energy / volume', '1', ''],
 ['12', 'reaction rate', 'r', 'molar per second', 'M / s', '', 'chemical amount / (volume time)', '3', 'Δc / Δt'],
 ['12', 'first order rate constant', 'k', 'per second', '1 /s', '', '1/ time', '3', ''],
 ['12', 'second order rate constant', 'k', 'per molar second', '1 / (M s)', '', 'volume / (time * chemical amount)', '3', ''],
 ['12', 'zero order rate constant', 'k', 'molar per second', 'M / s', '', 'chemical amount / (volume * time)', '3', ''],
 ['12', 'half life', 't_½', 'second', '1 / s', '', 'time', '3', ''],
 ['13', 'reaction quotient', 'Q', 'unitless', '', '', 'dimensionless', '2', ''],
 ['13', 'equilibrium constant', 'K', 'unitless', '', '', 'dimensionless', '1', ''],
 ['13', 'pH', 'pH', 'unitless', '', '', 'dimensionless', '1', '-log([H+])'],
 ['16', 'molar entropy', 'S', 'joule per mole kelvin', 'J / (mol K)', '', 'energy / (temperature * chemical amount)', '2', ''],
 ['16', 'molar Gibbs energy', 'G', 'kilojoule per mole', 'J / mol', '', 'energy / chemical amount', '2', ''],
 ['16', 'entropy', 'S', 'joule per kelvin', 'J / K', 'extensive', 'energy / temperature', '3', ''],
 ['16', 'Gibbs energy', 'G', 'kilojoule', 'kJ', 'extensive', 'energy', '3', ''],
 ['16', 'work', 'w', 'joule', 'J', 'extensive', 'energy', '3', ''],
 ['17', 'electrical potential (or voltage)', 'E', 'volt', 'V = kg m^2 / (A s^3)', '', 'energy / (time * current)', '2', ''],
 ['17', 'electrical current', 'I', 'ampere', 'A', '', 'current (basic unit)', '3', ''],
 ['17', 'electrical charge', 'Q', 'coulomb', 'C = A s', 'extensive', 'time * current', '3', ''],
 ['17', 'power', 'P', 'watt', 'W = J / s', '', 'energy / time', '3', '']]


def prep_quantities():
    for it in quant_table:
        newitems = [it[0], it[1]+' '+ it[2], it[3]+' ('+ it[4]+')', it[6], it[8], it[7]]
        quantities[int(newitems[0])].append(newitems)


def html_table(lol):
    out = ['<h3>Common quantities up to this chapter</h3>']
    out.append('<table>')
    out.append('  <tr>')
    out.extend('    <th>'+ b + '</th>' for b in lol[0])
    out.append('  </tr>')
    for sublist in lol[1:]:
        out.append('  <tr>')
        out.extend('    <td>' + b + '</td>' for b in sublist)
        out.append('  </tr>')
    out.append('</table>')
    return '\n'.join(out)


greek_alphabet = {
    u'\u0391': 'Alpha',
    u'\u0392': 'Beta',
    u'\u0393': 'Gamma',
    u'\u0394': 'Delta',
    u'\u0395': 'Epsilon',
    u'\u0396': 'Zeta',
    u'\u0397': 'Eta',
    u'\u0398': 'Theta',
    u'\u0399': 'Iota',
    u'\u039A': 'Kappa',
    u'\u039B': 'Lamda',
    u'\u039C': 'Mu',
    u'\u039D': 'Nu',
    u'\u039E': 'Xi',
    u'\u039F': 'Omicron',
    u'\u03A0': 'Pi',
    u'\u03A1': 'Rho',
    u'\u03A3': 'Sigma',
    u'\u03A4': 'Tau',
    u'\u03A5': 'Upsilon',
    u'\u03A6': 'Phi',
    u'\u03A7': 'Chi',
    u'\u03A8': 'Psi',
    u'\u03A9': 'Omega',
    u'\u03B1': 'alpha',
    u'\u03B2': 'beta',
    u'\u03B3': 'gamma',
    u'\u03B4': 'delta',
    u'\u03B5': 'epsilon',
    u'\u03B6': 'zeta',
    u'\u03B7': 'eta',
    u'\u03B8': 'theta',
    u'\u03B9': 'iota',
    u'\u03BA': 'kappa',
    u'\u03BB': 'lamda',
    u'\u03BC': 'mu',
    u'\u03BD': 'nu',
    u'\u03BE': 'xi',
    u'\u03BF': 'omicron',
    u'\u03C0': 'pi',
    u'\u03C1': 'rho',
    u'\u03C3': 'sigma',
    u'\u03C4': 'tau',
    u'\u03C5': 'upsilon',
    u'\u03C6': 'phi',
    u'\u03C7': 'chi',
    u'\u03C8': 'psi',
    u'\u03C9': 'omega',
}


def format_quantity(q, flashcard):
    if q[4]:
        q[4] = '\n@' + q[4] + '\n'
    if ' ' in q[1]:
        name, symbol = q[1].rsplit(maxsplit=1)
        if symbol[0] in greek_alphabet:
            symbol2 = symbol + ' (greek %s)' % greek_alphabet[symbol[0]]
        elif symbol.islower():
            symbol2 = '(lowercase) ' + symbol
        else:
            symbol2 = '(capital) ' + symbol
        if flashcard:
            q[1] = '%s<span title="%s"> (?)</span>' % (name, symbol2)
        else:
            q[1] = '%s<span title="%s"> (%s)</span>' % (name, symbol2, symbol)
    if flashcard:
        q[2] = '<span title="%s">?</span>' % q[2]
    return q


def show_quantities(chapter=1, flashcard=False):
    items = [header]
    for q in quantities[chapter]:
        q = format_quantity(q[:], False)
        items.append(q[:5])
    for chap in range(1,chapter):
        for q in quantities[chap]:
            q = format_quantity(q[:], flashcard)
            if q[5] and int(q[5]) < 3:
                items.append(q[:5])
    return(html_table(items))


def chemeq_harvest(text):
    first = text[1:].split()[0]
    if first.startswith('[') and first.endswith(']') and len(first) < 12:
        text = text[len(first):]
    species = re.split('(->|<=>| \+)', text[1:])
    species.append('')
    for s, sep in zip(species[0::2], species[1::2]):
        s = s.strip()
        stoich = 1
        for i, c in enumerate(s):
            if not c.isdigit():
                name = s[i:].strip()
                break
            digit = int(c)
            if i:
                stoich = 10 * stoich + digit
            else:
                stoich = digit
        molarmass = 'M[%s]' % (name.replace('(aq)', '').replace('(s)', '').replace('(l)', '').replace('(g)', ''))
        name = 'ν[%s]' % name
        expression = '%d' % stoich
        yield ('Known_stoich', text, name, expression, None)
        yield ('Known_chemformula', text, molarmass, molarmass, None)


physconst = {
    'R': Units(kg=1,m=2,s=-2,mol=-1,K=-1),
    'R_gas': Units(kg=1,m=2,s=-2,mol=-1,K=-1),
    'N_A': Units(mol=-1),
    'h_Planck': Units(kg=1,m=2,s=-1),
    'g0': Units(m=1,s=-2),
    'c0': Units(m=1,s=-1),
    'F': Units(A=1,s=1,mol=-1)
}

prep_formulae()

assessment = ['', '...important for many chemistry topics (you should know these by heart)', '...might need one of those', '...less likely']

header =  ['Ch.', 'quantity and symbol', 'typical unit (symbol)', 'dimension', 'definition']

prep_quantities()


def matching_closing(text):
    p = 1
    for i, c in enumerate(text[1:]):
        if c == '(':
             p += 1
        if c == ')':
            p -= 1
            if not p:
                return i
    return None

def chunks(text):
    tx = text[:]
    while tx:
        if tx[:2] in PSE:
            e = tx[:2]
            tx = tx[2:]
        elif tx[0] in PSE:
            e = tx[0]
            tx = tx[1:]
        elif tx[0] == '(':
            #rint(tx)
            p = matching_closing(tx[1:]) + 1
            e = tx[:p+1]
            tx = tx[p+2:]
            #rint(p, e, tx)
        else:
            raise SyntaxError(tx)
        if not tx or not tx[0].isdigit():
            nr = 1
        else:
            digs = ''
            while tx and tx[0].isdigit():
                digs += tx[0]
                tx = tx[1:]
            nr = int(digs)
        yield e, nr


def molar_mass(text):
    M = Q()
    tx = text.replace('(aq)', '').replace('(s)', '').replace('(l)', '').replace('(g)', '')
    for element, nr in chunks(tx):
        if element.startswith('('):
            #rint (nr, '* (', end='')
            M += Q(nr) * molar_mass(element[1:])
            #rint (')', end='+')
        else:
            M += Q(nr) * Q(PSE[element][0]) * unitquant['g'] / unitquant['mol']
            #rint(nr, '*', element, end='+')
    M.provenance = set()
    M.name = 'M[%s]' % text
    return M


PSE = {
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
 'Og': ['294.', 'Oganesson'],
}

naming_conventions = {
    'c': [(Units(m=-3, mol=1), 'concentration', 0)],
    'E': [(Units(kg=1, m=2, s=-2), 'energy', 0), (Units(A=-1, kg=1, m=2, s=-3), 'electrical potential', 0)],
    'S': [(Units(kg=1, m=2, s=-2, mol=-1, K=-1), 'molar entropy', 0)],
    'H': [(Units(kg=1, m=2, s=-2, mol=-1), 'molar enthalpy', 0)],
    'G': [(Units(kg=1, m=2, s=-2, mol=-1), 'molar Gibbs energy', 0)],
    'V': [(Units(m=3), 'volume', 0)],
    'v': [(Units(m=1, s=-1), 'velocity', 0)],
    'm': [(Units(kg=1), 'mass', 0)],
    'P': [(Units(kg=1, m=-1, s=-2), 'pressure', 0)],
    'T': [(Units(K=1), 'absolute temperature', 0)],
    't': [(Units(s=1), 'time', 0)],
    'n': [(Units(mol=1), 'chemical amount', 0)],
    'M': [(Units(kg=1, mol=-1), 'molar mass', 0)],
    '[': [(Units(), 'activity', 0)],
    'f': [(Units(), 'fraction', 0), (Units(s=-1), 'frequency', 0)],
    'ρ': [(Units(kg=1, m=-3), 'density', 0)],
    'ν': [(Units(), 'stoichiometric coefficient', 0), (Units(s=-1), 'frequency', 0)],
    'λ': [(Units(m=1), 'wavelength', 0)],
    'd': [(Units(m=1), 'length', 0)],
    'D': [(Units(kg=1, m=2, s=-2), 'bond dissociation energy', 0)],
    'q': [(Units(kg=1, m=2, s=-2), 'heat', 0)],
    'w': [(Units(kg=1, m=2, s=-2), 'work', 0)],
    'K': [(Units(), 'equilibrium constant', 0)],
    'k': [(Units(s=-1), 'first order rate constant', 0), (Units(m=3, s=-1, mol=-1), 'second order rate constant', 0), (Units(m=-3, s=-1, mol=1), 'zero order rate constant', 0)],
    'Π': [(Units(kg=1, m=-1, s=-2), 'osmotic pressure', 0)],
    'F': [(Units(kg=1, s=-2), 'force', 0)],
    'Q': [(Units(), 'reaction quotient', 0), (Units(A=1,s=1), 'electrical charge', 0)],
    'N': [(Units(), 'number of particles', 0)],
    'Hf': [(Units(kg=1, m=2, s=-2, mol=-1), 'heat of formation', 1)],
    'E_red': [(Units(A=-1, kg=1, m=2, s=-3), 'reduction potential', 1)],
    'E_ox': [(Units(A=-1, kg=1, m=2, s=-3), 'oxidation potential', 1)],
    'E_cell': [(Units(A=-1, kg=1, m=2, s=-3), 'cell potential', 1)],
    'k_second_order': [(Units(m=3, s=-1, mol=-1), 'second order rate constant', 1)],
    'k_first_order': [(Units(s=-1), 'first order rate constant', 1)],
    'k_zero_order': [(Units(m=-3, s=-1, mol=1), 'zero order rate constant', 1)],
    't½': [(Units(s=1), 'half life', 1)],
    't_½': [(Units(s=1), 'half life', 1)],
    'order_bond': [(Units(), 'bond order', 1)],
    'T_freeze': [(Units(K=1), 'freezing temperature', 1)],
    'T_boil': [(Units(K=1), 'boiling temperature', 1)],
    'T_melt': [(Units(K=1), 'melting temperature', 1)],
    'K_A': [(Units(), 'acid dissociation constant', 1)],
    'K_B': [(Units(), 'base dissociation constant', 1)],
    'pKa': [(Units(), 'pKa', 1)],
    'H_f': [(Units(kg=1, m=2, s=-2, mol=-1), 'heat of formation', 1)],
    'ΔHf°': [(Units(kg=1, m=2, s=-2, mol=-1), 'standard heat of formation', 1)],
    'E_kinetic': [(Units(kg=1, m=2, s=-2), 'kinetic energy', 1)],
    'E_potential': [(Units(kg=1, m=2, s=-2), 'potential energy', 1)],
    'E_kin': [(Units(kg=1, m=2, s=-2), 'kinetic energy', 1)],
    'E_pot': [(Units(kg=1, m=2, s=-2), 'potential energy', 1)],
    'pH': [(Units(), 'pH', 1)],
    'pOH': [(Units(), 'pOH', 1)],
    'E_bond': [(Units(kg=1, m=2, s=-2), 'bond energy', 1)],
    'P_vapor': [(Units(kg=1, m=-1, s=-2), 'vapor pressure', 1)],
    'P°': [(Units(kg=1, m=-1, s=-2), 'vapor pressure of pure', 1)],
    'K_boil': [(Units(kg=-1, mol=1, K=1), 'boiling point elevation constant', 1)],
    'K_freeze': [(Units(kg=-1, mol=1, K=1), 'freezing point depression constant', 1)],
    'c_p': [(Units(m=2, s=-2, K=-1), 'specific heat capacity', 1)],
    'c_P': [(Units(m=2, s=-2, K=-1), 'specific heat capacity', 1)],
    'R': [(Units(kg=1, m=2, s=-2, mol=-1, K=-1), 'universal gas constant', 2)],
    'N_A': [(Units(mol=-1), "Avogadro's constant", 2)],
    'h_Planck': [(Units(A=(0, 1, 2, -1, 0, 0, 0, 0)), "Planck's constant", 2)],
    'c0': [(Units(m=1, s=-1), 'speed of light', 2)],
    'g0': [(Units(m=1, s=-2), 'gravitational acceleration', 2)],
    'm_s': [(Units(), 'spin quantum number', 2)],
    'ℓ': [(Units(), 'angular quantum number', 2)],
    'm_ℓ': [(Units(), 'magnetic quantum number', 2)],
}

typical_units_reverse = {}
for symbol in naming_conventions:
    for item in naming_conventions[symbol]:
        if item[0] not in typical_units_reverse:
            typical_units_reverse[item[0]] = symbol

typicalunits = {symbol: naming_conventions[symbol][0][0] for symbol in naming_conventions if naming_conventions[symbol][0][2] == 0}


def good_units(symbol, units):
    if symbol not in naming_conventions:
        return False
    return any(units == item[0] for item in naming_conventions[symbol])

def dimension_name(units):
    return ' or '.join(item[1]
            for symbol in naming_conventions
                for item in naming_conventions[symbol]
                    if item[0] == units)

def quantity_name(symbol, units=None):
    if len(naming_conventions[symbol]) == 1 or not units:
        return naming_conventions[symbol][0][1]
    for item in naming_conventions[symbol]:
        if units == item[0]:
            return item[1]
    return symbol


SuperSpecials = dict([x.split(' ', 1) for x in '''R universal gas constant
N_A Avogadro's constant
h_Planck Planck's constant
c0 speed of light
g0 gravitational acceleration
m_s spin quantum number
ℓ angular quantum number
m_ℓ magnetic quantum number'''.splitlines()])
Specials = dict([x.split(' ', 1) for x in '''E_red reduction potential
k_second_order second order rate constant
k_first_order first order rate constant
k_zero_order zero order rate constant
t½ half life
t_½ half life
order_bond bond order
T_freeze freezing temperature
T_boil boiling temperature
T_melt melting temperature
K_A acid dissociation constant
K_B base dissociation constant
K_eq equilibrium constant
pKa pKa
H_f heat of formation
ΔHf° standard heat of formation
ΔᵣG Gibbs energy of reaction
E_kinetic kinetic energy
E_potential potential energy
E_kin kinetic energy
E_pot potential energy
pH pH
pOH pOH
E_kin kinetic energy
E_pot potential energy
E_bond bond energy
P_vapor vapor pressure
P° vapor pressure of pure
K_boil boiling point elevation constant
K_freeze freezing point depression constant
c_p specific heat capacity
c_P specific heat capacity'''.splitlines()])
Qnames = [x.split(' ', 1) for x in '''V volume
n chemical amount
c concentration
m mass
M molar mass
P pressure
T temperature
t time
G Gibbs energy
D bond dissociation energy
H enthalpy
Hf heat of formation
S entropy
q heat
w work
K equilibrium constant
k rate constant
ν stoichiometric coefficient
ρ density
λ wave length
Π osmotic pressure
E potential
F force
Q reaction quotient
N number of particles
'''.splitlines()]
extensive = set('m V n'.split())

Qdict = {q[0] : q[1] for q in Qnames}

abbr = {
    'eq': 'equilibrium',
    'avg': 'average',
    'init': 'initial',
    'max': 'maximal',
    'min': 'minimal',
    'RT': 'room temperature',
    'tot': 'total',
    'rel': 'relative',
    'rms': 'root-mean-square',
    'est': 'estimated'
}

adjectives = '''average
final
initial
maximal
minimal
diffusion
effusion
equilibrium
formal
atmospheric
forward
reverse
relative
theoretical
actual
total
molecular
atomic
average
estimated
measured
hydrostatic
'''.splitlines()

chemdatabase = [a.split(maxsplit=1) for a in '''H2(g)      hydrogen gas               54
H2O(g)     water vapor               42
H2O(l)     liquid water               41
CO2(g)     carbon dioxide gas              40
N2(g)      nitrogen gas               36
O2(g)      oxygen gas               31
NO(g)      nitrogen oxide gas               30
H2O        water               26
H3O+(aq)   hydronium ion               22
NH3(g)     ammonia gas               21
SO2(g)     sulfur dioxide gas               21
H+(aq)     aqueous hydrogen ion               19
CO(g)      carbon monoxide gas               19
Cl2(g)     chlorine gas               18
Ag+(aq)    silver ion               17
N          atomic nitrogen               17
Fe(s)      solid iron               16
HCl        hydrogen chloride               16
H          atomic hydrogen               16
NH3        ammonia               15
P          phosphorous               15
HCl(g)     hydrogen chloride gas               13
NO2(g)     nitrogen dioxide gas               13
P4(s)      white phosphorous                13
O2         dioxygen               13
O          atomic oxygen               13
OH-(aq)    hydroxid ion               12
Cl-(aq)    chloride ion               12
Cu(s)      elemental copper               12
K          potassium               12
K+          potassium ion               ?
K+(aq)          potassium ion               ?
Na+          sodium ion               ?
Na+(aq)          sodium ion               ?
Cl-          chloride ion               ?
Cl-(aq)          chloride ion               ?
NO3-(aq)   nitrate ion               11
Mg2+(aq)   magnesium ion               11
CaO(s)     calcium oxide               11
CaCl2     calcium chloride              ?
CH4(g)     methane gas               11
CH4     methane               ?
Zn(s)      elemental zinc               11
Hg(l)      liquid mercury               11
Sr         strontium               11
NO         nitrogenoxide               11
Na+(aq)    sodium ion               10
SO3(g)     sulfur trioxide gas               10
PO43-      phosphate ion               10
Ag(s)      elemental silver               10
Cl         chlorine               10
Al         Aluminum               10
N2         dinitrogen               10
S          sulfur               10
Ca2+(aq)   calcium ion               9
C2H5OH     ethanol               9
Al(s)      elemental aluminum               9
NaOH       sodium hydroxide               9
CO2        carbon dioxide               9
Ca(OH)2(aq) calcium hydroxide               8
Fe2O3(s)   iron(III)oxide               8
NH3(aq)    aqueous ammonia               8
H2PO4-     dihydrogen phosphate ion               8
HSO4-      hydrogen sulfate ion               8
H2S        dihidrogen sulfide               8
NO2        nitrogen dioxide               8
H3PO4 phosphoric acid ?
Ca(OH)2 calcium hydroxide  ?
NaCl sodium chloride ?'''.splitlines()]

chemdict = {formula: name[:-2].rstrip() for formula, name, *_ in chemdatabase}


def chemname(name):
    if name in PSE:
        return PSE[name][1].lower()
    if name in chemdict:
        return chemdict[name]
    return name

def formula(text):
    if any(c.isdigit() for c in text):
        return True
    if any(c.isupper() for c in text[1:]):
        return True
    if text in PSE:
        return True
    return False


#rint(Specials)

def pronounce(qname, units=None):
    #print(qname)
    if qname.startswith('!'):
        return 'Chemical formula or equation: ' + qname[1:]
    if qname.startswith('@'):
        return 'Mathematical expression: ' + qname[1:]
    if qname in naming_conventions and naming_conventions[qname][0][2] == 2:
        return naming_conventions[qname][0][1]
    sname = ''
    name = ''
    for spec in naming_conventions:
        if naming_conventions[spec][0][2] == 1 and qname.startswith(spec):
            sname = naming_conventions[spec][0][1]
            qname = qname[len(spec):]
    if qname.startswith('Δ') and not qname.startswith('Δᵣ'):
        name = 'change in '
        qname = qname[1:]
    if qname in SuperSpecials:
        qname = SuperSpecials[qname]
        is_special = True
    else:
        is_special = False
        for spec in Specials:
            if qname.startswith(spec):
                is_special = True
                sname = Specials[spec]
                qname = qname[len(spec):]
                break
    if not is_special:
        for spec in naming_conventions:
            if naming_conventions[spec][0][2] == 1 and qname.startswith(naming_conventions[spec][0][1]):
                sname = naming_conventions[spec][0][1]
                qname = qname[len(spec):]
    if '[' in qname:
        first, temp = qname.split('[', maxsplit=1)
        chem, second = temp.split(']', maxsplit=1)
        qname = '_'.join([first, '['+chemname(chem), second])
    qs = qname.split('_')
    #print(qs)
    if sname:
        name = name + sname
        basename = name
    else:
        basename = qs.pop(0)
        digits = ''
        while basename and basename[-1].isdigit():
            digits = basename[-1:] + digits
            basename = basename[:-1]
        if '°' in basename:
            name = name + 'standard '
            basename = basename.replace('°', '')
        if basename in naming_conventions:
            if basename == 'ν' and units and units != (0,0,0,0,0,0,0,0):
                name = name + 'frequency'
            elif basename == 'n' and units and units == (0, 0, 0, 0, 0, 0, 0, 0):
                    name = name + 'principal quantum number'
            else:
                name = name + quantity_name(basename, units)
        elif len(basename) == 1:
            name = name + 'quantity ' + basename
        elif not basename and qs[0].startswith('['):
            name = name + '['
        else:
            name = name + basename
        if digits:
            name = name + ' ' + digits
    for item in qs:
        if not item:
            continue
        if item.startswith('['):
            if name.endswith('['):
                name = name + chemname(item[1:]) + ']'
            else:
                name = name + ' of ' + chemname(item[1:])
            if basename in extensive and item.split(']')[0][-1] not in '+-)':
                name = name + ' sample'
        elif item in adjectives:
            name = item + ' ' + name
            continue
        elif item in abbr:
            name = abbr[item] + ' ' + name
            continue
        elif item == '298':
            name = name + ' at 298 K'
        elif item[0].isupper():
            if not formula(item):
                name = name + ' of ' + item.lower()
            else:
                name = name + ' of ' + item
        elif ' of particles' in name:
            name = ' '.join(name.split(' particles')) + ' ' + item
        elif ' of ' in name:
            name = name + ' ' + item
        else:
            name = name + ' of ' + item
        if ' of particles of ' in name:
            name = ' '.join(name.split(' particles of ')) + ' particles'
        if ' of the by of the ' in name:
            name = ' by '.join(name.split(' of the by of the '))
        if ' of pure of the ' in name:
            name = ' of pure '.join(name.split(' of pure of the '))
        if ' of pure of ' in name:
            name = ' of pure '.join(name.split(' of pure of '))
    return name


if __name__ == '__main__':
    print(molar_mass('CH4'))
    print(molar_mass('CH2(OH)2'))
    print(molar_mass('CH3(OH)'))
    print(pronounce('N[CH4(g)]'))
    print(pronounce('N[C2H6]'))
    print(pronounce('N[Mg]'))
    print(pronounce('m[C2H6]'))
    print(pronounce('m[Mg]'))
    print(pronounce('V[C2H6]'))
    print(pronounce('c_P'))
    print(pronounce('R'))
    print(pronounce('K_eq'))
    print(pronounce('K_eq[H2O]'))