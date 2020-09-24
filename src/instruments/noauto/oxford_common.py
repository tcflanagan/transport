"""Tools which are shared among multiple Oxford Instruments devices

This provides a class which can be overridden by the various instruments from
Oxford instruments. The `OxfordCommon` class provides the initialization and
communication routines common to the ITC503, the PS120, and the IPS120.
"""

import logging
from time import sleep, time

from src.core.instrument import RM, LIB
from visa import constants as vpc
#from src.instruments.pyvisa import vpp43_constants as vpc
#from src.instruments.pyvisa.vpp43 import get_attribute, flush, set_buffer

from src.tools import config_parser as cp
from src.tools.general import frange

PROTOCOLS = ['GPIB', 'Serial', 'Gateway Master', 'Gateway Slave', 'ISOBUS']

SERIAL_ALLOWED = {'baud_rate': ['300', '600', '2400', '4800', '9600', '19200'],
                  'parity': ['None', 'Odd', 'Even', 'Mark', 'Space'],
                  'data_bits': ['7', '8'],
                  'stop_bits': ['1.0', '1.5', '2.0']}

SERIAL_DEFAULTS = {'baud_rate': '9600',
                   'parity': 'None',
                   'data_bits': '8',
                   'stop_bits': '1.0'}

_NONSENSE_ERROR = '%s returned nonsense (%s) on command %s.'

_SERIAL_SIZE = 4096
_SERIAL_SIZE_MASK = vpc.VI_ASRL_IN_BUF + vpc.VI_ASRL_OUT_BUF
_SERIAL_FLUSH_MASK = vpc.VI_ASRL_IN_BUF_DISCARD + vpc.VI_ASRL_OUT_BUF_DISCARD

_SERIAL_CONVERT_BAUD_RATE = {'300': 300,
                             '600': 600, 
                             '2400': 2400, 
                             '4800': 4800, 
                             '9600': 9600, 
                             '19200': 19200}
_SERIAL_CONVERT_PARITY = {'None': vpc.VI_ASRL_PAR_NONE, 
                          'Odd': vpc.VI_ASRL_PAR_ODD, 
                          'Even': vpc.VI_ASRL_PAR_EVEN, 
                          'Mark': vpc.VI_ASRL_PAR_MARK, 
                          'Space': vpc.VI_ASRL_PAR_SPACE}
_SERIAL_CONVERT_DATA_BITS = {'7': 7, '8': 8}
_SERIAL_CONVERT_STOP_BITS = {'1.0': vpc.VI_ASRL_STOP_ONE,
                             '1.5': vpc.VI_ASRL_STOP_ONE5,
                             '2.0': vpc.VI_ASRL_STOP_TWO}
_SERIAL_CONVERT_FLOW = {'None': vpc.VI_ASRL_FLOW_NONE, 
                        'XON/XOFF': vpc.VI_ASRL_FLOW_XON_XOFF, 
                        'RTS/CTS': vpc.VI_ASRL_FLOW_RTS_CTS,
                        'XON/XOFF & RTS/CTS': (vpc.VI_ASRL_FLOW_XON_XOFF + 
                                               vpc.VI_ASRL_FLOW_RTS_CTS),
                        'DTR/DSR': vpc.VI_ASRL_FLOW_DTR_DSR,
                        'XON/XOFF & DTR/DSR': (vpc.VI_ASRL_FLOW_XON_XOFF + 
                                               vpc.VI_ASRL_FLOW_DTR_DSR)}

def _convertSerialDictionary(serial):
    """Convert serial information from human terms to instrument terms."""
    return {'baud_rate': _SERIAL_CONVERT_BAUD_RATE[serial['baud_rate']],
            'parity': _SERIAL_CONVERT_PARITY[serial['parity']],
            'data_bits': _SERIAL_CONVERT_DATA_BITS[serial['data_bits']],
            'stop_bits': _SERIAL_CONVERT_STOP_BITS[serial['stop_bits']]}

