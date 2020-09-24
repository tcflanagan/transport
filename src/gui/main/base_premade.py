"""Base class for premade experiments.
"""

import datetime
from functools import partial
import os
import wx
import wx.lib.scrolledpanel as scrolled

from src.core.configuration import c
from src.gui.graphing.basicpanel import GraphPanel as SingleGraphPanel
from src.gui.graphing.embeddable import EmbeddableGraphManager
from src.gui.main.base_experiment import ExperimentFrame
from src.tools import path_tools as pt
from src.tools import config_parser as cp
from src.tools.general import gridArrangement

_OPT_OPTS = wx.ALL | wx.ALIGN_CENTER_HORIZONTAL

class BasePremadeFrame(ExperimentFrame):
    """A class providing common functionality to premade experiment frames.
    
    Parameters
    ----------
    parent : wxFrame
        The frame which owns this frame (if any).
    title : str
        The title of this premade experiment (it will go in the title bar).
    graphData : list of tuple of str
        A list of tuples, where each tuple represents a single graph and
        contains three strings: the x-axis label, the y-axis label, and the
        title of the graph. Note that the first two must be the same as the
        names of the columns from which the data come.
    measurementType : str
        A short indication of the measurement type for going into the default
        filenames.
    """
    def __init__(self, parent, title, graphData, measurementType=None):
        super(BasePremadeFrame, self).__init__(parent,
                                               title=title,
                                               experiment=None,
                                               experimentPath=None,
                                               icon=None,
                                               premade=True)

        self.__edited = False

        framepanel = scrolled.ScrolledPanel(self)
        framesizer = wx.BoxSizer(wx.HORIZONTAL)
        framepanel.SetSizer(framesizer)

        self.__configpanel = ConfigPanel(framepanel)

        rightpanel = wx.Panel(framepanel)
        rightsizer = wx.BoxSizer(wx.VERTICAL)
        rightpanel.SetSizer(rightsizer)

        self.__fileData = FileData.fromFile('Heliox', measurementType, '.dat')
        self.__filepanel = FilenamePanel(rightpanel, self.__fileData)
        rightsizer.Add(self.__filepanel, 0, wx.EXPAND | wx.ALL, 2)
        self.__graphpanel = GraphPanel(rightpanel, graphData)
        rightsizer.Add(self.__graphpanel, 1, wx.EXPAND | wx.ALL, 2)


        framesizer.Add(self.__configpanel, 0, wx.EXPAND | wx.ALL, 2)
        framesizer.Add(rightpanel, 1, wx.EXPAND | wx.ALL, 4)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(framepanel, 1, wx.EXPAND)

        framepanel.SetupScrolling()
        self.SetSizer(sizer)
        self.SetAutoLayout(True)
        self.SetSizeHints(800, 600)

    def addConfigurationPanel(self, panel):
        """Add a panel to the configuration area.
        
        Parameters
        ----------
        panel : wxPanel
            A panel or a panel subclass to add to the configuration area.
        """
        panel.Reparent(self.__configpanel)
        self.__configpanel.add(panel)

    def showConfig(self, show):
        """Show or hide the configuration panel.
        
        Parameters
        ----------
        show : bool
            Whether to show the configuration panel.
        """
        self.__configpanel.show(show)

    @property
    def edited(self):
        """Return that the experiment has not been edited.
        
        Returns
        -------
        bool
            Whether the experiment has been edited. Always `False` for premade
            experiments.
        """
        return self.__edited

# GraphPanel -------------------------------------------------------------------

