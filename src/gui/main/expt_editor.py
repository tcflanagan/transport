"""A general frame for creating and editing experiments."""

import pickle
from collections import namedtuple
from functools import partial
import logging
import re
import textwrap
import wx

from src.core import progress
from src.core.action import constructAction
from src.core.errors import InstrumentInUseError
from src.core.graph import Graph
from src.core.inst_manager import INSTRUMENT_MANAGER
from src.gui import gui_helpers as gh
from src.gui import images as img
from src.gui import object_config as oc
from src.gui.main.base_experiment import (ExperimentFrame,
                                          ID_INSTRUMENTS, ID_CONSTANTS,
                                          ID_GRAPHS)

from src.gui.main.status_frame import StatusMonitorFrame
from src.gui.object_config import GraphDialog
from src.gui.object_config import InstrumentDialog
from src.tools import path_tools as pt
from src.tools.general import Command

log = logging.getLogger('transport')

_DEFAULT_OPTIONS = (wx.TR_NO_BUTTONS | wx.TR_HIDE_ROOT |
                    wx.TR_FULL_ROW_HIGHLIGHT | wx.TR_SINGLE | wx.TR_NO_LINES)
_INDENT = 30
_MIN_SIDE_WIDTH = 180

_ID_REBIND = wx.NewId()
_ID_ENABLE = wx.NewId()
_ID_INTERRUPT = wx.NewId()

_PRINT_SEQUENCE = False

SetupFrames = namedtuple('SetupFrames', ['instruments', 'constants', 'graphs'])

class SequenceFrame(ExperimentFrame):
    """A frame for creating general experiments.
    
    Parameters
    ----------
    parent : Transport
        The main Transport program frame (or anything which implements the
        same interface).
    experiment : Experiment
        The `Experiment` object which this frame edits.
    sourceDefault : bool
        Whether the sequence should be populated with the default items.
    title : str
        The title of the experiment.
    experimentPath : str
        The path to the experiment, if it was opened from a file. The default
        is `None`.
    """
    def __init__(self, parent, experiment, sourceDefault=True,
                 title='Experiment Editor', experimentPath=None):
        super(SequenceFrame, self).__init__(parent,
                                            experiment=experiment,
                                            title=title,
                                            premade=False,
                                            experimentPath=experimentPath,
                                            size=(800, 600))

        sizer = wx.BoxSizer(wx.VERTICAL)

        mainpanel = gh.Panel(self, 'horizontal')
        sizer.Add(mainpanel, 1, wx.EXPAND, 0)

        treepanel = gh.Panel(mainpanel, 'vertical', 'Sequence', extraBorder=0)
        self.tree = ActionTree(treepanel, self.experiment, parentFrame=self)
        self.appendControl(self.tree)
        treepanel.add(self.tree, 1, wx.EXPAND, 5)

        sidepanel = gh.Panel(mainpanel, 'vertical')
        instpanel = gh.Panel(sidepanel, 'vertical', 'Instruments',
                             extraBorder=0)
        actionspanel = gh.Panel(sidepanel, 'vertical', 'Actions', extraBorder=0)
        sidepanel.add(instpanel, 1, wx.ALL | wx.EXPAND, 0)
        sidepanel.add(actionspanel, 2, wx.ALL | wx.EXPAND, 0)

        self.insts = gh.ListBox(instpanel)
        self.appendControl(self.insts)
        self.insts.SetMinSize((_MIN_SIDE_WIDTH, -1))
        instpanel.add(self.insts, 1, wx.EXPAND | wx.ALL, 0)

        self.acts = gh.ListBox(actionspanel)
        self.appendControl(self.acts)
        self.acts.SetMinSize((_MIN_SIDE_WIDTH, -1))
        actionspanel.add(self.acts, 1, wx.EXPAND | wx.ALL, 0)

        mainpanel.add(treepanel, 1, wx.EXPAND | wx.ALL, 2)
        mainpanel.add(sidepanel, 0, wx.EXPAND | wx.ALL, 2)

        self.sourceDefault = sourceDefault
        if self.sourceDefault:
            self.tree.buildDefaultTree()
            graph = Graph(self.experiment, 'Item 0', 'Result', None)
            self.experiment.addGraph(graph)
        else:
            self.tree.refresh()

        self.Bind(wx.EVT_CLOSE, self.onClose)
        self.insts.Bind(wx.EVT_LIST_ITEM_FOCUSED, self.updateActionDisplay)
        self.acts.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._createAction)
        self.acts.Bind(wx.EVT_LIST_BEGIN_DRAG, self._beginDrag)

        self.dropTarget = MyDropTarget(self.tree, self.acts)
        self.tree.SetDropTarget(self.dropTarget)

        self._interrupt = False

        self.__edited = False
        self.editMenu = None
        self.pasteButton = None
        self.copyButton = None
        self.cutButton = None
        self.extendMenus()
        self.extendToolbar()

        self.SetSizerAndFit(sizer)
        self.SetSize((800, 600))
        self.updateInstrumentDisplay()
        self.setupFrames = self.createSetupFrames()
        self.updateName()
        
    def onClose(self, event):
        self.insts.Unbind(wx.EVT_LIST_ITEM_FOCUSED)
        super().onClose(event)

    def extendMenus(self):
        """Extend the menu bar with experiment editor-specific items."""

        # -- File Menu
        fileAdder = partial(gh.createMenuItem, self, self.fileMenu)
        fileAdder(wx.ID_SAVE, 'Save', handler=self.onSave, pos=4)
        fileAdder(wx.ID_SAVEAS, 'Save As', handler=self.onSaveAs, pos=5)

        self.editMenu = wx.Menu()
        editAdder = partial(gh.createMenuItem, self, self.editMenu)
        self.cutButton = editAdder(wx.ID_CUT, 'Cut', handler=self.tree.onCut)
        self.copyButton = editAdder(wx.ID_COPY, 'Copy',
                                    handler=self.tree.onCopy)
        self.pasteButton = editAdder(wx.ID_PASTE, 'Paste',
                                     handler=self.tree.onPaste)
        self.editMenu.AppendSeparator()
        editAdder(ID_INSTRUMENTS, 'Setup Instruments',
                  handler=self.onSetupInstruments)
        editAdder(ID_CONSTANTS, 'Setup Constants',
                  handler=self.onSetupConstants)
        editAdder(ID_GRAPHS, 'Setup Graphs',
                  handler=self.onSetupGraphs)
        self.cutButton.Enable(False)
        self.copyButton.Enable(False)
        self.pasteButton.Enable(False)
        self.menuBar.Insert(1, self.editMenu, 'Edit')

    def extendToolbar(self):
        """Extend the toolbar with experiment editor-specific items."""
        self.toolbar.AddSeparator()
