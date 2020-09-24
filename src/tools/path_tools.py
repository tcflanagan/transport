"""A set of tools for managing paths.

The `path_tools` module provides auxiliary methods for converting between 
different path names. It's main function is to convert path names indicated
relative to the Transport directory to absolute path names.
"""

import logging
import os
import re

from src import about, settings

_EXTS_DATA = settings.EXTS_DATA
_EXTS_PARAMETERS = settings.EXTS_PARAMETERS
_EXTS_IMAGE = settings.EXTS_IMAGE

DATA_DIR = about.DATA_FOLDER
HOME_DIR = about.APP_FOLDER
HOME_PATH = []

def flatten(nested):
    """
    Takes a nested list and returns a flattened list. The output is always a
    single-level list, and the input can be a tuple, a list, a string, an 
    uncombined sequence of strings, or any nested combination of these.
    
    Parameters
    ----------
    nested : sequence
        A (possibly) nested sequence of strings. It can be entered as a list,
        a single string, a tuple, or simply a comma-separated series of
        arguments.
        
    Returns
    -------
    list
        A single-level list of the same elements.
    """
    try:
        try:
            nested + ''
        except TypeError:
            pass
        else:
            raise TypeError
        for sublist in nested:
            for element in flatten(sublist):
                yield element
    except TypeError:
        yield nested

def unrel(*args, **kwargs):
    """Expand a relative path into an absolute path.
    
    Merges the components in args (which may be a list, a tuple, or simply a
    comma-separated series) and assembles a full path, assuming they are paths
    relative to the project root.
    
    Parameters
    ----------
    args : sequence
        A (possibly) nested sequence of strings representing path elements,
        relative to the root of the Transport project tree. It can be entered 
        as a list, a single string, a tuple, or simply a comma-separated series 
        of arguments.
    
    Returns
    -------
    str
        The absolute path of the specified file.
    """
    if 'sep' in kwargs:
        sep = kwargs['sep']
    else:
        sep = '/'
    fullList = HOME_PATH + list(flatten(list(args)))
    ans = sep.join(fullList)
    return ans

def rel(path, asList=False):
    """Convert an absolute path to one relative to the project home.
    
    Parameters
    ----------
    path : str
        The absolute path to convert to a relative path.
    asList : bool
        Whether to return the result as a list. If `False`, the path will be
        returned as a string. The default is `False`.
    
    Returns
    -------
    str or list(str)
        The path relative to the project home. If `asList` is `True`, the result
        is a list of path components. If it is `False`, the result is a relative
        path string. If `path` is not a child of the project home, `None` is
        returned.
    """
    pathList = splitPath(path)
    homePosition = len(HOME_PATH) - 1
    if len(pathList) < homePosition or pathList[homePosition] != HOME_DIR:
        return None

    relativeList = pathList[homePosition + 1:]
    if asList:
        return relativeList
    return '/'.join(relativeList)

def pathToImportString(path, isRelative=True, importItem=None, importFrom=True):
    """Convert a path to a string suitable for importing.
    
    Parameters
    ----------
    path : str
        The path of a python module.
    isRelative : bool
        Whether `path` is relative to the project home. If `False`, `path` will
        be taken to be an absolute path. The default is `True`.
    importItem : str
        The name of the item to be imported.
    importFrom : bool
        If `importItem` is `None`: Whether the import string should be of the 
        form ``from [package] import [module]``. If `False`, the import string 
        will be of the form ``import [package].[module]``. 
        
        If `importItem` is **not** `None`: whether the import string should be
        of the form ``from [package].[module] import [importItem]``. If `False`,
        the import string will be of the form 
        ``import [package].[module].[importItem]``.
        
        The default is `True`.

    Returns
    -------
    tuple (str, str)
        A two element tuple where the first element is a string containing
        the requested components separated by periods, and the second is a
        string which can be passed to `exec` to actually perform the import. 
    """
    element0 = ''
    element1 = ''

    if path.endswith('.py'):
        path = path.replace('.py', '')
    if isRelative:
        pathList = splitPath(path)
    else:
        pathList = rel(path, True)

    if importItem is None:
        element0 = '.'.join(pathList)
        if importFrom:
            element1 = ('from ' + '.'.join(pathList[:-1]) +
                        ' import ' + pathList[-1])
        else:
            element1 = 'import ' + element0

    else:
        element0 = '.'.join(pathList + [importItem])
        if importFrom:
            element1 = ('from ' + '.'.join(pathList) +
                        ' import ' + importItem)
        else:
            element1 = 'import ' + element0

    return (element0, element1)

