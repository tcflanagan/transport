"""Classes and functions to facilitate general wx actions."""

from abc import ABCMeta, abstractmethod
import textwrap
import sys
import wx
from wx.lib.wordwrap import wordwrap as wxwrap
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin
from wx.lib.mixins.listctrl import TextEditMixin
from src.gui import images as img

_LIST_BOX_OPTS = (wx.LC_ALIGN_LEFT | wx.LC_REPORT | wx.LC_NO_HEADER |
                       wx.LC_SINGLE_SEL)

_MIN_WIDTH = 500

_BUTTON_SIZE_ADDITION = 6

# pylint: disable=W0633
#===============================================================================
#
#                                                                CUSTOM CONTROLS
#
#===============================================================================

class ListBox(wx.ListCtrl, ListCtrlAutoWidthMixin):
    """A simple, single-column list control.
    
    This class is basically a wxListBox, except that it process more events.
    
    Parameters
    ----------
    parent : wxWindow
        The panel or frame which contains this control.
    wxId : int
        The ID of the control.
    items : list of str
        The initial contents of the control.
    """
    
    def __init__(self, parent, wxId=wx.ID_ANY, items=None, 
                 style=_LIST_BOX_OPTS):
        super(ListBox, self).__init__(parent, wxId, style=style)
        ListCtrlAutoWidthMixin.__init__(self)
        if items is not None:
            self.setItems(items)
            
        self.InsertColumn(0, '')
        
    def setItems(self, items):
        """Set the items in the list.
        
        Parameters
        ----------
        items : list of str
            The strings which should make up the list.
        """
        self.DeleteAllItems()
        for index, item in enumerate(items):
            self.InsertItem(index, item)
   
    def setSelection(self, index):
        """Select an item.
        
        Parameters
        ----------
        index : int
            The index of the row to select.
        """
        self.Focus(index)
        self.Select(index)
        
    def getSelection(self):
        """Get the index of the selected item.
        
        Returns
        -------
        int
            The index of the selected item.
        """
        return self.GetFocusedItem()


class StaticListCtrl(wx.ListCtrl, ListCtrlAutoWidthMixin):
    """An auto-sizing table.
    
    Parameters
    ----------
    parent : wxWindow
        The panel or frame which contains this control.
    wxId : int
        The ID of the control.
    headers : list of str
        A list of strings to serve as the headers for the columns (the length
        of the list determines the number of columns). If `None` (the default), 
        the table will contain a single, unlabeled column.
    listFormat : int or list of int
        Flags to indicate the formatting of the columns. If the input is a
        list, each element will be applied to a different column.
    """
    
    def __init__(self, parent, wxId=wx.ID_ANY, headers=None, 
                 listFormat=wx.LIST_FORMAT_RIGHT):
        wx.ListCtrl.__init__(self, parent, wxId, 
                             style=wx.LC_REPORT|wx.BORDER_SIMPLE)
        ListCtrlAutoWidthMixin.__init__(self)
        
        if headers is None:
            self.__headers = ['']
        else:
            self.__headers = headers
        self.__widthFactor = 0.97/len(self.__headers)
        if isinstance(listFormat, list):
            self.__format = listFormat
        else:
            self.__format = [listFormat]*len(self.__headers)

        self._createColumns()
        self.InsertItem(0, '')
        
        self.Bind(wx.EVT_SIZE, self._onSize)
        
    def _createColumns(self):
        """Create the column headers."""
        for index, info in enumerate(zip(self.__headers, self.__format)):
            title, columnFormat = info
            self.InsertColumn(index+1, title, columnFormat)
        
    def setValues(self, data):
        """Set the data stored in the table.
        
        Parameters
        ----------
        data : list of tuple of str
            A list of tuples of strings. Each tuple gets a row,
            and each string goes into its own column within the row.
        """
        self.ClearAll()
        self._createColumns()
        for row in data:
            self.Append(row)

    def getData(self):
        """Get the data stored in the table.
        
        Returns
        -------
        list of tuple of str
            A list of tuples of strings. Each tuple represents a single row.
        """
        dat = []
        for row in range(self.GetItemCount()):
            currentRow = []
            for col in range(len(self.__headers)):
                currentRow.append(self.GetItem(row, col).GetText())
            dat.append(tuple(currentRow))
        return dat

    def moveRowUp(self, index):
        """Move the indexed row up one position.
        
        Parameters
        ----------
        index : int
            The index of the row to move.
        """
        if index <= 0:
            return
        movingData = self.removeRow(index)
        self.InsertItem(index-1, movingData[0])
        for columnIndex, item in enumerate(movingData[1:]):
            self.SetItem(index-1, columnIndex+1, item)
    
    def moveRowDown(self, index):
        """Move the indicated row down one position.
        
        Parameters
        ----------
        index : int
            The position of the row which should be moved down.
        """
        numItems = self.GetItemCount()
        if not 0 <= index < numItems - 1:
            return
        movingData = self.removeRow(index)
        self.InsertItem(index+1, movingData[0])
        for columnIndex, item in enumerate(movingData[1:]):
            self.SetItem(index+1, columnIndex+1, item)
                
    def addRow(self, newData):
        """Add a new item to the end of the table.
        
        Parameters
        ----------
        newData : tuple of str
            A tuple with one element for each column to be added to the end of
            the list.
            
        Returns
        -------
        int
            The number of rows after the addition has taken place.
        """
        self.Append(newData)
        return self.GetItemCount()

    def insertRow(self, index, newData):
        """Insert an item at the specified index.
        
        Parameters
        ----------
        index : int
            The position at which to insert the new row.
        newData : tuple of str
            The row data to insert into the table.
            
        Returns
        -------
        int
            The number of rows after the addition has taken place.
        """
        self.InsertItem(index, newData[0])
        for column, item in enumerate(newData[1:]):
            self.SetItem(index, column + 1, item)
        return self.GetItemCount()
        
    def removeRow(self, index):
        """Remove the selected row from the table.
        
        Parameters
        ----------
        index
            The position of the row to remove.
        
        Returns
        -------
        list of str
            The data from the row which was removed.
        """
        rowData = []
        for columnIndex in range(len(self.__headers)):
            rowData.append(self.GetItem(index, columnIndex).GetText())
        self.DeleteItem(index)
        return rowData
            
    def getRowData(self, index):
        """Get the data from one row of the table.
        
        Parameters
        ----------
        index : int
            The index of the row whose data should be returned.
            
        Returns
        -------
        list of str
            A list of strings containing the data from the specified row.
        """
        output = []
        for col in range(self.GetColumnCount()):
            output.append(self.GetItem(index, col).GetText())
        return output
        
    def _onSize(self, event):
        """On resize events, automatically adjust all column widths."""
        colwidth = event.GetSize()[0]*self.__widthFactor
        for index in range(len(self.__headers)):
            self.SetColumnWidth(index, colwidth)
        event.Skip()


