"""Software representation of a physical instrument.

An `Instrument` is an object-oriented representation of an instrument---that is,
an object which can accept or return data or do things. Most instruments will be
physical devices like voltmeters or cryostats, but they may also be purely
computational.

This module provides the following class.

Instrument: 
    An abstract base class which should be extended by real instruments, each 
    of which should define their own capabilities.
"""

import imp
import logging
import os
from threading import Thread
from time import sleep, time # Consider replacing `time` with `perf_counter`
import types
import xml.etree.ElementTree as ET

from src import settings
from src.core import progress
from src.core.action import constructAction
from src.core.errors import Null

from src.core.action import (Action, ActionPostprocessor, ActionScan, 
                             ActionLoopTimed, ActionLoopIterations, 
                             ActionLoopWhile, ActionLoopUntilInterrupt, 
                             ActionSimultaneous, ActionSpec, ParameterSpec)
from src.core.configuration import c
try:
    import visa
except OSError:
    visa = Null()
from visa import VisaIOError
RM = visa.ResourceManager()
LIB = RM.visalib

from src.tools import path_tools as pt
from src.tools.parsing import escapeXML

log = logging.getLogger('transport')

_PREFER_COMPILED = False
_PP_DUPLICATE_ERROR = ('Postprocessor function %s (%s) found in multiple '
                       'locations. Version from %s will be used.')

_EXTS_DATA = settings.EXTS_DATA
# pylint: disable=R0201


#--------------------------------------------------------- Instrument base class

