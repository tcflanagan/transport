"""Scripts for building or compiling the software API

This module provides scripts for reading through the source code, pulling out
the docstrings, and generating HTML API from them. The output will be copied
to the `doc/api` directory.

"""

import os
import re
import shutil

from src import about
from src.tools import path_tools as pt
from src.tools.commandline import Environment
from src.tools.htmlhelper import HTMLHelper

MODULE_STRING = '.. automodule:: %s\n'
CLASS_STRING = '.. autoclass:: %s\n   :members:\n'
FUNCTION_STRING = '.. autofunction:: %s\n'

TOP = pt.unrel('src')

OUTPUT_FOLDER = pt.unrel('src', 'dev', 'docgen', 'api', 'source')

EXCLUSIONS = [pt.unrel('src', 'unusedbutpossiblyuseful'),
              pt.unrel('src', 'instruments', 'pyvisa')]
PATTERN_CLASS = re.compile(r'class *([a-zA-Z]\w+) *\(([\w\.]+)\) *:')
PATTERN_FUNCTION = re.compile(r'^def *([a-zA-Z]+[\w]*) *\((.*?)\) *?:', 
                              re.DOTALL|re.MULTILINE)

def toHeader(string, level):
    """Construct a reST header from a string.
    
    Parameters
    ----------
    string : str
        The string which should constitute the header.
    level : int
        The section level (i.e. if 0 is "part", then 1 is "chapter", 2 is
        "section", and so on).
    
    Returns
    -------
    str
        A string containing the input string with the appropriate markers
        below and possibly above it (as determined by `level`). 
    """
    length = len(string.strip())
    outputList = []
    if level == 0:
        outputList.append('='*length)
    outputList.append(string)
    if level <= 1:
        outputList.append('='*length)
    else:
        outputList.append('-'*length)
    return '\n'.join(outputList)

def toImportPath(path):
    """Convert a path to an import path.
    
    Parameters
    ----------
    path : str
        A proper, absolute file path.
    
    Returns
    -------
    str
        An import path (period-separated) relative to the home folder.
    """
    lst = ['src'] + path[len(TOP)+1:].split(os.path.sep)
    lst[-1] = lst[-1][:-3]
    return '.'.join(lst)

def toOutputModuleFile(path):
    """Construct the output file path for a module.
    
    The form of the output path is ``api_[packages]_[module name].rst``, where
    ``[packages]`` is an underscore-separated sequence of package names
    leading to the module, but not including "src".
    
    Parameters
    ----------
    path : str
        A proper, absolute file path for a module.
        
    Returns
    -------
    str
        The output path (with extension ".rst") for the module documentation
        file.
    """
    lst = ['api'] + path[len(TOP)+1:].split(os.path.sep)
    lst[-1] = lst[-1][:-3]
    return '_'.join(lst) + '.rst'

def toOutputPackageFile(path):
    """Construct the output file path for a package.
    
    If `path` refers to the top level of the source tree, the output is
    "index.rst". Otherwise, it is an underscore-separated list of path
    elements relative to the project home, beginning with "api" and not
    including "src".
    
    Parameters
    ----------
    path : str
        A proper, absolute file path for a module.
    
    Returns
    -------
    str
        The output path (with extension ".rst") for the package documentation
        file.
    """
    remainder = path[len(TOP)+1:].split(os.path.sep)
    if len(remainder) == 1 and remainder[0] == '':
        return 'index.rst'
    lst = ['api'] + remainder
    return '_'.join(lst) + '.rst'