class ListCtrl(StaticListCtrl, TextEditMixin):
    """An editable, auto-sizing table.
    
    Parameters
    ----------
    parent : wxWindow
        The panel or frame which contains this control.
    wxId : int
        The ID of the control.
    headers : list of str
        A list of strings to serve as the headers for the columns (the length
        of the list determines the number of columns). If `None` (the default), 
        the table will contain a single, unlabeled column.
    listFormat : int
        Flags to indicate the formatting of the columns.
    """
    
    def __init__(self, parent, wxId=wx.ID_ANY, headers=None, 
                 listFormat=wx.LIST_FORMAT_RIGHT):
        StaticListCtrl.__init__(self, parent, wxId, headers, listFormat)
        TextEditMixin.__init__(self)


class KeyValListCtrl(StaticListCtrl):
    """A list control for managing typed key-value pairs.
     
    Parameters
    ----------
    parent : wxWindow
        The panel or frame which contains this control.
    """
     
    def __init__(self, parent):
        StaticListCtrl.__init__(self, parent, wx.ID_ANY, 
                                headers=['Name', 'Default value', 'Type'],
                                style=wx.LIST_FORMAT_LEFT)        


#===============================================================================
# 
#                                                           ABSTRACT BASE DIALOG
#
#===============================================================================

#class BaseDialog(wx.Dialog, metaclass=ABCMeta):
class BaseDialog(wx.Dialog):
    """A base class to be extended by dialogs.
    
    Note: it is important to call this class's `finish` method after all
    components have been added.
    
    Parameters
    ----------
    parent : wxWindow
        The panel or frame which spawns this dialog.
    wxId : int
        The wxPython identification number for this dialog.
    title : str
        The title to display in the dialog's title bar.
    info : tuple of str
        A tuple of strings. The first is the title of the info bar, and the
        second is the text of the info bar. The info bar will not be displayed
        if `infoBar` is `None`.
    """
    
    def __init__(self, parent, wxId=wx.ID_ANY, title='Dialog', info=None,
                 minWidth=None):
        super(BaseDialog, self).__init__(parent, wxId)
        self.SetTitle(title)
        self._info = info
        if minWidth is None:
            self.minWidth = _MIN_WIDTH
        else:
            self.minWidth = minWidth
        
        self.__sizer = wx.BoxSizer(wx.VERTICAL)
        if self._info is not None:
            self.__infoBar = wx.StaticText(self)
            self.__sizer.Add(self.__infoBar, 0, wx.EXPAND|wx.ALL, 5)
            self.__sizer.Add(wx.StaticLine(self), 0, wx.EXPAND|wx.ALL, 5)
        
            
        
    def setPanel(self, panel, proportion=1, flags=wx.EXPAND|wx.ALL, border=5):
        """Finish laying out the panel."""
        self.__sizer.Add(panel, proportion, flags, border)
        
        buttonpanel = wx.Panel(self, wx.ID_ANY)
        buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonpanel.SetSizer(buttonsizer)
        
        okButton = wx.Button(buttonpanel, wx.ID_OK, 'OK')
        cancelButton = wx.Button(buttonpanel, wx.ID_CANCEL, 'Cancel')
        buttonsizer.Add(cancelButton, 0, wx.ALL, 2)
        buttonsizer.Add(okButton, 0, wx.ALL, 2)
        
        okButton.Bind(wx.EVT_BUTTON, self._onClose)
        cancelButton.Bind(wx.EVT_BUTTON, self._onClose)
        self.Bind(wx.EVT_CLOSE, self._onClose)
        
        self.__sizer.Add(buttonpanel, 0, wx.ALL|wx.ALIGN_RIGHT, 4)
        
        self.SetSizeHints(self.minWidth, -1)
        self.SetSizer(self.__sizer)
        self.Layout()
        self.Fit()
        if self._info is not None:
            newText = wxwrap(self._info[1], self.GetSize()[0]-5, 
                             wx.ClientDC(self.__infoBar), True)
            self.__infoBar.SetLabel(newText)
            self.Fit()
    
    @abstractmethod
    def update(self):
        """Update whatever objects this dialog is supposed to modify.
        
        Returns
        -------
        bool
            Whether the attempt to update the appropriate objects was
            successful.
        """
        return True
    
    def _onClose(self, event):
        """Update objects, and, if successful, close the dialog."""
        result = event.GetId()
        if result == wx.ID_OK:
            if self.update():
                self.EndModal(result)
                self.Destroy()
        else:
            self.EndModal(result)
            self.Destroy()
        
# class InfoBar(wx.Panel):
#     """A bar for displaying information about the purpose of the dialog.
#     
#     Parameters
#     ----------
#     parent : wxWindow
#         The panel or frame which contains this bar.
#     title : str
#         The title of the information bar.
#     string : str
#         The information string to display.
#     icon : wxIcon
#         The icon to display to the left of the string.
#     """
#     
#     leftBorder = 20
#     rightBorder = 30
# 
#     def __init__(self, parent, title, string, minWidth=None):
#         super(InfoBar, self).__init__(parent, wx.ID_ANY)
#         titleFont = wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_ITALIC,
#                             wx.FONTWEIGHT_BOLD)
#         infoFont = wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
#                            wx.FONTWEIGHT_NORMAL)
#         self.info = string
#         if minWidth is None:
#             self.minWidth = _MIN_WIDTH
#         else:
#             self.minWidth = minWidth
#         self.SetSizeHints(self.minWidth-5, -1, self.minWidth-5, -1)
#         
#         self.SetBackgroundColour(wx.WHITE)
#         
#         sizer = wx.BoxSizer(wx.HORIZONTAL)
#                 
#         rightpanel = wx.Panel(self, wx.ID_ANY)
#         rightsizer = wx.BoxSizer(wx.VERTICAL)
#         rightpanel.SetSizer(rightsizer)
#         rightpanel.SetBackgroundColour(wx.WHITE)
#         
#         titleText = wx.StaticText(rightpanel, wx.ID_ANY, label=title)
#         titleText.SetFont(titleFont)
#         
#         self.infopanel = wx.Panel(rightpanel, wx.ID_ANY)
#         infosizer = wx.BoxSizer(wx.HORIZONTAL)
#         self.infopanel.SetSizer(infosizer)
#         self.infopanel.SetBackgroundColour(wx.WHITE)
#         
#         self.infoText = StaticWrapText(self.infopanel, label=string)
#         infosizer.AddSpacer(10)
#         infosizer.Add(self.infoText, 1, wx.EXPAND|wx.ALL, 5)
# 
#         self.infoText.setFont(infoFont)
#         
#         rightsizer.AddSpacer(5)
#         rightsizer.Add(titleText, 0, wx.EXPAND|wx.LEFT, 5)
#         rightsizer.AddSpacer(5)
#         rightsizer.Add(self.infopanel, 0, wx.EXPAND|wx.LEFT, InfoBar.leftBorder)
#         rightsizer.AddSpacer(5)
#         
#         sizer.Add(rightpanel, 1, wx.EXPAND)
#         
#         self.SetSizer(sizer)
#         sizer.Fit(self)
# 
# class StaticWrapText(wx.PyControl):
#     """An auto-word-wrapping text label."""
#     
#     def __init__(self, parent, wxId=wx.ID_ANY, label='', pos=wx.DefaultPosition,
#                  size=wx.DefaultSize, style=wx.NO_BORDER):
#         super(StaticWrapText, self).__init__(parent, wxId, pos, size, style)
#         self.statictext = wx.StaticText(self, wx.ID_ANY, label, style=style)
#         self.wraplabel = label
#         self.SetBackgroundColour(wx.WHITE)
#         
#     def wrap(self):
#         """Wrap the label text based on the size of the control."""
#         self.Freeze()
#         self.statictext.SetLabel(self.wraplabel)
#         self.statictext.Wrap(self.GetSize().width)
#         self.Thaw()
#     
#     # pylint: disable=W0221
#     def DoGetBestSize(self):
#         """Get the best size."""
#         self.wrap()
#         self.SetSize(self.statictext.GetSize())
#         return self.GetSize()
#     # pylint: enable=W0221
# 
#     def setFont(self, newFont):
#         """Set the font of the label."""
#         self.statictext.SetFont(newFont)
        

