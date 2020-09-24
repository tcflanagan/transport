"""Controller for an oxford valve."""

from src.instruments.noauto.oxford_common import OxfordCommon

class OxfordValve (OxfordCommon):
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
    normallyClosed : bool
        Whether the valve is normally closed. `False` means the valve is
        normally open.
        
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
    
    def __init__(self, name='Valve', protocol='ISOBUS', isobusAddress='0', 
                 visaAddress='GPIB0::23', serialConfig=None, 
                 present=True, normallyClosed=True, channel='1'):
        
        super(OxfordValve, self).__init__(name, protocol, isobusAddress,
                                          visaAddress, serialConfig)
        self._present = present
        self._channel = '%d' % int(channel)
        if normallyClosed:
            self._openCommand = 'S' + self._channel + '1'
            self._closeCommand = 'S' + self._channel + '0'
            self._openCondition = '1'
        else:
            self._openCommand = 'S' + self._channel + '0'
            self._closeCommand = 'S' + self._channel + '1'
            self._openCondition = '0'
        self._normallyClosed = normallyClosed
    
    def openValve(self):
        """Open the valve."""
        self.communicate(self._openCommand)
        
    def closeValve(self):
        """Close the valve."""
        self.communicate(self._closeCommand)
        
    def getOpen(self):
        """Return whether the valve is open.
        
        Returns
        -------
        bool
            `True` if the valve is open, or `False` if it is closed.
        """
        return self.communicate('R' + self._channel) == self._openCondition
        