"""Tools for naming files."""

import wx
import wx.lib.scrolledpanel as scrolled

from src.gui import images as img
from src.gui.gui_helpers import createButton

MIN_SIZE = (70, -1)

class NavigableGridPanel(wx.Panel):
    """A panel for creating grids which can be simply altered."""

    def __init__(self, parent, initialData, formatString):

        super(NavigableGridPanel, self).__init__(parent)

#         scrollerpanel = wx.Panel(self, style=wx.BORDER_SUNKEN)
#         scrollersizer = wx.BoxSizer(wx.VERTICAL)
#         scrollerpanel.SetSizer(scrollersizer)
        self.__gridPanel = GridPanel(self, initialData, formatString)
#         scrollersizer.Add(self.__gridPanel, 1, wx.EXPAND)

        navpanel = wx.Panel(self)
        navsizer = wx.BoxSizer(wx.HORIZONTAL)
        navpanel.SetSizer(navsizer)

        self.navUp = createButton(navpanel, navsizer, wx.ID_ANY,
                                      img.getScanUpBitmap(),
                                      tooltip='Move up',
                                      handler=self.__gridPanel.onMoveUp)
        self.navDown = createButton(navpanel, navsizer, wx.ID_ANY,
                                    img.getScanDownBitmap(),
                                    tooltip='Move down',
                                    handler=self.__gridPanel.onMoveDown)
        self.navAdd = createButton(navpanel, navsizer, wx.ID_ANY,
                                   img.getScanAddBitmap(),
                                   tooltip='Add item',
                                   handler=self.__gridPanel.onAdd)
        self.navInsert = createButton(navpanel, navsizer, wx.ID_ANY,
                                      img.getScanInsertBitmap(),
                                      tooltip='Insert item',
                                      handler=self.__gridPanel.onInsert)
        self.navRemove = createButton(navpanel, navsizer, wx.ID_ANY,
                                      img.getScanRemoveBitmap(),
                                      tooltip='Remove item',
                                      handler=self.__gridPanel.onRemove)
        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(navpanel, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 1)
        mainsizer.Add(self.__gridPanel, 2, wx.ALL | wx.EXPAND, 1)
        self.__mainsizer = mainsizer

        self.SetSizerAndFit(mainsizer)