class Instrument(object):
    """An `Instrument` is an object-oriented software representation of a
    physical instrument. 
    
    The `Instrument` class essentially provides an interface (in the 
    technical, computer science sense) which all instruments should implement. 
    It defines the methods and properties which all `Instrument` subclasses 
    are expected to provide, and it should be overridden for each instrument 
    model.
    
    Since an instrument generally defines what operations it is able to carry
    out, subclasses of `Instrument` should implement the `getActions` method.
    
    Parameters
    ----------
    experiment : Experiment
        The `Experiment` object which owns this instrument.
    name : str
        The name of the instrument.
    spec : list of InstrumentParameter
        A list of instances of `InstrumentParameter` specifying the information
        necessary for the instrument to be used and referenced. This should
        include, for example, the VISA address of the instrument, if
        applicable. If `None`, the default values will be used.
    """

    def __init__(self, experiment, name='Abstract instrument', spec=None):
        self._expt = experiment
        self._name = name
        self._initialized = False
        if spec is not None:
            self._spec = spec
        else:
            self._spec = self.getRequiredParameters()
        self._info = self._name
        self._statusMonitor = progress.getStatusMonitor('default')

    def initialize(self):
        """Prepare the instrument for use."""
        self._initialized = True

    def finalize(self):
        """Release control of the instrument."""
        self._initialized = False
        
    def isInitialized(self):
        """Return whether the instrument has been initialized.
        
        Returns
        -------
        bool
            Whether the instrument has been initialized.
        """
        return self._initialized

    def getExperiment(self):
        """Return the experiment which owns this instrument.
        
        Returns
        -------
        Experiment
            The `Experiment` object of which this instrument is part.
        """
        return self._expt

    def setExperiment(self, experiment):
        """Set the experiment which owns this instrument.
        
        Parameters
        ----------
        experiment : Experiment
            The `Experiment` object of which this instrument is part.
        """
        self._expt = experiment

    def getStatusMonitor(self):
        """Return the status monitor.
        
        Returns
        -------
        StatusMonitor
            The `StatusMonitor` object for this instrument.
        """
        return self._statusMonitor

    def setStatusMonitor(self, statusMonitor):
        """Set the status monitor.
        
        Parameters
        ----------
        statusMonitor : StatusMonitor
            The new `StatusMonitor` object for this instrument.
        """
        self._statusMonitor = statusMonitor
    
    def __str__(self):
        """Return the user-specified name of this instrument.
        
        Returns
        -------
        str
            The name of the instrument.
        """
        return self._name
    
    def getName(self):
        """Return the user-specified name of this instrument.
        
        Returns
        -------
        str
            The name of the instrument.
        """
        return self._name

    def setName(self, name):
        """Set the name of the instrument.
        
        Parameters
        ----------
        name : str
            The name of the instrument.
        """
        self._name = name

    def getInformation(self):
        """Return the information string describing this instrument.
        
        Returns
        -------
        str
            The information string for this instrument.
        """
        return self._info

    def getSpecification(self):
        """Return the specification of the instrument.
        
        Returns
        -------
        list of InstrumentParameter
            A list of `InstrumentParameters` indicating the information
            characterizing the instrument.
        """
        return self._spec

    def setSpecification(self, newSpec):
        """Set the specification of the instrument.
        
        Parameters
        ----------
        newSpec : list of InstrumentParameter
            A list of `InstrumentParameters` indicating the information
            characterizing the instrument.
        """
        self._spec = newSpec

    def getEqualEnoughAction(self, compAction):
        """Return an `Action` which is 'the same as' compAction.
        
        Two actions are "the same" if they have the same description and the 
        same parameters. Parameters are "the same" if they have the same
        name, description, and format string.
        """
        for index, act in enumerate(self.getActions()):
            if compAction.isEqualEnough(act):
                return (index, act)
        return None

    def waitWhilePaused(self, obeyPause=True):
        """Wait until the experiment is no longer paused."""
        while obeyPause and self._expt.isPaused():
            sleep(0.2)

    def getActions(self):
        """Return a list of `Action` tuples implemented by the instrument."""
        return []

    def getAction(self, name, instantiate=True):
        """Return either the action tuple or object with the given name.
        
        Scan through the list of actions implemented by the instrument to find
        one which has the specified name, and return either the `ActionSpec`
        or an `Action` instance associated with it.
        
        Parameters
        ----------
        name : str
            A string specifying the name which identifies the desired action.
        instantiate : bool
            Whether to create an instance of the action. If `False`, the
            `ActionSpec` tuple will be returned instead of an `Action` object.
        
        Returns
        -------
        ActionSpec or Action
            The `ActionSpec` (if `instantiate` is `False`) or `Action` (if
            `instantiate` is `True) specified by `name`, or `None` if `name`
            cannot be found.
        """
        result = None
        for action in self.getActions():
            if action.name == name:
                result = action
        if instantiate and result is not None:
            return constructAction(result)
        return result

    def __getstate__(self):
        """Return a dictionary of the defining properties of the instrument.

        Returns
        -------
        dict
            The full dictionary of the class except that those elements which
            are incompatible with `pickle` have been removed.
        """
        odict = self.__dict__.copy()
        odict['_statusMonitor'] = None
        return odict

    def __setstate__(self, dictionary):
        """Reinstate the default status monitor after loading from a file."""
        self._statusMonitor = progress.getStatusMonitor('default')
        self.__dict__.update(dictionary)
        
    def getXML(self, parent):
        """Add XML to the tree."""
        instrument = ET.SubElement(parent, 'instrument')
        instrument.set('class', self.__class__.__name__)
        instrument.set('name', self._name)
        for item in self._spec:
            item.getXML(instrument)
        


    @classmethod
    def getDefaultName(cls):
        """Return a default name for the instrument."""
        return 'Abstract instrument'

    @classmethod
    def getRequiredParameters(cls):
        """Return a template for the specification of the instrument. 
        
        The specification indicates which parameters must be defined for the
        instrument to work. This should be overridden to indicate the 
        parameters required for specific instruments.
        
        Returns
        -------
        list of InstrumentParameter
            A list of `InstrumentParameter` objects indicating what 
            information must be supplied to configure the instrument.
        """
        return []
    
    @classmethod
    def isSingleton(cls):
        """Return whether at most one instance of the instrument may exist.
        
        Returns
        -------
        bool
            Whether only zero or one instance of the instrument may exist.
        """
        return False


#---------------------------------------------------------- Instrument parameter

