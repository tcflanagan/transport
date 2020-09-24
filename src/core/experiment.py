"""Experiment data and execution manager.

An `Experiment` is an object which keeps tracks of all the parts which compose
an actual measurement, including instruments, the actions performed on them, the
data returned by them, and real-time graphs of the data.
"""

import logging
import math
import numpy as np
import os
import threading
import time
import xml.etree.ElementTree as ET
from xml.dom import minidom

from src import settings
from src.core import instrument as instmod
from src.core.action import (ActionContainer, ActionThread,
                             ActionLoopUntilInterrupt, PARAM_ID)
from src.core.errors import (InstrumentInUseError, GeneralExperimentError)
from src.core.graph import AbstractGraphManager
from src.tools.general import formatReSTHeading
import src.tools.parsing as parsing
from dns.name import root

log = logging.getLogger('transport')

MARK_CONSTANT = '@'
MARK_PARAMETER = '$'
MARK_COLUMN = '#'
SUB_CONSTANT = '@(%s)'
SUB_PARAMETER = '$(%s)'
SUB_COLUMN = '#(%s)'

_SUPPORTED_FUNCTIONS = {'abs': 'abs',
                        'sin': 'math.sin',
                        'cos': 'math.cos',
                        'tan': 'math.tan',
                        'arcsin': 'math.asin',
                        'arccos': 'math.acos',
                        'arctan': 'math.atan',
                        'arctan2': 'math.atan2',
                        'deg2rad': 'math.radians',
                        'rad2deg': 'math.degrees',
                        'sinh': 'math.sinh',
                        'cosh': 'math.cosh',
                        'tanh': 'math.tanh',
                        'arcsinh': 'math.asinh',
                        'arccosh': 'math.acosh',
                        'arctanh': 'math.atanh',
                        'pow': 'math.pow',
                        'sqrt': 'math.sqrt',
                        'exp': 'math.exp',
                        'log': 'math.log',
                        'log10': 'math.log10',
                        'ceil': 'math.ceil',
                        'floor': 'math.floor'}

_EXTS_DATA = settings.EXTS_DATA
_EXTS_PARAMETERS = settings.EXTS_PARAMETERS
_EXTS_IMAGE = settings.EXTS_IMAGE