#===============================================================================
# 
#                                                                 SPECIAL PANELS
#
#===============================================================================


# General-purpose panel --------------------------------------------------------

class Panel(wx.Panel):
    """A panel subclass which builds in sizer support.
    
    Parameter
    ---------
    parent : wxWindow
        The panel or frame which contains this panel.
    sizerType : str
        The type of the sizer for the panel. It may be 'vertical' (the default)
        or 'horizontal', in which case a wxBoxSizer will be used, or 'flex_grid'
        or 'grid'.
    label : str
        The string to go in the panel's static box frame. If `None`, no
        static box will be displayed.
    """
    
    labelOptions = wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.ALL
    
    def __init__(self, parent, sizerType='vertical', label=None, 
                 *args, **kwargs):
        """Create a new panel."""
        super(Panel, self).__init__(parent, wx.ID_ANY)       
        
        if 'extraBorder' in kwargs:
            extraBorder = kwargs.pop('extraBorder')
        else:
            extraBorder = 0
        if 'panelStyle' in kwargs:
            panelStyle = kwargs.pop('panelStyle')
        else:
            panelStyle = 0
        if 'scrolling' in kwargs:
            scrolling = kwargs.pop('scrolling')
            self.panel = wx.ScrolledWindow(self, wx.ID_ANY, style=panelStyle)
            if scrolling:
                self.panel.SetScrollbars(1, 1, 1, 1)
        else:
            self.panel = wx.Panel(self, wx.ID_ANY, style=panelStyle)
            
        self.sizer = self.__setSizer(sizerType, *args, **kwargs)
        
        if label is None:
            mainsizer = wx.BoxSizer(wx.VERTICAL)
            mainsizer.Add(self.panel, 1, wx.EXPAND | wx.ALL, extraBorder)
            self.SetSizer(mainsizer)
        else:
            self.staticpanel = wx.StaticBox(self, wx.ID_ANY, label)
            staticsizer = wx.StaticBoxSizer(self.staticpanel, wx.VERTICAL)
            staticsizer.Add(self.panel, 1, wx.EXPAND | wx.ALL, extraBorder)
            self.SetSizer(staticsizer)
    
    def __setSizer(self, sizerType, *args, **kwargs):
        """Create the appropriate sizer
        
        Parameters
        ----------
        sizerType : str
            The type of the sizer for the panel. It may be 'vertical' (the 
            default) or 'horizontal', in which case a wxBoxSizer will be used, 
            or 'flex_grid' or 'grid', which are self-explanatory.
        """
        if sizerType == 'horizontal':
            sizer = wx.BoxSizer(wx.HORIZONTAL, *args, **kwargs)
        elif sizerType == 'flex_grid':
            sizer = wx.FlexGridSizer(*args, **kwargs)
        elif sizerType == 'grid':
            sizer = wx.GridSizer(*args, **kwargs)
        else:
            sizer = wx.BoxSizer(wx.VERTICAL, *args, **kwargs)
        self.panel.SetSizer(sizer)
        return sizer
        
    def setLabel(self, newLabel):
        """Set the label for the border.
        
        Parameters
        ----------
        newLabel : str
            The new label for the panel's border.
        """
        try:
            self.staticpanel.SetLabel(newLabel)
        except AttributeError:
            pass
        
    def add(self, item, *args, **kwargs):
        """Add an item to the panel's sizer.
        
        All extra arguments are passed to the `sizer.Add` method.
        
        Parameters
        ----------
        item : wxWindow
            The control to add to the panel.
        """
        item.Reparent(self.panel)
        self.sizer.Add(item, *args, **kwargs)
        
    def addLabel(self, text, border=3, flag=None):
        """Add a text label to the control using default options.
        
        Parameters
        ----------
        text : str
            The text of the label to add.
        border : int
            The width in pixels of the border which will surround the new
            text label.
            
        Returns
        -------
        wxStaticText
            The added text label.
        """
        if flag is None:
            flag = Panel.labelOptions
        staticText = wx.StaticText(self.panel, wx.ID_ANY, label=text)
        self.sizer.Add(staticText, 0, flag, border)
        return staticText
    
    def addLabeledText(self, label, initialValue=None, border=0, style=0,
                       defocusHandler=None):
        """Add a label and a text control.
        
        Parameters
        ----------
        label : str
            The text to label the text control.
        initialValue : str
            The initial value of the text control.
        border : int
            The width in pixels of the border which will surround both the
            new label and the new text control.
        style : int
            The style (in terms of `wx` constants) of the text control.
        defocusHandler : method
            The method to execute when the text control loses focus.
            
        Returns
        -------
        wxTextCtrl
            The text control which has been created and added to the panel.
        """
        staticText = wx.StaticText(self.panel, wx.ID_ANY, label)
        textCtrl = wx.TextCtrl(self.panel, wx.ID_ANY, initialValue,
                               style=style)
        if defocusHandler is not None:
            textCtrl.Bind(wx.EVT_KILL_FOCUS, defocusHandler)
        self.sizer.Add(staticText, 0, Panel.labelOptions, border)
        self.sizer.Add(textCtrl, 1, wx.EXPAND | wx.ALL, border)
        
        return textCtrl
    
    def addLabeledComboBox(self, label, initialValue='', choices=None, border=0,
                           style=0, defocusHandler=None, valueHandler=None,
                           proportion=1):
        """Add a label and a text control.
        
        Parameters
        ----------
        label : str
            The text to label the combo box.
        initialValue : str
            The initial value of the combo box.
        choices : list of str
            The accepted values for the combo box.
        border : int
            The width in pixels of the border which will surround both the
            new label and the new combo box.
        style : int
            The style (in terms of `wx` constants) of the combo box.
        defocusHandler : method
            The method to execute when the combo box loses focus.
        valueHandler : method
            The method to execute when the selection of the combo box changes.
        proportion : int
            The weighting factor for sizing the combo box.
        """
        if choices is None:
            choices = []
        staticText = wx.StaticText(self.panel, wx.ID_ANY, label)
        comboBox = wx.ComboBox(self.panel, wx.ID_ANY, initialValue, 
                               choices=choices, style=style)
        if defocusHandler is not None:
            comboBox.Bind(wx.EVT_KILL_FOCUS, defocusHandler)
        if valueHandler is not None:
            comboBox.Bind(wx.EVT_COMBOBOX, valueHandler)
        self.add(staticText, 0, Panel.labelOptions, border)
        self.add(comboBox, proportion, wx.EXPAND | wx.ALL, border)
        
        return comboBox
    
    def addLabeledMultiCtrl(self, label, initialValue=None, allowed=None,
                            border=0, style=0, defocusHandler=None):
        """Add a label and text controls to the panel.
        
        The number of controls to be added will be determined by
        `initialValue`. There will be one item for each value of `initialValue`,
        If the value of `allowed` at the same position as a value of
        `initialValue` is a list, the created control will be a `wxComboBox`
        with the listed choices available.
        
        Parameters
        ----------
        label : str
            The text to label the text control.
        initialValue : list of str 
            The initial values of the text controls.
        allowed : list of list of str
            A list of lists of strings. Each element in the outer list
            corresponds to a single control. The strings in the inner
            list correspond to the allowed values for the control. If
            any element of the outer list is `None`, that list item will
            create a `wxTextCtrl` instead of a `wxComboBox`. 
        border : int
            The width in pixels of the border which will surround both the
            new label and the new text control.
        style : int
            The style (in terms of `wx` constants) of the text control.
        defocusHandler : method or list of method
            The method to execute when the text control loses focus. If it is
            a list, the handlers will be applied sequentially to the controls
            created for each element in `initialValue`. If it is a single
            method, the same method will be bound to all controls.
            
        Returns
        -------
        list of (wxTextCtrl or wxComboBox)
            The list of text controls and combo box controls which have been 
            created and added to the panel.
        """
        staticText = wx.StaticText(self.panel, wx.ID_ANY, label)
        if not isinstance(defocusHandler, list):
            defocusHandler = [defocusHandler]*len(initialValue)
        if not isinstance(allowed, list):
            allowed = [allowed]*len(initialValue)
        
        self.sizer.Add(staticText, 0, Panel.labelOptions, border)
        ctrls = []
        for initial, handler, choices in zip(initialValue, defocusHandler,
                                             allowed):
            if choices is not None:
                ctrl = wx.ComboBox(self.panel, wx.ID_ANY, initial, 
                                   choices=choices, style=style)
            else:
                ctrl = wx.TextCtrl(self.panel, wx.ID_ANY, initial,
                                   style=style)
            ctrls.append(ctrl)
            if handler is not None:
                ctrl.Bind(wx.EVT_KILL_FOCUS, handler)
            self.sizer.Add(ctrl, 1, wx.EXPAND | wx.ALL, border)
        return ctrls
    
    def addSettingRow(self, label, initialValue=None, allowed=None,
                      border=0, style=0, buttonHandler=None):
        """Add a row consisting of a label, indicator, control, and set button.
        
        Add a row to a four-column table. The first element in the row is a
        label specifying the value controlled. The second is a read-only 
        wxTextCtrl specifying the last-read value of the parameter, the third
        is a writable wxTextCtrl (if `allowed` is `None`) or wxComboBox (if
        `allowed` is a `list`), and the fourth is a check-mark button.
        """ 
    
    def addButton(self, label, wxId=wx.ID_ANY, border=3, handler=None): 
        """Create a new button and add it to the panel.
        
        Parameters
        ----------
        label : str
            The text which should go on the button.
        wxId : int
            The ID for the button.
        border : int
            The size in pixels of the border to go around the button.
        handler : method
            The method to execute when the button is clicked.
            
        Returns
        -------
        wxButton
            The button created by this method.
        """
        button = wx.Button(self.panel, wxId, label)
        self.sizer.Add(button, 0, wx.ALL, border)
        if handler is not None:
            button.Bind(wx.EVT_BUTTON, handler)
        return button
    
    def addGrowableColumn(self, index, proportion=1):
        """Make a column growable in a flexible sizer.
        
        Parameters
        ----------
        index : int
            The index of the column to allow to expand.
        proportion : int
            The weighting factor for expansion.
        """
        try:
            function = getattr(self.sizer, 'AddGrowableCol')
            function(index, proportion)
        except AttributeError:
            pass
        
    def addStretchSpacer(self, proportion):
        """Add a stretchable spacer to the panel.
        
        Parameters
        ----------
        proportion : int
            The weighting factor for expansion.
        """
        self.sizer.AddStretchSpacer(proportion)


