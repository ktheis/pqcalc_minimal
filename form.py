# coding=utf-8
from quantities import functions, known_units
from html import escape, unescape
import urllib.parse

selector = '''
<select %s onchange="insertAtCaret('commands',this.options[this.selectedIndex].value, %s);">
  %s
</select>'''

selectoroption = '''
  <option value="%s">%s</option>'''

def fill_selector(header, choices, backup=0):
    html = ['<option value="" selected="selected" disable="disabled">%s</option>' % header]
    for term in choices:
        html.append(selectoroption % (term, term))
    return selector % ("", backup, "".join(html))

def fill_selector2(header, choices, backup=0):
    html = ['<option value="" selected="selected" disable="disabled">%s</option>' % header]
    for term in choices:
        html.append(selectoroption % (term[1], term[0]))
    return selector % ("", backup, "".join(html))


# unit selectors, pre-baked
unit_list = list(known_units.keys())+['°ΔC','°aC']
unit_list.sort(key=lambda x: x.lower())
unit_selector = fill_selector("units", unit_list)

# function selectors, pre-baked
function_list = [f + "()" for f in functions]
function_list.extend(["using  ", "in  "])
function_selector = fill_selector("functions", function_list, backup=1)

# special symbol selector, pre-baked
symbol_list = ["°","μ", "ΔHf°"," ％", "ν","Δ", "ℎνλ","ΔᵣG°","ρ","∞", "ΦΨ"]
symbol_selector = fill_selector("symbols", symbol_list)

def const_selectors(known):
    """ Make the selector for known quantities
    """
    constantlist = [
        ('Speed of light', 'c0 = 299792458 m/s\n'),
        ('Planck', 'ℎ = 6.62607015E-34 J s\n'),
        ('Avogadro', 'N_A = 6.02214076E23 /mol\n'),
        ('Boltzmann', 'k_B = 1.380649E-23 J/K\n'),
        ('Gas constant', 'R = 8.314463 J/(K mol)\n'),
        ('elem. charge', 'e = 1.602176634E-19 C\n'),
        ('Faraday', 'ℱ = 9.64853321e4 C/mol\n'),
        ]
    return fill_selector2("constants", constantlist)

example_template = '''
<h3>How to use PQcalc</h3>
<p>PQcalc is an online calculator for students learning science in college.
To learn how to use it by example, click on any of the tutorials below. A more comprehensive (but slightly outdated) documentation of
the program is  <a href="http://www.bioinformatics.org/pqcalc/manual">here</a>, and a paper describing the features is <a href="https://pubs.acs.org/doi/abs/10.1021/acs.jchemed.5b00366"> here </a>.

<h3>Help with General Chemistry</h3>
<a href="http:./ico/studytools.html">Study tools</a>
<h3>Tutorial topics</h3>%s
'''



