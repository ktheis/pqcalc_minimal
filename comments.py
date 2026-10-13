"""
comments.py

Everything to find math and chemistry in comments, mark it up and add links

Call tree:

create_comment(a, state): a starts with '!@#' or failed to compute
    displayed_chemical_equation (a, state): a starts with '!'
    displayed_algebra(a, state): a starts with '@'
    markup_comment
        markup_math
            split_at_equal
            left_of_equal
            right_of_equal
                symbolish
            scan_comment
            markup_all_but_math
            -> create_Python_expression, make_paired_tokens, scan
        markup_all_but_math
            autodetect
                endparen
                equal_score
                wordscore
                symbolscore
                scinot_score
                int_score
                formula_score
                    elementor
            format_image
            mysplit3
            format_natural_language
            -> latex_name, latex_number
         split_at_equal
         autodetect...
         mysplit2
         format_image...
extract_knowns
     -> scan_it, interpret

"""

from mathparser import interpret, scan, scan_it, scan_comment, make_paired_tokens, \
    create_Python_expression
from chemistry import PSE, typical_units_reverse
import quantities
from quantities import Q, X, unitquant, Units, latex_name, latex_number, latex_writer
#import calculator # access to State
from fractions import Fraction
from collections import OrderedDict


class BareState(OrderedDict):
    def __init__(self, memory=None, mob=None):
        OrderedDict.__init__(self)
        self.flags = set()
    def printit(self, *args, **kwargs):
        pass


'''
The concentration of CaCl2 in the solution is 1.5e-12 mol/L
                     !!!!!                    mmmmmmmmmmmmm

The reaction HOH -> H+ + OH- proceeds very quickly
             !!!!!!!!!!!!!!!

The relation is c = n/V, where n is the chemical amount of solute
                mm=mmmm

The bla (n0 refers to the ground state) occurs
         mm


Chemistry: enclose in mhchem tags and hope for the best
Math: interpret using X()

'''

def create_comment(a, state):
    """

    :param a: user input
    :param state: contains known quantities as ordered dict, along with flags and output
    :return: none (comment is written to state)
    """
    if 'plain math' in state.flags:
        result = a
    elif a.startswith("!"):
        result = displayed_chemical_equation(a, state)
    elif a.startswith("#"):
        result = '<span style="font-size:12pt;">%s</span>' % a[1:]
    elif a.startswith("@"):
        result = displayed_algebra(a, state)
    else:
        result = markup_comment(a)
    state.printnlog(result)


def displayed_algebra(a, state):
    if len(state.output) < 2 or not state.output[-2].endswith('>'):
        state.printnlog('<br>')
    out = []
    add = ''
    try:
        first = a[1:].split()[0]
        if first.startswith('[') and first.endswith(']') and len(first) < 12:
            a = a[len(first):]
            add = first[:]
    except:
        add = ''
    comment = ''
    if '@' in a[1:]:
        a, comment = a.rsplit('@', maxsplit=1)
    splitters = []
    inbetween = []
    bracket = 0
    for c in a[1:]:
        if c in '=≥≤<>' and bracket == 0:
            splitters.append(c)
            inbetween.append('=')
        else:
            inbetween.append(c)
            if c == '[':
                bracket += 1
            elif c == ']':
                bracket -= 1
    inbetween = ''.join(inbetween)
    for exp0 in inbetween.split('='):
        comment = format_math(comment, exp0, out)
    comment = markup_comment(comment, toplevel=False)
    raw = a[1:] + '\\n'
    result = []
    for e,o in zip(out, splitters):
        result.append(e)
        result.append(' ' + o + ' ')
    result.append(out[-1])
    result = ''.join(result)
    cl = clickable(raw, ' \\(%s\\)' % result)
    return '''<div style="font-size:12pt; display: flex; justify-content: space-between;"><div>%s</div><div>%s &nbsp;&nbsp;&nbsp;&nbsp; %s</div><div></div></div>''' %(add, cl, comment)
    cl = clickable(raw, ' \\(%s\\)</span>&nbsp;&nbsp;%s' % (' = '.join(out), comment))
    return add+'<div style="font-size:12pt; text-align: center;">%s</div>' % cl