def processModule(path):
    """Create a documentation file for a module.
    
    The output file consists of the following parts:
    
    1. The properly formatted module docstring.
    2. The classes contained in the module. Each class gets its own 
       sub-section, and all public methods are listed.
    3. The functions contained in the module.
    
    Parameters
    ----------
    path : str
        The absolute path to the module.
    """    
    
    filename = toOutputModuleFile(path)
    moduleName = os.path.basename(path)[:-3]
    modulePath = toImportPath(path)
    outputList = []
    outputList.append(toHeader('The `%s` module' % moduleName, 0)+'\n')
    outputList.append(MODULE_STRING % modulePath)
    
    functions = []
    with open(path) as moduleFile:
        contents = moduleFile.read()
    classes = PATTERN_CLASS.findall(contents)
    tempFunctions = PATTERN_FUNCTION.findall(contents) 
    for function in tempFunctions:
        if 'self' not in function[1]:
            functions.append(function)
    if len(classes) > 0:
        outputList.append(toHeader('Classes', 1) + '\n')
        for item in classes:
            clsname = item[0]
            item = modulePath + '.' + item[0]
            outputList.append(toHeader(clsname, 2) + '\n')
            outputList.append(CLASS_STRING % item)
    if len(functions) > 0:
        outputList.append(toHeader('Functions', 1) + '\n')
        for item in functions:
            item = modulePath + '.' + item[0]
            outputList.append(FUNCTION_STRING % item)
    with open(os.path.join(OUTPUT_FOLDER, filename), 'w') as outputFile:
        outputFile.write('\n'.join(outputList))

def processPackage(path, children, childPackages):
    """Construct the documentation file for a package.
    
    The file consists first of the docstring from the package's ``__init__`` 
    module. Then follows a list of the contents of the package. Its modules
    come first, and the sub-packages follow.
    
    Parameters
    ----------
    children : list of str
        A list of the paths of the modules in the package.
    childPackages : list of str
        A list of the paths of the sub-packages in the package.
    """
    filename = toOutputPackageFile(path)
    relPath = path[len(TOP)+1:]
    outputList = []
    if len(relPath) == 0:
        outputList.append(toHeader('The `src` package', 0) + '\n')
        outputList.append('.. automodule:: src\n')
    else:
        outputList.append(toHeader('The `%s` package' % 
                                   os.path.basename(relPath), 0)+'\n')
        outputList.append(MODULE_STRING % '.'.join(['src'] + 
                                                   relPath.split(os.path.sep)))
    if len(children + childPackages) > 0:
        outputList.append(toHeader('Contents', 1) + '\n')
    if len(childPackages) > 0:
        outputList.append(toHeader('Packages', 2) + '\n')
        outputList.append('.. toctree::')
        outputList.append('   :maxdepth: 1')
        outputList.append('')
        for child in childPackages:
            outputList.append('   %s' % toOutputPackageFile(child)[:-4]+'\n')
    if len(children) > 0:
        outputList.append(toHeader('Modules', 2) + '\n')
        outputList.append('.. toctree::')
        outputList.append('   :maxdepth: 1')
        outputList.append('')
        for child in children:
            outputList.append('   %s' % toOutputModuleFile(child)[:-4]+'\n')
    with open(os.path.join(OUTPUT_FOLDER, filename), 'w') as outputFile:
        outputFile.write('\n'.join(outputList))
    

PYTHONPATH = pt.unrel([])
LATEXPATH = pt.unrel('src', 'dev', 'docgen', 'manual', 'build', 'latex')

def formatHTMLHelp():
    """Format HTML Help files so that wxPython can display them."""
    htmlHelper = HTMLHelper()
    
    dirpath = pt.unrel('src', 'dev', 'docgen', 'manual', 'build', 'htmlhelp')
    initItems = os.listdir(os.path.normpath(dirpath))
    items = []
    for item in initItems:
        if item.endswith('.html'):
            items.append(pt.unrel('src', 'dev', 'docgen', 'manual', 'build', 
                                  'htmlhelp', item))
    
    for item in items:
        htmlHelper.scanFileForCode(item)
        

def generateManualHTMLHelp():
    """Produce the manual in the Microsoft HTML Help format.
    
    Remove the old documentation from ``doc/htmlhelp``. Then generate the
    new files by running the make file. Process these files to make them
    suitable for inclusion in wxPython's HTML Help frames, and run them
    through my own script to get the syntax highlighting done properly. Finally,
    move the result into the ``doc`` folder and delete the ``build`` directory.
    """
    cwd = pt.unrel('src', 'dev', 'docgen', 'manual')
    source = pt.unrel('src', 'dev', 'docgen', 'manual', 'build', 'htmlhelp')
    dest0 = ['doc', 'htmlhelp']
    
    if os.path.exists(pt.unrel(dest0)):
        shutil.rmtree(pt.unrel(dest0))
    
    env = Environment()

    env.extendPath('PYTHONPATH', PYTHONPATH)
    env.changeDirectory(cwd)
    if env.isWindows():
        response1 = env.communicate(r'make.bat htmlhelp')
        response2 = env.communicate(r'python sphinx-wxoptimize -c ' +
                                    r'source build\htmlhelp')
    else:
        response1 = env.communicate(r'make htmlhelp')
        response2 = env.communicate(r'python sphinx-wxoptimize -c ' +
                                    r'source build/htmlhelp')

    formatHTMLHelp()
    
    shutil.move(source, pt.unrel('doc'))
    shutil.rmtree(pt.unrel('src', 'dev', 'docgen', 'manual', 'build'))
    
    return (response1, response2)

