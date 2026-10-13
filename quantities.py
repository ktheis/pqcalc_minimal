# coding=utf-8
"""

Classes and functions to do arithmetic with physical quantities.

At the core of this module is the class Q, which defines a number that has units, a name, and a crude indication
of uncertainty (significant figures).

The way significant figures are treated here is just for number formatting - all calculations are done to the
maximum precision of python floats (~57 bits, equivalent to ~17 decimal digits). There is a special function
"moredigits" to retrieve the full internal representation of the number.

The online calculator hosted at http:\\\\ktheis.pythonanywhere.com uses this code.

Author: Karsten Theis (ktheis@westfield.ma.edu)
"""
import math
from math import log10 as math_log10
from math import log as math_log
from math import exp as math_exp
from math import sin as math_sin
from math import cos as math_cos
from math import tan as math_tan
from math import asin as math_asin
from math import acos as math_acos
from math import atan as math_atan
from math import floor
from math import sqrt as math_sqrt
from fractions import Fraction
import collections
import re
import string

SIunit_symbols = ["A", "kg", "m", "s", "mol", "K", "Cd", "$"]


def Units(A=0, kg=0, m=0, s=0, mol=0, K=0, Cd=0, dollar=0):
    return A, kg, m, s, mol, K, Cd, dollar


unity = Units()

def prettyU(units):
    symbols = ["A", "kg", "m", "s", "mol", "K", "Cd", "dollar"]
    return "Units(" + ",".join("%s=%s" % (x[0], repr(x[1])) for x in zip(symbols, units) if x[1]) + ")"


class QuantError(ArithmeticError):
    """An exception used by the class Q."""
    pass


def raise_QuantError(complaint, name, provenance):
    raise QuantError((complaint, Q(0, name, provenance=provenance)))


class Q(object):
    """A class for arithmetic with physical quantities having units and significant figures

    The class defines the arithmetic operators +, -, *, /, ** for Q. For binary operations, both
    operands must be instances of Q. Other methods serve to show the result and how it was
    calculated.

    Attributes:
      number(float): The number part of the quantity
      units(tuple): The base units of the quantity, see Units method
      name(str): The name of the quantity
      sigfig(int): The number of significant figures. 100 refers to an exact integer
      uncert(float): An estimate of the uncertainty of the quantity
      prefu(list(str)): the preferred units for the quantity, given as str in unitquant
      provenance: quantities from which it was derived

    Examples:
      Q(2) is the dimensionless number 2
      Q("kg") is the quantity 1 kg
      Q(3.0, "", Units(kg=1), 2, [], None) is 3.0 kg

    """

    def __init__(self, number=0.0, name="", units=unity, uncert=0.0, prefu=set(), provenance=None):
        """

        """

        try:
            number + 1.0
            self.number = number
            self.units = Units(*units)
            self.name = name[:]
            self.prefu = set(prefu)
            if 'M' in prefu:
                self.prefu.add('L')
            if 'mol' in prefu:
                pass #self.prefu.add('M')
            self.uncert = uncert
            self.provenance = provenance
            self.comment = ''
        except TypeError:
            if number in unitquant:
                q = unitquant[number]
            else:
                q = number2quantity(number)
            self.__dict__ = q.__dict__

    def __repr__(self):
        if self.name:
            self.fakename = 'somename'
        else:
            self.fakename = ''
        if self.name in unitquant and self.__dict__ == unitquant[self.name].__dict__:
            return u"Q('%s')" % self.name
        if repr(self.number).startswith("inf"):
            raise OverflowError(self.number)
        symbols = ["A", "kg", "m", "s", "mol", "K", "Cd", "dollar"]
        self.runits = "Units(" + ",".join("%s=%s" % (x[0], repr(x[1])) for x in zip(symbols, self.units) if x[1]) + ")"

        if self.provenance:
            return u"Q(%(number)r, '%(name)s', %(runits)s, %(uncert)r, %(prefu)s, %(provenance)s)" % self.__dict__
        if self.prefu:
            return u"Q(%(number)r, '%(name)s', %(runits)s, %(uncert)r, %(prefu)s)" % self.__dict__
        if self.name:
            rr = u"Q(%(number)r, '%(name)s', %(runits)s, %(uncert)r)" % self.__dict__
            return rr
        return u"Q(%(number)r, units=%(runits)s, uncert=%(uncert)r)" % self.__dict__

    def __str__(self):
        return ascii_qvalue(self)

    def copy(self):
        return Q(number=self.number, name=self.name, units=self.units,
                 uncert=self.uncert, prefu=self.prefu, provenance=self.provenance[:] if self.provenance else None)


    def setdepth(self):
        if not hasattr(self, "depth"):
            if not self.provenance:
                self.depth = 0
            else:
                self.depth = 1 + max(child.setdepth() for child in self.provenance)
                if self.name == "-%s":
                    self.depth -= 1
        return self.depth


    def steps(self, level, writer, subs=None, flaigs=()):
        """
        :param level: -1: task, 0: value, 1..n: work
        :param writer: either ascii or latex
        :param subs: modify q.name for latex output
        :return: a string describing an expression
        """
        if level < 0 and not self.provenance:
            return writer(self, showvalue=False, flags=flaigs)
        if not level or level > self.depth:
            return writer(self, flags=flaigs, guard=0 if (level <= 1 or not self.provenance) else 1)
        if not self.provenance:
            print('what the')
            return writer(self, showvalue=False, flags=flaigs)
        name = self.name
        ll = max((q.depth for q in self.provenance), default=-1)
        children = [child(index, level, name, q, subs, writer, flaigs, ll) for index, q in enumerate(self.provenance)]
        if subs and name in subs:
            name = subs[name]
        if subs and len(name) > 6 and name[:6] in ['sum(%s', 'avg(%s', 'min(%s', 'max(%s']:
            name = name.replace(name[:6], subs[name[:6]])
        return name % tuple(children)

    def __mul__(self, other):
        units = tuple([x[0] + x[1] for x in zip(self.units, other.units)])
        return muldiv(self.number * other.number, '%s * %s', units, self, other)

    def __truediv__(self, other):
        units = tuple([x[0] - x[1] for x in zip(self.units, other.units)])
        try:
            number = self.number / other.number
        except ZeroDivisionError:
            raise_QuantError("denominator is zero", "%s / %s", (self, other))
        if False and not self.uncert and not other.uncert:  # turns 1 / 2 into 1/2 rather than 0.5
            try:
                number = Fraction(self.number, other.number)
            except TypeError:
                pass
        return muldiv(number, '%s / %s', units, self, other)

    def __div__(self, other):
        return self.__truediv__(other)

    def __neg__(self):
        if self.name == "-%s":
            return self.provenance[0]
        return Q(-self.number, "-%s", self.units, self.uncert, self.prefu, (self,))

    def __pos__(self):
        return self

    def __add__(self, other):
        return addsub(self.number + other.number, '%s + %s', self, other)

    def __sub__(self, other):
        return addsub(self.number - other.number, '%s - %s', self, other)

    def __pow__(self, other):
        if other.units != unity:
            raise_QuantError("the exponent can't have units", "%s ^ %s", (self, other))
        if self.units == unity:
            units = self.units
        else:
            if not hasattr(other.number, 'denominator'): # not int or fraction
                raise_QuantError("can't raise units to irrational exponent", "%s ^ %s", (self, other))
            units = tuple([fraction_or_int(u * other.number) for u in self.units])
        try:
            if hasattr(self.number, 'denominator') and hasattr(other.number, 'denominator') and other.number > 10:
                number = self.number ** float(other.number)
            else:
                number = self.number ** other.number
        except ValueError:
            raise_QuantError("arithmetic problem, e.g. complex numbers not implemented", "%s ^ %s", (self, other))
        except OverflowError:
            raise_QuantError("overflow: value too high", "%s ^ %s", (self, other))
            # try:
            #     number = self.number ** mpmath.mpf(other.number)
            # except OverflowError:
            #     raise_QuantError("overflow: value too high", "%s ^ %s", (self, other))
        if number.imag:
            raise_QuantError("complex numbers not implemented", "%s ^ %s", (self, other))
        uncert1 = abs(self.uncert / self.number * number * other.number)
        if hasattr(self.number, 'denominator'):
            argument = float(self.number)
        else:
            argument = self.number
        uncert2 = abs(other.uncert * math_log(abs(argument)) * number)
        uncert = uncert1 + uncert2
        return Q(number, '%s ^ %s', units, uncert, self.prefu, (self, other))



