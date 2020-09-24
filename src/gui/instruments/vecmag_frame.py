"""A frame for monitoring and manually controlling the vector magnet."""

from time import sleep
import wx
from wx.lib.newevent import NewEvent

from src.gui.main.inst_control import ControllerFrame
from src.gui.instruments import cryomag_panels as cm

ID_FIELDX = wx.NewId()
ID_FIELDY = wx.NewId()
ID_FIELDZ = wx.NewId()
ID_FIELDRAMP = wx.NewId()
ID_TEMP = wx.NewId()

class VecMagControllerFrame (ControllerFrame):
    """A frame for monitoring and manually controlling the vector magnet."""
    
    MODEL = 'Oxford Vector Magnet'
    
    def __init__(self, parent, controller=None):
        super(VecMagControllerFrame, self).__init__(parent, wx.ID_ANY,
                                               title='Vector Magnet Controller')
        self.controller = controller
        (self.UpdateEvent, self.EVT_UPDATE_DATA) = NewEvent()
        
        fieldLabels = ['X (T)', 'Y (T)', 'Z (T)', 'Rate Fraction']
        tempLabels = ['Cold Stage', 'Magnet', 'Sorb', 'PT2 Plate',
                      'PT1 Plate', 'Heat Switch']
        
        datapanel = wx.Panel(self)
        datasizer = wx.BoxSizer(wx.VERTICAL)
        datapanel.SetSizer(datasizer)
        
        self.fieldpanel = cm.GridPanel(datapanel, 'Magnetic Fields', 
                                       fieldLabels,
                                       [ID_FIELDX, ID_FIELDY, ID_FIELDZ, 
                                        ID_FIELDRAMP])
        
        midpanel = wx.Panel(datapanel)
        midsizer = wx.BoxSizer(wx.HORIZONTAL)
        midpanel.SetSizer(midsizer)
        
        self.temppanel = cm.GridPanel(midpanel, 'Temperatures (K)', tempLabels,
                                      monitorOnly=True)
        
        comframepanel = wx.Panel(midpanel)
        comframesizer = wx.StaticBoxSizer(wx.StaticBox(comframepanel, wx.ID_ANY, 
                                                       'Controls'), 
                                          wx.VERTICAL)
        companel = wx.Panel(comframepanel)
        comsizer = wx.BoxSizer(wx.VERTICAL)
        companel.SetSizer(comsizer)
        
        self.btncool = wx.Button(companel, -1, 'Cooldown')
        self.btncon = wx.Button(companel, -1, 'Condense')
        self.btnrecon = wx.Button(companel, -1, 'Recondense')
        self.btnsetup = wx.Button(companel, -1, 'Setup')
        comsizer.AddSpacer(3)
        comsizer.Add(self.btncool, 0, wx.ALL, 2)
        comsizer.Add(self.btncon, 0, wx.ALL, 2)
        comsizer.Add(self.btnrecon, 0, wx.ALL, 2)
        comsizer.AddStretchSpacer(1)
        comsizer.Add(self.btnsetup, 0, wx.ALL, 2)
        comsizer.AddSpacer(3)
        
        comframesizer.Add(companel, 1, wx.EXPAND)
        comframepanel.SetSizer(comframesizer)
        
        midsizer.Add(self.temppanel, 1, wx.EXPAND)
        midsizer.Add(comframepanel, 0, wx.EXPAND)
        
        self.hetemppanel = cm.GridPanel(datapanel, 'He3 Pot Temperature (K)',
                                   ['Sample'], [ID_TEMP])
        
        datasizer.Add(self.fieldpanel, 0, wx.EXPAND|wx.ALL, 5)
        datasizer.Add(self.hetemppanel, 0, wx.EXPAND|wx.ALL, 5)
        datasizer.Add(midpanel, 0, wx.EXPAND|wx.ALL, 5)
        
        mainsizer = wx.BoxSizer(wx.HORIZONTAL)
        mainsizer.Add(datapanel, 1, wx.EXPAND)
        
        
        hoc = cm.UpdateCommand(self.UpdateEvent, self)        
        self.controller.setUpdateCommands([hoc])
        
        self.SetSizerAndFit(mainsizer)
    
    def _onSetFieldX(self, event):
        """Set the x-component of the magnetic field."""
        self.controller.setFieldX(self.fieldpanel.getSetpoints()[0])
        
    def _onSetFieldY(self, event):
        """Set the x-component of the magnetic field."""
        self.controller.setFieldY(self.fieldpanel.getSetpoints()[1])
        
    def _onSetFieldZ(self, event):
        """Set the x-component of the magnetic field."""
        self.controller.setFieldZ(self.fieldpanel.getSetpoints()[2])
        
    def _onSetFieldRamp(self, event):
        """Set the ramp rate fraction for the magnetic field."""
        self.controller.setFieldRampProportion(
                                        self.fieldpanel.getSetpoints()[3])
        
    def _onSetTemperature(self, event):
        """Set the vector magnet sample temperature."""
        self.controller.setTemperature(self.hetemppanel.getSetpoints()[0])
        
    def _onUpdate(self, event):
        """Update the display with information from the instrument."""
        data = event.data
        
        self.fieldpanel.setCurrents(data['fields'] + [data['ramp']])
        self.temppanel.setCurrents(data['temps'])
        self.hetemppanel.setCurrents([data['sample_temp']])
        
    def _onClose(self, event):
        """Unbind event handlers and destroy the frame."""
        self.controller.clearUpdateCommands()
        sleep(1)
        self.Destroy()
        
    def _bindEvents(self):
        """Set up the wx event handlers."""
        self.Bind(wx.EVT_BUTTON, self._onSetFieldX, id=ID_FIELDX)
        self.Bind(wx.EVT_BUTTON, self._onSetFieldY, id=ID_FIELDY)
        self.Bind(wx.EVT_BUTTON, self._onSetFieldZ, id=ID_FIELDZ)
        self.Bind(wx.EVT_BUTTON, self._onSetFieldRamp, id=ID_FIELDRAMP)
        self.Bind(self.EVT_UPDATE_DATA, self._onUpdate)
        self.Bind(wx.EVT_CLOSE, self._onClose)
        
if __name__ == '__main__':
    app = wx.App(0)
    frame = VecMagControllerFrame(None)
    frame.Show()
    app.MainLoop()
        