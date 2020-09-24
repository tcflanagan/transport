"""Basic drivers for an Oxford Instruments model ITC503 temperature controller

Note that this module does **not** represent an `Instrument` subclass, since
the ITC503 is never used by itself---it is always part of a larger system 
driving both a magnet power supply and temperature controllers, and the
temperature controller cannot usually be used in isolation.
"""

from src.instruments.noauto.oxford_common import OxfordCommon

class ITC503(OxfordCommon):
    """An Oxford Instruments ITC
    
    This is a basic driver for an Oxford Instruments ITC503 (Intelligent
    Temperature Controller). It should typically be included in an `Instrument`
    class representing a cryostat-magnet system.

    Parameters
    ----------
    name : str
        A name to identify the instrument.
    protocol : {'ISOBUS', 'GPIB', 'Serial', 'Gateway Master', 'Gateway Slave'}
        The protocol for communication between the computer and the temperature
        controller.
    isobusAddress : str
        An integer string representing the ISOBUS address, if relevant. An
        integer will be accepted and converted.
    visaAddress : str
        A full VISA resource address (including the bus) to locate the 
        instrument (e.g. "GPIB0::27").
    serialConfig : dict
        A dictionary to indicate how to configure a serial port, which is used
        with both the 'ISOBUS' and 'Serial' protocols.
    """
        
    def __init__(self, name="Temperatures", protocol='ISOBUS', isobusAddress=0, 
                 visaAddress='GPIB0::23', serialConfig=None):
        """Create a new temperature controller instance.
        
        Initialization for this object really only involves passing all
        arguments into the `OxfordCommon` superclass.
        """
         
        super(ITC503, self).__init__(name, protocol, isobusAddress,
                                     visaAddress, serialConfig)
        
        self._controlMode = '0'
        self._autoPID = '0'
        self._heaterSensor = '1'
        self._autoStatus = (False, False)
    
    def initialize(self):
        """Prepare the temperature controller for use.
        
        Prepare the temperature controller for use by 
            1. opening the appropriate communication channel;
            2. setting the control mode to 'remote and unlocked';
            3. setting the auto/manual status to full auto;
            4. get the currently set PID values;
            5. get the current temperature readings from all sensors; and
            6. read the status.
        """
        super(ITC503, self).initialize()
        self.setControlMode()
        self.setAutoStatus()
        self.getPID()
        self.getTemperatures()
        self._readStatus()
        
    def _readStatus(self):
        """Read the temperature controller status.
        
        Returns
        -------
        dict
            A dictionary specifying the status of the temperature controller.
            It includes the following keys: 'autoManualStatus', 'controlMode',
            'sweepStatus', 'sensor', and 'autoPID'. The meanings are 
            specified in the Notes section.
        
        Notes
        -----
        The temperature controller returns a string of the form 
        ``XnAnCnSnnHnLn``. The meanings and values of the parts of this are 
        described here.
        
        ``Xn``: System status
            Currently always zero
        ``An``: Auto/Manual status
            - 0: Heater manual, gas manual
            - 1: Heater auto, gas manual
            - 2: Heater manual, gas auto
            - 3: Heater auto, gas auto
        ``Cn``: Control status
            - 0: Local and locked
            - 1: Remote and locked
            - 2: Local and unlocked
            - 3: Remote and unlocked
        ``Snn``: Sweep status
            - nn=0: Sweep not running
            - nn=2P-1: Sweeping to step P
            - nn=2P: Holding at step P
        ``Hn``: Control sensor
            - 1: Sensor 1
            - 2: Sensor 2
            - 3: Sensor 3
        ``Ln``: Auto-PID status
            - 0: Disable use of auto-PID
            - 1: Enable use of auto-PID
        """
        status = self.communicate('X')
        if status[3] == '0':
            self._autoStatus = (False, False)
        elif status[3] == '1':
            self._autoStatus = (True, False)
        elif status[3] == '2':
            self._autoStatus = (False, True)
        else:
            self._autoStatus = (True, True)
        self._controlMode = status[5]
        self._heaterSensor = status[10]
        self._autoPID = status[12]
        
    def setControlMode(self, controlMode='3'):
        """Set the control mode for the temperature controller.
        
        Parameters
        ----------
        controlMode : str, optional
            An integer string representing the desired control mode. Allowed
            values are the following.
                - '0': Local and locked (power-up state).
                - '1': Remote and locked.
                - '2': Local and unlocked.
                - '3': Remote and unlocked (default).
        """
        self.communicate('C' + controlMode)
        self._controlMode = controlMode
        
    def getAutoStatus(self):
        """Return whether the heater and needle valve are in automatic mode.
        
        Returns
        -------
        bool
            Whether the heater is in automatic mode.
        bool
            Whether the needle valve (gas controller) is in automatic mode.
        """
        return self._autoStatus
    
    def setAutoStatus(self, heater=True, needleValve=True):#status='3'):
        """Set the auto/manual status of the heater and gas controller.
        
        Parameters
        ----------
        heater : bool
            Whether the temperature controller's heater should be placed in
            automatic mode. If `False`, the heater will be placed in manual
            mode.
        needleValve : bool
            Whether the temperature controller's needle valve (gas flow
            controller) should be placed in automatic mode. If `False`, the
            needle valve will be placed in manual mode.
        """
        if heater == False and needleValve == False:
            status = '0'
        elif heater == True and needleValve == False:
            status = '1'
        elif heater == False and needleValve == True:
            status = '2'
        else:
            status = '3'
        self.communicate('A' + status)
        self._autoStatus = (heater, needleValve)
    
    def setP(self, newP):
        """Set the PID values for the temperature controller.
        
        Parameters
        ----------
        newP : float
            The proportional band in Kelvin, to a resolution of 0.001 K.
        """
        self.communicate('P%.3f' % newP)
            
    def setI(self, newI):
        """Set the PID values for the temperature controller.
        
        Parameters
        ----------
        newI : float
            The integral action time in minutes. Values between 0 and
            140 minutes (inclusive), in steps of 0.1 minutes, are accepted.
        """
        self.communicate('I%.1f' % newI)
        
    def setD(self, newD):
        """Set the PID values for the temperature controller.
        
        Parameters
        ----------
        newD : float
            The derivative action time in minutes. The allowed range is
            0 to 273 minutes.
        """
        self.communicate('D%.1f' % newD)
        
    def setPID(self, newP=None, newI=None, newD=None):
        """Set the PID values for the temperature controller.
        
        Parameters
        ----------
        newP : float, optional
            The proportional band in Kelvin, to a resolution of 0.001 K.
        newI : float, optional
            The integral action time in minutes. Values between 0 and
            140 minutes (inclusive), in steps of 0.1 minutes, are accepted.
        newD : float, optional
            The derivative action time in minutes. The allowed range is
            0 to 273 minutes.
        """
        self.communicate('P%.3f' % newP)
        self.communicate('I%.1f' % newI)
        self.communicate('D%.1f' % newD)
        
    def getHeaterSensor(self):
        """Return which sensor is currently active.
        
        Returns
        -------
        str
            An integer string, '1', '2', or '3', indicating which sensor is
            currently being used to control the temperature(s).
        """
        return self._heaterSensor
    
    def setHeaterSensor(self, sensor='1'):
        """Set the active temperature sensor.
        
        Parameters
        ----------
        sensor : str
            An integer string representing the sensor to activate. Allowed
            values are '1', '2', and '3', the meanings of which should be
            obvious.
        """
        self.communicate('H' + sensor)
        self._heaterSensor = sensor

    def toggleAutoPid(self, autoPID='0'):
        """Set the auto-PID status of the temperature controller.
        
        If a PID table has been programmed into the instrument, you can enable
        auto-PID, so that the PID values will be automatically chosen based
        on the temperature range.
        
        .. warning:: If a PID table has not been programmed, attempting to 
           enable auto-PID will return an error.
           
        Parameters
        ----------
        autoPID : str
            An integer string representing the desired auto-PID status. The
            allowed values are below.
                - 0: Disable auto-PID
                - 1: Enable auto-PID
            This method also accepts a boolean value for `autoPID`, and this
            value would be interpreted in the obvious way.
        """
        
        if isinstance(autoPID, bool):
            if autoPID:
                autoPID = '1'
            else:
                autoPID = '0'
        self.communicate('L' + autoPID)
        self._autoPID = autoPID
        
    def getAutoPID(self):
        """Return whether auto-PID is enabled.
        
        Returns
        -------
        bool
            Whether the ITC is configured for auto-PID.
        """
        return self._autoPID == '1'
        
    def setTemperature(self, temperature):
        """Set the target temperature for the controller.
        
        Set the target temperature for the currently-selected sensor to
        `temperature`, and begin moving toward the setpoint.
        
        .. note:: If a sweep is in progress, the sweep will override the value
           set by this command.
        
        Parameters
        ----------
        temperature : float
            The temperature setpoint for the currently-enabled sensor.
        """
        self.communicate('T%.4s' % temperature)
        
    def setMaximumHeaterVoltage(self, voltage):
        """Set the maximum voltage for the currently controlled heater.
        
        Parameters
        ----------
        voltage : float
            The largest voltage allowed to be supplied to the heater.
        """
        self.communicate('M%d' % (voltage * 10))
    
    def getPID(self):
        """Get the PID values for the temperature controller.
        
        Return the values for the proportional band, the integral action time,
        and the derivative action time which the temperature controller is
        currently using.
        
        Returns
        -------
        tuple of float
            A tuple of floats containing, in order, P, I, and D.
        """
        return (float(self.communicate('R8')),
                float(self.communicate('R9')),
                float(self.communicate('R10')))
    
    def getSetpoint(self):
        """Read the setpoint temperature.
        
        Returns
        -------
        float
            The setpoint temperature in Kelvin.
        """
        return float(self.communicate('R0'))
        
    def getTemperature(self, sensor):
        """Get the temperature measured by the specified sensor.
        
        Parameters
        ----------
        sensor : {'1', '2', '3'}
            An integer string representing the temperature sensor from which
            to read.
        
        Returns
        -------
        float
            The temperature measured by the specified sensor in Kelvin.
        """
        return float(self.communicate('R' + sensor))
    
    def getTemperatures(self):
        """Get the readings from all three temperature sensors.
        
        Returns
        -------
        tuple of float
            The temperatures measured by sensors 1, 2, and 3, expressed as
            floats in a tuple with the obvious order.
        """
        return (float(self.communicate('R1')),
                float(self.communicate('R2')),
                float(self.communicate('R3')))

    def setHeaterOutput(self, output):
        """Set the output for the selected heater.
        
        Parameters
        ----------
        output : float
            The desired heater output as a percent of the maximum range.
        """
        self.communicate('O%f' % output)
