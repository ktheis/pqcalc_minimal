# coding=utf-8

from bottle import get, post, run, request, response, static_file, default_app
import re

import os
path = os.path.abspath(__file__)
dir_path = os.path.dirname(path)

"""
Module to tie the quantities, calculator, and form modules together into an online calculator.

The calculator is hosted on ktheis.pythonanywhere.com, but you could have a local server or run it
on other platforms. In the calculator, you define values of named physical quantities,
and then do arithmetic with them. The web server is implemented using web.py.

"""
from calculator import calc, State
from comments import extract_knowns, create_comment
from form import newform, printableLog
from chemistry import show_formulae, formula_details, show_quantities
import datetime
import urllib.parse
import json
from html import escape, unescape


@get('/')
def index_get():
    known = [' -- nothing yet -- ']
    browser = request.environ.get('HTTP_USER_AGENT')
    query = request.query
    if 'switch' in query:
        commands = "\n".join(["__%s__ = 1" % switch for switch in query['switch'].split("*")])
        result, inputlog = calc('', commands)
        return newform(result, '', inputlog, browser=browser)
    if 'prefill' in query:
        prefill = urllib.parse.unquote(query.prefill)
    else:
        prefill = ''
    datestamp = datetime.datetime.now()
    metadata = '\n'.join(["0","0", datestamp.isoformat()])
    print('The get time is', datestamp)
    if prefill:
        result, good_input = calc('', prefill)
        logbook = ''
        return newform(result, logbook, good_input, browser=browser, metadata=metadata)
    return newform(('', '', '', known, ''), '', '', browser=browser, metadata=metadata, prefill=prefill)


@post('/')
def index_post():
    # response.set_header('Content-Type', 'text/html; charset=utf-8')
    response.set_header('X-XSS-Protection', '0')
    browser = request.environ.get('HTTP_USER_AGENT').lower()
    datestamp = datetime.datetime.now()
    if request.forms.get('sub') == "reset":
        return newform(('', '', '', '', ''), '', '', browser=browser)
    if request.forms.get('sub') == "resubmit":
        prefill = request.forms.inputlog
        return newform(('', '', '', [], ''), '', '', browser=browser, actualpref=prefill)

    oldmemory = request.forms.get('memory')
    oldinputlog = request.forms.get('inputlog')
    oldlogbook = request.forms.get('logbook')
    md = unescape(request.forms.get('metadata'))
    print(md)
    try:
        level, sessionid, lasttime = md.splitlines()
        level = int(level)
        sessionid = int(sessionid)
    except:
        level, sessionid, lasttime = 0, 0, "no time"
    commands = request.forms.get('commands')
    level += 1
    if request.forms.get('sub') == "export":
        return printableLog(State(oldmemory), oldlogbook, oldinputlog)

    result, newinputlog = calc(oldmemory, commands)
    # verboselog, brieflog, memory, known, linespace = result
    metadata = '\n'.join([str(level), str(sessionid), datestamp.isoformat()])
    print(metadata)
    inputlog = oldinputlog + newinputlog
    print(inputlog)
    return newform(result, oldlogbook, inputlog, metadata=metadata)


@get('/ico/:file')
def send_ico(file):
    return static_file(file, root=dir_path+'/'+'static/')



run(host='localhost', port=8080, debug=True)
#application = default_app()
