"""A software representation of the Oxford Heliox 3He insert."""

from configparser import ConfigParser
from threading import Lock
from time import sleep, perf_counter

from src.core import instrument as inst
from src.core.action import Action, ActionScan, ActionSpec, ParameterSpec
from src.instruments.noauto.itc503 import ITC503
from src.instruments.noauto.oxford_common import (waitForStableTemperature,
                                                  expandRange)
from src.instruments.noauto.ps120 import PS120
from src.tools import path_tools as pt

MODE_DIRECT = 0
MODE_THROUGH_MONITOR = 1

UPDATE_DELAY = 0.5

class Heliox(inst.Instrument):
    """A Heliox 3He insert."""
     
    def __init__(self, experiment, name='Heliox', spec=None):
        super(Heliox, self).__init__(experiment, name, spec)
        
        self._info = ('Instrument: ' + self.getName() + '\n' + 
                      'Oxford Instruments Heliox 3He Insert')
        
        config = ConfigParser()
        config.read(pt.unrel('etc', 'heliox.conf'))
        
        # Power supply settings
        psProtocol = str(config.get('ps_address', 'protocol')).lower()
        psGpibaddress = config.get('ps_address', 'gpib_address')
        psIsobusaddress = config.get('ps_address', 'isobus_address')
        psSerial = None
        if psProtocol == 'serial' or psProtocol == 'isobus':
            psSerial = {'baud_rate': config.get('ps_address',
                                                'serial_baud_rate'),
                        'parity': config.get('ps_address',
                                             'serial_parity'),
                        'data_bits': config.get('ps_address',
                                                'serial_data_bits'),
                        'stop_bits': config.get('ps_address',
                                                'serial_stop_bits')}
        self._powerSupply = PS120('Magnet', psProtocol, psIsobusaddress,
                                  psGpibaddress, psSerial)
        
        # Temperature controller settings
        tcProtocol = str(config.get('tc_address', 'protocol')).lower()
        tcGpibaddress = config.get('tc_address', 'gpib_address')
        tcIsobusaddress = config.get('tc_address', 'isobus_address')
        tcSerial = None
        if tcProtocol == 'serial' or tcProtocol == 'isobus':
            tcSerial = {'baud_rate': config.get('tc_address',
                                                'serial_baud_rate'),
                        'parity': config.get('tc_address',
                                             'serial_parity'),
                        'data_bits': config.get('tc_address',
                                                'serial_data_bits'),
                        'stop_bits': config.get('tc_address',
                                                'serial_stop_bits')}
        self._tempController = ITC503('Temperature Controller', 
                                      tcProtocol, tcIsobusaddress,
                                      tcGpibaddress, tcSerial)

        self._standardPID = {'low': eval(config.get('pid', 'low')),
                             'high': eval(config.get('pid', 'high')),
                             'condense': eval(config.get('pid', 'condense'))}

        self._cutoffTemperature = config.getfloat('smart_temp', 'cutoff')
        self._tempStepArray = eval(config.get('smart_temp', 'step_array'))
        
        # These are set at initialization time.
        self._temperatures = None
        self._activeSensor = None
        self._pid = [0, 0, 0]
        self._field = 0
        self._fieldSetpoint = 0
        self._fieldRampRate = config.getfloat('field', 'default_ramp')
                
        self._mode = MODE_DIRECT
        self._lock = Lock()
    
    
    #===========================================================================
    # General
    #===========================================================================
    
    def getInformation(self):
        """Return the Heliox's information string."""
        return self._info
    
    def initialize(self):
        """Initialize the Oxford Heliox."""
        self._tempController.initialize()
        self._powerSupply.initialize()
        self._initialized = True
        
    #FIXME: write finalize methods  
    def finalize(self):
        """Finalize the Oxford Heliox."""
        self._tempController.closeCommunication()
        self._powerSupply.closeCommunication()
        self._initialized = False
        
    def setMode(self, newMode):
        """Set the Heliox reading mode.
        
        Parameters
        ----------
        newMode : int
            An integer (MODE_DIRECT or MODE_THROUGH_MONITOR) to specify the
            reading mode. If it is MODE_DIRECT, all data come directly from
            the temperature controller. If it is MODE_THROUGH_MONITOR, only
            the temperature monitor triggers direct readings from the 
            controller, and other requests from data receive the most recent
            readings so triggered.
        """
        self._mode = newMode
    
    
    #===========================================================================
    # Magnetic field
    #===========================================================================
    
    def setField(self, field, block='yes'):
        """Set the magnetic field.
        
        Parameters
        ----------
        field : float
            The magnetic field in Tesla.
        wait : str
            A string of either 'wait' or 'proceed' to determine whether to
            wait for the field to reach the target.
        """
        self.setFieldNoWait(field)
        
        if block.lower() == 'yes':
            while abs(field - self._field) < 0.0001:
                self.directGetField()
                sleep(0.2)
                if self._expt.isPaused():
                    self.setFieldNoWait(self._field)
                    while self._expt.isPaused():
                        sleep(0.2)
                    self.setFieldNoWait(field)
        self.directGetField()
    
    def setFieldNoWait(self, field):
        """Set the target magnetic field and return.
        
        Parameters
        ----------
        field : float
            The target magnetic field in Tesla.
        """
        with self._lock:
            self._powerSupply.setField(field)
            self._fieldSetpoint = field
                
    def directGetField(self):
        """Read the magnetic field from the power supply.
        
        Returns
        -------
        float
            The magnetic field in Tesla.
        """
        with self._lock:
            self._field = self._powerSupply.getField()
        return self._field
    
    def getField(self):
        """Get the magnetic field.
        
        Returns
        -------
        float
            The magnetic field in Tesla.
        """
        if self._mode == MODE_DIRECT:
            return self.directGetField()
        return self._field
    
    def directGetFieldSetpoint(self):
        """Read the field setpoint from the power supply.
        
        Returns
        -------
        float
            The magnetic field setpoint in Tesla.
        """
        with self._lock:
            self._fieldSetpoint = self._powerSupply.getFieldSetpoint()
        return self._fieldSetpoint
    
    def getFieldSetpoint(self):
        """Get the magnetic field setpoint.
        
        Returns
        -------
        float
            The magnetic field setpoint in Tesla.
        """
        if self._mode == MODE_DIRECT:
            return self.directGetFieldSetpoint()
        return self._fieldSetpoint
    
    def setFieldRampRate(self, rampRate):
        """Set the magnetic field ramp rate.
        
        Parameters
        ----------
        rampRate : float
            The desired magnetic field ramp rate in Tesla/min.
        """
        with self._lock:
            self._powerSupply.setSweepRate(rampRate)
            self._fieldRampRate = rampRate
    
    def directGetFieldRampRate(self):
        """Read the magnetic field sweep rate directly from the power supply.
        
        Returns
        -------
        float
            The magnetic field ramp rate in Tesla/min.
        """
        with self._lock:
            self._fieldRampRate = self._powerSupply.getSweepRate()
        return self._fieldRampRate
    
    def getFieldRampRate(self):
        """Get the magnetic field sweep rate.
        
        Returns
        -------
        float
            The magnetic field ramp rate in Tesla/min.
        """
        if self._mode == MODE_DIRECT:
            return self.directGetFieldRampRate()
        return self._fieldRampRate
    
    
    #===========================================================================
    # Temperature
    #===========================================================================
    
    def setTemperatureSorb(self, temperature):
        """Set the target for the sorb-temperature sensor.
        
        Parameters
        ----------
        temperature : float
            The target temperature in Kelvin.
        """
        with self._lock:
            if self._activeSensor != 1:
                self._tempController.setHeaterSensor('1')
                self._activeSensor = 1
            self._tempController.setTemperature(temperature)
        
        
    def directGetTemperatureSorb(self):
        """Read the sorb temperature from the temperature controller.
        
        Returns
        -------
        float
            The sorb temperature in Kelvin.
        """
        with self._lock:
            self._temperatures[0] = self._tempController.getTemperature('1')
        return self._temperatures[0]
    
    def getTemperatureSorb(self):
        """Get the sorb temperature.
        
        Returns
        -------
        float
            The sorb temperature in Kelvin.
        """
        if self._mode == MODE_DIRECT:
            return self.directGetTemperatureSorb()
        return self._temperatures[0]
        
    def setTemperatureLow(self, temperature):
        """Set the target for the low-temperature sensor.
        
        Parameters
        ----------
        temperature : float
            The target temperature in Kelvin.
        """
        with self._lock:
            if self._activeSensor != 2:
                self._tempController.setHeaterSensor('2')
                self._activeSensor = 2
            self._tempController.setTemperature(temperature)
        
    def directGetTemperatureLow(self):
        """Read the sample-low temperature from the temperature controller.
        
        Returns
        -------
        float
            The sample-low temperature in Kelvin.
        """
        with self._lock:
            self._temperatures[1] = self._tempController.getTemperature('2')
        return self._temperatures[1]
    
    def getTemperatureLow(self):
        """Get the sample-low temperature.
        
        Returns
        -------
        float
            The sorb temperature in Kelvin.
        """
        if self._mode == MODE_DIRECT:
            return self.directGetTemperatureLow()
        return self._temperatures[1]
    
    def setTemperatureHigh(self, temperature):
        """Set the target for the high-temperature sensor.
        
        Parameters
        ----------
        temperature : float
            The target temperature in Kelvin.
        """
        with self._lock:
            if self._activeSensor != 3:
                self._tempController.setHeaterSensor('3')
                self._activeSensor = 3
            self._tempController.setTemperature(temperature)
        
    def directGetTemperatureHigh(self):
        """Read the sample-high temperature from the temperature controller.
        
        Returns
        -------
        float
            The sample-high temperature in Kelvin.
        """
        with self._lock:
            self._temperatures[2] = self._tempController.getTemperature('3')
        return self._temperatures[2]
    
    def getTemperatureHigh(self):
        """Get the sample-high temperature.
        
        Returns
        -------
        float
            The sample-high temperature in Kelvin.
        """
        if self._mode == MODE_DIRECT:
            return self.directGetTemperatureHigh()
        return self._temperatures[2]
    
    def directGetTemperatures(self):
        """Read the temperatures measured on all three sensors.
        
        Returns
        -------
        tuple of float
            A tuple consisting of the sorb temperature, the sample-low
            temperature, and the sample-high temperature expressed as floats.
        """
        with self._lock:
            self._temperatures = list(self._tempController.getTemperatures())
        return tuple(self._temperatures) 
    
    def getTemperatures(self):
        """Read the temperatures measured on all three sensors.
        
        Returns
        -------
        tuple of float
            A tuple consisting of the sorb temperature, the sample-low
            temperature, and the sample-high temperature expressed as floats.
        """
        if self._mode == MODE_DIRECT:
            return self.directGetTemperatures()
        return tuple(self._temperatures)
        
    
    def directGetSampleTemperatures(self):
        """Read the sample temperatures from the temperature controller.
        
        Returns
        -------
        tuple of float
            A 2-tuple consisting of the low and high sample temperatures (i.e.
            all temperatures except that of the sorb).
        """
        with self._lock:
            self._temperatures = [self._temperatures[0],
                                  self._tempController.getTemperature('2'),
                                  self._tempController.getTemperature('3')]
        return tuple(self._temperatures[1:3])
    
    def getSampleTemperatures(self):
        """Get the sample temperatures.
        
        Returns
        -------
        tuple of float
            A 2-tuple consisting of the low and high sample temperatures (i.e.
            all temperatures except that of the sorb).
        """
        if self._mode == MODE_DIRECT:
            return self.directGetSampleTemperatures()
        return tuple(self._temperatures[1:3])
    
    def setTemperature(self, target):
        """Set the temperature intelligently.
        
        Parameters
        ----------
        target : float
            The temperature setpoint.
        """
        if target > self._cutoffTemperature:
            sensor = 3
        else:
            sensor = 2
        temps = self.directGetTemperatures()
                
        goingUp = target > temps[sensor-1]
        if goingUp:
            currTemp = min([temps[1], temps[2]])
                
        else:
            currTemp = max([temps[1], temps[2]])
    
        if (currTemp < self._cutoffTemperature and 
            target < self._cutoffTemperature):
            self._auxSetTemp(target, False)
        elif (currTemp < self._cutoffTemperature and
              target > self._cutoffTemperature):
            self._auxSetTemp(self._cutoffTemperature, False)
            self._auxSetTemp(target, True)
        elif (currTemp > self._cutoffTemperature and
              target < self._cutoffTemperature):
            self._auxSetTemp(self._cutoffTemperature, True)
            self._auxSetTemp(target, False)
        else:
            self._auxSetTemp(target, True)
        
        if target > self._cutoffTemperature:
            waitForStableTemperature(target, self.directGetTemperatureHigh, 5)
        else:
            waitForStableTemperature(target, self.directGetTemperatureLow, 5)
        
    def _auxSetTemp(self, target, aboveCutoff=True, timeout=30.0):
        """Help set the temperature.
        
        Help set the temperature by breaking up the full range into a series
        of smaller, user-defined steps. Set the temperature to a step value,
        wait until the temperature passes that value, then move on to the next
        step. Continue until the target temperature has been passed.
        
        Parameters
        ----------
        target : float
            The desired temperature in Kelvin.
        aboveCutoff : bool
            `True` if the **starting** temperature is above the low sensor/high
            sensor cutoff temperature.
        timeout : float
            The maximum time (in seconds) to wait after setting the temperature
            setpoint at each step before proceeding to the next step.
        """
        if aboveCutoff:
            getTemp = self.directGetTemperatureHigh
            setTemp = self.setTemperatureLow
        else:
            getTemp = self.directGetTemperatureLow
            setTemp = self.setTemperatureLow
            
        if target > getTemp():
            def compareTemp(tempA, tempB):
                """Return tempA < tempB. """
                return tempA < tempB
        else:
            def compareTemp(tempA, tempB):
                """Return tempB < tempA"""
                return tempB < tempA
            
        temp = getTemp()
        for step in expandRange(temp, target, self._tempStepArray):
            setTemp(step)
            startTime = perf_counter()
            while compareTemp(getTemp(), step):
                sleep(0.5)
                if perf_counter() - startTime > timeout:
                    break
       
    def getTemperature(self):
        """Get the temperature (a weighted average of the sample temperatures).
        
        Returns
        -------
        float
            The sample temperature.
        """
        if self._mode == MODE_DIRECT:
            self.directGetTemperatures()
        tempLowC = 1.6
        tempHighC = 2.5
        tempLow = self._temperatures[1]
        tempHigh = self._temperatures[2]
        if tempLow <= tempLowC:
            return tempLow
        if tempHigh >= tempHighC:
            return tempHigh
        return ((tempLow*(tempHighC-tempHigh) + tempHigh*(tempLow-tempLowC))/
               ((tempHighC-tempHigh) + (tempLow-tempLowC)))
                
    def setPID(self, newP, newI, newD=0.0):
        """Set the PID values for the temperature controller.
        
        Parameters
        ----------
        newP : float
            The proportional band in Kelvin, to a resolution of 0.001 K. 
        newI : float
            The integral action time in minutes. Values between 0 and
            140 minutes (inclusive), in steps of 0.1 minutes, are accepted.
        newD : float
            The derivative action time in minutes. The allowed range is
            0 to 273 minutes. The default is 0.0.
        """
        self._lock.acquire()
        self._tempController.setPID(newP, newI, newD)
        self._pid = (newP, newI, newD)
        self._lock.release()
        
    def directGetPID(self):
        """Read the PID values from the temperature controller.
        
        Returns
        -------
        tuple of float
            The proportional, integral, and derivative constants for the
            temperature controller as floats in a tuple.
        """
        self._lock.acquire()
        self._pid = self._tempController.getPID()
        self._lock.release()
        return self._pid
    
    def getPID(self):
        """Get the PID values.
        
        Returns
        -------
        tuple of float
            The proportional, integral, and derivative constants for the
            temperature controller as floats in a tuple.
        """
        if self._mode == MODE_DIRECT:
            return self.directGetPID()
        return self._pid
    
    def getActions(self):
        """Return the list of supported actions."""
        return [
            ActionSpec('get_field', Action,
                {'experiment': self._expt, 
                 'instrument': self, 
                 'description': 'Get field',
                 'outputs': [
                    ParameterSpec('field',
                        {'experiment': self._expt,
                        'description': 'Magnetic field',
                        'formatString': '%.4f',
                        'binName': 'Field',
                        'binType': 'column'})
                 ],
                 'string': 'Read the magnetic field.',
                 'method': self.getField}
            ),
            ActionSpec('set_field', Action,
                {'experiment': self._expt, 
                 'instrument': self, 
                 'description': 'Set field',
                 'inputs': [
                    ParameterSpec('field',
                        {'experiment': self._expt,
                        'description': 'Magnetic field',
                        'formatString': '%.4f',
                        'binName': 'Field',
                        'binType': 'column'}
                    ),
                    ParameterSpec('wait',
                        {'experiment': self._expt,
                        'description': 'Following action',
                        'formatString': '%s',
                        'binName': None,
                        'binType': None,
                        'allowed': ['wait', 'proceed'],
                        'value': 'wait'}
                    )
                 ],
                 'string': 'Set the magnetic field to $field T and $wait.',
                 'method': self.setField}
            ),
            ActionSpec('scan_field', ActionScan,
                {'experiment': self._expt, 
                 'instrument': self, 
                 'description': 'Scan field',
                 'inputs': [
                    ParameterSpec('field',
                        {'experiment': self._expt,
                        'description': 'Magnetic field',
                        'formatString': '%.4f[]',
                        'binName': 'Field',
                        'binType': 'column',
                        'value': [(0.0, 0.0, 0.0)]}
                    )
                 ],
                 'string': 'Scan the magnetic field',
                 'method': self.setField}
            )
        ]


    #===========================================================================
    # Class methods
    #===========================================================================
    
    @classmethod
    def getRequiredParameters(cls):
        return []
    
    @classmethod
    def isSingleton(cls):
        """Return whether at most one instance of the instrument may exist.
        
        Returns
        -------
        bool
            Whether only zero or one instance of the instrument may exist.
        """
        return True