class Experiment(object):
    """The main driver class of an experiment.

    The `Experiment` class is responsible for managing instruments; the actions
    those instruments should perform; and the collection, storage, saving, and
    graphing of data.
    """

    def __init__(self):
        log.info('Creating an experiment...')

        # The database of constants defined before the experiment is run. All
        # values will be coerced to floats.
        self._constants = {}

        # The list of instruments in the experiment, initialized to contain
        # the two built-in instruments.
        self._instruments = [instmod.System(self), instmod.Postprocessor(self)]

        # A tree structure for containing the experiment's action sequence.
        self._sequence = ActionContainer(self, None, 'root', None)

        # A dictionary of parameters
        self._parameters = {}
        # A list for storing parameter data before the file has been opened.
        self._parameterBuffer = []

        # A dictionary for column data. They keys are the names of the columns,
        # and the values are sub-dictionaries with the following keys:
        # curr : str
        #     The most recently acquired value, already formatted.
        # colindex : int
        #     The position in the **ordered** array where the data from this
        #     column should go.
        # graphx : list of `Graph`
        #     The list of graphs which should receive x-values whenever this
        #     column is updated.
        # graphy : list of `Graph`
        #     The list of graphs which should receive y-values whenever this
        #     column is updated.
        # graphadd : list of `Graph`
        #     The list of graphs which should produce next plots whenever
        #     this column is updated.
        self._columns = {}
        # An array containing column names in the order in which they should be
        # written to the file.
        self._columnArray = []
        self._lastColumnIndex = -1

        # The experiment's list of `Graph` objects.
        self._graphs = []

        # A buffer for holding data while a simultaneous block is running.
        self._tempBuffer = None

        # The basic file name, without an extension, for forming the filenames
        # for the actual filenames, and the extension to be used for the data
        # files.
        self._filenameBase = ''
        self._extension = '.xdat'
        # Files to which data will be written.
        self._dataFile = None
        self._parameterFile = None
        self._graphFile = None
        # List of tuples containing the paths of all files which have been
        # opened during the experiment.
        self._allFiles = []

        # Flags describing the status of the experiment. In order, they are
        # [running, paused, interrupted]. The third is for stopping the
        # indefinite-loop type actions.
        self._status = [False, False, False]

        # A StatusMonitor for displaying experiment history to the user.
        self._statusMonitor = None

        # Lists of commands to execute before and after the experiment. They
        # are set by whatever creates the experiment, and their primary purpose
        # is to update indicators in a GUI.
        self._preSequenceActions = None
        self._postSequenceActions = None

        # Lists of commands to execute before and after an interruptable loop.
        # They are set by whatever creates the experiment.
        self._loopEnterCommands = None
        self._loopExitCommands = None
        
        # A list of ActionPostprocessor objects which will be executed at the
        # end of the experiment (during the post-sequence).
        self._postprocessorActions = []

        # A subclass of `AbstractGraphManager` for managing the threads for
        # the graphs, an instance of that class, and the frame which should
        # be the parent for the graphing frames.
        self._graphManagerClass = AbstractGraphManager
        self._graphManager = None
        self._parentFrame = None


    #-------------------------------------------------------- Instrument control

    def getInstrumentStrings(self):
        """Return the names of the instruments in this experiment.

        Returns
        -------
        list of str
            A list of strings representing the names of the `Instrument` objects
            which used in this experiment.
        """
        return [instrument.getName() for instrument in self._instruments]

    def addInstrument(self, instrument):
        """Add an instrument to this experiment.

        Parameters
        ----------
        instrument : Instrument
            The `Instrument` object which should be added to the experiment.
        """
        self._instruments.append(instrument)

    def removeInstrument(self, instrument):
        """Remove an instrument from this experiment.

        Parameters
        ----------
        instrument : Instrument
            The instrument which should be removed from the experiment.
        """
        uses = self._checkForInstrumentUsage(instrument)
        if len(uses) == 0:
            self._instruments.remove(instrument)
        else:
            raise InstrumentInUseError(uses)

    def getInstrument(self, index):
        """Return the instrument at the specified index.

        Parameters
        ----------
        index : int
            The index of the `Instrument` which should be returned.
            
        Returns
        -------
        Instrument
            The instrument located at the specified position.
        """
        return self._instruments[index]

    def getEqualEnoughInstruments(self, action):
        """Return a list of instruments which implement the given action.

        Sometimes, the user may want to change the instrument which carries out
        a particular action. However, in order to change the instrument, it is
        necessary that the new instrument should have the *ability* to carry out
        the action.

        This method returns a list of dictionaries with information about the
        instruments (and their respective actions) which could potentially be
        used as a replacement for the instrument associated with the specified
        action.

        Parameters
        ----------
        action : Action
            The `Action` instance whose `Instrument` the user wants to replace.

        Returns
        -------
        list of dict
            A list of dictionaries. Each dictionary represents information about
            one `Action` which could replace `action`. The elements of the
            dictionary are the following:
                instrument_index
                    The index of the instrument in the experiment's list.
                instrument
                    The actual `Instrument` object.
                instrument_name
                    The name of the instrument.
                action_index
                    The index of the `Action` object which can replace `action`.
                    The index corresponds to the location in the list of
                    actions returned by the instrument's `getActions` method. 
                action
                    An `ActionSpec` representing the `Action` which can replace
                    the specified `action`.

        Notes
        -----
        Two `Action` objects are said to be "equal enough" if they have the same
        description and the same parameters. Two `Parameter` objects are said
        to be the same if they are identical in all *immutable* aspects (that
        is, they have the same name, the same description, and the same format
        string).
        """
        result = []
        for index, inst in enumerate(self._instruments):
            equalEnough = inst.getEqualEnoughAction(action)
            if equalEnough is not None:
                result.append({'instrument_index': index,
                               'instrument': inst,
                               'instrument_name': inst.getName(),
                               'action_index': equalEnough[0],
                               'action': equalEnough[1]})
        return result


    #------------------------------------------------------ Constants management

    def setConstant(self, name, value):
        """Set the value of a constant, creating it if necessary.
        
        Parameters
        ----------
        name : str
            The name of the constant whose value should be set.
        value : float
            The new value for the constant.
        """
        self._constants[name] = value

    def removeConstant(self, name):
        """Delete a defined constant.
        
        Parameters
        ----------
        name : str
            The name of the constant which should be deleted.
        """
        del self._constants[name]

    def getConstant(self, name):
        """Return the value of the named constant.
        
        Parameters
        ----------
        name : str
            The name of the constant whose value is desired.
        
        Returns
        -------
        float
            The value of the requested constant, or `None` if the constant
            does not exist.
        """
        try:
            return self._constants[name]
        except KeyError:
            return None

    def getAllConstants(self):
        """Return a copy of the constants dictionary.
        
        Returns
        -------
        dict
            A dictionary of constants in which the keys (str) are the names
            of the constants, and the values (float) are the values associated 
            with the relevant constant.
        """
        return self._constants.copy()

    def renameConstant(self, oldName, newName):
        """Rename the specified constant.
        
        Rename a constant and update all expressions in conditional loops
        and calculations to reflect the name change.
        
        Parameters
        ----------
        oldName : str
            The name of the constant to whose name should be changed.
        newName : str
            The new name of the constant.
        """
        self._constants[newName] = self._constants.pop(oldName)
        self._updateEvaluations(oldName, 'constant', newName, 'constant')
        
    def addDefaultConstants(self):
        """Add pi and the natural logarithm base to the constant dictionary."""
        self._constants['pi'] = math.pi
        self._constants['e'] = math.e


    #-------------------------------------------------------- Data storage setup

    def handleStorageBins(self, oldName, oldType, newName, newType):
        """Automatically handle the addition, removal, or renaming of a bin.

        If the new name is `None` or '', delete the old bin. If the old name is
        `None` or '', create the new bin. If the old name and the new name are
        are both non-trivial, the old name is changed to the new name, and the
        types are switched if necessary.
                
        Parameters
        ----------
        oldName : str
            The name of the column or parameter to be removed. If none is to be
            removed, this should be either `None` or an empty string.
        oldType : str
            The type ("column" or "parameter") of the bin to be removed. If a
            bin is to be created and none removed, this value is ignored.
        newName : str
            The name of the column or parameter to be created. If none is to be
            created, this should be either `None` or an empty string.
        newType : str
            The type ("column" or "parameter") of the bin to be created. If
            none is to be created, this value is ignored.
        """
        if oldName is None:
            oldName = ''
        if newName is None:
            newName = ''
        oldName = oldName.strip()
        newName = newName.strip()

        if oldName == newName and oldType == newType:
            return

        if oldName == '':
            self._addStorageBin(newName, newType)
            log.debug('Adding %s %s', newType, newName)
            return
        if newName == '':
            self._deleteStorageBin(oldName, oldType)
            log.debug('Removing %s %s', oldType, oldName)
            return

        self._renameStorageBin(oldName, oldType, newName, newType)
        log.debug('Replacing %s %s with %s %s',
                  oldType, oldName, newType, newName)
        log.debug('New columns are: ' + str(list(self._columns.keys())))

    def _addStorageBin(self, name, binType):
        """Create a column or parameter.
        
        If the bin to create is a column, and a missing column of the same
        name is the reason a graph is disabled, bind the new column to the
        graph and reenable it.
        
        Parameters
        ----------
        name : str
            The name of the bin to create.
        binType : str
            The type of the bin to create. It may be either 'parameter' or
            'column'. If `binType` is not recognized, it defaults to 'column'.
        """
        name = name.strip()

        if binType == 'parameter':
            if name not in self._parameters:
                self._parameters[name] = 0
                return True
        else:
            if name not in self._columns:
                self._columns[name] = {'curr'     : '',
                                       'colindex' : None,
                                       'graphx'   : [],
                                       'graphy'   : [],
                                       'graphadd' : []}
                for graph in self._graphs:
                    if not graph.isEnabled():
                        reenable = True
                        graphColumns = graph.getColumns()
                        for graphColumn in graphColumns:
                            if (graphColumn not in self._columns and
                                graphColumn is not None):
                                reenable = False
                        if reenable:
                            graph.setEnabled(True)
                            if name == graphColumns[0]:
                                self._columns[name]['graphx'].append(graph)
                            if name == graphColumns[1]:
                                self._columns[name]['graphy'].append(graph)
                            if name == graphColumns[2]:
                                self._columns[name]['graphadd'].append(graph)
                            log.info('Reenabling graph %s.', graph.getTitle())
                return True
        return False

    def _renameStorageBin(self, oldName, oldType, newName, newType):
        """Rename a storage bin.
         
        Rename a storage bin, and then update all calculations, conditional
        expressions, and graphs to reflect the change in name. If after 
        renaming one instance of `oldName` there are no `Action` instances 
        referring to `oldName`, then delete all data bins associated with 
        `oldName`.
        
        If an attempt is made to change a column to a parameter and if that
        column is bound to a graph, disable the graph.
        
        Parameters
        ----------
        oldName : str
            The name of the bin to rename.
        oldType : str
            The type of the bin to rename, which may be either 'parameter' or
            'column'.
        newName : str
            The new name for the bin.
        newType : str
            The new type for the bin, which may be either 'parameter' or
            'column'.
        """

        if oldType == 'column':
            graphs = (self._columns[oldName]['graphx'],
                      self._columns[oldName]['graphy'],
                      self._columns[oldName]['graphadd'])

        self._addStorageBin(newName, newType)
        if self._deleteStorageBin(oldName, oldType, False):
            self._updateEvaluations(oldName, oldType, newName, newType)
            if oldType == 'column':
                if newType == 'column':
                    for graph in graphs[0]:
                        graph.updateColumnsIfNecessary(oldName, newName)
                    for graph in graphs[1]:
                        graph.updateColumnsIfNecessary(oldName, newName)
                    for graph in graphs[2]:
                        graph.updateColumnsIfNecessary(oldName, newName)
                    self._columns[newName]['graphx'] = graphs[0]
                    self._columns[newName]['graphy'] = graphs[1]
                    self._columns[newName]['graphadd'] = graphs[2]
                if newType == 'parameter':
                    for graph in graphs[0] + graphs[1] + graphs[2]:
                        graph.setEnabled(False)
                        log.warn(('Graph %s is being disabled because '
                                  'it requires data from the column %s, '
                                  'which is being changed to a parameter.'),
                                 graph.getTitle(), oldName)

    def _deleteStorageBin(self, name, binType, checkGraphs=True):
        """Delete the specified storage bin.
        
        Delete the specified storage bin if and only if only one action in the
        sequence refers to the bin at the time the command is issued.
        
        If a column bound to a graph is deleted, then disable the bound
        graph, unless this behavior is overridden by setting `checkGraphs` to
        `False`.
        
        Parameters
        ----------
        name : str
            The name of the storage bin to remove.
        binType : str
            The type of the storage bin to remove. Allowed values are "column"
            and "parameter".
        checkGraphs : bool
            Whether to check the graph list to see whether any of the graphs
            require the column which is about to be deleted. If this flag is
            set to `True` and a graph does require the column, that graph
            will be disabled.
            
        Returns
        -------
        bool
            Whether the bin was actually deleted.
        """
        graphs = []
        if checkGraphs:
            graphs = (self._columns[name]['graphx'] +
                      self._columns[name]['graphy'] +
                      self._columns[name]['graphadd'])

        num = self._scanSequenceForStorageName(name, binType)
        if num < 1:
            if binType == 'parameter' and name in self._parameters:
                del self._parameters[name]
            elif binType == 'column' and name in self._columns:
                for graph in graphs:
                    graph.setEnabled(False)
                    log.warn(('Graph %s is being disabled because it '
                              'receives data from column %s, which '
                              'is being deleted.'), graph.getTitle(), name)
                del self._columns[name]
            return True
        return False

    def _prepareColumns(self):
        """Order the columns.
        
        Automatically scan through the list of actions to put the columns into
        the appropriate order, so that the order in the data file reflects the
        order in which the actions are executed. After this is run, each element
        in the column dictionary should contain an index which points to a
        position in the column array. The column array is filled in with the
        names of the columns in the order in which they will be written to the
        data file.
        """
        num = [0]
        def numberColumns(act):
            """Number the columns used by the specified action."""
            if act is None:
                return
            cols = act.getInputColumns() + act.getOutputColumns()
            for col in cols:
                if col not in self._columnArray and col in self._columns:
                    self._columns[col]['colindex'] = num[0]
                    self._columnArray.append(col)
                    if __debug__:
                        log.debug('Numbering column %s to %d.', col, num[0])
                    num[0] += 1

        self._traverse(numberColumns)

    def getStorageBinNames(self):
        """Get the names of all data storage bins.
        
        Returns
        -------
        list of str
            A list of the names of all constants in the experiment.
        list of str
            A list of the names of all columns in the experiment.
        list of str
            A list of the names of all parameters in the experiment.
        """
        return (list(self._constants.keys()), list(self._columns.keys()),
                list(self._parameters.keys()))

    def getStorageBinNamesString(self):
        """Return a formatted string representing the storage bin names.
        
        Returns
        -------
        str
            A three-line string, where the first line is a list of constants,
            the second is a list of columns, and the third is a list of
            parameters.
        """
        return ('constants: %s\ncolumns: %s\nparameters: %s' %
                self.getStorageBinNames())
    
    def getColumnDetails(self):
        """Return a formatted string containing a list of column details.
        
        Returns
        -------
        str
            A string containing details about the current status of each data
            column.
        """
        allElements = []
        for column in self._columns:
            data = self._columns[column]
            elements = ['Column %s ----------------' % column,
                        'Current:   %s' % data['curr'],
                        'Index:     %s' % data['colindex'],
                        'Graph X:   %s' % 
                        ['[' + g.getTitle() + ']' for g in data['graphx']],
                        'Graph Y:   %s' % 
                        ['[' + g.getTitle() + ']' for g in data['graphy']],
                        'Graph Add: %s' % 
                        ['[' + g.getTitle() + ']' for g in data['graphadd']]]
            allElements.append('\n'.join(elements))
        return '\n'.join(allElements)
            

    #------------------------------------------------------- Actual data storage

    def activateTemporaryBuffer(self):
        """Create a temporary buffer for simultaneous blocks.
        
        Create a temporary buffer, with the same keys as the main column
        dictionary, for storing data while running a simultaneous block. 
        This alleviates the danger of getting goofy garbage in the data file 
        due to, e.g., race conditions. The principal problem this averts is
        writing data to the file prematurely, which would happen if the actions
        return in the wrong order.
        """
        self._tempBuffer = dict.fromkeys(self._columns)
        for column in self._columns:
            self._tempBuffer[column] = []

    def deactivateTemporaryBuffer(self):
        """Save the data from the temporary buffer, then destroy the buffer.
        
        Take the data stored in the temporary buffer while running the 
        simultaneous block. If the same amount of data has been added for each
        column, add them to the appropriate column bins. Otherwise, save them
        as a separate file in the same folder as the data. Then destroy the 
        temporary buffer.
        """
        tempBuffer = self._tempBuffer
        self._tempBuffer = None

        sameSize = True
        length = None
        toKeep = {}
        indices = []
        for name, column in tempBuffer.items():
            columnLength = len(column)
            if columnLength > 0:
                toKeep[name] = column
                indices.append((name, self._columns[name]['colindex']))
                if length is None:
                    length = columnLength
                elif length != columnLength:
                    sameSize = False

        if sameSize:
            sortedColumns = sorted(indices, key=lambda colname: colname[1])
            for index in range(length):
                for column in sortedColumns:
                    name = column[0]
                    value = tempBuffer[name][index]
                    self.saveData('column', name, value)
        else:
            log.error('Unable to merge simultaneous block columns. '
                      'The data is being saved to a separate file for you '
                      'to sort out.')
            with open(self._filenameBase + '_simblock.txt', 'a') as simFile:
                simFile.write('-------------')
                for name, column in toKeep.items():
                    simFile.write(name)
                    simFile.write(str(column))

    def saveData(self, binType, binName, value):
        """Add data returned from actions to the appropriate dictionary.
        
        Take the input from the execute commands bound to an `Action` object
        and add it to the data column dictionary, the parameter dictionary, or 
        the temporary buffer as appropriate.
        
        Parameters
        ----------
        binType : str
            Where the data should go (either "parameter" or "column").
        binName : str
            The name of the column or parameter.
        value : str
            The **formatted** value to be saved to the bin specified by the
            above parameters.
        """
        if binType is None or binType == '' or binName == '':
            return
        if binType == 'parameter':
            self._parameters[binName] = value
            try:
                self._parameterFile.write('%s: %s\n' % (binName, value))
            except (AttributeError, IOError):
                log.warn(('Cannot write %s: %s. Perhaps the parameter file ' +
                          'is not open.'), binName, value)
                self._parameterBuffer.append('%s: %s\n' % (binName, value))
        elif self._tempBuffer is not None:
            self._tempBuffer[binName].append(value)
        else:
            cols = self._columns
            columnIndex = cols[binName]['colindex']
            if columnIndex <= self._lastColumnIndex:
                self._dataFile.write('\t'.join([cols[index]['curr'] for index
                                                in self._columnArray]) + '\n')
            self._lastColumnIndex = columnIndex
            currcol = cols[binName]
            currcol['curr'] = value
            for graph in currcol['graphx']:
                graph.addX(value)
            for graph in currcol['graphy']:
                graph.addY(value)
            for graph in currcol['graphadd']:
                graph.flagNewPlot()

    def checkExpression(self, expr):
        """Check the syntactic validity of the supplied expression.
        
        Substitute numeric values for columns, constants, and parameters
        and attempt to evaluate the given expression to determine whether the
        syntax of the expression is correct.
        
        Parameters
        ----------
        expr : str
            The expression to evaluate in string form.
            
        Returns
        -------
        bool
            `True` if the expression's syntax is valid, or `False` otherwise.
        """
        try:
            for name in self._constants:
                key = SUB_CONSTANT % name
                expr = expr.replace(key, str(self._constants[name]))
            for name in self._columns:
                key = SUB_COLUMN % name
                expr = expr.replace(key, str(np.random.rand()))
            for name in self._parameters:
                key = SUB_PARAMETER % name
                expr = expr.replace(key, str(np.random.rand()))
            for name in _SUPPORTED_FUNCTIONS:
                newName = _SUPPORTED_FUNCTIONS[name]
                expr = expr.replace(name + '(', newName + '(')
                expr = expr.replace(name + ' (', newName + '(')
            float(eval(expr))
            return True
        except SyntaxError:
            return False

    def evaluateExpression(self, expr, conditional=False):
        """Evaluate a given expression.
        
        Substitute all defined constants and the most recent values of all 
        columns and parameters into `expr`, evaluate it, and return the
        outcome.

        This is mainly used by the `Calculate` action from the `System` class.

        Parameters
        ----------
        expr : str
            A string giving the expression which should be evaluated.
        conditional : bool
            Whether the expression should evaluate to a boolean (`True` or
            `False`). The default is `False`, meaning that the expression should
            evaluate to a number.
        
        Returns
        -------
        float or bool
            If `conditional` is `True`, the boolean to which the supplied
            expression evaluates when known data have been substituted.
            Otherwise, the **number** to which the supplied expression 
            evaluates.
        """
        try:
            for name in self._constants:
                key = SUB_CONSTANT % name
                expr = expr.replace(key, str(self._constants[name]))
            if self._tempBuffer is not None:
                for name in self._tempBuffer:
                    if len(self._tempBuffer[name]) > 0:
                        key = SUB_COLUMN % name
                        expr = expr.replace(key, self._tempBuffer[name][-1])
            for name in self._columns:
                key = SUB_COLUMN % name
                expr = expr.replace(key, self._columns[name]['curr'])
            for name in self._parameters:
                key = SUB_PARAMETER % name
                expr = expr.replace(key, self._parameters[name])
            for name in _SUPPORTED_FUNCTIONS:
                newName = _SUPPORTED_FUNCTIONS[name]
                expr = expr.replace(name + '(', newName + '(')
                expr = expr.replace(name + ' (', newName + '(')
            ans = eval(expr)
            if conditional:
                if isinstance(ans, bool):
                    return ans
            else:
                return float(ans)
        except (TypeError, ValueError, SyntaxError) as err:
            if conditional:
                log.error('Cannot evaluate conditional [%s]. '
                          'Returning False.\n>>>>%s', expr, err)
                return False
            log.error('Cannot evaluate expression [%s]. Returning NaN\n>>>>%s.',
                      expr, err)
        return float('nan')
        

    #----------------------------------------------------------- Action sequence

    def getActionRoot(self):
        """Return the root of the action tree.
        
        Returns
        -------
        ActionContainer
            The `ActionContainer` object which serves as the root of the
            sequence tree.
        """
        return self._sequence
            
    def addPostprocessorAction(self, action):
        """Add a Postprocessor action to be executed after the experiment.
        
        Parameters
        ----------
        action : ActionPostprocessor
            An action to execute at the end of the experiment.
        """
        self._postprocessorActions.append(action)

    def _checkSequenceForErrors(self):
        """Check the sequence for problems.
        
        Returns
        -------
        list of tuple of str
            A list of tuples, where each tuple contains two elements. The first
            is either 'warning' or 'error', depending on the severity of the 
            problem, and the second is a message giving more detail about the
            problem.
        """
        fileOpen = [False]
        answer = []
        definedColumns = []
        definedParameters = []

        def checkAuxActions(action):
            """Check each action for problems."""
            if not action.isEnabled():
                return
            name = action.getName()
            inputProperties = action.getInputProperties()
            outputProperties = action.getOutputProperties()
            if action.getName() == 'set_file':
                value = inputProperties[0]['value']
                if not os.path.exists(os.path.normpath(value)):
                    answer.append('Folder "%s" does not exist.' % value)
                fileOpen[0] = True
            elif name == 'calculate' or name == 'loop_while':
                if name == 'calculate':
                    expression = inputProperties[0]['value']
                else:
                    expression = action.getExpression()
                allData = (list(self._constants.keys()),
                           list(self._columns.keys()),
                           list(self._parameters.keys()))
                definedData = (definedColumns, definedParameters)
                answer.extend(_checkExpressionForErrors(expression, allData,
                                                        definedData))
                if not self.checkExpression(expression):
                    answer.append(('error', 'Syntax error in expression [%s].'
                                   % expression))
            newBins = _getCreatedBins(inputProperties, outputProperties)
            definedColumns.extend(newBins[0])
            definedParameters.extend(newBins[1])
            if not fileOpen[0] and len(definedColumns) > 0:
                answer.append(('error', 'Writing to columns before ' +
                               'a file is opened: ' + str(definedColumns)))
        self._traverse(checkAuxActions)

        for item in self._graphs:
            toDisable = False
            for column in item.getColumns():
                if column is not None and column not in definedColumns:
                    toDisable = True
            if toDisable:
                item.setEnabled(False)
            if not item.isEnabled():
                answer.append(('warning', 'Graph [%s] is disabled.' %
                               item.getTitle()))

        return answer

    def _checkForInstrumentUsage(self, instrument):
        """Return a list of actions which use the specified instrument.
        
        Parameters
        ----------
        instrument : Instrument
            The `Instrument` object whose usage is to be determined.
            
        Returns
        -------
        list of str
            A list of strings representing the actions which rely on
            `instrument`.
        """
        usageData = [instrument, []]
        def checkAux(action):
            """Helper function to check a single instrument."""
            if action.getInstrument() is usageData[0]:
                usageData[1].append(str(action))
        self._traverse(checkAux)
        return usageData[1]

    def _scanSequenceForStorageName(self, name, binType):
        """Count occurrences of the specified bin in the action sequence.
        
        Search through the action tree for references to the bin named `name` of
        type `binType`, and return the total number of matches.
        
        Parameters
        ----------
        name : str
            The name of the bin for which to search.
        binType : str
            The type of the bin named `name`. May be either 'column' or
            'parameter'.
            
        Returns
        -------
        int
            The number of times the bin of type `binType` and name `name`
            occurs in the action sequence tree.
        """
        name = name.strip()
        if binType == 'parameter':
            name = PARAM_ID + name
        count = [0]

        def counter(action):
            """Helper function to count occurrences in each action."""
            colnames = action.getInputColumns() + action.getOutputColumns()
            for colname in colnames:
                if colname == name:
                    count[0] += 1
        self._traverse(counter)

        return count[0]

    def _updateEvaluations(self, oldName, oldType, newName, newType):
        """Change evaluations to reflect bin name changes.
         
        Run through the actions defined in the experiment. Update any 
        calculation or conditional which refers to the bin `oldName` to refer 
        to the bin `newName` instead.
        
        Parameters
        ----------
        oldName : str
            The old name of the data bin.
        oldType : str
            The type of the old bin, which may be 'constant', 'column', or
            'parameter'.
        newName : str
            The type name of the data bin.
        newType : str
            The type of the new bin, which may be 'constant', 'column', or
            'parameter'.
        """
        if oldType == 'constant':
            mOld = SUB_CONSTANT % oldName
        elif oldType == 'parameter':
            mOld = SUB_PARAMETER % oldName
        else:
            mOld = SUB_COLUMN % oldName

        if newType == 'constant':
            mNew = SUB_CONSTANT % newName
        elif newType == 'parameter':
            mNew = SUB_PARAMETER % newName
        else:
            mNew = SUB_COLUMN % newName

        columnData = [mOld, mNew]

        def updateName(act):
            """Helper to update the name in a single conditional."""
            if (act.getDescription() == 'Calculate' or
                act.getDescription() == 'Conditional interrupt'):
                act.replaceStringInInput(0, columnData[0], columnData[1])

        self._traverse(updateName)


    #------------------------------------------------------------ Graphs control

    def getGraphStrings(self):
        """Return a list of the names of the experiment's graphs.
        
        Returns
        -------
        list of str
            A list of strings, where each string is the name of a graph in the
            experiment.
        """
        return [graph.getTitle() for graph in self._graphs]

    def getGraphStringsAndStates(self):
        """Return the names of graphs and whether each graph is enabled.
        
        Returns
        -------
        str
            The title of the graph.
        bool
            Whether the graph is enabled.
        """
        return [(graph.getTitle(), graph.isEnabled()) for graph in self._graphs]

    def getGraph(self, index):
        """Return the graph at the specified index.
        
        Parameters
        ----------
        index : int
            The position of the desired graph in the experiment's list.
        
        Returns
        -------
        Graph
            The graph at the specified position.
        """
        return self._graphs[index]

    def addGraph(self, graph):
        """Add a graph to the experiment.
        
        Store `graph` in the list, and bind it to the columns which will 
        supply its data.
        
        Parameters
        ----------
        graph : Graph
            A `Graph` object to add to the experiment.
        """
        cols = graph.getColumns()
        self._graphs.append(graph)
        self._columns[cols[0]]['graphx'].append(graph)
        self._columns[cols[1]]['graphy'].append(graph)
        if cols[2] is not None:
            self._columns[cols[2]]['graphadd'].append(graph)

    def removeGraph(self, graph):
        """Remove a graph from the experiment
        
        First, remove `graph` from all columns which reference it. Then
        delete it from the list of graphs.
        
        Parameters
        ----------
        graph : Graph
            The `Graph` object to remove from the list.
        """
        for col in self._columns:
            if graph in self._columns[col]['graphx']:
                self._columns[col]['graphx'].remove(graph)
            if graph in self._columns[col]['graphy']:
                self._columns[col]['graphy'].remove(graph)
            if graph in self._columns[col]['graphadd']:
                self._columns[col]['graphadd'].remove(graph)
        self._graphs.remove(graph)

    def updateGraphColumns(self, graph):
        """Fix the column dictionary so that the graph is in the right slots.
        
        Remove the graph from the list (which includes unbinding it from the
        old columns), and then add it back, automatically placing the graph in 
        the slots for the newly-specified columns.
        
        Parameters
        ----------
        graph : Graph
            The `Graph` object whose associated columns have changed.
        """
        self.removeGraph(graph)
        self.addGraph(graph)

    def _updateGraphLabels(self, oldLabel, newLabel):
        """Update the axes' labels to reflect column name changes.
        
        Parameters
        ----------
        oldLabel : str
            The name of the column from which the graph previously received
            data.
        newLabel : str
            The name of the column from which the graph should now receive
            data.
        """
        for graph in self._graphs:
            graph.updateColumnsIfNecessary(oldLabel, newLabel)


    #-------------------------------------------------------------- File control

    def setFilenames(self, basePath):
        """Set the filenames and open the files.
        
        Use the supplied `baseName` to generate names for the data and
        parameter files, as well as the graph image file if applicable, by
        appending the appropriate extensions. Then open the files. Write
        the column headers to the data file and dump the parameter buffer
        into the parameter file.
        
        Important: All folders in the path to the files must already exist.
        
        Parameters
        ----------
        basePath : str
            The path where the data files should be stored. It should include
            all folders as well as a filename. The extension may be left off,
            but the only extensions that will be understood are ".xdat" (the
            default), ".txt" and ".dat".
        """

        if self._dataFile is not None:
            self._closeFiles()
        
        found = False
        for ext in _EXTS_DATA:
            dotext = '.' + ext
            if basePath.endswith(dotext):
                self._extension = ext
                self._filenameBase = basePath[:-len(dotext)]
                found = True
        if not found:
            self._filenameBase = basePath
            self._extension = _EXTS_DATA[0]

        # Open the data file and write the headers.
        filename = self._filenameBase + '.' + self._extension
        log.info('Opening data file: ' + filename)
        #self._dataFile = open(filename, 'w', 0)
        #self._dataFile = open(filename, 'w')
        self._dataFile = open(filename, 'w', 1)
        headers = [None] * len(self._columnArray)
        for columnName in self._columns:
            headers[self._columns[columnName]['colindex']] = columnName
        self._dataFile.write('\t'.join(headers) + '\n')

        # Open the parameter file and dump the parameter buffer.
        filename = self._filenameBase + '.' + _EXTS_PARAMETERS[0]
        log.info('Opening parameter file: ' + filename)
        #self._parameterFile = open(filename, 'w', 0)
        #self._parameterFile = open(filename, 'w')
        self._parameterFile = open(filename, 'w', 1)
        for line in self._parameterBuffer:
            self._parameterFile.write(line + '\n')
        self._parameterBuffer = []
        
    def _closeFiles(self):
        """Close the files.
        
        First, write the last row of data to the file (since writing to the
        file is normally determined by collisions, the last line will never
        be written without this). Then close the data and parameter files if
        they are open. Then attempt to save any graphs.
        """
        if self._dataFile is not None:
            self._dataFile.write('\t'.join([self._columns[name]['curr'] for
                                            name in self._columnArray]) + '\n')
            self._dataFile.close()
            self._dataFile = None

        if self._parameterFile is not None:
            self._parameterFile.close()
            self._parameterFile = None

        try:
            self._graphManager.saveGraphs(self._filenameBase + '.' + 
                                                    _EXTS_IMAGE[0])
            self._allFiles.append((self._filenameBase + '.' + self._extension,
                                   self._filenameBase + '.' + 
                                            _EXTS_PARAMETERS[0],
                                   self._filenameBase + '.' + _EXTS_IMAGE[0]))
        except (ValueError, NotImplementedError, AttributeError) as err:
            self._allFiles.append((self._filenameBase + '.' + self._extension,
                                   self._filenameBase + '.' + 
                                            _EXTS_PARAMETERS[0],
                                   None))
            log.error('Problem with graph manager. Graphs cannot be saved.' +
                      '\n>>>>%s', err)

    def getFiles(self):
        """Return a list of all files used so far in the experiment.
        
        Returns
        -------
        list of tuple of str
            A list of tuples. Each tuple represents one set of files opened and
            contains three strings. The first is a data file, the second is
            a parameter file, and the third is a graph file (the third can be
            `None` if no graph file was saved).
        """
        return list(self._allFiles)

    #------------------------------------------ Interaction with user interfaces

    def setInteractionParameters(self, **kwargs):
        """Set how the experiment should communicate with the outside.
        
        These parameters can be set only using keyword arguments.
        
        Any parameter which takes a list can be disabled by setting it to an
        empty list. Any parameter which takes something else can be disabled
        by setting it to `None`.
        
        Parameters
        ----------
        parentFrame : Frame
            A graphical frame which will be passed as the parent for the
            graph frames, if applicable.
        graphManagerClass : GraphManager
            A class (not an instance) to use for managing the graph threads,
            if applicable.
        graphManager : GraphManager
            A GraphManager **object** for managing the graph threads. If this
            is set, it will be preferred over creating a graphManagerClass.
        preSequenceCommands : list of Command
            A list of `Command` objects which should be executed immediately
            before the experiment begins to run.
        postSequenceCommands : list of Command
            A list of `Command` objects which should be executed immediately
            after the experiment has finished.
        statusMonitor : statusMonitor
            The new `StatusMonitor` object for the instruments to display
            information to the user.
        loopEnterCommands : list of Command
            The `Command` objects to execute before any other actions when the
            sequence enters an interruptable loop.
        loopExitCommands : list of Command
            The `Command` objects to execute after any other actions when an
            interruptable loop has been interrupted.
        """
        if 'parentFrame' in kwargs:
            self._parentFrame = kwargs['parentFrame']
        if 'graphManager' in kwargs:
            self._graphManager = kwargs['graphManager']
        if 'graphManagerClass' in kwargs:
            self._graphManagerClass = kwargs['graphManagerClass']
        if 'preSequenceCommands' in kwargs:
            self._preSequenceActions = kwargs['preSequenceCommands']
        if 'postSequenceCommands' in kwargs:
            self._postSequenceActions = kwargs['postSequenceCommands']
        if 'statusMonitor' in kwargs:
            self._statusMonitor = kwargs['statusMonitor']
        if 'loopEnterCommands' in kwargs:
            self._loopEnterCommands = kwargs['loopEnterCommands']
        if 'loopExitCommands' in kwargs:
            self._loopExitCommands = kwargs['loopExitCommands']


    #------------------------------------------------------ Experiment execution

    def run(self, errorCheck=True):
        """Perform the pre-sequence actions and begin the experiment.
        
        Parameters
        ----------
        errorCheck : bool
            Whether to check for errors before beginning execution. The default
            is `True`.
            
        Raises
        ------
        GeneralExperimentError
            An exception containing a list of warnings and errors about
            problems with the experiment. This is only raised if `errorCheck`
            is `True`.
        """
        if not self._status[0]:
            if errorCheck:
                errors = self._checkSequenceForErrors()
                if len(errors) > 0:
                    log.error('Errors detected.')
                    for error in errors:
                        log.error('Severity: [%s]. Message: [%s]', *error)
                    raise GeneralExperimentError(errors)
            else:
                log.warn('Running experiment without checking for errors.')
            self._preSequence()
            mainThread = ExecutionThread(self)
            mainThread.start()
        else:
            log.error('Cannot run: the sequence is already running.')

    def pause(self):
        """Pause the experiment."""
        log.info('Pausing the experiment.')
        self._status[1] = True

    def resume(self):
        """Unpause the experiment."""
        log.info('Resuming the experiment.')
        self._status[1] = False

    def abort(self):
        """Stop the experiment and run the post-sequence actions."""
        if self._status[0]:
            self._status[0] = False
            time.sleep(1)
            self._postSequence()

    def interruptLoop(self):
        """Interrupt a running loop."""
        self._status[2] = True

    def isRunning(self):
        """Return whether the experiment is running.
        
        Returns
        -------
            Whether the experiment is running.
        """
        return self._status[0]

    def isPaused(self):
        """Return whether the experiment has been paused.
        
        Returns
        -------
        bool
            Whether the experiment is paused.
        """
        return self._status[1]

    def isInterrupted(self):
        """Return whether the next loop should be interrupted.
        
        Returns
        -------
        bool
            Whether a loop has been manually interrupted.
        """
        if self._status[2]:
            self._status[2] = False
            return True
        return False

    def _preSequence(self):
        """Prepare the experiment to execute."""
        log.info('Starting pre-sequence...')

        # Set the "running" flag to true.
        self._status[0] = True

        # Execute any pre-sequence actions specified by the user.
        if self._preSequenceActions is not None:
            try:
                for action in self._preSequenceActions:
                    action.execute()
            except TypeError:
                log.error('Invalid pre-sequence action list')

        # Initialize the instruments.
        self._parameterBuffer.append(formatReSTHeading('Instruments', 0))
        for instrument in self._instruments:
            instrument.initialize()
            if self._statusMonitor is not None:
                instrument.setStatusMonitor(self._statusMonitor)
            self._parameterBuffer.append(instrument.getInformation())
            self._parameterBuffer.append('-----')

        # Write the defined data to the parameter buffer.
        self._parameterBuffer.append(formatReSTHeading('Constants', 0))
        for constant in self._constants.items():
            self._parameterBuffer.append('%s : %f' % constant)
        self._parameterBuffer.append('')
        self._parameterBuffer.append(formatReSTHeading('Sequence', 0))
        self._parameterBuffer.append(self._sequence.getTreeString(0))
        self._parameterBuffer.append('')
        self._parameterBuffer.append(formatReSTHeading('Parameters', 0))

        # Prepare all actions for execution (including ensuring that they
        # refer to this experiment).
        self._sequence.setExperiment(self)
        def applyActionCommands(action):
            """Set the pre- and post-loop actions for interruptable loops."""
            if isinstance(action, ActionLoopUntilInterrupt):
                action.setLoopCommands(self._loopEnterCommands,
                                       self._loopExitCommands)
        self._traverse(applyActionCommands)

        if self._statusMonitor is not None:
            self._sequence.setStatusMonitor(self._statusMonitor)
        self._sequence.prepareToExecute()

        # Prepare columns to store data (i.e. number them).
        self._prepareColumns()

        # Prepare and start the graph manager.
        try:
            if self._graphManagerClass is None:
                pass
            elif self._graphManager is None:
                self._graphManager = self._graphManagerClass(self._parentFrame)
            if self._graphManager is not None:
                enabledGraphs = [gph for gph in self._graphs if gph.isEnabled()]
                self._graphManager.setGraphs(enabledGraphs)
                self._graphManager.start()
                time.sleep(1)
        except (ValueError, NotImplementedError, TypeError) as err:
            log.error('Problem with graph manager...proceeding without ' +
                      'graphs.\n>>>>%s', err)

        log.info('Pre-sequence finished.')

    def _postSequence(self):
        """Free resources and clear stored data."""
        log.info('Starting post-sequence...')

        # Finalize all instruments
        for instrument in self._instruments:
            instrument.finalize()

        # Abort the graph manager and clear graph data
        try:
            self._graphManager.abort()
        except (AttributeError, TypeError, ValueError, NotImplementedError):
            log.error('Problem with graph manager...cannot abort.')
        time.sleep(1)
        for graph in self._graphs:
            graph.clear()

        # Close files (and save graphs, if applicable)
        self._closeFiles()
        
        # Execute postprocessorAction objects
        for action in self._postprocessorActions:
            action.executeReal()
        self._postprocessorActions = []
        self._allFiles = []

        # Delete the convenience attributes in the `Action` objects
        self._sequence.cleanupAfterExecution()

        # Empty the column and parameter information storage.
        for colname in self._columns:
            col = self._columns[colname]
            col['curr'] = ''
            col['colindex'] = None
        self._columnArray = []

        # Reset the running flag to False
        self._status[0] = False

        # Execute user-defined post-sequence actions
        if self._postSequenceActions is not None:
            try:
                for action in self._postSequenceActions:
                    action.execute()
            except TypeError as err:
                log.error('Invalid post-sequence action list.\n>>>>%s', err)

        # Clear the status monitor
        if self._statusMonitor is not None:
            self._statusMonitor.clear()

        log.info('Post-sequence finished.')


    #------------------------------------------------------------ Helper methods

    def _traverse(self, func):
        """Scan the action sequence, applying a function to each element."""
        def traverseAux(node, func):
            """Helper for traverse. Actually does the work."""
            if node.allowsChildren():
                children = node.getChildren()
                for child in children:
                    func(child)
                    traverseAux(child, func)
        func(self._sequence)
        traverseAux(self._sequence, func)


    #---------------------------------------------------------- Data persistence

    def __getstate__(self):
        """Return a dictionary of the defining properties of the experiment.

        Returns
        -------
        dict
            The full dictionary of the class except that those elements
            are incompatible with `pickle` have been removed.
        """
        odict = self.__dict__.copy()
        odict['_parentFrame'] = None
        odict['_graphManager'] = None
        odict['_graphManagerClass'] = None
        odict['_preSequenceActions'] = None
        odict['_postSequenceActions'] = None
        odict['_loopEnterCommands'] = None
        odict['_loopExitCommands'] = None
        odict['_status'] = [False, False, False]
        odict['_statusMonitor'] = None
        odict['_postprocessorActions'] = []
        return odict

    def __setstate__(self, dictionary):
        """Set the dictionary defining the properties of the experiment."""
        self.__dict__.update(dictionary)
        
    def getXML(self):
        """Build XML to serialize the experiment.
        
        Returns
        -------
        str
            The XML string indicating the components of the experiment.
        """
        root = ET.Element('experiment')
        
        constants = ET.SubElement(root, 'constants')
        for key, val in self._constants.items():
            constant = ET.SubElement(constants, 'constant')
            constant.set('name', key)
            constant.set('value', val)
            
        instruments = ET.SubElement(root, 'instruments')
        for inst in self._instruments:
            inst.getXML(instruments)
            
        sequence = ET.SubElement(root, 'sequence')
        self._sequence.getXML(sequence)
        
        graphs = ET.SubElement(root, 'graphs')
        for graph in self._graphs:
            graph.getXML(graphs)
            
        xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
        return xmlstr
          

    @classmethod
    def open(cls, filename):
        """Open an experiment from a file."""

        with open(filename, 'rb') as inputFile:
            expt = pickle.load(inputFile)
        return expt

    @classmethod
    def save(cls, experiment, filename):
        """Save an experiment to a file."""
        with open(filename, 'w') as outputFile:
            outputFile.write(experiment.getXML());



