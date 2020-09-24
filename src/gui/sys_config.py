"""Dialogs and panels for managing the system configuration."""

import logging
import re
import wx.html
import wx.adv

from src import about
from src.core.configuration import c
from src.gui import gui_helpers as gh
from src.tools import path_tools as pt

log = logging.getLogger('transport')

_USERNAME_ERROR_MESSAGE = ('Usernames may not contain special characters '
                           'except for underscores (spaces count as special '
                           'characters)')
_NAME = about.APP_NAME
_COPYRIGHT = '(C) 2013-2020 Thomas C. Flanagan'
_ABOUT = ('Transport Experiment is a program for running electrical transport '
          'measurements. It features a functional interface for defining '
          'sequences of steps for controlling and reading information from '
          'various instruments. The interface for implementing instruments in '
          'most cases is quite straightforward, making the software easily '
          'extensible.\n\n'
          'Other features of the software include graphing, real-time '
          'information on the state of the experiment, user-customizable '
          'settings for the saving of data, and a handful of pre-made '
          'experiments to prevent the user from having to "re-invent the '
          'wheel" every time.')


# Help and Versioning Dialogs and Frames ---------------------------------------

def showAboutWindow(parent):
    """Display an "About" dialog."""

    name = _NAME
    copyrightInfo = _COPYRIGHT
    description = _ABOUT

    info = wx.adv.AboutDialogInfo()

    info.SetName(name)
    info.SetVersion(about.getVersion())
    info.SetDescription(description)
    info.SetCopyright(copyrightInfo)
    log.debug('About window called from %s.', str(parent))
    wx.adv.AboutBox(info)

def getHelpWindow():
    """Create a help window.
    
    Load the HTML Help Workshop documentation from the `doc` folder and embed
    it in a wxPython HtmlHelpController window, and return that window.
    
    .. note:: This function does not actually *show* the window---it just 
       creates it. The window must be displayed by whatever calls the function.
        
    Returns
    -------
    wxHtmlHelpController
        A window containing software documentation
    """
    helpwindow = wx.html.HtmlHelpController()
    helpPath = pt.unrel('doc', 'htmlhelp', 'TransportExperimentdoc.hhp')
    if not helpwindow.AddBook(helpPath):
        print('error loading ' + helpPath)
    return helpwindow

def getChangeLogDialog(parent):
    """Create a change log dialog.
    
    Create and return a window displaying the change log. If the system can
    access the SVN server, the change log is read from that. Otherwise, it is
    read from a file whenever the system was last able to access the server.
    
    Parameters
    ----------
    parent : wxFrame
        The wxFrame of which the returned dialog is a child. (This is useful
        for things like centering and making sure that this window is closed
        if the application is closed.)
        
    Returns
    -------
    ChangeLogDialog
        A simple dialog containing information about all known changes to the
        software.
    """
    return ChangeLogDialog(parent)