def normalizePath(path):
    """Replace all backslashes with front-slashes.
    
    Parameters
    ----------
    path : str
        A file path to normalize.
    
    Returns
    -------
    str
        The path with all front-slashes.
    """
    answer = os.path.normpath(path)
    while '\\' in answer or '//' in answer:
        answer = answer.replace('\\', '/')
        answer = answer.replace('//', '/')
    return answer

def splitPath(path):
    """Return the path split into its components.
    
    Parameters
    ----------
    path : str
        A file path.
    
    Returns
    -------
    list of str
        A list of strings representing the components of `path`.
    """
    return normalizePath(path).split('/')

def lsAbsolute(directory, filesOnly=False):
    """List the contents of a directory specified by an absolute path.
    
    Parameters
    ----------
    directory : str
        The absolute path of the directory to list.
    filesOnly : bool
        Whether to ignore subdirectories of `directory`.
        
    Returns
    -------
    list of str
        The contents of `directory` as a list of strings.
    """
    os.path.isabs(directory)
    if filesOnly:
        return [f for f in os.listdir(directory) if
                os.path.isfile(os.path.join(directory, f))]
    return [f for f in os.listdir(directory)]


def ls(directory, filesOnly=False):
    """List the contents of a directory specified relative to the project home.
    
    Parameters
    ----------
    directory : str
        The relative (to the project home) path of the directory to list.
    filesOnly : bool
        Whether to ignore subdirectories of `directory`.
        
    Returns
    -------
    list(str)
        The contents of `directory` as a list of strings.
    """
    directory = unrel(directory)
    return lsAbsolute(directory, filesOnly)


def getNextScan(directory):
    """Determine the next scan number.
    
    Determine the next unused scan number, assuming that scans are indicated
    by 'sNNN' or 'sNNNN', where N is a digit.
    
    Parameters
    ----------
    directory : str
        The absolute path of the directory of data files.
    
    Returns
    -------
    str
        A string representing the next scan number. It's format is "sNNN",
        where N is an integer.
    """
    pat = '^s[0-9]{3,4}'
    numbers = []
    for item in lsAbsolute(directory, True):
        match = re.search(pat, item)
        if match != None:
            numbers.append(int(match.group(0)[1:]))
    if len(numbers) == 0:
        return 's000'
    return 's%03.u' % (max(numbers) + 1)

def appendDigitsAsNecessary(folder, basename, extension='xdat'):
    """Append digits to avoid filename clashes.
    
    Append incrementally larger digits to the name of a file until the name
    does not collide with existing files.
    
    Parameters
    ----------
    folder : str
        The folder in which the data file will be saved. It should **not**
        include a trailing slash.
    basename : str
        The base name of the data file. It should include a scan number, if
        applicable, but it should **not** include an extension.
    extension : str
        The intended extension of the filename. It should not include a
        leading period.
        
    Returns
    -------
    str
        The base name for the data file with appropriate digits added and
        no extension.
    """
    extensions = _EXTS_DATA + _EXTS_PARAMETERS + _EXTS_IMAGE
    def checkExistance(fileToCheck):
        """Return whether a file exists."""
        for ext in extensions:
            if os.path.exists('%s/%s.%s' % (folder, fileToCheck, ext)):
                return True
        return False

    log = logging.getLogger('transport')
    log.info('Checking for and avoiding filename collisions.')
    extensionfree = basename
    filename = os.sep.join([folder, basename]) + '.' + extension
    cont = checkExistance(extensionfree)
    if cont:
        log.warn('File ' + filename + ' exists. Appending digits.')
    num = 0
    while cont:
        extensionfree = basename + str(num)
        filename = os.sep.join([folder, extensionfree]) + '.' + extension
        cont = checkExistance(extensionfree)
        if cont:
            log.warn('File ' + filename + ' exists. Appending digits.')
        else:
            log.warn('File ' + filename + ' does not exist. ' +
                         'Finished collision avoidance.')
        num += 1
    return extensionfree