class InstrumentParameter(object):
    """A parameter for characterizing an instrument.
    
    Each `Instrument` object must specify what information is necessary to
    initially configure itself. For example, in order to communicate with the
    computer, an `Instrument` representing any GPIB instrument must have
    a VISA address, so that `Instrument` should require a `Parameter` object
    corresponding to said address.
    
    Parameters
    ----------
    description : str
        A string indicating what the parameter is, so that the software can
        prompt the user for a value in an understandable way.
    value : str or int or float
        The value of the parameter. Since parameters are initially defined
        at compile time, they are defined with a *default* value. This can
        later be changed.
    allowed : list or function or None
        Information to indicate what values are permitted for the parameter.
        If `allowed` is `None`, any value will be accepted (assuming, of
        course, that it can be typecast into the form indicated by 
        `formatString`). If it is a function (or a method), the function
        will be evaluated and returned every time the `allowed` property is
        queried. Using a function would be useful for getting a list of
        VISA addresses seen by the computer; a simple list would not be
        good, since instruments can be connected or disconnected, which would
        change the values.
    formatString : str
        A string indicating how the value should be formatted. An example
        could be '%.6e' for an exponential value with six digits after the
        decimal. Note that '%s' (a simple string) is the only value which
        makes sense if `allowed` is not `None`.
    """

    def __init__(self, description, value='', allowed=None, formatString='%s'):
        """Create a new instrument parameter."""

        self.__description = description
        self.__value = value
        self.__allowed = allowed
        self.__formatString = formatString
        if 'd' in formatString:
            self.__coerce = int
        elif 'f' in formatString or 'e' in formatString:
            self.__coerce = float
        else:
            self.__coerce = str

    @property
    def description(self):
        """Get the description of the instrument parameter.
        
        Returns
        -------
        str
            The description of the instrument parameter.
        """
        return self.__description

    @property
    def value(self):
        """Get the value of the instrument parameter.
        
        Returns
        -------
        str or int or float
            The value of the instrument parameter. The value will be of the
            proper type. For example, if the parameter represents a lock-in's
            frequency, the value will be a float.
        """
        return self.__value
    @value.setter
    def value(self, value):
        """Set the value of the instrument parameter.
        
        Parameters
        ----------
        value : str or int or float
            The new value of the parameter. It will be coerced to the proper
            type.
        """
        self.__value = self.__coerce(value)

    @property
    def allowed(self):
        """Get the allowed values for the parameter.
        
        Returns
        -------
        list of str or None
            The allowed values for the parameter. If any value is accepted,
            then `None` is returned. Otherwise, the returned value will be
            a list of strings.
        """
        if self.__allowed is None:
            return None
        if isinstance(self.__allowed, list):
            return list(self.__allowed)
        return self.__allowed()

    def __str__(self):
        """Return a formatted string representation of the parameter.
    
        Returns
        -------
        str
            A string representing the value of the parameter with the
            correct format.
        """
        return self.__formatString % self.__value
    
    def getXML(self, parent):
        instrumentparameter = ET.SubElement(parent, "instrumentparameter")
        instrumentparameter.set('value', self.__value)
        print(ET.tostring(instrumentparameter))
    


# Instrument controller base class ---------------------------------------------

class Controller(Thread):
    """A base class for instrument controllers.
    
    Every subclass must implement the `getInstrumentClassName` class method,
    which should return a string indicating the name of the class of the
    instrument controlled by the `Controller` subclass.
    """

    @classmethod
    def getInstrumentClassName(cls):
        """Return the class name of the instrument managed by this controller.
        
        Returns
        -------
        str
            The name of the class of the instrument controlled by this object.
        """
        raise NotImplementedError
    
    @classmethod
    def isSingleton(cls):
        """Return whether at most one instance of the controller may exist.
        
        Returns
        -------
        bool
            Whether only zero or one instance of the controller may exist.
        """
        return False


#-------------------------------------------------------------- Helper functions

def getVisaAddresses():
    """Return a list of available VISA addresses.
    
    Returns
    -------
    list of str
        A list of strings representing the VISA addresses which the
        VISA controller recognizes as having an associated instrument
        attached.
    """
    if isinstance(visa, Null):
        return ['No address']
    try:
        ans = RM.list_resources()
        return ans
    except VisaIOError:
        log.error('Cannot get VISA addresses.')
        return ['No address']



#------------------------------------------------------------- System instrument