def newform(result, oldlog, inputlog,
            browser=None, actualpref='', prefill="",
            action='.', button2='help', otherbuttons=('export', 'reset'),
            show_top=False, hints='', metadata=''):
    '''

    :param result: calculated results from user input - (verboselog, brieflog, memory, known, linespace)
    :param oldlog: work from previous calculations
    :param inputlog: all user input (previous and current)
    :param browser:
    :param actualpref: text to place in textarea
    :param prefill: reference to example input to place in textarea
    :param action: local url to visit after form submission
    :param button2: label on 2nd button
    :param otherbuttons: list of labels for other buttons
    :return: http of form
    '''

    # prepare text for hidden fields (log, memory, inputlog) and visible info (log)
    if not action:
        show_top = True
    verboselog, brieflog, memory, known, linespace = result
    log = escape(oldlog, quote=True) + "\n" + escape(brieflog, quote=True)
    out = unescape(oldlog) + verboselog
    memory = escape(memory, quote=True)
    inputlog = escape(inputlog, quote=True)
    hints = escape(hints, quote=True)
    # assemble widgets
    keyb = "" if browser else 'class="keyboardInput"'
    #selectors = quant_selectors(known)
    selectors = unit_selector + function_selector + symbol_selector + const_selectors(0)
    obut_text = ''.join('<input type="submit" name = "sub" value="%s" />\n' % but for but in otherbuttons)
    rows = 3
    if actualpref:
        prefill  = actualpref
        rows = max(3, len(prefill.split("\n")), len(prefill) // 80)
    logo = '' if verboselog else PQlogo
    #linespace = "100%"

    data = dict(output=out, memory=memory, rows=rows, selectors=selectors, logbook=log, keyboard=keyb,
                prefill=prefill, head=head, buttons=buttons, linespacing=linespace, logo=logo,
                inputlog=inputlog, action=action, button2=button2, obut_text=obut_text, hints=hints, metadata=metadata)
    if show_top:
        data['head'] = head_noscroll
        return template_noninteractive % data
    return template % data

def stripped(text):
    result = []
    html = False
    c_old = ' '
    for c in text:
        if c == '<':
            html = True
        elif c == '>' and c_old not in ['-', '=']:
            html = False
        elif not html:
            result.append(c)
        c_old = c
    r = '<pre>' + ''.join(result) + '</pre>'
    r = r.replace(r'\) \(','').replace(r'}\)\(\ce{', '').replace('\r\n\r\n\r\n', '\r\n')
    return r



def printableLog(symbols, logbook, inputlog):
    known = "\n".join([s + "=" + si.__str__() for s, si in symbols.items()])
    inputlog_hidden = escape(inputlog, quote=True)
    #logbook = logbook.replace(r'\(',' $').replace(r'\)','$ ').replace('$  $', '')
    return printable_view % (inputlog_hidden, escape(inputlog), known, logbook, stripped(logbook),
                             urllib.parse.quote(inputlog.encode('utf8')))




head = '''<head>
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="format-detection" content="telephone=no">
<meta name="viewport" content="width=device-width; initial-scale=0.8;">

<link rel="shortcut icon" href="/ico/favicon.ico">


<script type="text/javascript" id="MathJax-script" async
  src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js">
</script>

<script type="text/x-mathjax-config">
  MathJax.Hub.Config({
    "fast-preview": {disabled: true},
    tex2jax: {preview: ["[...]"]},
    TeX: { extensions: ["[Contrib]/mhchem/mhchem.js"] },
    "HTML-CSS": {size:90}
    });
</script>

<script type="text/javascript">

MathJax.Hub.Register.StartupHook("End",function () {
  document.getElementById('commands').scrollIntoView({behavior: "smooth"})
});

</script>

<script type="text/javascript">
function process(event) {
    if (event.keyCode == 13 ) {
        if (!event.shiftKey) document.forms["myform"].submit();
    }
}
</script>


<script type="text/javascript">
<!--

function insertAtCaret(areaId,text,backup) {
    var txtarea = document.getElementById(areaId);
    var scrollPos = txtarea.scrollTop;
    var strPos = 0;
    var br = ((txtarea.selectionStart || txtarea.selectionStart == '0') ?
        "ff" : (document.selection ? "ie" : false ) );
    if (br == "ie") {
        txtarea.focus();
        var range = document.selection.createRange();
        range.moveStart ('character', -txtarea.value.length);
        strPos = range.text.length;
    }
    else if (br == "ff") strPos = txtarea.selectionStart;

    var front = (txtarea.value).substring(0,strPos);
    var back = (txtarea.value).substring(strPos,txtarea.value.length);
    txtarea.value=front+text+back;
    strPos = strPos + text.length - backup;
    if (br == "ie") {
        txtarea.focus();
        var range = document.selection.createRange();
        range.moveStart ('character', -txtarea.value.length);
        range.moveStart ('character', strPos);
        range.moveEnd ('character', 0);
        range.select();
    }
    else if (br == "ff") {
        txtarea.selectionStart = strPos;
        txtarea.selectionEnd = strPos;
        txtarea.focus();
    }
    txtarea.scrollTop = scrollPos;
}
</script>
<style>
@media all {
	.page-break	{ display: none; }
}

@media print {
	.page-break	{ display: block; page-break-before: always; }
}
</style>

<style>
html, body {
    height: 100%;
    margin: 1%;
    padding: 0;
}

img {
    padding: 0;
    display: block;
    margin: 0 auto;
    max-height: 100%;
    max-width: 100%;
}
</style>
</head>
'''

head_noscroll = '''<head>
<meta name="format-detection" content="telephone=no">
<meta name="viewport" content="width=device-width; initial-scale=0.8;">

<link rel="shortcut icon" href="/ico/favicon.ico">



<script type="text/javascript"
  src="http://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML">
</script>

<script type="text/x-mathjax-config">
  MathJax.Hub.Config({
    TeX: { extensions: ["[Contrib]/mhchem/mhchem.js"] },
    "HTML-CSS": {scale: 90}
    });
</script>


<script type="text/javascript">
<!--

function insertAtCaret(areaId,text,backup) {
    var txtarea = document.getElementById(areaId);
    var scrollPos = txtarea.scrollTop;
    var strPos = 0;
    var br = ((txtarea.selectionStart || txtarea.selectionStart == '0') ?
        "ff" : (document.selection ? "ie" : false ) );
    if (br == "ie") {
        txtarea.focus();
        var range = document.selection.createRange();
        range.moveStart ('character', -txtarea.value.length);
        strPos = range.text.length;
    }
    else if (br == "ff") strPos = txtarea.selectionStart;

    var front = (txtarea.value).substring(0,strPos);
    var back = (txtarea.value).substring(strPos,txtarea.value.length);
    txtarea.value=front+text+back;
    strPos = strPos + text.length - backup;
    if (br == "ie") {
        txtarea.focus();
        var range = document.selection.createRange();
        range.moveStart ('character', -txtarea.value.length);
        range.moveStart ('character', strPos);
        range.moveEnd ('character', 0);
        range.select();
    }
    else if (br == "ff") {
        txtarea.selectionStart = strPos;
        txtarea.selectionEnd = strPos;
        txtarea.focus();
    }
    txtarea.scrollTop = scrollPos;
}
</script>
<style>
@media all {
	.page-break	{ display: none; }
}

@media print {
	.page-break	{ display: block; page-break-before: always; }
}
</style>

<style>
html, body {
    height: 100%;
    margin: 1%;
    padding: 0;
}

img {
    padding: 0;
    display: block;
    margin: 0 auto;
    max-height: 100%;
    max-width: 100%;
}
</style>

<style>
table {
    border-collapse: collapse;
}

td, th {
    border: 1px solid black;
    padding: 3px;
}
</style>
</head>
'''

buttons = ''

oldbuttons = '''
<input type="button" value="+" onclick="insertAtCaret('commands','+',0);" />
<input type="button" value="-" onclick="insertAtCaret('commands','-',0);" />
<input type="button" value="*" onclick="insertAtCaret('commands',' * ',0);" />
<input type="button" value="/" onclick="insertAtCaret('commands',' / ',0);" />
<input type="button" value="^" onclick="insertAtCaret('commands','^',0);" />
<input type="button" value="()" onclick="insertAtCaret('commands','()', 1);" />
<input type="button" value="=" onclick="insertAtCaret('commands',' = ', 0);" />
<input type="button" value="[]" onclick="insertAtCaret('commands','[]', 1);" />
'''

rest ='''
'''

PQlogo = '''<table><tr><td>

   <img  src="data:image/gif;base64,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"
width="115" height="76">



    </td><td>
    <h3> <br> 1. Set up a problem <br> 2. Solve it and press "go" <br> 3. See the work and the results </h3>
    </td></tr></table><br>
'''

template = '''<html>
%(head)s
<body>

    %(logo)s
    <div style="line-height:%(linespacing)s">

            %(output)s</div>
            <div class="page-break"></div>
            <form enctype="multipart/form-data" action="%(action)s" method="post" id="myform">
            <textarea onkeypress="process(event)" autofocus rows="%(rows)d" cols="40" id="commands" name="commands" %(keyboard)s  type="number" autocapitalize="off"
              autocomplete="on" spellcheck="false" style="font-weight: bold; font-size: 12pt;"
              >%(prefill)s</textarea> <p>
            <input type="submit" name="sub" style="font-weight: bold; font-size: 18pt;" value="  go  ">
            <input type="submit" name="sub" style="font-weight: bold; font-size: 18pt;" value="%(button2)s">

            %(selectors)s
            %(buttons)s
            %(obut_text)s </p>

            <input type="hidden" name="memory" value = "%(memory)s"/>
            <input type="hidden" name="inputlog" value = "%(inputlog)s"/>
            <input type="hidden" name="logbook" value = "%(logbook)s"/>
            <input type="hidden" name="hints" value = "%(hints)s"/>
            <input type="hidden" name="metadata" value = "%(metadata)s"/>
</form>
</body>
</html>
'''

template_noninteractive = '''<html>
%(head)s
<body>
    %(logo)s
    <div style="line-height:%(linespacing)s">

            <textarea rows="%(rows)d" cols="40" id="commands" name="commands" type="number" autocapitalize="off"
              autocomplete="on" spellcheck="false" style="font-weight: bold; font-size: 12pt;"
              >%(prefill)s</textarea> <p>
            %(output)s</div>
</body>
</html>
'''

template_oneline = '''<html>
%(head)s
<body onload="goToAnchor();">
<table>
    <tr><td><h1> PQCalc</h1></td><td>
    <h3> : a scientific calculator that keeps track of units and uncertainties of physical quantities</h3>
    </td></tr></table>
<table width=100%% cellspacing="2" cellpadding="10">

    <tr>
        <td width=100%% valign="top" style="border-width:6;border-color:#1132FF;border-style:ridge">
            %(output)s
            <form enctype="multipart/form-data" action="." method="post">
            <input type="text" autofocus size="50" id="commands" name="commands" %(keyboard)s  autocapitalize="off"
              autocomplete="off" spellcheck="false" style="font-weight: bold; font-size: 12pt;">
            <input type="submit" name="sub" value="  go  ">
            <p>
            <a name="myAnchor" ></a>
            %(buttons)s
            <input type="submit" name = "sub" value="print" />
            <input type="submit" name = "sub" value="reset" />
            <input type="submit" name = "sub" value="help" />
            </p>
            %(selectors)s
            <input type="hidden" name="memory" value = "%(memory)s"/>
            <input type="hidden" name="inputlog" value = "%(inputlog)s"/>
            <input type="hidden" name="logbook" value = "%(logbook)s"/>
            </form>

</body>
</html>
'''



printable_view = '''<html>
<head>
<meta name="format-detection" content="telephone=no">
<link rel="shortcut icon" href="/ico/favicon.ico">

<script type="text/javascript" id="MathJax-script" async
  src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js">
</script>

<script type="text/x-mathjax-config">
  MathJax.Hub.Config({
    "fast-preview": {disabled: true},
    tex2jax: {preview: ["[...]"]},
    TeX: { extensions: ["[Contrib]/mhchem/mhchem.js"] },
    "HTML-CSS": {size:90}
    });
</script>

</head>
<body>Calculation done with PQCalc, the physical quantity calculator<br>
that knows about quantities, units and uncertainties.<br><br>
by Karsten Theis, Chemical and Physical Sciences, Westfield State University<br>
inquiries and bug reports to ktheis@westfield.ma.edu<br><br>
Program currently hosted at
<a href="http://www.bioinformatics.org/pqcalc">
bioinformatics.org/PQCalc </a> and (newer version) at
<a href="http://pqcalc.pythonanywhere.com/">
http://pqcalc.pythonanywhere.com/ </a>
<h2> Input </h2>
<PRE>%s</PRE>
<div><form action="." method="post">
<input type="submit" name="sub" value="resubmit"/>
<input type="hidden" name="inputlog" value = "%s"/>
</form>
</div>
<h2> Known quantities </h2>
<PRE>%s</PRE>
<h2> Log of the calculation </h2>
%s
<h2> Formatted for Libretexts </h2>
%s
<h2> Send input via link </h2>
pqcalc.pythonanywhere.com/?prefill=%s
</div>
</body>
</html>
'''



