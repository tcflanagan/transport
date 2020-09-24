"""Basic drivers for an Oxford Instruments model IPS120

Note that this module does **not** represent an `Instrument` subclass, since
the IPS120 is never used by itself---it is always part of a larger system 
driving both a magnet power supply and temperature controllers, and the power 
supply often cannot be used in an isolated way. 
"""

import time

from src.instruments.noauto.oxford_common import OxfordCommon

HEATER_DELAY = 20

class IPS120(OxfordCommon):
    """This is a basic driver for an Oxford Instruments model IPS120 power 
    supply. It should be included in an `Instrument` class representing a
    cryostat-magnet system.

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
    """
    
    def __init__(self, name="Magnet", protocol='ISOBUS', isobusAddress='0', 
                 visaAddress='GPIB0::23', serialConfig=None):
        """Create a new power supply instance.
        
        Initialization for this object really only involves passing all
        arguments into the `OxfordCommon` superclass.
        """
         
        super(IPS120, self).__init__(name, protocol, isobusAddress,
                                     visaAddress, serialConfig)
        self._activity = None
        self._polarity1 = None
        self._polarity2 = None
    
    def initialize(self):
        """Prepare the power supply for use.
        
        Prepare the power supply for use by 
            1. opening the appropriate communication channel;
            2. setting the control mode to 'remote and unlocked';
            3. setting the activity to 'hold';
            4. setting the polarity to 'forward';
            5. setting the sweep rate to 0.5 T/min;
            6. setting the sweep mode to 'Tesla, sweep, fast'; and
            7. setting the switch heater to 'Off, magnet at zero'.
        """
        super(IPS120, self).openCommunication()
        self.setControlMode()
        self.setActivity()
        self.setPolarity('1')
        self.setSweepRate()
        self.setSweepMode()
        self.setSwitchHeater()
        self.getStatus()
        
    def getStatus(self):
        """Update the power supply status.
        
        Read the power supply status, and set the local variables to reflect
        the new status.
        
        Notes
        -----
        The power supply returns a string of the form ``XmnAnCnHnMmnPmn``. The
        meanings and values of the parts of this are described here.
        
        ``Xmn``: System status
            ``m``: Status 1
                - 0: Normal
                - 1: Quenched
                - 2: Over-heated
                - 4: Warming up
                - 8: Fault
            ``n``: Status 2
                - 0: Normal
                - 1: On positive voltage limit
                - 2: On negative voltage limit
                - 4: Outside negative current limit
                - 8: Outside positive current limit 
        ``An``: Activity
            - 0: Hold
            - 1: To setpoint
            - 2: To zero
            - 4: Output clamped
        ``Cn``: Control status
            - 0: Local and locked
            - 1: Remote and locked
            - 2: Local and unlocked
            - 3: Remote and unlocked
            - 4: Auto-run-down
            - 5: Auto-run-down
            - 6: Auto-run-down
            - 7: Auto-run-down
        ``Hn``: Switch heater status
            - 0: Off---magnet at zero (switch closed)
            - 1: On (switch open)
            - 2: Off---magnet at field (switch closed)
            - 5: Heater fault (heater is on, but current is low)
            - 8: No switch fitted
        ``Mmn``: Mode
            ``m``: Mode 1
                - 0: Amps, Fast
                - 1: Tesla, Fast
                - 4: Amps, Slow
                - 5: Tesla, Slow
            ``n``: Mode 2
                - 0: At rest (output constant)
                - 1: Sweeping (output changing)
                - 2: Rate limiting (output changing)
                - 3: Sweeping and rate limiting (output changing)
        ``Pmn``: Polarity
            ``m``: Polarity 1 (see below)
                - 0: pos, pos, pos
                - 1: pos, pos, neg
                - 2: pos, neg, pos
                - 3: pos, neg, neg
                - 4: neg, pos, pos
                - 5: neg, pos, neg
                - 6: neg, neg, pos
                - 7: neg, neg, neg
            ``n``: Polarity 2 (verification flags)
                - 1: Negative contactor closed
                - 2: Positive contactor closed
                - 3: Both contactors open
                - 4: Both contactors closed
        
        .. note:: Unlike with the PS120, with the IPS120, Immediate mode is 
           indicated by Mode 2 returning the value '2' (sweep limiting, but not
           sweeping); it does not have its own flag.
        
        .. note:: For the IPS power supplied, the polarity flags have been
           superceded by signed numbers for currents and fields.
        """
        status = self.communicate('X')
        self._activity = status[4]
        self._polarity1 = status[13]
        self._polarity2 = status[14]
        
        return {'system_status_1': status[1],
                'system status 2': status[2],
                'activity': self._activity,
                'control_mode': status[6],
                'switch_heater': status[8],
                'mode_1': status[10],
                'mode_2': status[11],
                'polarity_1': self._polarity1,
                'polarity_2': self._polarity2}
        
    def setControlMode(self, controlMode='3'):
        """Set the control mode for the power supply.
        
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
        
    def setActivity(self, activity='0'):
        """Set the activity mode of the power supply.
        
        Parameters
        ----------
        activity : str
            An integer string representing the desired activity. The accepted
            values are listed below.
                - '0': Hold at current field (default).
                - '1': Ramp the field to the setpoint.
                - '2': Ramp the field to zero.
                - '4': Clamp the output.
        """
        self.communicate('A' + activity)
        self._activity = activity
    
    def setPolarity(self, polarity='0'):
        """Set the power supply polarity.
        
        Parameters
        ----------
        polarity : str
            A string containing a single integer representing the desired
            polarity (or polarity-changing action). The following values are
            accepted.
                - '0': Do nothing (default).
                - '1': Set the polarity to forward.
                - '2': Set the polarity to reverse.
                - '4': Swap the polarity.
        
        .. note:: This method is included for backward compatibility. The
           polarity has been deprecated in favor of signed numbers for the
           field or current setpoints.
        """
        self.communicate('P' + polarity)
        self.getStatus()
        
    def setSweepMode(self, sweepMode='9'):
        """Set the power supply's sweep mode.
        
        The power supply's sweep mode consists of two parameters:
            Display:
                The instrument's front-panel display units (amps or tesla)
            Magnet sweep rate:
                One of two user-defined sweep profiles: "fast" and "slow"; the
                "fast" mode is entered upon power supply startup. The names have
                no significance, and the actual rates are user-defined 
                variables.
        
        Parameters
        ----------
        sweepMode : str, optional
            The integer string code to specify the sweep mode of the power
            supply. The allowed codes are the following.
                - 0: Amps, Fast
                - 1: Tesla, Fast
                - 4: Amps, Slow
                - 5: Tesla, Slow
                - 8: Amps, Unaffected
                - 9: Tesla, Unaffected
        """
        self.communicate('M' + sweepMode)
        self.getStatus()
        
    def setSwitchHeater(self, heaterStatus='0', delay=20.0):
        """Set the status of the switch heater.
        
        Turn the switch heater on or off, optionally checking whether it is
        safe to do so. Then wait a specified amount of time for the power
        supply to carry out the command.
        
        Parameters
        ----------
        heaterStatus : {'0', '1', '2'}, optional
            An integer string representing the desired switch heater status.
            The following values are accepted.
                - '0': Turn the heater off (default).
                - '1': Turn the heater on if the power supply current and the 
                  magnet current are equal. Otherwise, do nothing.
                - '2': Turn the heater on without checking the currents.
            
        delay : float, optional
            The time to wait (in seconds) after commanding the switch heater to
            adopt the specified status. The value should be *at least* 15s.
        """
        self.communicate('H' + heaterStatus)
        time.sleep(delay)
        self.getStatus()


    def setField(self, field):
        """Set the magnetic field in Tesla.
        
        Parameters
        ----------
        field : float
            The magnetic field setpoint in Tesla.
        """
        self.communicate('J%.4f' % field)
        self.setActivity('1')
        
    def setSweepRate(self, sweepRate=0.5):
        """Set the magnetic field sweep rate in Tesla/min.
        
        Parameters
        ----------
        sweepRate : float, optional
            The desired sweep rate for the magnet in Tesla/min (default 0.5).
        """
        self.communicate('T%.3f' % sweepRate)
        
    def getField(self):
        """Return the magnetic field in Tesla.
        
        Returns
        -------
        float
            The magnetic field in Tesla.
        """
        self.getStatus()
        return float(self.communicate('R7'))
    
    def getFieldSetpoint(self):
        """Return the field setpoint in Tesla.
        
        Returns
        -------
        float
            The magnetic field setpoint.
        """
        self.getStatus()
        return float(self.communicate('R8'))
        
    def getSweepRate(self):
        """Return the field sweep rate in Tesla/min.
        
        Returns
        -------
        float
            The magnetic field sweep rate in Tesla/min.
        """
        return float(self.communicate('R9'))


    
    