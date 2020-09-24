"""Abstract base class for experiment frames.
"""

from functools import partial
import logging
import os
import wx

from src import settings
from src.core.errors import GeneralExperimentError
from src.gui import gui_helpers as gh
from src.gui import images as img
from src.tools.general import Command

log = logging.getLogger('transport')

ID_PREMADE = wx.NewId()

ID_INSTRUMENTS = wx.NewId()
ID_CONSTANTS = wx.NewId()
ID_GRAPHS = wx.NewId()

ID_EXEC_RUN = wx.NewId()
ID_EXEC_PAUSE = wx.NewId()
ID_EXEC_STOP = wx.NewId()

_EXTS_EXPERIMENT = settings.EXTS_EXPERIMENT

class ExperimentFrame(wx.Frame):
    """A frame meant to be overridden by frames for developing experiments.
    
    Parameters
    ----------
    parent : Transport
        The main Transport program frame (or anything which implements the
        same interface).
    experiment : Experiment
        The `Experiment` object which this frame edits.
    title : str
        The default name for the experiment.
    icon : code
        Bitmap data in the form of Python code to use as the icon for this
        frame.
    premade : bool
        Whether this `ExperimentFrame` represents a premade experiment frame.
        Some features---like saving and manually editing the instruments---are 
        only available to custom experiments, so they are disabled in frames 
        for premade experiments. The default is `True`. 
    experimentPath : str
        The path to the experiment, if it was opened from a file. The default
        is `None`.
    globalStatus : str
        The status of the software, indicating whether any experiments are
        running.
    """
    
    def __init__(self, parent, experiment=None, title='Untitled Experiment', 
                 icon=None, premade=True, experimentPath=None, 
                 globalStatus='none-running', **kwargs):
        super(ExperimentFrame, self).__init__(parent, id=wx.ID_ANY, title=title,
                                              **kwargs)
        
        self.parent = parent
        
        self.premade = premade
        self.experiment = experiment
        self.experimentPath = experimentPath
        ext = _EXTS_EXPERIMENT[0]
        if experimentPath is not None:
            self.experimentName = os.path.basename(experimentPath)
            if self.experimentName.endswith(ext):
                self.experimentName = self.experimentName[:-len(ext)-1]
        else:
            self.experimentName = title
        self.__edited = False
        
        self.menuBar = None
        self.fileMenu = None
        
        
        if icon is None:
            self.SetIcon(img.getExperimentIconIcon())
        else:
            self.SetIcon(icon)
            
        self.controls = []
        
        self.initializeMenus()
        self.toolbar = self.initializeToolbar()
        self.notifyStatus(globalStatus)

        self.Bind(wx.EVT_CLOSE, self.onClose)
    
    
    def initializeMenus(self):
        """Create the menu bar."""
        self.menuBar = wx.MenuBar()
        
        #--- File Menu 
        self.fileMenu = wx.Menu()
        fileAdder = partial(gh.createMenuItem, self, self.fileMenu)
        fileAdder(wx.ID_HOME, 'Open Home Screen', handler=self.onHome)
        self.fileMenu.AppendSeparator()
        fileAdder(wx.ID_NEW, 'New', handler=self.onNew)
        fileAdder(wx.ID_OPEN, 'Open', handler=self.onOpen)
        self.fileMenu.AppendSeparator()
        fileAdder(ID_PREMADE, 'Open Premade', handler=self.onPremade)
        self.fileMenu.AppendSeparator()
        fileAdder(wx.ID_CLOSE, 'Close', handler=self.onClose)
        fileAdder(wx.ID_EXIT, 'Exit', handler=self.onExit)
        
        self.menuBar.Append(self.fileMenu, 'File')        
        
        #-- Help Menu 
        helpMenu = wx.Menu()
        helpAdder = partial(gh.createMenuItem, self, helpMenu)
        helpAdder(wx.ID_HELP, 'Help', handler=self.onHelp)
        helpAdder(wx.ID_ABOUT, 'About', handler=self.onAbout)
        self.menuBar.Append(helpMenu, 'Help')
        
        #-- Attach the menus
        self.SetMenuBar(self.menuBar)
        
    def initializeToolbar(self):
        """Create the toolbar."""
        
        toolbar = self.CreateToolBar()
        
        #-- Home
        toolbar.AddTool(wx.ID_HOME, 'Home', img.getHomeButtonBitmap(),
                              'Open the home screen.')
        self.Bind(wx.EVT_TOOL, self.onHome, id=wx.ID_HOME)
        
        #-- Execution
        toolbar.AddSeparator()
        toolbar.AddTool(ID_EXEC_RUN, 'Run', img.getRunButtonBitmap(),
                        'Begin execution of the experiment.')
        toolbar.AddTool(ID_EXEC_PAUSE, 'Pause', img.getPauseButtonBitmap(), 
                        'Pause the experiment.')
        toolbar.AddTool(ID_EXEC_STOP, 'Stop', img.getStopButtonBitmap(),
                        'Stop the experiment.')

        self.Bind(wx.EVT_TOOL, self.onRun, id=ID_EXEC_RUN)
        self.Bind(wx.EVT_TOOL, self.onPause, id=ID_EXEC_PAUSE)
        self.Bind(wx.EVT_TOOL, self.onStop, id=ID_EXEC_STOP)

        toolbar.Realize()
        return toolbar
        
    def appendControl(self, newControl):
        """Append a control to the list to be disabled when run begins.
        
        Parameters
        ----------
        newControl : wxWindow
            The control to add to the list.
        """
        self.controls.append(newControl)
        
        
    #------------------------------------------------------------ Event handlers
    
    def onHome(self, event):
        """Show the home screen, assuming it is the parent."""
        if not self.parent.IsShown():
            self.parent.Show()
        
    def onNew(self, event):
        """Create a new experiment."""
        try:
            self.parent.newExperiment()
        except AttributeError:
            log.error('Parent does not implement newExperiment.')
        
    def onOpen(self, event):
        """Open an experiment."""
        try:
            self.parent.openExperiment()
        except AttributeError:
            log.error('Parent does not implement openExperiment.')
        
    def onSave(self, event):
        """Save the experiment."""
        self.parent.saveExperiment(self)
        
    def onSaveAs(self, event):
        """Save the experiment, prompting for a file name."""
        self.parent.saveExperimentAs(self)
        
    def onPremade(self, event):
        """Open a premade experiment."""
        self.parent.openPremade()
        
    def onClose(self, event):
        """Close the experiment."""
        if self.experiment is not None:
            self.experiment.abort()
        try:
            self.parent.closeExperiment(self)
        except AttributeError:
            log.error('Parent does not implement closeExperiment.')
            self.Destroy()
        
    def onExit(self, event):
        """Exit the software (this is mostly handled by the parent)."""
        self.parent.exitSoftware(self)
        
    def onHelp(self, event):
        """Open the help system."""
        self.parent.onHelp(None)
        
    def onAbout(self, event):
        """Open the About screen."""
        self.parent.onAbout(None)
    
    def onRun(self, event=None):
        """Run the experiment.
        
        Returns
        -------
        bool
            Whether the experiment aws successfully initiated. The method
            returns `False` if an unrecoverable error was detected or if the
            user cancels in response to a recoverable error.
        """
        if self.parent is not None:
            command1 = Command(self.parent.runExperiment, self)
            command2 = Command(self.parent.endExperiment) 
            self.experiment.setInteractionParameters(
                    preSequenceCommands=[command1],
                    postSequenceCommands=[command2])
        else:
            command = Command(self.notifyStatus, status='none-running')
            self.experiment.setInteractionParameters(
                    postSequenceCommands=[command])
        try:
            self.experiment.run()
        except GeneralExperimentError as err:
            dialog = gh.ErrorDialog(self, err)
            result = dialog.ShowModal()
            if result == wx.ID_OK:
                self.experiment.run(False)
            else:
                self.notifyStatus('none-running')
                return False
        return True
        
    def onPause(self, event):
        """Pause the experiment."""
        if self.experiment.isPaused():
            self.experiment.resume()
        else:
            self.experiment.pause()
            
    def onStop(self, event):
        """Stop the experiment."""
        self.experiment.abort()
        
    def notifyStatus(self, status=None):
        """Update this frame to reflect the status of the software.
        
        Update the execution button status and the editability of panels
        to reflect changes in the software status (e.g., whether the
        experiment for this frame is running, whether the experiment
        for another frame is running, or whether nothing is running).
        
        Parameters
        ----------
        status : str
            The status of the software. Valid options are the following:
                - self-running
                - self-paused
                - other-running
                - none-running
        """
        if status == 'self-running':
            self.toolbar.EnableTool(ID_EXEC_RUN, False)
            self.toolbar.EnableTool(ID_EXEC_PAUSE, True)
            self.toolbar.EnableTool(ID_EXEC_STOP, True)
            for control in self.controls:
                control.Enable(False)
        elif status == 'self-paused':
            self.toolbar.EnableTool(ID_EXEC_RUN, False)
            self.toolbar.EnableTool(ID_EXEC_PAUSE, True)
            self.toolbar.EnableTool(ID_EXEC_STOP, True)
            for control in self.controls:
                control.Enable(False)
        elif status == 'other-running':
            self.toolbar.EnableTool(ID_EXEC_RUN, False)
            self.toolbar.EnableTool(ID_EXEC_PAUSE, False)
            self.toolbar.EnableTool(ID_EXEC_STOP, False)
            for control in self.controls:
                control.Enable(True)
        elif status == 'none-running':
            self.toolbar.EnableTool(ID_EXEC_RUN, True)
            self.toolbar.EnableTool(ID_EXEC_PAUSE, False)
            self.toolbar.EnableTool(ID_EXEC_STOP, False)
            for control in self.controls:
                control.Enable(True)
        else:
            self.toolbar.EnableTool(ID_EXEC_RUN, False)
            self.toolbar.EnableTool(ID_EXEC_PAUSE, False)
            self.toolbar.EnableTool(ID_EXEC_STOP, False)
            for control in self.controls:
                control.Enable(False)
            
    def getEnded(self):
        """Return whether the experiment has finished running."""
        return not self.experiment.isRunning()
        
