"""DSP Lock-In Amplifier
"""

from time import sleep
from src.core import instrument as inst
from src.core.instrument import visa
from src.core.action import Action, ActionScan
from src.core.action import ActionSpec, ParameterSpec
from src.tools.general import splitAtComma


REFERENCE_SOURCES = ['External', 'Internal']
REFERENCE_TRIGGERS = ['Sine zero crossing', 'TTL rising edge', 
                      'TTL falling edge']

INPUT_CONFIGS = ['A', 'A-B', 'I (1 MOhm)', 'I (100 MOhm)']
INPUT_GROUNDS = ['Float', 'Ground']
INPUT_COUPLINGS = ['AC', 'DC']
INPUT_NOTCHES = ['Out or none', 'Line notch in', '2x line notch in',
                 'Both notches in']

SENSITIVITIES = ['2nV', '5nV', '10nV', '20nV', '50nV', 
                 '100nV', '200nV', '500nV', 
                 '1uV', '2uV', '5uV', '10uV', '20uV', '50uV', 
                 '100uV', '200uV', '500uV', 
                 '1mV', '2mV', '5mV', '10mV', '20mV', '50mV',
                 '100mV', '200mV', '500mV', '1V']
RESERVE_MODES = ['High reserve', 'Normal', 'Low noise (minimum)']
TIME_CONSTANTS = ['10us', '30us', '100us', '300us', 
                  '1ms', '3ms', '10ms', '30ms', '100ms', '300ms', 
                  '1s', '3s', '10s', '30s', '100s', '300s', 
                  '1ks', '3ks', '10ks', '30ks']
FILTER_SLOPES = ['6 dB/oct', '12 dB/oct', '18 dB/oct', '24 dB/oct']
SYNC_FILTERS = ['Off', 'Below 200 Hz']          