def child(index, level, name, q, subs, writer, flags, ll):
    '''
    returns subexpression, in parentheses if needed
    :param index: 0: LHS, 1: RHS
    :param level: how deep into the expression
    :param name: operation on child
    :param q: Q(child)
    :param subs: empty for plain, substitutions needed for LaTeX
    :param writer: LaTeX or plain function
    :param flags: ...flags
    :return: string giving the subexpression
    '''
    ch = q.steps(level, writer, subs, flags)
    if '°aC' in q.prefu and level>=1 and ll<level and ('/' in name or '*' in name):
        q.prefu.remove('°aC')
        ch = q.steps(level, writer, subs, flags)
        #rint('hello', q.depth, level, ll, q.provenance, ch, name, repr(q))
    if ((q.provenance and level <= q.depth and opprio[name] > opprio[q.name] and opprio[name] and opprio[
        q.name] and not (subs and "/" in name)) or  # order of precedence requires it
            (name.startswith("-") and ch.startswith("-")) or  # double negative
            ("-" in name and index == 1 and ch.startswith("-")) or  # minus negative
            ("*" in name and index == 1 and ch.startswith("-")) or  # times a negative something
            ("^" in name and level >= 0 and q.units != unity) or  # power of something with a unit
            ("^" in name and ch.startswith("-") and index == 0) or  # raising a negative something to a power
            ("^" in name and (
                            "times" in ch or "frac" in ch))):  # fractions or scientific notation raised to power
        return "(" + ch + ")"
    return ch


def addsub(number, name, left, right):
    if left.units != right.units and left.number and right.number:
        raise_QuantError("Units in sum/difference not compatible", name, (left, right))
    prefu, provenance = inherit_binary(left, right)
    units = left.units if left.number else right.units
    uncert = math_sqrt(left.uncert ** 2 + right.uncert ** 2)
    if '°aC' in prefu:
        if units != unitquant['K'].units:
            raise_QuantError("Units °aC in sum/difference can't have compound units", name, (left, right))
        if '°aC' in left.prefu and '°ΔC' in right.prefu:
            prefu.discard('°ΔC')
        elif '°aC' in right.prefu and '°ΔC' in left.prefu and name == '%s + %s':
            prefu.discard('°ΔC')
        elif '°aC' in left.prefu and '°aC' in right.prefu and name == '%s - %s':
            prefu.discard('°aC')
            prefu.add('°ΔC')
        elif left.number and right.number: #but adding zero is o.k.
            prefu.discard('°aC')

    return Q(number, name, units, uncert, prefu, provenance)


def muldiv(number, name, units, self, other):
    if number:
        uncert = math_sqrt((self.uncert / self.number) ** 2 + (other.uncert / other.number) ** 2) * abs(number)
    elif not other.uncert:
        uncert = self.uncert
    elif not self.uncert:
        uncert = other.uncert
    else:
        uncert = 0.0
    if hasattr(number, 'denominator') and number.denominator == 1:
        number = int(number)
    prefu, provenance = inherit_binary(self, other)
    if '°aC' in prefu:
        prefu.remove('°aC')
    return Q(number, name, units, uncert, prefu, provenance)


