# -*- coding: utf-8 -*-
"""Panels for use in various custom experiments.

See Also
--------
src.gui.panels.scanpanel
"""
from functools import partial
import wx

from src.core import instrument
from src.gui import gui_helpers as gh

V_MODES = ['Set', 'Read', 'Neither']

# pylint: disable=R0904
    
class VisaPanel(wx.Panel):
    """A panel to gather a VISA address for an instrument."""
    
    def __init__(self, parent, label):
        super(VisaPanel, self).__init__(parent, -1)
        
        self.staticpanel = wx.StaticBox(self, -1, label)
        staticsizer = wx.StaticBoxSizer(self.staticpanel, wx.VERTICAL)
        
        self.visapanel = BaseVisaPanel(self)
        
        staticsizer.Add(self.visapanel, 0, wx.EXPAND|wx.ALL, 5)
        self.SetSizerAndFit(staticsizer)
        
    @property
    def label(self):
        """Get the panel's label."""
        return self.staticpanel.GetLabel()
    @label.setter
    def label(self, newLabel):
        """Set the panel's label."""
        self.staticpanel.SetLabel(newLabel)
        
    @property
    def address(self):
        """Get the VISA resource address."""
        return self.visapanel.value
    
    
class LockinPanel(wx.Panel):
    """A panel for configuring an SRS 830 lock-in amplifier."""
        
    def __init__(self, parent, label):
        super(LockinPanel, self).__init__(parent, -1)
         
        self.staticpanel = wx.StaticBox(self, -1, label)
        staticsizer = wx.StaticBoxSizer(self.staticpanel, wx.VERTICAL)
         
        self.visapanel = BaseVisaPanel(self)
         
        otherpanel = wx.Panel(self, -1)
        othersizer = wx.FlexGridSizer(7, 2, 2, 2)
        otherpanel.SetSizer(othersizer)
 
        controlStyle = wx.TE_RIGHT
        myCtrl = partial(gh.createLabeledTextControl, otherpanel, othersizer, 
                         wx.ID_ANY, style=controlStyle, 
                         defocusHandler=self._onDefocusText)
         
        self.voltageBox = myCtrl('Ref. Voltage (V):', '1.000')
        self.voltageBox.Enable(False)
         
        self.voltageMode = gh.createLabeledComboBox(otherpanel, othersizer,
                                                 label='Voltage Action:',
                                                 choices=V_MODES,
                                                 initialValue='Read',
                                                 style=wx.CB_READONLY)
        self.voltageMode.SetMinSize((125, -1))
        self.voltageMode.Bind(wx.EVT_COMBOBOX, self._onChangeVoltageMode)
         
        self.ballastBox = myCtrl('Ballast (Ω):', '1.000e+06')        
        self.offsetBox = myCtrl('Offset (V):', '0.000000e+00')
        self.averageBox = myCtrl('Averages:', '20')
        self.pretimeBox = myCtrl('Pre-time (s):', '1.000')
        self.intertimeBox = myCtrl('Inter-time (s):', '0.050')
         
        othersizer.AddGrowableCol(1, 1)
         
        staticsizer.Add(self.visapanel, 0, wx.EXPAND|wx.ALL, 5)
        staticsizer.Add(otherpanel, 0, wx.EXPAND|wx.ALL, 5)

        self.SetSizerAndFit(staticsizer)
    
    def _onChangeVoltageMode(self, event):
        """Update the enabled state of the reference voltage based on mode."""
        newMode = self.voltageMode.GetValue()
        if newMode == 'Read':
            self.voltageBox.Enable(False)
        else:
            self.voltageBox.Enable(True)
    
    def _onDefocusText(self, event):
        """Format a value when its control loses focus."""
        source = event.GetEventObject()
        value = source.GetValue()
        try:
            fval = float(value)
        except ValueError:
            fval = 0.0
        if source is self.voltageBox:
            source.SetValue('%.3f' % fval)
        elif source is self.ballastBox:
            source.SetValue('%.3e' % fval)
        elif source is self.offsetBox:
            source.SetValue('%.6e' % fval)
        elif source is self.averageBox:
            source.SetValue('%d' % fval)
        elif source is self.pretimeBox:
            source.SetValue('%.3f' % fval)
        elif source is self.intertimeBox:
            source.SetValue('%.3f' % fval)
    
    @property
    def label(self):
        """Get the panel's label."""
        return self.staticpanel.GetLabel()
    @label.setter
    def label(self, newLabel):
        """Set the panel's label."""
        self.staticpanel.SetLabel(newLabel)
        
    @property
    def address(self):
        """Get the VISA resource address."""
        return self.visapanel.value
    
    @property
    def outputVoltage(self):
        """Get the output voltage."""
        return float(self.voltageBox.GetValue())
    @outputVoltage.setter
    def outputVoltage(self, newVoltage):
        """Set the output voltage."""
        self.voltageBox.SetValue('%.3f' % newVoltage)
    
    @property
    def outputAction(self):
        """Get the output voltage action."""
        return self.voltageMode.GetValue()
    
    @property
    def ballastResistance(self):
        """Get the ballast resistance in ohms."""
        return float(self.ballastBox.GetValue())
    
    @property
    def offsetVoltage(self):
        """Get the offset voltage in volts."""
        return float(self.offsetBox.GetValue())
    
    @property
    def averages(self):
        """Get the number of averages."""
        return int(self.averageBox.GetValue())
    
    @property
    def intertime(self):
        """Get the time between averages."""
        return float(self.intertimeBox.GetValue())
    
    @property
    def pretime(self):
        """Get the time before averaging begins in seconds."""
        return float(self.pretimeBox.GetValue())