class OxfordCommon(object):
    """This is a class to perform actions common to most Oxford Instruments
    devices, including the ITC503, the PS120, and the IPS120.
    
    Parameters
    ----------
    name : str
        A name to identify the instrument
    protocol : {'ISOBUS', 'GPIB', 'Serial', 'Gateway Master', 'Gateway Slave'}
        The protocol for communication between the computer and the power
        supply.
    isobusAddress : str
        An integer string representing the ISOBUS address, if relevant. An
        integer will be accepted and converted.
    visaAddress : str
        A full VISA resource address (including the bus) to locate the 
        instrument (e.g. "GPIB0::27").
    serialConfig : dict
        A dictionary to indicate how to configure a serial port, which is used
        with both the 'ISOBUS' and 'Serial' protocols.
        
    Methods
    -------
    openCommunication()
        Open a new (protocol-specific) communication channel between the
        computer and the instrument, initializing initializing the ports
        and sending device clears as appropriate.
    closeCommunication()
        Close the communication channel between the computer and the
        instrument, freeing reserved resources.
    communicate(command)
        Send a command (str) to the instrument and read its response.
    """
    
    def __init__(self, name='Magnet', protocol='ISOBUS', isobusAddress='0', 
                 visaAddress='GPIB0::23', serialConfig=None):
        """Initialize a new power supply object."""
        
        self._name = name
        self._inst = None
        self._vi = None
        
        self._protocol = protocol.lower().replace(' ', '')
        
        if self._protocol == 'gpib':
            self.communicate = self._communicateGPIB
        elif self._protocol == 'serial':
            self.communicate = self._communicateSerial
        elif self._protocol == 'gatewaymaster' or protocol == 'master':
            self.communicate = self._communicateGateway
        elif self._protocol == 'gatewayslave' or protocol == 'slave':
            self.communicate = self._communicateGateway
        else:
            self.communicate = self._communicateISOBUS
        
        if isinstance(isobusAddress, int):
            self._isobus = '%d' % isobusAddress
        else:
            self._isobus = isobusAddress
        self._visa = visaAddress
        if serialConfig is not None:
            self._serial = _convertSerialDictionary(serialConfig)
            
    
    #===========================================================================
    # Initialization and finalization
    #===========================================================================
    
    def openCommunication(self):
        """Initialize the instrument.
        
        Open a new (protocol-specific) communication channel between the
        computer and the instrument, initializing initializing the ports
        and sending device clears as appropriate.
        
        Parameters
        ----------
        protocol : str
            A string to indicate the communication protocol for the
            instrument. It may be one of the following: 'GPIB', 'Gateway
            Master', 'Gateway Slave', or 'ISOBUS'. The default is 'ISOBUS'.
        """
        
        if self._protocol == 'gpib':
            self._openCommunicationGPIB()
        elif self._protocol == 'serial':
            self._openCommunicationISOBUS()
        elif self._protocol == 'gatewaymaster':
            self._openCommunicationGPIB()
        elif self._protocol == 'gatewayslave':
            self._openCommunicationGatewaySlave()
        else:
            self._openCommunicationISOBUS()
            
    def _openCommunicationISOBUS(self):
        """Initialize the instrument for RS232 or ISOBUS communication."""
        #self._inst = visa.SerialInstrument(self._visa, **self._serial)
        self._inst = RM.open_resource(self._visa, **self._serial)
        self._vi = self._inst.vi
        sleep(0.1)
        self._serialFlushBuffer()
        LIB.set_buffer(self._vi, _SERIAL_SIZE_MASK, _SERIAL_SIZE)
        
    def _openCommunicationGPIB(self):
        """Initialize the instrument for GPIB communication."""
        self._inst = RM.get_instrument(self._visa)
        self._inst.read_termination = '\r'
        self._inst.write_termination = '\r'
        self._inst.clear()
        
    def _openCommunicationGatewaySlave(self):
        """Initialize the power supply as a gateway slave, i.e., do nothing."""
        pass
        
    def closeCommunication(self):
        """Finalize the instrument."""
        if self._inst is not None:
            self._inst.close()
    
    
    #===========================================================================
    # Communication
    #===========================================================================
    
    def _communicateSerial(self, command):
        """Communicate over a serial port."""
        self._serialFlushBuffer()
        return self._communicateGeneral(command)
        
    def _communicateGPIB(self, command):
        """Communicate over a GPIB port."""
        return self._communicateGeneral(command)
        
    def _communicateGateway(self, command):
        """Communicate with a gateway system."""
        return self._communicateGeneral(self._formatForIsobus(command))
        
    def _communicateISOBUS(self, command):
        """Communicate over ISOBUS."""
        self._serialFlushBuffer()
        return self._communicateGeneral(self._formatForIsobus(command))
    
    def _communicateGeneral(self, command):
        """Send a command to the power supply, and read the response.
        
        Parameters
        ----------
        command : str
            A string representing a valid command for an OI instrument. All
            necessary modifications (e.g. adding an ISOBUS address) should
            have already been made.
            
        Returns
        -------
        str
            The instrument's response with `command` stripped.
        """
        sleep(0.1)
        
        commandLength = len(command)
        if command.startswith('Q') or command.startswith('$'):
            self._inst.write(command)
            return ''
        
        response = self._inst.ask(command + '\r')

        if command[:commandLength] != response[:commandLength]:
            message = _NONSENSE_ERROR % (self._name, response, command)
            logging.critical(message)
            raise Exception(message)
        
        return response[commandLength:].strip()
        
    def _formatForIsobus(self, command):
        """Modify a command to include the ISOBUS address.
        
        Parameters
        ----------
        command : str
            The basic command, without an ISOBUS address.
        
        Returns
        -------
        str
            The command with the ISOBUS added, ensuring that any $s remain at 
            the beginning
        """
        if command.startswith('$'):
            return '$@' + self._isobus + command[1:]
        return '@' + self._isobus + command
    
    
    #===========================================================================
    # Serial port tools
    #===========================================================================
    
    def _serialQueryBytesAtPort(self):
        """Query the data at the serial port.
        
        Returns
        -------
        int
            An integer indicating the number of bytes at the serial port for
            this instrument.
        """
        return int(LIB.get_attribute(self._vi, vpc.VI_ATTR_ASRL_AVAIL_NUM))
    
    def _serialFlushBuffer(self):
        """Flush the serial buffer if there are bytes at the port."""
        if self._serialQueryBytesAtPort() > 0:
            sleep(0.05)
            LIB.flush(self._vi, _SERIAL_FLUSH_MASK)
            sleep(0.1)