def fraction_or_int(number):
    if number.denominator == 1:
        return int(number)
    return number

def sigfig(number, uncert):
    '''
    returns number of significant figures of a quantity
    :param number: the value of the quantity
    :param uncert: the uncertainty of the quantity
    :return: integer giving significant figures (100 = exact number)
    >>> sigfig(4, 0.0)
    100
    >>> sigfig(12.56, 0.04)
    4
    >>> sigfig(5.6, 0.09999999999999999)
    2
    >>> sigfig(0.0, 0.14142135623730953)
    0
    '''
    if not uncert:
        return 100
    if not number:
        return 1 - int(floor(math_log10(uncert * 1.05)))
    most = int(floor(math_log10(abs(number))))
    sig = int(floor(math_log10(uncert * 1.05)))
    sigfig = most - sig + 1
    if sigfig > 0:
        return sigfig
    return 1


def ascii_units(list1):
    list2 = [i[0] for i in list1 if i[1] == 1]
    list2.extend(["%s^%s" % i for i in list1 if i[1] != 1])
    return " ".join(list2)


def latex_units(list1):
    '''
    Formats units (all positive exponents) for output in LaTeX
    :param list1: list of ('unit', exponent) tuples
    :return string showing units in LaTeX:
    >>> latex_units([('J', 1)])
    '\\mathrm{J}'
    >>> latex_units([('mol', 1), ('K', 1)])
    '\\mathrm{mol}\\ \\mathrm{K}'
    >>> latex_units([('K', 1), ('s', 2), ('mol', 1)])
    '\\mathrm{K}\\ \\mathrm{mol}\\ \\mathrm{s}^{2}'
    '''
    list2 = ["\\mathrm{%s}" % i[0] for i in list1 if i[1] == 1]
    list2.extend(["\\mathrm{%s}^{%s}" % i for i in list1 if i[1] != 1])
    return "\\ ".join(list2)


def ascii_qvalue(q, guard=0):
    """Formats quantities as number times a fraction of units, all with positive exponents"""
    value, poslist, neglist = unit_string(q.number, q.units, q.prefu)
    numbertext = ascii_number(value, sigfig(q.number, q.uncert) + guard)
    if len(neglist) == 1 and neglist[0][1] == 1:
        negtext = "/" + neglist[0][0]
    elif neglist:
        negtext = "/(%s)" % ascii_units(neglist)
    else:
        negtext = ""
    if not poslist:
        if not neglist:
            return numbertext
        return numbertext + " 1" + negtext
    return numbertext + " " + ascii_units(poslist) + negtext


def latex_qvalue(q, guard, flags):
    '''
    String representing a quantity in LaTeX
    :param q: quantity
    :param guard: extra decimal points
    :param flags: set(flags)
    :return: the string representation
    >>> latex_qvalue(Q(5.4, units=Units(), uncert=0.1), 0, set())
    '5.4'
    >>> latex_qvalue(Q(6.022e+23, '', Units(mol=-1), 1e+20, {'mol'}), 0, set())
    '6.022\\times 10^{23}\\frac{1}{\\mathrm{mol}}'
    >>> latex_qvalue(Q(81.3, '', Units(m=2), 0.1, {'m'}), 0, set())
    '81.3\\  \\mathrm{m}^{2}'
    >>> latex_qvalue(Q(3900.0, '', Units(m=-3,mol=1), 100.00000000000001, {'L', 'mol'}), 0, set())
    '3.9\\  \\frac{\\mathrm{mol}}{\\mathrm{L}}'
    >>> latex_qvalue(Q(6.1, units=Units(), uncert=0.1), 0, {'__showuncert__'})
    '6.1(1)'
    >>> latex_qvalue(Q(8.13e-56, units=Units(), uncert=4e-58), 0, {'__showuncert__'})
    '8.13(4)\\times 10^{-56}'
    '''
    value, poslist, neglist = unit_string(q.number, q.units, q.prefu)
    #rint(value, poslist, neglist, q.uncert)
    if poslist == [('°aC',1)]:
        uc = q.uncert
        poslist = [('°aC',1)]
    else:
        try:
            uc = q.uncert * value / q.number
        except ZeroDivisionError:
            uc = q.uncert
    sf = sigfig(value, uc)
    if '__showuncert__' in flags:
        numbertext = latex_number(ascii_number(value, sf, uc))
    elif '__hidenumbers__' in flags:
        numbertext = "\_\_\_\_\_\_\_\_\_\_\_\_"
    else:
        numbertext = latex_number(ascii_number(value, sf + guard))
    if '__hideunits__' in flags:
        return numbertext + ("\\phantom{\\frac{km mol}{kg mol}}" if q.units != unity else "")
    if neglist:
        unittext = "\\frac{%%s}{%s}" % latex_units(neglist)
    else:
        unittext = "%s"
    if not poslist:
        if not neglist:
            return numbertext
        return numbertext + unittext % "1"
    return numbertext + "\\  " + unittext % latex_units(poslist)


def ascii_writer(q, showvalue=True, guard=0, flags=()):
    if not showvalue and q.name:
        return q.name
    return ascii_qvalue(q, guard)


def latex_writer(q, showvalue=True, guard=0, flags=()):
    if not showvalue and q.name:
        return latex_name(q.name)
    return latex_qvalue(q, guard, flags)