#         self.toolbar.AddSimpleTool(ID_INSTRUMENTS, 
#                               img.getInstrumentsButtonBitmap(),
#                               'Instruments', 'Configure the instruments.')
#         self.toolbar.AddSimpleTool(ID_CONSTANTS, img.getConstantsButtonBitmap(),
#                               'Constants', 'Edit constants.')
#         self.toolbar.AddSimpleTool(ID_GRAPHS, img.getGraphsButtonBitmap(),
#                               'Graphs', 'Edit graphs.')
        self.toolbar.AddTool(ID_INSTRUMENTS, 'Instruments',
                             img.getInstrumentsButtonBitmap())
        self.toolbar.AddTool(ID_CONSTANTS, 'Constants', 
                             img.getConstantsButtonBitmap())
        self.toolbar.AddTool(ID_GRAPHS, 'Graphs',
                             img.getGraphsButtonBitmap())
        self.toolbar.AddCheckTool(_ID_INTERRUPT, 'Interrupt', img.getInterruptBitmap(),
                                   shortHelp='Interrupt')
        self._enableInterrupt(False)

        self.Bind(wx.EVT_TOOL, self.onSetupInstruments, id=ID_INSTRUMENTS)
        self.Bind(wx.EVT_TOOL, self.onSetupConstants, id=ID_CONSTANTS)
        self.Bind(wx.EVT_TOOL, self.onSetupGraphs, id=ID_GRAPHS)
        self.Bind(wx.EVT_TOOL, self._onInterrupt, id=_ID_INTERRUPT)

        self.toolbar.Realize()

    #===========================================================================
    # Edit flags
    #===========================================================================

    def getEdited(self):
        """Return whether the experiment has been edited.
        
        Returns
        -------
        bool
            Whether the experiment has been edited.
        """
        return self.__edited
    def setEdited(self, newValue):
        """Set whether the experiment has been edited.
        
        Parameters
        ----------
        newValue : bool
            Whether the experiment has been edited.
        """
        self.__edited = newValue
        self.updateName()
    edited = property(getEdited, setEdited)
    def flagEdit(self):
        """Indicate that the experiment has been edited.
        
        This is a simple shorthand for `self.edited = True`.
        """
        self.edited = True

    def onRun(self, event=None):
        """Run the experiment."""
        smon = progress.getStatusMonitor('main')
        loopEnter = Command(self._enableInterrupt, True)
        loopExit = Command(self._enableInterrupt, False)
        self.experiment.setInteractionParameters(statusMonitor=smon,
                                                 loopEnterCommands=[loopEnter],
                                                 loopExitCommands=[loopExit])
        statmon = StatusMonitorFrame(self, smon)
        statmon.Show()
        statmon.SetTitle(self.experimentName + ' - Status Monitor')
        result = super(SequenceFrame, self).onRun(event)
        if result == False:
            statmon.Destroy()

    def updateInstrumentDisplay(self, event=None):
        """Update the list of instruments."""
        self.insts.setItems(self.experiment.getInstrumentStrings())
        self.insts.setSelection(0)
        self.insts.Select(0)
        self.updateActionDisplay()

    def updateActionDisplay(self, event=None):
        """Update the list of actions for changes in selected instrument."""
        instrument = self.experiment.getInstrument(self.insts.getSelection())
        actions = instrument.getActions()
        actionStrings = []
        for action in actions:
            actionStrings.append(action.args['description'])
        self.acts.setItems(actionStrings)

    def updateExperimentDisplay(self, event=None):
        """Refresh the sequence tree."""
        self.tree.refresh()

    def updateName(self, newName=None):
        """Update the name of the experiment."""
        if newName is None:
            newName = self.experimentName
        if self.edited:
            newName += '*'
        self.SetTitle(newName + ' - Experiment Editor')
        self.setupFrames.instruments.SetTitle(newName + ' - Instruments')
        self.setupFrames.constants.SetTitle(newName + ' - Constants')
        self.setupFrames.graphs.SetTitle(newName + ' - Graphs')


    #-------------------------------------------------------------- Setup frames

    def createSetupFrames(self):
        """Create frames for managing constants, instruments, and graphs."""
        if self.premade:
            return None
        command1 = Command(self.updateInstrumentDisplay)
        command2 = Command(self.updateExperimentDisplay)
        command3 = Command(self.flagEdit)
        return SetupFrames(
                InstrumentFrame(self, self.experiment,
                                [command1, command2, command3]),
                ConstantFrame(self, self.experiment, [command3]),
                GraphFrame(self, self.experiment, [command3]))

    def onSetupInstruments(self, event):
        """Open the instrument configuration tool."""
        if self.setupFrames is not None:
            win = self.setupFrames.instruments
            win.populate()
            win.Show()
            win.Raise()

    def onSetupConstants(self, event):
        """Open the constants configuration tool."""
        if self.setupFrames is not None:
            win = self.setupFrames.constants
            win.populate()
            win.Show()
            win.Raise()

    def onSetupGraphs(self, event):
        """Open the graphs configuration tool."""
        if self.setupFrames is not None:
            win = self.setupFrames.graphs
            win.populate()
            win.Show()
            win.Raise()


    #----------------------------------------------------------- Clipboard setup

    def setClipboardButtonStatus(self, cut=None, copy=None, paste=None):
        """Set the enabled state of the clipboard-related buttons.
        
        Parameters
        ----------
        cut : bool
            Whether the 'cut' button should be enabled.
        copy : bool
            Whether the 'copy' button should be enabled.
        paste : bool
            Whether the 'paste' button should be enabled.
        """
        try:
            if cut is not None:
                self.cutButton.Enable(cut)
            if copy is not None:
                self.copyButton.Enable(copy)
            if paste is not None:
                self.pasteButton.Enable(paste)
        except AttributeError:
            pass

    def _createAction(self, event=None):
        """Create a new action based on selections."""
        instrument = self.experiment.getInstrument(self.insts.getSelection())
        actionTuple = instrument.getActions()[self.acts.getSelection()]
        action = constructAction(actionTuple)
        actionDialog = oc.getDialog(action)(self, self.experiment, action)
        result = actionDialog.ShowModal()
        if result == wx.ID_OK:
            self.tree.addAction(action)

    def _beginDrag(self, event=None):
        """Handle initiation of action dragging."""
        instrumentIndex = self.insts.getSelection()
        actionIndex = self.acts.getSelection()

        dropData = DropData()
        dropData.setObject((instrumentIndex, actionIndex))

        dropSource = wx.DropSource(self)
        dropSource.SetData(dropData)
        dropSource.DoDragDrop(True)

    def _onInterrupt(self, event=None):
        """Interrupt a running loop."""
        if self._interrupt:
            self._interrupt = False
            self.experiment.isInterrupted()
            self.toolbar.ToggleTool(_ID_INTERRUPT, False)
        else:
            self._interrupt = True
            self.experiment.interruptLoop()
            self.toolbar.ToggleTool(_ID_INTERRUPT, True)

    def _enableInterrupt(self, enable=True):
        """Enable or disable the interrupt button."""
        self.toolbar.EnableTool(_ID_INTERRUPT, enable)
        self._interrupt = False
        self.toolbar.ToggleTool(_ID_INTERRUPT, False)


#--------------------------------------------------------- Drag and drop storage

