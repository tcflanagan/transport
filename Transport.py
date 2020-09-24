"""The main program."""
from functools import partial
import logging
import os.path
import wx
import wx.lib.agw.gradientbutton as GB
import wx.lib.platebtn as platebtn

from src import about, settings
import src.initialize
src.initialize.initialize()
from src.core.experiment import Experiment
from src.core.configuration import c
from src.dev import test_frame as tf
from src.gui import sys_config as sc
from src.gui import gui_helpers as gh
from src.gui import images as img
from src.gui.graphing.basicframe import StandardGraphManager
from src.gui.main.expt_editor import SequenceFrame
from src.gui.main.inst_control import INSTRUMENT_CONTROLLERS as ICS
from src.gui.main.premade_loader import PremadeFrame
from src.tools import loader


log = logging.getLogger('transport')

TEST_MODE = True

ID_HELP = wx.ID_HELP
ID_ABOUT = wx.ID_ABOUT
ID_USERS = wx.NewIdRef()
ID_SETTINGS = wx.ID_SETUP
ID_USER_SETTINGS = wx.ID_PREFERENCES
ID_INSTRUMENTS = wx.NewIdRef()

ID_NEWEXPT = wx.ID_NEW
ID_OPENEXPT = wx.ID_OPEN
ID_PREMADE = wx.NewIdRef()

ID_CHANGELOG = wx.NewIdRef()

_STYLE = wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX)
_MSG_UNSAVED = ('%s has unsaved changes. Do you want to save them now?')

_EXTS_EXPERIMENT = settings.EXTS_EXPERIMENT