def try_all_derived(SIunits, derived):
    """Score the benefits of replacing SI units by any of the preferred derived units
    and return the best substitution.

    Yields: A tuple(score, derived unit, exponent)

    There is a reward of 20 for each SIunit dropped, and a penalty of 30 for adding a derived unit.
    E.g. going from m^2 to L/m receives a score of -10, but from m^3 to L a score of +30.
    >>> try_all_derived([0, 0, 3, 0, 0, 0, 0, 0], {'L': 0})
    (36, 'L', 1)
    >>> try_all_derived([0, 0, 0, 0, 0, 0, 0, 0], {'L': 1})
    (-90, 'L', 1)
    >>> try_all_derived([0, 0, 0, 0, 1, 0, 0, 0], {'mM': 0, 'L': 0})
    (-64, 'mM', 1)
    """
    res = []
    for d in derived:
        for sign in [-1, 1]:  # 1 means in numerator, -1 in denominator
            improvement = -30
            if derived[d] * sign < 0:
                continue  # don't take away derived units
            for old, used_in_derived in zip(SIunits, unitquant[d].units):
                improvement += 20 * (abs(old) - abs(old - sign * used_in_derived))
                if old and not (old - sign * used_in_derived):
                    improvement += 6
            res.append( (improvement, d, sign) )
    return max(iter(res))


def unit_string(value, units, prefu={'L', 'J', 'C', 'V', 'N', 'W', 'Pa'}):
    """Determine the most compact set of units for a quantity given in SI units. Also, choose which units of equal dimensions to
    choose while keeping the number near 1.

    Returns: (the number(float) and, as two lists, the positive and negative units of the quantity

    >>> unit_string(8.314, (0, 1, 2, -2, -1, -1, 0, 0), {'K', 'J', 'mol'})
    (8.314, [('J', 1)], [('K', 1), ('mol', 1)])
    >>> unit_string(8.314, (0, 1, 2, -2, -1, -1, 0, 0), set())
    (8.314, [('kg', 1), ('m', 2)], [('K', 1), ('s', 2), ('mol', 1)])
    >>> unit_string(0.00513, (0, 0, 1, 0, 0, 0, 0, 0), {'mm'})
    (5.13, [('mm', 1)], [])
    >>> unit_string(0.04713, (0, 0, 1, 0, 0, 0, 0, 0), {'m', 'mm'})
    (47.13, [('mm', 1)], [])
    >>> unit_string(4.713, (0, 0, 1, 0, 0, 0, 0, 0), {'m', 'mm'})
    (4.713, [('m', 1)], [])
    """
    if units == unity or not value:
        if value and '％' in prefu:
            return value*100, [('％', 1)], []
        return value, "", ""
    SIunits = list(units)
    derived = dict((pu, 0) for pu in prefu if (pu in unitquant and sum(abs(t) for t in unitquant[pu].units) > 1))
    while derived:
        (improvement, d, sign) = try_all_derived(SIunits, derived)
        if improvement <= 0:
            break
        derived[d] += sign
        for i, used_in_derived in enumerate(unitquant[d].units):
            SIunits[i] -= used_in_derived * sign
        value /= unitquant[d].number ** sign
    allunits = dict([(x, derived[x]) for x in derived if derived[x]])
    DUS = [du for du in allunits if du in derived]
    for DU in DUS: # choose between atm and mmHg etc.
        choices = [pu for pu in derived if unitquant[pu].units == unitquant[DU].units]
        if not choices:
            break
        quality = [(abs(math_log10(abs(value) / (unitquant[c].number / unitquant[DU].number) ** allunits[DU]) - 1.0), c)
                   for c in choices]
        best = min(quality)[1]
        if best != DU:
            allunits[best] = allunits[DU]
            value /= (unitquant[best].number / unitquant[DU].number) ** allunits[best]
            allunits[DU] = 0
    for i, SIU in enumerate(SIunit_symbols): # choose between m, cm, mm etc.
        if not SIunits[i]:
            continue
        choices = [pu for pu in prefu if (pu not in derived and pu in unitquant) and unitquant[pu].units[i]]
        if not choices:
            break
        quality = [(abs(math_log10(abs(value) / unitquant[c].number ** (SIunits[i] / unitquant[c].units[i])) - 1.0), c)
                   for c in choices]
        best = min(quality)[1]
        allunits[best] = Fraction(SIunits[i], unitquant[best].units[i])
        if allunits[best].denominator == 1:
            allunits[best] = int(allunits[best])
        SIunits[i] = 0
        value /= unitquant[best].number ** allunits[best]
    for u, d in zip(SIunit_symbols, SIunits):
        if d:
            allunits[u] = d
    #print('unitstring', allunits, prefu)
    if '°ΔC' in prefu and 'K' in allunits:
        allunits['°ΔC'] = allunits['K']
        allunits['K'] = 0
        #rint('unitstring delC', allunits)
    elif '°aC' in prefu and allunits == {'K':1}:
        #unitstring {'K': 1} {'°aC', 'K'}
        allunits = {'°aC':1}
        value -= 273.15
        #rint('unitstring absC', allunits)
    poslist = [(u, exp) for u, exp in allunits.items() if exp > 0]
    neglist = [(u, -exp) for u, exp in allunits.items() if exp < 0]
    return value, poslist, neglist


def mostsig(number, ope=1.00000000001): return int(floor(math_log10(abs(number) * ope)))



def latex_number(ascii):
    '''
    format fractions and exponential notation in LaTeX
    :param ascii: plain number string
    :return: LateX-formatted number
    >>> latex_number('3.4e-5')
    '3.4\\times 10^{-5}'
    >>> latex_number('(1 / 2)')
    '\\frac{1 }{ 2}'
    '''
    if "e" in ascii:
        return ascii.replace("e", r"\times 10^{") + "}"
    if "/" in ascii:
        sign, rest = ascii.split("(")
        n, d = rest.split("/")
        return "%s\\frac{%s}{%s}" % (sign, n, d[:-1])
    return ascii