class BaseVisaPanel(wx.Panel):
    """A simple VISA panel (without a border)."""
    
    def __init__(self, parent, wxId=wx.ID_ANY, controlWxId=wx.ID_ANY):
        """Constructor."""
        super(BaseVisaPanel, self).__init__(parent, wxId)

        
        visaLabel = wx.StaticText(self, wx.ID_ANY, label='Visa Address:')
        self.visaControl = wx.ComboBox(self, controlWxId, style=wx.CB_DROPDOWN)
        self.updateValues()
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(visaLabel, 0, wx.BOTTOM, 2)
        sizer.Add(self.visaControl, 1, wx.EXPAND|wx.LEFT, 10)
        
        self.SetSizer(sizer)
        self.Layout()
    
    @property
    def value(self):
        """Return the selected value of the VISA control.
        
        Returns
        -------
        str
            The selected VISA resource address.
        """
        return self.visaControl.GetValue()

    def updateValues(self):
        """Update the available resource addresses."""
        currentValue = self.visaControl.GetValue()
        values = instrument.getVisaAddresses()
        self.visaControl.SetItems(values)
        if len(values) > 0:
            if currentValue in values:
                self.visaControl.SetStringSelection(currentValue)
            else:
                self.visaControl.SetSelection(0)
    
class DcVoltmeterPanel(wx.Panel):
    """A panel for configuring DC Voltmeter."""

    def __init__(self, parent, label):
        super(DcVoltmeterPanel, self).__init__(parent, -1)
        
        self.staticpanel = wx.StaticBox(self, -1, label)
        staticsizer = wx.StaticBoxSizer(self.staticpanel, wx.VERTICAL)
        
        self.visapanel = BaseVisaPanel(self)
        
        otherpanel = wx.Panel(self, -1)
        othersizer = wx.FlexGridSizer(3, 2, 2, 2)
        otherpanel.SetSizer(othersizer)

        controlStyle = wx.TE_RIGHT
        myCtrl = partial(gh.createLabeledTextControl, otherpanel, othersizer, 
                         wx.ID_ANY, style=controlStyle, 
                         defocusHandler=self._onDefocusText)
        
        self.averageBox = myCtrl('Averages:', '3')
        self.pretimeBox = myCtrl('Pre-time (s):', '1.000')
        self.intertimeBox = myCtrl('Inter-time (s):', '0.100')
        
        othersizer.AddGrowableCol(1, 1)
        
        staticsizer.Add(self.visapanel, 0, wx.EXPAND|wx.ALL, 5)
        staticsizer.Add(otherpanel, 0, wx.EXPAND|wx.ALL, 5)
        
        self.SetSizerAndFit(staticsizer)
    
    def _onDefocusText(self, event):
        """Format a value when its control loses focus."""
        source = event.GetEventObject()
        value = source.GetValue()
        try:
            fval = float(value)
        except ValueError:
            fval = 0.0
        if source is self.averageBox:
            source.SetValue('%d' % fval)
        elif source is self.pretimeBox:
            source.SetValue('%.3f' % fval)
        elif source is self.intertimeBox:
            source.SetValue('%.3f' % fval)
    
    @property
    def label(self):
        """Get the panel's label."""
        return self.staticpanel.GetLabel()
    @label.setter
    def label(self, newLabel):
        """Set the panel's label."""
        self.staticpanel.SetLabel(newLabel)
        
    @property
    def address(self):
        """Get the VISA resource address."""
        return self.visapanel.value
    
    @property
    def averages(self):
        """Get the number of averages."""
        return int(self.averageBox.GetValue())
    
    @property
    def intertime(self):
        """Get the time between averages."""
        return float(self.intertimeBox.GetValue())
    
    @property
    def pretime(self):
        """Get the time before averaging begins in seconds."""
        return float(self.pretimeBox.GetValue())
    
