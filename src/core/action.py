"""Object-oriented representation of interactions with instruments.

An `Action` is an operation on an instrument to set data, retrieve data, or 
both. The following types of actions are supported by this module.

Action: 
    An `Action` is some operation which should be performed on an instrument. 
    It serves as the base class of several types of container actions. Normally,
    an instance of `Action` will perform some simple read or write operation
    on the instrument.
ActionScan: 
    An `ActionScan` is a container for other `Action` objects which 
    executes its children at each value of some parameter.
ActionSimultaneous: 
    An `ActionSimultaneous` is a container for other `Action` objects which
    spawns threads for each of its children and begins those threads at the same
    time so that they run in parallel.
    
Parameter:
    A `Parameter` is an atomic input or output. It consists of the value of 
    the input (typically set by the user) or output (typically set by the 
    `Instrument` which actually carries out the `Action` which owns the 
    it), information to indicate to the user what it represents, a string to 
    determine how to format its numeric values, and directions regarding how and
    where the data should be saved.
        
"""

from collections import namedtuple
import copy
import logging
import math
import re
from string import Template
import threading
from time import perf_counter, sleep
import xml.etree.ElementTree as ET

from src.core import progress
from src.core.errors import InvalidInputError
from src.tools import general as gentools
from sympy.physics.units.definitions.dimension_definitions import action

log = logging.getLogger('transport')

PARAM_ID = '$'



TOLERANCE = 1E-10


#------------------------------------------------------------- Action - Standard