class DropData(wx.CustomDataObject):
    """An object for storing data for drag-and-drop creation of actions."""

    def __init__(self):
        wx.CustomDataObject.__init__(self, wx.DataFormat("ActionDrop"))
        self.setObject(None)

    def setObject(self, obj):
        """Set the information necessary to choose the correct action.
        
        Parameters
        ----------
        obj : tuple of int
            A tuple consisting of the two integers: the index of the correct
            instrument in experiment's list and the index of the correct
            action in the instrument's list.
        """
        self.SetData(pickle.dumps(obj))

    def getObject(self):
        """Get the information necessary to construct the correct action.
        
        Returns
        -------
        obj : tuple of int
            A tuple consisting of the two integers: the index of the correct
            instrument in experiment's list and the index of the correct
            action in the instrument's list.
        """
        return pickle.loads(self.GetData())


#---------------------------------------------------------- Drag and drop target

class MyDropTarget(wx.DropTarget):
    """A class to handle drop actions on the tree.
    
    Parameters
    ----------
    tree : ActionTree
        The tree into which actions may be dropped.
    acts : ListBox
        The list box of actions from which actions will be dragged.
    """

    def __init__(self, tree, acts):
        super(MyDropTarget, self).__init__()

        self.data = DropData()
        self.SetDataObject(self.data)

        self.selections = []

        self.tree = tree
        self.acts = acts
        self.selections = []

    def _resetObjects(self):
        """Reset the data objects."""
        self.data = DropData()
        self.SetDataObject(self.data)

    def _saveSelection(self):
        """Record the currently selected tree item(s)."""
        self.selections = self.tree.GetSelections()
        self.tree.UnselectAll()

    def _restoreSelection(self):
        """Reselect the previously selected tree item(s)."""
        self.tree.UnselectAll()
        for i in self.selections:
            self.tree.SelectItem(i)
        self.selections = []

    # pylint: disable=W0613,W0221,C0103
    def OnEnter(self, x, y, defResult):
        """Handle the situation with the user drags something over the tree.
        
        When the user drags the right data type over the tree, unselect
        all tree items and save them to a list.
        """
        self._saveSelection()
        return defResult

    def OnLeave(self):
        """Handle the situation when the user drags something off the tree.
        
        When the user drags the data from the action list outside of the tree
        window, restore the items that were selected before the tree window
        was entered.
        """
        self._restoreSelection()

    def OnDrop(self, x, y):
        """Reselect the previously selected items after data is dropped."""
        self._restoreSelection()
        return True

    def OnDragOver(self, x, y, defResult):
        """When data is dragged over a tree item, select that item."""
        item = self.tree.HitTest((x, y))[0]
        selections = self.tree.GetSelections()
        if item:
            if selections != [item]:
                self.tree.UnselectAll()
                self.tree.SelectItem(item)
        elif selections:
            self.tree.UnselectAll()
        return defResult

    def OnData(self, x, y, defResult):
        """Tell the tree to make the action.
        
        This method is called when `self.OnDrop` returns `True`. It tells the
        `ActionTree` to create the object based on the stored data tuple.
        """
        if self.GetData():
            data = self.data.getObject()
            item = self.tree.HitTest((x, y))[0]
            self.tree.insertAction(data, item)
            self._resetObjects()
        return defResult
    # pylint: enable=W0613,W0221,C0103


#----------------------------------------------------------- Action tree control