class System(Instrument):
    """A software representation of the computer.
    
    The `System` instrument carries out a host of general-purpose operations
    including inserting time delays, setting filenames, and performing
    calculations.
    
    It also provides access to a series of loop types for performing a
    single action, or a set of actions, multiple times.
    """

    def __init__(self, experiment):
        """Initialize a system instrument."""
        super(System, self).__init__(experiment, 'System', [])
        self.num = 0
        self.storedstring = ''

        self.defaultFolder = c.getDataFolder()
        self.defaultFile = c.getDataFile()
        if c.getPrependScan():
            self.defaultScan = 'Auto'
        else:
            self.defaultScan = ''

        self._info = 'Name: System\nDescription: The computer'

    def initialize(self):
        """Initialize the instrument."""
        pass

    def finalize(self):
        """Finalize the instrument"""
        pass

    def setFile(self, folder, filebase, scan):
        """Set the files to which the data will be stored.
        
        Parameters
        ----------
        folder : str
            The folder into which the file will be saved. The folder must
            exist.
        filebase : str
            The base name of the file, which is the filename without any
            leading directories or following extensions.
        scan : int
            A scan number to prepend to the filename. If it is a positive
            number, it will be used as-is. If it is negative, the scan
            will be chosen to be the first integer larger than all other
            scan numbers in the data folder. If it is `None`, no scan number
            will be prepended.
        """
        self._expt.setFilenames(generateFilenameA(folder, filebase, scan))
        self._statusMonitor.post('Set Filename')
        return ()

    def setNumber(self, number):
        """Set the value of an internal number."""
        self.num = number
        self._statusMonitor.post('Set number to %d.' % number)
        return ()

    def setStoredString(self, string):
        """Set the value of an internal string."""
        self.storedstring = string
        return ()

    
    def waitShort(self, delay):
        """Pause for a specified time.
        
        Parameters
        ----------
        time : float
            The time to wait, in seconds.
        """
        sleep(delay)
        return ()

    def waitLong(self, delay):
        """Pause for a specified time, updating while waiting.
        
        Parameters
        ----------
        delay : float
            The time to wait, in seconds.
        """
        upd = self._statusMonitor.update
        startTime = time()
        elapsed = 0.0
        while elapsed < delay:
            upd('Waited %.3f s of %.3f s.' % (elapsed, delay))
            elapsed = time() - startTime
            sleep(0.1)
        self._statusMonitor.post('Waited %.3f s.' % delay)
        return ()


    def calculate(self, expr):
        """Numerically evaluate an expression.
        
        Parameters
        ----------
        expr : str
            A string which, when constants, parameters, column data, and
            standard mathematical functions have been substituted into it,
            represents a mathematical expression that can be evaluated to
            yield a floating-point number.
            
        Returns
        -------
        float
            The result of evaluating the input expression.
        """
        return (self._expt.evaluateExpression(expr),)

    def getActions(self):
        """Return a list of supported actions."""
        return [
            ActionSpec('set_file', Action,
                {'experiment': self._expt,
                 'instrument': self,
                 'description': 'Set data file',
                 'inputs': [
                     ParameterSpec('folder',
                         {'experiment': self._expt,
                          'description': 'Data folder',
                          'formatString': '%s',
                          'value': self.defaultFolder}),
                     ParameterSpec('filebase',
                         {'experiment': self._expt,
                          'description': 'Data file',
                          'formatString': '%s',
                          'value': self.defaultFile}),
                     ParameterSpec('scan',
                         {'experiment': self._expt,
                          'description': 'Scan number',
                          'formatString': '%s',
                          'value': self.defaultScan})
                     ],
                     'string': ('Set file to $filebase.txt in ' +
                                pt.normalizePath('$folder') +
                                ', inserting scan number [$scan].'),
                     'method': self.setFile}
                ),
                ActionSpec('loop_timed', ActionLoopTimed,
                    {'experiment': self._expt,
                     'instrument': self,
                     'description': 'Loop: time',
                     'duration': 10}),
                ActionSpec('loop_iterations', ActionLoopIterations,
                    {'experiment': self._expt,
                     'instrument': self,
                     'description': 'Loop: iterations',
                     'iterations': 10}),
                ActionSpec('loop_while', ActionLoopWhile,
                    {'experiment': self._expt,
                     'instrument': self,
                     'description': 'Loop: conditional',
                     'expression': 'True'}),
                ActionSpec('loop_interrupt', ActionLoopUntilInterrupt,
                    {'experiment': self._expt,
                     'description': 'Loop: manual',
                     'instrument': self}),
                ActionSpec('simultaneous', ActionSimultaneous,
                    {'experiment': self._expt,
                     'description': 'Execute simultaneously',
                     'instrument': self}),
                ActionSpec('wait', Action,
                    {'experiment': self._expt,
                     'instrument': self,
                     'description': 'Wait',
                     'inputs': [
                         ParameterSpec('delay',
                             {'experiment': self._expt,
                              'description': 'Wait time (s)',
                              'formatString': '%.3f',
                              'value': 0.01})
                         ],
                     'string': 'Wait for $delay s.',
                     'method': self.waitShort}
                ),
                ActionSpec('wait_long', Action,
                    {'experiment': self._expt,
                     'instrument': self,
                     'description': 'Wait (long)',
                     'inputs': [
                         ParameterSpec('delay',
                             {'experiment': self._expt,
                              'description': 'Wait time (s)',
                              'formatString': '%.3f',
                              'value': 60.0})
                         ],
                     'string': 'Wait for $delay s.',
                     'method': self.waitLong}
                ),
                ActionSpec('calculate', Action,
                    {'experiment': self._expt,
                     'instrument': self,
                     'description': 'Calculate',
                     'inputs': [
                         ParameterSpec('expr',
                             {'experiment': self._expt,
                              'description': 'Expression',
                              'formatString': '%s',
                              'value': ''})
                     ],
                     'outputs': [
                         ParameterSpec('result',
                             {'experiment': self._expt,
                              'description': 'Result',
                              'formatString': '%.6e',
                              'binName': 'Result',
                              'binType': 'column'})
                     ],
                     'string': 'Evaluate the expression $expr.',
                     'method': self.calculate}
                ),
                ActionSpec('set_num', Action,
                    {'experiment': self._expt,
                     'instrument': self,
                     'description': 'Set number',
                     'inputs': [
                         ParameterSpec('number',
                             {'experiment': self._expt,
                              'description': 'Number value',
                              'formatString': '%d',
                              'binName': 'Number',
                              'binType': 'column',
                              'value': 0})
                     ],
                     'string': 'Set number to $number.',
                     'method': self.setNumber}
                ),
                ActionSpec('scan_num', ActionScan,
                    {'experiment': self._expt,
                     'instrument': self,
                     'description': 'Scan number',
                     'inputs': [
                         ParameterSpec('number',
                             {'experiment': self._expt,
                              'description': 'Number value',
                              'formatString': '%d',
                              'binName': 'Number',
                              'binType': 'column',
                              'value': [(0, 10, 1)]})
                     ],
                     'string': 'Scan number',
                     'method': self.setNumber}
                ),
                ActionSpec('set_string', Action,
                    {'experiment': self._expt,
                     'instrument': self,
                     'description': 'Set string',
                     'inputs': [
                         ParameterSpec('value',
                             {'experiment': self._expt,
                              'description': 'String value',
                              'formatString': '%s',
                              'value': ''})
                     ],
                     'string': 'Set string to $value.',
                     'method': self.setStoredString}
                )
        ]


