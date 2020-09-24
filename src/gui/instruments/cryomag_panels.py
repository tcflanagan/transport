"""Panels for controlling cryostat-magnet systems

This module provides a versatile panel for receiving data from and sending
data to a cryostat-magnet system, featuring an indicator to show received
values, a control for setting new values, and a button for sending commands.
"""

import string 
import wx

from src.gui import images as img

# pylint: disable=W0221,C0103,W0613
_BUTTON_SIZE_ADDITION = 6

_LABEL_OPTS = wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL

class GridPanel(wx.Panel):
    """A panel for displaying and setting values, allowing arbitrary rows.
    
    This panel features four columns:
        1. A label to indicate what the row represents.
        2. An indicator to show a measured value.
        3. A control for specifying new setpoints.
        4. A button for sending the setpoint to the appropriate handler.
    
    The rows which receive buttons is somewhat customizable. If the 
    `buttonIDs` is set to `None`, no buttons will be created. If it is a 
    single integer or a list of integers of length 1, a single button will
    be created in the last row. If it is a list of integers of the same
    length as the list of row labels, each row will receive a button.
    
    Even if no buttons are to be added, the space will be reserved for them
    to ensure that, when multiple instances of this panel are placed
    above and below one another, the controls will still line up 
    aesthetically.
    
    Parameters
    ----------
    parent : wx.Window
        The frame or panel which owns this panel.
    panelLabel : str
        The string which labels the panel (in the border).
    rowLabels : list of str
        A list of strings which label the rows in the grid.
    buttonIDs : list of int
        A list of integer IDs for the buttons so that the parent can bind
        actions to them.
    monitorOnly : bool
        Whether the frame is only for monitoring values. If `True`, there will
        be no buttons or setpoint fields.
    """
        
    def __init__(self, parent, panelLabel, rowLabels, buttonIDs=None,
                 monitorOnly=False):
        """Create a new GridPanel."""
        super(GridPanel, self).__init__(parent, wx.ID_ANY)
        