#===============================================================================
# General functions
#===============================================================================

def waitForStableTemperature(targetTemperature, measurementFunction, 
                             allowedDeviation, deviationType='percent', 
                             stabilizedTime=60.0, timeout=600.0):
    """Wait for the temperature to stabilize.
    
    Wait for the temperature to become steady (within some specified tolerance)
    at a particular target temperature. There are two timers in use in this
    method. One is the total time elapsed since the function starts, and the
    other is the time over which the temperature has been within the tolerance
    (i.e., it resets whenever the temperature goes out of range). The function 
    ends when either the latter timer reaches `stabilizedTime` or when the
    former reaches `timeout`, whichever comes first.
    
    Parameters
    ----------
    targetTemperature : float
        The temperature at which to stabilize.
    measurementFunction : function
        The function or method to use to measure the temperature.
    allowedDeviation : float
        By how much the temperature can vary and still be considered to be
        at the target temperature.
    deviationType : str {'percent', 'absolute'}
        Whether `allowedDeviation` should be treated as a percentage of the
        target temperature or an absolute temperature in Kelvin. For example,
        assume that the target temperature is 10.0 K, and `allowedDeviation` 
        is 5. If `deviationType` is 'percent', then the temperature will
        be accepted as at the target if it is between 9.5 K and 10.5 K,
        inclusive. If `deviationType` is 'absolute', the accepted range is
        5.0 K to 15.0 K, inclusive.
    stabilizedTime : float
        The minimum time, in seconds, over which the temperature must remain
        within the accepted range.
    timeout : float
        Loosely speaking, the maximum time to wait (see `timeoutReset`).
        
    Returns
    -------
    bool
        `True` if the temperature has been within the allowed range long enough
        to be considered stable, or `False` if the function times out.
    """
    
    if deviationType == 'percent':
        validMin = (1.0 - allowedDeviation/100.0)*targetTemperature
        validMax = (1.0 + allowedDeviation/100.0)*targetTemperature
    else:
        validMin = targetTemperature - allowedDeviation
        validMax = targetTemperature + allowedDeviation
    
    startTime = time()
    atTemp = False
    currTemp = measurementFunction()
    timeAtTemp = 0.0
    stabilized = False
    currTime = startTime
    while currTime - startTime < timeout:
        currTime = time()
        currTemp = measurementFunction() 
        print('Total running time: %.3f' % (currTime - startTime))
        print('Current temp: ' + str(currTemp))
        if validMin <= currTemp <= validMax:
            if not atTemp:
                startTimeAtTemp = currTime
                atTemp = True
            timeAtTemp = currTime - startTimeAtTemp
            print('Time at temp: %.3f' % timeAtTemp)
            if timeAtTemp >= stabilizedTime:
                print('At temp long enough. Stopping.')
                stabilized = True
                break
        else: 
            atTemp = False
            print('Not close enough. Restarting timer.')
    return stabilized