class Action(object):
    """A single action to perform a simple get/set/query on an instrument.
    
    Parameters
    ----------
    experiment : Experiment
        The `Experiment` object to which this action belongs.
    instrument : Instrument
        The `Instrument` object which will perform this action (though not
        necessarily its children).
    name : str
        A short name with no special characters except (possibly) an 
        underscore, to use for looking up this action.
    description : str
        A short phrase to indicate what this action does.
    inputs : list of Parameter
        A list of `Parameter` objects which this action will pass to the
        instrument.
    outputs : list of Parameter
        A list of `Parameter` objects which the instrument will fill in and
        pass back to this action to be processed and, in most cases, written
        to the appropriate files.
    string : str
        A template string which can be filled in with input values to provide
        the user with a specific description of what this action will do.
    method : instancemethod
        The method bound to `instrument` which will actually carry out this
        action.
    """

    def __init__(self, experiment, instrument, name, description,
                 inputs=None, outputs=None, string=None, method=None):
        """Initialize a new action."""

        self._expt = experiment
        self._inst = instrument

        self._enabled = True

        self._name = name
        self._description = description
        self._templateString = string

        if inputs is None:
            inputs = []
        if outputs is None:
            outputs = []
        self._inputs = inputs
        self._outputs = outputs

        self._method = method
        self._methodString = ''
        if method != None:
            self._methodString = self._method.__name__
        else:
            self._methodString = None

        self._inputSubs = {}
        self._statusMonitor = progress.getStatusMonitor('default')

    def setExperiment(self, experiment):
        """Set the experiment which owns this action and its parameters.
        
        Parameters
        ----------
        newExperiment : Experiment
            The `Experiment` object which should own this action.
        """
        self._expt = experiment
        for parameter in self._inputs + self._outputs:
            parameter.experiment = experiment

    def setStatusMonitor(self, statusMonitor):
        """Set the status monitor for the action.
        
        Parameters
        ----------
        statusMonitor : StatusMonitor
            The new `StatusMonitor` object for this action.
        """
        self._statusMonitor = statusMonitor

    def instantiate(self):
        """Instantiate all parameters, establishing the necessary data storage.
        
        Create the appropriate data bins---based on the default names of the 
        input/output columns and parameters---in the experiment file (using the
        instantiate method of the `Parameter` class).
        """
        for item in self._inputs:
            item.instantiate()
        for item in self._outputs:
            item.instantiate()

    def setEnabled(self, enabled):
        """Set whether this action will actually be executed.
        
        Parameters
        ----------
        enabled : bool
            Whether to execute this action when the experiment is run.
        """
        self._enabled = enabled

    def isEnabled(self):
        """Get whether this action will be executed when the experiment is run.
        
        Returns
        -------
        bool
            Whether this action will actually be executed.
        """
        return self._enabled

    def getName(self):
        """Return the name of the action."""
        return self._name

    def getDescription(self):
        """Return the description of the action."""
        return self._description

    def __str__(self):
        """Return the long description string with values substituted.
        
        Returns
        -------
        str
            An informative description of this action, formed by substituting
            input values into the template string.
        """
        if self._inst is None:
            return 'ActionSequence:'
        if self._enabled:
            ans = ''
        else:
            ans = '(disabled) '
        ans += self._inst.getName() + ': '
        if self._templateString is None:
            return ans + 'do something, or maybe nothing.'
        else:
            subs = {}
            for anInput in self._inputs:
                subs[anInput.name] = str(anInput)

            return ans + Template(self._templateString).substitute(subs)

    def getTreeString(self, depth=0):
        """Return a descriptive string with appropriate indentation."""
        return ''.join(['\t' * depth, str(self), '\n'])

    def printme(self, depth=0):
        """Print a descriptive string with appropriate indentation."""
        print(self.getTreeString(depth))

    def getInstrument(self):
        """Return the instrument bound to this action.
        
        Returns
        -------
        Instrument
            The `Instrument` object bound to this action.
        """
        return self._inst

    def setInstrument(self, inst):
        """Bind an new instrument to this action.
        
        Parameters
        ----------
        inst : Instrument
            The `Instrument` object which will perform the action.
        """
        self._inst = inst
        self._method = eval('self._inst.' + self._methodString)

    def getInstrumentName(self):
        """Return the name of the instrument which will perform the action.
        
        Returns
        -------
        str
            A string indicating the name of the `Instrument` which will
            perform the action.
        """
        return self._inst.getName()

    def setInputValues(self, inputValues):
        """Set the values which will be sent to the ``Instrument`` object."""
        for inputObject, newValue in zip(self._inputs, inputValues):
            inputObject.value = newValue

    def getInputColumns(self):
        """Return the input columns.
        
        Returns
        -------
        list of str
            A list of strings representing the names of the columns or 
            parameters to which the input values will be saved when the action
            is executed.
        """
        ans = []
        for parameter in self._inputs:
            ans.append(parameter.binName)
        return ans

    def setInputColumns(self, inputColumns):
        """Set the input columns.
        
        Set the column names (or parameter names) to which the input values 
        will be saved when the action is executed.
        
        Parameters
        ----------
        inputColumns : list of str
            A list of strings representing the names of the columns or
            parameters to which the input values should be saved when the
            action is executed.
        """
        for anInput, inputColumn in zip(self._inputs, inputColumns):
            anInput.binName = inputColumn

    def getInputProperties(self):
        """Return the input properties for the action.
        
        Returns
        -------
        list of dict
            A list of dictionaries containing information about the input
            parameters. The following keys will be present.
                - description
                - column (name of the column or parameter)
                - value (as a formatted string)
                - allowed
                - formatString
        """
        ans = []
        for parameter in self._inputs:
            name = parameter.binName
            if name is None:
                name = ''
            curr = {'description': parameter.description,
                    'column': name,
                    'value': parameter.getFormattedValue(),
                    'allowed': parameter.allowedValues,
                    'format_string': parameter.formatString
                   }
            ans.append(curr)
        return ans

    def replaceStringInInput(self, inputIndex, original, replacement):
        """Perform a string replacement in one of the inputs for this action.
        
        The primary purpose of this method is to update expressions (either
        for calculations or for conditionals) to reflect changes in the names
        of columns, parameters, or constants.
        
        Parameters
        ----------
        inputIndex : int
            The index in the list of input parameters of the parameter
            where the replacement should take place.
        original : str
            The string which should be replaced.
        replacement : str
            The string which should go in place of `original`.
        """
        try:
            oldval = self._inputs[inputIndex].value
            newval = oldval.replace(original, replacement)
            self._inputs[inputIndex].value = newval
        except IndexError:
            log.error('Replacement fail: %s with %s at index %d',
                      original, replacement, inputIndex)

    def getOutputColumns(self):
        """Return the output column names.
        
        Returns
        -------
        list of str
            A list of strings representing the names of the columns or
            parameters to which the output values will be saved when the action
            is executed.
        """

        ans = []
        for parameter in self._outputs:
            ans.append(parameter.binName)
        return ans

    def setOutputColumns(self, outputColumns):
        """Set the output column names.
        
        Set the column names (or parameter names) to which the output values 
        will be saved when the action is executed.
        """
        for (columnName, parameter) in zip(outputColumns, self._outputs):
            parameter.binName = columnName

    def getOutputProperties(self):
        """Return the output properties for the action.
        
        Returns
        -------
        list of dict
            A list of dictionaries. Each dictionary corresponds to one output
            and contains the following keys:
                - 'description'
                - 'column'
                - 'allowed'
        """
        ans = []
        for parameter in self._outputs:
            name = parameter.binName
            if name is None:
                name = ''
            ans.append({'description': parameter.description,
                        'column': name,
                        'allowed': parameter.allowedValues})
        return ans

    def prepareToExecute(self):
        """Prepare to execute by creating a substitution dictionary."""
        self._inputSubs = {}
        for item in self._inputs:
            self._inputSubs[item.name] = item.value
        if self._method is None:
            self._method = nullFunction

    def execute(self, obeyPause=True):
        """Execute the action.
        
        If the experiment has been aborted, return. If it is paused, wait.
        Otherwise, execute the action, and then save the data to the file.
        
        Parameters
        ----------
        obeyPause : bool
            Whether to wait until the experiment is no longer paused before
            executing the action.
        """
        if not self._enabled:
            return
        if not self._expt.isRunning():
            return
        while obeyPause and self._expt.isPaused():
            sleep(0.2)

        if self._method is not None:
            for inputParameter in self._inputs:
                inputParameter.saveData()
            response = self._method(**self._inputSubs)
            for (outputParameter, value) in zip(self._outputs, response):
                outputParameter.value = value
                outputParameter.saveData()

    def cleanupAfterExecution(self):
        """Cleanup after execution."""
        if self._method is nullFunction:
            self._method = None
        self._inputSubs = {}


    #===========================================================================
    # State-variable commands
    #===========================================================================

    def clone(self):
        """Duplicate this action.
        
        Produce a new `Action` instance---with a new location in 
        memory---which is the same as this one in all respects. This is for 
        copy-and-paste operations.
        """
        newClass = eval(self.__class__.__name__)

        newInputs = cloneParameterList(self._inputs)
        newOutputs = cloneParameterList(self._outputs)

        return newClass(self._expt, self._inst, self._name,
                            self._description,
                            newInputs, newOutputs,
                            self._templateString,
                            self._method)

    def isEqualEnough(self, otherSpec):
        """Determine whether the other action is interchangeable with this one.
        
        To decide whether some action can be reasonably bound to a different
        instrument, consider whether the two actions have the same description,
        the same name, and input and output arrays. Two arrays are said to be
        'the same' if there is a one-to-one mapping of parameters between them
        where the two parameters have the same name, description, and format
        strings.
        """
        otherArgs = otherSpec.args
        if self._description != otherArgs['description']:
            return False
        if len(self._inputs) > 0:
            if (not 'inputs' in otherArgs or
                len(self._inputs) != len(otherArgs['inputs'])):
                return False
            for mine, his in zip(self._inputs, otherArgs['inputs']):
                if (mine.name != his.name or
                    mine.description != his.args['description'] or
                    mine.formatString != his.args['formatString']):
                    return False
        if len(self._outputs) > 0:
            if (not 'outputs' in otherArgs or
                len(self._outputs) != len(otherArgs['outputs'])):
                return False
            for mine, his in zip(self._outputs, otherArgs['outputs']):
                if (mine.name != his.name or
                    mine.description != his.args['description'] or
                    mine.formatString != his.args['formatString']):
                    return False
        return True

    def trash(self):
        """Destroy the action.
        
        Set all of the bin (column or parameter) names to blanks, which removes
        them from the owning experiment's relevant dictionaries.
        """
        for item in self._inputs:
            item.binName = ''
        for item in self._outputs:
            item.binName = ''

    def __getstate__(self):
        """Remove the method reference for pickling purposes."""
        odict = self.__dict__.copy()
        del odict['_method']