class SRS830(inst.Instrument):
    """Driver for an SRS830 lock-in amplifier."""
    
    def __init__ (self, experiment, name='SRS830: Lock-in amplifier', 
                  spec=None):
        super(SRS830, self).__init__(experiment, name, spec)
        self._instrument = None
        self._info = 'Name: ' + self.getName()
        self._info += 'Model: SRS830 Lock-in amplifier'
    
    def initialize (self):
        """Open the communication channel."""
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
    
    
    #---------------------------------------------------- Data transfer commands
    
    def readSingleVoltageXY (self):
        """Take a single in- and out-of-phase voltage measurement."""
        result = splitAtComma(self._instrument.ask('SNAP? 1,2'))
        return (result[0], result[1])
    
    def readAverageVoltageXY (self, pretime, numavg, intertime):
        """Take an average in- and out-of-phase voltage measurement."""
        action = self._instrument.ask
        strings = ['']*numavg
        sleep(pretime)
        for i in range(numavg):
            strings[i] = action('SNAP? 1,2')
            sleep(intertime)
        voltagesX = [0]*len(numavg)
        voltagesY = [0]*len(numavg)
        for index, item in enumerate(strings):
            result = splitAtComma(item)
            voltagesX[index] = result[0]
            voltagesY[index] = result[1]
        return (sum(voltagesX)/len(voltagesX), sum(voltagesY)/len(voltagesY))
    
    
    #---------------------------------------------- Reference and phase commands
    
    def setReferencePhase(self, phase):
        """Set the lock-in's reference phase."""
        self._instrument.write('PHAS %.2f' % phase)
        return ()
    
    def getReferencePhase(self):
        """Get the lock-in's reference phase."""
        return (float(self._instrument.ask('PHAS?')), )
    
    def setReferenceSource(self, source):
        """Set the lock-in's reference source."""
        self._instrument.write('FMOD %d' % REFERENCE_SOURCES.index(source))
        return ()
        
    def getReferenceSource(self):
        """Get the lock-in's reference source."""
        return (REFERENCE_SOURCES[int(self._instrument.ask('FMOD?'))], )
    
    def setReferenceFrequency(self, freq):
        """Set the lock-in's reference frequency."""
        self._instrument.write('FREQ %.5f' % freq)
        return ()
    
    def getReferenceFrequency(self):
        """Get the lock-in's reference frequency."""
        return (float(self._instrument.ask('FREQ?')), )
    
    def setReferenceTrigger(self, trig):
        """Set the lock-in's reference trigger for external reference mode."""
        self._instrument.write('RSLP %d' % REFERENCE_TRIGGERS.index(trig))
        return ()
    
    def getReferenceTrigger(self):
        """Get the lock-in's reference trigger for external reference mode."""
        return (REFERENCE_TRIGGERS[int(self._instrument.ask('RSLP?'))], )
    
    def setDetectionHarmonic(self, harm):
        """Set the lock-in's detection harmonic."""
        self._instrument.write('HARM %d' % harm)
        return ()
    
    def getDetectionHarmonic(self):
        """Get the lock-in's detection harmonic."""
        return (int(self._instrument.ask('HARM?')), )
        
    def setReferenceVoltage (self, vref):
        """Set the lock-in's reference voltage."""
        self._instrument.write('SLVL %.4f' % vref)
        return ()
    
    def getReferenceVoltage(self):
        """Get the lock-in's reference voltage."""
        return (float(self._instrument.ask('SLVL?')), )
    
    
    #------------------------------------------------- Input and filter commands
    
    def setInputConfiguration(self, config):
        """Set the lock-in's input configuration."""
        self._instrument.write('ISRC %d' % INPUT_CONFIGS.index(config))
        return ()
    
    def getInputConfiguration(self):
        """Get the lock-in's input configuration."""
        return (INPUT_CONFIGS[int(self._instrument.ask('ISRC?')), ])
    
    def setInputGrounding(self, ground):
        """Set the lock-in's input shield grounding configuration."""
        self._instrument.write('IGND %d' % INPUT_GROUNDS.index(ground))
        return ()
    
    def getInputGrounding(self):
        """Get the lock-in's input shield grounding configuration."""
        return (INPUT_GROUNDS[int(self._instrument.ask('IGND?'))], )
    
    def setInputCoupling(self, cpl):
        """Set the lock-in's input coupling configuration."""
        self._instrument.write('ICPL %d' % INPUT_COUPLINGS.index(cpl))
        return ()
    
    def getInputCoupling(self):
        """Get the lock-in's input coupling configuration."""
        return (INPUT_COUPLINGS[int(self._instrument.ask('ICPL?'))], )
    
    def setInputNotch(self, notch):
        """Set the input line notch filter status."""
        self._instrument.write('ILIN %d' % INPUT_NOTCHES.index(notch))
        return ()
    
    def getInputNotch(self):
        """Get the input line notch filter status."""
        return (INPUT_NOTCHES[int(self._instrument.ask('ILIN?'))], )
    
    
    #------------------------------------------- Gain and time constant commands
    
    def setSensitivity (self, sens):
        """Set the lock-in's sensitivity."""
        self._instrument.write('SENS %d' % SENSITIVITIES.index(sens))
        return ()
    
    def getSensitivity (self):
        """Get the lock-in's sensitivity."""
        return (SENSITIVITIES[int(self._instrument.ask('SENS?'))], )
    
    def setReserveMode (self, mode):
        """Set the lock-in's reserve mode."""
        self._instrument.write('RMOD %d' % RESERVE_MODES.index(mode))
        return ()
    
    def getReserveMode (self):
        """Get the lock-in's reserve mode."""
        return (RESERVE_MODES[int(self._instrument.ask('RMOD?'))], )
    
    def setTimeConstant (self, tconst):
        """Set the lock-in's time constant."""
        self._instrument.write('OFLT %d' % TIME_CONSTANTS.index(tconst))
        return ()
    
    def getTimeConstant (self):
        """Get the lock-in's time constant."""
        return (TIME_CONSTANTS[int(self._instrument.ask('OFLT?'))], )
    
    def setLowPassFilter (self, filt):
        """Set the lock-in's low-pass filter slope."""
        self._instrument.write('OFSL %d' % FILTER_SLOPES.index(filt))
        return ()
    
    def getLowPassFilter (self):
        """Get the lock-in's low-pass filter slope."""
        return (FILTER_SLOPES[int(self._instrument.ask('OFSL?'))], )
    
    def setSynchronousFilter (self, filt):
        """Set the lock-in's synchronous filter status."""
        self._instrument.write('SYNC %d' % SYNC_FILTERS.index(filt))
        return ()
    
    def getSynchronousFilter (self):
        """Get the lock-in's synchronous filter status."""
        return (SYNC_FILTERS[int(self._instrument.ask('SYNC?'))], )
    
    
    def getAllParameters(self):
        """Read all lock-in parameters."""
        return (self.getReferencePhase()[0],
                self.getReferenceSource()[0],
                self.getReferenceFrequency()[0],
                self.getReferenceTrigger()[0],
                self.getDetectionHarmonic()[0],
                self.getReferenceVoltage()[0],
                self.getInputConfiguration()[0],
                self.getInputGrounding()[0],
                self.getInputCoupling()[0],
                self.getInputNotch()[0],
                self.getSensitivity()[0],
                self.getReserveMode()[0],
                self.getTimeConstant()[0],
                self.getLowPassFilter()[0],
                self.getSynchronousFilter()[0]
                )
        
        
    #--------------------------------------------------------- Action definition
    
    def getActions (self):
        """Get the list of supported actions."""
        return [
            ActionSpec('read_voltages', Action,
                {'experiment': self._expt, 
                 'instrument': self, 
                 'description': 'Read average voltages (X and Y)',
                 'inputs': [
                    ParameterSpec('pretime', 
                        {'experiment': self._expt, 
                         'description': 'Time before averaging (s)', 
                         'formatString': '%.3f', 
                         'binName': None, 
                         'binType': None, 
                         'value': 0.1, 
                         'allowed': None, 
                         'instantiate': False}),
                    ParameterSpec('numavg',
                        {'experiment': self._expt,
                         'description': 'Number of averages', 
                         'formatString': '%d', 
                         'binName': None, 
                         'binType': None, 
                         'value': 100, 
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
                    ParameterSpec('avgvx',
                        {'experiment': self._expt,
                         'description': 'Average Vx', 
                         'formatString': '%.6e', 
                         'binName': 'Vx_avg', 
                         'binType': 'column', 
                         'value': 0, 
                         'allowed': None, 
                         'instantiate': False}),
                    ParameterSpec('avgvy',
                        {'experiment': self._expt,
                         'description': 'Average Vy', 
                         'formatString': '%.6e', 
                         'binName': 'Vy_avg', 
                         'binType': 'column', 
                         'value': 0, 
                         'allowed': None, 
                         'instantiate': False})
                 ],
                 'string': ('Wait $pretime s, '
                            'then average voltage $numavg times, '
                            'spaced by $intertime s'),
                 'method': self.readAverageVoltageXY
                }
            ),
            ActionSpec('read_voltages_single', Action,
                {'experiment': self._expt, 
                 'instrument': self, 
                 'description': 'Read single voltage (X and Y)',
                 'outputs': [
                    ParameterSpec('vx',
                        {'experiment': self._expt,
                         'description': 'Vx', 
                         'formatString': '%.6e', 
                         'binName': 'Vx', 
                         'binType': 'column', 
                         'value': 0, 
                         'allowed': None, 
                         'instantiate': False}),
                    ParameterSpec('vy',
                        {'experiment': self._expt,
                         'description': 'Vy', 
                         'formatString': '%.6e', 
                         'binName': 'Vy', 
                         'binType': 'column', 
                         'value': 0, 
                         'allowed': None, 
                         'instantiate': False})
                 ],
                 'string': 'Read the in-phase and out-of-phase voltages once.',
                 'method': self.readSingleVoltageXY
                }
            ),
            ActionSpec('set_vref', Action,
                {'experiment': self._expt, 
                 'instrument': self, 
                 'description': 'Set reference voltage',
                 'inputs': [
                    ParameterSpec('vref',
                        {'experiment': self._expt,
                         'description': 'Vref (V)',
                         'formatString': '%.3e',
                         'binName': 'Vref (V)',
                         'binType': 'parameter',
                         'value': 0.0,
                         'allowed': None,
                         'instantiate': False})
                 ],
                 'string': 'Set the sine-out voltage to $vref.',
                 'method': self.setReferenceVoltage
                }
            ),
            ActionSpec('get_vref', Action,
                {'experiment': self._expt, 
                 'instrument': self, 
                 'description': 'Get reference voltage',
                 'outputs': [
                    ParameterSpec('vref',
                        {'experiment': self._expt,
                         'description': 'Vref',
                         'formatString': '%.3e',
                         'binName': 'Vref (V)',
                         'binType': 'parameter',
                         'value': 0.0, 
                         'allowed': None, 
                         'instantiate': False})
                 ],
                 'string': 'Get the sine-out voltage.',
                 'method': self.getReferenceVoltage
                }
            ),
            ActionSpec('set_sens', Action,
                {'experiment': self._expt, 
                 'instrument': self, 
                 'description': 'Set sensitivity',
                 'inputs': [
                    ParameterSpec('sens',
                        {'experiment': self._expt,
                         'description': 'Sensitivity', 
                         'formatString': '%s', 
                         'binName': None, 
                         'binType': None, 
                         'value': '10uV', 
                         'allowed': list(SENSITIVITIES), 
                         'instantiate': False})
                 ],
                 'string': 'Set sensitivity to $sens.',
                 'method': self.setSensitivity
                }
            ),
            ActionSpec('set_tc', Action,
                {'experiment': self._expt, 
                 'instrument': self, 
                 'description': 'Set time constant',
                 'inputs': [
                    ParameterSpec('tconst',
                        {'experiment': self._expt,
                         'description': 'Time constant', 
                         'formatString': '%s', 
                         'binName': None, 
                         'binType': None, 
                         'value': '300ms', 
                         'allowed': list(TIME_CONSTANTS), 
                         'instantiate': False})
                 ],
                 'string': 'Set time constant to $tconst.',
                 'method': self.setTimeConstant
                }
            ),
            ActionSpec('read_params', Action,
                {'experiment': self._expt, 
                 'instrument': self, 
                 'description': 'Read parameters',
                 'outputs': [
                    ParameterSpec('ref_phase',
                        {'experiment': self._expt,
                         'description': 'Ref. phase', 
                         'formatString': '%.2f', 
                         'binName': self._name + ' - Reference Phase (deg)', 
                         'binType': 'parameter', 
                         'value': 0.0, 
                         'instantiate': False}),
                    ParameterSpec('ref_source',
                        {'experiment': self._expt,
                         'description': 'Ref. source', 
                         'formatString': '%s', 
                         'binName': self._name + ' - Reference source', 
                         'binType': 'parameter', 
                         'value': 'Internal',
                         'allowed': list(REFERENCE_SOURCES), 
                         'instantiate': False}),
                    ParameterSpec('ref_freq',
                        {'experiment': self._expt,
                         'description': 'Ref. frequency', 
                         'formatString': '%.4f', 
                         'binName': self._name + ' - Reference frequency (Hz)', 
                         'binType': 'parameter', 
                         'value': '19.0000',
                         'instantiate': False}),
                    ParameterSpec('ref_trig',
                        {'experiment': self._expt,
                         'description': 'Ref. trigger', 
                         'formatString': '%s', 
                         'binName': self._name + ' - Reference trigger', 
                         'binType': 'parameter', 
                         'value': 'Sine zero crossing',
                         'allowed': list(REFERENCE_TRIGGERS), 
                         'instantiate': False}),
                    ParameterSpec('harm',
                        {'experiment': self._expt,
                         'description': 'Detection harmonic', 
                         'formatString': '%d', 
                         'binName': self._name + ' - Detection harmonic', 
                         'binType': 'parameter',
                         'value': '1',
                         'instantiate': False}),
                    ParameterSpec('vref',
                        {'experiment': self._expt,
                         'description': 'Ref. voltage', 
                         'formatString': '%.3f', 
                         'binName': self._name + ' - Reference voltage (V)', 
                         'binType': 'parameter', 
                         'value': '1.000',
                         'instantiate': False}),
                    ParameterSpec('conf',
                        {'experiment': self._expt,
                         'description': 'Input config', 
                         'formatString': '%s', 
                         'binName': self._name + ' - Input configuration', 
                         'binType': 'parameter', 
                         'value': 'A-B',
                         'allowed': list(INPUT_CONFIGS),
                         'instantiate': False}),
                    ParameterSpec('ground',
                        {'experiment': self._expt,
                         'description': 'Input grounding', 
                         'formatString': '%s', 
                         'binName': self._name + ' - Input grounding', 
                         'binType': 'parameter', 
                         'value': 'Ground',
                         'allowed': list(INPUT_GROUNDS),
                         'instantiate': False}),
                    ParameterSpec('couple',
                        {'experiment': self._expt,
                         'description': 'Input coupling', 
                         'formatString': '%s', 
                         'binName': self._name + ' - Input coupling', 
                         'binType': 'parameter', 
                         'value': 'AC',
                         'allowed': list(INPUT_COUPLINGS),
                         'instantiate': False}),
                    ParameterSpec('notch',
                        {'experiment': self._expt,
                         'description': 'Notch filter', 
                         'formatString': '%s', 
                         'binName': self._name + ' - Notch filter', 
                         'binType': 'parameter',
                         'value': 'Out or none',
                         'allowed': list(INPUT_NOTCHES),
                         'instantiate': False}),
                    ParameterSpec('sens',
                        {'experiment': self._expt,
                         'description': 'Sensitivity', 
                         'formatString': '%s', 
                         'binName': self._name + ' - Sensitivity', 
                         'binType': 'parameter',
                         'value': '10uV',
                         'allowed': list(SENSITIVITIES),
                         'instantiate': False}),
                    ParameterSpec('mode',
                        {'experiment': self._expt,
                         'description': 'Reserve mode', 
                         'formatString': '%s', 
                         'binName': self._name + ' - Reserve mode', 
                         'binType': 'parameter',
                         'value': 'High reserve',
                         'allowed': list(RESERVE_MODES),
                         'instantiate': False}),
                    ParameterSpec('tconst',
                        {'experiment': self._expt,
                         'description': 'Time constant', 
                         'formatString': '%s', 
                         'binName': self._name + ' - Time constant', 
                         'binType': 'parameter',
                         'value': '300ms',
                         'allowed': list(TIME_CONSTANTS),
                         'instantiate': False}),
                    ParameterSpec('lp_filt',
                        {'experiment': self._expt,
                         'description': 'Low-pass filter', 
                         'formatString': '%s', 
                         'binName': self._name + ' - Low-pass filter slope', 
                         'binType': 'parameter',
                         'value': '6 dB/oct',
                         'allowed': list(FILTER_SLOPES),
                         'instantiate': False}),
                    ParameterSpec('sync_filt',
                        {'experiment': self._expt,
                         'description': 'Synchronous filter', 
                         'formatString': '%s', 
                         'binName': self._name + ' - Synchronous filter', 
                         'binType': 'parameter',
                         'value': 'Off',
                         'allowed': list(SYNC_FILTERS),
                         'instantiate': False})
                 ],
                 'string': 'Read all lock-in parameters.',
                 'method': self.getAllParameters
                }
            ),
            ActionSpec('scan_vref', ActionScan,
                {'experiment': self._expt, 
                 'instrument': self, 
                 'description': 'Scan reference voltage',
                 'inputs': [
                    ParameterSpec('vref',
                        {'experiment': self._expt,
                         'description': 'Reference voltage', 
                         'formatString': '%.3f', 
                         'binName': 'V_ref', 
                         'binType': 'column', 
                         'value': [(0,0,0)], 
                         'allowed': None, 
                         'instantiate': False})
                 ],
                 'string': 'Scan reference voltage',
                 'method': self.setReferenceVoltage
                }
            )
        ]
        
    #===========================================================================
    # Class methods
    #===========================================================================
    @classmethod
    def getRequiredParameters(cls):
        return [inst.InstrumentParameter('VISA Address', '', 
                                         inst.getVisaAddresses, '%s')]
        