class LockinPanelMaster(wx.Panel):
    """A panel for configuring an SRS 830 lock-in as a current source.
    
    This class differs from the plain `LockinPanel` in that averaging
    information is left out, since if the `LockinPanelMaster` is used, there
    is probably another lock-in involved, in which case both would typically
    use the same averaging parameters, so it does not make sense to have the
    user enter it all twice.
    """
    
    def __init__(self, parent, label):
        super(LockinPanelMaster, self).__init__(parent, -1)
        
        self.staticpanel = wx.StaticBox(self, -1, label)
        staticsizer = wx.StaticBoxSizer(self.staticpanel, wx.VERTICAL)
        
        self.visapanel = BaseVisaPanel(self)
        
        otherpanel = wx.Panel(self, -1)
        othersizer = wx.FlexGridSizer(4, 2, 2, 2)
        otherpanel.SetSizer(othersizer)

        controlStyle = wx.TE_RIGHT
        myCtrl = partial(gh.createLabeledTextControl, otherpanel, othersizer, 
                         wx.ID_ANY, style=controlStyle, 
                         defocusHandler=self._onDefocusText)
        
        
        self.voltageBox = myCtrl('Ref. Voltage (V):', '1.000')
        self.voltageBox.Enable(False)
        
        self.voltageMode = gh.createLabeledComboBox(otherpanel, othersizer,
                                                 label='Voltage Action:',
                                                 choices=V_MODES,
                                                 initialValue='Read',
                                                 style=wx.CB_READONLY)
        self.voltageMode.SetMinSize((125, -1))
        self.voltageMode.Bind(wx.EVT_COMBOBOX, self._onChangeVoltageMode)
        
        self.ballastBox = myCtrl('Ballast (Ω):', '1.000e+06')        
        self.offsetBox = myCtrl('Offset (V):', '0.000000e+00')
        
        othersizer.AddGrowableCol(1, 1)
        
        staticsizer.Add(self.visapanel, 0, wx.EXPAND|wx.ALL, 5)
        staticsizer.Add(otherpanel, 0, wx.EXPAND|wx.ALL, 5)

        self.SetSizerAndFit(staticsizer)
    
    def _onChangeVoltageMode(self, event):
        """Update the enabled state of the reference voltage based on mode."""
        newMode = self.voltageMode.GetValue()
        if newMode == 'Read':
            self.voltageBox.Enable(False)
        else:
            self.voltageBox.Enable(True)
    
    def _onDefocusText(self, event):
        """Format a value when its control loses focus."""
        source = event.GetEventObject()
        value = source.GetValue()
        try:
            fval = float(value)
        except ValueError:
            fval = 0.0
        if source is self.voltageBox:
            source.SetValue('%.3f' % fval)
        elif source is self.ballastBox:
            source.SetValue('%.3e' % fval)
        elif source is self.offsetBox:
            source.SetValue('%.6e' % fval)
    
    @property
    def label(self):
        """Get the panel's label."""
        return self.staticpanel.GetLabel()
    @label.setter
    def label(self, newLabel):
        """Set the panel's label."""
        self.staticpanel.SetLabel(newLabel)
        
    @property
    def address(self):
        """Get the VISA resource address."""
        return self.visapanel.value
    
    @property
    def outputVoltage(self):
        """Get the output voltage."""
        return float(self.voltageBox.GetValue())
    @outputVoltage.setter
    def outputVoltage(self, newVoltage):
        """Set the output voltage."""
        self.voltageBox.SetValue('%.3f' % newVoltage)
    
    @property
    def outputAction(self):
        """Get the output voltage action."""
        return self.voltageMode.GetValue()
    
    @property
    def ballastResistance(self):
        """Get the ballast resistance in ohms."""
        return float(self.ballastBox.GetValue())
    
    @property
    def offsetVoltage(self):
        """Get the offset voltage in volts."""
        return float(self.offsetBox.GetValue())
    