#         if '_loopEnterCommands' in odict:
#             del odict['_loopEnterCommands']
#         if '_loopExitCommands' in odict:
#             del odict['_loopExitCommands']
        odict['_statusMonitor'] = None
        return odict

    def __setstate__(self, dictionary):
        """Reinstate the method reference after loading from a file."""
        methodString = dictionary['_methodString']
        if methodString is not None:
            self._method = eval('dictionary["_inst"].' + methodString)
        else:
            self._method = None
        self._statusMonitor = progress.getStatusMonitor('default')
        self.__dict__.update(dictionary)
        
    def getXML(self, parent):
        """Add XML to the tree"""
        action = ET.SubElement(parent, 'action')
        action.set('class', self.__class__.__name__)
        action.set('instrument_name', str(self._inst))
        action.set('name', self._name)
        action.set('enabled', repr(self._enabled))
        print("SUB ACTION")
        print(ET.tostring(action))
        print("END SUB ACTION")
        if isinstance(self, ActionLoopTimed):
            action.set('duration', repr(self._duration))
        elif isinstance(self, ActionLoopIterations):
            action.set('iterations', repr(self._iterations))
        elif isinstance(self, ActionLoopWhile):
            action.set('expression', self._expression)
            action.set('timeout', repr(self._timeout))
        else:
            inputs = ET.SubElement(action, 'inputs')
            for item in self._inputs:
                item.getXML(inputs)
            outputs = ET.SubElement(action, 'outputs')
            for item in self._outputs:
                item.getXML(outputs)
        print("SUB ACTION")
        print(ET.tostring(action))
        print("END SUB ACTION")
        
        if self.allowsChildren():
            children = ET.SubElement(action, 'children')
            for child in self._children:
                child.getXML(children)

    def allowsChildren(self):
        """Return whether this action can have children.
        
        Since members of the `Action` class (i.e. not a derived class) are 
        *simple* actions, they cannot have children.
        """
        return isinstance(self, ActionContainer)


#-------------------------------------------------------- Action - Postprocessor

class ActionPostprocessor(Action):
    """An action for postprocessor events.
    
    The postprocessor actions all follow the same format. They take a
    single argument: a list of tuples representing the files created by the
    experiment. Note that all postprocessor actions are executed together at
    the end of the experiment.
    """
    
    def __init__(self, experiment, instrument, name, description, method,
                 sourceFile):
        super(ActionPostprocessor, self).__init__(experiment, instrument, name,
                                                  description, None, None,
                                                  description, method)
        self._sourceFile = sourceFile
        
    def execute(self, obeyPause=True):
        """Add the action to the experiment's postprocessor action queue.
        
        Parameters
        ----------
        obeyPause : bool
            Whether to wait until the experiment is no longer paused before
            executing the action.
        """
        if not self._enabled:
            return
        while obeyPause and self._expt.isPaused():
            sleep(0.2)
        self._expt.addPostprocessorAction(self)
        
    def executeReal(self):
        """Actually execute the action.
        
        If the experiment has been aborted, return. If it is paused, wait.
        Otherwise, execute the action, and then save the data to the file.
        
        Parameters
        ----------
        obeyPause : bool
            Whether to wait until the experiment is no longer paused before
            executing the action.
        """
        self._method(self._expt.getFiles())        
        
        
    def clone(self):
        """Duplicate this action.
        
        Produce a new `Action` instance---with a new location in 
        memory---which is the same as this one in all respects. This is for 
        copy-and-paste operations.
        """
        newClass = eval(self.__class__.__name__)

        return newClass(self._expt, self._inst, self._name,
                            self._description, self._method, self._sourceFile)
        

#------------------------------------------------------------ Action - Container

