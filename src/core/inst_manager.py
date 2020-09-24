"""A tool to manage instruments.
"""

import imp
import logging
import os

from src import settings as stng
from src.core import instrument as inst
from src.tools import path_tools as pt

log = logging.getLogger('transport')

_PATH = pt.unrel(stng.DIR_INSTRUMENT_DRIVERS)
_LOOKUP_ORDER = stng.INST_PREFERENCE_ORDER
_COUNTER = [0]

_MSG_IMPORT_SUCCESS = 'Successfully loaded %s %s from file %s.'
_MSG_IMPORT_FAILURE = 'Error loading %s %s. Is VISA installed?\n>>>>%s'

class InstrumentManager(object):
    """A class for managing instruments.

    There are several purposes for this class. One is loading available
    instruments and relaying them to other objects. Perhaps the most important
    is ensuring that only one instance of each cryostat object exists at a
    time, since major problems can occur if there are multiple instances.
    """

    def __init__(self):
        log.info('Creating an instrument manager.')
        self._knownInstruments, self._knownSingletons = _loadDrivers(_PATH)
        self._knownControllers = _loadDrivers(_PATH, inst.Controller, 
                                              'Controller')
        self._presentSingletons = []
        self._controllers = []

    def getAvailableInstrumentStrings(self):
        """Get a list of strings of available instruments.

        Returns
        -------
        list of str
            A list of strings indicating the names of the available
            instruments.
        """
        instrumentNames = list(self._knownInstruments.keys())
        cryostatNames = list(self._knownSingletons.keys())
        return instrumentNames + cryostatNames

    def constructInstrument(self, name, experiment):
        """Construct a new instrument.

        Parameters
        ----------
        name : str
            The name of the class of the instrument to create.
        experiment : Experiment
            The experiment which should own the instrument.

        Returns
        -------
        Instrument
            An instance of the desired instrument class. If the requested
            instrument is a cryostat and the class has already been
            instantiated, the returned value is the already-instantiated
            cryostat. Otherwise, a newly created instrument is returned.
        """
        if name in self._knownInstruments:
            instrumentClass = self._knownInstruments[name]
            return instrumentClass(experiment)
        if name in self._knownSingletons:
            singletonClass = self._knownSingletons[name]
            for existing in self._presentSingletons:
                if isinstance(existing, singletonClass):
                    if experiment is not None:
                        existing.setExperiment(experiment)
                    return existing
            newSingleton = singletonClass(experiment)
            log.info('Creating singleton instrument %s', name)
            self._presentSingletons.append(newSingleton)
            return newSingleton
        return None

    def constructController(self, instrument):
        """Construct a controller for the specified instrument if possible.

        Parameters
        ----------
        instrument : Instrument
            The `Instrument` object for which to construct a controller.

        Returns
        -------
        Controller
            A `Controller` object for the specified instrument. If the
            specified instrument already has a controller associated with it,
            the existing controller will be returned.
        """
        name = instrument.__class__.__name__
        experiment = instrument.getExperiment()
        for currInst, currCont in self._controllers:
            if currInst is instrument:
                return currCont
        if name in self._knownControllers:
            new = self._knownControllers[name](experiment, instrument)
            self._controllers.append((instrument, new))
            return new
        return None
    
    def constructControlledInstrument(self, name, experiment=None):
        """Construct an instrument and a controller for it.
        
        Parameters
        ----------
        name : str
            The class name of the instrument to create.
        experiment : Experiment
            The experiment which should own the instrument.
            
        Returns
        -------
        Controller
            A `Controller` object for the specified instrument. If the
            specified instrument already has a controller associated with it,
            the existing controller will be returned.
        """
        instrument = self.constructInstrument(name, experiment)
        controller = self.constructController(instrument)
        return controller
    
    def removeController(self, controller):
        """Remove a controller from the database.
        
        Parameters
        ----------
        controller : Controller
            The `Controller` object to remove from the system.
        """
        for i, curr in enumerate(self._controllers):
            if curr[1] is controller:
                del self._controllers[i]
                return
            
 