class ChangeLogDialog(wx.Dialog):
    """A dialog for displaying the software change log.
    
    Parameters
    ----------
    parent : wxFrame
        The wxFrame which should serve as the parent of this dialog.
    """

    def __init__(self, parent):
        """Constructor."""
        super(ChangeLogDialog, self).__init__(parent, wx.ID_ANY, 'Change Log')

        sizer = wx.BoxSizer(wx.VERTICAL)

        self.textbox = wx.TextCtrl(self, wx.ID_ANY, style = wx.TE_MULTILINE)
        self.textbox.SetEditable(False)
        self.textbox.SetValue(about.getChangelog())
        sizer.Add(self.textbox, 1, wx.EXPAND | wx.ALL, 5)

        self.okbutton = wx.Button(self, wx.ID_OK, label = 'OK')
        btns = wx.StdDialogButtonSizer()
        btns.AddButton(self.okbutton)
        btns.Realize()
        sizer.Add(btns, 0, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(sizer)


# Dialogs for Configuring System Settings --------------------------------------

class SettingsDialog(wx.Dialog):
    """A dialog for configuring the system-wide settings.
    
    Parameters
    ----------
    parent : wxWindow
        The frame or panel which spawns the dialog.
    """
    def __init__(self, parent):
        super(SettingsDialog, self).__init__(parent)

        self.SetTitle('Settings')

        genpanel = wx.Panel(self)
        gensizer = wx.BoxSizer(wx.VERTICAL)
        genpanel.SetSizer(gensizer)

        self.genFiles = FilesPanel(genpanel, False)
        self.genGraph = GraphsPanel(genpanel)

        gensizer.Add(self.genFiles, 0, wx.EXPAND | wx.ALL, border = 5)
        gensizer.Add(self.genGraph, 0, wx.EXPAND | wx.ALL, border = 5)

        buttonok = wx.Button(self, wx.ID_OK)
        buttoncancel = wx.Button(self, wx.ID_CANCEL)
        btnsizer = wx.StdDialogButtonSizer()
        btnsizer.AddButton(buttoncancel)
        btnsizer.AddButton(buttonok)
        btnsizer.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(genpanel, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(btnsizer, 0, wx.EXPAND | wx.ALL, 5)

        # self.SetAutoLayout(True)
        self.SetSizerAndFit(sizer)
        # self.Layout()

    def saveSettings(self):
        """Save the new settings to the configuration manager."""
        self.genFiles.applyData()
        self.genGraph.applyData()

class UserSettingsDialog(wx.Dialog):
    """A dialog for configuring user-specific settings.
    
    Parameters
    ----------
    parent : wxWindow
        The panel or frame which spawns this dialog.
    """
    def __init__(self, parent):
        super(UserSettingsDialog, self).__init__(parent)

        self.SetTitle(c.getUserName() + '\'s Settings')

        userpanel = wx.Panel(self)
        usersizer = wx.BoxSizer(wx.VERTICAL)
        userpanel.SetSizer(usersizer)

        self.userFiles = FilesPanel(userpanel, True)
        self.userPersonal = PersonalPanel(userpanel)

        usersizer.Add(self.userPersonal, 0, wx.EXPAND | wx.ALL, border = 5)
        usersizer.Add(self.userFiles, 0, wx.EXPAND | wx.ALL, border = 5)

        buttonok = wx.Button(self, wx.ID_OK)
        buttoncancel = wx.Button(self, wx.ID_CANCEL)
        btnsizer = wx.StdDialogButtonSizer()
        btnsizer.AddButton(buttoncancel)
        btnsizer.AddButton(buttonok)
        btnsizer.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(userpanel, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(btnsizer, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizerAndFit(sizer)

    def saveSettings(self):
        """Save the new user settings to the configuration manager."""
        self.userFiles.applyData()
        self.userPersonal.applyData()

class UsersDialog(wx.Dialog):
    """A dialog for creating and deleting users.
    
    Parameters
    ----------
    parent : wxWindow
        The panel or frame which spawns this dialog.
    """
    def __init__(self, parent):
        super(UsersDialog, self).__init__(parent)

        self.SetTitle('Users')

        userpanel = wx.Panel(self)
        usersizer = wx.BoxSizer(wx.VERTICAL)
        userpanel.SetSizer(usersizer)

        self.userList = UsersPanel(userpanel)

        usersizer.Add(self.userList, 0, wx.EXPAND | wx.ALL, border = 5)

        buttonok = wx.Button(self, wx.ID_OK)
        btnsizer = wx.StdDialogButtonSizer()
        btnsizer.AddButton(buttonok)
        btnsizer.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(userpanel, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(btnsizer, 0, wx.EXPAND | wx.ALL, 5)

        self.SetAutoLayout(True)
        self.SetSizerAndFit(sizer)
        self.Layout()


# Panels for Configuring System Settings ---------------------------------------

class FilesPanel(wx.Panel):
    """A panel for configuring user defaults.
    
    This panel allows the user to set and get the settings related to where
    data and experiment files are saved by default, as well as whether the user
    wants to have scan numbers automatically included.
    
    Parameters
    ----------
    parent : wxWindow
        The frame or panel which contains this panel.
    user : bool
        Whether this panel represents the settings of a particular user. If
        `False`, the panel will represent the global system settings.
    """

    def __init__(self, parent, user=False):
        super(FilesPanel, self).__init__(parent)
        self._user = user

        outerpanel = gh.Panel(self, 'vertical', 'Files')

        mainpanel = gh.Panel(outerpanel, 'flex_grid', None, 3, 2, 5, 5)
        flags = wx.EXPAND | wx.TOP | wx.BOTTOM

        exptpanel = wx.Panel(mainpanel, wx.ID_ANY)
        exptsizer = wx.BoxSizer(wx.HORIZONTAL)
        exptpanel.SetSizer(exptsizer)

        self.textexpt = wx.TextCtrl(exptpanel, wx.ID_ANY)
        self.textexpt.Enable(False)
        self.btnexpt = wx.Button(exptpanel, wx.ID_ANY, '...')
        txtheight = self.textexpt.GetSize()[1]
        self.btnexpt.SetMinSize((30, txtheight))
        exptsizer.Add(self.textexpt, proportion = 1, flag = flags)
        exptsizer.Add(self.btnexpt, proportion = 0, flag = wx.ALL)
        self.btnexpt.Bind(wx.EVT_BUTTON, self._onFolder)

        foldpanel = wx.Panel(mainpanel, wx.ID_ANY)
        foldsizer = wx.BoxSizer(wx.HORIZONTAL)
        foldpanel.SetSizer(foldsizer)

        self.textfold = wx.TextCtrl(foldpanel, wx.ID_ANY)
        self.textfold.Enable(False)

        self.btnfold = wx.Button(foldpanel, wx.ID_ANY, '...')
        foldheight = self.textfold.GetSize()[1]
        self.btnfold.SetMinSize((30, foldheight))
        foldsizer.Add(self.textfold, proportion = 1, flag = flags)
        foldsizer.Add(self.btnfold, proportion = 0, flag = wx.ALL)
        self.btnfold.Bind(wx.EVT_BUTTON, self._onFolder)

        self.textfile = wx.TextCtrl(mainpanel, wx.ID_ANY)
        self.textfile.SetMinSize((245, -1))

        mainpanel.addLabel('Experiment folder:')
        mainpanel.add(exptpanel, 1, flags)
        mainpanel.addLabel('Data folder:')
        mainpanel.add(foldpanel, 1, flags)
        mainpanel.addLabel('Default filename:')
        mainpanel.add(self.textfile, 1, flags)
        mainpanel.addGrowableColumn(1, 1)

        self.prependscan = wx.CheckBox(outerpanel, wx.ID_ANY, 'Prepend scan')

        outerpanel.add(mainpanel, 0, wx.EXPAND, 5)
        outerpanel.add(self.prependscan, 0,
                       wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 5)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(outerpanel, 1, wx.EXPAND)

        self.fillData()

        self.SetAutoLayout(True)
        self.SetSizer(sizer)
        self.Layout()

    def _onFolder(self, event):
        """Browse for a directory."""
        eventId = event.GetId()
        if eventId == self.btnexpt.GetId():
            defaultDirectory = self.textexpt.GetValue()
        else:
            defaultDirectory = self.textfold.GetValue()
        dialog = wx.DirDialog(self, 'Choose a directory', defaultDirectory)
        if dialog.ShowModal() == wx.ID_OK:
            if eventId == self.btnexpt.GetId():
                self.textexpt.SetValue(dialog.GetPath())
            else:
                self.textfold.SetValue(dialog.GetPath())

    def fillData(self):
        """Fill controls with data from the system configuration."""
        self.textexpt.SetValue(c.getExperimentFolder(self._user))
        self.textfold.SetValue(c.getDataFolder(self._user))
        self.textfile.SetValue(c.getDataFile(self._user))
        self.prependscan.SetValue(c.getPrependScan(self._user))

    def applyData(self):
        """Set the system configuration with data from the controls."""
        c.setExperimentFolder(self.textexpt.GetValue(), self._user)
        c.setDataFolder(self.textfold.GetValue(), self._user)
        c.setDataFile(self.textfile.GetValue(), self._user)
        c.setPrependScan(str(self.prependscan.GetValue()), self._user)

class PersonalPanel(wx.Panel):
    """A panel for configuring a user's personal settings.
    
    This panel allows a certain user to control settings related to whether
    to send text messages on certain events automatically and to set the numbers
    to which such messages should be sent.
    
    Parameters
    ----------
    parent : wxWindow
        The panel or frame which should be used as the parent for this panel.
    """

    def __init__(self, parent):
        super(PersonalPanel, self).__init__(parent)

        self.carriers = c.getCarrierStrings()

        staticbox = wx.StaticBox(self, wx.ID_ANY, 'Personal')
        staticsizer = wx.StaticBoxSizer(staticbox, wx.VERTICAL)

        innerpanel = wx.Panel(self, wx.ID_ANY)
        innersizer = wx.BoxSizer(wx.VERTICAL)
        innerpanel.SetSizer(innersizer)

        subpanel = wx.Panel(innerpanel, wx.ID_ANY)
        subsizer = wx.FlexGridSizer(3, 2, 5, 5)
        subpanel.SetSizer(subsizer)

        labelname = wx.StaticText(subpanel, wx.ID_ANY, 'Name:')
        labelphon = wx.StaticText(subpanel, wx.ID_ANY, 'Phone Number:')
        labelcarr = wx.StaticText(subpanel, wx.ID_ANY, 'Carrier:')

        self.textname = wx.TextCtrl(subpanel, wx.ID_ANY)
        self.textphon = wx.TextCtrl(subpanel, wx.ID_ANY)
        self.textcarr = wx.ComboBox(subpanel, wx.ID_ANY, style = wx.CB_READONLY)
        self.textcarr.SetItems(self.carriers)

        flags = wx.EXPAND | wx.TOP | wx.BOTTOM

        subsizer.Add(labelname, 0, wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        subsizer.Add(self.textname, 1, flags, 2)
        subsizer.Add(labelphon, 0, wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        subsizer.Add(self.textphon, 1, flags, 2)
        subsizer.Add(labelcarr, 0, wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL)
        subsizer.Add(self.textcarr, 1, flags, 2)

        subsizer.AddGrowableCol(1, 1)

        checkpanel = wx.Panel(innerpanel)
        checksizer = wx.GridSizer(1, 2, 5, 5)
        checkpanel.SetSizer(checksizer)

        self.smserr = wx.CheckBox(checkpanel, wx.ID_ANY,
                                  'Text on system error')
        self.smsfin = wx.CheckBox(checkpanel, wx.ID_ANY,
                                  'Text on experiment completion')

        checksizer.Add(self.smserr)
        checksizer.Add(self.smsfin)

        innersizer.Add(subpanel, 1, wx.EXPAND | wx.ALL, 5)
        innersizer.Add(checkpanel, 0, wx.EXPAND | wx.ALL, 5)

        staticsizer.Add(innerpanel, proportion = 1, flag = wx.EXPAND)

        self.fillData()

        self.SetAutoLayout(True)
        self.SetSizer(staticsizer)
        self.Layout()

    def fillData(self):
        """Fill the controls with data from the system configuration."""
        self.textname.SetValue(c.getUserName())
        self.textphon.SetValue(str(c.getPhone()))
        self.textcarr.SetValue(c.getCarrier())
        self.smsfin.SetValue(c.getSmsFinished())
        self.smserr.SetValue(c.getSmsError())

    def applyData(self):
        """Update the system configuration with data from the controls."""
        c.setUserName(self.textname.GetValue())
        c.setPhone(self.textphon.GetValue())
        c.setCarrier(self.textcarr.GetValue())
        c.setSmsFinished(self.smsfin.GetValue())
        c.setSmsError(self.smserr.GetValue())

class GraphsPanel(wx.Panel):
    """A panel for configuring global graph settings.
    
    In its current implementation, this panel presents a way of changing
    the following graphing settings:
        - The list of colors used for successive plots within a graph, and
        - The rate at which the graph updates (expressed as a delay time in
          seconds).
    """

    def __init__(self, *args, **kwargs):
        """Constructor."""
        super(GraphsPanel, self).__init__(*args, **kwargs)

        self.graphColors = None

        staticbox = wx.StaticBox(self, wx.ID_ANY, 'Graph Settings')
        staticsizer = wx.StaticBoxSizer(staticbox, wx.VERTICAL)

        colorpanel = wx.Panel(self)
        colorsizer = wx.BoxSizer(wx.HORIZONTAL)
        colorpanel.SetSizer(colorsizer)

        buttonpanel = wx.Panel(colorpanel)
        buttonsizer = wx.BoxSizer(wx.VERTICAL)
        buttonpanel.SetSizer(buttonsizer)

        colorlabel = wx.StaticText(self, wx.ID_ANY, 'Plot color sequence:')

        self.buttonadd = gh.createButton(buttonpanel, buttonsizer,
                                         label = 'Add', handler = self._onAdd)
        self.buttonedit = gh.createButton(buttonpanel, buttonsizer,
                                          label = 'Edit', handler = self._onEdit)
        self.buttonremove = gh.createButton(buttonpanel, buttonsizer,
                                    label = 'Remove', handler = self._onRemove)
        self.buttonup = gh.createButton(buttonpanel, buttonsizer,
                                    label = 'Up', handler = self._onMoveUp)
        self.buttondown = gh.createButton(buttonpanel, buttonsizer,
                                    label = 'Down', handler = self._onMoveDown)

        self.colorlist = wx.ListBox(colorpanel, wx.ID_ANY)
        self.colorlist.Bind(wx.EVT_LISTBOX, self._updateButtons)
        colorsizer.Add(buttonpanel, 0, wx.EXPAND | wx.ALL, border = 5)
        colorsizer.Add(self.colorlist, 1, wx.EXPAND | wx.ALL, border = 5)

        delaypanel = wx.Panel(self)
        delaysizer = wx.BoxSizer(wx.HORIZONTAL)
        delaypanel.SetSizer(delaysizer)

        delaylabel = wx.StaticText(delaypanel, wx.ID_ANY, 'Graph update delay:')
        self.delayvalue = wx.TextCtrl(delaypanel, wx.ID_ANY)

        delaysizer.Add(delaylabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, border = 5)
        delaysizer.Add(self.delayvalue, 0, wx.ALL, border = 5)

        staticsizer.Add(colorlabel, 0, wx.ALIGN_CENTER_HORIZONTAL)
        staticsizer.Add(colorpanel, 1, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)
        staticsizer.Add(wx.StaticLine(self), 0, wx.EXPAND)
        staticsizer.Add(delaypanel, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 5)

        self.fillData()

        self.SetAutoLayout(True)
        self.SetSizer(staticsizer)
        self.Layout()

    def _onAdd(self, event):
        """Add a new color to the end of the list."""
        dialog = wx.ColourDialog(self)

        if dialog.ShowModal() == wx.ID_OK:
            tup = _colorDataToTuple(dialog.GetColourData())
            self.graphColors.append(tup)
            self._tupleListToStrings()
        self._updateButtons(None)

    def _onEdit(self, event):
        """Open a dialog to change the selected color."""
        index = self.colorlist.GetSelection()
        icol = self._indexTupleToColor(index)
        icd = wx.ColourData()
        icd.SetColour(icol)
        dialog = wx.ColourDialog(self, icd)

        if dialog.ShowModal() == wx.ID_OK:
            tup = _colorDataToTuple(dialog.GetColourData())
            self.graphColors[index] = tup
            self._tupleListToStrings()
        self._updateButtons(None)

    def _onRemove(self, event):
        """Remove the selected color from the list."""
        index = self.colorlist.GetSelection()
        del self.graphColors[index]
        self._tupleListToStrings()
        if len(self.graphColors) > 0:
            self.colorlist.SetSelection(0)
        self._updateButtons(None)

    def _onMoveUp(self, event):
        """Move the selected color up."""
        index = self.colorlist.GetSelection()
        self.graphColors.insert(index - 1, self.graphColors.pop(index))
        self._tupleListToStrings()
        self.colorlist.SetSelection(index - 1)
        self._updateButtons(None)

    def _onMoveDown(self, event):
        """Move the selected color down."""
        index = self.colorlist.GetSelection()
        self.graphColors.insert(index + 1, self.graphColors.pop(index))
        self._tupleListToStrings()
        self.colorlist.SetSelection(index + 1)
        self._updateButtons(None)

    def _indexTupleToColor(self, index):
        """Convert a color tuple to a color object.
        
        Parameters
        ----------
        index : int
            The position of the color tuple in the list of graph colors.
        
        Returns
        -------
        wxColor
            A wxColor object representing the color at `index`.
        """
        coltuple = self.graphColors[index]
        color = wx.Colour()
        color.Set(coltuple[0] * 255, coltuple[1] * 255, coltuple[2] * 255)
        return color


    def _tupleListToStrings(self):
        """Convert the graph colors to a list of strings.
        
        Returns
        -------
        list of str
            A list of string representations of the colors in the graph color
            list. Each string contains three elements (RGB data)
        """
        graphColorStrings = []
        previousSelection = self.colorlist.GetSelection()
        print(repr(self.graphColors))
        if isinstance(self.graphColors, str):
            self.graphColors = eval(self.graphColors)
        for col in self.graphColors:
            col1 = '%.2f' % float(col[0])
            col2 = '%.2f' % float(col[1])
            col3 = '%.2f' % float(col[2])
            graphColorStrings.append(', '.join([col1, col2, col3]))
        self.colorlist.SetItems(graphColorStrings)
        if 0 <= previousSelection < len(graphColorStrings):
            self.colorlist.SetSelection(previousSelection)
        return graphColorStrings

    def fillData(self):
        """Fill the controls with data from the software configuration."""
        self.graphColors = c.getGraphColors()
        self._tupleListToStrings()
        self.colorlist.SetSelection(0)
        self.delayvalue.SetValue(str(c.getGraphDelay()))
        self._updateButtons(None)

    def applyData(self):
        """Set the software configuration with the data from the controls."""
        c.setGraphColors(self.graphColors)
        c.setGraphDelay(float(self.delayvalue.GetValue()))

    def _updateButtons(self, event):
        """Update buttons according to selected items."""
        selectedIndex = self.colorlist.GetSelection()
        number = self.colorlist.GetCount()
        try:
            if not 0 <= selectedIndex < number:
                self.buttondown.Enable(False)
                self.buttonup.Enable(False)
                self.buttonremove.Enable(False)
                self.buttonedit.Enable(False)
            elif selectedIndex == 0:
                self.buttondown.Enable(True)
                self.buttonup.Enable(False)
                self.buttonremove.Enable(True)
                self.buttonedit.Enable(True)
            elif selectedIndex == number - 1:
                self.buttondown.Enable(False)
                self.buttonup.Enable(True)
                self.buttonremove.Enable(True)
                self.buttonedit.Enable(True)
            else:
                self.buttondown.Enable(True)
                self.buttonup.Enable(True)
                self.buttonremove.Enable(True)
                self.buttonedit.Enable(True)
        except wx.PyDeadObjectError:
            pass


class UsersPanel(wx.Panel):
    """This panel allows for the creation and deletion of users.
    """

    def __init__(self, *args, **kwargs):
        super(UsersPanel, self).__init__(*args, **kwargs)

        mainsizer = wx.BoxSizer(wx.VERTICAL)

        buttonpanel = wx.Panel(self)
        buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonpanel.SetSizer(buttonsizer)

        self.buttonadd = wx.Button(buttonpanel, wx.ID_ANY, 'Add')
        self.buttonremove = wx.Button(buttonpanel, wx.ID_ANY, 'Remove')
        buttonsizer.Add(self.buttonadd, 0, wx.ALL, border = 5)
        buttonsizer.Add(self.buttonremove, 0, wx.ALL, border = 5)
        self.buttonadd.Bind(wx.EVT_BUTTON, self._onAdd)
        self.buttonremove.Bind(wx.EVT_BUTTON, self._onRemove)

        self.userlist = wx.ListBox(self, wx.ID_ANY)
        self.userlist.SetMinSize((300, 250))

        mainsizer.Add(self.userlist, 1, wx.EXPAND | wx.ALL, border = 5)
        mainsizer.Add(buttonpanel, 0, wx.BOTTOM | wx.ALIGN_CENTER_HORIZONTAL, 5)

        self.users = []
        self.fillData()

        self.SetAutoLayout(True)
        self.SetSizer(mainsizer)
        self.Layout()

    def fillData(self):
        """Set the controls to reflect those from the software configuration."""
        self.users = c.getUserNames()
        self.userlist.SetItems(self.users)

    def _onAdd(self, event):
        """Add a new user."""
        finished = False
        pattern = re.compile(r'[^a-zA-Z0-9_]')
        while not finished:
            dialog = wx.TextEntryDialog(self, 'New user name.', 'Username',
                                        '', style = wx.OK | wx.CANCEL)
            if dialog.ShowModal() == wx.ID_OK:
                newusername = dialog.GetValue()
                if re.search(pattern, newusername):
                    message = wx.MessageDialog(self, _USERNAME_ERROR_MESSAGE,
                                               'Error', wx.OK | wx.ICON_ERROR)
                    message.ShowModal()
                elif newusername in self.users:
                    message = wx.MessageDialog(self,
                                               'That user already exists.',
                                               'Error', wx.OK | wx.ICON_ERROR)
                else:
                    c.addUser(newusername)
                    self.users.append(newusername)
                    self.userlist.SetItems(self.users)
                    finished = True
            else:
                finished = True

    def _onRemove(self, event):
        """Delete the selected user."""
        sel = self.userlist.GetSelection()
        if sel >= 0:
            c.removeUser(self.userlist.GetString(sel))
            self.userlist.Delete(sel)
            del self.users[sel]
        if len(self.users) >= 0:
            self.userlist.SetSelection(0)
        else:
            self.userlist.SetSelection(-1)


# Helper Functions -------------------------------------------------------------

def _colorDataToTuple(colorData):
    """Convert a color object to a color tuple.
    
    Parameters
    ----------
    colorData : wxColourData
        A wxColourData object to convert to a tuple.
    
    Returns
    -------
    tuple of float
        A 3-tuple of floats (the maximum value is 1.0) specifying the RGB
        values for the input color.
    """
    col = colorData.GetColour().Get()
    result = col[0] / 255.0, col[1] / 255.0, col[2] / 255.0
    return result