#-------------------------------------------------------------------- Form panel

FP_USE_CONTROLS = 1
FP_USE_INDICATORS = 2
FP_USE_BUTTONS = 4

class FormPanel(wx.Panel):
    """A panel subclass for easily creating framed forms.
    
    Parameter
    ---------
    parent : wxWindow
        The panel or frame which contains this panel.
    label : str
        The string to go in the panel's static box frame. If `None`, no
        static box will be displayed.
    """
    
    labelOptions = wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.ALL
    
    def __init__(self, parent, label='Information', hgap=5, vgap=5, 
                 style=FP_USE_CONTROLS|FP_USE_INDICATORS|FP_USE_BUTTONS,
                 *args, **kwargs):
        """Create a new panel."""
        super(FormPanel, self).__init__(parent, wx.ID_ANY)       
        
        if 'extraBorder' in kwargs:
            extraBorder = kwargs.pop('extraBorder')
        else:
            extraBorder = 0
        if 'scrolling' in kwargs:
            scrolling = kwargs.pop('scrolling')
            self.panel = wx.ScrolledWindow(self, wx.ID_ANY)
            if scrolling:
                self.panel.SetScrollbars(1, 1, 1, 1)
        else:
            self.panel = wx.Panel(self, wx.ID_ANY)
        
        useIndicators = bool(style & FP_USE_INDICATORS)
        useControls = bool(style & FP_USE_CONTROLS)
        useButtons = bool(style & FP_USE_BUTTONS)
        cols = 1 + useIndicators + useControls + useButtons
        self.sizer = wx.FlexGridSizer(cols=cols, hgap=hgap, vgap=vgap)
        self.panel.SetSizer(self.sizer)
        if useIndicators and useControls:
            self.sizer.AddGrowableCol(1, 1)
            self.sizer.AddGrowableCol(2, 1)
        elif useIndicators or useControls:
            self.sizer.AddGrowableCol(1, 1)
        
        self.staticpanel = wx.StaticBox(self, wx.ID_ANY, label)
        staticsizer = wx.StaticBoxSizer(self.staticpanel, wx.VERTICAL)
        staticsizer.Add(self.panel, 1, wx.EXPAND | wx.ALL, extraBorder)
        self.SetSizer(staticsizer)
        
        self.addRow = getattr(self, '_addRow%d' % style)
        
    def setLabel(self, newLabel):
        """Set the label for the border.
        
        Parameters
        ----------
        newLabel : str
            The new label for the panel's border.
        """
        try:
            self.staticpanel.SetLabel(newLabel)
        except AttributeError:
            pass
    
    def _addRow1(self, label, conValue='', conFormat=None, allowed=None,):
        """Add a row."""
        statictext = wx.StaticText(self.panel, wx.ID_ANY, label)
        self.sizer.Add(statictext, 0, self.labelOptions)
        
        control = self.__addControl(conValue, conFormat, allowed)
        
        return (control, )
    
    def _addRow2(self, label, indValue='', indFormat=None):
        """Add a row."""
        statictext = wx.StaticText(self.panel, wx.ID_ANY, label)
        self.sizer.Add(statictext, 0, self.labelOptions)
        
        indicator = self.__addIndicator(indValue, indFormat)
        
        return (indicator, )
    
    def _addRow3(self, label, 
                indValue='', indFormat=None,
                conValue='', conFormat=None, allowed=None):
        """Add a row."""
        statictext = wx.StaticText(self.panel, wx.ID_ANY, label)
        self.sizer.Add(statictext, 0, self.labelOptions)
        
        indicator = self.__addIndicator(indValue, indFormat)
        control = self.__addControl(conValue, conFormat, allowed)
        
        return (indicator, control)
    
    def _addRow4(self, label, btnInclude=True, handler=None):
        """Add a row."""
        statictext = wx.StaticText(self.panel, wx.ID_ANY, label)
        self.sizer.Add(statictext, 0, self.labelOptions)
        
        button = self.__addButton(btnInclude, handler)
        
        return (button, )   
    
    def _addRow5(self, label,
                conValue='', conFormat=None, allowed=None,
                btnInclude=True, handler=None):
        """Add a row."""
        statictext = wx.StaticText(self.panel, wx.ID_ANY, label)
        self.sizer.Add(statictext, 0, self.labelOptions)
        
        control = self.__addControl(conValue, conFormat, allowed)
        button = self.__addButton(btnInclude, handler)
        
        return (control, button)
    
    def _addRow6(self, label, 
                indValue='', indFormat=None,
                btnInclude=True, handler=None):
        """Add a row."""
        statictext = wx.StaticText(self.panel, wx.ID_ANY, label)
        self.sizer.Add(statictext, 0, self.labelOptions)
        
        indicator = self.__addIndicator(indValue, indFormat)
        button = self.__addButton(btnInclude, handler)
        
        return (indicator, button)   
       
    def _addRow7(self, label, 
                indValue='', indFormat=None,
                conValue='', conFormat=None, allowed=None,
                btnInclude=True, handler=None):
        """Add a row."""
        statictext = wx.StaticText(self.panel, wx.ID_ANY, label)
        self.sizer.Add(statictext, 0, self.labelOptions)
        
        indicator = self.__addIndicator(indValue, indFormat)
        control = self.__addControl(conValue, conFormat, allowed)
        button = self.__addButton(btnInclude, handler)
        
        return (indicator, control, button)
        
    def __addIndicator(self, indValue='', indFormat=None):
        if indValue is None:
            self.sizer.AddSpacer((0, 0))
            indicator = None
        elif indFormat is None:
            indicator = wx.TextCtrl(self.panel, wx.ID_ANY, indValue)
            self.sizer.Add(indicator, 1, wx.EXPAND)
        else:
            fmtFunc, fmtStr = indFormat
            indicator = MaskedText(self.panel, wx.ID_ANY, indValue,
                                   fmtFunc, fmtStr, True)
            self.sizer.Add(indicator, 1, wx.EXPAND)
        return indicator
    
    def __addControl(self, conValue='', conFormat=None, allowed=None):
        if conValue is None:
            self.sizer.AddSpacer((0, 0))
            control = None
        elif conFormat is None and allowed is None:
            control = wx.TextCtrl(self.panel, wx.ID_ANY, conValue)
            self.sizer.Add(control, 1, wx.EXPAND)
        elif conFormat is None and allowed is not None:
            control = wx.ComboBox(self.panel, wx.ID_ANY, conValue,
                                  choices=allowed, style=wx.CB_READONLY)
            self.sizer.Add(control, 1, wx.EXPAND)
        elif conFormat is not None: 
            fmtFunc, fmtStr = conFormat
            if allowed is None:
                myMin, myMax = (None, None)
            else:
                myMin, myMax = allowed
            control = MaskedText(self.panel, wx.ID_ANY, conValue,
                                 fmtFunc, fmtStr, False, myMin, myMax)
            self.sizer.Add(control, 1, wx.EXPAND)
        return control
    
    def __addButton(self, btnInclude=True, handler=None):
        if btnInclude:
            bmp = img.getOkBitmap()
            buttonSize = [x + _BUTTON_SIZE_ADDITION for x in bmp.GetSize()]
            button = wx.BitmapButton(self.panel, wx.ID_ANY, bmp, 
                                     size=buttonSize)
            self.sizer.Add(button, 0)
            if handler is not None:
                button.Bind(wx.EVT_BUTTON, handler)
        else:
            button = None
            self.sizer.AddSpacer((0, 0))
        return button
        

        