class GraphPanel(wx.Panel):
    """A panel for storing individual graphing panels.
    
    Parameters
    ----------
    parent : wxWindow
        The frame or panel into which this panel will be inserted.
    graphData : list of tuple of str
        A list of tuples, where each tuple represents a single graph and
        contains three strings: the x-axis label, the y-axis label, and the
        title of the graph. Note that the first two must be the same as the
        names of the columns from which the data come.
    """

    def __init__(self, parent, graphData):
        super(GraphPanel, self).__init__(parent, wx.ID_ANY)

        self.__graphPanels = []

        rows, cols = gridArrangement(len(graphData))
        sizer = wx.GridSizer(rows, cols, 5, 5)
        for graphDatum in graphData:
            xLabel, yLabel, title = graphDatum
            currentGraph = SingleGraphPanel(self, (xLabel, yLabel), title)
            self.__graphPanels.append(currentGraph)
            sizer.Add(currentGraph, 1, wx.EXPAND | wx.ALL, 2)

        self.SetSizer(sizer)
        self.SetAutoLayout(True)

    def getGraphManager(self):
        """Get the graph manager to deal with data.
        
        Returns
        -------
        EmbeddableGraphManager
            The graph manager with this panel as its parent and the
            graph panels this panel has created as its contents.
        """
        return EmbeddableGraphManager(self, self.__graphPanels)


# ConfigPanel ------------------------------------------------------------------

class ConfigPanel(wx.Panel):
    """The panel for configuring the instruments before use.
    
    Parameters
    ----------
    parent : wxWindow
        The panel or frame which should be the parent of this panel.
    """

    def __init__(self, parent):
        super(ConfigPanel, self).__init__(parent, wx.ID_ANY)

        self._sizer = wx.BoxSizer(wx.VERTICAL)
        self._sizer.SetSizeHints(self)

        self.SetSizer(self._sizer)
        self.SetAutoLayout(True)

    def add(self, panel):
        """Add an item to the panel.
        
        Parameters
        ----------
        panel : wxPanel
            The sub-panel to add to this panel.
        """
        panel.Reparent(self)
        self._sizer.Add(panel, 0, wx.EXPAND | wx.ALL, 3)
        self.SetMinSize(self.GetBestSize())
        # self.FitInside()

    def show(self, show):
        """Show or hide this panel.
        
        Parameters
        ----------
        show : bool
            Whether to show the panel.
        """
        if show:
            self.SetMinSize(self.GetBestSize())
        else:
            self.SetMaxSize((0, 0))


#---------------------------------------------------------------- Filename panel

class FilenamePanel(wx.Panel):
    """A panel for displaying a filename and parameter comments."""

    def __init__(self, parent, fileData):

        super(FilenamePanel, self).__init__(parent)

        self.fileData = fileData

        mainsizer = wx.FlexGridSizer(2, 2, 5, 5)

        self.__filename = wx.TextCtrl(self, -1, 
                                      style=wx.TE_RIGHT|wx.TE_READONLY)
        self.__filename.SetValue(self.fileData.getPath())
        self.__comments = wx.TextCtrl(self, -1, style=wx.TE_MULTILINE)
        self.__comments.SetToolTip(('Comments which will be written to '
                                          'the parameter file but not '
                                          'indicated in filenames.'))
        defaultHeight = self.__comments.GetSize()[1]
#         defaultHeight = defaultHeight * 2
        self.__comments.SetSizeHints(-1, defaultHeight)

        mainsizer.Add(wx.StaticText(self, -1, 'Filename:'), 0,
                      wx.ALIGN_RIGHT | wx.ALIGN_TOP)
        mainsizer.Add(self.__filename, 0, wx.EXPAND)
        mainsizer.Add(wx.StaticText(self, -1, 'Comments:'), 0,
                      wx.ALIGN_RIGHT | wx.ALIGN_TOP)
        mainsizer.Add(self.__comments, 0, wx.EXPAND)

        mainsizer.AddGrowableCol(1, 1)
        mainsizer.AddGrowableRow(0, 1)
        mainsizer.AddGrowableRow(1, 2)

        self.__filename.Bind(wx.EVT_LEFT_UP, self.__onFilename)

        self.SetSizerAndFit(mainsizer)

    def __onFilename(self, event):
        """Open a dialog to edit the filename."""
        dialog = FilenameDialog(self, self.fileData)
        result = dialog.ShowModal()
        if result == wx.ID_OK:
            self.__filename.SetValue(self.fileData.getPath())
        event.Skip()


