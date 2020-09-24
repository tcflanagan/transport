"""A graphical interface for controlling the Heliox.
"""

from time import time, sleep
import wx
from wx.lib.newevent import NewEvent
from wx.lib.plot import PlotCanvas, PlotGraphics, PolyLine

from src.gui.main.inst_control import ControllerFrame
from src.gui.instruments import cryomag_panels as cm
# from src.gui.instruments.cryomag_panels import UpdateCommand

ID_PID = wx.NewId()
ID_TEMP1 = wx.NewId()
ID_TEMP2 = wx.NewId()
ID_TEMP3 = wx.NewId()
ID_TEMPAUTO = wx.NewId()
ID_FIELD = wx.NewId()
ID_RAMP = wx.NewId()

class HelioxControllerFrame(ControllerFrame):
    """A frame for communicating with an Oxford Heliox system."""

    MODEL = 'Oxford Heliox'
    
    def __init__(self, parent, controller=None):
     
        super(HelioxControllerFrame, self).__init__(parent, wx.ID_ANY, 
                                                    title='Heliox Controller')
        self.controller = controller
        (self.UpdateEvent, self.EVT_UPDATE_DATA) = NewEvent()
        
        pidLabels = ['Proportional (K)', 'Integral (min)', 
                     'Derivative (min)']
        tempLabels = ['Sorb (K)', 'Sample low (K)', 'Sample high (K)',
                      'Automatic (K)']
        fieldLabels = ['Field (T)', 'Sweep rate (T/min)']
        
        datapanel = wx.Panel(self)
        datasizer = wx.BoxSizer(wx.VERTICAL)
        datapanel.SetSizer(datasizer)
        
        self.pidPanel = cm.GridPanel(datapanel, 'PID settings', pidLabels,
                                     [ID_PID])
        self.tempPanel = cm.GridPanel(datapanel, 'Temperatures', tempLabels,
                                   [ID_TEMP1, ID_TEMP2, ID_TEMP3, ID_TEMPAUTO])
        self.fieldPanel = cm.GridPanel(datapanel, 'Field settings', fieldLabels, 
                                       [ID_FIELD, ID_RAMP])
        
        settingsPanel = wx.Panel(datapanel)
        settingsSizer = wx.BoxSizer(wx.HORIZONTAL)
        settingsPanel.SetSizer(settingsSizer)
        
        self.graphingEnabledCheck = wx.CheckBox(settingsPanel, wx.ID_ANY, 
                                        label='Graphs enabled')
        self.graphingEnabledCheck.SetValue(True)
        settingsSizer.Add(self.graphingEnabledCheck, 0, 
                          wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 5)
        
        datasizer.Add(self.pidPanel, 0, wx.EXPAND|wx.ALL, 5)
        datasizer.Add(self.tempPanel, 0, wx.EXPAND|wx.ALL, 5)
        datasizer.Add(self.fieldPanel, 0, wx.EXPAND|wx.ALL, 5)
        datasizer.Add(settingsPanel, 0, wx.EXPAND|wx.ALL, 5)
        
        self.graphingEnabled = True
        self.autoScaleEnabled = True
        
        self.canvas = PlotCanvas(self)
        self.canvas.SetMinSize((650, -1))
        self.canvas.SetEnableZoom(True)
        self.canvas.SetEnableDrag(True)
        self.canvas.SetEnableLegend(True)
        
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(datapanel, 0, wx.EXPAND, 5)
        self.sizer.Add(self.canvas, 1, wx.EXPAND, 5)
        
        self.SetSizerAndFit(self.sizer)
        
        self._bindEvents()
        
        self.startTime = time()
        self.tempDataLow = []
        self.tempDataHigh = []
        
        
        hoc = cm.UpdateCommand(self.UpdateEvent, self)        
        self.controller.setUpdateCommands([hoc])
        
    def _onSetPID(self, event):
        """Set the Heliox's PID values."""
        self.controller.setPID(*self.pidPanel.getSetpoints())
        
    def _onSetTempSorb(self, event):
        """Set the sorb temperature."""
        self.controller.setTemperatureSorb(
                                    self.tempPanel.getSetpoints()[0])
    
    def _onSetTempLow(self, event):
        """Set the sample-low temperature."""
        self.controller.setTemperatureSampleLow(
                                    self.tempPanel.getSetpoints()[1])
        
    def _onSetTempHigh(self, event):
        """Set the sample-high temperature."""
        self.controller.setTemperatureSampleHigh(
                                    self.tempPanel.getSetpoints()[2])
        
    def _onSetField(self, event):
        """Set the magnetic field."""
        self.controller.setField(self.fieldPanel.getSetpoints()[0])
        
    def _onSetRampRate(self, event):
        """Set the magnetic field ramp rate."""
        self.controller.setFieldRampRate(self.fieldPanel.getSetpoints()[1])
            
    def _onUpdate(self, event):
        """Update the graph."""
        newData = event.data
        temps = newData['temperatures'] + [newData['auto_temp']]
        self.pidPanel.setCurrents(newData['pid'])
        self.tempPanel.setCurrents(temps)
        self.fieldPanel.setCurrents([newData['field'], newData['ramp_rate']])
        
        currtime = time() - self.startTime
        self.tempDataLow.append((currtime, temps[1]))
        self.tempDataHigh.append((currtime, temps[2]))
        if len(self.tempDataLow) >= 60:
            del self.tempDataLow[:20]
            del self.tempDataHigh[:20]
        if self.graphingEnabled:
            pl2 = PolyLine(self.tempDataLow, width=2, colour='blue', 
                           legend='Sample Low')
            pl3 = PolyLine(self.tempDataHigh, width=2, colour='red', 
                           legend='Sample High')
            pgph = PlotGraphics([pl2, pl3], 'Temperatures vs. Time', 'Time (s)', 
                              'Temperature (K)')
            self.canvas.Draw(pgph)
    
    def _onGraphEnabled(self, event):
        """Toggle enabled graphing."""
        self.graphingEnabled = self.graphingEnabledCheck.GetValue()
        if self.graphingEnabled:
            self.canvas.Show(True)
            self.sizer.Layout()
        else:
            self.canvas.Show(False)
            self.sizer.Layout()
    
    def _onClose(self, event):
        """Unbind event handlers and destroy the frame."""
        self.controller.clearUpdateCommands()
        sleep(1)
        self.Destroy()
        
    def _bindEvents(self):
        """Bind the event handlers."""
        self.Bind(wx.EVT_BUTTON, self._onSetPID, id=ID_PID)
        self.Bind(wx.EVT_BUTTON, self._onSetTempSorb, id=ID_TEMP1)
        self.Bind(wx.EVT_BUTTON, self._onSetTempLow, id=ID_TEMP2)
        self.Bind(wx.EVT_BUTTON, self._onSetTempHigh, id=ID_TEMP3)
        self.Bind(wx.EVT_BUTTON, self._onSetField, id=ID_FIELD)
        self.Bind(wx.EVT_BUTTON, self._onSetRampRate, id=ID_RAMP)
        self.Bind(self.EVT_UPDATE_DATA, self._onUpdate)
        self.Bind(wx.EVT_CHECKBOX, self._onGraphEnabled, 
                  self.graphingEnabledCheck)
        self.Bind(wx.EVT_CLOSE, self._onClose)
        
    
if __name__ == '__main__':
    app = wx.App(0)
    heliox = HelioxControllerFrame(None)
    heliox.Show()
    app.MainLoop()