class MaskedText (wx.TextCtrl):
    def __init__(self, parent, wxId, value=0.0, coerceFunc=float, fmt='%.6e', 
                 readonly=False, minVal=None, maxVal=None):
        if readonly:
            style = wx.TE_RIGHT|wx.TE_READONLY
        else:
            style = wx.TE_RIGHT
        super(MaskedText, self).__init__(parent, wxId, value, style=style)

        self.__min = minVal
        self.__max = maxVal
        self.__coerce = coerceFunc
        self.__fmt = fmt
        self.__lastVal = value
        
        self.Bind(wx.EVT_KILL_FOCUS, self.__onLoseFocus)
        self.Bind(wx.EVT_SET_FOCUS, self.__onGainFocus)
        
    def fixValue(self):
        """Apply the appropriate formatting to the value."""
        value = self.GetValue()
        try:
            value = self.__coerce(value)
        except ValueError:
            self.SetValue(self.__lastVal)
            return
        if self.__min is not None and value < self.__min:
            self.SetValue(self.__lastVal)
            return
        if self.__max is not None and value > self.__max:
            self.SetValue(self.__lastVal)
            return
        self.SetValue(self.__fmt % value)
    
    def __onGainFocus(self, event):
        """Record the current value when the control gains focus."""
        self.__lastVal = self.GetValue()
        event.Skip()
        
    def __onLoseFocus(self, event):
        """Fix the formatting when the control loses focus."""
        event.GetEventObject().fixValue()
        event.Skip()
        
    @staticmethod
    def intfloat(value):
        """Return an integer from a float string.
        
        Parameters
        ----------
        value : str
            A string representing a floating-point number.
            
        Returns
        -------
        int
            An integer resulting from first casting the input string to a float
            and then to an integer.
        """
        return int(float(value))
    