class ActionTree(wx.TreeCtrl):
    """A tree control for displaying experiment sequences.
    
    This subclass of wxTreeCtrl implements a number of features, including
    drag-and-drop and copy-and-paste while ensuring that the underlying 
    experiment sequence remains in sync.
    
    Parameters
    ----------
    parent : wxWindow
        The panel or frame which contains this control.
    experiment : Experiment
        The experiment which manages the action sequence represented in this
        control.
    wxId : int
        The wxPython internal ID of this control.
    style : int
        The style for the control in terms of wx constants.
    parentFrame : ExperimentFrame
        The ExperimentFrame (or a derived class thereof) which contains this
        control.
    """

    def __init__(self, parent, experiment, idnum=wx.ID_ANY,
                 style=_DEFAULT_OPTIONS, parentFrame=None):

        super(ActionTree, self).__init__(parent, idnum, style=style)
        self.experimentFrame = parentFrame
        self.experiment = experiment
        self.clipboard = None
        self.moveData = None
        self.activeItem = None
        self.root = self.AddRoot('The Root Item')
        self.SetItemData(self.root, self.experiment.getActionRoot())
        self.SetIndent(_INDENT)
        self.endmarkFont = wx.Font(9, wx.FONTFAMILY_DEFAULT,
                                   wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL)

        # Bind the event handlers
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self._onDoubleClick)
        self.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self._onRightClick)
        self.Bind(wx.EVT_LEFT_DOWN, self._onLeftClick)
        self.Bind(wx.EVT_TREE_BEGIN_DRAG, self._onBeginDrag)
        self.Bind(wx.EVT_TREE_END_DRAG, self._onEndDrag)

        self.ExpandAll()

    def buildDefaultTree(self):
        """Fill a tree with default values. 
        
        Currently, the values are for testing purposes only and are not
        really useful. For the final, working version, everything except
        the set filename action will be removed.
        """
        location = pt.normalizePath(pt.os.path.expanduser('~') + '/Desktop')
        inst = self.experiment.getInstrument(0)

        actSetFile = inst.getAction('set_file', True)
        actSetFile.setInputValues([location, r'testing', r'Auto'])
        self._appendAction(self.root, actSetFile)

        nameRange1 = "Item 0"
        actRange1 = inst.getAction('scan_num', True)
        actRange1.setInputValues([[(2, 2 + 10, 1)]])
        actRange1.setInputColumns([nameRange1])
        actRange2 = inst.getAction('scan_num', True)
        actRange2.setInputValues([[(3, 5, 1)]])
        actRange2.setInputColumns(['AnotherNumber'])
        actRange1.appendChild(actRange2)
        actCalc = inst.getAction('calculate', True)
        actCalc.setInputValues(['3*#(Item 0)'])
        actRange2.appendChild(actCalc)
        actWait = inst.getAction('wait', True)
        actWait.setInputValues([.2])
        actRange2.appendChild(actWait)
        self._appendAction(self.root, actRange1)
        self.ExpandAll()

    def refresh(self):
        """Fill in the entire tree from the experiment's action sequence."""
        self.DeleteChildren(self.root)

        self._buildSubtree(self.root)
        lastChild = self.GetLastChild(self.root)
        if self.GetItemData(lastChild) is None:
            self.Delete(lastChild)

    def getItemAtPosition(self, parentItem, index):
        """Get the item at a position under a specified parent.
        
        Parameters
        ----------
        parentItem : wxTreeItemId
            The parent under which the desired item is located.
        index : int
            The position of the item to get.
            
        Returns
        -------
        wxTreeItemId
            The item at the specified position, or `None` if the position
            is out of range.
        """
        count = self.GetChildrenCount(parentItem)
        if index < count:
            child, cookie = self.GetFirstChild(parentItem)
            for currentIndex in range(count):
                if currentIndex == index:
                    return child
                child, cookie = self.GetNextChild(parentItem, cookie)
        return None

    def getItemPosition(self, parentItem, item):
        """Get the position of an item within its list of siblings.
        
        Parameters
        ----------
        parentItem : wxTreeItemId
            The parent of the item in question.
        item : wxTreeItemId
            The item whose position is sought.
        
        Returns
        -------
        int
            The position of `item` in the list of children of `parentItem`. If
            `item` is not a child of `parentItem`, then `None` is returned.
        """
        count = self.GetChildrenCount(parentItem)
        child, cookie = self.GetFirstChild(parentItem)
        for currentIndex in range(count):
            if child is item:
                return currentIndex
            child, cookie = self.GetNextChild(parentItem, cookie)
        return None


    #===========================================================================
    # Action and item insertion
    #===========================================================================

    def _appendAction(self, parentItem, action, skipCore=False):
        """Append an action to a sub-tree.
        
        Parameters
        ----------
        parentItem : wxTreeItemId
            The item to which the new action should be appended.
        action : Action
            The action which should be appended.
        skipCore : bool
            Whether to skip operations on `Action` objects (from the `core`
            package). This should be `True` when `action` is already formed
            (for instance, when creating a GUI tree branch from an existing
            `Action` tree, as is done by the `_buildSubtree` method).
        
        Returns
        -------
        wxTreeItem
            The newly created and appended item.
        """
        newItem = self.AppendItem(parentItem, str(action))
        if action.isEnabled():
            self.SetItemTextColour(newItem, wx.BLACK)
        else:
            self.SetItemTextColour(newItem, wx.LIGHT_GREY)
        self.SetItemData(newItem, action)
        parentAction = self.GetItemData(parentItem)
        if not skipCore:
            parentAction.appendChild(action)
        self._buildSubtree(newItem)
        return newItem

    def _insertActionAtItem(self, parentItem, posItem, action, skipCore=False):
        """Insert an action before a specified item.
        
        Parameters
        ----------
        parentItem : wxTreeItemId
            The item under which to insert the new item.
        posItem : wxTreeItemId
            The item indicating the position where the new item should be
            inserted (i.e. the item which should be immediately **after** the
            new item once it has been inserted).
        action : Action
            The action to add to the branch.
        skipCore : bool
            Whether to skip operations on `Action` objects (from the `core`
            package). This should be `True` when `action` is already formed
            (for instance, when creating a GUI tree branch from an existing
            `Action` tree, as is done by the `_buildSubtree` method).

        Returns
        -------
        wxTreeItemId
            The item which has been added.
        """
        newItemText = str(action)
        if self.GetFirstChild(parentItem)[0] is posItem:
            newItem = self.PrependItem(parentItem, newItemText)
        else:
            previousItem = self.GetPrevSibling(posItem)
            newItem = self.InsertItem(parentItem, previousItem, newItemText)
        if not skipCore:
            parentAction = self.GetItemData(parentItem)
            posAction = self.GetItemData(posItem)
            parentAction.insertChildBefore(action, posAction)
        if action.isEnabled():
            self.SetItemTextColour(newItem, wx.BLACK)
        else:
            self.SetItemTextColour(newItem, wx.LIGHT_GREY)
        self.SetItemData(newItem, action)
        self._buildSubtree(newItem)
        return newItem

    def _buildSubtree(self, parentItem):
        """Recursively Construct a sub-tree under a specified item.
        
        Parameters
        ----------
        parentItem : wxTreeItemId
            The tree item whose sub-tree should be constructed.
            
        Returns
        -------
        list of wxTreeItemId
            The new items created for the subtree.
        """
        newChildren = []
        def auxBuildSubtree(nodeItem):
            """Help build the subtree."""
            count = self.GetChildrenCount(nodeItem)
            if count > 0:
                self.DeleteChildren(nodeItem)
            nodeAction = self.GetItemData(nodeItem)
            if nodeAction.allowsChildren():
                children = nodeAction.getChildren()
                for child in children:
                    newItem = self._appendAction(nodeItem, child, True)
                    newChildren.append(newItem)
                self._appendEndMark(nodeItem)
        auxBuildSubtree(parentItem)
        self.ExpandAll()
        if _PRINT_SEQUENCE:
            self.experiment.getActionRoot().printme()
        return newChildren

    def _appendEndMark(self, parentItem):
        """Append an end-of-container marker.
        
        Parameters
        ----------
        parentItem : wxTreeItemId
            The item for the container whose last item should be the end
            marker.
        """
        newMark = self.AppendItem(parentItem, '-----------------')
        self.SetItemTextColour(newMark, wx.LIGHT_GREY)
        # self.SetItemFont(newMark, self.endmarkFont)
        self.SetItemData(newMark, None)


    #===========================================================================
    # Clipboard control (copy/paste)
    #===========================================================================

    def clearClipboard(self):
        """Clear the clipboard, trashing its contents."""
        if self.clipboard is not None:
            if self.clipboard[0] == 'cut':
                self.clipboard[1].trash()
            self.clipboard = None

    def cutAction(self, item):
        """Cut an item from the tree to the clipboard.
        
        Parameters
        ----------
        item : wxTreeItemId
            The item to cut from the tree.
        """
        self.clearClipboard()
        parentItem = self.GetItemParent(item)
        parentAction = self.GetItemData(parentItem)
        action = self.GetItemData(item)
        self.Delete(item)
        parentAction.removeChild(action)
        self.clipboard = ('cut', action)
        self.flagEdit()

    def copyAction(self, item):
        """Copy an item from the tree to the clipboard.
        
        Parameters
        ----------
        item : wxTreeItemId
            The item to copy from the tree.
        """
        self.clearClipboard()
        action = self.GetItemData(item)
        self.clipboard = ('copy', action.clone())

    def pasteAction(self, item):
        """Paste an item from the clipboard onto the tree.
                
        Parameters
        ----------
        item : wx.TreeItemId
            The tree item before which to paste the clipboard's contents.
            
        Notes
        -----
        At the end of this operation, the clipboard's `operation` flag is
        always 'copy', and its `action` is always a clone of whatever action
        was originally put there. That way, the user can continue to do paste
        operations even if the clipboard was filled using a cut (and clones
        do not need to be trashed, since they were never instantiated in the
        first place).
        """
        if self.clipboard is not None:
            action = self.clipboard[1]
            if item is None:
                self._appendAction(self.root, action)
            elif self.GetItemData(item) is None:
                parentItem = self.GetItemParent(item)
                self.Delete(item)
                self._appendAction(parentItem, action)
                self._appendEndMark(parentItem)
            else:
                parentItem = self.GetItemParent(item)
                self._insertActionAtItem(parentItem, item, action)
            self.clipboard = ('copy', action.clone())
            self.flagEdit()

    def _updateClipboardStatus(self, item):
        """Update the active item and the clipboard buttons."""
        paste = self.clipboard is not None
        if item is None:
            self.activeItem = None
            self.experimentFrame.setClipboardButtonStatus(False, False, paste)
        elif self.GetItemData(item) is None:
            self.activeItem = item
            self.experimentFrame.setClipboardButtonStatus(False, False, paste)
        else:
            self.activeItem = item
            self.experimentFrame.setClipboardButtonStatus(True, True, paste)

    def _traverse(self, func, startNode):
        """Apply a function recursively to all children of an action.
        
        Parameters
        ----------
        func : function
            The function to apply to each node in the sub-tree.
        startNode : wx.TreeItem
            The parent to which, and to whose children, the function should be
            applied.
        """

        def traverseAux(node, depth, func):
            """Traverse the sub-elements of the current node."""
            count = self.GetChildrenCount(node, 0)
            child, cookie = self.GetFirstChild(node)
            for _ in range(count):
                func(child, depth)
                traverseAux(child, depth + 1, func)
                child, cookie = self.GetNextChild(node, cookie)
        func(startNode, 0)
        traverseAux(startNode, 1, func)

    def _itemIsChildOf(self, potentialDescendant, ancestor):
        """Determine whether one item is a child of another.
        
        Parameters
        ----------
        potentialDescendant : wx.TreeItem
            The item whose ancestry to check.
        ancestor : wx.TreeItem
            The item which might be an ancestor of `potentialDescendant`.
        
        Returns
        -------
        bool
            `True` if `potentialDescendant` is in fact a descendant of
            `ancestor`, or `False` otherwise.
        """
        result = [False]
        def _testFunction(node, _):
            """Return whether a node is the desired descendant."""
            if node == potentialDescendant:
                result[0] = True

        self._traverse(_testFunction, ancestor)
        return result[0]

    def _onBeginDrag(self, event):
        """Respond to drag start: record the item being dragged.
        
        Parameters
        ----------
        event : wxTreeEvent
            The TreeEvent which contains the object to be moved.
        """
        event.Allow()
        eventItem = event.GetItem()
        if self.GetItemData(eventItem) is not None:
            self.moveData = eventItem
        else:
            self.moveData = None

    def _onEndDrag(self, event):
        """Respond to drag end: move the item being dragged."""
        if self.moveData is None:
            return

        if event.GetItem().IsOk():
            target = event.GetItem()
        else:
            target = None

        if self._itemIsChildOf(target, self.moveData):
            self.Unselect()
            return

        self.moveAction(self.moveData, target)

    def _onLeftClick(self, event):
        """Respond to left click: select item."""
        point = event.GetPosition()
        item, flags = self.HitTest(point)
        if flags == wx.TREE_HITTEST_NOWHERE:
            item = None
            self.UnselectAll()
        else:
            self._updateClipboardStatus(item)
            self.SelectItem(item)
        self._updateClipboardStatus(item)
        event.Skip()

    def _onRightClick(self, event):
        """Respond to right click: show context menu."""

        event.Skip()
        item = event.GetItem()
        self.SelectItem(item)
        self._updateClipboardStatus(item)

        def editAction(eventSub):
            """Edit the selected action."""
            self.editAction(item)

        def editInstrument(eventSub):
            """Edit the instrument bound to the selected action."""
            action = self.GetItemData(item)
            instdialog = oc.RebindInstrumentDialog(self, self.experiment,
                                                   action)
            result = instdialog.ShowModal()
            if result == wx.ID_OK:
                instdialog.update()
                self.SetItemText(item, str(action))

        def deleteAction(eventSub):
            """Delete the selected action."""
            self.deleteAction(item)

        menu = wx.Menu()

        menu.Append(wx.ID_CUT, 'Cut')
        menu.Append(wx.ID_COPY, 'Copy')
        menu.Append(wx.ID_PASTE, 'Paste')
        menu.AppendSeparator()
        menu.Append(wx.ID_EDIT, 'Edit action')
        menu.Append(wx.ID_DELETE, 'Delete action')
        menu.Append(_ID_REBIND, 'Change instrument')
        if self.GetItemData(item) is not None:
            menu.Enable(wx.ID_CUT, True)
            menu.Enable(wx.ID_COPY, True)
            menu.Enable(wx.ID_EDIT, True)
            menu.Enable(wx.ID_DELETE, True)
            menu.Enable(_ID_REBIND, True)
            if self.GetItemData(item).isEnabled():
                menu.Append(_ID_ENABLE, 'Disable action')
            else:
                menu.Append(_ID_ENABLE, 'Enable action')
        else:
            menu.Enable(wx.ID_CUT, False)
            menu.Enable(wx.ID_COPY, False)
            menu.Enable(wx.ID_EDIT, False)
            menu.Enable(wx.ID_DELETE, False)
            menu.Enable(_ID_REBIND, False)
            menu.Append(_ID_ENABLE, 'Enable action')
            menu.Enable(_ID_ENABLE, False)
        if self.clipboard is not None:
            menu.Enable(wx.ID_PASTE, True)
        else:
            menu.Enable(wx.ID_PASTE, False)

        menu.Bind(wx.EVT_MENU, self.onCut, id=wx.ID_CUT)
        menu.Bind(wx.EVT_MENU, self.onCopy, id=wx.ID_COPY)
        menu.Bind(wx.EVT_MENU, self.onPaste, id=wx.ID_PASTE)
        menu.Bind(wx.EVT_MENU, editAction, id=wx.ID_EDIT)
        menu.Bind(wx.EVT_MENU, deleteAction, id=wx.ID_DELETE)
        menu.Bind(wx.EVT_MENU, editInstrument, id=_ID_REBIND)
        menu.Bind(wx.EVT_MENU, self.onEnable, id=_ID_ENABLE)

        self.PopupMenu(menu)

    def _onDoubleClick(self, event):
        """Respond to double click: edit the action."""
        item = event.GetItem()
        if self.GetItemData(item) is not None:
            self.editAction(item)

    def onEnable(self, event):
        """Enable or disable the selected item."""
        toEnable = [False]
        def enableAux(node, dummy):
            """Do something."""
            if node is not None:
                currentAction = self.GetItemData(node)
                if currentAction is not None:
                    currentAction.setEnabled(toEnable[0])

        item = self.GetSelection()

        if item is not None:
            action = self.GetItemData(item)
            if action is not None:
                if not action.isEnabled():
                    toEnable[0] = True
                self._traverse(enableAux, item)
                self.flagEdit()

        self.refresh()

    def enableTree(self, top, enable):
        """Change the color of a tree of actions based on the top."""
        if top is None:
            return
        action = self.GetItemData(top)
        if action is None:
            self.SetItemTextColour(top, wx.LIGHT_GREY)
            return
        if enable:
            self.SetItemTextColour(top, wx.BLACK)
        else:
            self.SetItemTextColour(top, wx.LIGHT_GREY)
        childrenCount = self.GetChildrenCount(top, False)
        child, cookie = self.GetFirstChild(top)
        for _ in range(childrenCount):
            self.enableTree(child, enable)
            child, cookie = self.GetNextChild(child, cookie)

    def onCut(self, event):
        """Cut the item from the tree (pass the work to the tree)."""
        self.cutAction(self.GetSelection())

    def onCopy(self, event):
        """Copy the selected item (pass the work to the tree)."""
        self.copyAction(self.GetSelection())

    def onPaste(self, event):
        """Paste an item into the tree (pass the work to the tree)."""
        self.pasteAction(self.GetSelection())

    def addAction(self, action):
        """Add an action to the end of the tree.
        
        Parameters
        ----------
        action : Action
            The action to add to the end of the tree (at the highest level).
        """
        self._appendAction(self.root, action)
        self.flagEdit()

    def insertAction(self, actionTuple, targetItem):
        """Insert an action above the specified item.
        
        Parameters
        ----------
        actionTuple : tuple of int 
            A tuple consisting of two integers. The first should be the index
            of the instrument in the experiment's list. The second should be
            the index of the action within the instrument's list.
        targetItem : wxTreeItemId
            The tree item above which the new action should be added.
        """
        instrument = self.experiment.getInstrument(actionTuple[0])
        actionSpec = instrument.getActions()[actionTuple[1]]
        action = constructAction(actionSpec)

        if not targetItem:
            target = None
        else:
            target = targetItem

        dialog = oc.getDialog(action)(self, self.experiment, action)
        result = dialog.ShowModal()
        if result == wx.ID_OK:
            if target is None:
                self._appendAction(self.root, action)
            elif self.GetItemData(target) is None:
                targetParent = self.GetItemParent(target)
                self.Delete(target)
                self._appendAction(targetParent, action)
                self._appendEndMark(targetParent)
            else:
                targetParent = self.GetItemParent(target)
                self._insertActionAtItem(targetParent, target, action)
            self.flagEdit()

    def editAction(self, item):
        """Edit the selected action.
        
        Parameters
        ----------
        item : wxTreeItemId
            The item whose action the user wants to edit.
        """
        action = self.GetItemData(item)
        dialog = oc.getDialog(action)(self, self.experiment, actionIn=action)
        result = dialog.ShowModal()
        if result == wx.ID_OK:
            self.SetItemText(item, str(action))
            self.flagEdit()

    def moveAction(self, sourceItem, targetItem):
        """Move the item and its action from one place to another.
        
        Essentially, this is just a cut and paste operation rolled into one,
        allowing for drag-and-drop move operations without messing with the
        clipboard.
        
        Parameters
        ----------
        sourceItem : wxTreeItemId
            The item which is to be moved.
        targetItem : wxTreeItemId
            The item before which `sourceItem` should be placed.
        """
        self.clearClipboard()
        parentItem = self.GetItemParent(sourceItem)
        parentAction = self.GetItemData(parentItem)
        action = self.GetItemData(sourceItem)
        self.Delete(sourceItem)
        parentAction.removeChild(action)

        if targetItem is None:
            self._appendAction(self.root, action)
        elif self.GetItemData(targetItem) is None:
            parentItem = self.GetItemParent(targetItem)
            self.Delete(targetItem)
            self._appendAction(parentItem, action)
            self._appendEndMark(parentItem)
        else:
            parentItem = self.GetItemParent(targetItem)
            self._insertActionAtItem(parentItem, targetItem, action)