#-------------------------------------------- Special instrument - postprocessor

class Postprocessor(Instrument):
    """An instrument for performing post-experiment actions and calculations."""
    
    def __init__(self, experiment):
        super(Postprocessor, self).__init__(experiment, 'Postprocessor', [])
        self._commands, self._actionSpecs = _POSTPROCESSOR_COMMANDS
                    
    def __getattribute__(self, name):
        """Get a method or attribute."""
        try:
            return super(Postprocessor, self).__getattribute__(name)
        except AttributeError:
            return self._commands[name]
    
    def __getstate__(self):
        """Remove the method reference for pickling purposes."""
        odict = self.__dict__.copy()
        odict['_commands'] = {}
        odict['_actionSpecs'] = []
        return odict

    def __setstate__(self, dictionary):
        """Reinstate the method reference after loading from a file."""
        self.__dict__.update(dictionary)
        self._loadMethods()

    def initialize(self):
        pass

    def finalize(self):
        pass

    def getActions(self):
        return [ActionSpec(spec['name'], ActionPostprocessor,
                           {'experiment': self._expt,
                            'instrument': self,
                            'description': spec['description'],
                            'method': self._commands[spec['name']],
                            'sourceFile': spec['source']})
                for spec in self._actionSpecs]


#-------------------------------------------------------------- Helper functions