class ActionContainer(Action):
    """An abstract action which may have children.
    
    Parameters
    ----------
    experiment : Experiment
        The `Experiment` object to which this action belongs.
    instrument : Instrument
        The `Instrument` object which will perform this action (though not
        necessarily its children).
    name : str
        A short name with no special characters except (possibly) an 
        underscore, to use for looking up this action.
    description : str
        A short phrase to indicate what this action does.
    inputs : list of Parameter
        A list of `Parameter` objects which this action will pass to the
        instrument.
    outputs : list of Parameter
        A list of `Parameter` objects which the instrument will fill in and
        pass back to this action to be processed and, in most cases, written
        to the appropriate files.
    string : str
        A template string which can be filled in with input values to provide
        the user with a specific description of what this action will do.
    method : instancemethod
        The method bound to `instrument` which will actually carry out this
        action.
    """

    def __init__(self, experiment, instrument, name, description, inputs=None,
                 outputs=None, string='Do nothing.', method=None):
        super(ActionContainer, self).__init__(experiment, instrument, name,
                                              description, inputs, outputs,
                                              string, method)
        self._children = []

    def setExperiment(self, newExperiment):
        """Set the owner of this action, its children, and its parameters.
        
        Parameters
        ----------
        newExperiment : Experiment
            The `Experiment` object which should own this action, its children,
            and its parameters.
        """
        super(ActionContainer, self).setExperiment(newExperiment)
        for child in self._children:
            child.setExperiment(newExperiment)

    def setStatusMonitor(self, newStatusMonitor):
        """Set the status monitor for the action and its children.
        
        Parameters
        ----------
        statusMonitor : StatusMonitor
            The new `StatusMonitor` object for this action.
        """
        super(ActionContainer, self).setStatusMonitor(newStatusMonitor)
        for child in self._children:
            child.setStatusMonitor(newStatusMonitor)

    def appendChild(self, child):
        """Add a child to the end of the list.
        
        Parameters
        ----------
        child : Action
            The child to add to the end of the list.
        """
        child.instantiate()
        self._children.append(child)

    def prependChild(self, child):
        """Add a child to the beginning of the list.
        
        Parameters
        ----------
        child : Action
            The child to add to the beginning of the list.
        """
        child.instantiate()
        self._children.insert(0, child)

    def insertChild(self, index, child):
        """Add an action to the list of children at a specified position.
        
        Parameters
        ----------
        index : int
            The position at which to add the child. If `index` is out of range,
            the action is appended to the list.
        child : Action
            The action to add to the list.
        """
        child.instantiate()
        if 0 <= index < len(self._children):
            self._children.insert(index, child)
        else:
            self.appendChild(child)

    def insertChildBefore(self, child, positionAction):
        """Insert a child before another child.
        
        Parameters
        ----------
        child : Action    
            The action which should be inserted.
        positionAction : Action
            The action before which the new child should be added. If this
            action does not exist, `child` will be prepended to the list.
        """
        child.instantiate()
        try:
            index = self._children.index(positionAction)
            self._children.insert(index, child)
        except ValueError:
            self._children = [child] + self._children

    def insertChildAfter(self, child, positionAction):
        """Insert a child before another child.
        
        Parameters
        ----------
        child : Action    
            The action which should be inserted.
        positionAction : Action
            The action after which the new child should be added. If this
            action does not exist, `child` will be appended to the list.
        """
        child.instantiate()
        try:
            index = self._children.index(positionAction)
            self._children.insert(index, child)
            self._children.insert(index + 1, child)
        except ValueError:
            self._children.append(child)

    def replaceChild(self, index, child):
        """Replace the child action at a given position
        
        Parameters
        ----------
        index : int
            The position of the action to replace.
        child : Action
            The action which should go in the specified position.
        """
        child.instantiate()
        self._children[index] = child

    def setChildren(self, replacementChildren):
        """Replace the list of children with a new list.
        
        Parameters
        ----------
        replacementChildren : list of Action
            A list of actions which should be used as children of this action.
            It will replace any actions already considered to be children.
        """
        for child in replacementChildren:
            child.instantiate()
        self._children = replacementChildren

    def getChildren(self):
        """Return the list of children.
        
        Returns
        -------
        list of Action
            The list of actions which are considered to be children of this
            action.
        """
        return self._children

    def removeChild(self, child):
        """Remove the a child action from the list.
        
        Parameters
        ----------
        child : Action
            The action to remove from the list.
        """
        self._children.remove(child)

    def removeChildByIndex(self, index):
        """Remove the action at the specified position.
        
        Parameters
        ----------
        index : int
            The position of the child to remove.
        """
        del self._children[index]

    def removeChildren(self):
        """Empty the list of actions."""
        self._children = []

    def trash(self):
        """Destroy all children, then destroy the container."""
        for child in self._children:
            child.trash()
        super(ActionContainer, self).trash()


    #===========================================================================
    # Execution
    #===========================================================================
    def prepareToExecute(self):
        """Prepare all children for execution.
        
        Preparing for execution means generating dictionaries for substitution
        into instrument methods and performing various other relevant 
        optimization-related actions.
        """
        for child in self._children:
            child.prepareToExecute()

    def execute(self, obeyPause=True):
        """Execute all children objects sequentially."""
        if not self._enabled:
            return
        for child in self._children:
            child.execute(obeyPause)

    def executePass(self, obeyPause=True):
        """Execute the container using its superclass's method."""
        super(ActionContainer, self).execute(obeyPause)

    def cleanupAfterExecution(self):
        """Cleanup temporary data after execution."""
        for child in self._children:
            child.cleanupAfterExecution()

    #===========================================================================
    # Information strings
    #===========================================================================

    def getTreeString(self, depth=0):
        """Return a descriptive string for the container, including children."""
        ansList = [super(ActionContainer, self).getTreeString(depth)]
        for child in self._children:
            ansList.append(child.getTreeString(depth + 1))
        return ''.join(ansList)

    def printme(self, depth=0):
        """Return a descriptive string for the container, including children."""
        print(self.getTreeString(depth))


    #===========================================================================
    # State variable commands
    #===========================================================================

    def clone(self):
        """Copy this action, including its children.
        
        Produce a new `Action` instance---with a new location in 
        memory---which is the same as this one in all respects. Then do the same
        for all children, adding them to the new container. This is for 
        copy-and-paste operations.
        """
        newSelf = super(ActionContainer, self).clone()
        newSelf.setChildren([child.clone() for child in self._children])
        return newSelf


#----------------------------------------------------------------- Action - Scan

class ActionScan(ActionContainer):
    """A action which executes other actions at multiple values of a parameter.
        
    Create a scanning action---one which executes a series of other actions
    (children) at each value of some varied parameter. The only input should
    be a list of tuples, where each tuple contains three numbers: the
    starting and ending bounds and step size for a scan (in that order). 
        
    Parameters
    ----------
    experiment : Experiment
        The `Experiment` object to which this action belongs.
    instrument : Instrument
        The `Instrument` object which will perform this action (though not
        necessarily its children).
    name : str
        A short name with no special characters except (possibly) an 
        underscore, to use for looking up this action.
    description : str
        A short phrase to indicate what this action does.
    inputs : list of Parameter
        A list of `Parameter` objects which this action will pass to the
        instrument. For an `ActionScan`, this list should contain a single
        element.
    outputs : list of Parameter
        A list of `Parameter` objects which the instrument will fill in and
        pass back to this action to be processed and, in many cases, written
        to the appropriate files.
    string : str
        A template string which can be filled in with input values to provide
        the user with a specific description of what this action will do.
    method : instancemethod
        The method bound to `instrument` which will actually carry out this
        action.
    """

    def __init__(self, experiment, instrument, name, description, inputs=None,
                 outputs=None, string='Do nothing.', method=None):
        """Create a new ActionScan."""
        super(ActionScan, self).__init__(experiment, instrument, name,
                                         description, inputs, outputs, string,
                                         method)
        self._expandedProfile = []

    def __str__(self):
        """Return an informative string about the action, including ranges.
        
        Return a string describing the action and its bound instrument with all
        input parameters substituted. The returned string includes the initial
        and final points as well as the step size for each sub-range.
        """
        if self._enabled:
            ans = ''
        else:
            ans = '(disabled) '
        ans += self._inst.getName() + ': '
        if self._templateString is None:
            return ans + 'do something, or maybe nothing.'
        else:
            values = self._inputs[0].getFormattedValue()
            length = len(values)
            ans = ans + self._templateString
            for (i, value) in enumerate(values):
                ans = ans + ' from %s to %s in steps of %s' % value
                if i < length - 1 and length > 2:
                    ans = ans + ','
                if i == length - 2:
                    ans = ans + ' and'
        return ans + '.'

    def prepareToExecute(self):
        """Prepare the ActionScan to execute by expanding the range."""
        self._expandedProfile = []

        inputParameter = self._inputs[0]
        profiles = inputParameter.value
        steps = []
        for profile in profiles:
            initial = profile[0]
            final = profile[1]
            dif = float(final - initial)
            step = dif / math.fabs(dif) * math.fabs(profile[2])
            same = ActionScan.zeroWithinTolerance(dif, TOLERANCE)
            nostep = ActionScan.zeroWithinTolerance(step, TOLERANCE)
            if same or nostep:
                rng = [initial]
            else:
                rng = gentools.frange(initial, final, step)
            steps.extend(rng)
        for step in steps:
            subParameter = Parameter(self._expt,
                                     inputParameter.name,
                                     inputParameter.description,
                                     inputParameter.formatString,
                                     inputParameter.binName,
                                     inputParameter.binType,
                                     step)
            stepString = self._templateString + ' At ' + str(subParameter) + '.'
            subAction = Action(self._expt, self._inst, self._name,
                               self._description, [subParameter], [],
                               stepString, self._method)
            self._expandedProfile.append(subAction)
            subAction.prepareToExecute()
        super(ActionScan, self).prepareToExecute()

    def execute(self, obeyPause=True):
        """Execute the ActionScan.
        
        Expand the scans into the individual values for which the action's
        method will be executed, and then execute the method with each of those
        values.
        """
        if not self._enabled:
            return
        if not self._expt.isRunning():
            return
        while obeyPause and self._expt.isPaused():
            sleep(0.2)

        for action in self._expandedProfile:
            action.execute(obeyPause)
            for child in self._children:
                child.execute()

    def cleanupAfterExecution(self):
        """Cleanup temporary data after execution."""
        self._expandedProfile = []
        super(ActionScan, self).cleanupAfterExecution()

    @staticmethod
    def zeroWithinTolerance(dif, tolerance):
        """Return whether a number is small enough to be treated as zero.
        
        Parameters
        ----------
        dif : float
            The number to compare to zero.
        tolerance : float
            The maximum difference between two numbers for them to be called
            equal.
        """
        dif = math.fabs(float(dif))
        tol = math.fabs(float(tolerance))
        return dif < tol


