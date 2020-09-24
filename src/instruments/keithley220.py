"""
``Instrument`` representation of a Keithley 220 DC Current Source
"""

from src.core import instrument as inst
from src.core.action import Action, ActionSpec, ParameterSpec

from src.core.instrument import visa

from src.tools import general

OUTPUT_STRING = 'F%dX'
OUTPUT_STATUS = ['Off', 'On']
CURRENT_SET = 'I%.4eX'

class Keithley220(inst.Instrument):
    """Driver for a Keithley 220 current source.""" 
    
    def __init__(self, experiment, name='Keithley220: DC current source', 
                 spec=None):
        super(Keithley220, self).__init__(experiment, name, spec)
        self._instrument = None
        self._info = 'Name: ' + self.getName()
        self._info += '\nModel: Keithley220 DC current source'

    def initialize(self):
        """Open the communication channel."""
        self._instrument = visa.instrument(self.getSpecification()['Address'])
        self._info += '\n' + self._instrument.ask('*IDN?')
        self._initialized = True
        
    def finalize(self):
        """Close the communication channel."""
        self._instrument.write(CURRENT_SET % 0.0)
        self._instrument.close()
        self._initialized = False
                
    def getAddress(self):
        """Return the instrument's VISA resource address."""
        return self.getSpecification()[0].value
    
    def setCurrent(self, current):
        """Set the current source's output current."""
        self._instrument.write(CURRENT_SET % current)
        return ()
        
    def getCurrent(self):
        """Read the output current from the current source."""
        return (general.splitAtComma(self._instrument.ask('')), )
        
    def setOutput(self, output):
        """Toggle the output current on and off."""
        val = OUTPUT_STATUS.index(output)
        self._instrument.write(OUTPUT_STRING % val)
    
    def getActions(self):
        """Return the list of supported actions."""
        return [
                ActionSpec('set_current', Action,
                    {'experiment': self._expt, 
                     'instrument': self, 
                     'description': 'Set current',
                     'inputs': [
                         ParameterSpec('current',
                             {'experiment': self._expt, 
                              'description': 'Current', 
                              'formatString': '%.6e', 
                              'binName': 'Current',
                              'binType': 'column'})
                     ],
                     'string': 'Set current to $current.',
                     'method': self.setCurrent}
                ),
                ActionSpec('get_current', Action,
                    {'experiment': self._expt, 
                     'instrument': self, 
                     'description': 'Get current',
                     'outputs': [
                         ParameterSpec('current',
                            {'experiment': self._expt, 
                             'description': 'Current', 
                             'formatString': '%.6e', 
                             'binName': 'Current',
                             'binType': 'column'})
                     ],
                     'string': 'Read current.',
                     'method': self.getCurrent}
                ),
                ActionSpec('set_outp', Action,
                    {'experiment': self._expt, 
                     'instrument': self, 
                     'description': 'Toggle current output',
                     'inputs': [
                        ParameterSpec('output',
                            {'experiment': self._expt, 
                             'description': 'Output', 
                             'formatString': '%s',
                             'value': 'On', 
                             'allowed': list(OUTPUT_STATUS)})
                     ],
                     'string': 'Turn current output $output.',
                     'method': self.setOutput}
                )
        ]
                
    #===========================================================================
    # Class methods
    #===========================================================================
    @classmethod
    def getRequiredParameters(cls):
        return [inst.InstrumentParameter('VISA Address', '', 
                                         inst.getVisaAddresses, '%s')]
        