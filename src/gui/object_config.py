"""Dialogs for setting up the main objects: actions, instruments, and graphs."""

from functools import partial
import os
import wx

from src.core import action as act
from src.core import experiment
from src.core.configuration import c
from src.core.errors import InvalidInputError
from src.core.graph import Graph
from src.gui import gui_helpers as gh

MARK_CONSTANT = experiment.MARK_CONSTANT
MARK_COLUMN = experiment.MARK_COLUMN
MARK_PARAM = experiment.MARK_PARAMETER

SUB_CONSTANT = experiment.SUB_CONSTANT
SUB_COLUMN = experiment.SUB_COLUMN
SUB_PARAMETER = experiment.SUB_PARAMETER

FILE_DIRECTIONS = ('Choose a folder to store data files using the "Browse for '
                   'Folder" button, and enter a filename for the current data '
                   'file, without any extensions.')

CALCULATE_DIRECTIONS = (('Enter an expression. Expressions may include the '
        'standard mathematical functions and any constants, parameters, or '
        'columns you have defined. Names of constants should be specified in '
        'the form %s(constant name), parameters in the form %s(parameter name) '
        'and columns in the form %s(column name).') %
        (MARK_CONSTANT, MARK_PARAM, MARK_COLUMN))

CONDITIONAL_DIRECTIONS = (('Enter a boolean expression (an expression that '
        'evaluates to true or false). The expression may include any constants '
        'columns, or parameters you have defined, the basic operations (+, -, '
        '*, /, **), the standard mathematical functions, and the standard '
        'comparison operators (==, >, >=, <, <=, !=). Names of constants '
        'should be specified in the form %s(constant name), parameters in the '
        'form %s(parameter name) and columns in the form %s(column name).') %
        (MARK_CONSTANT, MARK_PARAM, MARK_COLUMN))


# Dialog Dispatcher ------------------------------------------------------------

def getDialog(action):
    """Return the appropriate dialog for the supplied action.

    Parameters
    ----------
    action : Action
        An `Action` object which the user wants to edit.

    Returns
    -------
    class
        The appropriate dialog class (uninstantiated) for modifying `action`.
    """
    result = None
    if isinstance(action, act.ActionScan):
        result = ScanDialog
    elif (isinstance(action, act.ActionLoopTimed) or
                    isinstance(action, act.ActionLoopIterations)):
        result = LoopTimesDialog
    elif isinstance(action, act.ActionLoopWhile):
        result = LoopWhileDialog
    elif (isinstance(action, act.ActionLoopUntilInterrupt) or
                    isinstance(action, act.ActionSimultaneous) or
                    isinstance(action, act.ActionContainer)):
        result = BlankDialog
    elif isinstance(action, act.Action):
        instname = action.getInstrumentName()
        actdesc = action.getDescription()
        if instname == 'System':
            if actdesc == 'Set data file':
                result = FileDialog
            elif actdesc == 'Calculate':
                result = CalculateDialog
            else:
                result = ActionDialog
        elif instname == 'Postprocessor':
            result = BlankDialog        
        else:
            result = ActionDialog

    if result is not None:
        return result

    className = action.__class__.__name__
    myself = os.path.abspath( __file__ )
    raise NotImplementedError(('%s: No dialog has been associated ' +
                               'with this class of actions. Please edit ' +
                               'the dispatcher at %s') % (className, myself))


# Action Configuration Dialogs -------------------------------------------------