#------------------------------------------------------- Action - Loop - By Time

class ActionLoopTimed(ActionContainer):
    """A container which repeats its children for a specified length of time.
    
    Parameters
    ----------
    experiment : Experiment
        The `Experiment` instance which owns this loop.
    instrument : Instrument
        The `Instrument` which will carry out this action.
    name : str
        A short name with no special characters except (possibly) an 
        underscore, to use for looking up this action.
    description : str
        A short phrase to indicate what this action does.
    duration : float 
        The amount of time, in seconds, after which the loop should stop.
        
    Notes
    -----
    At the end of each cycle, the system determines how much time has elapsed.
    If the time elapsed is greater than or equal to the specified time, the
    loop is interrupted and the sequence resumes. Therefore, it is possible
    (and even likely) that the loop will run somewhat longer than specified. 
    Precisely how much longer will be determined by the run time of the 
    children.
    """

    def __init__(self, experiment, instrument, name, description, duration):
        """Create a new timed action loop."""

        super(ActionLoopTimed, self).__init__(experiment, instrument, name,
                                              description)

        self._duration = duration

    def getDuration(self):
        """Return the time after which the loop will stop.
        
        Returns
        -------
        float
            The time, in seconds, after which the loop will stop running.
            Depending on the run time of the children, the loop may run longer
            than the specified time.
        """
        return self._duration

    def setDuration(self, duration):
        """Set how long the loop should run.
        
        Parameters
        ----------
        duration : float
            The length of time after which the loop will stop running. The
            loop may run longer than the specified time, depending on the run
            time of the children. But after the specified time, no new 
            iterations of the loop will be started.
        """
        self._duration = duration

    def __str__(self):
        """Return an informative string about the action.
        
        Returns
        -------
            A string describing this action and the instrument which is bound
            to it, substituting all relevant settings.
        """
        if self._enabled:
            ans = ''
        else:
            ans = '(disabled) '
        return (ans + 'Execute the following actions for %.3f s.' %
                self._duration)

    def execute(self, obeyPause=True):
        """Execute the loop action."""
        if not self._enabled:
            return
        if not self._expt.isRunning():
            return
        while obeyPause and self._expt.isPaused():
            sleep(0.2)

        startTime = perf_counter()
        currTime = startTime
        while currTime - startTime < self._duration:
            if __debug__:
                log.debug('Looping: %.3f s of %.3f s elapsed',
                          currTime, self._duration)
            for child in self.getChildren():
                child.execute(obeyPause)
            currTime = perf_counter()

    def clone(self):
        """Return a copy of this action."""
        newSelf = ActionLoopTimed(self._expt, self._inst, self._name,
                                  self._description, self._duration)
        newSelf.setChildren([child.clone() for child in self._children])
        return newSelf


#------------------------------------------ Action - Loop - Number of Iterations

class ActionLoopIterations(ActionContainer):
    """A container which repeats its children a specified number of times.
    
    Parameters
    ----------
    experiment : Experiment
        The `Experiment` instance which owns this loop.
    instrument : Instrument
        The `Instrument` which will carry out the action (though not necessarily
        its children).
    name : str
        A short name with no special characters except (possibly) an 
        underscore, to use for looking up this action.
    description : str
        A short phrase to indicate what this action does.
    iterations : int 
        The number of times the children should be executed.
    """

    def __init__(self, experiment, instrument, name, description, iterations):
        """Create a new iterations-based action loop."""

        super(ActionLoopIterations, self).__init__(experiment, instrument, name,
                                                   description)

        self._iterations = iterations

    def getIterations(self):
        """Return the number of times the loop's children will be executed.
        
        Returns
        -------
        int
            The number of times the children will be executed.
        """
        return self._iterations

    def setIterations(self, iterations):
        """Set how long the loop should run.
        
        Parameters
        ----------
        iterations : int
            The number of times the children should be executed.
        """
        self._iterations = iterations

    def __str__(self):
        """Return an informative string about the action.
        
        Returns
        -------
            A string describing this action and the instrument which is bound
            to it, substituting all relevant settings.
        """
        if self._enabled:
            ans = ''
        else:
            ans = '(disabled) '
        return (ans + 'Execute the following actions %d times.' %
                self._iterations)

    def execute(self, obeyPause=True):
        """Execute the loop action."""
        if not self._enabled:
            return
        if not self._expt.isRunning():
            return
        while obeyPause and self._expt.isPaused():
            sleep(0.2)

        for cycle in range(self._iterations):
            if __debug__:
                log.debug('Looping: %d of %d iterations completed.',
                          cycle, self._iterations)
            for child in self._children:
                child.execute(obeyPause)

    def clone(self):
        """Return a copy of this action."""
        newSelf = ActionLoopIterations(self._expt, self._inst, self._name,
                                       self._description, self._iterations)
        newSelf.setChildren([child.clone() for child in self._children])
        return newSelf


