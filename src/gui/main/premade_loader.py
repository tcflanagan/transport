"""A loader and filter system for premade experiments.
"""
import imp
import os
import re
import wx

from src.tools import path_tools as pt

class PremadeManager(object):
    """A class for managing and filtering premade experiments."""
    
    def __init__(self):
        self.premades = _loadPremades()
        self.measurementTypes = ['All']
        self.devices = ['All']
        self.voltageModes = ['All']
        self.cryostats = ['All']
        
        for premade in self.premades:
            info = self.premades[premade]
            
            currType = info['measurement_type']
            currCryostat = info['cryostat']
            currVoltage = info['voltage_type']
            currDevices = info['devices']

            for item in currType:
                if item not in self.measurementTypes:
                    self.measurementTypes.append(item)
            for item in currCryostat:
                if item not in self.cryostats:
                    self.cryostats.append(item)
            for item in currVoltage:
                if item not in self.voltageModes:
                    self.voltageModes.append(item)
            if str(currDevices) not in self.devices:
                self.devices.append(str(currDevices))
        
    def getFiltered(self, measurementType, cryostat, voltageMode, devices):
        """Return the items which pass through the filtering parameters.
        
        Any of the parameters may be 'All', in which case that filter
        parameter will not have any effect on the output list. Any input
        which is not 'All' must be in a particular premade's signature
        in order to be returned.
        
        Parameters
        ----------
        measurementType : str
            The measurement type string.
        cryostat : str
            The cryostat name.
        voltageMode : str
            The voltage mode (either 'AC' or 'DC' in most cases)
        devices : str
            An integer string representing the number of devices to measure.
            
        Returns
        -------
        tuple of list
            A two-element tuple. The first element is a list of the names
            of the experiments which match the filter conditions. The second
            element is a list of classes corresponding to the names in the
            first list.
        """
        classes = []
        names = []
        for premadeKey in self.premades:
            premade = self.premades[premadeKey]
            if ((measurementType == 'All' or 
                 measurementType in premade['measurement_type']) and
                (cryostat == 'All' or cryostat in premade['cryostat']) and
                (devices == 'All' or str(premade['devices']) == devices) and
                (voltageMode == 'All' or 
                 voltageMode in premade['voltage_type'])):
                classes.append(premade['class'])
                names.append(premade['name'])
        return (names, classes)
    
    def getStrings(self):
        """Return a list of strings representing possible filter values.
        
        Returns
        -------
        tuple of list of str
            A 4-tuple of lists of strings. The first list contains the
            recognized measurement types. The second contains the names of
            the cryostats. The third contains the valid source voltage modes
            (usually either 'AC' or 'DC' or both) used in the premades.
            The last list contains the numbers of devices which are represented
            in the premades.
        """
        return (list(self.measurementTypes), list(self.cryostats), 
                list(self.voltageModes), list(self.devices))

def constructListBox(parent, sizer, label, items, handler=None):
    """Construct a list box.
    
    Parameters
    ----------
    parent : wxWindow
        The parent or frame which should own the list box.
    sizer : wxSizer
        The sizer into which the list box's panel should go.
    label : str
        The label for the list box's static frame.
    items : list of str
        The strings which should serve as the list box's initial data.
    handler : method
        The method which should be called when the list box's selection
        changes.
        
    Returns
    -------
    wxListBox
        A list box control.
    """
    staticbox = wx.StaticBox(parent, -1, label)
    staticsizer = wx.StaticBoxSizer(staticbox, wx.VERTICAL)
    listbox = wx.ListBox(parent, wx.ID_ANY)
    listbox.SetItems(items)
    if len(items) > 0:
        listbox.SetSelection(0)
    if handler is not None:
        listbox.Bind(wx.EVT_LISTBOX, handler)
    staticsizer.Add(listbox, 1, wx.EXPAND|wx.ALL, 5)
    sizer.Add(staticsizer, 1, wx.EXPAND|wx.ALL, 5)
    return listbox

