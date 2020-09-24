"""
``Instrument`` representation of a Keithley 6220 DC Current Source
"""

__all__ = ['Keithley6220']

import logging
from math import fabs

from src.core import instrument as inst
from src.core.action import Action, ActionSpec, ParameterSpec

from src.core.instrument import visa

MIN_CURRENT = 0.105
CURRENT_STRING = ':SOURce:CURRent:LEVel:IMMediate:AMPlitude'

class Keithley6220(inst.Instrument):
    """Driver for a Keithley 6220 current source."""
    
    def __init__(self, experiment, name='Keithley6220: DC current source', 
                 spec=None):
        super(Keithley6220, self).__init__(experiment, name, spec)
        self._instrument = None
        self._info = 'Name: ' + self.getName()
        self._info += '\nModel: Keithley6220 DC current source'

    def initialize(self):
        """Open the communication channel."""
        self._instrument = visa.instrument(self.getSpecification()[0].value)
        self._info += '\n' + self._instrument.ask('*IDN?')
        self._initialized = True
        
    def finalize(self):
        """Close the communication channel."""
        self._instrument.write(CURRENT_STRING + ' 0')
        self._initialized = False
                
    def getAddress(self):
        """Return the instrument's VISA resource address."""
        return self.getSpecification()[0].value
    
    def setCurrent(self, current):
        """Set the current source's output current."""
        if fabs(current) <= MIN_CURRENT:
            logging.error(self.getName() + ': Current ' + str(current) + 
                          ' out of range. Setting to zero.')
            self._instrument.write(CURRENT_STRING + ' 0')
        else:
            self._instrument.write(CURRENT_STRING + ' %.6e' % current)
        return ()
        
    def getCurrent(self):
        """Read the output current from the current source."""
        return (float(self._instrument.ask(CURRENT_STRING + '?')), )
        
    def setOutput(self, output):
        """Toggle the output current on and off."""
        self._instrument.write(':OUTPut ' + output)
        return ()
    
    def getActions(self):
        """Get the list of supported actions."""
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
                             'allowed': ['On', 'Off']})
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