#         self.clipboard = ('copy', action.clone())
        self.flagEdit()

    def deleteAction(self, item):
        """Delete the action contained within a given tree item.
        
        Parameters
        ----------
        item : wxTreeItemId
            The tree item which should be deleted, along with its associated
            action and all of their children.
        """
        action = self.GetItemData(item)
        parentItem = self.GetItemParent(item)
        parentAction = self.GetItemData(parentItem)
        parentAction.removeChild(action)
        action.trash()
        self.Delete(item)
        self.flagEdit()

    def flagEdit(self):
        """Indicate that the sequence has been edited."""
        try:
            self.experimentFrame.flagEdit()
        except AttributeError:
            log.warn('Parent frame has no method flagEdit')


#--------------------------------------------------------------- InstrumentFrame

class InstrumentFrame(wx.Frame):
    """A frame for configuring the instruments in an experiment.
    
    Parameters
    ----------
    parent : wx.Window
        The panel or frame which contains this instrument frame.
    experiment : Experiment
        The experiment whose instruments should be modified by this frame.
    successAction : Command or list of Command
        The action or actions to perform when the instruments are updated.
    """

    def __init__(self, parent, experiment, successAction=None):
        """Create an instrument frame."""
        super(InstrumentFrame, self).__init__(parent,
                                              title='Instrument Manager',
                                              size=(300, 300))
        self.experiment = experiment
        if successAction is None:
            self.successAction = []
        else:
            self.successAction = successAction

        mainpanel = gh.Panel(self, 'vertical')

        instpanel = gh.Panel(mainpanel, 'vertical')
        self.instrumentBox = wx.ListBox(instpanel, wx.ID_ANY, choices=[],
                                        style=wx.LB_SINGLE | wx.LB_ALWAYS_SB)
        instpanel.add(self.instrumentBox, 1, wx.EXPAND | wx.ALL, 5)
        self.instrumentBox.Bind(wx.EVT_LISTBOX_DCLICK, self.onEdit)
        self.instrumentBox.Bind(wx.EVT_LISTBOX, self.onSelection)

        additionpanel = gh.Panel(mainpanel, 'horizontal')
        additionpanel.addLabel('Instrument to add:', 3)
        self.instrumentOptions = wx.ComboBox(additionpanel, choices=[],
                                             style=wx.CB_READONLY)
        additionpanel.add(self.instrumentOptions, 1, wx.EXPAND | wx.ALL, 3)

        buttonpanel = gh.Panel(mainpanel, 'horizontal')
        self.btnAdd = buttonpanel.addButton('Add', handler=self.onAdd)
        self.btnEdit = buttonpanel.addButton('Edit', handler=self.onEdit)
        self.btnRemove = buttonpanel.addButton('Remove', handler=self.onRemove)

        mainpanel.add(instpanel, 1, wx.ALL | wx.EXPAND, 0)
        mainpanel.add(additionpanel, 0, wx.ALL | wx.EXPAND, 0)
        mainpanel.add(buttonpanel, 0, wx.BOTTOM | wx.ALIGN_CENTER_HORIZONTAL, 3)

        self.Bind(wx.EVT_CLOSE, self.onClose)

        self.SetIcon(img.getInstrumentsIconIcon())

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(mainpanel, 1, wx.EXPAND)
        self.SetSizeHints(300, 300)
        self.SetSizer(sizer)
        self.Fit()

        self.populate()

    def populate(self):
        """Fill the available and included instruments boxes."""
        instrumentStrings = self.experiment.getInstrumentStrings()[2:]
        availableStrings = INSTRUMENT_MANAGER.getAvailableInstrumentStrings()
        self.instrumentBox.SetItems(instrumentStrings)
        if self.instrumentBox.GetCount() > 0:
            self.instrumentBox.SetSelection(0)
        self.instrumentOptions.SetItems(availableStrings)
        self.instrumentOptions.Select(0)
        self.updateButtonEnabled()

    def updateButtonEnabled(self):
        """Enable and disable buttons based on selections."""
        isel = self.instrumentBox.GetSelection()
        if 0 <= isel < len(self.instrumentBox.GetItems()):
            self.btnEdit.Enable(True)
            self.btnRemove.Enable(True)
        else:
            self.btnEdit.Enable(False)
            self.btnRemove.Enable(False)

    def onAdd(self, event):
        """Add a new instrument."""
        selection = self.instrumentOptions.GetStringSelection()
        newInstrument = INSTRUMENT_MANAGER.constructInstrument(selection,
                                                               self.experiment)
        instrumentDialog = InstrumentDialog(self, newInstrument)
        if instrumentDialog.ShowModal() == wx.ID_OK:
            self.experiment.addInstrument(newInstrument)
            self.populate()
            self.updateButtonEnabled()
            self.executeSuccessActions()

    def onEdit(self, event):
        """Edit the selected instrument."""
        selectionIndex = self.instrumentBox.GetSelection() + 2
        instrument = self.experiment.getInstrument(selectionIndex)
        instrumentDialog = InstrumentDialog(self, instrument)
        if instrumentDialog.ShowModal() == wx.ID_OK:
            self.populate()
            self.executeSuccessActions()

    def onRemove(self, event):
        """Remove the selected instrument."""
        localsel = self.instrumentBox.GetSelection()
        ins = self.experiment.getInstrument(localsel + 2)
        try:
            self.experiment.removeInstrument(ins)
        except InstrumentInUseError as err:
            wrapper = textwrap.TextWrapper(width=60)
            txt0 = ('The instrument is still in use. The following actions '
                    'must be bound to some other instrument or deleted '
                    'before this instrument can be deleted:')
            txt = wrapper.fill(txt0) + '\n'
            wrapper.initial_indent = '  '
            wrapper.subsequent_indent = '      '
            for act in err.actions:
                txt += wrapper.fill(act) + '\n'
            dialog = wx.MessageDialog(self, txt, 'Cannot delete instrument',
                                      wx.OK | wx.ICON_ERROR)
            dialog.ShowModal()
            dialog.Destroy()

        self.populate()
        self.updateButtonEnabled()
        self.executeSuccessActions()

    def executeSuccessActions(self):
        """Execute any success actions."""
        for successAction in self.successAction:
            successAction.execute()

    def onSelection(self, event):
        """Change the buttons to reflect selections."""
        self.updateButtonEnabled()

    def onClose(self, event):
        """Hide the frame."""
        self.Show(False)