class ActionDialog(gh.BaseDialog):
    """A dialog to configure standard actions.

    This dialog presents a way to configure normal `Action` objects. It
    presents a two-region panel. On the left are options for inputs, and on
    the right are options for outputs. Inputs may have both their values
    and their column names set here, and outputs may have their column
    names set.

    Parameters
    ----------
    parent : wxWindow
        The panel or frame which owns this dialog.
    experiment : Experiment
        The experiment which owns the action being configured by this dialog.
    actionIn : Action
        The action whose parameters will be set by this dialog.
    """
    def __init__(self, parent, expt, actionIn):
        self.experiment = expt
        self.action = actionIn
        self.inputs = self.action.getInputProperties()
        self.outputs = self.action.getOutputProperties()

        super(ActionDialog, self).__init__(parent, wx.ID_ANY,
                                           self.action.getDescription(),
                                           minWidth=650)

        mainpanel = gh.Panel(self, 'horizontal')

        columnFlag = wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL
        self.controls = []
        self.inputcols = []
        self.inputvals = []
        self.outputcols = []

        inputpanel = gh.Panel(mainpanel, 'flex_grid', 'Inputs',
                                   len(self.inputs)+1, 3, 5, 5,
                                   scrolling=True)
        inputpanel.addLabel('Parameter', 0, columnFlag)
        inputpanel.addLabel('Column Name', 0, columnFlag)
        inputpanel.addLabel('Value', 0, columnFlag)
        inputpanel.addGrowableColumn(1, 1)
        inputpanel.addGrowableColumn(2, 1)

        for dat in self.inputs:
            currentLabel = dat['description']
            choices = [None, dat['allowed']]
            initialValues = [dat['column'], dat['value']]
            currentControls = inputpanel.addLabeledMultiCtrl(currentLabel,
                                                             initialValues,
                                                             choices, 0)
            self.inputcols.append(currentControls[0])
            self.inputvals.append(currentControls[1])

        outputpanel = gh.Panel(mainpanel, 'flex_grid', 'Outputs',
                                    len(self.outputs)+1, 2, 5, 5,
                                    scrolling=True)
        outputpanel.addLabel('Parameter', 0, columnFlag)
        outputpanel.addLabel('Column Name', 0, columnFlag)
        outputpanel.addGrowableColumn(1, 1)

        for dat in self.outputs:
            currCol = outputpanel.addLabeledText(dat['description'],
                                                 dat['column'])
            self.outputcols.append(currCol)

        mainpanel.add(inputpanel, 3, wx.EXPAND|wx.ALL, 2)
        mainpanel.add(outputpanel, 2, wx.EXPAND|wx.ALL, 2)

        mainpanel.SetMinSize((600, 200))
        self.setPanel(mainpanel)

    def update(self):
        """Try to update the action to reflect changes made by this dialog."""
        newincols = []
        newinvals = []
        for col, val in zip(self.inputcols, self.inputvals):
            newincols.append(col.GetValue())
            newinvals.append(val.GetValue())
        try:
            self.action.setInputValues(newinvals)
            self.action.setInputColumns(newincols)
        except InvalidInputError as err:
            dialog = wx.MessageDialog(self, str(err), 'Invalid Input',
                                      wx.OK|wx.ICON_ERROR)
            dialog.ShowModal()
            return False

        newoutcols = []
        for col in self.outputcols:
            newoutcols.append(col.GetValue())
        return True


class ScanDialog(gh.BaseDialog):
    """A dialog for configuring scan actions.

    Parameters
    ----------
    parent : wxWindow
        The panel or frame which owns this dialog.
    expt : Experiment
        The experiment which owns the action being configured by this dialog.
    actionIn : Action
        The action whose parameters will be set by this dialog.
    """
    def __init__(self, parent, expt, actionIn):

        self.experiment = expt
        self.action = actionIn
        self.inprop = self.action.getInputProperties()[0]
        super(ScanDialog, self).__init__(parent, wx.ID_ANY,
                                         title=self.action.getDescription(),
                                         minWidth=250)

        mainpanel = gh.Panel(self)

        inpanel = wx.Panel(mainpanel, wx.ID_ANY)
        insizer = wx.BoxSizer(wx.HORIZONTAL)
        inpanel.SetSizer(insizer)

        labelText = 'Column name for [%s]:' % self.inprop['description']
        self.incol = gh.createLabeledTextControl(inpanel, insizer,
                         label=labelText, initialValue=self.inprop['column'])

        self.scanPanel = gh.ScanPanel(mainpanel,
                                      initialData=self.inprop['value'],
                                      formatString=self.inprop['format_string'])
        self.scanPanel.SetMinSize((400, -1))
        mainpanel.add(inpanel, 0, wx.EXPAND|wx.ALL, 5)
        mainpanel.add(self.scanPanel, 1, wx.EXPAND)
        self.setPanel(mainpanel)

    def getData(self):
        """Return the data contained in the scan panel.

        Returns
        -------
        list of tuple of str
            The scan panel data.
        """
        return self.scanPanel.getData()

    def update(self):
        """Try to update the action to reflect changes made by this dialog."""
        try:
            self.action.setInputValues([self.getData()])
            self.action.setInputColumns([self.incol.GetValue()])
        except InvalidInputError as err:
            dialog = wx.MessageDialog(self, str(err), 'Invalid Input',
                                      wx.OK|wx.ICON_ERROR)
            dialog.ShowModal()
            return False
        return True


