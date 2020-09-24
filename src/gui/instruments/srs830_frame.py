"""A frame for monitoring and manually controlling the vector magnet."""

# from time import sleep
import wx
# from wx.lib.newevent import NewEvent

from src.gui import gui_helpers as gh
from src.gui.main.inst_control import ControllerFrame
from src.instruments import srs830 as srs
from src.tools.general import frange

ADDRESSES = ['GPIB0::8', 'GPIB0::9', 'GPIB0::12']

class HomelessSRS830Frame (ControllerFrame):
    """A frame for monitoring and manually controlling the vector magnet."""
    MODEL = 'SRS 830: Lock-In'
    def __init__(self, parent, instrument=None):
        super(HomelessSRS830Frame, self).__init__(parent, wx.ID_ANY,
                                                    title='Lock-in Controller')
        if instrument is None:
            self.instrument = srs.SRS830(None)
        else:
            self.instrument = instrument
        
        # Create controls
        outersizer = wx.BoxSizer(wx.HORIZONTAL)
        mainpanel = wx.Panel(self)
        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainpanel.SetSizer(mainsizer)
        
        self.gpibList = None
        self.csens = None
        self.sens = None
        self.ctc = None
        self.tc = None
        self.vx = None
        self.vy = None
        self.cmode = None
        self.mode = None
        self.modeSet = None
        self.cvref = None
        self.vref = None
        self.vrefSet = None
        self.rampStep = None
        self.cfreq = None
        self.freq = None
        self.freqSet = None
        
        self.__initializeInterface(mainpanel, mainsizer)
        
        outersizer.Add(mainpanel, 1, wx.EXPAND)
        self.SetSizerAndFit(outersizer)
        
    def __initializeInterface(self, panel, sizer):
        """Create and layout the controls and indicators."""
        instPanel = gh.Panel(panel, 'horizontal', 'Instrument Addressing')
        instPanel.addStretchSpacer(1)
        instPanel.addLabel('GPIB Address:', 3, 
                           wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        self.gpibList = wx.ComboBox(instPanel, -1, choices=ADDRESSES,
                                    style=wx.CB_READONLY)
        instPanel.add(self.gpibList, 0, wx.ALL, 3)
        self.gpibList.Bind(wx.EVT_COMBOBOX, self.__onChangeAddress)
        instPanel.addButton('Update Addresses', 
                            handler=self.__onUpdateAddressList)
        instPanel.addStretchSpacer(2)
        instPanel.addButton('Initialize',
                            handler=self.__onInitializeInstrument)
        instPanel.addButton('Finalize',
                            handler=self.__onFinalizeInstrument)
        
        refreshBtn = instPanel.addButton('Refresh',
                                         handler=self.__readParameters)
        refreshBtn.SetToolTipString('Update the values of the lock-in\'s '
                                    'settings.')
        instPanel.addStretchSpacer(1)
        
        centerpanel = wx.Panel(panel)
        centersizer = wx.BoxSizer(wx.HORIZONTAL)
        centerpanel.SetSizer(centersizer)
        
        # Input settings
        inputPanel = gh.FormPanel(centerpanel, 'Input Settings', 3, 3)
        centersizer.Add(inputPanel, 1, wx.EXPAND|wx.ALL, 5)
        sens = inputPanel.addRow('Sensitivity', '', None, '', None,
                                 srs.SENSITIVITIES, True, 
                                 handler=self.__onSensitivity)
        self.csens = sens[0]
        self.sens = sens[1]
        self.sens.SetMinSize((80, -1))
        
        tc = inputPanel.addRow('Time Constant', '', None, '', None,
                               srs.TIME_CONSTANTS, True, 
                               handler=self.__onTimeConstant)
        self.ctc = tc[0]
        self.tc = tc[1]
        self.tc.SetMinSize((80, -1))
        
        # Voltage readings
        valuePanel = gh.Panel(centerpanel, 'flex_grid', 'Readings', cols=2)
        valuePanel.addGrowableColumn(1, 1)
        centersizer.Add(valuePanel, 1, wx.EXPAND|wx.ALL, 5)
        self.vx = valuePanel.addLabeledText('Vx (V)', '', border=3, 
                                            style=wx.TE_READONLY|wx.TE_RIGHT)
        self.vy = valuePanel.addLabeledText('Vy (V)', '', border=3, 
                                            style=wx.TE_READONLY|wx.TE_RIGHT)
        bigFont = self.vx.GetFont()
        bigFont.SetPointSize(18)
        self.vx.SetFont(bigFont)
        self.vy.SetFont(bigFont)
        self.vx.SetValue('0.0')
        self.vy.SetValue('0.0')
        
        # Source settings
        sourcePanel = gh.FormPanel(centerpanel, 'Source Settings', 3, 3)
        mode = sourcePanel.addRow('Source', 'Internal', None, 'Internal',
                                  None, srs.REFERENCE_SOURCES, 
                                  handler=self.__onMode)
        self.cmode, self.mode, self.modeSet = mode
        self.mode.SetMinSize((90, -1))
        vref = sourcePanel.addRow('Reference (V)', '0.004', (float, '%.3f'),
                                  '0.004', (float, '%.3f'), (0.004, 5.0),
                                  handler=self.__onVref)
        self.cvref, self.vref, self.vrefSet = vref
        step = sourcePanel.addRow('Ramp Step (V)', None, None,
                                  '0.100', (float, '%.3f'), None,
                                  None, None)
        self.rampStep = step[1]
        freq = sourcePanel.addRow('Frequency (Hz)', '19.0000', (float, '%.4f'),
                                  '19.0000', (float, '%.4f'), (0.0001, 32000))
        self.cfreq, self.freq, self.freqSet = freq   

        centersizer.Add(sourcePanel, 1, wx.EXPAND|wx.ALL, 5)

        sizer.Add(instPanel, 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(centerpanel, 0, wx.EXPAND)
        
    def __readParameters(self):
        """Read parameters from the instrument and fill in the fields."""
        self.ctc.SetValue(self.instrument.getTimeConstant()[0])
        self.csens.SetValue(self.instrument.getSensitivity()[0])
        
        self.cmode.SetValue(self.instrument.getReferenceSource()[0])
        self.cvref.SetValue(self.instrument.getReferenceVoltage()[0])
        self.cfreq.SetValue(self.instrument.getReferenceFrequency()[0])
        
    def __onUpdateAddressList(self, event):
        """Update the list of available GPIB addresses."""
        self.gpibList.SetItems(self.gpibList.GetItems() + ['Another'])
        print('Adding an element.')
        
    def __onChangeAddress(self, event):
        """Change the GPIB address of the instrument."""
        spec = self.instrument.getSpecification()
        spec[0].value = self.gpibList.GetStringSelection()
        
    def __onInitializeInstrument(self, event):
        """Initialize the instrument."""
        self.instrument.initialize()
        
    def __onFinalizeInstrument(self, event):
        """Finalize the instrument."""
        self.instrument.finalize()
        
    def __onSensitivity(self, event):
        """Change the instrument's sensitivity."""
        newValue = self.sens.GetStringSelection()
        print('Changing sensitivity to %s.' % newValue)
        
    def __onTimeConstant(self, event):
        """Change the instrument's time constant."""
        newValue = self.tc.GetStringSelection()
        print('Changing time constant to %s.' % newValue)
    
    def __onMode(self, event):
        """Set the reference source."""
        print('Changing the mode.')
            
    def __onVref(self, event):
        """Set the reference voltage."""
#         oldVal = self.instrument.getReferenceVoltage()[0]
        oldVal = 1.0
        newVal = float(self.vref.GetValue())
        step = abs(float(self.rampStep.GetValue()))
        if step < 0.000001:
            step = 6.0
        
        if abs(newVal - oldVal) < abs(step):
            steps = [newVal]
        else:
            sign = (newVal - oldVal) / abs(newVal - oldVal)
            steps = frange(oldVal, newVal, sign*step)
        
        print(steps)
    
        
    
        
if __name__ == '__main__':
    app = wx.App(0)
    frame = HomelessSRS830Frame(None, None)
    frame.Show()
    app.MainLoop()
        