def ascii_number(number, sigfig, uncert=None, delta=0.0000000001):
    '''
    Formats a number with given significant figures as a string
    :param number: float
    :param sigfig: number of significant figures
    :param uncert: 0 or uncertainty
    :param delta: how close to integer to show integer
    :return: string representing the number and uncertainty
    >>> ascii_number(0.000563, 3, None, 1e-10)
    '5.63e-4'
    >>> ascii_number(4.713, 4, None, 1e-10)
    '4.713'
    >>> ascii_number(Fraction(1, 2), 100, None, 1e-10)
    '(1 / 2)'
    >>> ascii_number(8.13e-56, 3, 4e-58, 1e-10)
    '8.13(4)e-56'

    '''
    if (not uncert) and sigfig >= 100:
        return exact_number(number, delta)
    if number == 0.0 or number == 0:
        if sigfig:
            return '0.' + '0'*(sigfig-1)
        return "0"
    least, uncert_str = format_uncert(number, sigfig, uncert)
    if least < 0 and -2 < least + sigfig < 5:
        return "%.*f%s" % (-least, number, uncert_str)  # number is a decimal
    if not least:
        return "%.0f%s." % (number, uncert_str)  # number ends with . to show the ones are significant
    if sigfig:
        t = ("%.*e" % (sigfig - 1, number)).replace("e+", "e").replace("e0", "e").replace("e-0", "e-")
        if t == 'inf' or t == '0e0':
            t = str(number)
            m, e = t.split("e")
        else:
            m, e = t.split("e")
        return "%s%se%s" % (m, uncert_str, e)  # number will be shown in scientific notation
    return "%.0f(?)" % number  # neither sigfig nor uncert was given



def format_uncert(number, sigfig, uncert):
    '''
    format the explicit uncertainty (or not)
    :param number: the value
    :param sigfig: the number of significant figures
    :param uncert: the uncertainty or 0
    :return: (least signigicant digit, uncertainty string or '')
    >>> format_uncert(8.13e-56, 3, 4e-58)
    (-59, '(4)')
    >>> format_uncert(100.1, 4, None)
    (-1, '')
    >>> format_uncert(10010.0, 4, None)
    (1, '')
    '''
    if uncert:  # shown as n.nn(n)
        u = "%.1G" % uncert
        if "." in u:
            least = -len(u.split(".")[1])
        else:
            least = len(u)
        u = u.replace(".", "").lstrip("0")
        if "E" in u:
            u, exp = u.split("E")
            least = int(exp) - 1
        u = "(" + u + ")"
    else:  # shown by truncating at least significant digit
        u = ""
        least = mostsig(number) - sigfig + 1
    return least, u


def exact_number(number, delta):
    '''

    :param number:
    :param delta:
    :return:
    >>> exact_number(34, 1e-10)
    '34'
    >>> exact_number(Fraction(34, 13), 1e-10)
    '(34 / 13)'
    >>> exact_number(2.0000000000000004, 1e-10)
    '2'
    >>> exact_number(1.4142135623730951, 1e-10)
    '1.4142135623730951'
    >>> exact_number(-0.5000000000000001, 1e-10)
    '-(1 / 2)'
    '''
    if hasattr(number, 'denominator'):
        if number.denominator == 1:
            return "%d" % int(number)
        else:
            if number.numerator > 0:
                return "(%d / %d)" % (number.numerator, number.denominator)
            return "-(%d / %d)" % (-number.numerator, number.denominator)
    if int(number) and abs(number) - abs(int(number)) < delta:
        return "%d" % int(number)
        #raise_QuantError('What a crazy coincidence', '', None)
    a = Fraction(number).limit_denominator()
    if a.numerator:
        discr = number * a.denominator / a.numerator
        if a.denominator < 10000 and 1.00000001 > discr > 0.99999999:
            if a.numerator > 0:
                return "(%d / %d)" % (a.numerator, a.denominator)
            return "-(%d / %d)" % (-a.numerator, a.denominator)
    return ascii_number(number, 17, 0.0, delta)


def number2quantity(text):
    '''
    turns a number string into a quantity. The main task is to determine the uncertainty.
    :param text: the number string
    :return: the quantity Q()
    >>> number2quantity('4.513')
    Q(4.513, units=Units(), uncert=0.001)
    >>> number2quantity('0.037')
    Q(0.037, units=Units(), uncert=0.001)
    >>> number2quantity('1000.')
    Q(1000.0, units=Units(), uncert=1.0)
    >>> number2quantity('50000')
    Q(50000, units=Units(), uncert=0.0)
    >>> number2quantity('2.51e89')
    Q(2.51e+89, units=Units(), uncert=1e+87)
    >>> number2quantity('4.53(7)')
    Q(4.53, units=Units(), uncert=0.07)
    '''
    text = text.strip()
    mult = 1
    if "(" in text and ")" in text:
        before, tmp = text.split("(")
        uncert, after = tmp.split(")")
        text = before + after
        mult = float(uncert)
    if '/' in text:
        numerator, denominator = text.split('/')
        return Q(Fraction(int(numerator), int(denominator)), "", uncert=0)  # pure fraction such as 1/2
    try:
        f = int(text)
    except ValueError:
        #print('converting', text)
        f = float(text)
        # f = mpmath.mpf(text)
    '''if math.isinf(f) or math.isnan(f):
        raise OverflowError(text)
    '''
    text = text.lower().lstrip("-0")
    expo = 0
    if "e" in text:
        text, expotext = text.split("e")
        expo = int(expotext)
    if "." in text or mult != 1:  # there is info on uncertainty
        if "." in text:
            before, after = text.split(".")
            expo -= len(after)
        # return Q(f, "", uncert=mpmath.mpf("1e%s" % expo) * mult)
        return Q(f, "", uncert=float("1e%s" % expo) * mult)
    return Q(f, "", uncert=0.0)