#--------------------------------------------------- Action - Loop - Conditional

class ActionLoopWhile(ActionContainer):
    """A container which repeats its children a specified number of times.
    
    Parameters
    ----------
    experiment : Experiment
        The `Experiment` instance which owns this loop.
    instrument : Instrument
        The `Instrument` which will carry out the action (though not necessarily
        its children).
    name : str
        A short name with no special characters except (possibly) an 
        underscore, to use for looking up this action.
    description : str
        A short phrase to indicate what this action does.
    expression : str
        An expression which can evaluate to a boolean. The loop continues
        as long as `expression` evaluates to `True`.
    timeout : float
        The maximum amount of time, in seconds, to wait for the expression
        to evaluate to `True`. If `timeout` is set to `None`, the loop will
        run until `expression` becomes false or until the experiment is
        aborted.
        
        This is a fail-safe to prevent infinite loops (for example, if you set
        it to run until a desired temperature is reached, but the cryostat
        is unable to reach that temperature).
    """

    def __init__(self, experiment, instrument, name, description, expression,
                 timeout=None):
        """Create a new conditional (while) loop."""

        super(ActionLoopWhile, self).__init__(experiment, instrument, name,
                                              description)

        self._expression = expression
        self._timeout = timeout

    def getExpression(self):
        """Return the conditional which determines the number of iterations.
        
        Returns
        -------
        str
            The expression which will be evaluated to a boolean value to
            determine whether to keep looping. If it evaluates to `True`, the
            loop continues. Otherwise, it terminates.
        """
        return self._expression

    def setExpression(self, expression):
        """Set the conditional expression which determines when to stop.
        
        Parameters
        ----------
        expression : str
            The expression which will be evaluated to a boolean value to
            determine whether to keep looping. If it evaluates to `True`, the
            loop continues. Otherwise, it terminates.
        """
        self._expression = expression

    def getTimeout(self):
        """Return the maximum time to wait for the condition to become `False`.
        
        Returns
        -------
        float
            The maximum time in seconds that the system will wait for the
            condition to return `False`. If it is set to `None`, the loop
            will run until the condition returns `False` or until the
            experiment is aborted.
        """
        return self._timeout

    def setTimeout(self, timeout):
        """Set the maximum time to wait for the condition to become false.
        
        Parameters
        ----------
        timeout : float
            The maximum time in seconds that the system will wait for the
            condition to return `False`. If it is set to `None`, the loop
            will run until the condition returns `False` or until the
            experiment is aborted.
        """
        self._timeout = timeout

    def __str__(self):
        """Return an informative string about the action.
        
        Returns
        -------
            A string describing this action and the instrument which is bound
            to it, substituting all relevant settings.
        """
        if self._enabled:
            ans = ''
        else:
            ans = '(disabled) '
        if self._timeout is None:
            return (ans + 'Execute the following actions while [%s] is True.'
                            % self._expression)
        return (ans + 'Execute the following actions while [%s] is True. ' +
                'Timeout=%.3fs') % (self._expression, self._timeout)

    def execute(self, obeyPause=True):
        """Execute the loop action."""
        if not self._enabled:
            return

        if not self._expt.isRunning():
            return
        while obeyPause and self._expt.isPaused():
            sleep(0.2)

        startTime = perf_counter()
        maxtime = startTime + self._timeout
        while self._expt.evaluateConditional(self._expression, True):
            for child in self.getChildren():
                child.execute(obeyPause)

            if self._timeout is not None and perf_counter() >= maxtime:
                log.info('Loop timed out for expression [%s].', 
                         self._expression)
                break

    def clone(self):
        """Return a copy of this action."""
        newSelf = ActionLoopWhile(self._expt, self._inst, self._name,
                                  self._description, self._expression,
                                  self._timeout)
        newSelf.setChildren([child.clone() for child in self._children])
        return newSelf


#---------------------------------------------- Action - Loop - Manual Interrupt

class ActionLoopUntilInterrupt(ActionContainer):
    """A container to execute its children until manually interrupted.
        
    Parameters
    ----------
    experiment : Experiment
        The `Experiment` instance which owns this loop.
    instrument : Instrument
        The `Instrument` which will carry out this action.
    name : str
        A short name with no special characters except (possibly) an 
        underscore, to use for looking up this action.
    description : str
        A short phrase to indicate what this action does.
    """

    def __init__(self, experiment, instrument, name, description):
        """Create a new indefinitely-running loop."""
        super(ActionLoopUntilInterrupt, self).__init__(experiment, instrument,
                                                       name, description)

        self._loopEnterCommands = []
        self._loopExitCommands = []

    def setLoopCommands(self, loopEnterCommands=None, loopExitCommands=None):
        """Set the commands to execute when the loop begins and finishes.
        
        Parameters
        ----------
        loopEnterCommands : list of Command
            The `Command` objects to execute before any other actions when the
            sequence enters the loop.
        loopExitCommands : list of Command
            The `Command` objects to execute after any other actions when the
            loop has been interrupted.
        """
        if loopEnterCommands is not None:
            self._loopEnterCommands = loopEnterCommands
        if loopExitCommands is not None:
            self._loopExitCommands = loopExitCommands


    def __str__(self):
        """Return an informative string about the action.
        
        Returns
        -------
            A string describing this action and the instrument which is bound
            to it, substituting all relevant settings.
        """
        if self._enabled:
            ans = ''
        else:
            ans = '(disabled) '
        return ans + 'Repeat the following actions until interrupted.'

    def execute(self, obeyPause=True):
        """Execute the loop action."""
        if not self._enabled:
            return
        if not self._expt.isRunning():
            return
        while obeyPause and self._expt.isPaused():
            sleep(0.2)

        for command in self._loopEnterCommands:
            command.execute()

        if __debug__:
            log.debug('Looping: wait for user interrupt.')

        while self._expt.isRunning() and not self._expt.isInterrupted():
            if __debug__:
                log.debug('Still looping.')
            for child in self.getChildren():
                child.execute(obeyPause)

        if __debug__:
            log.debug('Loop interrupted.')

        for command in self._loopExitCommands:
            command.execute()

    def clone(self):
        """Return a copy of this action."""
        newSelf = ActionLoopUntilInterrupt(self._expt, self._inst, self._name,
                                           self._description)
        newSelf.setChildren([child.clone() for child in self._children])

        newSelf.setLoopCommands(list(self._loopEnterCommands),
                                list(self._loopExitCommands))

        return newSelf

    def __getstate__(self):
        """Remove the enter/exit commands from the list."""
        odict = self.__dict__.copy()
        odict['_loopEnterCommands'] = None
        odict['_loopExitCommands'] = None
        odict['_statusMonitor'] = None
        del odict['_method']
        return odict


