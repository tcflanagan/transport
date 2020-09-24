"""Basic drivers for an Oxford Instruments model PS120 power supply

Note that this module does **not** represent an `Instrument` subclass, since
the PS120 is never used by itself---it is always part of a larger system 
driving both a magnet power supply and temperature controllers, and the
power supply cannot usually be used in isolation.
"""

from src.instruments.noauto.oxford_common import OxfordCommon
from math import copysign
from time import sleep

class PS120(OxfordCommon):
    """This is a basic driver for an Oxford Instruments model PS120 power
    supply. It should be included in an `Instrument` class representing a
    cryostat-magnet system.

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
    
    def __init__(self, name="Magnet", protocol='ISOBUS', isobusAddress='0', 
                 visaAddress='GPIB0::23', serialConfig=None):
        """Create a new power supply instance.
        
        Initialization for this object really only involves passing all
        arguments into the `OxfordCommon` superclass.
        """
         
        super(PS120, self).__init__(name, protocol, isobusAddress,
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
            6. setting the sweep mode to its default (Tesla, auto, 
               unaffected); and
            7. setting the switch heater to 'Off, magnet at zero'.
        """
        self.openCommunication()
        
        self.getStatus()
        self.setControlMode()
        self.setActivity()
        self.setPolarity('1')
        self.setSweepRate()
        self.setSweepMode()
        self.setSwitchHeater()
        self.getStatus()

    def getStatus(self):
        """Update the power supply status.
        
        Read the power supply status, and update the local polarity variables
        to reflect this change.
        
        Returns
        -------
        dict
            The status dictionary, containing the following items:
            'system_status_1', 'system_status_2', 'activity', 'control_mode',
            'switch_heater', 'mode_1', 'mode_2', 'polarity_1', and
            'polarity_2'. The meanings are described in the Notes section.
        
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
            - 8: No switch fitted
        ``Mmn``: Mode
            ``m``: Mode 1
                - 0: Amps, Immediate, Fast
                - 1: Tesla, Immediate, Fast
                - 2: Amps, Sweep, Fast
                - 3: Tesla, Sweep, Fast
                - 4: Amps, Immediate, Train
                - 5: Tesla, Immediate, Train
                - 6: Amps, Sweep, Train
                - 7: Tesla, Sweep, Train
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
            ``n``: Polarity 2
                - 0: Output clamped (transition)
                - 1: Forward (verification)
                - 2: Reverse (verification)
                - 4: Output clamped (requested)
                
        The Polarity 1 value actually contains the values of three separate
        polarities: desired, magnet, and commanded (in order). "pos" represents
        forward polarity, and "neg" means reverse polarity. The three values
        are defined to be
            - "desired": the final or target polarity (polarity of the setpoint
              current)
            - "magnet": the polarity of the power supply last time the magnet 
              was left persistent
            - "commanded": the present polarity of the power supply unless the
              output is clamped
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
        
    def getActivity(self):
        """Get the activity status.
        
        Returns
        -------
        str
            An integer contained in a string representing the current 
            activity status. The recognized values are these:
                - 0: Hold at current field, 
                - 1: Ramp the field to the setpoint, 
                - 2: Ramp the field to zero, and
                - 4: Clamp the output.
        """
        self.getStatus()
        return self._activity
    
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
        """
        self.communicate('P' + polarity)
        self.getStatus()
        
    def setSweepMode(self, sweepMode='9'):
        """Set the power supply's sweep mode.
        
        The power supply's sweep mode consists of three parameters:
            Display:
                The instrument's front-panel display units (amps or tesla)
            Mode:
                Either "immediate" or "sweep"; in "immediate" mode, the power
                supply ramps current at its maximum allowed value, while in 
                "sweep" mode, the power supply uses a user-specified sweep rate
            Magnet sweep:
                One of two user-defined sweep profiles: "fast" and "train"; the
                "fast" mode is entered upon power supply startup
        
        Parameters
        ----------
        sweepMode : str, optional
            The integer string code to specify the sweep mode of the power
            supply. The allowed codes are the following.
                - '0': Amps, Immediate, Fast
                - '1': Tesla, Immediate, Fast
                - '2': Amps, Sweep, Fast
                - '3': Tesla, Sweep, Fast
                - '4': Amps, Immediate, Train
                - '5': Tesla, Immediate, Train
                - '6': Amps, Sweep, Train
                - '7': Tesla, Sweep, Train
                - '8': Amps, Auto, Unaffected
                - '9': Tesla, Auto, Unaffected (default)
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
        sleep(delay)
        self.getStatus()

    def setField(self, field):
        """Set the magnetic field in Tesla.
        
        Parameters
        ----------
        field : float
            The magnetic field setpoint in Tesla.
        """
        self.getStatus()
        fieldSign = copysign(1, field)
        fieldMagnitude = int(round(abs(field*1000)))
        currentlyForward = self._polarity2 == '1'
        if fieldSign > 0:
            if currentlyForward: 
                pass
            else: 
                self.setPolarity('1')
        else:
            if currentlyForward: 
                self.setPolarity('2')
            else: 
                pass
        self.communicate('J' + str(fieldMagnitude))
        self.setActivity('1')
        
    def setSweepRate(self, sweepRate=0.5):
        """Set the magnetic field sweep rate in Tesla/min.
        
        Parameters
        ----------
        sweepRate : float, optional
            The desired sweep rate for the magnet in Tesla/min (default 0.5).
        """
        self.communicate('T' + int(round(abs(sweepRate*1000))))
        
    def getField(self):
        """Return the magnetic field in Tesla.
        
        Returns
        -------
        float
            The magnetic field in Tesla.
        """
        self.getStatus()
        field = float(self.communicate('R7'))/1000
        if self._polarity2 == '2':
            return (-1)*field
        return field
    
    def getFieldSetpoint(self):
        """Return the field setpoint in Tesla.
        
        Returns
        -------
        float
            The magnetic field setpoint in Tesla.
        """
        self.getStatus()
        setpointMagnitude = float(self.communicate('R8'))/1000
        if int(self._polarity1) >= 4:
            return (-1)*setpointMagnitude
        return setpointMagnitude
        
    def getSweepRate(self):
        """Return the field sweep rate in Tesla/min.
        
        Returns
        -------
        float
            The magnetic field sweep rate in Tesla/min.
        """
        return float(self.communicate('R9'))/1000