# Scan configuration panel -----------------------------------------------------

class ScanPanel(wx.Panel):
    """A scan panel with extra options.
    
    Parameters
    ----------
    parent : wxWindow
        The panel or frame which contains this panel.
    wxId : int
        The ID of this panel.
    initialData : list of tuple of float
        The data the table should contain initially. Each tuple is one row
        and should be of the form (initial point, final point, step size),
        where all are in the same units.
    formatString : str
        The string used to format the floats into appropriate strings.
    buttonIcons : bool
        Whether to use icons for the editing buttons. If `False`, text will
        be used instead.
    label : str
        The label to surround the panel. If `None`, the panel will not have
        either a label or a border.
    """
    
    def __init__(self, parent, wxId=wx.ID_ANY, initialData=None, 
                 formatString='%.3f', buttonIcons=True, label=None):
        
        super(ScanPanel, self).__init__(parent, wxId)
        
        self.__formatString = formatString
        
        if label is not None:
            staticbox = wx.StaticBox(self, wx.ID_ANY, label)
            mainsizer = wx.StaticBoxSizer(staticbox, wx.HORIZONTAL)
        else:
            mainsizer = wx.BoxSizer(wx.HORIZONTAL)
        
        
        listpanel = wx.Panel(self, wx.ID_ANY)
        listsizer = wx.BoxSizer(wx.VERTICAL)
        listpanel.SetSizer(listsizer)
        
        self.__list = ListCtrl(listpanel, wx.ID_ANY,
                               headers=('Initial', 'Final', 'Step'))
        listsizer.Add(self.__list, 1, wx.EXPAND|wx.ALL)
        if initialData is not None:
            self.setData(initialData)
            
        navpanel = wx.Panel(self, wx.ID_ANY)
        navsizer = wx.BoxSizer(wx.VERTICAL)
        navpanel.SetSizer(navsizer)
        
        if buttonIcons:
            self.navUp = createButton(navpanel, navsizer, wx.ID_ANY,
                                      img.getScanUpBitmap(),
                                      tooltip='Move up', 
                                      handler=self.onMoveUp)
            self.navDown = createButton(navpanel, navsizer, wx.ID_ANY,
                                        img.getScanDownBitmap(), 
                                        tooltip='Move down', 
                                        handler=self.onMoveDown)
            self.navAdd = createButton(navpanel, navsizer, wx.ID_ANY,
                                       img.getScanAddBitmap(), 
                                       tooltip='Add item', 
                                       handler=self.onAdd)
            self.navInsert = createButton(navpanel, navsizer, wx.ID_ANY,
                                          img.getScanInsertBitmap(), 
                                          tooltip='Insert item', 
                                          handler=self.onInsert)
            self.navRemove = createButton(navpanel, navsizer, wx.ID_ANY,
                                          img.getScanRemoveBitmap(), 
                                          tooltip='Remove item', 
                                          handler=self.onRemove)
        else:
            self.navUp = createButton(navpanel, navsizer, wx.ID_ANY, 
                                      label='Up',
                                      tooltip='Move up', 
                                      handler=self.onMoveUp)
            self.navDown = createButton(navpanel, navsizer, wx.ID_ANY,
                                        label='Down',
                                        tooltip='Move down', 
                                        handler=self.onMoveDown)
            self.navAdd = createButton(navpanel, navsizer, wx.ID_ANY, 
                                       label='Add',
                                       tooltip='Add item', 
                                       handler=self.onAdd)
            self.navInsert = createButton(navpanel, navsizer, wx.ID_ANY, 
                                          label='Insert',
                                          tooltip='Insert item', 
                                          handler=self.onInsert)
            self.navRemove = createButton(navpanel, navsizer, wx.ID_ANY, 
                                          label='Remove',
                                          tooltip='Remove item', 
                                          handler=self.onRemove)
        
        mainsizer.Add(listpanel, 1, wx.ALL|wx.EXPAND, 3)
        mainsizer.Add(navpanel, 0, wx.ALL, 3)
        
        if self.__formatString is not None and self.__formatString != '%s':
            self.__list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._verifyData)
        
        self.SetSizerAndFit(mainsizer)
            
    def onMoveUp(self, event):
        """Move the currently selected item up."""
        cpos = self.__list.GetFocusedItem()
        if cpos <= 0:
            return
        self.__list.Select(cpos, False)
        self.__list.moveRowUp(cpos)
        self.__list.Select(cpos - 1)
        self.__list.Focus(cpos - 1)
    
    def onMoveDown(self, event):
        """Move the selected item down."""
        cpos = self.__list.GetFocusedItem()
        if not 0 <= cpos < self.__list.GetItemCount() - 1:
            return
        self.__list.Select(cpos, False)
        self.__list.moveRowDown(cpos)
        self.__list.Select(cpos + 1)
        self.__list.Focus(cpos + 1)
        
    def onAdd(self, event):
        """Add a new item."""
        self.__list.Select(self.__list.GetFocusedItem(), False)
        numItems = self.__list.GetItemCount()
        if numItems > 0:
            previousData = self.getRowData(numItems-1)
        else:
            tempData = []
            for _ in range(self.__list.GetColumnCount()):
                tempData.append(0)
            previousData = (0, 0, 0)
        newData = list(previousData)
        newData[0] = previousData[1]
        newData[1] = 0
        self.__list.addRow(self._formatData([newData])[0])
        self.__list.Select(numItems)
        self.__list.Focus(numItems)

    def onInsert(self, event):
        """Insert an item at the current position"""
        cpos = self.__list.GetFocusedItem()
        self.__list.Select(cpos, False)
        if cpos > 0:
            previousData = self.getRowData(cpos-1)
        else:
            previousData = (0, 0, 0)
        newData = list(previousData)
        newData[0] = previousData[1]
        newData[1] = 0
        self.__list.insertRow(cpos, self._formatData([newData])[0])
        self.__list.Focus(cpos)
        self.__list.Select(cpos)
        
    def onRemove(self, event):
        """Remove the selected item."""
        cpos = self.__list.GetFocusedItem()
        if cpos >= 0:
            self.__list.Select(cpos, False)
            self.__list.removeRow(cpos)
            if self.__list.GetItemCount() > 0:
                self.__list.Select(0, True)
            
    def getRowData(self, index):
        """Get the data from one row of the table.
        
        Parameters
        ----------
        index : int
            The index of the row whose data should be returned.
            
        Returns
        -------
        list of str
            A list of strings containing the data from the specified row.
        """
        data = self.__list.getRowData(index)
        return self._formatData([data])[0]

        
    def _formatData(self, data):
        """Format the data using the format string.
        
        Parameters
        ----------
        data : list of tuple
            The data to go into the table. Each tuple represents a single
            row. The data type of the elements may be `str`, `int`, or `float`,
            but it must be castable to `float`.
            
        Returns
        -------
        list of tuple of str
            The same data as was entered, but formatted according to the
            specified format string.
        """
        if self.__formatString is not None and self.__formatString != '%s':
            formattedData = []
            for row in data:
                currentRow = []
                for col in row:
                    try: 
                        newValue = self.__formatString % float(col) 
                    except (ValueError, TypeError):
                        newValue = self.__formatString % 0.0
                    currentRow.append(newValue)
                formattedData.append(tuple(currentRow))
            return formattedData
        return data
    
    def formatData(self):
        """Format the data in the control using the format string."""
        self.setData(self.getData())
        
        
    def setData(self, data, formatData=True):
        """Set the data values in the table control.
        
        Parameters
        ----------
        data : list of tuple
            A list of tuples, where each tuple contains the data for one row.
            The data type of the elements in the tuples can be `str`, `int`, or
            `float`, as long as it can be cast to `float`.
        formatData : bool
            Whether to format the data before passing it to the table control.
        """
        if formatData:
            data = self._formatData(data)
        self.__list.setValues(data)
        
    def getData(self, formatData=False):
        """Get the data values from the table control.
        
        Parameters
        ----------
        formatData : bool
            Whether to format the data before returning it from the table.

        Returns
        -------
        list of tuple of str
            The data from the list control. Each tuple represents one row.
        """
        if formatData:
            return self._formatData(self.__list.getData())
        return self.__list.getData()
    
    def _verifyData(self, event):
        """Make sure all inputs are floats."""
        self.formatData()
        self.Layout()


