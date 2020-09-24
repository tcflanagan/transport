"""Code to experiment data from XML files."""

from xml.sax import parse
from xml.sax.handler import ContentHandler

from src.core import action
from src.core import experiment
from src.core import graph
from src.core.inst_manager import INSTRUMENT_MANAGER as IM

PARAM_ID = action.PARAM_ID

class _Dispatcher (ContentHandler):
    """A class for parsing experiment XML data files."""
    
    def __init__(self):
        ContentHandler.__init__(self)
    
        self.experiment = None
        
        self.instruments = {}
        self.currentInstrument = None
        self.instrumentParameters = []
        
        self.actions = []
        self.actValues = []
        self.actNames = []
        
        self.graphs = []
    
    def startElement(self, name, attrs):
        self.dispatch('start', name, attrs)
        
    def endElement(self, name):
        self.dispatch('end', name)
        
    def dispatch(self, prefix, name, attrs=None):
        mname = prefix + name.capitalize()
        dname = 'default' + prefix.capitalize()
        method = getattr(self, mname, None)
        if callable(method):
            args = ()
        else:
            method = getattr(self, dname, None)
            args = (name, )
        if prefix == 'start':
            args += (attrs, )
        if callable(method):
            method(*args)
            
    def startExperiment(self, dummy):
        self.experiment = experiment.Experiment()
        self.instruments = {'System': self.experiment.getInstrument(0),
                            'Postprocessor': self.experiment.getInstrument(1)}
        self.actions.append(self.experiment.getActionRoot())
        
    def endExperiment(self):
        pass
        
    def startConstants(self, dummy):
        pass
        
    def endConstants(self):
        pass
        
    def startConstant(self, attrs):
        self.experiment.setConstant(attrs['name'], float(attrs['value']))
        
    def endConstant(self):
        pass
        
    def startInstruments(self, dummy):
        pass
        
    def endInstruments(self):
        pass

    def startInstrument(self, attrs):
        cls, name = attrs['class'], attrs['name']
        if cls != 'System' and cls != 'Postprocessor':
            inst = IM.constructInstrument(cls, self.experiment)
            if inst is None:
                raise Exception('Instrument driver for %s not available.' % cls)
            else:
                inst.setName(name)
            self.currentInstrument = inst
            self.instruments[name] = inst
            self.experiment.addInstrument(inst)
        
    def endInstrument(self):
        if self.currentInstrument is not None:
            for item, val in zip(self.currentInstrument.getSpecification(), 
                                 self.instrumentParameters):
                item.value = val
            self.currentInstrument = None
            self.instrumentParameters = []
        
    def startInstrumentparameter(self, attrs):
        self.instrumentParameters.append(attrs['value'])
        
    def endInstrumentparameter(self):
        pass
    
    def startAction(self, attrs):
        if attrs['instrument_name'] != 'None':
            inst = self.instruments[attrs['instrument_name']]
            act = inst.getAction(attrs['name'])
            if attrs['enabled'] == True:
                act.setEnabled = True
            else:
                act.setEnabled = False
            parent = self.actions[-1]
            parent.appendChild(act)
            self.actions.append(act)
            
    def endAction(self):
        self.actions.pop()
        
    def startInputs(self, attrs):
        pass
        
    def endInputs(self):
        currAct = self.actions[-1]
        currAct.setInputColumns(self.actNames)
        currAct.setInputValues(self.actValues)
        self.actValues = []
        self.actNames = []
        
    def startOutputs(self, attrs):
        pass
    
    def endOutputs(self):
        currAct = self.actions[-1]
        currAct.setOutputColumns(self.actNames)
        self.actValues = []
        self.actNames = []
        
    def startActionparameter(self, attrs):
        self.actValues.append(eval(attrs['value']))
        binName = attrs['bin_name'].strip()
        binType = attrs['bin_type'].strip()
        if binName == '' or binType == '' or binType == 'None':
            self.actNames.append('')
        elif binType == 'parameter':
            self.actNames.append(PARAM_ID + binName)
        else:
            self.actNames.append(binName)
    
    def endActionparameter(self):
        pass
    
    def startChildren(self, attrs):
        pass
    
    def endChildren(self):
        pass
    
    def startSequence(self, attrs):
        pass
    
    def endSequence(self):
        pass
    
    def startGraphs(self, dummy):
        pass
        
    def endGraphs(self):
        pass
        
    def startGraph(self, attrs):
        xcol = attrs['xcol']
        ycol = attrs['ycol']
        addcol = attrs['addcol']
        if addcol == 'None':
            addcol = None
        enabled = eval(attrs['enabled'])
        newGraph = graph.Graph(self.experiment, xcol, ycol, addcol)
        newGraph.setEnabled(enabled)
        self.experiment.addGraph(newGraph)
        
    def endGraph(self):
        pass
            
    def defaultStart(self, name, attrs):
        print('Reading unknown: %s (%s)....' % (name, attrs))
    
    def defaultEnd(self, name):
        print('Finished reading unknown: %s.' % name)


def loadExperiment(experimentFile):
    """Load an experiment from a file.
    
    Parameters
    ----------
    experimentFile : str
        The full path to the experiment which should be loaded.
        
    Returns
    -------
    Experiment
        The experiment contained in the specified file.
    """
    disp = _Dispatcher()
    parse(experimentFile, disp)
    
    return disp.experiment