class PremadeFrame(wx.Dialog):
    """A frame for managing and loading premade experiments.
    
    Parameters
    ----------
    parent : wxWindow
        The panel or frame which owns this frame.
    """
    
    def __init__(self, parent):
        super(PremadeFrame, self).__init__(parent, wx.ID_ANY, 
                                           title='Premade Experiments')
        self.parent = parent
        self.premadeManager = PremadeManager()
        strings = self.premadeManager.getStrings()
        self.names, self.classes = self.premadeManager.getFiltered('All', 'All',
                                                                   'All', 'All')
        self.selectedClass = None
        
        filterpanel = wx.Panel(self)
        filtersizer = wx.BoxSizer(wx.HORIZONTAL)
        filterpanel.SetSizer(filtersizer)
        
        self.typebox = constructListBox(filterpanel, filtersizer, 
                                        'Measurement Type', strings[0],
                                        self._onUpdateFilter)
        self.cryobox = constructListBox(filterpanel, filtersizer,
                                        'Cryostat', strings[1],
                                        self._onUpdateFilter)
        self.voltbox = constructListBox(filterpanel, filtersizer,
                                        'Voltage Mode', strings[2],
                                        self._onUpdateFilter)
        self.sampbox = constructListBox(filterpanel, filtersizer,
                                        'Devices', strings[3],
                                        self._onUpdateFilter)
        
        optionpanel = wx.Panel(self)
        optionsizer = wx.BoxSizer(wx.VERTICAL)
        optionpanel.SetSizer(optionsizer)
        
        self.optionbox = constructListBox(optionpanel, optionsizer,
                                          'Options', self.names,
                                          self._onSelectOption)
        
        buttonpanel = wx.Panel(self)
        buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonpanel.SetSizer(buttonsizer)
        
        self.okButton = wx.Button(buttonpanel, wx.ID_OK, label='OK')
        self.cancelButton = wx.Button(buttonpanel, wx.ID_CANCEL, label='Cancel')
        self.okButton.Bind(wx.EVT_BUTTON, self._onClose)
        self.cancelButton.Bind(wx.EVT_BUTTON, self._onClose)
        buttonsizer.Add(self.cancelButton, 0, wx.ALL, 5)
        buttonsizer.Add(self.okButton, 0, wx.ALL, 5)

        self.Bind(wx.EVT_CLOSE, self._onClose)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(filterpanel, 2, wx.EXPAND, 5)
        sizer.Add(optionpanel, 3, wx.EXPAND, 5)
        sizer.Add(buttonpanel, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        
        self.SetSizerAndFit(sizer)
        self.SetSizeHints(-1, 500)
        
    def _onUpdateFilter(self, event):
        """Update the options to reflect the filters."""
        try:
            measurement = self.typebox.GetStringSelection()
            cryostat = self.cryobox.GetStringSelection()
            voltageMode = self.voltbox.GetStringSelection()
            devices = self.sampbox.GetStringSelection()
        
        
            self.names, self.classes = \
                self.premadeManager.getFiltered(measurement,
                                                cryostat,
                                                voltageMode,
                                                devices)
            self.optionbox.SetItems(self.names)
            if len(self.names) > 0:
                self.optionbox.SetSelection(0)
                self.okButton.Enable(True)
        except wx.PyDeadObjectError:
            pass
        
    def _onSelectOption(self, event):
        """Update buttons to reflect the selection of an action."""
        if self.optionbox.GetSelection() >= 0:
            self.okButton.Enable(True)
        else:
            self.okButton.Enable(False)
            
    def _onClose(self, event):
        """Close the frame, opening the premade if appropriate."""
        sel = self.optionbox.GetSelection()
        self.selectedClass = self.classes[sel]
        self.EndModal(event.GetId())
        self.Destroy()

def _loadPremades():
    """Load the premades from their folder.
    
    Returns
    -------
    dict of dict
        Information about the available premades. The keys are the names of
        the modules. The values for each key are also dictionaries with the
        following keys:
            
            class : class
                The class for the premade experiment frame.
            name : str
                The name of the premade experiment.
            voltage_type : list of str
                A list of voltage types ('AC' or 'DC') used in the experiment.
            cryostat : list of str
                A list of cryostats used in the experiment.
            measurement_type : list of str
                A list of the general categories which can describe the
                experiment (e.g. 'Hall effect' or 'Magnetoresistance').
            devides : int
                The number of devices to be measured.
    """
    pattern = re.compile(r'class *([\w_]+) *\( *[\w_\.]* *\) *:')
    premadeFolder = pt.unrel('src', 'premades')
    allData = {}
    
    def _importModule(moduleName):
        """Import the module and record the data."""
        fileName = pt.unrel('src', 'premades', moduleName)
        with open(fileName + '.py') as moduleFile:
            data = moduleFile.read()
            match = pattern.search(data)
        loadedModule = imp.load_source(moduleName, fileName + '.py')
        if hasattr(loadedModule, 'INFORMATION') and match is not None:
            className = match.group(1)
            information = getattr(loadedModule, 'INFORMATION')
            allData[moduleName] = information
            allData[moduleName]['class'] = getattr(loadedModule, className)
            
    for item in os.walk(premadeFolder):
        fnames = item[2]
        for fname in fnames:
            if fname.endswith('.py') and not fname.startswith('__init__'):
                currentModule = fname[:-3]
                _importModule(currentModule)

    return allData
    

if __name__ == '__main__':
    app = wx.App(0)
    premadeFrame = PremadeFrame(None)
    premadeFrame.ShowModal()
    app.MainLoop()
    