#===============================================================================
# 
# MULTIPURPOSE CONTROL CONSTRUCTORS
#
#===============================================================================

def createButton(parent, sizer, wxId=wx.ID_ANY, icon=None, label='', 
                 tooltip=None, border=2, handler=None):
    """Create a new button.
    
    Parameters
    ----------
    parent : wxWindow
        The button's parent frame or panel.
    sizer : wxSizer
        The sizer to which the button should be added.
    wxId : int
        The ID number of the control (default: wx.ID_ANY).
    icon : wxBitmap
        A bitmap object to use as the icon for the button (default: `None`). If
        `None`, the label will be used instead of an icon.
    label : str
        The label for the button. If `icon` is provided, then `label` will be
        ignored.
    tooltip : str
        The tooltip to display when the user hovers over the button.
    border : int
        The amount of space in pixels to display around all sides of the button.
    handler : method
        The method which will be invoked when the user clicks on the button.
        
    Returns
    -------
    wxButton
        The newly created button.
    """
    if icon is not None:
        button = wx.BitmapButton(parent, wxId, icon)
    else:
        button = wx.Button(parent, wxId, label)
    
    if tooltip is not None:
        button.SetToolTip(tooltip)
    
    sizer.Add(button, 0, wx.ALL, border)
    
    if handler is not None:
        button.Bind(wx.EVT_BUTTON, handler)
    
    return button

def createMenuItem(parent, menu, wxId, label, tooltip=None, handler=None, 
                   pos=None):
    """Create a new menu item and add it to the appropriate menu.
    
    Parameters
    ----------
    parent : wxWindow
        The frame or control which contains the appropriate menu bar.
    menu : wxMenu
        The menu to which the item should be added.
    wxId : int
        The ID of the menu item.
    label : str
        The text which should label the item.
    tooltip : str
        The text which should go in the tooltip and/or the status bar
        when the item is highlighted.
    handler : method
        The method which should respond to clicks on the item.
    pos : int
        The position before which the item should be inserted. If `None` (the
        default), the item will be appended to the end.
        
    Returns
    -------
    wxMenuItem
        The newly created menu item.
    """
    if pos is None:
        if tooltip is not None:
            newButton = menu.Append(wxId, label, tooltip)
        else:
            newButton = menu.Append(wxId, label)
    else:
        if tooltip is not None:
            newButton = menu.Insert(pos, wxId, label, tooltip)
        else:
            newButton = menu.Insert(pos, wxId, label)
        
    if handler is not None:
        parent.Bind(wx.EVT_MENU, handler, newButton)
    return newButton
    
def createMenu(parent, menuBar, menuTitle, menuItems):
    """Create a new menu and populate it.
    
    Parameters
    ----------
    parent : wxWindow
        The frame or control which contains the appropriate menu bar.
    menuBar : wxMenuBar
        The menu bar which should contain the new menu.
    menuTitle : str
        The title of the menu.
    menuItems : list of tuple
        A list of tuples, where each tuple describes one item for the menu.
        The tuples should contain, in order, wxId, label, tooltip, and
        handler. For the meanings, see `createMenuItem`. If an element in
        the list is `None`, a separator will be appended at that point.
        
    Returns
    -------
    list of wxMenuItem
        The menu item objects which constitute the menu.
    """
    newMenu = wx.Menu()
    itemsOut = []
    for item in menuItems:
        if item is None:
            newMenu.AppendSeparator()
        else:
            itemsOut.append(createMenuItem(parent, newMenu, *item))
    menuBar.Append(newMenu, menuTitle)
    return itemsOut

def createLabeledTextControl(parent, sizer, wxId=wx.ID_ANY, label='Input:', 
                             initialValue='', border=0, style=0,
                             defocusHandler=None):
    """Create a label and a text control and add them to the sizer.
    
    Parameters
    ----------
    parent : wxWindow
        The panel or frame which should serve as the parent for the label
        and control.
    sizer : wxSizer
        The sizer to which the label and text control should be added. Usually,
        it should be a wxFlexGridSizer or wxGridSizer.
    wxId : int
        The ID for the text control (default: wx.ID_ANY).
    label : str
        The text that goes in the label (default: "Input:").
    initialValue : str
        The initial value for the control (default: "").
    border : int
        The border thickness in pixels (default: 0). The same border is applied
        around both the label and the control.
    style : int
        The style (normally, use wx constants) to use for the text control
        (default: 0).
    defocusHandler : method
        A method to be called when the text control loses focus (default: 
        `None`).
    
    Returns
    -------
    wxTextCtrl
        The text control created by this function.
    """
    staticText = wx.StaticText(parent, wx.ID_ANY, label=label)
    textControl = wx.TextCtrl(parent, wxId, value=initialValue, style=style)
    sizer.Add(staticText, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.ALL,
              border)
    sizer.Add(textControl, 1, wx.EXPAND|wx.ALL, border)
    if defocusHandler is not None:
        textControl.Bind(wx.EVT_KILL_FOCUS, defocusHandler)
        
    return textControl

