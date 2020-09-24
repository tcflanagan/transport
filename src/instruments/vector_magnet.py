"""A software representation of the Oxford Heliox 3He insert."""

from threading import Lock
from time import sleep, time

from src.core import instrument as inst
from src.core.action import Action, ActionScan, ActionSpec, ParameterSpec
from src.instruments.noauto.itc503 import ITC503
from src.instruments.noauto.oxford_common import readAddressConfig
from src.instruments.noauto.oxford_valve import OxfordValve
from src.instruments.noauto.ips120 import IPS120
from src.tools import path_tools as pt
from src.tools import config_parser as cp
from src.tools.coordinates import cartesianToSpherical as c2s
from src.tools.coordinates import sphericalToCartesian as s2c
from src.tools.stability import StabilityTrend, StabilitySetpoint
from src.tools.general import simpleLinearRegression

MODE_DIRECT = 0
MODE_THROUGH_MONITOR = 1

UPDATE_DELAY = 0.5

class VectorMagnet(inst.Instrument):
    """A Vector Magnet.
    
    Parameters
    ----------
    experiment : Experiment
        The experiment which owns the instrument.
    name : str
        The name of the instrument. Typically, it will always be 'Vector
        Magnet'.
    
    """

    def __init__(self, experiment, name='Vector Magnet', spec=None):
        super(VectorMagnet, self).__init__(experiment, name, spec)

        self._info = ('Instrument: ' + self.getName() + '\n' +
                      'Oxford Instruments Vector Magnet and Triton 3He System')

        confFile = pt.unrel('config', 'vector_magnet.conf')

        confmag1 = readAddressConfig(confFile, 'ps1_address')
        confmag2 = readAddressConfig(confFile, 'ps2_address')
        confmag3 = readAddressConfig(confFile, 'ps3_address')

        self._powerSupplies = [IPS120(**confmag1),
                               IPS120(**confmag2),
                               IPS120(**confmag3)]

        conftemp1 = readAddressConfig(confFile, 'tc1_address')
        conftemp2 = readAddressConfig(confFile, 'tc2_address')
        conftemp3 = readAddressConfig(confFile, 'tc3_address')
        self._tempControllers = [ITC503(**conftemp1),
                                 ITC503(**conftemp2),
                                 ITC503(**conftemp3)]
        confvalve = readAddressConfig(confFile, 'aux_address')
        self._valve = OxfordValve(**confvalve)

        conf = cp.ConfigParser(confFile, cp.FORMAT_AUTO)
        
        self._heSorb = conf.getOptionsDict('he3_sorb')
        self._heLow = conf.getOptionsDict('he3_pot_low')
        self._heHigh = conf.getOptionsDict('he3_pot_high')
        self._heatSwitch = conf.getOptionsDict('heat_switch')
        self._pt1 = conf.getOptionsDict('pt1_plate')
        self._pt2 = conf.getOptionsDict('pt2_plate')
        self._int = conf.getOptionsDict('int_plate')
        self._mag = conf.getOptionsDict('magnet')
        for item in (self._heSorb, self._heLow, self._heHigh, self._heatSwitch,
                     self._pt1, self._pt2, self._int, self._mag):
            item['itc'] = self._tempControllers[item['itc']]
        self._ctrlTemp = conf.getOptionsDict('control_temp')
        self._ctrlCool = conf.getOptionsDict('control_cooldown')
        self._ctrlPrecon = conf.getOptionsDict('control_precondense')
        self._ctrlCon = conf.getOptionsDict('control_condense')
        self._ctrlRecon = conf.getOptionsDict('control_autorecondense')

        self._temperatures = {}


        # These are set at initialization time.

        self._field = [0.0, 0.0, 0.0]
        self._fieldSetpoint = [0.0, 0.0, 0.0]
        self._rampLimits = [0.250, 0.125, 0.125]
        self._rampProportion = 1.0
        self._cartesian = True

        self._mode = MODE_DIRECT
        self._lock = Lock()


    #===========================================================================
    # General
    #===========================================================================

    def getInformation(self):
        """Return the vector magnet system's information string."""
        return self._info

    def initialize(self):
        """Initialize the Oxford vector magnet system."""
        for supply in self._powerSupplies:
            supply.initialize()
        for controller in self._tempControllers:
            controller.initialize()
        self._initialized = True

    def finalize(self):
        """Finalize the Oxford vector magnet system."""
        for supply in self._powerSupplies:
            supply.closeCommunication()
        for controller in self._tempControllers:
            controller.closeCommunication()
        self._initialized = False

    def setMode(self, newMode):
        """Set the vector magnet system reading mode.
        
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

    def setFieldNoWaitX(self, field):
        """Set the x-component of the magnetic field.
        
        Parameters
        ----------
        field : float
            The new value of the x-component of the magnetic field in Tesla.
        """
        with self._lock:
            if not self._cartesian:
                self._fieldSetpoint = s2c(*self._fieldSetpoint)
                self._field = s2c(*self._field)
                self._cartesian = True
            self._fieldSetpoint[0] = field
            self._powerSupplies[0].setSweepRate(self._rampLimits[0] *
                                                self._rampProportion)
            self._powerSupplies[0].setField(field)

    def setFieldX(self, field, block):
        """Set the x-component of the magnetic field.
        
        Parameters
        ----------
        field : float
            The new x-component for the magnetic field.
        block : str
            A string, either 'Yes' or 'No', indicating whether to block the
            sequence until the desired field is reached.
        """
        self.setFieldNoWaitX(field)

        if block.lower() == 'yes':
            self.waitForField(self.directGetFieldCartesian)
        self.directGetFieldCartesian()

    def setFieldNoWaitY(self, field):
        """Set the y-component of the magnetic field.
        
        Parameters
        ----------
        field : float
            The new value of the y-component of the magnetic field in Tesla.
        """
        with self._lock:
            if not self._cartesian:
                self._fieldSetpoint = s2c(*self._fieldSetpoint)
                self._field = s2c(*self._field)
                self._cartesian = True
            self._fieldSetpoint[1] = field
            self._powerSupplies[1].setSweepRate(self._rampLimits[1] *
                                                self._rampProportion)
            self._powerSupplies[1].setField(field)

    def setFieldY(self, field, block):
        """Set the y-component of the magnetic field.
        
        Parameters
        ----------
        field : float
            The new x-component for the magnetic field.
        block : str
            A string, either 'Yes' or 'No', indicating whether to block the
            sequence until the desired field is reached.
        """
        self.setFieldNoWaitY(field)

        if block.lower() == 'yes':
            self.waitForField(self.directGetFieldCartesian)
        self.directGetFieldCartesian()

    def setFieldNoWaitZ(self, field):
        """Set the z-component of the magnetic field.
        
        Parameters
        ----------
        field : float
            The new value of the z-component of the magnetic field in Tesla.
        """
        with self._lock:
            if not self._cartesian:
                self._fieldSetpoint = s2c(*self._fieldSetpoint)
                self._field = s2c(*self._field)
                self._cartesian = True
            self._fieldSetpoint[2] = field
            self._powerSupplies[0].setSweepRate(self._rampLimits[2] *
                                                self._rampProportion)
            self._powerSupplies[0].setField(field)

    def setFieldZ(self, field, block):
        """Set the z-component of the magnetic field.
        
        Parameters
        ----------
        field : float
            The new x-component for the magnetic field.
        block : str
            A string, either 'Yes' or 'No', indicating whether to block the
            sequence until the desired field is reached.
        """
        self.setFieldNoWaitZ(field)

        if block.lower() == 'yes':
            self.waitForField(self.directGetFieldCartesian)
        self.directGetFieldCartesian()

    def setField(self, field, block='yes'):
        """Set the z-component of the magnetic field.
        
        Parameters
        ----------
        field : float
            The desired z-component of the magnetic field in Tesla.
        """
        self.setFieldZ(field, block)

    def setFieldNoWaitMagnitude(self, field):
        """Set the magnitude of the magnetic field.
        
        Parameters
        ----------
        field : float
            The new magnitude for the magnetic field in Tesla.
        """
        with self._lock:
            if self._cartesian:
                self._field = c2s(*self._field)
                self._fieldSetpoint = c2s(*self._fieldSetpoint)
                self._cartesian = False
            self._fieldSetpoint[0] = field
            self._setSphericalFieldNoLock()

    def setFieldMagnitude(self, field, block):
        """Set the magnitude of the magnetic field.
        
        Parameters
        ----------
        field : float
            The new magnitude for the magnetic field in Tesla.
        block : str
            A string, either 'Yes' or 'No', indicating whether to block the
            sequence until the desired field is reached.
        """
        self.setFieldNoWaitMagnitude(field)

        if block.lower() == 'yes':
            self.waitForField(self.directGetFieldSpherical)
        self.directGetFieldSpherical()

    def setFieldNoWaitAzimuthal(self, azimuthalAngle):
        """Set the azimuthal angle of the magnetic field.
        
        Parameters
        ----------
        azimuthalAngle : float
            The desired azimuthal angle for the magnetic field, measured in
            degrees down from the positive z-axis.
        """
        with self._lock:
            if self._cartesian:
                self._field = c2s(*self._field)
                self._fieldSetpoint = c2s(*self._fieldSetpoint)
                self._cartesian = False
            self._fieldSetpoint[1] = azimuthalAngle
            self._setSphericalFieldNoLock()

    def setFieldAzimuthal(self, azimuthalAngle, block):
        """Set the magnitude of the magnetic field.
        
        Parameters
        ----------
        azimuthalAngle : float
            The new azimuthal angle for the field vector, measured in degrees
            down from the positive z-axis.
        block : str
            A string, either 'Yes' or 'No', indicating whether to block the
            sequence until the desired field is reached.
        """
        self.setFieldNoWaitAzimuthal(azimuthalAngle)

        if block.lower() == 'yes':
            self.waitForField(self.directGetFieldSpherical)
        self.directGetFieldSpherical()

    def setFieldNoWaitPolar(self, polarAngle):
        """Set the polar angle of the magnetic field.
        
        Parameters
        ----------
        polarAngle : float
            The desired polar angle for the magnetic field, measured in
            degrees counter-clockwise from the positive x-axis.
        """
        with self._lock:
            if self._cartesian:
                self._field = c2s(*self._field)
                self._fieldSetpoint = c2s(*self._fieldSetpoint)
                self._cartesian = False
            self._fieldSetpoint[1] = polarAngle
            self._setSphericalFieldNoLock()

    def setFieldPolar(self, polarAngle, block):
        """Set the magnitude of the magnetic field.
        
        Parameters
        ----------
        polarAngle : float
            The new polar angle for the field vector, measured in degrees
            counter-clockwise from the positive x-axis.
        block : str
            A string, either 'Yes' or 'No', indicating whether to block the
            sequence until the desired field is reached.
        """
        self.setFieldNoWaitAzimuthal(polarAngle)

        if block.lower() == 'yes':
            self.waitForField(self.directGetFieldSpherical)
        self.directGetFieldSpherical()

    def setFieldNoWaitCartesian(self, fieldX, fieldY, fieldZ):
        """Set the magnetic field to a specified value in Cartesian coordinates.
        
        Parameters
        ----------
        fieldX : float
            The x-component of the field in Tesla.
        fieldY : float
            The y-component of the field in Tesla.
        fieldZ : float
            The z-component of the field in Tesla.
        """
        with self._lock:
            if not self._cartesian:
                self._field = s2c(*self._field)
                self._cartesian = True
            self._fieldSetpoint = [fieldX, fieldY, fieldZ]
            rates = self._calculateSweepRate(self._field, self._fieldSetpoint)
            for supply, rate, target in zip(self._powerSupplies, rates,
                                            self._fieldSetpoint):
                supply.setSweepRate(rate)
                supply.setField(target)

    def setFieldCartesian(self, fieldX, fieldY, fieldZ, block):
        """Set the magnetic field to a specified value in Cartesian coordinates.
        
        Parameters
        ----------
        fieldX : float
            The x-component of the field in Tesla.
        fieldY : float
            The y-component of the field in Tesla.
        fieldZ : float
            The z-component of the field in Tesla.
        block : str
            A string, either 'Yes' or 'No', indicating whether to block the
            sequence until the desired field is reached.
        """
        self.setFieldNoWaitCartesian(fieldX, fieldY, fieldZ)

        if block.lower() == 'yes':
            self.waitForField(self.directGetFieldCartesian)
        self.directGetFieldSpherical()

    def setFieldNoWaitSpherical(self, magnitude, azimuthalAngle, polarAngle):
        """Set the magnetic field in spherical coordinates.
        
        Parameters
        ----------
        magnitude : float
            The magnitude of the magnetic field in Tesla.
        azimuthalAngle : float
            The desired azimuthal angle, measured in degrees downward from the
            positive z-axis.
        polarAngle : float
            The desired polar angle, measured in degrees counter-clockwise from
            the positive x-axis.
        """
        with self._lock:
            if self._cartesian:
                self._cartesian = False
                self._field = c2s(*self._field)
            self._fieldSetpoint = [magnitude, azimuthalAngle, polarAngle]
            self._setSphericalFieldNoLock()

    def setFieldSpherical(self, magnitude, azimuthalAngle, polarAngle, block):
        """Set the magnetic field in spherical coordinates.
        
        Parameters
        ----------
        magnitude : float
            The magnitude of the magnetic field in Tesla.
        azimuthalAngle : float
            The desired azimuthal angle, measured in degrees downward from the
            positive z-axis.
        polarAngle : float
            The desired polar angle, measured in degrees counter-clockwise from
            the positive x-axis.
        block : str
            A string, either 'Yes' or 'No', indicating whether to block the
            sequence until the desired field is reached.
        """
        self.setFieldNoWaitSpherical(magnitude, azimuthalAngle, polarAngle)

        if block.lower() == 'yes':
            self.waitForField(self.directGetFieldSpherical)
        self.directGetFieldSpherical()

    def _setSphericalFieldNoLock(self):
        """Command the power supplies to ramp to the spherical setpoints.
        
        Assume that the current field and setpoint are in spherical coordinates
        and convert to Cartesian in local variables (i.e., without changing any
        instance attributes), calculate the appropriate ramp rates, 
        set the ramp rates, and command the supplies to proceed.
        """
        oldField = s2c(*self._field)
        newField = s2c(*self._fieldSetpoint)
        ramps = self._calculateSweepRate(oldField, newField)
        for supply, ramp, field in zip(self._powerSupplies, ramps, newField):
            supply.setSweepRate(ramp)
            supply.setField(field)

    def _calculateSweepRate(self, oldField, newField):
        """Determine the sweep rates to go from one field to another.
        
        Parameters
        ----------
        oldField : list of float
            The old Cartesian field components, in Tesla.
        newField : list of float
            The new Cartesian field components, in Tesla.
        
        Returns
        -------
        list of float
            The field sweep rates for the three power supplies in Tesla/min.
        """
        differences = []
        rampTimes = []
        for oldComp, newComp, maxRamp in zip(oldField, newField,
                                             self._rampLimits):
            fieldDiff = abs(newComp - oldComp)
            rampTimes.append(fieldDiff / (self._rampProportion * maxRamp))
            differences.append(abs(newComp - oldComp))
        rampTime = max(rampTimes)
        realRates = []
        for diff in differences:
            realRates.append(diff / rampTime)
        return realRates

    def pauseField(self):
        """Pause the field sweep."""
        for supply in self._powerSupplies:
            supply.setActivity('0')

    def unpauseField(self):
        """Resume the field sweep."""
        for supply in self._powerSupplies:
            supply.setActivity('1')

    def isFieldAtSetpoint(self):
        """Return whether the fields have reached the setpoints."""
        answer = True
        for field, setpoint in zip(self._field, self._fieldSetpoint):
            if abs(field - setpoint) > 0.00001:
                answer = False
        return answer

    def waitForField(self, readMethod):
        """Wait until the field has reached its target.
        
        Parameters
        ----------
        readMethod : instancemethod
            The method to use to update information about the current fields.
            It should probably be either `directGetFieldCartesian` or
            `directGetFieldSpherical`.
        """
        while not self.isFieldAtSetpoint():
            readMethod()
            sleep(0.2)
            if self._expt.isPaused():
                self.pauseField()
                while self._expt.isPaused():
                    sleep(0.2)
                self.unpauseField()

    def directGetFieldCartesian(self):
        """Get the magnetic field in Cartesian coordinates.
        
        Returns
        -------
        float
            The x-component of the magnetic field.
        float
            The y-component of the magnetic field.
        float
            The z-component of the magnetic field.
        """
        with self._lock:
            newX = self._powerSupplies[0].getField()
            newY = self._powerSupplies[1].getField()
            newZ = self._powerSupplies[2].getField()
            if self._cartesian:
                self._field = [newX, newY, newZ]
                return tuple(self._field)
            else:
                self._field = c2s(newX, newY, newZ, self._fieldSetpoint[0] < 0)
                return (newX, newY, newZ)

    def getFieldCartesian(self):
        """Get the field vector in Cartesian coordinates.
        
        Returns
        -------
        float
            The x-component of the magnetic field vector.
        float
            The y-component of the magnetic field vector.
        float
            The z-component of the magnetic field vector.
        """
        if self._mode == MODE_DIRECT:
            return self.directGetFieldCartesian()
        elif self._cartesian:
            return tuple(self._field)
        return tuple(s2c(*self._field))

    def getField(self):
        """Get the z-component of the magnetic field.
        
        Returns
        -------
        float
            The z-component of the magnetic field in Tesla.
        """
        return self.getFieldCartesian()[2]

    def directGetFieldSpherical(self):
        """Get the magnetic field in Cartesian coordinates.
        
        Returns
        -------
        float
            The magnitude of the magnetic field in Tesla.
        float
            The azimuthal angle of the magnetic field vector, measured in
            degrees down from the positive z-axis.
        float
            The polar angle of the magnetic field vector, measured in
            degrees counter-clockwise from the positive x-axis.
        """
        with self._lock:
            newX = self._powerSupplies[0].getField()
            newY = self._powerSupplies[1].getField()
            newZ = self._powerSupplies[2].getField()
            if self._cartesian:
                self._field = [newX, newY, newZ]
                return tuple(c2s(newX, newY, newZ, self._fieldSetpoint[0] < 0))
            else:
                self._field = c2s(newX, newY, newZ, self._fieldSetpoint[0] < 0)
                return tuple(self._field)

    def getFieldSpherical(self):
        """Get the field vector in spherical coordinates.
        
        Returns
        -------
        float
            The magnitude of the magnetic field vector.
        float
            The azimuthal angle of the magnetic field vector, measured in
            degrees down from the positive z-axis.
        float
            The polar angle of the magnetic field vector, measured in degrees
            counter-clockwise from the positive x-axis.
        """
        if self._mode == MODE_DIRECT:
            return self.directGetFieldSpherical()
        elif self._cartesian:
            return tuple(c2s(self._field[0], self._field[1], self._field[2],
                             self._fieldSetpoint[0] < 0))
        return tuple(self._field)

    def directGetFieldSetpoints(self):
        """Read the (Cartesian) field setpoints from the power supplies.
        
        Returns
        -------
        float
            The magnetic field setpoint in the x-direction in Tesla.
        float
            The magnetic field setpoint in the y-direction in Tesla.
        float
            The magnetic field setpoint in the z-direction in Tesla.
        """
        with self._lock:
            setpointX = self._powerSupplies[0].getFieldSetpoint()
            setpointY = self._powerSupplies[1].getFieldSetpoint()
            setpointZ = self._powerSupplies[2].getFieldSetpoint()
            if self._cartesian:
                self._fieldSetpoint = [setpointX, setpointY, setpointZ]
            else:
                self._fieldSetpoint = c2s(setpointX, setpointY, setpointZ,
                                          self._fieldSetpoint[0] < 0)
        return (setpointX, setpointY, setpointZ)

    def getFieldSetpoints(self):
        """Get the magnetic field setpoints.
        
        Returns
        -------
        float
            The magnetic field setpoint in the x-direction in Tesla.
        float
            The magnetic field setpoint in the y-direction in Tesla.
        float
            The magnetic field setpoint in the z-direction in Tesla.
        """
        if self._mode == MODE_DIRECT:
            return self.directGetFieldSetpoints()
        elif self._cartesian:
            return tuple(self._fieldSetpoint)
        return tuple(s2c(*self._fieldSetpoint))

    def setFieldRampProportion(self, proportion):
        """Set the magnetic field ramp rate proportion.
        
        Parameters
        ----------
        proportion : float
            The ratio of the desired ramp rate to the maximum ramp rate. The
            actual rate used for any given magnet sweep will be such that all
            power supplies reach the target at the same time, limited by the
            power supply with the lowest maximum ramp rate, which will be
            multiplied by `proportion`.
        """
        self._rampProportion = proportion

    def getFieldRampProportion(self):
        """Get the magnetic field ramp rate proportion.
        
        Returns
        -------
        float
            The ratio of the desired ramp rate to the maximum ramp rate. The
            actual rate used for any given magnet sweep will be such that all
            power supplies reach the target at the same time, limited by the
            power supply with the lowest maximum ramp rate, which will be
            multiplied by `proportion`.
        """
        return self._rampProportion

    def directGetFieldRampRates(self):
        """Read the magnetic field sweep rates directly from the power supplies.
        
        Returns
        -------
        float
            The ramp rate for the x-component of the magnetic field in 
            Tesla/min.
        float
            The ramp rate for the y-component of the magnetic field in 
            Tesla/min.
        float
            The ramp rate for the z-component of the magnetic field in 
            Tesla/min.
        """
        ans = []
        for supply in self._powerSupplies:
            ans.append(supply.getSweepRate())
        return tuple(ans)

    def getFieldRampRates(self):
        """Get the magnetic field ramp rates.
        
        Returns
        -------
        float
            The ramp rate for the x-component of the magnetic field in 
            Tesla/min.
        float
            The ramp rate for the y-component of the magnetic field in 
            Tesla/min.
        float
            The ramp rate for the z-component of the magnetic field in 
            Tesla/min.
        """
        if self._mode == MODE_DIRECT:
            return self.directGetFieldRampRates()
        answer = []
        for rate in self._rampLimits:
            answer.append(self._rampProportion * rate)
        return tuple(answer)


    #===========================================================================
    # Temperature
    #===========================================================================

    def _auxReadTemp(self, sensorData):
        """Return the temperature measured by the specified sensor.
        
        Acquire the lock, read the temperature from the relevant controller,
        update the temperature in the vector magnet's dictionary, and return
        the temperature.
        
        Parameters
        ----------
        sensorData : dict
            A dictionary indicating the sensor from which to read. It must have
            an `ITC503` object under the heading 'itc' and a sensor index
            string ('1', '2', or '3') under the key 'sensor'.
        
        Returns
        -------
        float
            The temperature measured by the specified sensor in Kelvin.
        """
        with self._lock:
            temp = sensorData['itc'].getTemperature(sensorData['sensor'])
            self._temperatures['label'] = temp
        return temp

    def _auxReadSetpointAndPID(self, tempController):
        """Return the setpoint and PID values for the temperature controller.
        
        Acquire the lock and read the setpoint and the PID values from the
        ITC.
                
        Parameters
        ----------
        tempController : ITC503
            The Oxford ITC 503 from which to read the requested data.
                    
        Returns
        -------
        float
            The setpoint for the active sensor on the controller.
        float
            The proportional band value for the controller.
        float
            The integral action time for the controller.
        float
            The derivative action time for the controller.
        """
        with self._lock:
            setpoint = tempController.getSetpoint()
            pid = tempController.getPID()
        return (setpoint, pid[0], pid[1], pid[2])

    def directGetTemperatureHe3(self):
        """Read the He3 pot temperature from the temperature controller.
        
        Returns
        -------
        float
            The temperature of the He3 pot.
        """
        maxLowTemp = self._heLow['max_temp']
        lowTemp = self._auxReadTemp(self._heLow)
        if lowTemp <= maxLowTemp:
            self._temperatures['He3 Pot'] = lowTemp
            return lowTemp
        highTemp = self._auxReadTemp(self._heHigh)
        self._temperatures['He3 Pot'] = highTemp
        return highTemp

    def directGetTemperatureSorb(self):
        """Read the sorb temperature from the temperature controller.
        
        Returns
        -------
        float
            The temperature of the sorb.
        """
        return self._auxReadTemp(self._heSorb)

    def directGetTemperatureHeatSwitch(self):
        """Read the heat switch temperature from the temperature controller.
        
        Returns
        -------
        float
            The temperature of the heat switch.
        """
        return self._auxReadTemp(self._heatSwitch)

    def directGetTemperaturePT1Plate(self):
        """Read the PT 1 plate temperature from the temperature controller.
        
        Returns
        -------
        float
            The temperature of the PT1 plate.
        """
        return self._auxReadTemp(self._pt1)

    def directGetTemperaturePT2Plate(self):
        """Read the PT 2 plate temperature from the temperature controller.
        
        Returns
        -------
        float
            The temperature of PT 2 plate.
        """
        return self._auxReadTemp(self._pt2)

    def directGetTemperatureIntPlate(self):
        """Read the intermediate plate temperature from the controller.
        
        Returns
        -------
        float
            The temperature of the intermediate plate.
        """
        return self._auxReadTemp(self._int)

    def directGetTemperatureMagnet(self):
        """Read the magnet temperature from the temperature controller.
        
        Returns
        -------
        float
            The temperature of the magnet plate.
        """
        return self._auxReadTemp(self._mag)

    def directGetHe3SetpointAndPid(self):
        """Read the He3 temperature setpoint and PID values from the controller.
        
        Returns
        -------
        float
            The setpoint for the He3 pot.
        float
            The proportional band value for the controller.
        float
            The integral action time for the controller.
        float
            The derivative action time for the controller.
        """
        low = self._heLow
        high = self._heHigh
        if (low['itc'].getHeaterSensor() == low['sensor'] and
            low['itc'].getAutoStatus()[0]):
            return self._auxReadSetpointAndPID(low['itc'])
        elif (high['itc'].getHeaterSensor() == high['sensor'] and
              high['itc'].getAutoStatus()[0]):
            return self._auxReadSetpointAndPID(high['itc'])
        return (0.0, 0.0, 0.0, 0.0)

    def procedureCooldown(self):
        """Perform the system initial cooldown sequence."""

        # Turn off power to all heaters
        with self._lock:
            for sensor in (self._heSorb, self._heHigh, self._heLow, self._pt1,
                           self._heatSwitch):
                sensor['itc'].setAutoStatus(False, False)
                sensor['itc'].setTemperature(0.0)
                sensor['itc'].setHeaterOutput(0.0)

        # Pre-cool: PT2 heater on, Valve V1 open
        with self._lock:
            _auxToggleHeater(self._pt2, True)
            self._valve.openValve()

        # Pre-cool: Wait for final He3 temp
        targetTemp = self._ctrlCool['precool_final_he3_temp']
        currentTemp = self._auxReadTemp(self._heHigh)
        while targetTemp <= currentTemp:
            currentTemp = self._auxReadTemp(self._heHigh)
            sleep(0.5)

        # Pre-cool: PT2 heater off
        with self._lock:
            _auxToggleHeater(self._pt2, False)

        # Open V1, close heat switch
        with self._lock:
            _auxToggleHeater(self._heatSwitch, True)
            self._valve.openValve()

        # Turn on compressor
        # FIXME: Send a message

        # Wait for He3 to stabilize with sorb < target
        sorbTarget = self._ctrlCool['sorb_target']
        timer = StabilityTrend(120, self._ctrlCool['he3_stability_initial'])
        while not (timer.isFinished() and
                   self.directGetTemperatureSorb() < sorbTarget):
            timer.addPoint(self.directGetTemperatureHe3())
            sleep(0.5)
        del timer

        # Close V1
        with self._lock:
            self._valve.closeValve()

        # Open heat switch
        with self._lock:
            _auxToggleHeater(self._heatSwitch, False)

        # Wait for heat switch to open
        targetTemp = self._heatSwitch['off_temp']
        currentTemp = self.directGetTemperatureHeatSwitch()
        while currentTemp >= targetTemp:
            currentTemp = self.directGetTemperatureHeatSwitch()
            sleep(0.5)

        # Ramp sorb to condense temperature
        with self._lock:
            _auxSetSetpointAndPID(self._heSorb,
                                       self._ctrlCon['sorb_setpoint'])

        # Wait for the He3 pot to start cooling
        self._waitForHe3PotToStartCooling()

        # Wait for He3 pot to get below 5K
        currTemp = self.directGetTemperatureHe3()
        while currTemp >= 5.0:
            currTemp = self.directGetTemperatureHe3()
            sleep(0.5)

    def _waitForHe3PotToStartCooling(self):
        """Wait for the He3 pot to start cooling."""
        startTime = downTime = currTime = time()
        timeout = 1800.0
        duration = 120.0
        times = []
        vals = []
        while currTime - downTime < duration and currTime - startTime < timeout:
            currTime = time()
            times.append(currTime)
            currTemp = self.directGetTemperatureHe3()
            vals.append(currTemp)
            if simpleLinearRegression(times, vals)[0] > -0.00001:
                downTime = currTime
                times = [currTime]
                vals = [currTemp]
            sleep(1.0)

    def procedurePrecondense(self):
        """Prepare to condense the helium."""

        # Turn the sorb off, turn the heat switch on, and open V1
        with self._lock:
            self._valve.openValve()
            _auxSetSetpointAndPID(self._heSorb, 0.0, False, False)
            _auxToggleHeater(self._heatSwitch, True)

        # Delay
        delay = 600.0
        startTime = currTime = time()
        while currTime - startTime < delay:
            currTime = time()
            sleep(1.0)

        # Wait for the sorb to fall below its target
        target = self._ctrlPrecon['sorb_target']
        currTemp = self.directGetTemperatureSorb()
        while currTemp > target:
            currTemp = self.directGetTemperatureSorb()
            sleep(0.5)

        # Delay
        delay = self._ctrlPrecon['delay']
        startTime = currTime = time()
        while currTime - startTime < delay:
            currTime = time()
            sleep(1.0)

        # Close V1
        with self._lock:
            self._valve.closeValve()

    def procedureCondense(self):
        """Condense the He3."""

        # Close V1, turn off heat switch, and turn off sorb power
        with self._lock:
            self._valve.closeValve()
            _auxToggleHeater(self._heatSwitch, False)
            _auxSetSetpointAndPID(self._heSorb, 0.0, False, False)

        # Wait for heat switch to turn off
        tempOff = self._heatSwitch['off_temp']
        currTemp = self.directGetTemperatureHeatSwitch()
        while currTemp >= tempOff:
            currTemp = self.directGetTemperatureHeatSwitch()
            sleep(0.5)

        # Warm sorb to intermediate temperature
        sweepStart = self._ctrlCon['sorb_sweep_start']
        with self._lock:
            _auxSetSetpointAndPID(self._heSorb, sweepStart)

        # Delay
        _generalDelay(1200.0)

        # Warm sorb to final sweep temperature
        self._condenseWarmSorbToFinalRampTemp()

        # Warm sorb to final condense temp
        with self._lock:
            _auxSetSetpointAndPID(self._heSorb,
                                       self._ctrlCon['sorb_setpoint'])

        # Delay
        _generalDelay(1200.0)

        # Wait for He3 pot to start cooling, waiting at least 3 min
        minTime = 180.0
        startTime = currTime = time()
        timer = StabilityTrend(120, 0.0)
        while (currTime - startTime < minTime or not timer.isBufferFull() or
               timer.getTrend() > 0.0):
            newTemp = self.directGetTemperatureHe3()
            timer.addPoint(newTemp)
            sleep(1.0)
        del timer

        # Wait for He3 to stabilize
        minTime = 600.0
        stability = self._ctrlCon['he3_stability']
        absStability = abs(stability)
        startTime = currTime = time()
        timer = StabilityTrend(120, stability)
        finished = False
        while not finished:
            runTime = currTime - startTime
            newValue = self.directGetTemperatureHe3()
            timer.addPoint(newValue)
            slope = timer.getTrend()
            if (runTime >= minTime and slope <= 0 and
                abs(slope * 60.0) < absStability and timer.isStable()):
                finished = True
            sleep(1.0)
        del timer

        # Delay
        _generalDelay(self._ctrlCon['delay'])

        # Turn off sorb heater
        with self._lock:
            _auxSetSetpointAndPID(self._heSorb, 0.0, False, False)

        # Wait for 1 min
        sleep(60.0)

        # Open valve V1
        with self._lock:
            self._valve.openValve()

        # Wait for some time after valve opened
        _generalDelay(self._ctrlCon['v1_open_time'])

        # Close V1, close heat switch
        with self._lock:
            self._valve.closeValve()
            _auxToggleHeater(self._heatSwitch, True)

    def _condenseWarmSorbToFinalRampTemp(self):
        """Warm the sorb to its final condensation temperature."""
        sweep = self._heSorb['sweep']
        finalTemp = self._ctrlCon['sorb_sweep_end']
        if sweep:
            startTemp = self.directGetTemperatureSorb()
            sweepRate = self._heSorb['sweep_rate'] / 60.0
            sweepRate = abs(sweepRate) * ((finalTemp - startTemp) /
                                          abs(finalTemp - startTemp))
            finished = False
            startTime = time()
            while not finished:
                currTime = time()
                nextTemp = startTemp + (currTime - startTime) * sweepRate
                if finalTemp > startTemp and nextTemp > finalTemp:
                    nextTemp = finalTemp
                    finished = True
                elif finalTemp < startTemp and nextTemp < finalTemp:
                    nextTemp = finalTemp
                    finished = True
                with self._lock:
                    _auxSetSetpointAndPID(self._heSorb, nextTemp)
                sleep(0.25)
        else:
            with self._lock:
                _auxSetSetpointAndPID(self._heSorb, finalTemp)

    def procedureRecondense(self):
        """Recondense the cryostat."""
        self.procedurePrecondense()
        self.procedureCondense()

    def procedureSetTemp(self, target):
        """Enter a temperature setpoint.
        
        Parameters
        ----------
        target : float
            The desired temperature for the He3 pot in Kelvin.
        """
        upperTemp = self._ctrlTemp['he3_upper_temp']
        check = upperTemp > target
        with self._lock:
            if check:
                self._valve.closeValve()
            if check and self._ctrlTemp['he3_low_lim_low_hs_tset'] < target:
                _auxSetSetpointAndPID(self._heatSwitch,
                                           self._ctrlTemp['low_hs_tset'])
            else:
                _auxToggleHeater(self._heatSwitch, check)

            if check:
                ctrl = self._heLow
            else:
                ctrl = self._heHigh

            _auxSetSetpointAndPID(ctrl, target, target < 1e-6, True, True)

    def procedureRunToTemp(self, target):
        """Run the cryostat to the desired temperature.
        
        Parameters
        ----------
        target : float
            The desired temperature for the He3 pot in Kelvin.
        """

        # Enter the setpoint
        self.procedureSetTemp(target)

        # Wait for stability
        if target < 1E-5:
            timer = StabilityTrend(180, 0.005, 115200.0)
            while not timer.isFinished():
                newTemp = self.directGetTemperatureHe3()
                timer.addPoint(newTemp)
                sleep(1.0)
        else:
            stabilityTable = self._ctrlTemp['stability_table']
            maxDeviation = searchStabilityTable(target, stabilityTable)
            timer = StabilitySetpoint(180, target, maxDeviation, 7200.0)
            while not timer.isFinished():
                newTemp = self.directGetTemperatureHe3()
                timer.addPoint(newTemp)
                sleep(1.0)
        del timer

        # Delay
        delay = self._ctrlTemp['delay_before_stable']
        startTime = currTime = time()
        while currTime - startTime < delay:
            currTime = time()
            sleep(1.0)

    def getTemperature(self):
        """Return the temperature of the He3 pot.
        
        Returns
        -------
        float
            The temperature of the He3 pot in Kelvin.
        """
        return self.directGetTemperatureHe3()

    def setTemperature(self, temp):
        """Set the temperature for the He3 pot.
        
        Parameters
        ----------
        temp : float
            The desired temperature for the He3 pot in Kelvin.
        """
        currTemp = self.directGetTemperatureHe3()
        cutoff = self._ctrlTemp['he3_upper_temp']

        if temp < currTemp - 25:
            self.procedureCooldown()
        if temp < currTemp and currTemp > cutoff and temp < cutoff:
            self.procedureRecondense()
        self.procedureRunToTemp(temp)

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
    
    
class VectorMagnetController(inst.Controller):
    """A tool for monitoring and controlling the VectorMagnet status."""
    
    def __init__(self, experiment, vectorMagnet):
        """Instantiate a VectorMagnet monitor."""
        super(VectorMagnetController, self).__init__()
        self.setDaemon(True)
        self._expt = experiment
        self._vecmag = vectorMagnet

        self._continue = True
        self._running = False
        
        self._data = {}
        
        self._commands = []
        
    def run(self):
        """Start updating the monitor and listening for commands."""
        self._running = True
        vecmag = self._vecmag
        while self._continue:
            self._data = {'field': vecmag.directGetFieldCartesian(),
                          'setpoint': vecmag.getFieldSetpoints(),
                          'ramp': vecmag.getFieldRampProportion(),
                          'temps': [vecmag.directGetTemperatureIntPlate(),
                                    vecmag.directGetTemperatureMagnet,
                                    vecmag.directGetTemperatureSorb(),
                                    vecmag.directGetTemperaturePT2(),
                                    vecmag.directGetTemperaturePT1(),
                                    vecmag.directGetTemperatureHeatSwitch()],
                          'sample_temp': vecmag.directGetTemperatureHe3()}
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
            - 'ramp'
            - 'temps'
            - 'sample_temp'
        
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
        
    def setFieldX(self, field):
        """Set the magnetic field in the x direction.
         
        Parameters
        ----------
        field : float
            The desired x-component of the magnetic field in Tesla.
        """
        self._vecmag.setFieldX(field, 'no')
        
    def setFieldY(self, field):
        """Set the magnetic field in the y direction.
         
        Parameters
        ----------
        field : float
            The desired y-component of the magnetic field in Tesla.
        """
        self._vecmag.setFieldY(field, 'no')
        
    def setFieldZ(self, field):
        """Set the magnetic field in the z direction.
         
        Parameters
        ----------
        field : float
            The desired z-component of the magnetic field in Tesla.
        """
        self._vecmag.setFieldZ(field, 'no')
         
    def setFieldRampProportion(self, ramp):
        """Set the magnetic field ramp rate.
         
        Parameters
        ----------
        ramp : float
            The desired magnetic field ramp rate as a fraction of the power
            supplies' maximum ramp rate.
        """
        self._vecmag.setFieldRampProportion(ramp)
 
    def setTemperature(self, temperature):
        """Set the sample temperature using the automatic algorithm.
         
        Parameters
        ----------
        temperature : float
            The desired sample temperature in Kelvin.
        """
        self._vecmag.setTemperature(temperature)

    @classmethod
    def getInstrumentClassName(cls):
        """Return the instrument class managed by this controller."""
        return 'VectorMagnet'
    
    @classmethod
    def isSingleton(cls):
        """Return whether at most one instance of the controller may exist.
        
        Returns
        -------
        bool
            Whether only zero or one instance of the controller may exist.
        """
        return True
    
    
#-------------------------------------------------------------- Helper functions

def _auxToggleHeater(dev, heaterOn=True):
    """Turn the PT2 or heat switch heater on or off.
    
    Note that if the heater is off, this creates an "open thermal circuit",
    so there is no thermal contact.
    
    This method does **not** acquire the lock.
    
    Parameters
    ----------
    dev : dict
        A dictionary of configuration parameters for the heater to toggle. 
        It should probably be either _pt2 or _heatSwitch.
    heaterOn : bool
        Whether the heater should be turned on. If `False`, the heater
        will be turned off.
    """
    _auxSetSetpointAndPID(dev, dev['setpoint_on'], heaterOn, False)

def _auxSetSetpointAndPID(dev, setpoint, heaterOn=True,
                          checkAutoPID=True, forcePID=False):
    """Set the temperature setpoint and PID values.
    
    Set the setpoint and the PID values for the sensor specified by
    `dev`, which should be a dictionary which specifies the ITC503
    to use, the channel of the appropriate sensor, and either individual
    PID values (i.e. the keys 'p', 'i', and 'd') or a table of PID values
    specified as a list of tuples, where the elements of each tuple are,
    in order, the upper temperature bound for the specified sensor, P, I,
    and D.
    
    This method does **not** acquire the lock.
    
    Parameters
    ----------
    dev : dict
        The sensor configuration dictionary.
    setpoint : float
        The desired temperature setpoint in Kelvin.
    heaterOn : bool
        Whether to turn the heater on. If `False`, the heater will be
        turned off. It should be set to `False` only for items which
        control a thermal link (e.g. the PT2 plate and the switch heater),
        and then only if the heater is to be turned off, causing thermal
        isolation. The default is `True`.
    checkAutoPID : bool
        Whether to make sure auto-PID is disabled before setting the PID
        values. The default is `True`.
    forcePID : bool
        Whether the PID values should be set regardless of the value of
        `heaterOn`.
    """
    devitc = dev['itc']
    if 'pid_table' in dev:
        foundPID, newPID = searchPIDTable(setpoint, dev['pid_table'])
    else:
        try:
            newPID = (dev['p'], dev['i'], dev['d'])
            foundPID = True
        except KeyError:
            newPID = (0, 0, 0)
            foundPID = False
    if checkAutoPID and devitc.getAutoPID():
        foundPID = False

    channelChanged = False
    if not (devitc.getAutoStatus()[0] and
            devitc.getHeaterSensor() == dev['sensor']):
        devitc.setAutoStatus(False, False)
        devitc.setHeaterSensor(dev['sensor'])
        if 'heater_limit' in dev:
            devitc.setMaximumHeaterVoltage(dev['heater_limit'])
        channelChanged = True

    if heaterOn:
        devitc.setTemperature(setpoint)
        if foundPID:
            devitc.setPID(*newPID)
        if channelChanged:
            devitc.setAutoStatus(True, False)
    elif forcePID and foundPID:
        devitc.setPID(*newPID)
    else:
        devitc.setAutoStatus(False, False)
        devitc.setHeaterOutput(0.0)
        devitc.setTemperature(0.0)


def _generalDelay(delayTime, sleepTime=1.0):
    """Wait for a specified amount of time.
    
    Parameters
    ----------
    delayTime : float
        The total time to wait, in seconds.
    sleepTime : float
        The time to sleep between checks, in seconds. This is so that
        (1) the software can periodically update status information and (2)
        the software can respond to user-generated "skip" events.
    """
    startTime = currTime = time()
    while currTime - startTime < delayTime:
        currTime = time()
        sleep(sleepTime)

def searchPIDTable(targetTemp, pidTable):
    """Return the PID values appropriate for a specified setpoint.
    
    Parameters
    ----------
    targetTemp : float
        The setpoint for which PID values are desired.
    pidTable : list of tuple of float
        The PID table for the appropriate sensor. Each tuple should consist
        of four values: the largest temperature for which the row applies
        and the values of the P, I, and D control terms.
        
    Returns
    -------
    bool
        Whether the supplied PID table contains a row suitable for the 
        specified setpoint.
    tuple of float
        The PID values appropriate for the specified setpoint if such values
        are contained in the table. Otherwise, the PID values associated
        with the largest upper-bound temperature in the table.
    """

    for upper, pVal, iVal, dVal in pidTable:
        if upper >= targetTemp:
            return (True, (pVal, iVal, dVal))
    return (False, tuple(pidTable[-1][1:]))

def searchStabilityTable(targetTemp, stabilityTable):
    """Return the allowed deviation for the specified setpoint.
    
    Parameters
    ----------
    targetTemp : float
        The desired temperature setpoint in Kelvin.
    stabilityTable : list of tuple
        A list of tuples, where each tuple contains three elements: a float
        indicating the maximum temperature for which the row is applicable,
        a float indicating the maximum deviation, and a string indicating how
        the maximum deviation should be interpreted. If the string is 'value',
        the deviation will be interpreted as an absolute value; otherwise, it
        will be interpreted as a fraction of the setpoint.
    
    Returns
    -------
    float
        The maximum deviation from the setpoint a system can exhibit while
        still be considered stable. 
    """
    ans = stabilityTable[-1][1:]
    for upper, dev, kind in stabilityTable:
        if upper >= targetTemp:
            ans = [dev, kind]

    dev, kind = ans
    if kind == 'value':
        return dev
    return dev * targetTemp