def latex_name(name):
    """
    adds chemistry mark up to bracketed text and turns text following _ into subscript
    :param name:
    :return:
    """
    name = name + '_' #protects against .split('_') failing
    if name.startswith('[') or name.startswith('Δ['): #format leading [] as concentration
        if name[0] != 'Δ':
            head, tail = name[1:].rsplit(']', 1)
            head = r'[\ce{%s}]' % head
        else:
            head, tail = name[2:].rsplit(']', 1)
            head = r'Δ[\ce{%s}]' % head

    else:
        if '[' in name: # turn internal [] into marked-up subscripts
            before, inside, after = re.match(r'([^[]+)\[(.*)\]([^]]*)', name).groups() # separates bracketed material
            name = r'%s_\ce{%s}_%s' % (before, inside, after)
        head, tail = name.split('_', 1)
        if len(head) > 1: # special cases like v12 (=> v_12) and roman multiple letter symbol
            if re.match(r'^.[0-9]+$', head): # single character following by integer, i.e. v0
                head, tail = name[:1], name[1:]
            elif re.match(r'^Δ.[0-9]+$', head):  # single character following by integer, i.e. v0
                head, tail = name[:2], name[2:]
            elif sum(1 for c in head if c in string.ascii_letters) > 1 :
                head = r'\mathrm{%s}' % head.replace('&', r'\&').replace('%', r'\%').replace('$', r'\$')
    subscripts = re.findall(r'(\\ce{.*}|[^_]+)_', tail) # tail.split('_') but ignoring underscore within chem mark-up
    head = head.replace('ᵣ','_r')
    if subscripts:
        if len(subscripts) == 2  and subscripts[1] and (len(subscripts[0]) == 1 or '\\ce{' in subscripts[0]):
            return head + r'_{\mathrm{' + ','.join(subscripts) + '}}'
        return head + r'_{\mathrm{' + '\ '.join(subscripts) + '}}'
    return head


def inherit_binary(q1, q2):
    prefu = q1.prefu | q2.prefu
    provenance = (q1, q2)
    return prefu, provenance


opprio = collections.defaultdict(int)
opprio["%s ^ %s"] = 5
opprio["%s * %s"] = 3
opprio["%s / %s"] = 3
opprio["%s + %s"] = 2
opprio["-%s"] = 3
opprio["%s - %s"] = 2

known_units = dict(
    A=(1, Units(A=1)),
    g=(Fraction(1, 1000), Units(kg=1)),
    Da=(1.660539040E-27, Units(kg=1)),
    m=(1, Units(m=1)),
    cm=(Fraction(1, 100), Units(m=1)),
    s=(1, Units(s=1)),
    mol=(1, Units(mol=1)),
    K=(1, Units(K=1)),
    Cd=(1, Units(Cd=1)),
    N=(1, Units(kg=1, m=1, s=-2)),
    J=(1, Units(kg=1, m=2, s=-2)),
    eV=(1.602176565e-19, Units(kg=1, m=2, s=-2)),
    V=(1, Units(A=-1, kg=1, m=2, s=-3)),
    C=(1, Units(A=1, s=1)),
    L=(Fraction(1, 1000), Units(m=3)),
    M=(1000, Units(mol=1, m=-3)),
    Pa=(1, Units(kg=1, m=-1, s=-2)),
    Hz=(1, Units(s=-1)),
    atm=(101325, Units(kg=1, m=-1, s=-2)),
    mmHg=(133.322368421, Units(kg=1, m=-1, s=-2)),
    torr=(133.322368421, Units(kg=1, m=-1, s=-2)),
    min=(60, Units(s=1)),
    h=(3600, Units(s=1)),
    W=(1, Units(kg=1, m=2, s=-3)),
    parsec=(3.085677581e16, Units(m=1)),
)

known_units["Ω"] = (1.0, Units(A=-2, kg=1, m=2, s=-3))
known_units["$"] = (1.0, Units(dollar=1))
known_units["Å"] = (Fraction(1, 10000000000), Units(m=1))
known_units["％"] = (Fraction(1, 100), Units())

metric_prefices = dict(
    f=Fraction(1, 1000000000000000),
    p=Fraction(1, 1000000000000),
    n=Fraction(1, 1000000000),
    u=Fraction(1, 1000000),
    m=Fraction(1, 1000),
    k=1000,
    M=1000000,
    G=1000000000,
    T=1000000000000)

metric_prefices['μ'] = Fraction(1, 1000000)

unitquant = {}
for unit, meaning in known_units.items():
    unitquant[unit] = Q(meaning[0], unit, meaning[1], prefu=[unit])
    if unit in ["cm", "h", "d", "atm", "kg", "min", "mmHg", "$"]:
        continue
    for prefix in metric_prefices:
        punit = prefix + unit
        unitquant[punit] = Q(meaning[0] * metric_prefices[prefix], punit, meaning[1], prefu=[punit])


def qabs(m):
    return Q(abs(m.number), "absolute(%s)", m.units, m.uncert, m.prefu, (m,))


def unit_mismatch(a):
    units = a[0].units
    for q in a:
        if units != q.units:
            return q
    if '°aC' in a[0].prefu:
        for q in a:
            if '°aC' not in q.prefu:
                raise_QuantError("If one temperature is in absolute degC, all others have to be as well", "average(%s...%s)", (a[0], q))
    else:
        for q in a:
            if '°aC' in q.prefu:
                raise_QuantError("If one temperature is in absolute degC, all others have to be as well", "average(%s...%s)", (a[0], q))
    return None


def qmin(*a):
    q = unit_mismatch(a)
    if q: raise_QuantError("Can't compare quantities with different dimensions", "min(%s, ... %s)", (a[0], q))
    if len(a) == 1:
        raise_QuantError("min take at least two arguments", "min(%s)", a)
    m = min(*a, key=lambda x: x.number)
    return Q(m.number, "min(%s)" % ", ".join(["%s"] * len(a)), m.units, m.uncert, m.prefu, tuple(a))


def qmax(*a):
    q = unit_mismatch(a)
    if q: raise_QuantError("Can't compare quantities with different dimensions", "max(%s, ... %s)", (a[0], q))
    m = max(*a, key=lambda x: x.number)
    return Q(m.number, "max(%s)" % ", ".join(["%s"] * len(a)), m.units, m.uncert, m.prefu, tuple(a))