def createLabeledComboBox(parent, sizer, wxId=wx.ID_ANY, label='Input:', 
                          initialValue='', choices=None, border=0, 
                          style=wx.CB_DROPDOWN, defocusHandler=None,
                          valueHandler=None):
    """Create a label and a combo box and add them to the sizer.
    
    Parameters
    ----------
    parent : wxWindow
        The panel or frame which should serve as the parent for the label
        and control.
    sizer : wxSizer
        The sizer to which the label and combo box should be added. Usually,
        it should be a wxFlexGridSizer or wxGridSizer.
    wxId : int
        The ID for the combo box (default: wx.ID_ANY).
    label : str
        The text that goes in the label (default: "Input:").
    initialValue : str
        The initial value for the control (default: "").
    choices : list of str
        A list of strings representing the values the combo box offers. If
        `None` (the default), no options will be available initially. (If
        `None`, make sure that `style` is not `wx.CB_READONLY`, or the combo
        box will be entirely useless.)
    border : int
        The border thickness in pixels (default: 0). The same border is applied
        around both the label and the control.
    style : int
        The style (normally, use wx constants) to use for the combo box
        (default: `wx.CB_DROPDOWN`; the other typical value is 
        `wx.CB_READONLY`).
    defocusHandler : method
        A method to be called when the text control loses focus (default: 
        `None`).
    valueHandler : method
        A method to be called when the value selection in the combo box
        changes (default: `None`)
    
    Returns
    -------
    wxComboBox
        The combo box created by this function.
    """
    if choices is None:
        choices = []
    staticText = wx.StaticText(parent, wx.ID_ANY, label=label)
    comboBox = wx.ComboBox(parent, wxId, initialValue, 
                           choices=choices, style=style)
    sizer.Add(staticText, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT|wx.ALL,
              border)
    sizer.Add(comboBox, 1, wx.EXPAND|wx.ALL, border)
    if defocusHandler is not None:
        comboBox.Bind(wx.EVT_KILL_FOCUS, defocusHandler)
    if valueHandler is not None:
        comboBox.Bind(wx.EVT_COMBOBOX, valueHandler)
        
    return comboBox



class ErrorDialog(wx.Dialog):
    """A dialog for displaying general sequence errors.
    
    Parameters
    ----------
    parent : wxWindow
        The panel or frame which spawns this dialog.
    error : GeneralExperimentError
        The exception whose contents should be displayed in the dialog.
    """
    
    def __init__(self, parent, error):
        super(ErrorDialog, self).__init__(parent)
        
        self.error = error
        
        imageList = wx.ImageList(16, 16, True)
        iconError = imageList.Add(wx.ArtProvider.GetBitmap(wx.ART_ERROR, 
                                                           size=(16, 16)))
        iconWarning = imageList.Add(wx.ArtProvider.GetBitmap(wx.ART_WARNING, 
                                                             size=(16, 16)))
        self.list = ListBox(self, wx.ID_ANY, style=wx.LC_REPORT|wx.LC_NO_HEADER|
                            wx.BORDER_SIMPLE)
        self.list.AssignImageList(imageList, wx.IMAGE_LIST_SMALL)
        self.list.InsertColumn(0, '')
        self.list.Bind(wx.EVT_LIST_ITEM_FOCUSED, self._onSelection)
        
        for kind, text in error.items:
            if kind == 'error':
                imageIndex = iconError
            else:
                imageIndex = iconWarning
            index = self.list.InsertItem(sys.maxsize, text)
            self.list.SetItemImage(index, imageIndex, imageIndex)
        
        
        buttonpanel = wx.Panel(self)
        buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonpanel.SetSizer(buttonsizer)
        
        self.buttonCancel = wx.Button(buttonpanel, wx.ID_CANCEL, label='Cancel')
        self.buttonCancel.Bind(wx.EVT_BUTTON, self._onClose)
        self.buttonProceed = wx.Button(buttonpanel, wx.ID_OK, label='Proceed')
        self.buttonProceed.Bind(wx.EVT_BUTTON, self._onClose)
        if error.errorCount > 0:
            self.buttonProceed.Enable(False)
            label = wx.StaticText(self, label='There are errors in the ' +
                                  'sequence. Cannot proceed.')
            self.SetIcon(wx.ArtProvider.GetIcon(wx.ART_ERROR, size=(16, 16)))
        else:
            label = wx.StaticText(self, label='There are problems with the ' +
                                  'sequence. Are you sure you want to ' +
                                  'proceed?')
            self.SetIcon(wx.ArtProvider.GetIcon(wx.ART_WARNING, size=(16, 16)))
        self.SetTitle('Sequence Errors Detected')
        
        self.infobox = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        self.infobox.SetEditable(False)
        buttonsizer.Add(self.buttonCancel, 0, wx.ALL, 2)
        buttonsizer.Add(self.buttonProceed, 0, wx.ALL, 2)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(label, 0, wx.ALIGN_LEFT|wx.ALL, 5)
        sizer.Add(self.list, 2, wx.ALL|wx.EXPAND, 5)
        sizer.Add(self.infobox, 1, wx.ALL|wx.EXPAND, 5)
        sizer.Add(buttonpanel, 0, wx.ALL|wx.ALIGN_RIGHT, 5)
        
        self.Bind(wx.EVT_CLOSE, self._onClose)
        
        sizer.SetMinSize((400, 300))
        self.SetSizer(sizer)
        self.Layout()
        self.Fit()
        self.list.SetColumnWidth(0, wx.LIST_AUTOSIZE)


    def _onClose(self, event):
        """Respond to a close event."""
        buttonId = event.GetId()
        self.EndModal(buttonId)
        self.Destroy()
        
    def _onSelection(self, event):
        """Respond to selection of items."""
        index = self.list.getSelection()
        message = self.error.items[index][1]
        self.infobox.SetValue(message)
      

#--------------------------------------------------------------------- Prompters

class ComboBoxPrompter(object):
    """An object for prompting for user input from a combo box dialog."""
    
    def __init__(self, parent=None, width=60):
        self._parent = parent
        self._width = width
        
    def prompt(self, prompt, options):
        dialog = wx.SingleChoiceDialog(self._parent, 
                                       textwrap.fill(prompt, self._width),
                                       'Enter a selection',
                                       options,
                                       style=wx.CHOICEDLG_STYLE&~wx.CANCEL)
                                       
        dialog.ShowModal()
        response = dialog.GetSelection()
        dialog.Destroy()
        return response