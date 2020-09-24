"""Nano-volt meter.
"""

from time import sleep
from src.core import instrument as inst
from src.core.action import Action
from src.core.action import ActionSpec, ParameterSpec
from src.core.instrument import visa


class HP34420A(inst.Instrument):
    """Driver for an HP34420A: Nanovolt meter."""
    
    def __init__ (self, experiment, name='HP34420A: Nanovolt meter', spec=None):
        super(HP34420A, self).__init__(experiment, name, spec)
        self._instrument = None
        self._info = 'Name: ' + self.getName()
        self._info += '\nModel: HP34420A Nanovolt meter'
    
    def initialize (self):
        """Open communication with the nanovolt meter."""
        self._instrument = visa.instrument(self.getSpecification()[0].value)
        self._info += '\n' + self._instrument.ask('*IDN?')
        self._initialized = True
    
    def finalize(self):
        """Close the communication channel."""
        self._instrument.close()
        self._initialized = False
    
    def getAddress (self):
        """Return the instrument's VISA resource address."""
        return self.getSpecification()[0].value
    
    def readSingleVoltage(self):
        """Read the voltage."""
        return (self._instrument.ask('MEASure?'),)
    
    def readAverageVoltage(self, numavg, intertime):
        """Read the average voltage."""
        total = 0.0
        for _ in range(numavg):
            total += float(self._instrument.ask('MEASure?'))
            sleep(intertime)
        return (total/numavg, )
    
    def getActions (self):
        """Get the list of supported actions."""
        return [
            ActionSpec('read_average_voltage', Action,
                {'experiment': self._expt, 
                 'instrument': self, 
                 'description': 'Read average voltage',
                 'inputs': [
                    ParameterSpec('numavg', 
                        {'experiment': self._expt, 
                         'description': 'Number of averages',
                         'formatString': '%d', 
                         'binName': None, 
                         'binType': None, 
                         'value': 3, 
                         'allowed': None, 
                         'instantiate': False}),
                    ParameterSpec('intertime',
                        {'experiment': self._expt,
                         'description': 'Time between averages (s)', 
                         'formatString': '%.3f', 
                         'binName': None, 
                         'binType': None, 
                         'value': 0.01, 
                         'allowed': None, 
                         'instantiate': False})
                 ],
                 'outputs': [
                    ParameterSpec('avgv',
                        {'experiment': self._expt,
                         'description': 'Average Voltage', 
                         'formatString': '%.6e', 
                         'binName': 'V_avg', 
                         'binType': 'column', 
                         'value': 0, 
                         'allowed': None, 
                         'instantiate': False})
                 ],
                 'string': ('Average voltage $numavg times, '
                            'spaced by $intertime s'),
                 'method': self.readAverageVoltage
                }
            ),
            ActionSpec('read_single_voltage', Action,
                {'experiment': self._expt, 
                 'instrument': self, 
                 'description': 'Read single voltage',
                 'outputs': [
                    ParameterSpec('voltage',
                        {'experiment': self._expt,
                         'description': 'Voltage', 
                         'formatString': '%.6e', 
                         'binName': 'Voltage', 
                         'binType': 'column', 
                         'value': 0.0, 
                         'allowed': None, 
                         'instantiate': False})
                 ],
                 'string': 'Take a single voltage measurement.',
                 'method': self.readSingleVoltage
                }
            )
        ]
        
    #===========================================================================
    # Class methods
    #===========================================================================
    @classmethod
    def getRequiredParameters(cls):
        """Return the list of required parameters for the HP34420A."""
        return [inst.InstrumentParameter('VISA Address', '', 
                                         inst.getVisaAddresses, '%s')]
        