#--------------------------------------------------- Action - Simultaneous block

class ActionSimultaneous(ActionContainer):
    """A container which executes all of its children in parallel.
    
    Parameters
    ----------
    experiment : Experiment
        The `Experiment` object which owns this action container.
    instrument : Instrument
        The `Instrument` which will perform this action.
    name : str
        A short name with no special characters except (possibly) an 
        underscore, to use for looking up this action.
    description : str
        A short phrase to indicate what this action does.
    """

    def __init__(self, experiment, instrument, name, description):
        """Create a simultaneous action block."""
        super(ActionSimultaneous, self).__init__(experiment, instrument,
                                                 name, description)

    def __str__(self):
        """Return an informative string about the action.
        
        Returns
        -------
            A string describing this action and the instrument which is bound
            to it, substituting all relevant settings.
        """
        if self._enabled:
            ans = ''
        else:
            ans = '(disabled) '
        return (ans + 'Begin executing all of the following actions at ' +
                'the same time.')

    def execute(self, obeyPause=True):
        """Execute the children simultaneously.
        
        If the experiment has been stopped, return. If the experiment is paused,
        wait until it is not. Otherwise, create threads for all of the action's
        children. Then tell the `Experiment` to activate the temporary
        buffer for storing the data. Then start the threads, and wait for them
        to finish. Finally, tell the `Experiment` that the simultaneously-
        running actions are finished so that it will save the data and empty
        the buffer.
        
        Parameters
        ----------
        obeyPause : bool
            The indication of whether the action should wait if the experiment
            is paused.
        """
        if not self._enabled:
            return

        if not self._expt.isRunning():
            return
        while obeyPause and self._expt.isPaused():
            sleep(0.2)

        threads = []
        for child in self._children:
            thread = ActionThread(child, obeyPause)
            threads.append(thread)

        self._expt.activateTemporaryBuffer()
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        threads = []
        self._expt.deactivateTemporaryBuffer()


    def clone(self):
        """Return a copy of this action."""
        newSelf = ActionSimultaneous(self._expt, self._inst, self._name,
                                     self._description)
        newSelf.setChildren([child.clone() for child in self._children])
        return newSelf


#--------------------------------------------------------------------- Parameter