class LoopTimesDialog(gh.BaseDialog):
    """A dialog for configuring the most simple looping actions.

    This dialog allows configuration both of actions which loop for a specified
    amount of time (in seconds) and of actions which loop for a specified
    number of iterations.

    Parameters
    ----------
    parent : wxWindow
        The panel or frame which owns this dialog.
    expt : Experiment
        The experiment which owns the action being configured by this dialog.
    actionIn : Action
        The action whose parameters will be set by this dialog.
    """
    def __init__(self, parent, expt, actionIn):

        self.experiment = expt
        self.action = actionIn

        super(LoopTimesDialog, self).__init__(parent, wx.ID_ANY,
                                              self.action.getDescription(),
                                              minWidth=150)

        mainpanel = gh.Panel(self, 'horizontal')

        if isinstance(self.action, act.ActionLoopTimed):
            self.label = 'Loop time (s): '
            self.value = self.action.getDuration()
        else:
            self.label = 'Number of iterations: '
            self.value = self.action.getIterations()

        self.valueBox = mainpanel.addLabeledText(self.label, str(self.value), 3)

        self.setPanel(mainpanel, 0, wx.EXPAND|wx.ALL, 20)


    def update(self):
        """Try to update the action to reflect changes made by this dialog."""
        val = self.valueBox.GetValue()

        if isinstance(self.action, act.ActionLoopTimed):
            self.action.setDuration(float(val))
        else:
            self.action.setIterations(int(val))
        return True


class BlankDialog(gh.BaseDialog):
    """An empty dialog which closes immediately.

    Parameters
    ----------
    parent : wxWindow
        The panel or frame which owns this dialog.
    expt : Experiment
        The experiment which owns the action being configured by this dialog.
    actionIn : Action
        The action whose parameters will be set by this dialog.
    """
    def __init__(self, parent, expt, actionIn):
        super(BlankDialog, self).__init__(parent, -1)

        self.experiment = expt
        self.action = actionIn

    def close(self):
        """Close the dialog."""
        self.EndModal(wx.ID_OK)
        self.Destroy()

    # pylint: disable=W0221
    def ShowModal(self, event=None):
        """Return immediately, so that the dialog closes."""
        return wx.ID_OK
    # pylint: enable=W0221

    def update(self):
        """Try to update the action to reflect changes made by this dialog."""
        return True