def generateManualPDF():
    """Generate a PDF of the documentation.
    
    Delete the old PDF. Then set the PYTHONPATH to include the Transport
    directory. Run the make file to prepare the LaTeX sources. Then run
    pdflatex (twice to make sure contents and indices get updated). Move the
    resulting PDF into the project home folder. Delete the documentation
    build directory to avoid keeping old files.
    """
    cwd = pt.unrel('src', 'dev', 'docgen', 'manual')
    source = pt.unrel('src', 'dev', 'docgen', 'manual', 'build',
                      'latex', 'TransportExperiment.pdf')
    dest = pt.unrel('manual.pdf')
    
    if os.path.exists(dest):
        os.remove(dest)

    env = Environment()

    env.extendPath('PYTHONPATH', PYTHONPATH)
    env.changeDirectory(cwd)
    if env.isWindows():
        response1 = env.communicate('make.bat latex')
    else:
        response1 = env.communicate('make latex')
    env.changeDirectory(LATEXPATH)
    response2 = env.communicate('pdflatex TransportExperiment.tex')
    response3 = env.communicate('pdflatex TransportExperiment.tex')

    shutil.move(source, dest)
    shutil.rmtree(pt.unrel('src', 'dev', 'docgen', 'manual', 'build'))
    
    return (response1, response2, response3)

 
def generateAPI():
    """Extract the docstrings from the desired modules and create HTML API.
    
    First, remove the previous version of the documentation from the ``src/api``
    directory. Then run the ``make.bat`` file generated by the 
    ``sphinx-quickstart`` script to convert this to HTML. Finally, move the
    output back into the ``src/api`` directory.
    """
    cwd = pt.unrel('src', 'dev', 'docgen', 'api')
    source = pt.unrel('src', 'dev', 'docgen', 'api', 'build', 'html')
    dest0 = ['doc', 'api']
    
    if os.path.exists(pt.unrel(dest0)):
        shutil.rmtree(pt.unrel(dest0))
    
    env = Environment()

    env.extendPath('PYTHONPATH', PYTHONPATH)
    env.changeDirectory(cwd)
    if env.isWindows():
        response = env.communicate('make.bat html')
    else:
        response = env.communicate('make html')

    shutil.move(source, pt.unrel('doc'))
    os.rename(pt.unrel('doc', 'html'), pt.unrel('doc', 'api'))
    shutil.rmtree(pt.unrel('src', 'dev', 'docgen', 'api', 'build'))
    
    return response

def copySvnAdminAreas(sourcetop, destinationtop):
    """Copy the SVN admin areas without connecting to the repository."""
    sourcetopLength = len(sourcetop)
    
    for item in os.walk(sourcetop):
        relative = item[0][sourcetopLength+1:]
        if not relative.startswith('.') and '.svn' in relative:
            sourcedir = '/'.join([sourcetop, relative])
            destinationdir = '/'.join([destinationtop, relative])
            if not os.path.exists(destinationdir):
                os.makedirs(destinationdir)
            for filebase in item[2]:
                sourcepath = '/'.join([sourcedir, filebase])
                destinationpath = '/'.join([destinationdir, filebase])
                shutil.copy2(sourcepath, destinationpath)

    