def format_math(comment, exp0, out):
    if not exp0.strip():
        out.append('')
        return
    try:
        paired, comment2 = make_paired_tokens(scan(exp0))
        expression = create_Python_expression(paired, BareState(), free_expression=True, warning=False)
        x = eval(expression)
        x.setdepth()
        out.append(x.steps(-1, quantities.latex_writer, subs=latex_subs))
        return comment2 + comment
    except:
        out.append('Failed to interpret math QQQ' + exp0 + 'QQQ')
        return exp0 + comment


def displayed_chemical_equation(a, state):
    cond = len(state.output) < 2 or not state.output[-2].endswith('>')
    if cond:
        state.printnlog('<br>')
    add = ''
    app = ''
    try:
        first = a[1:].split()[0]
        if first.startswith('[') and first.endswith(']') and len(first) < 12:
            a = a[len(first):]
            add = first[:]
        if '!' in a[1:]:
            a, app = a.rsplit('!', maxsplit=1)
            app = '             ' + app
    except:
        add = ''
        app = ''
    result = chemeq_addlinks(a[1:], '__negreact__' in state.flags)
    if app:
        app = '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;' + markup_comment(app, toplevel=False)
    return ('''<div style="font-size:12pt; display: flex; justify-content: space-between;"><div>%s</div><div>%s %s</div><div></div></div>''' %
        (add, result, app))


def markup_comment(b, toplevel=True):
    '''
    Find chemistry and math in text and mark it up.
    Used for entire input line (toplevel=True), and for comments after second @ or !
    autodetect returns N=i!._ when it detects scientific notation, equal sign, integer, chemistry, plain word or quantity name
    '''

    try:
        #rint('markup_commment: ', b)
        #separate out into chemical equations and the rest
        listt = [item for word in split_at_blank(b) for item in autodetect(word)]
        if any(item[0] == '!' for item in listt):
            newlist = []
            formula = ''
            while listt:
                current = listt.pop(0)
                if current[0] == '!':
                    if not formula and newlist and newlist[-1][0] == 'i':
                        formula = newlist.pop()[1]
                    formula = formula + current[1]
                elif formula and current[0] == 'N':
                    formula = formula + current[1]
                elif formula and current[1] == '+ ' and listt and listt[0][0] in '!i':
                    formula = formula + current[1] + listt.pop(0)[1]
                else:
                    if formula:
                        newlist.append(('!', formula))
                        formula = ''
                    newlist.append(current)
            if formula:
                newlist.append(('!', formula))
            listt = newlist[:]
        for i, item in enumerate(listt):
            if item[1].startswith('http://') or item[1].startswith('https://'):
                listt[i] = ('<', '<a href="%s" target="_blank">%s</a>' % (item[1], item[1]))
        newlist = []
        math = ''
        #rint('first pass:', '|'.join(':'.join(item) for item in listt))
        #separate math from chemistry, html, and {} image tags
        while listt:
            current = listt.pop(0)
            if current[0] in '!<{':
                if math:
                    newlist.append(('.', math))
                    math = ''
                newlist.append(current)
            else:
                math = math + current[1]
        if math:
            newlist.append(('.', math))
        #rint('second pass:', '|'.join(':'.join(item) for item in newlist))
        listt = newlist[:]
        result = []
        for i, item in enumerate(listt):
            if item[0] == '<':
                result.append(item[1])
            elif item[0] == '{':
                result.append(format_image(item[1]))
            elif item[0] == '!':
                if item[1].endswith(' '):
                    item = (item[0], item[1][:-1])
                    blank = ' '
                else:
                    blank = ''
                result.append(clickable('['+item[1]+']', '\\(\ce{%s}\\)%s' % (item[1], blank)))
            elif len(list(split_at_equal(item[1]))) > 1:
                result.append(markup_math(item[1]))
            else:
                result.append(markup_all_but_math(item[1]))
        if toplevel and len(result) == 1 and 'insertAtCaret' in result[0] and result[0][0] == '<' and result[0][-1] == '>':
            result[0] = '<div style="font-size:12pt; text-align: center;">%s</div>' % result[0]
        #rint('third pass:', '|'.join(result))
        return ''.join(result)
    except ZeroDivisionError:
        return(b)