def getFilesPostprocessor():
    """Return a dictionary containing data about postprocessor scripts.
    
    Returns
    -------
    dict
        A dictionary in which the keys are strings representing an absolute
        filename without an extension. The value for each key is a dictionary
        with three keys: 'py', 'pyc', 'pyo'. Each of the values is a `bool`
        specifying whether the base file with the corresponding extension 
        exists.
    """
    data = {}
    projectDir = unrel('lib', 'postprocessors')
#     if os.name.lower().startswith('posix'):
#         userDir = os.path.expanduser('~/.%s/lib/postprocessors')
#     else:
#         userDir = os.path.expanduser('~/AppData/Local/%s/lib/postprocessors')
    if os.path.exists(projectDir) and os.path.isdir(projectDir):
        contents = lsAbsolute(projectDir, True)
        for newFile in contents:
            current = os.path.join(projectDir, _chopExtension(newFile))
            if current is not None and current not in data:
                data[current] = {'py': os.path.exists(current + '.py'),
                                 'pyc': os.path.exists(current + '.pyc'),
                                 'pyo': os.path.exists(current + '.pyo')}
#     if os.path.exists(userDir) and os.path.isdir(userDir):
#         contents = lsAbsolute(userDir, True)
#         for newFile in contents:
#             current = os.path.join(userDir, _chopExtension(newFile))
#             if current is not None and current not in data:
#                 data[current] = {'py': os.path.exists(current + '.py'),
#                                  'pyc': os.path.exists(current + '.pyc'),
#                                  'pyo': os.path.exists(current + '.pyo')}
    return data

def _chopExtension(filename):
    """Remove a .py, .pyo, or .pyc extension from a filename."""
    if filename.endswith('.py'):
        return filename[:-3]
    if filename.endswith('.pyc') or filename.endswith('.pyo'):
        return filename[:-4]
    return None
    
def _locateDirectories():
    """Find the directories for various files to supplement the software."""
    def checkDirectory(dirPath):
        """Check whether a given path exists and is writable."""
        return os.path.exists(dirPath) and os.access(dirPath, os.W_OK)
    
    print("Finding directories")
    
    # configuration files
    if os.name.lower().startswith('posix'):
        confOpts = [os.path.expanduser('~/.%s/etc' % DATA_DIR),
                     os.path.abspath('/etc/%s' % DATA_DIR),
                     unrel('etc')]
        libOpts = [os.path.expanduser('~/.%s/lib' % DATA_DIR),
                    os.path.abspath('/lib/%s' % DATA_DIR),
                    unrel('lib')]
    subLibs = ['instruments', 'postprocessors', 'premades']
    
    confdir = None
    for opt in confOpts:
        print(opt)
        if checkDirectory(opt):
            confdir = opt
            break
    if confdir is None:
        os.makedirs(confOpts[0])

    libdir = None
    for opt in libOpts:
        if checkDirectory(opt):
            libdir = opt
            break
    if libdir is None:
        libdir = libOpts[0]
        os.makedirs(libdir)
        for sub in subLibs:
            fullPath = os.path.join(libdir, sub)
            os.makedirs(fullPath)
    else:
        for sub in subLibs:
            fullPath = os.path.join(libdir, sub)
            try:
                os.makedirs(fullPath)
            except OSError:
                pass
    
            
    print('Configuration directory = ' + confdir)
    print('Library directory =       ' + libdir)
    

def createHomePathOld():
    """Create the home path the old way if necessary."""
    myPath = splitPath(__file__)
    HOME_PATH.append(myPath.pop(0))
    while HOME_PATH[-1] != HOME_DIR:
        HOME_PATH.append(myPath.pop(0))

def createHomePath():
    """Create the home path if necessary."""
    myPath = splitPath(__file__)
    for component in myPath[:-3]:
        HOME_PATH.append(component)

def getSourceFiles(directory):
    """Return a list of source files in a given directory."""
    validExts = ['.py', '.pyc', '.pyo']
    considered = []
    output = {}
    filenames = lsAbsolute(directory, True)
    for filename in filenames:
        base, ext = os.path.splitext(os.path.split(filename)[1])
        if ext not in validExts:
            continue
        if base in considered:
            continue
        considered.append(base)
        output[base] = {}
        for item in validExts:
            curr = os.path.join(directory, base+item)
            if os.path.exists(curr):
                output[base][item] = True
            else:
                output[base][item] = False
    return output
        
    
if len(HOME_PATH) == 0:
    createHomePath()

# _locateDirectories()