"""Script for counting lines of code.

Run : 04/19/2014 ----
Code        12754
Docstring    9336
Comment       944

Run : 01/08/2014 ----
Code        11845
Docstring   11319
Comment       926

Run : 12/04/2013 ----
Code        10574
Docstrings   8715
Comments      802

"""

import os
from subprocess import check_output, STDOUT, CalledProcessError
import re
from src.tools import path_tools as pt

CODE_PATTERN = re.compile(r'\|code *\|(\d+) *\|[\d\.]+')
DOCSTRING_PATTERN = re.compile(r'\|docstring *\|(\d+) *\|[\d\.]+')
COMMENT_PATTERN = re.compile(r'\|comment *\|(\d+) *\|[\d\.]+')

TOP = pt.unrel()

EXCLUSIONS = [pt.unrel('src', 'instruments', 'pyvisa'),
              pt.unrel('temporary_files')]

def isIncluded(path):
    """Return whether the given path should be included in the API.
    
    Parameters
    ----------
    path : str
        The absolute path of the file to check.
    
    Returns
    -------
    bool
        Whether the path should be included in the API generation (i.e. whether
        it does **not** start with a member of the `EXCLUSIONS` module 
        constant).
    """
    for exclusion in EXCLUSIONS:
        if path.startswith(os.path.normpath(exclusion)):
            return False
    return True
    
def extractData(filename, data):
    codeLines = -1
    docstringLines = -1
    commentLines = -1
    
    match = CODE_PATTERN.search(data)
    if match:
        codeLines = match.group(1)
    else:
        print("Code fail on: " + filename + '\n' + data)
    match = DOCSTRING_PATTERN.search(data)
    if match:
        docstringLines = match.group(1)
    else:
        print("Docstring fail on: " + filename + '\n' + data)
    match = COMMENT_PATTERN.search(data)
    if match:
        commentLines = match.group(1)
    else:
        print("Comment fail on: " + filename + '\n' + data)
    
    return (int(codeLines), int(docstringLines), int(commentLines))

def processFile(filename):
    try:      
        data = check_output(['pylint ' + filename], shell=True, stderr=STDOUT)
    except CalledProcessError as err:
        data = err.output
    return extractData(filename, data)

runningCount = [0, 0, 0]
    
for dirpath, dirnames, fnames in os.walk(TOP):
    dirpath = os.path.normpath(dirpath)
    if isIncluded(dirpath):
        for fname in fnames:
            if fname.endswith('.py') and not fname.startswith('__init__'):
                result = processFile(os.path.join(dirpath, fname))
                if result[0] >= 0 and result[1] >= 0 and result[2] >= 0:
                    runningCount[0] += result[0]
                    runningCount[1] += result[1]
                    runningCount[2] += result[2]
                    print('%8d,%8d,%8d > %s' % tuple(runningCount + [fname]))