#--------------------------------------------------------------- ExecutionThread

class ExecutionThread(threading.Thread):
    """Helper class for executing the sequence without blocking the program."""

    def __init__(self, experiment):
        super(ExecutionThread, self).__init__()
        self.experiment = experiment
        self.name = 'Experiment Thread Starter'

    def run(self):
        """Begin executing the main sequence."""
        log.info('Main sequence started.')
        actionThread = ActionThread(self.experiment.getActionRoot(), True)
        actionThread.name = 'Main Experiment Thread'
        actionThread.start()
        actionThread.join()
        log.info('Main sequence finished.')
        self.experiment.abort()


#-------------------------------------------------------------- Helper functions

def _checkExpressionForErrors(expression, allProperties, definedProperties):
    """Return errors related to undefined data bins.
    
    Parameters
    ----------
    expression : str
        The expression to check for errors.
    allProperties : tuple of list of str
        A tuple of lists. The first list contains the names of all constants
        defined in the experiment. The second contains the names of all
        columns, and the third contains the names of all parameters.
    definedProperties : tuple of list of str
        A tuple of lists. The first list contains the names of the columns
        which have been defined by the time the expression is to be evaluated,
        and the second contains the names of parameters defined up to that
        same point.
    
    Returns
    -------
    list of tuple of str
        A list of tuples, where each tuple contains two elements. The first
        is either 'warning' or 'error', depending on the severity of the 
        problem, and the second is a message giving more detail about the
        problem.
    """
    answer = []
    constants, columns, parameters = allProperties
    definedColumns, definedParameters = definedProperties
    needConst, needCol, needParam = parsing.extractNames(expression)
    for item in needConst:
        if item not in constants:
            answer.append(('error', 'Undefined constant in ' +
                           'expression [%s]: [%s]' %
                           (expression, item)))
    for item in needCol:
        if item not in columns:
            answer.append(('error', 'Undefined column in ' +
                           'expression [%s]: [%s].' %
                           (expression, item)))
        elif item not in definedColumns:
            answer.append(('warning', 'Column referenced before ' +
                           'assignment in expression ' +
                           '[%s]: [%s]. Zero will be used.' %
                           (expression, item)))
    for item in needParam:
        if item not in parameters:
            answer.append(('error', 'Undefined parameter in ' +
                           'expression [%s]: [%s].' %
                           (expression, item)))
        elif item not in definedParameters:
            answer.append(('warning', 'Parameter referenced ' +
                           'before assignment in expression ' +
                           '[%s]: [%s]. Zero will be used.' %
                           (expression, item)))
    return answer

def _getCreatedBins(inputProperties, outputProperties):
    """Get the parameters and columns defined by an action.
    
    Parameters
    ----------
    inputProperties : list of dict
        A list of dictionaries of the form returned by the `Action` class's
        `getInputProperties()` method.
    outputProperties : list of dict
        A list of dictionaries of the form returned by the `Action` class's
        `getOutputProperties()` method.
        
    Returns
    -------
    tuple of list of str
        A tuple consisting of two lists, the first of which names all the 
        columns created by the relevant action, and the second names all the
        parameters.
    """
    definedColumns = []
    definedParameters = []
    for item in inputProperties:
        name = item['column']
        if name.startswith(MARK_PARAMETER):
            parameterName = name[len(MARK_PARAMETER):]
            if parameterName not in definedParameters:
                definedParameters.append(parameterName)
        elif len(name) > 0 and name not in definedColumns:
            definedColumns.append(name)
    for item in outputProperties:
        name = item['column']
        if name.startswith(MARK_PARAMETER):
            parameterName = name[len(MARK_PARAMETER):]
            if parameterName not in definedParameters:
                definedParameters.append(parameterName)
        elif len(name) > 0 and name not in definedColumns:
            definedColumns.append(name)
    return (definedColumns, definedParameters)