def markup_math(text):
    '''
    text contains math that needs to be marked up
    equations are of the form: middle LHS = RHS middle LHS = RHS middle
    text is first split at equal signs, and then blocks of RHS middle LHS are processed
    right_of_equal() and left_of_equal() consume items in block, leaving middle if any
    '''
    comment = []
    listt = list(split_at_equal(text))
    for i, block in enumerate(listt):
        scanned, remainder = scan_comment(block)
        if scanned and i:
            RHS = right_of_equal(scanned)
            try:
                out = []
                for exp0 in LHS, RHS:
                    format_math('', exp0, out)
                cl = clickable(LHS + ' = ' + RHS + '\\n', '\\(%s\\)' % ' = '.join(out))
                comment.append('''<span style="font-size:12pt; text-align: center;">%s</span>''' % cl)
            except ZeroDivisionError:
                raise
        if scanned and i < len(listt) - 1:
            LHS = left_of_equal(scanned)
        else:
            LHS = ''
        if scanned:
            middle = ''.join(t for o, t in scanned)
            if middle:
                comment.append(markup_all_but_math(middle))
        middle = None
    if middle:
        comment.append(markup_all_but_math(middle))
    return ''.join(comment)


def split_at_blank(line):
    if not line:
        return ''
    openers = '"{<'
    closers = {'{':'}', '"': '"', '<': '>', '[': ']'}
    curword = []
    closewith = None
    for c in line:
        if closewith == c:
            curword.append(c)
            yield ''.join(curword)
            curword = []
            closewith = None
        elif not closewith and c in openers and closers[c] in line:
            if curword:
                yield ''.join(curword)
            curword = [c]
            closewith = closers[c]
        elif not closewith and c == ' ' and curword:
            yield ''.join(curword) + ' '
            curword = []
        else:
            curword.append(c)
    if curword:
        yield ''.join(curword)


def split_at_equal(line):
    openers = '"{<'
    closers = {'{':'}', '"': '"', '<': '>', '[': ']'}
    curword = []
    closewith = None
    for c in line:
        if closewith == c:
            closewith = None
        elif not closewith and c in openers and closers[c] in line:
            closewith = closers[c]
        if not closewith and c == '=':
            yield ''.join(curword)
            curword = []
        else:
            curword.append(c)
    if curword:
        yield ''.join(curword)


def clickable(paste, text):
    return '''<span onclick="insertAtCaret('commands','%s', '0')">%s</span>''' % (paste, text)


def markup_all_but_math(line):
    """

    :param line: String containing the comment
    :return: String with variables and chemistry marked-up in LateX
    autodetect returns N=i!._ when it detects scientific notation, equal sign, integer, chemistry, plain word or quantity name

    """
    interpretation = []
    for item in (it for word in split_at_punctuation(line) for it in autodetect(word)):
        if item[0] == "!":
            interpretation.append('\\(\\ce{%s}\\)' % item[1])
        elif item[0] == "{":
            interpretation.append(format_image(item[1]))
        elif item[0] == "N":
            if 'E' in item[1] or 'e' in item[1]:
                numbertext = '\\(' + latex_number(item[1]) + '\\)'
            else:
                numbertext = item[1]
            interpretation.append(clickable(item[1], numbertext))
        elif item[0] == "i":
            numbertext = item[1]
            if not '.' in numbertext:
                numbertext = numbertext.rstrip() + '.'
            interpretation.append(clickable(numbertext, item[1]))
        elif item[0] == "_":
            try:
                delim = ' ' if item[1].endswith(' ') else ''
                interpretation.append(clickable(item[1], '\\(%s\\)%s' % (latex_name(item[1].rstrip()), delim)))
            except:
                interpretation.append(item[1])
        else:
            interpretation.append(format_natural_language(item[1]))
    return ''.join(interpretation)