def qaverage(*a):
    q = unit_mismatch(a)
    if q: raise_QuantError("Can't average quantities with different dimensions", "average(%s, ... %s)", (a[0], q))
    q0 = a[0] - a[0]
    m = sum(a, q0) / Q(len(a))
    if '°aC' in a[0].prefu:
        m.prefu.add('°aC')
    return Q(m.number, "avg(%s)" % ", ".join(["%s"] * len(a)), m.units, m.uncert, m.prefu, tuple(a))


def qsum(*a):
    q = unit_mismatch(a)
    if q: raise_QuantError("Can't add quantities with different dimensions", "sum(%s, ... %s)", (a[0], q))
    zero = Q(0)
    zero.units = a[0].units
    m = sum(a, zero)
    return Q(m.number, "sum(%s)" % ", ".join(["%s"] * len(a)), m.units, m.uncert, m.prefu, tuple(a))



def check_argument(f):
  def f_(*args, **kw):
    fn= f.__name__[1:]
    if len(args) > 1:
        raise_QuantError("This function cannot have more than one argument", fn + "(%s,%s ...)", (args[0],args[1]))
    if args[0].units != unity:
        raise_QuantError("Can't apply function to quantity with units", fn + "(%s)", (args[0],))
    try:
        return f(*args, **kw)
    except OverflowError:
        raise_QuantError("The result is too large for this calculator", fn + "(%s)", (args[0],))
    except ValueError:
        raise_QuantError("The argument of the function is outside of the allowed range (negative?)", fn + "(%s)", (args[0],))
  return f_


@check_argument
def qexp(a):
    number = math_exp(a.number)
    return Q(number, "exp0(%s)", a.units, abs(a.uncert * number), a.prefu, (a,))


def qsqrt(a):
    '''if a.number < 0.0:
        raise_QuantError("Won't take square root of negative number", "sqrt(%s)", (a,))
    '''
    answer = a ** Q('1/2')
    answer.name = "sqrt(%s)"
    answer.provenance = (a,)
    return answer


@check_argument
def qlog(a):
    return Q(math_log10(a.number), "log(%s)", a.units, abs(a.uncert / a.number), a.prefu, (a,))


@check_argument
def qln(a):
    return Q(math_log(a.number), "ln(%s)", a.units, abs(a.uncert / a.number), a.prefu, (a,))


@check_argument
def qsin(a):
    return Q(math_sin(a.number), "sin(%s)", a.units, abs(a.uncert * math_cos(a.number)), a.prefu, (a,))


@check_argument
def qcos(a):
    return Q(math_cos(a.number), "cos(%s)", a.units, abs(a.uncert * math_sin(a.number)), a.prefu, (a,))


@check_argument
def qtan(a):
    number = math_tan(a.number)
    return Q(number, "tan(%s)", a.units, a.uncert * (1 + number ** 2), a.prefu, (a,))

@check_argument
def qasin(a):
    return Q(math_asin(a.number), "asin(%s)", a.units, a.uncert, a.prefu, (a,))


@check_argument
def qacos(a):
    return Q(math_acos(a.number), "acos(%s)", a.units, a.uncert, a.prefu, (a,))


@check_argument
def qatan(a):
    number = math_atan(a.number)
    return Q(number, "atan(%s)", a.units, a.uncert, a.prefu, (a,))



def quad(A, B, C):
    BB = B ** Q(2)
    AC4 = Q(4) * A * C
    if BB.units != AC4.units:
        raise_QuantError("B * B has to have the same units as 4 * A * C ", "quad(%s, %s, %s)", (A, B, C))
    discriminant = BB - AC4
    if discriminant.number < 0:
        raise_QuantError("discriminant %f is negative, can't take its root" % discriminant.number, "quad(%s, %s, %s)",
                         (A, B, C))
    root = qsqrt(discriminant)
    sol_big, sol_small = (-B + root) / (Q(2) * A), (-B - root) / (Q(2) * A)
    if B.number > 0:
        sol_big, sol_small = sol_small, sol_big
    if abs(abs(B.number) - root.number) < 0.000001:
        sol_big_temp = Q(sol_big.number, uncert=sol_big.uncert, units=sol_big.units, prefu=sol_big.prefu)
        sol_big_temp.provenance = (A, B, C)
        sol_big_temp.name = "(quadp(%s, %s, %s))"
        sol_small = C / A / sol_big_temp
    return sol_big, sol_small


def qquadp(A, B, C):
    return quad(A, B, C)[0]


def qquadn(A, B, C):
    return quad(A, B, C)[1]


def qmoredigits(a):
    return Q(a.number, "moredigits(%s)", a.units, a.uncert / 100000., a.prefu, [a])


def quncertainty(a):
    return Q(a.uncert, "uncertainty(%s)", a.units, a.uncert / 100000., a.prefu, [a])


Kelvin = Q("K")
Kelvinshift = Q("273.15") * Kelvin


def qFtoKscale(a):
    if a.units == unity and not a.provenance:
        Kscale = (a - Q(32)) * Q('5/9') * Kelvin + Kelvinshift
        Kscale.provenance = (a,)
        Kscale.name = "\\mathrm{FtoKscale}(%s)"
        if Kscale.number < 0:
            raise_QuantError("Input temperature is lower than absolute zero", "text{FtoKscale}(%s)", (a,))
        return Kscale
    else:
        raise_QuantError("Input temperature has to be a unit-less number", "text{FtoKscale}(%s)", (a,))