class LockinPanelSlave(wx.Panel):
    """A panel for configuring an SRS 830 lock-in amplifier as a slave.
    
    The `LockinPanelSlave` panel differs from the full `LockinPanel` in the
    following ways.
    
    1. Since the voltage and current are sourced by a "master" lock-in, the
       reference voltage, the voltage mode, and the ballast resistance are
       unnecessary.
    2. Since there is another lock-in, which will typically use the same
       averaging parameters, including averaging here is unnecessary.
       
    This leaves only the resource address and the offset voltage.
    """
    
    def __init__(self, parent, label):
        super(LockinPanelSlave, self).__init__(parent, -1)
        
        self.staticpanel = wx.StaticBox(self, -1, label)
        staticsizer = wx.StaticBoxSizer(self.staticpanel, wx.VERTICAL)
        
        self.visapanel = BaseVisaPanel(self)
        
        otherpanel = wx.Panel(self, -1)
        othersizer = wx.FlexGridSizer(1, 2, 2, 2)
        otherpanel.SetSizer(othersizer)

        controlStyle = wx.TE_RIGHT
        myCtrl = partial(gh.createLabeledTextControl, otherpanel, othersizer, 
                         wx.ID_ANY, style=controlStyle, 
                         defocusHandler=self._onDefocusText)
        
          
        self.offsetBox = myCtrl('Offset (V):', '0.000000e+00')
        othersizer.AddGrowableCol(1, 1)
        
        staticsizer.Add(self.visapanel, 0, wx.EXPAND|wx.ALL, 5)
        staticsizer.Add(otherpanel, 0, wx.EXPAND|wx.ALL, 5)

        
        self.SetSizerAndFit(staticsizer)
    
    def _onDefocusText(self, event):
        """Format a value when its control loses focus."""
        source = event.GetEventObject()
        value = source.GetValue()
        try:
            fval = float(value)
        except ValueError:
            fval = 0.0
        if source is self.offsetBox:
            source.SetValue('%.6e' % fval)
    
    @property
    def label(self):
        """Get the panel's label."""
        return self.staticpanel.GetLabel()
    @label.setter
    def label(self, newLabel):
        """Set the panel's label."""
        self.staticpanel.SetLabel(newLabel)
        
    @property
    def address(self):
        """Get the VISA resource address."""
        return self.visapanel.value
    
    @property
    def offsetVoltage(self):
        """Get the offset voltage in volts."""
        return float(self.offsetBox.GetValue())
    
class AveragingPanel(wx.Panel):
    """A panel for configuring the averaging parameters for some instrument."""
    
    def __init__(self, parent, label='Averaging'):
        super(AveragingPanel, self).__init__(parent, -1)
        
        controlStyle = wx.TE_RIGHT
        
        self.staticpanel = gh.Panel(self, 'flex_grid', label, 3, 2, 5, 5)
        self.staticpanel.addGrowableColumn(1, 1)
        myCtrl = partial(self.staticpanel.addLabeledText, style=controlStyle,
                         border=0, defocusHandler=self._onDefocusText)
        
        self.averageBox = myCtrl('Averages:', '20')
        self.pretimeBox = myCtrl('Pre-time (s):', '1.000')
        self.intertimeBox = myCtrl('Inter-time (s):', '1.000')

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.staticpanel, 1, wx.EXPAND | wx.ALL)
        self.SetSizerAndFit(sizer)
        
    def _onDefocusText(self, event):
        """Format a value when its control loses focus."""
        source = event.GetEventObject()
        value = source.GetValue()
        try:
            fval = float(value)
        except ValueError:
            fval = 0.0
        if source is self.averageBox:
            source.SetValue('%d' % fval)
        elif source is self.pretimeBox:
            source.SetValue('%.3f' % fval)
        elif source is self.intertimeBox:
            source.SetValue('%.3f' % fval)
    
    @property
    def label(self):
        """Get the panel's label."""
        return self.staticpanel.GetLabel()
    @label.setter
    def label(self, newLabel):
        """Set the panel's label."""
        self.staticpanel.SetLabel(newLabel)
            
    @property
    def averages(self):
        """Get the number of averages."""
        return int(self.averageBox.GetValue())
    
    @property
    def intertime(self):
        """Get the time between averages."""
        return float(self.intertimeBox.GetValue())
    
    @property
    def pretime(self):
        """Get the time before averaging begins in seconds."""
        return float(self.pretimeBox.GetValue())

        