def autodetect(b2):
    if b2.endswith(' '):
        trailing_blank = ' '
        a = b2.rstrip()
    else:
        trailing_blank = ''
        a = b2[:]
    if b2 and b2[0] in '{[<"':
        yield (b2[0], b2)
        return
    delim = ''
    frontdelim = ''
    if not a:
        yield (' ', ' ')
        return
    if a[-1] in '.,?' or endparen(a):
        delim = a[-1]
        a = a[:-1]
        if a and endparen(a):
            delim = ')' + delim
            a = a[:-1]
    if not a:
        yield (')', delim+trailing_blank)
        return
    if a[0] == '(' and ')' not in a:
        frontdelim = '( '
        a = a[1:]
    if not a:
        yield ('(', frontdelim + delim)
        return
    b = [(scinot_score(a), 'N'), (equal_score(a), '='), (int_score(a), 'i'),
         (formula_score(a), '!'), (wordscore(a), '.'), (symbolscore(a), '_')]
    if a == 'CO':
        pass #rint(b)
    b.sort(key=lambda x: -x[0])
    if delim:
        delim = delim + trailing_blank
        trailing_blank = ''
    if frontdelim:
        yield ('(', '(')
    yield(b[0][1], a+trailing_blank)
    if delim:
        yield (')', delim)


def split_at_punctuation(line): # in the absence of equations
    openers = '"{<'
    closers = {'{':'}', '"': '"', '<': '>', '[': ']'}
    curword = []
    closewith = None
    for ci, c in enumerate(line):
        if closewith:
            curword.append(c)
            if closewith == c:
                yield ''.join(curword)
                curword = []
                closewith = None
            continue
        if c in openers and closers[c] in line:
            if curword:
                yield ''.join(curword)
            curword = [c]
            closewith = closers[c]
        elif c in ' ?).' and curword:
            if c == ')' and ci < len(line)-1 and not line[ci+1] in ' .?':
                curword.append(c)
            elif c == '.' and curword[-1].isdigit and ci < len(line)-1 and line[ci+1] != ' ':
                curword.append(c)
            else:
                curword.append(c)
                yield ''.join(curword)
                curword = []
        elif curword and curword[0] in ' ?).' and c != ' ':
            yield ''.join(curword)
            curword = [c]
        else:
            curword.append(c)
    if curword:
        yield ''.join(curword)


tests = '''
Where is the <bold>NaCl<unbold> in the mixture (glucose plus alanine)?
Here the number is 3.452e-4 (tomorrow and (NH4)2SO4) and stuff'''.splitlines()

for line in tests:
    pass#rint('|'.join(a for a in mysplit3(line)))



def format_image(text):
    return '<img src=%s>' % text[1:-1]


def format_natural_language(word):
    charlist = list(word)
    cl2 = []
    while charlist:
        c = charlist.pop(0)
        if c == " " and cl2 and cl2[-1] == ' ':
            cl2.append("&nbsp;")
        else:
            cl2.append(c)
    return "".join(cl2)



'''element_regex = r'[BCFHIKNOPSUVWY]|[ISZ][nr]|[ACELP][ru]|A[cglmst]|B[aehikr]|C[adefl-os]|D[bsy]|Es|F[elmr]|G[ade]|H[efgos]|Kr|L[aiv]|M[cdgnot]|N[abdehiop]|O[gs]|P[abdmot]|R[abe-hnu]|S[bcegim]|T[abcehilms]|Xe|Yb'
'''

def elementor(t):
    text = t.replace('(aq)', 'Og').replace('(l)', 'Og').replace('(s)', 'Og').replace('(g)', 'Og')
    if text.endswith('-') or text.endswith('+'):
        text = text[:-1] + 'Ts'
    candidate = []
    textlist = list(text)
    while textlist:
        c = textlist.pop(0)
        if c.isdigit() or c in '+-()^':
            yield 0.5
        elif not c.isupper():
            candidate.append(c)
            if textlist:
                continue
        cc = ''.join(candidate)
        if cc in PSE:
            yield 1
        elif cc:
            yield -len(candidate)/2
        candidate=[]
        if c.isupper():
            candidate = [c]
    cc = ''.join(candidate)
    if cc in PSE:
        yield 1


def formula_score(text):
    if text == 'H+' or text == '->' or text == '<=>' or text in '(s) (l) (g) (aq)'.split():
        return 1
    nritems = score = 1
    elements = 0
    for u in elementor(text):
        nritems += abs(u)
        score += u
        if u == 1.0:
            elements += 1
    if not elements:
        return 0.0
    if elements == 1 and not any(c.isdigit() for c in text):
        return 0.0
    if score == nritems:
        return 1.0
    return score/nritems


def int_score(text):
    if 'e' in text or 'E' in text:
        return 0.0
    try:
        i = float(text)
        return 1.0
    except:
        return 0.0