def generateFilenameA(folder, baseName, scan=-1, noOverwrite=True):
    """Generate a filename, applying the desired modifications.
    
    Parameters
    ----------
    folder : str
        The path to the folder into which data will be saved.
    baseName : str
        The name, relative to `folder`, which should be used for the data
        files. If it does not include an extension, ".xdat" will be used.
    scan : int
        If positive, `scan` will be interpreted as the scan number for the
        files. If it is negative, the next scan number will be chosen
        automatically. If it is `None`, no scan number will be prepended
        to the filenames. (default = -1)
    noOverwrite : bool
        Whether to append numbers to the end of the name to prevent over-
        writing data. (default = `True`)
    """
    if folder.endswith('/') or folder.endswith('\\'):
        folder = folder[:-1]
    extension = None
    for ext in _EXTS_DATA:
        dotext = '.' + ext
        if baseName.endswith(dotext):
            baseName = baseName[:-len(dotext)]
            extension = ext
    if extension is None:
        extension = _EXTS_DATA[0]

    if scan is not None and scan != '':
        try:
            scan = int(scan)
        except (TypeError, ValueError):
            scan = -1
        if scan >= 0:
            baseName = 's%03.u%s' % (scan, baseName)
        elif scan < 0:
            baseName = pt.getNextScan(folder) + baseName
    if noOverwrite:
        baseName = pt.appendDigitsAsNecessary(folder, baseName, extension)
    return pt.normalizePath('%s/%s.%s' % (folder, baseName, extension))

def _processMatch(match):
    """Convert a match tuple to a more readable format."""
    if len(match) != 6:
        return None
    if len(match[0]) == 0:
        match = match[3:]
    else:
        match = match[:3]
    temp1 = match[2].split('\n')
    desclist = []
    for item in temp1:
        desclist.extend(item.split(' ')) 
    done = False
    while not done:
        try:
            desclist.remove('')
        except ValueError:
            done = True
    return {'name': match[0].strip(), 'args': match[1], 
            'description': ' '.join(desclist)}

def _loadPostprocessorCommands():
    """Load the functions available to the postprocessor environment.
    
    Returns
    -------
    dict
        A dictionary in which the keys are the names of the various functions
        and in which the values are the functions themselves.
    list of dict
        A list of dictionaries containing the information necessary to construct
        `Action` objects for the postprocessor commands.
    """
    commands = {}
    actionSpecs = []
    data = pt.getFilesPostprocessor()
    for fname in data:
        modname = os.path.basename(fname)
        module = None
        if _PREFER_COMPILED:
            if data[fname]['pyo']:
                module = imp.load_compiled(modname, fname + '.pyo')
            elif data[fname]['pyc']:
                module = imp.load_compiled(modname, fname + '.pyc')
            elif data[fname]['py']:
                module = imp.load_source(modname, fname + '.py')
        else:
            if data[fname]['py']:
                module = imp.load_source(modname, fname + '.py')
            elif data[fname]['pyo']:
                module = imp.load_compiled(modname, fname + '.pyo')
            elif data[fname]['pyc']:
                module = imp.load_compiled(modname, fname + '.pyc')
                
        if module is None:
            continue
            
        for item in module.__dict__:
            curr = getattr(module, item)
            if not isinstance(curr, types.FunctionType):
                continue
            name = curr.__name__
            desc = curr.__doc__
            numargs = curr.__code__.co_argcount
            if numargs != 1:
                continue
            result = {'name': name,
                      'description': desc,
                      'source': module.__file__}
            if name in commands:
                offensive = ''
                for item in actionSpecs:
                    if item['name'] == name:
                        offensive = item['source'] 
                log.warn(_PP_DUPLICATE_ERROR, name, result['description'], 
                         offensive)
            else:
                commands[name] = curr
                actionSpecs.append(result)
    return (commands, actionSpecs)

_POSTPROCESSOR_COMMANDS = _loadPostprocessorCommands()       