class Parameter(object):
    """An input/output and information to identify, format, and describe it.
    
    Parameters
    ----------
    experiment : Experiment
        The `Experiment` object which owns the `Action` for which this is a
        parameter.
    name : str
        A short, one-word name used for substitutions into the `Action` object's
        descriptive template string.
    description : str
        A relatively short phrase describing the purpose of this parameter.
    formatString : str
        A standardized string indicating how values should be formated (e.g.,
        "%.3e" for an exponential-format number with three decimal places).
        If this parameter represents a scan profile, the formatString should
        end with '[]'.
    binName : str
        The default name of the data column or parameter slot into which
        this parameter's data should be saved.
    binType : str
        The default **type** of slot for saving data. It may be 'column',
        'parameter', if the data is not to be saved by default, or `None` or ''.
    value : various
        The default value of the parameter. Its type depends on the parameter
        (it could be a floating-point number, an integer, a boolean, a string,
        or a list of 3-tuples of integers or floats).
    allowed : list of str
        A list of strings representing the allowed values for the parameter. If
        it is `None`, any type-appropriate value will be accepted.
    instantiate : bool
        Whether to immediately alter the experiment's column or parameter
        database.
    """

    def __init__(self, experiment, name, description, formatString='%.6e',
                 binName=None, binType=None, value=0, allowed=None,
                 instantiate=False, isScan=False):
        """Create a new parameter."""

        self.expt = experiment

        self.name = name
        self.description = description

        self.instantiated = instantiate
        if instantiate:
            self.__binName = None
            self.binType = binType
            if binName is not None:
                self.binName = binName
        else:
            self.__binName = binName
            self.binType = binType

        self.__value = value

        self.formatString = formatString.strip()
        self.isScanProfile = isScan
        self.coerce = str
        self._establishCoersion()
        self.__allowedValues = allowed


    #===========================================================================
    # Data storage bin control
    #===========================================================================

    def instantiate(self):
        """Instantiate the parameter.
        
        If this method has not been run previously, set the bin names using the
        method (as opposed to simply changing the value of the variable), which
        passes the name change to the experiment to update the data storage
        dictionaries.
        """
        if not self.instantiated:
            self.instantiated = True
            tempname = self.binName
            self.__binName = None
            self.binName = tempname

    @property
    def binName(self):
        """Return the name of the storage bin.
        
        If the value is to be stored in a column, return the column name simply.
        If it is to be stored as a parameter, return the parameter name prefixed
        by the _PARAM_. Return `None` if the data is not to be saved.
        """
        if self.binType is None or self.__binName is None:
            return None
        elif self.binType == 'parameter':
            return PARAM_ID + self.__binName
        return self.__binName
    @binName.setter
    def binName(self, newName):
        """Set the name of the relevant storage bin.
        
        Set the name and type of the storage bin associated with this
        parameter. Then update the owning experiment accordingly.
        
        Parameters
        ----------
        newName : str
            The desired name for the storage bin associated with this
            parameter. If it starts with `PARAM_ID` (which is currently the
            dollar sign), the bin type will be set to 'parameter' and the
            leading `PARAM_ID` will be removed. Otherwise, the bin type
            will be set to 'column'.
        """
        oldname = self.__binName
        oldtype = self.binType
        if newName is None or newName.strip() == '':
            self.__binName = self.binType = None
        elif newName.startswith(PARAM_ID):
            self.__binName = newName[len(PARAM_ID):]
            self.binType = 'parameter'
        else:
            self.__binName = newName
            self.binType = 'column'
        if self.instantiated:
            self.expt.handleStorageBins(oldname, oldtype,
                                        self.__binName, self.binType)

    #===========================================================================
    # Data values
    #===========================================================================

    @property
    def value(self):
        """Return a copy of the value of the parameter."""
        if self.isScanProfile:
            return copy.deepcopy(self.__value)
        return self.__value
    @value.setter
    def value(self, newValue):
        """Set the value of the parameter.
        
        Parameters
        ----------
        newValue
            The value to which the parameter should be set. Depending on the
            context, it might be a str, an int, a float, or a list.
            
        Raises
        ------
        InvalidInputError
            An error to indicate that `newValue` cannot be cast to the type
            this parameter is expecting.
        """
        try:
            self.__value = self.coerce(newValue)
        except (ValueError, TypeError) as err:
            raise InvalidInputError(err.args[0], self.description, newValue)

    def __str__(self):
        """Return a string representing the formatted value of the parameter."""
        return self.formatString % self.__value

    def getFormattedValue(self):
        """Return the value formatted as a string."""
        if self.isScanProfile:
            ans = []
            for item in self.__value:
                ans.append((self.formatString % item[0],
                            self.formatString % item[1],
                            self.formatString % item[2]))
            return ans
        else:
            return str(self)

    def saveData(self):
        """Save the parameter to the relevant file (data or parameter)."""
        self.expt.saveData(self.binType, self.__binName, str(self))

    @property
    def allowedValues(self):
        """Return a copy of the list of allowed values."""
        if self.__allowedValues is None:
            return None
        return list(self.__allowedValues)


    #===========================================================================
    # Comparison and state variable commands
    #===========================================================================

    def _establishCoersion(self):
        """Create the coerce method to get input values to be the right type."""
        pattern = re.compile(r'%[-+0]{0,3}\d*\.?\d*(\w)')
        typeStringMatch = pattern.match(self.formatString)
        self.coerce = None
        if typeStringMatch:
            typeString = typeStringMatch.group(1)

            if typeString == 'e' or typeString == 'E' or typeString == 'f':
                self.coerce = float
            elif typeString == 'd' or typeString == 'i' or typeString == 'u':
                self.coerce = int
        if self.coerce is None:
            self.coerce = str

        if self.isScanProfile:
            oldcoerce = self.coerce
            def listCoerce(profile):
                """Helper for coercing lists."""
                ans = []
                for item in profile:
                    ans.append((oldcoerce(item[0]),
                                oldcoerce(item[1]),
                                oldcoerce(item[2])))
                return ans
            self.coerce = listCoerce

    def clone(self):
        """Return a copy of this parameter."""
        return Parameter(self.expt,
                         self.name,
                         self.description,
                         self.formatString,
                         self.__binName,
                         self.binType,
                         copy.deepcopy(self.__value),
                         copy.copy(self.__allowedValues),
                         False,
                         self.isScanProfile)

    def getXML(self, parent):
        """Add XML to tree."""
        actionparameter = ET.SubElement(parent, 'actionparameter')
        actionparameter.set('name', self.name)
        actionparameter.set('value', repr(self.__value))
        actionparameter.set('bin_name', str(self.__binName))
        actionparameter.set('bin_type', str(self.binType))
        
    def __getstate__(self):
        """Remove the method reference for pickling purposes."""
        odict = self.__dict__.copy()
        del odict['coerce']
        return odict

    def __setstate__(self, dictionary):
        """Reinstate the method reference after loading from a file."""
        self.__dict__.update(dictionary)
        self._establishCoersion()


#---------------------------------------------------- Action and Parameter Specs

ActionSpec = namedtuple('ActionSpec', ['name', 'cls', 'args'])
ParameterSpec = namedtuple('ParameterSpec', ['name', 'args'])

def constructAction(actionSpec):
    """Construct an action from an action specification.
    
    Parameters
    ----------
    actionSpec : ActionSpec
        An instance of the `namedtuple` class `ActionSpec`.
    
    Returns
    -------
    Action
        The instance of `Action` or one of its subclasses specified by
        `actionSpec`.
    """
    newArgs = actionSpec.args
    newArgs['name'] = actionSpec.name
    isScan = actionSpec.cls == ActionScan
    if 'inputs' in newArgs:
        newInputs = []
        for inputItem in newArgs['inputs']:
            newInputs.append(constructParameter(inputItem, isScan))
        newArgs['inputs'] = newInputs
    if 'outputs' in newArgs:
        newOutputs = []
        for outputItem in newArgs['outputs']:
            newOutputs.append(constructParameter(outputItem, isScan))
        newArgs['outputs'] = newOutputs

    return actionSpec.cls(**newArgs)

def constructParameter(parameterSpec, isScan=False):
    """Construct a parameter from a parameter specification.
    
    Parameters
    ----------
    parameterSpec : ParameterSpec
        An instance of the `namedtuple` class `ParameterSpec`.
    
    Returns
    -------
    Parameter
        The instance of `Parameter` specified by `parameterSpec`.
    """
    args = list(parameterSpec.args.items()) + [('name', parameterSpec.name),
                                         ('isScan', isScan)]
    return Parameter(**dict(args))


#------------------------------------------------------------- Utility Functions

def nullFunction():
    """Do nothing."""
    pass

def cloneParameterList(parameterList):
    """Clone a list of input or output parameters."""
    ans = []
    for parameter in parameterList:
        ans.append(parameter.clone())
    return ans

def coerceIntThroughFloat(number):
    """Convert a number to a float and then to an int.
    
    Certain kinds of string literals cannot be cast directly to integers. This
    function takes such a string and converts it to a float and then to an
    integer.
    
    Parameters
    ----------
    number : str
        A string containing a number which should be cast to an integer.
    """
    return int(float(number))


#----------------------------------------------------------------- Action Thread

class ActionThread(threading.Thread):
    """A thread for executing sub-actions without blocking."""

    def __init__(self, action, obeyPause=True):
        """Create a new thread for executing an action."""
        super(ActionThread, self).__init__()

        self.action = action
        self.obeyPause = obeyPause

    def run(self):
        """Execute the action."""
        self.action.execute(self.obeyPause)