class FilenameDialog(wx.Dialog):
    """A frame for setting filenames according to lab conventions."""

    def __init__(self, parent, fileData):

        super(FilenameDialog, self).__init__(parent)

        self.__fileData = fileData
        self.__system = fileData.system
        self.__measurementType = fileData.measurementType
        self.__extension = fileData.extension
        self.__fieldNames = self.__fieldCodes = None

        mainpanel = wx.Panel(self)
        mainsizer = wx.GridBagSizer(5, 5)
        mainpanel.SetSizer(mainsizer)

        optpanel = wx.Panel(mainpanel)
        optsizer = wx.BoxSizer(wx.HORIZONTAL)
        optpanel.SetSizer(optsizer)

        addLabel = partial(_addLabel, mainpanel, mainsizer)
        alt = partial(_addLabeledText, mainpanel, mainsizer)

        # Controls
        self.__rootFolder = alt('Root Folder:', (0, 0), 3, editable=False)
        self.__sampleName = alt('Sample Name:', (0, 4), 1)
        addLabel((0, 6), 'Cooldown Date:')
        self.__cooldownDate = wx.DatePickerCtrl(mainpanel)
        mainsizer.Add(self.__cooldownDate, (0, 7), (1, 1), flag=wx.EXPAND)
        addLabel((1, 0), 'Field:')
        self.__fieldConfiguration = wx.ComboBox(mainpanel)
        mainsizer.Add(self.__fieldConfiguration, (1, 1), flag=wx.EXPAND)
        self.__dimensions = alt('Dimensions:', (1, 2), 1)
        self.__options = alt('Options:', (1, 4), 3)
        self.__folderComment = alt('Comment:', (2, 0), 7)
        self.__fileComment = alt('Identifiers:', (3, 0), 7)
        mainsizer.Add(optpanel, (4, 0), (1, 8), flag=wx.ALIGN_CENTER_HORIZONTAL)
        self.__filename = alt('Filename:', (5, 0), 7, False,
                              style=wx.TE_MULTILINE)

        self.__addNumber = wx.CheckBox(optpanel,
                                       label='Prepend Measurement Number')
        self.__groupDrive = wx.CheckBox(optpanel, label='Copy to Group Drive')
        self.__manualOverride = wx.CheckBox(optpanel, label='Manually Override')

        optsizer.Add(self.__addNumber, 0, _OPT_OPTS, 5)
        optsizer.Add(self.__groupDrive, 0, _OPT_OPTS, 5)
        optsizer.Add(self.__manualOverride, 0, _OPT_OPTS, 5)

        for i in [1, 3, 5, 7]:
            mainsizer.AddGrowableCol(i, 1)

        btnpanel = wx.Panel(self)
        btnsizer = wx.BoxSizer(wx.HORIZONTAL)
        btnpanel.SetSizer(btnsizer)

        self.__okButton = wx.Button(btnpanel, wx.ID_OK, label='OK')
        self.__cancelButton = wx.Button(btnpanel, wx.ID_CANCEL, label='Cancel')

        btnsizer.Add(self.__cancelButton, 0, wx.ALL, 5)
        btnsizer.Add(self.__okButton, 0, wx.ALL, 5)

        outersizer = wx.BoxSizer(wx.VERTICAL)
        outersizer.Add(mainpanel, 1, wx.EXPAND | wx.ALL, 5)
        outersizer.Add(btnpanel, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        self.__fillData()
        self.__addHandlers()

        self.SetSizerAndFit(outersizer)


    def __fillData(self):
        """Fill the controls with data."""
        rootFolder = os.path.normpath(self.__fileData.rootDirectory)
        if not os.path.exists(rootFolder) or not os.path.isdir(rootFolder):
            rootFolder = c.getDataFolder()
        self.__rootFolder.SetValue(rootFolder)
        self.__sampleName.SetValue(self.__fileData.sampleName)
        wxdatetime = wx.DateTime()
        year, month, day = self.__fileData.cooldownDate.timetuple()[0:3]
        wxdatetime.Set(day, month, year)
        self.__cooldownDate.SetValue(wxdatetime)
        self.__fieldNames = self.__fileData.fieldNames
        self.__fieldCodes = self.__fileData.fieldCodes
        self.__fieldConfiguration.SetItems(self.__fieldNames)
        self.__fieldConfiguration.SetValue(self.__fileData.fieldConfiguration)
        self.__dimensions.SetValue(self.__fileData.dimensions)
        self.__options.SetValue(self.__fileData.options)
        self.__folderComment.SetValue(self.__fileData.directoryComment)
        self.__fileComment.SetValue(self.__fileData.fileComment)
        self.__addNumber.SetValue(self.__fileData.prependNumber)
        self.__groupDrive.SetValue(self.__fileData.groupDrive)
        manualFile = self.__fileData.manualFile.strip()
        manualOverride = len(manualFile) > 0
        if manualOverride:
            self.__manualOverride.SetValue(True)
            self.__filename.Enable(True)
            self.__filename.SetValue(manualFile)
        else:
            self.__manualOverride.SetValue(False)
            self.__filename.Enable(False)
            self.__filename.SetValue(self.__constructPath())

    def __updateData(self):
        """Update the file data container with information from the controls."""
        self.__fileData.rootDirectory = self.__rootFolder.GetValue()
        cooldate = self.__cooldownDate.GetValue()
        year, month, day = (cooldate.GetYear(), cooldate.GetMonth(),
                            cooldate.GetDay())
        self.__fileData.cooldownDate = datetime.date(year, month, day)
        self.__fileData.sampleName = self.__sampleName.GetValue()
        fldconf = self.__fieldConfiguration.GetValue()
        self.__fileData.fieldConfiguration = fldconf
        self.__fileData.dimensions = self.__dimensions.GetValue()
        self.__fileData.options = self.__options.GetValue()
        self.__fileData.directoryComment = self.__folderComment.GetValue()
        self.__fileData.fileComment = self.__fileComment.GetValue()
        self.__fileData.prependNumber = self.__addNumber.GetValue()
        self.__fileData.groupDrive = self.__groupDrive.GetValue()
        if self.__manualOverride.GetValue():
            self.__fileData.manualFile = self.__filename.GetValue()
        else:
            self.__fileData.manualFile = u''

    def __addHandlers(self):
        """Add event handlers to the controls."""
        self.__rootFolder.Bind(wx.EVT_LEFT_UP, self.__onRootFolder)
        self.__rootFolder.Bind(wx.EVT_TEXT, self.__updateName)
        self.__sampleName.Bind(wx.EVT_TEXT, self.__updateName)
        self.__cooldownDate.Bind(wx.EVT_DATE_CHANGED, self.__updateName)
        self.__fieldConfiguration.Bind(wx.EVT_COMBOBOX, self.__updateName)
        self.__dimensions.Bind(wx.EVT_TEXT, self.__updateName)
        self.__options.Bind(wx.EVT_TEXT, self.__updateName)
        self.__fileComment.Bind(wx.EVT_TEXT, self.__updateName)
        self.__folderComment.Bind(wx.EVT_TEXT, self.__updateName)
        self.__addNumber.Bind(wx.EVT_CHECKBOX, self.__updateName)
        self.Bind(wx.EVT_CLOSE, self.__onClose)
        self.Bind(wx.EVT_BUTTON, self.__onClose, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.__onClose, id=wx.ID_CANCEL)
        self.__manualOverride.Bind(wx.EVT_CHECKBOX, self.__onManualOverride)

    def __onRootFolder(self, event):
        """Show the folder-picker dialog."""
        dialog = wx.DirDialog(self, defaultPath=self.__rootFolder.GetValue())
        if dialog.ShowModal() == wx.ID_OK:
            self.__rootFolder.SetValue(dialog.GetPath())
        event.Skip()

    def __onManualOverride(self, event):
        """Toggle whether the filename is manually overridden."""
        if self.__manualOverride.GetValue():
            self.__filename.Enable(True)
        else:
            self.__filename.Enable(False)
            self.__filename.SetValue(self.__constructPath())

    def __updateName(self, event):
        """Update the filename if appropriate."""
        if not self.__manualOverride.GetValue():
            self.__filename.SetValue(self.__constructPath())

    def __onClose(self, event):
        """Close the dialog."""
        eventId = event.GetId()
        if eventId == wx.ID_OK:
            self.__updateData()
            self.__fileData.save()
        self.EndModal(eventId)
        self.Destroy()

    def __constructPath(self):
        """Return the full path name of the file."""
        base, main, sub, name = self.__constructPathList()
        main = '_'.join(main)
        sub = '_'.join(sub)
        return os.path.normpath(os.path.join(base, main, sub, name))

    def __constructPathList(self):
        """Create a filename from supplied data."""
        sampleName = self.__sampleName.GetValue().strip()
        fileComps = [sampleName]
        fileComment = self.__fileComment.GetValue().strip()
        if len(fileComment) > 0:
            fileComps.append(fileComment)

        dirComps = [sampleName]
        subdirComps = [self.__cooldownDate.GetValue().Format('%Y%m%d')]
        folderComment = self.__folderComment.GetValue().strip()
        if len(folderComment) > 0:
            subdirComps.append(folderComment)
            dirComps.append(folderComment)
        subdirComps.append(self.__measurementType)
        dimensions = self.__dimensions.GetValue().strip()
        if len(dimensions) > 0:
            subdirComps.append(dimensions)
        subdirComps.append(self.__system)
        fldconf = self.__fieldConfiguration.GetValue().strip()
        if fldconf in self.__fieldNames:
            fldconf = self.__fieldCodes[self.__fieldNames.index(fldconf)]
        subdirComps.append(fldconf)
        options = self.__options.GetValue().strip()
        if len(options) > 0:
            subdirComps.append(options)

        basedir = self.__rootFolder.GetValue().strip()
        sampledir = '_'.join(dirComps)
        subdir = '_'.join(subdirComps)
        filename = '_'.join(fileComps) + self.__extension

        basepath = os.path.join(basedir, sampledir, subdir)
        if os.path.exists(basepath) and self.__addNumber.GetValue():
            filename = pt.getNextScan(basepath) + '_' + filename
        elif self.__addNumber.GetValue():
            filename = 's000_' + filename
        return [basedir, dirComps, subdirComps, filename]

    def getPath(self):
        """Return the actual intended path for the data file."""
        if self.__manualOverride.GetValue():
            return self.__filename.GetValue()
        return self.__constructPath()

    def createPath(self):
        """Create the directory tree as far as necessary."""
        basedir, sampledir, subdir = self.__constructPathList()[0:3]
        sampledir = os.path.join(basedir, '_'.join(sampledir))
        if not os.path.exists(sampledir):
            try:
                os.mkdir(sampledir)
            except OSError:
                return False
        subdir = os.path.join(sampledir, '_'.join(subdir))
        if not os.path.exists(subdir):
            try:
                os.mkdir(subdir)
            except OSError:
                return False
        return True


class FileData(object):
    """A container for the standard path components for a data file."""

    dateFormatLocal = '%Y%m%d'
    dateFormatConfig = '%m/%d/%Y'

    def __init__(self, system, measurementType, extension,
                 fieldNames, fieldCodes, rootDirectory, sampleName,
                 cooldownDate, fieldConfiguration, dimensions, options,
                 directoryComment, fileComment, prependNumber, groupDrive,
                 manualFile):

        self.system = system
        self.measurementType = measurementType
        self.extension = extension
        self.fieldNames = fieldNames
        self.fieldCodes = fieldCodes
        self.rootDirectory = rootDirectory
        self.sampleName = sampleName
        self.cooldownDate = cooldownDate
        self.fieldConfiguration = fieldConfiguration
        self.dimensions = dimensions
        self.options = options
        self.directoryComment = directoryComment
        self.fileComment = fileComment
        self.prependNumber = prependNumber
        self.groupDrive = groupDrive
        self.manualFile = manualFile

    def update(self, rootDirectory, sampleName,
               cooldownDate, fieldConfiguration, dimensions, options,
               directoryComment, fileComment, prependNumber, groupDrive,
               manualFile):
        """Update the information associated with the data file."""

        self.rootDirectory = rootDirectory
        self.sampleName = sampleName
        self.cooldownDate = cooldownDate
        self.fieldConfiguration = fieldConfiguration
        self.dimensions = dimensions
        self.options = options
        self.directoryComment = directoryComment
        self.fileComment = fileComment
        self.prependNumber = prependNumber
        self.groupDrive = groupDrive
        self.manualFile = manualFile

    def save(self):
        """Save the file data to the configuration file."""
        conf = cp.ConfigParser(pt.unrel('config', 'premades.conf'),
                               cp.FORMAT_REPR)
        section = 'last_filename_vals'

        fieldDirections = []
        for fieldDirection in zip(self.fieldNames, self.fieldCodes):
            fieldDirections.append(fieldDirection)
        conf.set('general', 'field_directions', fieldDirections)

        conf.set(section, 'rootDirectory', self.rootDirectory)
        conf.set(section, 'sampleName', self.sampleName)
        conf.set(section, 'cooldownDate',
                 self.cooldownDate.strftime(FileData.dateFormatConfig))
        conf.set(section, 'fieldConfiguration', self.fieldConfiguration)
        conf.set(section, 'dimensions', self.dimensions)
        conf.set(section, 'options', self.options)
        conf.set(section, 'directoryComment', self.directoryComment)
        conf.set(section, 'fileComment', self.fileComment)
        conf.set(section, 'prependNumber', self.prependNumber)
        conf.set(section, 'groupDrive', self.groupDrive)
        conf.set(section, 'manualFile', self.manualFile)


    @staticmethod
    def fromFile(system, measurementType, extension):
        """Construct an object from a configuration file."""
        conf = cp.ConfigParser(pt.unrel('etc', 'premades.conf'),
                               cp.FORMAT_REPR)
        section = 'last_filename_vals'

        fieldDirections = conf.get('general', 'field_directions')
        fieldNames = []
        fieldCodes = []
        for fieldName, fieldCode in fieldDirections:
            fieldNames.append(fieldName)
            fieldCodes.append(fieldCode)
#         data = dict.fromkeys(conf.getOptions(section))
#         for key in data:
#             data[key] = conf.get(section, key)
        data = conf.getOptionsDict(section)
        month, day, year = data['cooldownDate'].strip().split('/')
        data['cooldownDate'] = datetime.date(int(year), int(month), int(day))
        data['system'] = system
        data['measurementType'] = measurementType
        data['extension'] = extension
        data['fieldNames'] = fieldNames
        data['fieldCodes'] = fieldCodes

        return FileData(**data)

    def __constructPath(self):
        """Return the full path name of the file."""
        base, main, sub, name = self.__constructPathList()
        main = '_'.join(main)
        sub = '_'.join(sub)
        return os.path.normpath(os.path.join(base, main, sub, name))

    def __constructPathList(self):
        """Create a filename from supplied data."""
        sampleName = self.sampleName.strip()
        fileComps = [sampleName]
        fileComment = self.fileComment.strip()
        if len(fileComment) > 0:
            fileComps.append(fileComment)

        dirComps = [sampleName]
        subdirComps = [self.cooldownDate.strftime(FileData.dateFormatLocal)]
        folderComment = self.directoryComment.strip()
        if len(folderComment) > 0:
            subdirComps.append(folderComment)
            dirComps.append(folderComment)
        subdirComps.append(self.measurementType)
        dimensions = self.dimensions.strip()
        if len(dimensions) > 0:
            subdirComps.append(dimensions)
        subdirComps.append(self.system)
        fieldConfig = self.fieldConfiguration.strip()
        if fieldConfig in self.fieldNames:
            fieldConfig = self.fieldCodes[self.fieldNames.index(fieldConfig)]
        subdirComps.append(fieldConfig)
        options = self.options.strip()
        if len(options) > 0:
            subdirComps.append(options)

        basedir = self.rootDirectory.strip()
        sampledir = '_'.join(dirComps)
        subdir = '_'.join(subdirComps)
        filename = '_'.join(fileComps) + self.extension

        basepath = os.path.join(basedir, sampledir, subdir)
        if os.path.exists(basepath) and self.prependNumber:
            filename = pt.getNextScan(basepath) + '_' + filename
        elif self.prependNumber:
            filename = 's000_' + filename
        return [basedir, dirComps, subdirComps, filename]

    def getPath(self):
        """Return the actual intended path for the data file."""
        if len(self.manualFile.strip()) > 0:
            return self.manualFile
        return self.__constructPath()



#-------------------------------------------------------------- Helper functions

def _addLabeledText(panel, sizer, label, pos, colspan=1,
                    alignCenter=True, enabled=True, startValue='',
                    editable=True, **kwargs):
    """Add a labeled text control and return the control."""
    if alignCenter:
        flag = wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT
    else:
        flag = wx.ALIGN_TOP | wx.ALIGN_RIGHT
    newLabel = wx.StaticText(panel, wx.ID_ANY, label)
    sizer.Add(newLabel, pos, (1, 1), flag=flag)
    newControl = wx.TextCtrl(panel, wx.ID_ANY, **kwargs)
    newControl.Enable(enabled)
    newControl.SetValue(startValue)
    newControl.SetEditable(editable)
    sizer.Add(newControl, (pos[0], pos[1] + 1), (1, colspan), flag=wx.EXPAND)
    return newControl


def _addLabel(panel, sizer, pos, label):
    """Add a label to the specified sizer."""
    newLabel = wx.StaticText(panel, wx.ID_ANY, label)
    sizer.Add(newLabel, pos, (1, 1),
              flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)

def _addCheck(parent, sizer, label, value=True):
    """Add a check box control to the specified sizer.
    
    Parameters
    ----------
    parent : wxWindow
        The parent for the check box control.
    sizer : wxSizer
        The sizer to which the control should be added.
    label : str
        The label for the control.
    value : bool
        The starting value for the control.
        
    Returns
    -------
    wxCheckBox
        The newly created control.
    """
    checkbox = wx.CheckBox(parent, wx.ID_ANY, label)
    sizer.Add(checkbox, 0, wx.ALL, 3)
    checkbox.SetValue(value)
    return checkbox

# def _addLabeledText(parent, sizer, row, col, colspan, label, value='',
#                     labelOptions=None, controlOptions=None):
#     """Add a label and text control to a grid bag sizer.
#
#     Parameters
#     ----------
#     parent : wxWindow
#         The parent for the controls.
#     sizer : wxGridBagSizer
#         The sizer to which the controls should be added.
#     row : int
#         The row to which the controls should be added.
#     col : int
#         The first column to use for the controls.
#     colspan : int
#         The number of columns which the text control should span.
#     label : str
#         The text of the label.
#     value : str
#         The initial value of the text control.
#     labelOptions : int
#         The options to use when adding the label to the sizer. If `None`, the
#         default value (wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.ALL) will
#         be used.
#     controlOptions : int
#         The options to use when adding the text control to the sizer. If
#         `None`, the default value (wx.EXPAND|wx.ALL) will be used.
#
#     Returns
#     -------
#     wxTextCtrl
#         The newly created control.
#     """
#     if labelOptions is None:
#         labelOptions = wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL | wx.ALL
#     if controlOptions is None:
#         controlOptions = wx.EXPAND | wx.ALL
#     statictext = wx.StaticText(parent, label=label)
#     textctrl = wx.TextCtrl(parent, wx.ID_ANY, value)
#     sizer.Add(statictext, (row, col), (1, 1), labelOptions)
#     sizer.Add(textctrl, (row, col + 1), (1, colspan), controlOptions)
#     return textctrl