#------------------------------------------------------------------- Graph Frame

class GraphFrame(wx.Frame):
    """A frame for setting the graphs which the owning experiment will create.
    
    Parameters
    ----------
    parent : wx.Window
        The panel or frame which contains this graph frame.
    experiment : Experiment
        The experiment whose graphs should be modified by this frame.
    successAction : list of Command
        The action or actions to perform when the graphs are updated.
    """

    def __init__(self, parent, experiment, successAction=None):
        super(GraphFrame, self).__init__(parent, title='Graph Manager')
        self.experiment = experiment

        self.graphData = self.experiment.getGraphStringsAndStates()
        if successAction is None:
            self.successAction = []
        else:
            self.successAction = successAction

        mainpanel = gh.Panel(self)

        graphpanel = gh.Panel(mainpanel)
        self.graphs = wx.ListBox(graphpanel, wx.ID_ANY, choices=[],
                                 style=wx.LB_SINGLE | wx.LB_ALWAYS_SB)
        graphpanel.add(self.graphs, 1, wx.EXPAND | wx.ALL, 5)
        self.graphs.Bind(wx.EVT_LISTBOX_DCLICK, self.onEdit)
        self.graphs.Bind(wx.EVT_LISTBOX, self.onSelection)

        buttonpanel = gh.Panel(mainpanel, 'horizontal')
        self.btnAdd = buttonpanel.addButton('Add', handler=self.onAdd)
        self.btnEdit = buttonpanel.addButton('Edit', handler=self.onEdit)
        self.btnRemove = buttonpanel.addButton('Remove', handler=self.onRemove)

        mainpanel.add(graphpanel, 1, wx.EXPAND | wx.ALL, 3)
        mainpanel.add(buttonpanel, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.BOTTOM, 3)

        self.Bind(wx.EVT_CLOSE, self.onClose)
        self.SetIcon(img.getGraphsIconIcon())

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(mainpanel, 1, wx.EXPAND)
        self.SetSizeHints(300, 300)
        self.SetSizer(sizer)
        self.Fit()
        self.populate()

    def populate(self):
        """Fill the list of graphs."""
        self.graphData = self.experiment.getGraphStringsAndStates()
        self.graphs.SetItems([datum[0] for datum in self.graphData])
        for index, datum in enumerate(self.graphData):
            name, enabled = datum
            if not enabled:
                self.graphs.SetItemForegroundColour(index, wx.LIGHT_GREY)
                self.graphs.SetString(index, name + ' (disabled)')

        num = len(self.graphData)
        if num > 0:
            self.graphs.SetSelection(0)
        self.updateButtonEnabled()

    def onAdd(self, event):
        """Add a new graph."""
        if self.checkAbility():
            dialog = GraphDialog(self, self.experiment)
            val = dialog.ShowModal()
            if val == wx.ID_OK:
                self.populate()
                self.executeSuccessActions()

    def onEdit(self, event):
        """Edit an existing graph."""
        pos = self.graphs.GetSelection()
        selected = self.experiment.getGraph(pos)
        dialog = GraphDialog(self, self.experiment, selected)
        val = dialog.ShowModal()
        if val == wx.ID_OK:
            self.populate()
            self.executeSuccessActions()

    def onRemove(self, event):
        """Delete an existing graph."""
        pos = self.graphs.GetSelection()
        selected = self.experiment.getGraph(pos)
        self.experiment.removeGraph(selected)
        self.populate()
        self.executeSuccessActions()

    def executeSuccessActions(self):
        """Execute any success actions."""
        for successAction in self.successAction:
            successAction.execute()

    def updateButtonEnabled(self):
        """Enable or disable buttons based on current selection."""
        isel = self.graphs.GetSelection()
        if 0 <= isel < len(self.graphs.GetItems()):
            self.btnEdit.Enable(True)
            self.btnRemove.Enable(True)
        else:
            self.btnEdit.Enable(False)
            self.btnRemove.Enable(False)

    def checkAbility(self):
        """Return whether there are enough columns to create a graph."""
        columnNames = self.experiment.getStorageBinNames()[1]

        if len(columnNames) < 2:
            wx.MessageBox(('A graph cannot be created at this time. '
                           'You must have at least two columns '
                           'defined in order to graph things.'),
                          'Cannot create graph.',
                          wx.OK | wx.ICON_ERROR)
            return False
        return True

    def onSelection(self, event):
        """Change the buttons to reflect selections."""
        self.updateButtonEnabled()

    def onClose(self, event):
        """Hide the frame."""
        self.Show(False)