class _InfoBox(object):
    """A convenience class for containing information about driver modules.
    
    Parameters
    ----------
    directory : str
        The absolute path of the directory holding the modules represented by
        the `_InfoBox`.
    moduleName : str
        The name of the module file (with no extension or base path) represented
        by the `_InfoBox`. Note that **all** modules with the specified name
        (that is, both source and byte-compiled files) will be scanned.
    superclass : class
        The class of which driver classes contained within the represented
        module should be subclasses (all subclasses of `superclass` will be
        returned as implemented drivers; `superclass` itself will not be
        reported).
    """
    def __init__(self, directory, moduleName, superclass=inst.Instrument):
        self.moduleName = moduleName
        self.data = {}
        self.sources = {}
        pathBase = os.path.join(directory, self.moduleName)
         
        self._addElements(pathBase, imp.load_source, 'py', superclass)
        self._addElements(pathBase, imp.load_compiled, 'pyc', superclass)
        self._addElements(pathBase, imp.load_compiled, 'pyo', superclass)
         
    def _addElements(self, path, meth, ext, superclass):
        """Load the drivers contained in a particular file.
        
        Parameters
        ----------
        path : str
            The absolute path to the file to load, without an extension.
        meth : function or instancemethod
            The function or method to import the requested module (usually
            a function contained in the `imp` module).
        ext : str
            The extension of the file to load, without a leading period (usually
            "py", "pyc", or "pyo".
        superclass : class
            The class of which driver classes contained within the represented
            module should be subclasses (all subclasses of `superclass` will be
            returned as implemented drivers; `superclass` itself will not be
            reported).
        """
        filepath = path + '.' + ext
        if os.path.exists(filepath):
            module = meth(self.moduleName + str(_COUNTER[0]), filepath)
            _COUNTER[0] += 1
            curr = {}
            for key, val in module.__dict__.items():
                try:
                    if issubclass(val, superclass) and val is not superclass:
                        curr[key] = val
                except (AttributeError, TypeError):
                    pass
            for key, val in curr.items():
                if key not in self.data:
                    self.data[key] = {}
                    self.sources[key] = {}
                self.data[key][ext] = getattr(module, key)
                self.sources[key][ext] = module
                 
    def getElements(self, order=None):
        """Return the objects which have drivers in the specified modules.
        
        Return a tuple of lists. The first list contains information about
        instruments of which more than one instance may exist, and the second
        contains information about instruments of which at most one instance
        may exist.
        
        Each list contains a series of tuples specifying information about
        the instruments in the modules represented by the `_InfoBox`. The
        tuple elements are
            1. A `str` specifying the name of the instrument;
            2. The `class` which can be used to create an instance of the
               instrument; and
            3. The absolute path of the file from which the class was loaded.
        
        The file from which the loaded class will be taken depends on `order`,
        which specifies extensions of Python code files in order of decreasing
        preference. For example, if the module name is "somefile" and
        "somefile.py" and "somefile.pyc" both exist, an `order` of
        ``['pyc', 'py']`` will result in the class from "somefile.pyc" being
        used.
        
        Parameters
        ----------
        order : list of str
            A list of strings indicating the extensions (without leading 
            periods) of Python source files **in order of preference**.
        
        Returns
        -------
        tuple of list of tuple
            A tuple of lists containing necessary information about the
            implemented drivers.
        """
        multiples = []
        singletons = []
        if order is None:
            order = _LOOKUP_ORDER
        for key, val in self.data.items():
            curr = None
            cmod = None
            done = False
            for ext in order:
                if ext in val and not done:
                    curr = val[ext]
                    cmod = self.sources[key][ext]
                    done = True
            if curr.isSingleton():
                singletons.append((key, curr, cmod.__file__))
            else:
                multiples.append((key, curr, cmod.__file__))
        return (multiples, singletons)
         
def _listModulesNoDuplicates(directory):
    """Return a duplicate-free list of Python files in a given directory.
    
    Parameters
    ----------
    directory : str
        A string indicating the absolute path to the folder in which to search 
        for Python files.

    Returns
    -------
    list of str
        A list of strings, where each string is the name of a Python file (a
        file ending with ".py", ".pyc", or ".pyo"). All extensions and 
        duplicates are removed, so that if "somefile.py" and "somefile.pyc" 
        both exist, a single element, "somefile", will be reported.
    """
    extensions = ['.' + x for x in _LOOKUP_ORDER]
    rawFiles = pt.lsAbsolute(directory, True)
    modules = []
    for filename in rawFiles:
        root, ext = os.path.splitext(filename)
        if ext in extensions and root not in modules:
            modules.append(root)
    return modules
 
def _loadDrivers(directories, superclass=inst.Instrument, tag='Instrument'):
    """Load instrument drivers.
    
    Parameters
    ----------
    directories : list of str
        A list of strings specifying folders to scan for instruments.
    superclass : class
        The class whose subclasses should represent drivers of the desired
        type. Note that `superclass` itself will **not** be loaded.
    tag : str
        The type of object being loaded, specified for logging purposes.
    
    Returns
    -------
    tuple of dict
        A tuple of two dictionaries containing information about drivers
        located in the specified places. In each dictionary, the keys are
        names of objects with drivers (usually subclasses of `Instrument`), and
        the values are the `class` objects corresponding to the given name.
        
        The first dictionary contains the drivers for those instruments of which
        more than one instance is permitted, and drivers in the second 
        dictionary are for those instruments of which no more than one 
        instance should exist.
    """
    multiples = {}
    singletons = {}
    allFiles = []
    if not isinstance(directories, list):
        directories = [directories]
    for folder in directories:
        for mod in _listModulesNoDuplicates(folder):
            allFiles.append((folder, mod))
    for directory, codefile in allFiles:
        ibox = _InfoBox(directory, codefile, superclass)
        currm, currs = ibox.getElements()
        for key, val, loc in currm:
            multiples[key] = val
            log.info(_MSG_IMPORT_SUCCESS, tag, key, loc)
        for key, val, loc in currs:
            singletons[key] = val
            log.info(_MSG_IMPORT_SUCCESS, tag, key, loc)
    return (multiples, singletons)

INSTRUMENT_MANAGER = InstrumentManager()