class HelioxController(inst.Controller):
    """A tool for monitoring the Heliox status and manually controlling it."""
    
    def __init__(self, experiment, heliox):
        """Instantiate a Heliox monitor."""
        super(HelioxController, self).__init__()
        self.setDaemon(True)
        self._expt = experiment
        self._heliox = heliox

        self._continue = True
        self._running = False
        
        self._data = {}
        
        self._commands = []
        
    def run(self):
        """Start updating the monitor and listening for commands."""
        self._running = True
        while self._continue:
            self._data = {'field': self._heliox.directGetField(),
                          'setpoint': self._heliox.getFieldSetpoint(),
                          'ramp_rate': self._heliox.getFieldRampRate(),
                          'pid': self._heliox.getPID(),
                          'temperatures': self._heliox.directGetTemperatures(),
                          'auto_temp': self._heliox.getTemperature()}
            for command in self._commands:
                command.execute(data=self._data)
            sleep(UPDATE_DELAY)
        self._running = False

    def abort(self):
        """Stop the monitor."""
        self._continue = False
        self._commands = []
        
    def setUpdateCommands(self, commands):
        """Set the commands to execute each time the monitor updates.
        
        All of the parameters of which the monitor keeps track will be 
        substituted into the commands as keyword arguments every time there
        is an update. The keys are as follows:
            - 'field'
            - 'setpoint'
            - 'ramp_rate'
            - 'pid'
            - 'temperatures'
        
        Parameters
        ----------
        commands : list of Command
            A list of `Command` objects which will be executed each time the
            monitor object updates.
        """
        self._commands = commands
        
    def clearUpdateCommands(self):
        """Remove all update commands."""
        self._commands = []
        
    def setField(self, field):
        """Set the magnetic field.
         
        Parameters
        ----------
        field : float
            The desired magnetic field in Tesla.
        """
        self._heliox.setField(field, 'proceed')
         
    def setFieldRampRate(self, rampRate):
        """Set the magnetic field ramp rate.
         
        Parameters
        ----------
        rampRate : float
            The desired magnetic field ramp rate.
        """
        self._heliox.setFieldRampRate(rampRate)
         
    def setPID(self, newP, newI, newD):
        """Set the PID values for the temperature controller.
         
        Parameters
        ----------
        newP : float
            The proportional band in Kelvin, to a resolution of 0.001 K. 
        newI : float
            The integral action time in minutes. Values between 0 and
            140 minutes (inclusive), in steps of 0.1 minutes, are accepted.
        newD : float
            The derivative action time in minutes. The allowed range is
            0 to 273 minutes. The default is 0.0.
        """
        self._heliox.setPID(newP, newI, newD)
         
    def setTemperatureSorb(self, temperature):
        """Set the sorb temperature.
         
        Parameters
        ----------
        temperature : float
            The desired sorb temperature in Kelvin.
        """
        self._heliox.setTemperatureSorb(temperature)
         
    def setTemperatureSampleLow(self, temperature):
        """Set the sample-low temperature.
         
        Parameters
        ----------
        temperature : float
            The desired sample-low temperature in Kelvin.
        """
        self._heliox.setTemperatureSampleLow(temperature)
         
    def setTemperatureSampleHigh(self, temperature):
        """Set the sample-high temperature.
         
        Parameters
        ----------
        temperature : float
            The desired sample-high temperature in Kelvin.
        """
        self._heliox.setTemperatureSampleHigh(temperature)
 
    def setTemperature(self, temperature):
        """Set the sample temperature using the automatic algorithm.
         
        Parameters
        ----------
        temperature : float
            The desired sample temperature in Kelvin.
        """
        self._heliox.setTemperature(temperature)

    @classmethod
    def getInstrumentClassName(cls):
        """Return the instrument class managed by this controller."""
        return 'Heliox'
    
    @classmethod
    def isSingleton(cls):
        """Return whether at most one instance of the controller may exist.
        
        Returns
        -------
        bool
            Whether only zero or one instance of the controller may exist.
        """
        return True
    
    
    