def scinot_score(text):
    if text[0].isdigit and '.' in text:
        try:
            a = float(text)
            return 1
        except:
            pass
    return 0


def equal_score(text):
    if text.strip() == '=':
        return 1
    return 0


def wordscore(text):
    length = len(text)
    dings = 0
    vowel = 0
    for c in text:
        if c in "aeiouy":
            vowel += 1
        elif c.isdigit():
            dings = +1
    for c in text[1:]:
        if c.isupper():
            dings += 1
    if not vowel:
        dings += 1
    return max((length - dings)/length-0.1, 0.7)


def symbolscore(text):
    if '_' in text and not '/' in text:
        return 1.0
    if text.startswith('Δ'):
        return 1.0
    if '[' in text and ']' in text.split('[')[1]:
        return 1.0
    if len(text) == 2 and text[1].isdigit() and not text[0] in '+-0123456789':
        return 0.75
    return 0.0


def endparen(a):
    if a[-1] != ')':
        return False
    if a.count('(') - a.count(')') == -1:
        return True
    return False


latex_subs = {"%s * %s": "%s \\cdot %s",
            "%s / %s": "\\dfrac{%s}{%s}",
              "%s ^ %s": "{%s}^{%s}",
            "exp0(%s)": "e^{%s}",
            "exp(%s)": "\\mathrm{exp}(%s)",
            "log(%s)": "\\mathrm{log}(%s)",
            "ln(%s)": "\\mathrm{ln}(%s)",
            "sin(%s)": "\\mathrm{sin}(%s)",
            "cos(%s)": "\\mathrm{cos}(%s)",
            "tan(%s)": "\\mathrm{tan}(%s)",
            "sqrt(%s)": "\\sqrt{%s}",
            "quadn(%s": "\\mathrm{quadn}(%s",
            "quadp(%s": "\\mathrm{quadp}(%s",
            "avg(%s": "\\mathrm{avg}(%s",
            "min(%s": "\\mathrm{min}(%s",
            "sum(%s": "\sum (%s",
            "max(%s": "\\mathrm{max}(%s",
            "abs(%s)": "\\mathrm{abs}(%s)",
            "moredigits(%s)": "\\mathrm{moredigits}(%s)",
            "uncertainty(%s)": "\\mathrm{uncertainty}(%s)",
    }




def extract_knowns(text):
    """
    Generator for numerical data in a text
    :param text: The question text
    :yield: Commands to set numerical data
    """
    text = text.replace('<em>M</em>', 'M').\
        replace('×10', ' × 10').replace('−', '-').replace('<sup>', '^').\
        replace('10^', '10 ').replace('</sup>', '')
    while text:
        tokens, remainder = scan_it(text)
        if remainder and remainder.startswith('='):
            text = remainder[1:].strip()
        else:
            text = remainder
        ltokens = [[t[0], t[1]] for t in tokens]
        #rint(ltokens)
        for j, t in enumerate(ltokens): #first pass to find units
            if t[0] == 'I':
                punit = t[1]
                while punit and punit[-1] in '),.?':
                    punit = punit[:-1]
                if punit in unitquant:
                    ltokens[j][0] = 'U'
                    ltokens[j][1] = punit
                elif punit == '°C' or punit == '°aC':
                    ltokens[j][0] = 'U'
                    ltokens[j][1] = '°aC'
        shift = 0
        for j, t in enumerate(ltokens): #second pass to find number + unit
            if shift:
                shift -= 1
                continue
            if t[0] != 'N':
                continue
            known = t[1] + (' ' if '.' in t[1] else '. ')
            if len(ltokens) > j+7 and ltokens[j+1:j+5] == [['O', ''], ['I', '×'], ['O', ''], ['N', '10']]:
                known = known[:-1] + 'E' + ltokens[j+5][1]
                if ltokens[j+6][0] == 'N':
                    known += ltokens[j+6][1]
                shift = 6
            units = False
            for j2, t2 in enumerate(ltokens[j+1+shift:]):
                if t2[0] in 'OU' and t2[1] != ',':
                    known = known + t2[1]
                    units = True
                elif known.endswith('-') and t2[0] == 'N' and len(t2[1]) == 1 and t2[1] in '123':
                    known = known + t2[1]
                    shift += j2 + 1
                else:
                    break
            if units:
                while known and known[-1] in '),.?':
                    known = known[:-1]
                try:
                    q = interpret(known, BareState())
                    if q.units in typical_units_reverse:
                        yield(typical_units_reverse[q.units] + ' = ' + known)
                    else:
                        yield('Q1 = ' + known)
                except:
                    yield('Q2 = ' + known)
            else:
                yield('N = ' + known)