def expandRange(initial, final, stepArray):
    """Expand a range, getting the step sizes from an array.
    
    Parameters
    ----------
    initial : float
        The value at which the returned array should start.
    final : float
        The final value in the returned array.
    stepArray : list of 3-tuple of float
        A list of tuples specifying step sizes. Each tuple should consist
        of three elements. The last is the step size, the first is the lowest
        value for which the step size should be used, and the second is
        the highest value for which the step size should be used.
    
    Returns
    -------
    list of float
        A list of floats spanning from `initial` to `final` (inclusive), where
        the step sizes vary based on the value.
    """
    
    if initial > final:
        goingDown = True
        temporary = initial
        initial = final
        final = temporary
    else:
        goingDown = False
    ans = []
    going = False
    for item in stepArray:
        start, stop, step = item
        if start <= final < stop:
            going = False
            ans.extend(frange(start, final, step))
        elif start <= initial < stop:
            going = True
            ans.extend(frange(initial, stop, step))
        elif going:
            ans.extend(frange(start, stop, step))
    if going:
        ans.extend(frange(ans[-1], final, stepArray[-1][2]))
    ans.append(final)
    if goingDown:
        ans.reverse()
    return ans


def readAddressConfig(configurationFile, section):
    """Read the configuration for an Oxford instrument.
    
    Parameters
    ----------
    configurationFile : str
        The absolute path to the configuration file containing the information
        about the instrument.
    section : str
        The section within the configuration file containing the information
        about the relevant instrument.
        
    Returns
    -------
    protocol : str
        The communication protocol, which may be 'ISOBUS', 'GPIB',
        'Serial', 'Gateway Master', and 'Gateway Slave'.
    visaAddress : str
        The VISA resource address for the power supply.
    isobusAddress : str
        The ISOBUS address of the instrument
    serialConfig : dict
        Either `None`, if no serial port is needed, or a dictionary
        containing these keys: 'baud_rate', 'parity', 'data_bits', and
        'stop bits'.
    """
    defaults = {(section, 'protocol'): 'ISOBUS',
                (section, 'gpib_address'): 'GPIB0::24',
                (section, 'isobus_address'): '0',
                (section, 'serial_baud_rate'): '9600',
                (section, 'serial_parity'): 'None',
                (section, 'serial_data_bits'): '8',
                (section, 'serial_stop_bits'): '1.0'}
    conf = cp.ConfigParser(configurationFile, cp.FORMAT_BASIC, 
                           defaultValues=defaults)
    protocol = conf.get(section, 'protocol').lower()
    visaAddress = conf.get(section, 'gpib_address')
    isobusAddress = conf.get(section, 'isobus_address')
    serialConfig = None
    if protocol == 'isobus' or protocol == 'serial':
        serialConfig = {'baud_rate': conf.get(section, 'serial_baud_rate'),
                        'parity': conf.get(section, 'serial_parity'),
                        'data_bits': conf.get(section, 'serial_data_bits'),
                        'stop_bits': conf.get(section, 'serial_stop_bits')}
    
    answer = {'protocol': protocol,
              'visaAddress': visaAddress,
              'isobusAddress': isobusAddress,
              'serialConfig': serialConfig}
    return answer
    

# Serial port flow control does not appear to be implemented. Here are the 
# allowed values, just in case they're needed in the future.
#         'flow_control': ['None', 'XON/XOFF', 'RTS/CTS', 
#                                     'XON/XOFF & RTS/CTS', 'DTR/DSR', 
#                                     'XON/XOFF & DTR/DSR']
#         default = 'None'