class TransportExperiment(wx.Frame):
    """The main frame for managing experiments (the main application frame)."""

    def __init__(self):
        super(TransportExperiment, self).__init__(parent=None,
                                                  id=wx.ID_ANY,
                                                  title=about.APP_NAME,
                                                  style=_STYLE)

        self.frames = []
        self.names = []
        self.nextUntitled = 0
        
        self.helpwindow = None
        
        self.controllerIDs = {}
        for item in ICS:
            self.controllerIDs[item] = wx.NewIdRef()
        
        self.btnUserSettings = None
        self._initializeMenus()

        mainpanel = gh.Panel(self, panelStyle=wx.SUNKEN_BORDER)

        splashpanel = gh.Panel(mainpanel, 'horizontal')
        bmp = img.getBannerBitmap()
        splashimage = wx.StaticBitmap(splashpanel, wx.ID_ANY, bmp)
        splashpanel.add(splashimage, 0)

        userpanel = gh.Panel(mainpanel, 'horizontal')
        userpanel.addStretchSpacer(1)
        self.userbox = userpanel.addLabeledComboBox('User: ', 'None',
                                        style=wx.CB_READONLY,
                                        valueHandler=self._onSelectUser,
                                        proportion=3)
        userpanel.addStretchSpacer(1)
        self.updateUsers()

        buttonpanel = gh.Panel(mainpanel, 'horizontal')
        btnMaker = partial(createGradientButton, buttonpanel)
        buttonpanel.addStretchSpacer(2)
        btnMaker(ID_NEWEXPT, img.getExperimentNewBitmap(), self._onNew)
        buttonpanel.addStretchSpacer(1)
        btnMaker(ID_OPENEXPT, img.getExperimentOpenBitmap(), self._onOpen)
        buttonpanel.addStretchSpacer(1)
        btnMaker(ID_PREMADE, img.getExperimentPremadeBitmap(), self._onPremade)
        buttonpanel.addStretchSpacer(2)

        hidepanel = wx.Panel(mainpanel)
        hidesizer = wx.BoxSizer(wx.HORIZONTAL)
        hidepanel.SetSizer(hidesizer)
        self.hidebutton = platebtn.PlateButton(hidepanel, wx.ID_ANY, 'Hide',
                                               style=platebtn.PB_STYLE_SQUARE)
        hidesizer.Add(self.hidebutton)

        mainpanel.add(splashpanel, 0, wx.EXPAND)
        mainpanel.addStretchSpacer(2)
        mainpanel.add(userpanel, 0, wx.EXPAND | wx.ALL, 10)
        mainpanel.addStretchSpacer(1)
        mainpanel.add(buttonpanel, 0, wx.EXPAND | wx.ALL, 10)
        mainpanel.addStretchSpacer(5)
        mainpanel.add(hidepanel, 0, wx.ALIGN_RIGHT, 0)

        outersizer = wx.BoxSizer(wx.VERTICAL)
        outersizer.Add(mainpanel, 1, wx.EXPAND)

        self.hidebutton.Bind(wx.EVT_BUTTON, self._onHide)
        self.Bind(wx.EVT_SHOW, self._onShow)
        self.Bind(wx.EVT_CLOSE, self._onExit)

        self.SetSizerAndFit(outersizer)
        self.SetSize((-1, 450))

    def _initializeMenus(self):
        """Create the menus and add them to the frame."""
        menubar = wx.MenuBar()

        fileMenuData = [(wx.ID_NEW, 'New Experiment', None, self._onNew),
                        (wx.ID_OPEN, 'Open Experiment', None, self._onOpen),
                        (ID_PREMADE, 'Open Premade', None, self._onPremade),
                        (wx.ID_EXIT, 'Exit', None, self._onExit)]
        gh.createMenu(self, menubar, '&File', fileMenuData)
        
        toolsMenu = wx.Menu()
        controllerMenu = wx.Menu()
        keys = list(self.controllerIDs.keys())
        keys.sort()
        for key in keys:
            currId = self.controllerIDs[key].GetValue()
            controllerMenu.Append(currId, key)
            self.Bind(wx.EVT_MENU, self._onController, id=currId)
        toolsMenu.AppendSubMenu(controllerMenu, 'Controllers')
        toolsMenu.AppendSeparator()
        toolsMenu.Append(ID_SETTINGS, 'Settings', 'Edit software settings')
        toolsMenu.Append(ID_USERS.GetValue(), 'Users', 'Edit the list of users')
        self.btnUserSettings = toolsMenu.Append(ID_USER_SETTINGS, 
                                                'User settings', 
                         'Edit the preferences for the currently-selected user')
        self.Bind(wx.EVT_MENU, self._onSettings, id=ID_SETTINGS)
        self.Bind(wx.EVT_MENU, self._onUsers, id=ID_USERS)
        self.Bind(wx.EVT_MENU, self._onUserSettings, id=ID_USER_SETTINGS)
        menubar.Append(toolsMenu, '&Tools')

        helpMenuData = [(wx.ID_HELP, 'Help', 'View software help',
                          self.onHelp),
                         (wx.ID_ABOUT, 'About', 'About', self.onAbout),
                         (ID_CHANGELOG, 'Change log', 'View revision history',
                          self._onChangeLog)]
        gh.createMenu(self, menubar, '&Help', helpMenuData)

        self.SetMenuBar(menubar)

    def _onController(self, event):
        """Open a controller frame."""
        eventId = event.GetId()
        frame = None
        for name, val in self.controllerIDs.items():
            if val == eventId:
                frame = self.openController(name, self)
                log.info('Opened controller for %s', name)
        if frame is None:
            log.error('Failed to find the desired controller.')
    
    def openController(self, name, parent):
        """Open a controller frame for some instrument.
        
        Parameters
        ----------
        name : str
            The name (value of `MODEL`) of the instrument to be controlled.
        parent : wxFrame
            The frame which should be used as the parent of the controller frame
            to be opened.
        """
        frame = ICS[name](parent)
        frame.Show()
        return frame
        
    def _onHide(self, event):
        """Hide this frame."""
        self.Show(False)

    def _onShow(self, event):
        """When this frame opens determine whether to show the hide button.
        
        This frame should be allowed to be hidden if other frames are open.
        Otherwise, it should not be allowed to be hidden.
        """
#         try:
        if len(self.frames) > 0:
                self.hidebutton.Show(True)
        else:
            self.hidebutton.Show(False)