#         outerpanel = wx.StaticBox(self, wx.ID_ANY, panelLabel)
#         outersizer = wx.StaticBoxSizer(outerpanel, wx.VERTICAL)
        outersizer = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, 
                                                    panelLabel), 
                                       wx.VERTICAL)
        
        if monitorOnly:
            numCols = 2
        else:
            numCols = 4
        
        mainpanel = wx.Panel(self)
        mainsizer = wx.FlexGridSizer(len(rowLabels)+1, numCols, 5, 5)
        mainpanel.SetSizer(mainsizer)
        mainsizer.AddGrowableCol(0, 1)
        
        okBitmap = img.getOkBitmap()
        buttonSize = [x + _BUTTON_SIZE_ADDITION for x in okBitmap.GetSize()]


        #-- HEADER ROW ---------------------------------------------------------        
        mainsizer.Add(wx.StaticText(mainpanel, wx.ID_ANY, label=''),
                      0, wx.ALIGN_CENTER_HORIZONTAL, 5)
        mainsizer.Add(wx.StaticText(mainpanel, wx.ID_ANY, label='Current'),
                      0, wx.ALIGN_CENTER_HORIZONTAL, 5)
        if not monitorOnly:
            mainsizer.Add(wx.StaticText(mainpanel, wx.ID_ANY, label='Setpoint'),
                          0, wx.ALIGN_CENTER_HORIZONTAL, 5)
        
        if not monitorOnly:
            if buttonIDs is not None:
                mainsizer.Add(wx.StaticText(mainpanel, wx.ID_ANY, label='Set'),
                              0, wx.ALIGN_CENTER_HORIZONTAL, 5)
            else:
                mainsizer.AddSpacer(buttonSize)

        
        #-- ITEMS --------------------------------------------------------------
        self.currentCtrls = []
        self.setpointCtrls = []
        for index, label in enumerate(rowLabels):
            # Row label
            mainsizer.Add(wx.StaticText(mainpanel, wx.ID_ANY, label=label),
                          1, _LABEL_OPTS, 5)
            
            # Current value indicator
            indicator = wx.TextCtrl(mainpanel, wx.ID_ANY, 
                                    style=(wx.TE_RIGHT|wx.TE_RICH2|
                                           wx.TE_READONLY), value='0.0')
            indicator.SetBackgroundColour(wx.WHITE)
            indicator.SetForegroundColour(wx.BLUE)
            mainsizer.Add(indicator, 0, wx.EXPAND, 5)
            self.currentCtrls.append(indicator)
            
            if not monitorOnly:
                # Setpoint control
                control = wx.TextCtrl(mainpanel, wx.ID_ANY, style=wx.TE_RIGHT,
                                      validator=CharValidator(), value='0.0')
                mainsizer.Add(control, 0, wx.EXPAND, 5)
                self.setpointCtrls.append(control)
                
                # Button
                if isinstance(buttonIDs, int):
                    buttonIDs = [buttonIDs]
                if buttonIDs is None:
                    mainsizer.AddSpacer(buttonSize)
                elif len(buttonIDs) == 1:
                    if index == len(rowLabels) - 1:
                        mainsizer.Add(wx.BitmapButton(mainpanel, buttonIDs[0], 
                                                      okBitmap, 
                                                      size=buttonSize), 
                                      0, wx.EXPAND, 5)
                    else:
                        mainsizer.AddSpacer(buttonSize)
                elif len(buttonIDs) == len(rowLabels):
                    mainsizer.Add(wx.BitmapButton(mainpanel, buttonIDs[index], 
                                                  okBitmap, size=buttonSize), 
                                  0, wx.EXPAND, 5)
        
        outersizer.Add(mainpanel, 1, wx.ALL|wx.EXPAND, 5)
        self.SetSizerAndFit(outersizer)
        
    def getSetpoints(self):
        """Get the values of the setpoints.
        
        Returns
        -------
        list of float
            The values of the setpoint controls.
        """
        ans = []
        for setpoint in self.setpointCtrls:
            try:
                value = float(setpoint.GetValue())
            except ValueError:
                value = 0.0
                setpoint.SetValue('0.0')
            ans.append(value)
        return ans
    
    def setCurrents(self, values):
        """Set the values of the current indicators.
        
        Parameters
        ----------
        values : list of float
            Set the indicators for the current values of the parameters
            contained in the panel.
        """
        for (current, value) in zip(self.currentCtrls, values):
            current.SetValue(str(value))


class CharValidator(wx.PyValidator):
    """A validator to ensure that only digits are entered into a control."""
    
    def __init__(self):
        """Create a new validator."""
        super(CharValidator, self).__init__()
        self.Bind(wx.EVT_CHAR, self.OnChar)
        
    def OnChar(self, event):
        """Make sure the character is a digit."""
        key = event.GetKeyCode()
        if key in [wx.WXK_LEFT, wx.WXK_RIGHT]:
            event.Skip()
        else:
            try:
                key = chr(event.GetKeyCode())
                win = self.GetWindow()
                if '.' in win.GetValue() and key == '.':
                    return
                if key in string.letters or key == ' ':
                    return
            except ValueError:
                pass
        event.Skip()
        
    def Validate(self, win):
        """Nothing needs doing when the frame is closed."""
        return True
    
    def Clone(self):
        """Create a new validator."""
        return CharValidator()
    
    def TransferToWindow(self):
        """No data needs to be transferred."""
        return True
    
    def TransferFromWindow(self):
        """No data needs to be transferred."""
        return True

class UpdateCommand(object):
    """A Command subclass for updating a cryostat monitor's data."""
    
    def __init__(self, eventClass, window):
        self.eventClass = eventClass
        self.window = window
        
    def execute(self, *args, **kwargs):
        wx.PostEvent(self.window, self.eventClass(data=kwargs['data']))
        