"""Premade: AC/DC differential resistance for one sample on the Heliox.
"""
import wx

from src.gui.instruments.common_panels import LockinPanel, DcVoltmeterPanel
from src.gui.gui_helpers import ScanPanel
from src.gui.main.base_premade import BasePremadeFrame

INFORMATION = {'name': 'Heliox: Differential resistance (1 device)',
               'voltage_type': ['AC', 'DC'],
               'cryostat': ['Heliox'],
               'measurement_type': ['Differential resistance', 'IV'],
               'devices': 1}

class PremadeFrame(BasePremadeFrame):
    """Frame for configuring a one-sample AC Hall measurement on the Heliox."""
    
    def __init__(self, parent):
        
        self.experiment = None
        
        graphData = [('I (A)', 'AC R (Ohm)', 'AC Resistance vs Current'),
                     ('I (A)', 'DC V (V)', 'DC Voltage vs Current')]
        
        super(PremadeFrame, self).__init__(parent, 
                                           INFORMATION['name'], 
                                           graphData,
                                           'IV')
        

        self.lockinpanel = LockinPanel(self, 'Excitation Voltage')
        self.dcvoltpanel = DcVoltmeterPanel(self, 'Bias Voltage')
        self.scanpanel = ScanPanel(self, wx.ID_ANY, 
                                   [(-6, 6, 0.05), (6, -6, 0.05)], 
                                   '%.3f',
                                   label='Magnetic Field (T)')
        self.addConfigurationPanel(self.scanpanel)
        self.addConfigurationPanel(self.lockinpanel)
        self.addConfigurationPanel(self.dcvoltpanel)
        
    def onRun(self, event=None):
        pass
#         expt = Experiment()
#         fileResult = self.filepanel.create()
#         if fileResult == wx.ID_OK:
#             expt.setFilenames(self.filepanel.filename)
#         else:
#             return
#         actionRoot = expt.getActionRoot()
#         inst = expt.getInstrument(0)
#         
#         scanNumber = inst.getAction('scan_num', True)
#         scanNumber.setInputValues([self.scanpanel.getData()])
#         scanNumber.setInputColumns(['Number'])
#         actionRoot.appendChild(scanNumber)
#         
#         calc1 = inst.getAction('calculate', True)
#         calc1.setInputValues(['3*#(Number)'])
#         calc1.setOutputColumns(['Result 1'])
#         scanNumber.appendChild(calc1)
#         calc2 = inst.getAction('calculate', True)
#         calc2.setInputValues(['#(Number)**2'])
#         calc2.setOutputColumns(['Result 2'])
#         scanNumber.appendChild(calc2)
#         delay = inst.getAction('wait', True)
#         delay.setInputValues([1])
#         scanNumber.appendChild(delay)
#         
#         graph1 = Graph(self.experiment, 'Number', 'Result 1', None)
#         graph2 = Graph(self.experiment, 'Number', 'Result 2', None)
#         manager = EmbeddableGraphManager(self.graphspanel, [self.graphPanel1, self.graphPanel2])
#         
#         expt.addGraph(graph1)
#         expt.addGraph(graph2)
#         expt.setInteractionParameters(self, graphManager=manager)
#         
#         self.experiment = expt 
#         
#         super(TestFrame, self).onRun(event)

if __name__ == '__main__':
    app = wx.App(0)
    myFrame = PremadeFrame(None)
    myFrame.Show()
    app.MainLoop()