class LoopWhileDialog(gh.BaseDialog):
    """A dialog for configuring a while loop action.

    Parameters
    ----------
    parent : wxWindow
        The panel or frame which owns this dialog.
    expt : Experiment
        The experiment which will execute the action configured by this
        dialog.
    actionIn : Action
        The looping action whose parameters will be set by this dialog.
    """

    def __init__(self, parent, expt, actionIn):
        info = ('Loop while condition holds', CONDITIONAL_DIRECTIONS)

        super(LoopWhileDialog, self).__init__(parent, wx.ID_ANY,
                                              'Loop: conditional', info=info)

        self.experiment = expt
        self.action = actionIn

        data = self.experiment.getStorageBinNames()

        mainpanel = gh.Panel(self)

        timeoutpanel = wx.Panel(mainpanel)
        timeoutsizer = wx.StaticBoxSizer(wx.StaticBox(timeoutpanel,
                                                      wx.ID_ANY,
                                                      'Timeout'),
                                         wx.VERTICAL)
        timeoutpanel.SetSizer(timeoutsizer)

        timeoutsubpanel = wx.Panel(timeoutpanel)
        timeoutsubsizer = wx.FlexGridSizer(2, 2, 5, 5)
        timeoutsubpanel.SetSizer(timeoutsubsizer)

        timeoutlabel = wx.StaticText(timeoutsubpanel, label='Timeout (s): ')
        timeoutenablelabel = wx.StaticText(timeoutsubpanel,
                                           label='Timeout enabled: ')
        self.timeoutvalue = wx.TextCtrl(timeoutsubpanel, wx.ID_ANY)
        self.timeoutenabled = wx.CheckBox(timeoutsubpanel, wx.ID_ANY)

        timeoutsubsizer.Add(timeoutlabel, 0,
                            wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        timeoutsubsizer.Add(self.timeoutvalue, 0,
                            wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        timeoutsubsizer.Add(timeoutenablelabel, 0,
                            wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        timeoutsubsizer.Add(self.timeoutenabled, 0,
                            wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        timeoutsubsizer.AddGrowableCol(1, 1)

        timeoutsizer.Add(timeoutsubpanel, 0,
                         wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)

        timeoutValue = self.action.getTimeout()
        if timeoutValue is None:
            self.timeoutvalue.SetValue('')
            self.timeoutenabled.SetValue(False)
        else:
            self.timeoutvalue.SetValue(str(timeoutValue))
            self.timeoutenabled.SetValue(True)


        self.exprpanel = ExpressionPanel(mainpanel, data)
        self.exprpanel.setExpression(self.action.getExpression())

        mainpanel.add(timeoutpanel, 0, wx.EXPAND|wx.ALL, 5)
        mainpanel.add(self.exprpanel, 1, wx.EXPAND|wx.ALL, 5)
        mainpanel.SetSizeHints(-1, 300)

        self.setPanel(mainpanel, 1, wx.EXPAND|wx.ALL)


    def update(self):
        """Try to update the action to reflect changes made by this dialog."""
        newexpr = self.exprpanel.getExpression()
        if self.timeoutenabled.GetValue():
            try:
                newto = float(self.timeoutvalue.GetValue())
            except ValueError:
                newto = None
        else:
            newto = None
        self.action.setExpression(newexpr)
        self.action.setTimeout(newto)
        return True


# System Instrument Dialogs and Panels -----------------------------------------

class FileDialog(gh.BaseDialog):
    """A dialog for setting the data filename.

    Parameters
    ----------
    parent : wxWindow
        The panel or frame which owns this dialog.
    expt : Experiment
        The experiment which will be writing to the files.
    actionIn : Action
        The file-saving action whose parameters will be set by this dialog.
    """
    def __init__(self, parent, expt, actionIn):
        super(FileDialog, self).__init__(parent, wx.ID_ANY, 'Set filename',
                                         info=('Data Files', FILE_DIRECTIONS))

        self.experiment = expt
        self.action = actionIn

        mainpanel = wx.Panel(self)
        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainpanel.SetSizer(mainsizer)

        datpanel = gh.Panel(mainpanel, 'flex_grid', None, 2, 2, 5, 5)

        folderpanel = gh.Panel(datpanel, 'horizontal')

        self.folder = wx.TextCtrl(folderpanel)
        self.folder.SetEditable(False)
        self.folder.Disable()
        self.btnBrowse = wx.Button(folderpanel, wx.ID_OPEN, label='...',
                                   style=wx.BU_EXACTFIT)
#         self.btnBrowse.SetMinSize((20, 20))
        self.btnBrowse.Bind(wx.EVT_BUTTON, self.onBrowse)
        folderpanel.add(self.folder, proportion=1, flag=wx.EXPAND)
        folderpanel.add(self.btnBrowse, proportion=0)

        inprops = self.action.getInputProperties()
        self.folder.SetValue(inprops[0]['value'])
        datpanel.addLabel('Data folder:', 0)
        datpanel.add(folderpanel, 1, wx.EXPAND)
        self.file = datpanel.addLabeledText('Base filename:',
                                            inprops[1]['value'])

        datpanel.addGrowableColumn(1, 1)
#         datpanel.addGrowableColumn(2, 1)

        scanpanel = gh.Panel(mainpanel, 'horizontal')
        self.scanbox = scanpanel.addLabeledText('Scan number:',
                                                inprops[2]['value'], 2)


        mainsizer.Add(datpanel, proportion=1, flag=wx.ALL|wx.EXPAND, border=5)
        mainsizer.Add(scanpanel, 0, wx.ALIGN_CENTER|wx.ALL, 5)

        self.setPanel(mainpanel, 1, wx.EXPAND|wx.ALL, 5)


    def onBrowse(self, event):
        """Show a dialog to browse for a folder."""
        defFolder = c.getDataFolder()
        dialog = wx.DirDialog(None, "Choose a directory:", defFolder,
                              style=wx.DD_DEFAULT_STYLE | wx.DD_NEW_DIR_BUTTON)
        if dialog.ShowModal() == wx.ID_OK:
            self.folder.SetValue(dialog.GetPath())
        dialog.Destroy()

    def update(self):
        """Try to update the action to reflect changes made by this dialog."""
        self.action.setInputValues([self.folder.GetValue(),
                                self.file.GetValue(),
                                self.scanbox.GetValue()])
        return True


class CalculateDialog(gh.BaseDialog):
    """A dialog for configuring calculation actions.

    Parameters
    ----------
    parent : wxWindow
        The panel or frame which owns this dialog.
    expt : Experiment
        The experiment which owns the action being configured by this dialog.
    actionIn : Action
        The action whose parameters will be set by this dialog.
    """
    def __init__(self, parent, expt, actionIn):
        information = ('Evaluate expression', CALCULATE_DIRECTIONS)
        super(CalculateDialog, self).__init__(parent, title='Calculation',
                                              info=information)

        self.experiment = expt
        self.action = actionIn

        data = self.experiment.getStorageBinNames()

        mainpanel = gh.Panel(self)

        colnamepanel = gh.Panel(mainpanel, 'flex_grid', 'Column names',
                               2, 2, 5, 5)

        indat = self.action.getInputProperties()[0]
        outdat = self.action.getOutputProperties()[0]
        indesc = indat['description']
        incol = indat['column']
        inval = indat['value']
        outdesc = outdat['description']
        outcol = outdat['column']
        self.incol = colnamepanel.addLabeledText(indesc, incol)
        self.outcol = colnamepanel.addLabeledText(outdesc, outcol)
        colnamepanel.addGrowableColumn(1, 1)

        self.exprpanel = ExpressionPanel(mainpanel, data)
        self.exprpanel.setExpression(inval)

        mainpanel.add(colnamepanel, 0, wx.EXPAND|wx.ALL, 4)
        mainpanel.add(self.exprpanel, proportion=1, flag=wx.EXPAND|wx.ALL)
        mainpanel.SetSizeHints(-1, 300)

        self.setPanel(mainpanel, 1, wx.EXPAND|wx.ALL)

    def update(self):
        """Try to update the action to reflect changes made by this dialog."""
        newincol = self.incol.GetValue()
        newoutcol = self.outcol.GetValue()
        newexpr = self.exprpanel.getExpression()
        self.action.setInputValues([newexpr])
        self.action.setInputColumns([newincol])
        self.action.setOutputColumns([newoutcol])
        return True


class ExpressionPanel(wx.Panel):
    """A panel for creating and editing expressions for later evaluation.

    Parameters
    ----------
    parent : wxWindow
        The panel or frame which contains this panel.
    data : tuple of list of str
        A three-element tuple of lists of strings. The first element of the
        tuple contains a list of the names of constants, the second
        contains a list of columns, and the last contains a list of
        parameters.
    """

    def __init__(self, parent, data):
        super(ExpressionPanel, self).__init__(parent, size=(450, 500))


        exprpanel = wx.Panel(self)
        exprbox = wx.StaticBox(exprpanel, wx.ID_ANY, 'Expression')
        exprsizer = wx.StaticBoxSizer(exprbox, wx.VERTICAL)
        exprpanel.SetSizer(exprsizer)

        self.exprbox = wx.TextCtrl(exprpanel, wx.ID_ANY, style=wx.TE_MULTILINE)
        exprsizer.Add(self.exprbox, 1, wx.EXPAND|wx.ALL, 1)

        bottompanel = wx.Panel(self)
        bottomsizer = wx.BoxSizer(wx.HORIZONTAL)
        bottompanel.SetSizer(bottomsizer)

        constpanel = gh.Panel(bottompanel, 'vertical', 'Constants')

        self.constbox = wx.ListBox(constpanel)
        self.constbox.SetItems(data[0])
        self.constbox.Bind(wx.EVT_LISTBOX_DCLICK, self.__insertConstant)
        constpanel.add(self.constbox, proportion=1, flag=wx.EXPAND)

        colpanel = gh.Panel(bottompanel, 'vertical', 'Columns')

        self.colbox = wx.ListBox(colpanel)
        self.colbox.SetItems(data[1])
        self.colbox.Bind(wx.EVT_LISTBOX_DCLICK, self.__insertColumn)
        colpanel.add(self.colbox, proportion=1, flag=wx.EXPAND)

        parampanel = gh.Panel(bottompanel, 'vertical', 'Parameters')

        self.parambox = wx.ListBox(parampanel)
        self.parambox.SetItems(data[2])
        self.parambox.Bind(wx.EVT_LISTBOX_DCLICK, self.__insertParameter)
        parampanel.add(self.parambox, proportion=1, flag=wx.EXPAND)

        bottomsizer.Add(constpanel, proportion=1, flag=wx.EXPAND)
        bottomsizer.Add(colpanel, proportion=1, flag=wx.EXPAND)
        bottomsizer.Add(parampanel, proportion=1, flag=wx.EXPAND)

        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(exprpanel, 1, wx.EXPAND|wx.ALL, 2)
        mainsizer.Add(bottompanel, 1, wx.EXPAND|wx.ALL, 2)

        self.SetAutoLayout(True)
        self.SetSizer(mainsizer)
        self.Layout()

    def getExpression(self):
        """Get the value of the expression box.

        Returns
        -------
        str
            The string expression set by the user.
        """
        return self.exprbox.GetValue()

    def setExpression(self, expression):
        """Set the value of the expression box.

        Parameters
        ----------
        expression : str
            The value which should go in the expression box. The expression
            may, on use of `eval`, return an `int`, a `float`, or a `bool`.
        """
        self.exprbox.SetValue(expression)

    def __insertConstant(self, event):
        """Insert the name of the selected constant at the cursor position."""
        val = self.exprbox.GetValue()
        insertionPoint = self.exprbox.GetInsertionPoint()
        pre = val[:insertionPoint]
        post = val[insertionPoint:]
        newString = SUB_CONSTANT % event.GetString()
        self.exprbox.SetValue(''.join([pre, newString, post]))

    def __insertColumn(self, event):
        """Insert the name of the selected column at the cursor position."""
        val = self.exprbox.GetValue()
        insertionPoint = self.exprbox.GetInsertionPoint()
        pre = val[:insertionPoint]
        post = val[insertionPoint:]
        newString = SUB_COLUMN % event.GetString()
        self.exprbox.SetValue(''.join([pre, newString, post]))

    def __insertParameter(self, event):
        """Insert the name of the selected parameter at the cursor position."""
        val = self.exprbox.GetValue()
        insertionPoint = self.exprbox.GetInsertionPoint()
        pre = val[:insertionPoint]
        post = val[insertionPoint:]
        newString = SUB_PARAMETER % event.GetString()
        self.exprbox.SetValue(''.join([pre, newString, post]))


# Instruments ------------------------------------------------------------------

class InstrumentDialog(gh.BaseDialog):
    """A simple dialog for creating new instruments.
    """

    def __init__(self, parent, inst):
        """Create a new instrument dialog."""
        super(InstrumentDialog, self).__init__(parent, wx.ID_ANY,
                                               title='Edit instrument',
                                               minWidth=300)

        self.inst = inst
        self.spec = inst.getSpecification()

        setpanel = wx.Panel(self)
        setsizer = wx.FlexGridSizer(len(self.spec) + 1, 2, 3, 3)
        setpanel.SetSizer(setsizer)

        name = self.inst.getName()

        self.tbs = []
        setsizer.Add(wx.StaticText(setpanel, label='Name:'), 0,
                     wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        self.namefield = wx.TextCtrl(setpanel)
        self.namefield.SetValue(name)
        setsizer.Add(self.namefield, proportion=1, flag=wx.EXPAND)
        self.controls = []
        for item in self.spec:
            itemLabel = wx.StaticText(setpanel, label=item.description + ':')
            setsizer.Add(itemLabel, 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
            if item.allowed is None:
                control = wx.TextCtrl(setpanel)
            else:
                control = wx.ComboBox(setpanel, style=wx.CB_DROPDOWN,
                                      choices=item.allowed)

            control.SetValue(str(item))
            control.SetMinSize((200, -1))
            self.controls.append(control)
            setsizer.Add(control, 1, wx.EXPAND)

        setsizer.AddGrowableCol(1, 1)

        self.setPanel(setpanel)

    def update(self):
        """Update the instrument to reflect changes."""
        for item, control in zip(self.spec, self.controls):
            item.value = control.GetValue()
        self.inst.setName(self.namefield.GetValue())
        self.inst.setSpecification(self.spec)
        return True


class RebindInstrumentDialog(gh.BaseDialog):
    """A dialog to change the instrument to which an action is bound.
    """

    def __init__(self, parent, expt, action):
        super(RebindInstrumentDialog, self).__init__(parent, wx.ID_ANY,
                                                     title='Change instrument')

        self.experiment = expt
        self.action = action
        self.inst = self.action.getInstrument()
        self.options = self.experiment.getEqualEnoughInstruments(action)

        self.names = []
        self.initindex = None
        for index, option in enumerate(self.options):
            self.names.append(option['instrument_name'])
            if option['instrument'] is self.inst:
                self.initindex = index

        instpanel = wx.Panel(self)
        instbox = wx.StaticBox(instpanel, wx.ID_ANY, "Instrument")
        instsizer = wx.StaticBoxSizer(instbox, wx.HORIZONTAL)
        instpanel.SetSizer(instsizer)

        self.instbox = wx.ComboBox(instpanel, style=wx.CB_READONLY)
        self.instbox.SetMinSize((200, -1))
        self.instbox.SetItems(self.names)
        self.instbox.Select(self.initindex)

        instsizer.AddStretchSpacer(1)
        instsizer.Add(self.instbox, 5, wx.EXPAND|wx.TOP|wx.BOTTOM, 5)
        instsizer.AddStretchSpacer(1)

        self.setPanel(instpanel)

    def update(self):
        """Update the action to use the new instrument."""
        sel = self.instbox.GetSelection()
        if sel != self.initindex:
            self.action.setInstrument(self.options[sel]['instrument'])
        return True


# Graphs -----------------------------------------------------------------------

class GraphDialog(gh.BaseDialog):
    """A dialog for editing graphs.

    Parameters
    ----------
    parent : wxWindow
        The frame or panel which owns this dialog.
    experiment : Experiment
        The experiment which contains the graphs edited by this dialog.
    graphIn : Graph
        The graph to edit.
    """

    def __init__(self, parent, expt, graphIn=None):
        super(GraphDialog, self).__init__(parent, -1, title='Edit graph',
                                          minWidth=300)

        self.experiment = expt
        self.graphIn = graphIn


        self.columnNames = self.experiment.getStorageBinNames()[1]
        self.trigNames = ['None'] + self.columnNames

        datapanel = gh.Panel(self, 'flex_grid', None, 3, 2, 2, 2)
        myCombo = partial(datapanel.addLabeledComboBox, style=wx.CB_READONLY,
                          border=2)

        if self.graphIn is not None:
            selectedColumns = self.graphIn.getColumns()
            initialX = selectedColumns[0]
            initialY = selectedColumns[1]
            initialTrig = selectedColumns[2]
        else:
            initialX = self.columnNames[1]
            initialY = self.columnNames[0]
            initialTrig = None
        if initialTrig is None:
            initialTrig = 'None'

        self.xbox = myCombo(choices=self.columnNames, initialValue=initialX,
                            label='X column:')
        self.ybox = myCombo(choices=self.columnNames, initialValue=initialY,
                            label='Y column:')
        self.trigbox = myCombo(choices=self.trigNames, initialValue=initialTrig,
                               label='Plot trigger:')

        datapanel.addGrowableColumn(1, 1)

        self.setPanel(datapanel)

    def update(self):
        """Update the input graph or create a new graph."""
        newcols = [self.xbox.GetValue(), self.ybox.GetValue(),
                   self.trigbox.GetValue()]
        if self.trigbox.GetValue() == 'None':
            newcols[2] = None
        if self.graphIn is not None:
            self.graphIn.setColumns(newcols)
            self.experiment.updateGraphColumns(self.graphIn)
        else:
            self.graphIn = Graph(self.experiment, *newcols)
            self.experiment.addGraph(self.graphIn)

        cols = self.experiment.getStorageBinNames()[1]
        if newcols[0] in cols and newcols[1] in cols:
            self.graphIn.setEnabled(True)
        else:
            self.graphIn.setEnabled(False)
        return True