#         except wx.PyDeadObjectError:
#             pass

    def getNextUntitled(self):
        """Return an integer string for labeling the next new experiment."""
        self.nextUntitled += 1
        return str(self.nextUntitled)

    def updateUsers(self):
        """Update the list of users."""
        sel = self.userbox.GetValue()
        usernames = ['None'] + c.getUserNames()
        self.userbox.SetItems(usernames)
        if sel in self.userbox.GetItems():
            self.userbox.SetValue(sel)
            if sel == 'None':
                self.btnUserSettings.Enable(False)
            else:
                self.btnUserSettings.Enable(True)
        else:
            self.userbox.SetSelection(0)
            self.btnUserSettings.Enable(False)

    def newExperiment(self):
        """Create a new, empty experiment, and display it in a SequenceFrame."""
        experiment = Experiment()
        newtitle = 'Untitled ' + self.getNextUntitled()
        experimentFrame = SequenceFrame(self, experiment, True, newtitle)
        experiment.setInteractionParameters(parentFrame=experimentFrame,
                                   graphManagerClass=StandardGraphManager)
        self.frames.append(experimentFrame)
        self.names.append(newtitle)
        log.info('Created experiment ' + newtitle)
        experimentFrame.Show()
        testFrame = tf.TestingFrame(experimentFrame, experiment)
        testFrame.Show()
        self.Show(False)

    def openExperiment(self):
        """Open a previously-saved experiment.
        
        Open a dialog to prompt for a filename for an experiment which was
        previously saved. Open the experiment, and display it in a
        SequenceFrame.
        """
        ext = _EXTS_EXPERIMENT[0]
        wildcard = 'Transport experiment (*.%s)|*.%s' % (ext, ext)
        dialog = wx.FileDialog(self, "Open Experiment", c.getExperimentFolder(),
                               '', wildcard, wx.FD_OPEN)
        if dialog.ShowModal() == wx.ID_OK:
            experimentPath = dialog.GetPath()
            experimentName = os.path.basename(experimentPath)
            if experimentName.endswith(ext):
                experimentName = experimentName[:-len(ext)-1]
            experiment = loader.loadExperiment(experimentPath)
            frame = SequenceFrame(self, experiment, False,
                                  title=experimentName,
                                  experimentPath=experimentPath)
            experiment.setInteractionParameters(parentFrame=frame,
                                       graphManagerClass=StandardGraphManager)
            self.frames.append(frame)
            self.names.append(experimentName)
            log.info('Opened experiment ' + experimentName)
            frame.Show()
            self.Show(False)

    def saveExperiment(self, frameToSave):
        """Save an experiment.
        
        Parameters
        ----------
        frameToSave : ExperimentFrame
            The frame managing the experiment the user wants to save. If this
            frame does not have an experiment path set, a Save As dialog will
            be opened.
        """
        if frameToSave.experimentPath is None:
            self.saveExperimentAs(frameToSave)
        else:
            self._saveExperiment(frameToSave.experiment, 
                                 frameToSave.experimentPath)
        log.info('Saved experiment ' + frameToSave.experimentName)
        frameToSave.edited = False

    def saveExperimentAs(self, frameToSave):
        """Save the experiment, prompting for a file name.
        
        Parameters
        ----------
        frameToSave : ExperimentFrame
            The frame managing the experiment the user wants to save.
        """
        ext = _EXTS_EXPERIMENT[0]
        wildcard = 'Transport experiment (*.%s)|*.%s' % (ext, ext)
        dialog = wx.FileDialog(self, "Save Experiment As",
                               c.getExperimentFolder(), '', wildcard, wx.FD_SAVE)
        if dialog.ShowModal() == wx.ID_OK:
            newPath = dialog.GetPath()
            if not newPath.endswith(ext):
                newPath += '.' + ext
            frameToSave.experimentPath = newPath
            experimentName = os.path.basename(newPath)
            if experimentName.endswith(ext):
                experimentName = experimentName[:-len(ext)-1]
            frameToSave.experimentName = experimentName
            self._saveExperiment(frameToSave.experiment, newPath)
            self.renameExperiment(frameToSave, experimentName)
            frameToSave.edited = False
            
    def _saveExperiment(self, experiment, path):
        """Save an experiment to XML text.
        
        Parameters
        ----------
        experiment : Experiment
            The experiment to save.
        path : str
            The path to which the experiment should be saved.
        """
        Experiment.save(experiment, path);

    def openPremade(self):
        """Open a premade experiment.
        
        Open the filter dialog for premade experiments. On confirmation, 
        open a premade and display it in its relevant frame.
        """
        dialog = PremadeFrame(self)
        if dialog.ShowModal() == wx.ID_OK:
            newClass = dialog.selectedClass
            newFrame = newClass(self)
            self.frames.append(newFrame)
            self.names.append(newFrame.experimentName)
            newFrame.Show()
            newFrame.Maximize()
            self.Show(False)

    def renameExperiment(self, frame, newName):
        """Change the name of an experiment.
        
        Parameters
        ----------
        frame : ExperimentFrame
            The frame associated with the experiment whose name is to be 
            changed.
        newName : str
            The new value for the name of the appropriate experiment.
        """
        ext = _EXTS_EXPERIMENT[0]
        if newName.endswith(ext):
            newName = newName[:-len(ext)-1]
        try:
            index = self.frames.index(frame)
            log.info('Renaming experiment %s to %s.', self.names[index],
                     newName)
            self.names[index] = newName
        except ValueError:
            log.error('Experiment not found ' + newName)

    def closeExperiment(self, frameToClose):
        """Close an experiment.
        
        Parameters
        ----------
        frameToClose : ExperimentFrame
            The frame used to display the experiment.
        
        Returns
        -------
        int
            The wxID of the button which was pressed to close the dialog (one
            of wx.ID_YES, wx.ID_NO, and wx.ID_CANCEL).
        """
        result = wx.ID_YES
        try:
            index = self.frames.index(frameToClose)
            title = self.names[index]
            if frameToClose.edited:
                dialog = wx.MessageDialog(frameToClose, _MSG_UNSAVED % title,
                                          'Save changes?',
                                          wx.YES_NO | wx.CANCEL | 
                                          wx.ICON_QUESTION)
                result = dialog.ShowModal()
                dialog.Destroy()
                if result == wx.ID_YES:
                    self.saveExperiment(frameToClose)
                    title = self.names[index]
                elif result == wx.ID_CANCEL:
                    return result
            del self.frames[index]
            del self.names[index]
            frameToClose.Destroy()
            log.info('Closed experiment ' + title)
            if len(self.frames) == 0:
                self.Show()
        except ValueError:
            log.error('Experiment [%s] not found.', title)
        return result


    #--------------------------------------------------------- Execution control

    def runExperiment(self, frameToRun):
        """Prepare the experiments for one of them to run.
        
        Only one experiment can be run at a time, so when one is about to run,
        all of the others must be unexecutable. Scan through all open sequence
        frames, and disable the execution buttons on all of them except the
        one about to go.
        
        Parameters
        ----------
        frameToRun : ExperimentFrame
            The frame which presents the experiment which is about to run. 
        """
        if __debug__:
            log.debug('Attempting to update execution buttons: run.')
        for frame in self.frames:
            if frame is frameToRun:
                frame.notifyStatus('self-running')
            else:
                frame.notifyStatus('other-running')

    def endExperiment(self):
        """Indicate that an experiment has finished running.
        
        Update all open experiment frames to reflect the fact that one of them
        has finished running. The main effect is to enable the Run buttons
        on the other frames.
        
        Parameters
        ----------
        finishedFrame : ExperimentFrame
            The experiment editor frame which has finished.
        """
        if __debug__:
            log.debug('Attempting to update execution buttons: end.')
        for frame in self.frames:
            frame.notifyStatus('none-running')

    def exitSoftware(self, initiator=None):
        """Exit the software.
        
        Parameters
        ----------
        initiator : wxWindow
            The frame initiating the exit sequence. If `None`, it will be
            assumed that the main transport frame initiated the exit
            sequence.
        """
        if len(self.frames) > 0:
            if initiator is not None and len(self.frames) == 1:
                result = wx.ID_YES
            else:
                dialog = wx.MessageDialog(self, ('Experiments are still open. '
                                                 'Are you sure you want to '
                                                 'exit?'), 'Exit?',
                                                 wx.YES_NO | wx.YES_DEFAULT)
                result = dialog.ShowModal()
            if result == wx.ID_YES:
                cancelled = False
                while len(self.frames) > 0 and not cancelled:
                    response = self.closeExperiment(self.frames[0])
                    if response == wx.ID_CANCEL:
                        cancelled = True
                if cancelled:
                    return
            else:
                return

        log.info('Exiting the application.')
        self.Destroy()


    #------------------------------------------------------------ Event Handlers

    def _onNew(self, event):
        """Create a new custom experiment."""
        self.newExperiment()

    def _onOpen(self, event):
        """Open a saved custom experiment."""
        self.openExperiment()

    def _onPremade(self, event):
        """Open the dialog to open a premade experiment."""
        self.openPremade()

    def _onExit(self, event):
        """Close the application."""
        self.exitSoftware()

    #===========================================================================
    # Handlers - Help
    #===========================================================================

    def onHelp(self, event):
        """Show the HTML Help window."""
        if self.helpwindow is None:
            self.helpwindow = sc.getHelpWindow()
        self.helpwindow.DisplayContents()

    def onAbout(self, event):
        """Show the about window."""
        sc.showAboutWindow(self)

    #===========================================================================
    # Handlers - Settings and development
    #===========================================================================

    def _onSelectUser(self, event):
        """Change the active user."""
        c.loadUser(self.userbox.GetValue())
        if self.userbox.GetSelection() == 0:
            self.btnUserSettings.Enable(False)
        else:
            self.btnUserSettings.Enable(True)

    def _onUsers(self, event):
        """Show the user addition/removal tool."""
        dialog = sc.UsersDialog(self)
        dialog.ShowModal()
        dialog.Destroy()
        self.updateUsers()

    def _onSettings(self, event):
        """Show the system configuration dialog."""
        dialog = sc.SettingsDialog(self)
        if dialog.ShowModal() == wx.ID_OK:
            dialog.saveSettings()
        dialog.Destroy()

    def _onUserSettings(self, event):
        """Show the user configuration dialog."""
        dialog = sc.UserSettingsDialog(self)
        if dialog.ShowModal() == wx.ID_OK:
            dialog.saveSettings()
        dialog.Destroy()
        
        sel = self.userbox.GetSelection()
        usernames = ['None'] + c.getUserNames()
        self.userbox.SetItems(usernames)
        self.userbox.SetSelection(sel)
        

#     def _onInstrumentTool(self, event):
#         """Show the instrument implementation tool."""
#         iframe = InstrumentFrame(self)
#         iframe.Show()

    def _onChangeLog(self, event):
        """Show the log of changes to the software."""
        cld = sc.getChangeLogDialog(self)
        cld.Show()


#-------------------------------------------------------------- Helper functions

def createGradientButton(parent, wxId, bitmap, handler):
    """Create a new gradient button.
    
    Parameters
    ----------
    parent : gh.Panel
        The panel which contains this button.
    wxId : int
        The ID for this button.
    bitmap : wxBitmap
        The image to go on the button.
    handler : method
        The method to execute when the button is pressed.
        
    Returns
    -------
    wxGradientButton
        The newly created gradient button.
    """
    buttonSize = (bitmap.GetWidth() + 10, bitmap.GetHeight() + 10)
    button = GB.GradientButton(parent, wxId, bitmap, size=buttonSize)
    button.Bind(wx.EVT_BUTTON, handler, id=wxId)
    parent.add(button)
    return button

def start():
    """Begin the application"""
    log.info('Starting the application.')
    app = wx.App(0)
    mainFrame = TransportExperiment()
    mainFrame.Show()
    app.MainLoop()

if __name__ == '__main__':
    start()