def symbolish(text):
    for t in text:
        if t in '_[0123456789':
            return True
    if len(text) == 1 and text not in '.!?,':
        return True
    return False


def left_of_equal(scanned):
    LHS = []
    best = None
    for i, item in enumerate(reversed(scanned)):
        if item[0] == 'I' and (not LHS or symbolish(item[1]) or (LHS and LHS[-1][0] == 'O' and LHS[-1][1] != ' ')):
            LHS.append(item)
            best = i
        elif item[0] == 'O':
            LHS.append(item)
        else:
            break
    if best:
        del(scanned[-best-1:])
        return ''.join(item[1] for item in reversed(LHS[:best+1]))
    return ''


def right_of_equal(scanned):
    RHS = []
    best = None
    leftover = None
    for i, item in enumerate(scanned):
        if item[0] == 'N' or (item[0] == 'I' and
             (not best or symbolish(item[1]) or item[1] in quantities.unitquant or
             (RHS and RHS[-1][0] == 'O' and RHS[-1][1] != ' '))):
            if item[0] == 'I' and item[1][-1] in '?.':
                leftover = item[1][-1]
                item = ('I', item[1][:-1])
            RHS.append(item)
            best = i
            if leftover:
                break
        elif item[0] == 'O' and ',' not in item[1]:
            RHS.append(item)
        else:
            break
    if best:
        del(scanned[:best+1])
        if leftover:
            scanned.append(('.', leftover))
        return ''.join(item[1] for item in RHS[:best+1])
    else:
        return ''


import re


def chemeq_addlinks(text, neg_react=True):
    if '->' not in text and '<=>' not in text:
        return clickable('!' + text, '\\(\\ce{%s}\\)' % text)
    species = re.split(r'(->(?:\[[^]]+\])?|<=>(?:\[[^]]+\])?| \+)', text)
    species.append('')
    answer = []
    sign = -1 if neg_react else 1
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
        else:
            name = ''
        stoich *= sign
        if sep.startswith('->') or sep.startswith('<=>'):
            sep = clickable('!' + text + '\\n', '\\(\\ce{%s}\\)' % sep)
            sign = 1
        else:
            sep = '''\\(\\ce{ %s }\\)''' % sep.strip()
        insert = 'ν[%s] = %d\\n' % (name, stoich)
        answer.append(clickable(insert, '\\(\\ce{%s}\\)' % s) + sep)
    return ''.join(answer)




if __name__ == '__main__':
    print(list(split_at_equal('Hello a = b and "c = d" is different')))
    print(chemeq_addlinks('MgCl2 -> Mg2+ + 2 Cl-'))
    text = 'This is a test with a = b and other stuff. The new sentence "bla = bla" starts <em>here</em>.'
    print(text)
    print('|'.join(split_at_blank(text)))
    print('|'.join(split_at_equal(text)))
    print('|'.join(split_at_punctuation(text)))

    a = '''The concentration of http://google.com/bla?asdf=5 calcium chloride, CaCl2, in the solution is 1.5e-12 mol/L
    The reaction HOH -> H+ + OH- (aq) proceeds very quickly when NaCl and CuBr2 are heated
    The relation is Cobalt = n/V, where n is the chemical amount of solute
    The bla (n0 refers to the ground state) occurs'''.splitlines()
    b = 'The concentration of MgCl2 -> Mg^2+ + 2 Cl- is calculated as c[MgCl2] = b * 3.14 mg * n[MgCl2] / V_solution'

    for line in a:
        print(markup_comment(line))


    task = '''for i in range(100000): calc("","dd = exp(45.34) / log(6.9654) \\n yy = 87 mg/uL", False)'''

    print(markup_math('When a0 = b0, c = 4.53 and d = 5.245.'))
    print(markup_comment('The formula is H2O. The name is water.'))

    for t in split_at_punctuation('. The name is water.'):
        print(t, list(autodetect(t)))

    print(list(autodetect('. ')))