#----------------------------------------------------------------- ConstantFrame

class ConstantFrame(wx.Frame):
    """A frame for setting the constants which the owning experiment can use.
    
    Parameters
    ----------
    parent : wx.Window
        The panel or frame which contains this constant frame.
    experiment : Experiment
        The experiment whose constants should be modified by this frame.
    successAction : Command or list of Command
        The action or actions to perform when the constants are updated.
    """

    def __init__(self, parent, experiment, successAction=None):
        super(ConstantFrame, self).__init__(parent, size=(300, 300))
        self.experiment = experiment
        if successAction is None:
            self.successAction = []
        else:
            self.successAction = successAction

        mainpanel = gh.Panel(self)
        headerlist = ['Name', 'Value']
        formatlist = [wx.LIST_FORMAT_LEFT, wx.LIST_FORMAT_RIGHT]
        listpanel = gh.Panel(mainpanel)
        self.constants = gh.StaticListCtrl(listpanel, wx.ID_ANY, headerlist,
                                           formatlist)
        self.constants.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onSelection)
        listpanel.add(self.constants, 1, wx.EXPAND | wx.ALL, 5)

        settingspanel = gh.Panel(mainpanel, 'flex_grid', None, 1, 4, 3, 3)
        settingspanel.addGrowableColumn(1, 1)
        settingspanel.addGrowableColumn(3, 1)
        self.name = settingspanel.addLabeledText('Name:', '', 3)
        self.value = settingspanel.addLabeledText('Value:', '', 3)
        self.name.Bind(wx.EVT_TEXT, self.onEdit)
        self.value.Bind(wx.EVT_TEXT, self.onEdit)

        buttonpanel = gh.Panel(mainpanel, 'horizontal')
        self.btnAdd = buttonpanel.addButton('Add', handler=self.onAdd)
        self.btnSet = buttonpanel.addButton('Set', handler=self.onSave)
        self.btnRemove = buttonpanel.addButton('Remove', handler=self.onRemove)
        self.btnClear = buttonpanel.addButton('Clear', handler=self.onClear)
        self.btnAdd.Enable(False)
        self.btnRemove.Enable(False)
        self.btnSet.Enable(False)
        self.btnClear.Enable(False)

        mainpanel.add(listpanel, 1, wx.EXPAND | wx.ALL, 0)
        mainpanel.add(settingspanel, 0, wx.EXPAND | wx.ALL, 0)
        mainpanel.add(buttonpanel, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.BOTTOM, 3)

        self.Bind(wx.EVT_CLOSE, self.onClose)
        self.SetIcon(img.getConstantsIconIcon())
        self.populate()

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(mainpanel, 1, wx.EXPAND)
        self.SetSizeHints(300, 300)
        self.SetSizer(sizer)
        self.Fit()

    def populate(self):
        """Read the constants (names and values) from the experiment."""
        self.constants.DeleteAllItems()
        constants = self.experiment.getAllConstants()
        for currentName in constants:
            currentValue = str(constants[currentName])
            position = self.constants.GetItemCount()
            self.constants.InsertStringItem(position, currentName)
            self.constants.SetStringItem(position, 1, currentValue)

    def executeSuccessActions(self):
        """Execute any success actions which have been defined."""
        for successAction in self.successAction:
            successAction.execute()

    def onAdd(self, event):
        """Add a new constant with the entered name and value."""
        if not self.name.GetValue() or not self.value.GetValue():
            return
        if self.checkValue() > 0:
            return
        numItems = self.constants.GetItemCount()
        newName = self.name.GetValue()
        newValue = self.value.GetValue()
        self.constants.InsertStringItem(numItems, newName)
        self.constants.SetStringItem(numItems, 1, newValue)

        self.experiment.setConstant(newName, float(newValue))
        self.name.Clear()
        self.value.Clear()
        self.deselectAll()
        self.btnAdd.Enable(False)
        self.btnSet.Enable(False)
        self.btnRemove.Enable(False)
        self.btnClear.Enable(False)
        self.executeSuccessActions()

    def onRemove(self, event):
        """Remove the selected constant."""
        index = self.constants.GetFocusedItem()
        self.experiment.removeConstant(self.name.GetValue())
        self.constants.DeleteItem(index)
        self.name.SetValue("")
        self.value.SetValue("")
        self.btnAdd.Disable()
        self.btnRemove.Disable()
        self.btnSet.Disable()
        self.deselectAll()
        self.btnAdd.Enable(False)
        self.btnSet.Enable(False)
        self.btnRemove.Enable(False)
        self.btnClear.Enable(False)
        self.executeSuccessActions()

    def onClear(self, event):
        """Clear the name and value controls."""
        self.name.SetValue('')
        self.value.SetValue('')
        self.btnAdd.Enable(False)
        self.btnSet.Enable(False)
        self.btnRemove.Enable(False)
        self.deselectAll()

    def onSave(self, event):
        """Save the value if it is legitimate."""
        if not self.name.GetValue() or not self.value.GetValue():
            return
        if self.checkValue() > 0:
            return
        index = self.constants.GetFocusedItem()
        newName = self.name.GetValue()
        newValue = self.value.GetValue()
        self.experiment.setConstant(newName, float(newValue))
        self.constants.DeleteItem(index)
        self.constants.InsertStringItem(index, newName)
        self.constants.SetStringItem(index, 1, newValue)
        self.name.Clear()
        self.value.Clear()
        self.deselectAll()
        self.btnAdd.Enable(False)
        self.btnSet.Enable(False)
        self.btnRemove.Enable(False)
        self.btnClear.Enable(False)
        self.executeSuccessActions()

    def deselectAll(self):
        """Deselect all items in the list."""
        for index in range(self.constants.GetItemCount()):
            self.constants.Select(index, False)

    def onEdit(self, event):
        """Update buttons based on the contents of the controls."""
        self.btnRemove.Enable(False)
        nameLength = len(self.name.GetValue())
        valueLength = len(self.name.GetValue())
        if nameLength == valueLength == 0:
            self.btnClear.Enable(False)
        elif nameLength == 0 or valueLength == 0:
            self.btnAdd.Disable()
            self.btnSet.Disable()
            self.btnClear.Enable(True)
        elif self.experiment.getConstant(self.name.GetValue()) is not None:
            self.btnAdd.Disable()
            self.btnSet.Enable()
            self.btnClear.Enable(True)
        else:
            self.btnAdd.Enable()
            self.btnSet.Disable()
            self.btnClear.Enable(True)

    def onSelection(self, event):
        """Update buttons and values as the list selection changes."""
        if self.constants.GetFocusedItem() >= 0:
            index = self.constants.GetFocusedItem()
            selectedName = self.constants.GetItemText(index)
            self.name.SetValue(selectedName)
            self.value.SetValue(str(self.experiment.getConstant(selectedName)))
            self.btnRemove.Enable()
        else:
            self.name.Clear()
            self.value.Clear()
            self.btnRemove.Disable()
        self.btnAdd.Disable()
        self.btnSet.Disable()

    def checkValue(self):
        """Make sure the entered value is legitimate."""
        try:
            float(self.value.GetValue())
        except (TypeError, ValueError):
            wx.MessageBox('Constant value must be a number.', 'Error',
                          wx.OK | wx.ICON_ERROR)
            return 1
        if re.match('[^a-zA-Z]', self.name.GetValue()):
            wx.MessageBox('Constant name must begin with a letter', 'Error',
                          wx.OK | wx.ICON_ERROR)
            return 1
        if re.search('[^a-zA-Z0-9]', self.name.GetValue()):
            wx.MessageBox('Constant name may not contain special characters.',
                          'Error', wx.OK | wx.ICON_ERROR)
            return 1
        return 0

    def onClose(self, event):
        """Hide the frame."""
        self.Show(False)