class GridPanel(scrolled.ScrolledPanel):
    """A panel."""

    def __init__(self, parent, initialData, formatString):

        super(GridPanel, self).__init__(parent,
                                        style=wx.VSCROLL | wx.BORDER_SIMPLE)
        self.SetupScrolling(False, True)
        self.ShowScrollbars(0, 1)
        self.SetBackgroundColour(wx.WHITE)

        self.__data = []
        for row in initialData:
            currentRow = []
            for col in row:
                currentRow.append(col)
            self.__data.append(currentRow)
        self.__format = formatString
        self.__columns = len(self.__data[0])

        self.__sizer = wx.FlexGridSizer(cols=3, vgap=0, hgap=0)
        self.__sizer.AddGrowableCol(0, 1)
        self.__sizer.AddGrowableCol(1, 1)
        self.__sizer.AddGrowableCol(2, 1)

        self.__controls = []
        self.__controlId = {}

        for row in self.__data:
            for col in row:
                self.__createControl(col)


        self.__lastSelected = (-1, -1)
        self.Bind(wx.EVT_CHILD_FOCUS, self.__onGainFocus)
        self.SetSizer(self.__sizer)

    def __createControl(self, value=0.0):
        """Create a new text control."""
        newId = wx.NewId()
        newControl = wx.TextCtrl(self, newId, style=wx.TE_RIGHT)
        newControl.SetMinSize(MIN_SIZE)
        newControl.SetValue(self.__format % value)
        newControl.Bind(wx.EVT_KILL_FOCUS, self.__onKillFocus)
        self.__controlId[newId] = newControl
        self.__controls.append(newControl)
        self.__sizer.Add(newControl, 1, wx.EXPAND)
        return newControl

    def __fillData(self):
        """Fill all controls with the appropriate data."""
        index = 0
        for row in self.__data:
            for col in row:
                self.__controls[index].SetValue(self.__format % col)
                index += 1

    def __getSelectedPosition(self):
        """Return te position of the selected item.
        
        Returns
        -------
        int
            The index of the selected row.
        int
            The index of the selected column.
        """
        window = self.FindFocus()
        baseIndex = self.__controls.index(window)
        try:
            return (baseIndex // 3, baseIndex % 3)
        except IndexError:
            return -1

    def __positionToIndex(self, position):
        """Convert a position in the grid to an index in the array.
        
        Parameters
        ----------
        position : tuple of int
            The row and column in which the control is located.
        
        Returns
        -------
        int
            The index of the control in the 1D list of controls.
        """
        row, col = position
        return row * self.__columns + col

    def __indexToPosition(self, index):
        """Covert an index in the list to a position in the grid.
        
        Parameters
        ----------
        index : int
            The index of a control in the 1D list of controls.
            
        Returns
        -------
        int
            The row of the specified control.
        int
            The column of the specified control.
        """
        cols = self.__columns
        return (index // cols, index % cols)

    def __getControlPosition(self, control):
        """Return the position of the specified text control.
        
        Parameters
        ----------
        control : wxControl
            The text control whose position is sought.
        
        Returns
        -------
        int
            The index of the row containing the specified control.
        int
            The index of the column containing the specified control.
        """
        try:
            return self.__indexToPosition(self.__controls.index(control))
        except IndexError:
            return (-1, -1)


    #------------------------------------------------------------ Event Handlers

    def onAdd(self, event):
        """Add a row."""
        self.__addRow()
        self.__lastSelected = (len(self.__data) - 1, 0)
        self.__focusLast()

    def onInsert(self, event):
        """Insert a row at the current position."""
        self.__insertRow(self.__lastSelected[0])
        self.__focusLast()

    def onMoveUp(self, event):
        """Move the current row up one position."""
        row, col = self.__lastSelected
        self.__moveRowUp(row)
        self.__lastSelected = (row - 1, col)
        self.__focusLast()

    def onMoveDown(self, event):
        """Move the current row down one position."""
        row, col = self.__lastSelected
        self.__moveRowDown(row)
        self.__lastSelected = (row + 1, col)
        self.__focusLast()

    def onRemove(self, event):
        """Remove the row at the current position."""
        self.__removeRow(self.__lastSelected[0])
        self.__focusLast()

    def __focusLast(self):
        """Focus the last selected element."""
        try:
            lastSelectedIndex = self.__positionToIndex(self.__lastSelected)
            newControl = self.__controls[lastSelectedIndex]
            newControl.SetFocus()
        except IndexError:
            if len(self.__controls) > 0:
                self.__lastSelected = (0, 0)
                self.__focusLast()



    def __addRow(self, initialData=None):
        """Create a new row at the end."""
        if initialData is None:
            initialData = [0.0] * self.__columns
        for item in initialData:
            self.__createControl(item)
        self.__data.append(list(initialData))

        self.GetParent().Layout()

    def __insertRow(self, index=0, initialData=None):
        """Insert a row at a specified index."""
        if initialData is None:
            initialData = [0.0] * self.__columns
        for _ in range(self.__columns):
            self.__createControl(0.0)
        self.__data.insert(index, initialData)
        self.__fillData()
        self.GetParent().Layout()

    def __removeRow(self, index=0):
        """Remove the row at the specified index."""
        del self.__data[index]
        print(self.__data)
        print(index)
        for _ in range(self.__columns):
            control = self.__controls.pop()
            del self.__controlId[control.GetId()]
            self.__sizer.Remove(control)
            control.Destroy()
        self.__fillData()
        self.GetParent().Layout()

    def __moveRowUp(self, index):
        """Move the row at the specified index up one position."""
        self.__data.insert(index - 1, self.__data.pop(index))
        self.__fillData()

    def __moveRowDown(self, index):
        """Move the row at the specified index down one position."""
        self.__data.insert(index + 1, self.__data.pop(index))
        self.__fillData()

    def __onKillFocus(self, event):
        """Format the previously control and store the new value."""
        try:
            control = self.__controlId[event.GetId()]
            row, column = self.__getControlPosition(control)
            try:
                newValue = float(control.GetValue())
                control.SetValue(self.__format % newValue)
                self.__data[row][column] = newValue
            except ValueError:
                control.SetValue(self.__format % self.__data[row][column])
        except KeyError:
            pass
        event.Skip()

    def __onGainFocus(self, event):
        """Update the selected item."""
        control = self.__controlId[event.GetWindow().GetId()]
        if control in self.__controls:
            self.__lastSelected = self.__getControlPosition(control)
            print(self.__lastSelected)

class TestFrame(wx.Frame):

    def __init__(self):

        super(TestFrame, self).__init__(None, -1, title='Testing')

        mainsizer = wx.BoxSizer(wx.VERTICAL)

        myData = [(2.4, 12, 9.8), (11, 92.9, 0.0)]
        namepanel = NavigableGridPanel(self, myData, '%.3f')
        mainsizer.Add(namepanel, 1, wx.EXPAND)

        self.SetSizerAndFit(mainsizer)


app = wx.App(0)
frame = TestFrame()
frame.Show()
app.MainLoop()