class HelioxDummy(object):
    """A dummy class for testing Heliox updating"""
    
    def __init__(self):
        """Create a new heliox dummy."""
        
    def directGetField(self):
        """Dummy...read field from file."""
        tempfile = 'C:/Users/thomas.DellWin-PC/Desktop/field.txt'
        with open(tempfile) as temp:
            ans = float(temp.readline().strip())
        return ans
    def getFieldSetpoint(self):
        """Dummy...read field setpoint from file."""
        tempfile = 'C:/Users/thomas.DellWin-PC/Desktop/setpoint.txt'
        with open(tempfile) as temp:
            ans = float(temp.readline().strip())
        return ans
    def getFieldRampRate(self):
        """Dummy...read ramp rate from file."""
        tempfile = 'C:/Users/thomas.DellWin-PC/Desktop/ramp.txt'
        with open(tempfile) as temp:
            ans = float(temp.readline().strip())
        return ans
    def getPID(self):
        """Dummy...read PID from file."""
        tempfile = 'C:/Users/thomas.DellWin-PC/Desktop/pid.txt'
        with open(tempfile) as temp:
            val1 = float(temp.readline().strip())
            val2 = float(temp.readline().strip())
            val3 = float(temp.readline().strip())
        return [val1, val2, val3]
    def directGetTemperatures(self):
        """Dummy...read temperature from file."""
        tempfile = 'C:/Users/thomas.DellWin-PC/Desktop/temp.txt'
        with open(tempfile) as temp:
            val1 = float(temp.readline().strip())
            val2 = float(temp.readline().strip())
            val3 = float(temp.readline().strip())
        return [val1, val2, val3]
    def getTemperature(self):
        """Get the temperature."""
        vals = self.directGetTemperatures()
        tempLowC = 1.6
        tempHighC = 2.5
        tempLow = vals[1]
        tempHigh = vals[2]
        if tempLow <= tempLowC:
            return tempLow
        if tempHigh >= tempHighC:
            return tempHigh
        return ((tempLow*(tempHighC-tempHigh) + tempHigh*(tempLow-tempLowC))/
               ((tempHighC-tempHigh) + (tempLow-tempLowC)))
        
    def setField(self, field, action='wait'):
        """Set the magnetic field."""
        pass
    def setFieldRampRate(self, rampRate):
        """Set the magnetic field ramp rate."""
        pass
    def setPID(self, newP, newI, newD):
        """Set the PID values for the temperature controller."""
        pass
    def setTemperatureSorb(self, temperature):
        """Set the sorb temperature."""
        pass
    def setTemperatureSampleLow(self, temperature):
        """Set the sample-low temperature."""
        pass
    def setTemperatureSampleHigh(self, temperature):
        """Set the sample-high temperature."""
        pass
    def setTemperature(self, temperature):
        """Set the sample temperature using the automatic algorithm."""
        pass

