"""Premade: AC Hall effect for one sample on the Heliox.
"""
import wx

from src.core.experiment import Experiment
from src.gui.gui_helpers import Panel, ScanPanel
from src.gui.main.base_premade import BasePremadeFrame
from src.gui.instruments.common_panels import (LockinPanelMaster,
                                          LockinPanelSlave, AveragingPanel)


INFORMATION = {'name': 'Heliox: AC Hall effect (1 sample)',
               'voltage_type': ['AC'],
               'cryostat': ['Heliox'],
               'measurement_type': ['Magnetoresistance'],
               'devices': 1}

class PremadeFrame(BasePremadeFrame):
    """Frame for configuring a one-sample AC Hall measurement on the Heliox."""

    def __init__(self, parent):

        self.experiment = None

        graphData = [('H (T)', 'Rxx (Ohm)', 'Longitudinal Resistance vs Field'),
                     ('H (T)', 'Rxy (Ohm)', 'Transverse Resistance vs Field')]

        super(PremadeFrame, self).__init__(parent,
                                           INFORMATION['name'],
                                           graphData,
                                           'RvsH')


        self.scanpanel = ScanPanel(self, wx.ID_ANY,
                                   [(-6, 6, 0.05), (6, -6, 0.05)],
                                   '%.3f',
                                   label='Magnetic Field (T)')
        self.addConfigurationPanel(self.scanpanel)

        sourcepanel = Panel(self, 'horizontal')
        sourcepanel.addLabel('Source Lock-in:', 5)
        self.sourcevalue = wx.ComboBox(sourcepanel, -1, 'Longitudinal',
                                       choices=['Longitudinal', 'Transverse'])
        self.sourcevalue.SetMinSize((125, -1))
        sourcepanel.add(self.sourcevalue, 1, wx.EXPAND | wx.ALL, 5)
        self.addConfigurationPanel(sourcepanel)

        self.masterpanel = LockinPanelMaster(self, 'Longitudinal Resistance')
        self.slavepanel = LockinPanelSlave(self, 'Transverse Resistance')
        self.addConfigurationPanel(self.masterpanel)
        self.addConfigurationPanel(self.slavepanel)

        self.sourcevalue.Bind(wx.EVT_COMBOBOX, self._onUpdateSource)

        self.averagingpanel = AveragingPanel(self, 'Averaging')
        self.addConfigurationPanel(self.averagingpanel)




    def constructExperiment(self):
        """Create an experiment from the supplied parameters."""
        experiment = Experiment()
        actionRoot = experiment.getActionRoot()
        # FIXME availableInstruments should come from inst_manager
        availableInstruments = experiment.getAvailableInstruments()
        lockinClass = availableInstruments['SRS830']
        inst = experiment.getInstrument(0)

        scanNumber = inst.getAction('scan_num', True)
        scanNumber.setInputValues([self.scanpanel.getData()])
        scanNumber.setInputColumns(['Number'])
        actionRoot.appendChild(scanNumber)


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

    def _onUpdateSource(self, event):
        """Update the static labels to reflect which lock-in is master."""
        sel = self.sourcevalue.GetValue()
        if sel == 'Longitudinal':
            self.masterpanel.label = 'Longitudinal Resistance'
            self.slavepanel.label = 'Transverse Resistance'
        else:
            self.masterpanel.label = 'Transverse Resistance'
            self.slavepanel.label = 'Longitudinal Resistance'

if __name__ == '__main__':
    app = wx.App(0)
    myFrame = PremadeFrame(None)
    myFrame.Show()
    app.MainLoop()