def qCtoKscale(a):
    if a.units == unity and not a.provenance:
        Kscale = a * Kelvin + Kelvinshift
        if Kscale.number < 0:
            raise_QuantError("Input temperature is lower than absolute zero", "text{CtoKscale}(%s)", (a,))
        Kscale.name = "\\mathrm{CtoKscale}(%s)"
        Kscale.provenance = (a,)
        return Kscale
    else:
        raise_QuantError("Input temperature has to be a unit-less number", "text{CtoKscale}(%s)", (a,))


functions = dict(
    sin=qsin,
    cos=qcos,
    tan=qtan,
    asin=qasin,
    acos=qacos,
    atan=qatan,
    exp=qexp,
    sqrt=qsqrt,
    log=qlog,
    ln=qln,
    quadp=qquadp,
    quadn=qquadn,
    min=qmin,
    max=qmax,
    abs=qabs,
    CtoKscale=qCtoKscale,
    FtoKscale=qFtoKscale,
    moredigits=qmoredigits,
    uncertainty=quncertainty,
    avg=qaverage,
    sum=qsum,
)
unit_list = []

class X(object):
    '''quantity without value'''
    def __init__(self, number, name = '', units=unity, uncert=0.0, prefu=set(), provenance = None):
        try:
            number + 1.0
            self.number = number
            self.units = Units(*units)
            self.name = name[:]
            self.prefu = set(prefu)
            self.uncert = uncert
            self.provenance = provenance
        except TypeError:
            try:
                if number in unitquant:
                    q = unitquant[number]
                else:
                    q = number2quantity(number)
                self.__dict__ = q.__dict__
            except:
                self.number = None
                self.uncert = None
                self.name = number
                self.provenance = provenance
                self.units = unity
                self.prefu = set()
    def setdepth(self):
        if not hasattr(self, "depth"):
            if not self.provenance:
                self.depth = 0
            else:
                self.depth = 1 + max(child.setdepth() for child in self.provenance)
                if self.name == "-%s" or self.name == '%s':
                    self.depth -= 1
        return self.depth

    def __add__(self, other):
        return X('%s + %s', provenance=(self, other))
    def __sub__(self, other):
        return X('%s - %s', provenance=(self, other))
    def __mul__(self, other):
        return X('%s * %s', provenance=(self, other))
    def __truediv__(self, other):
        return X('%s / %s', provenance=(self, other))
    def __neg__(self):
        return X('- %s', provenance=(self,))
    def __pos__(self):
        return X('+ %s', provenance=(self,))
    def __pow__(self, other):
        return X('%s ^ %s', provenance=(self, other))

    def steps(self, level, writer, subs=None, flaigs=()):
        if not self.provenance:
            return writer(self, showvalue=False, flags=flaigs)
        name = self.name
        children = [child(index, level, name, q, subs, writer, flaigs, 0) for index, q in enumerate(self.provenance)]
        if subs and name in subs:
            name = subs[name]
        if len(subs) > 6 and name[:6] in ['avg(%s', 'sum(%s', 'min(%s', 'max(%s', 'avg(%s']:
            name = name.replace(name[:6], subs[name[:6]])
        return name % tuple(children)

    def __repr__(self):
        if self.name in unitquant and self.__dict__ == unitquant[self.name].__dict__:
            return u"Q('%s')" % self.name
        if repr(self.number).startswith("inf"):
            raise OverflowError(self.number)
        symbols = ["A", "kg", "m", "s", "mol", "K", "Cd", "dollar"]
        self.runits = "Units(" + ",".join("%s=%s" % (x[0], repr(x[1])) for x in zip(symbols, self.units) if x[1]) + ")"

        if self.provenance:
            return u"X(%(number)r, '%(name)s', %(runits)s, %(uncert)r, %(prefu)s, %(provenance)s)" % self.__dict__
        if self.prefu:
            return u"X(%(number)r, '%(name)s', %(runits)s, %(uncert)r, %(prefu)s)" % self.__dict__
        if self.name:
            rr = u"X(%(number)r, '%(name)s', %(runits)s, %(uncert)r)" % self.__dict__
            return rr
        return u"X(%(number)r, units=%(runits)s, uncert=%(uncert)r)" % self.__dict__

def qfunc(a, *b):
    return functions[a](*b)

def xfunc(a, *b):
    if len(b) == 1:
        return X(('%s' % a)+'(%s)', provenance=tuple(b))
    return X(('%s' % a) + '(' + ', '.join(["%s"] * len(b))+ ')', provenance=tuple(b))

if __name__ == "__main__":
    x = eval("X('c0') / ((X('[MgCl2]')) + X('b')) + X('3.5E+3')")
    x.setdepth()
    print(x.steps(-1, latex_writer, subs=''))

    g5 = Q(4.5, u'blaν', Units(m=1), 0.1)
    print(g5)
    print(str(g5))
    rr = repr(g5)
    print(rr)
    print('%s' % g5.name)

""" Tests and ideas

c = 7 (g m)/(mol s)

calc([],["f = 3.4 mg + 20 s"],True)

unitquant[kg]

Quantity(3.5)
Quantity("3.5")
Quantity("kg")

figure_out_name("fg90 = 3.4 mg", [], [])

calc([],["f = 3.4 mg", "m = 20 s"],False)

text = "24.5e-65 kg/m/s^2 / g0 + t0^2 + log(x0)"
tokens = scan(text)
triple_tokens = make_triple_tokens(tokens)
stripped = "".join(t[1] if t[0]=="O" else "%*s" % (len(t[1]),t[1]) for t in tokens)
shortcut = "".join(t[1] if t[0]=="O" else "%*s" % (len(t[1]),t[0]) for t in tokens)
triple_shortcut = "".join(t[1]+("%*s" % (len(t[2]),t[0])) for t in triple_tokens)
print(text)
print(tokens)
print(stripped)
print(shortcut.replace("O","*"))
print(triple_shortcut)
i = create_Python_expression(triple_tokens, dict(g0="g_val", t0="t_val", x0="x_val"))
print (i)


"""