def updateVersion(filename, newVersion, newRevision):
    """Update a conf.py file to use the new verison."""
    patternV = re.compile(r'version\s*=\s*[\'\"]\s*(.+?)\s*[\'\"]')
    patternR = re.compile(r'release\s*=\s*[\'\"]\s*(.+?)\s*[\'\"]')

    lines = []
    with open(filename) as configFile:
        for fileLine in configFile:
            fileLine = fileLine.rstrip()
            match = patternV.search(fileLine)
            if match:
                fileLine = fileLine.replace(match.group(1), newVersion)
            match = patternR.search(fileLine)
            if match:
                fileLine = fileLine.replace(match.group(1), newRevision)
            lines.append(fileLine)
            
    with open(filename, 'w') as configFile:
        for newline in lines:
            configFile.write(newline + '\n')

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
    
def compileAPI(newVersion=None):
    """Read through ``src/`` and generate an API; update the version.
    
    Recursively scan through the main source code folder of the project and
    construct code for the documented packages and modules. Treat any folder 
    which contains an ``__init__.py`` as a package, and treat all items with
    a ".py" extension in such a folder as modules. From each package, create
    a list of sub-packages and modules and from each module extract a list
    of classes and functions, constructing reST documentation as appropriate. 
    """
    for dirpath, dirnames, fnames in os.walk(TOP):
        dirpath = os.path.normpath(dirpath)
        if isIncluded(dirpath) and '__init__.py' in fnames:
            children = []
            childPackages = []
            for fname in fnames:
                if fname.endswith('.py') and not fname.startswith('__init__'):
                    children.append(os.path.join(dirpath, fname))
            for folder in dirnames:
                folderName = os.path.join(dirpath, folder)
                if (isIncluded(folderName) and 
                                os.path.exists(os.path.join(dirpath, folder, 
                                                            '__init__.py'))):
                    childPackages.append(os.path.join(dirpath, folder))
            processPackage(dirpath, children, childPackages)
            for fname in fnames:
                if fname.endswith('.py') and not fname.startswith('__init__'):
                    processModule(os.path.join(dirpath, fname))

    if newVersion is not None:
        pattern = re.compile(r'(\d+)\.(\d+)\.(\d+)')
        match = pattern.search(newVersion)
        if match:
            newMinorVersion = match.group(1) + '.' + match.group(2)
            updateVersion(pt.unrel('src', 'dev', 'docgen', 'api', 'source', 
                                   'conf.py'), 
                          newMinorVersion,
                          newMinorVersion + '.' + match.group(3))
    return generateAPI()

def compileManual(newVersion=None):
    """Compile the manual's reST sources into a PDF and HTML Help files."""
    if newVersion is not None:
        pattern = re.compile(r'(\d+)\.(\d+)\.(\d+)')
        match = pattern.search(newVersion)
        if match:
            minorVersion = match.group(1) + '.' + match.group(2)
            minorRevision = minorVersion + '.' + match.group(3)
            updateVersion(pt.unrel('src', 'dev', 'docgen', 'manual', 
                                   'source', 'conf.py'), 
                          minorVersion, minorRevision)
    result1 = generateManualHTMLHelp()
    result2 = generateManualPDF()
    return (result1, result2)

def compileDocumentation(newVersion=None, api=True, manual=True):
    """Update software documentation.
    
    Parameters
    ----------
    newVersion : str
        The new version for the documentation. If `None` (the default), the 
        version string in the Sphinx configuration files will not be changed.
    api : bool
        Whether to update the API. The default is `True`.
    manual : bool
        Whether to update the manual. The default is `True`.
    """
    parent = '/'.join(pt.unrel().rsplit('/')[:-1])
    realtop = pt.unrel('doc')
    temptop = '/'.join([parent, 'transport_temp', 'doc'])
    copySvnAdminAreas(realtop, temptop)
    
    if api:
        shutil.rmtree(pt.unrel('doc', 'api'))
        result1 = compileAPI(newVersion)
    else:
        result1 = ()
    
    if manual:
        shutil.rmtree(pt.unrel('doc', 'htmlhelp'))
        result2 = compileManual(newVersion)
    else:
        result2 = ()
    
    copySvnAdminAreas(temptop, realtop)
    toRemove = '/'.join([parent, 'transport_temp'])
    if os.path.exists(toRemove):
        shutil.rmtree(toRemove)
        
    return (result1, result2)


if __name__ == '__main__':
    OUTPUT = compileDocumentation(newVersion=about.getVersion(), manual=True)
    for line in OUTPUT[0].splitlines():
        print(line)
