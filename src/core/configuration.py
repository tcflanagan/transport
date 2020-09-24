"""Tools for keeping track of system settings.

The `configuration` module provides a system for managing the general, 
reusable settings for the software---both a collection of default settings and 
some user-specific settings---including default file locations, graph colors, 
graph update delays, and so on. It keeps track of these data in memory and saves
them to (and initially reads them from) a file on the disk.

The module defines some classes for the above-mentioned purposes, and it creates
an actual instance of the ``Configuration`` class, so that other modules can
access the configuration without having to create a new instance and, therefore
without having to re-read the file from the hard drive.
"""

from copy import deepcopy
import logging
import os
import subprocess
from tempfile import TemporaryFile

from src.tools import config_parser as cp
from src.tools.config_parser import _bool
from src.tools import path_tools as pt

log = logging.getLogger('transport')

CONFIG_FOLDER = 'etc'
MAIN_PATH = pt.unrel([CONFIG_FOLDER, 'general.conf'])
EDITORS_PATH = pt.unrel([CONFIG_FOLDER, 'editors.conf'])
DEFAULT_FOLDER = os.path.expanduser('~')

class Configuration(object):
    """The `Configuration` class is a container for system-wide settings
    concerning appearance of certain components, default file locations, and 
    helpful ways for letting users know that an experiment is finished or that
    serious system errors (e.g. magnet quenches) have occurred.
    """
    
    def __init__(self):
        """Initialize a new Configuration object.
        
        Set default values for the various saved settings. Then attempt to read
        the data from the configuration file. If it works (i.e. the file exists
        and has the desired information), read the data from the file. If it
        does not, save the default data to the file. 
        """
        defaults = {('experiment_defaults', 'experiment_folder'): 
                                                            DEFAULT_FOLDER,
                    ('file_defaults', 'data_folder'): DEFAULT_FOLDER,
                    ('file_defaults', 'data_file'): 'data.dat',
                    ('file_defaults', 'prepend_scan'): True,
                    ('graph_defaults', 'graph_colors'): [(1, 0, 0)],
                    ('graph_defaults', 'graph_delay'): 2.0,
                    ('users', 'user_names'): [],
                    ('miscellaneous_data', 'phone_carriers'):
                        [('AT&T', 'txt.att.net'), ('Verizon', 'vtext.com')]}
        
        self._configParser = cp.ConfigParser(MAIN_PATH, cp.FORMAT_AUTO,
                                             defaultValues=defaults)
        
        self._experimentFolder = self._configParser.get('experiment_defaults',
                                                        'experiment_folder')
        
        self._dataFolder = self._configParser.get('file_defaults', 
                                                  'data_folder')
        self._dataFile = self._configParser.get('file_defaults',
                                                'data_file')
        self._prependScan = self._configParser.getBoolean('file_defaults',
                                                          'prepend_scan')

        self._graphColors = self._configParser.get('graph_defaults', 
                                                          'graph_colors')
        self._graphDelay = self._configParser.get('graph_defaults',
                                                       'graph_delay')
        
        self._carriers = self._configParser.get('miscellaneous_data',
                                                       'phone_carriers')
        
        self._userNames = self._configParser.get('users', 'user_names')
        self._users = []
        for userName in self._userNames:
            self._users.append(User(str(userName)))
        self._activeUser = None
    
    def _set(self, section, option, value):
        """Set the value associated with a specified key.
        
        This method is simply a shorthand for self._configParser.set
        
        Parameters
        ----------
        section : str
            The section in which the key is located.
        option : str
            The key whose value is to be set.
        value : variable
            The new value to associate with the given key.
        
        Returns
        -------
        variable
            The unchanged value of `value`.
        """
        return self._configParser.set(section, option, value)
        
    def getExperimentFolder(self, user=True):
        """Return the experiment folder.
        
        If a user is active and not overridden, return the user's default
        experiment folder. Otherwise, return the system default experiment
        folder.
        """
        if not user or not self._activeUser:
            return self._experimentFolder
        return self._activeUser.getExperimentFolder()
    
    def setExperimentFolder(self, newValue, user=True):
        """Set the default experiment file folder.
        
        If a user is active and not overridden, set the user's experiment file
        folder. Otherwise, set the system default experiment folder, which will 
        be used whenever no user is active and will be the default for new 
        users.
        """
        if not user or not self._activeUser:
            self._experimentFolder = self._set('experiment_defaults',
                                               'experiment_folder',
                                               newValue)
        else:
            self._activeUser.setExperimentFolder(newValue)
    
    def getDataFolder(self, user=True):
        """Return the data folder.
        
        If a user is active and not overridden, return the user's default
        data folder. Otherwise, return the system default data folder.
        """
        if not user or not self._activeUser:
            return self._dataFolder
        return self._activeUser.getDataFolder()
    def setDataFolder(self, newValue, user=True):
        """Set the default data folder.
        
        If a user is active and not overridden, set the user's default data 
        folder. Otherwise, set the system default data folder, which will be 
        used whenever no user is active and will be the default for new users.
        """
        if not user or not self._activeUser:
            self._dataFolder = self._set('file_defaults', 'data_folder',
                                         newValue)
        else:
            self._activeUser.setDataFolder(newValue)
    
    def getDataFile(self, user=True):
        """Return the default filename.
        
        If a user is active and not overridden, return the user's default
        file name. Otherwise, return the system default data file name.
        """
        if not user or not self._activeUser:
            return self._dataFile
        return self._activeUser.getDataFile()
    def setDataFile(self, newValue, user=True):
        """Set the default filename.
        
        If a user is active and not overridden, set the user's default filename.
        Otherwise, set the system default filename, which will be used whenever
        no user is active and will be the default for new users. 
        """
        if not user or not self._activeUser:
            self._dataFile = self._set('file_defaults', 'data_file',
                                       newValue)
        else:
            self._activeUser.setDataFile(newValue)
    
    def getPrependScan(self, user=True):
        """Return whether to prepend filenames with a scan number by default.
        
        If a user is active and not overridden, return whether the user wants
        to prepend a scan number by default. Otherwise, return whether the 
        system default is to prepend a scan number.
        """
        if not user or not self._activeUser:
            return _bool(self._prependScan)
        return _bool(self._activeUser.getPrependScan())
    def setPrependScan(self, newValue, user=True):
        """Set whether to prepend filenames with a scan number by default.
        
        If a user is active and not overridden, set whether the user wants
        to prepend a scan number by default. Otherwise, return whether the 
        system default is to prepend a scan number.
        """
        if not user or not self._activeUser:
            self._prependScan = self._set('file_defaults', 'prepend_scan',
                                          _bool(newValue))
        else:
            self._activeUser.setPrependScan(newValue)
        
    def getGraphColors(self):
        """Return the list of graph colors (a list of RGB tuples)."""
        return deepcopy(self._graphColors)
    def setGraphColors(self, newValue):
        """Set the colors (a list of RGB tuples) to use for plots."""
        print(repr(newValue))
        self._graphColors = self._set('graph_defaults', 'graph_colors',
                                      deepcopy(newValue))
        
    def getGraphDelay(self):
        """Return the time between successive updates of plots."""
        return self._graphDelay
    def setGraphDelay(self, newValue):
        """Set the time between successive updates of plots."""
        self._graphDelay = self._set('graph_defaults', 'graph_delay', newValue)
        
    def getCarrierStrings(self):
        """Return a list of strings representing mobile carrier names."""
        return [item[0] for item in self._carriers]
    
    def loadUser(self, username):
        """Change the active user.
        
        Parameters
        ----------
        username : str
            The username of the user whose data should be loaded. If 'None'
            or `None` is supplied, or if the specified user does not exist,
            the default settings will be loaded.
        """
        if username in self._userNames:
            log.info('Loading user ' + str(username))
            self._activeUser = self._users[self._userNames.index(username)]
        elif username == 'None' or username is None:
            log.info('Loading default user.')
            self._activeUser = None
        else:
            log.warn('User [%s] does not exist. Loading default.', username)
            self._activeUser = None
        
    def getUserName(self):
        """Return the name of the active user.
        
        Returns
        -------
        str
            The name of the active user, or 'None' if no user has been loaded.
        """
        if self._activeUser is not None:
            return self._activeUser.getUserName()
        return 'None'
    
    def setUserName(self, newValue):
        """Rename the active user.
        
        Parameters
        ----------
        newValue : str
            The new value for the name of the current user, if one has been
            loaded. If no user is active, nothing will happen.
        """
        if self._activeUser is not None:
            self._activeUser.setUserName(newValue)

    def getPhone(self):
        """Return the phone number of the active user.
        
        Returns
        -------
        str
            The phone number of the active user, or an empty string if there
            is no active user.
        """
        if self._activeUser is not None:
            return self._activeUser.getPhone()
        return ''
    
    def setPhone(self, newValue):
        """Set the phone number of the active user.
        
        Parameters
        ----------
        newValue : str
            The new phone number for the active user. If there is no active
            user, nothing will happen.
        """
        if self._activeUser is not None:
            self._activeUser.setPhone(newValue)

    def getCarrier(self):
        """Return the carrier of the active user.
        
        Returns
        -------
        str
            The carrier of the active user, or an empty string if there is no
            active user or no carrier associated with the active user.
        """
        if self._activeUser is not None:
            return self._activeUser.getCarrier()
        return ''
    
    def setCarrier(self, newValue):
        """Set the carrier of the active user, or do nothing if none."""
        if self._activeUser is not None:
            self._activeUser.setCarrier(newValue)
    
    def getSmsFinished(self):
        """Return whether to text the active user on experiment completion."""
        if self._activeUser is not None:
            return _bool(self._activeUser.getSmsFinished())
        return False
    def setSmsFinished(self, newValue):
        """Set whether to text the active user on experiment completion."""
        if self._activeUser is not None:
            self._activeUser.setSmsFinished(newValue)
    
    def getSmsError(self):
        """Return whether to text the active user on a system error."""
        if self._activeUser is not None:
            return _bool(self._activeUser.getSmsError())
        return False
    def setSmsError(self, newValue):
        """Set whether to text the active user on a system error."""
        if self._activeUser is not None:
            self._activeUser.setSmsError(newValue)
    
    def getUserNames(self):
        """Return a list of usernames as strings."""
        names = []
        for user in self._users:
            names.append(user.getUserName())
        return names
        
    def addUser(self, username):
        """Create a new user."""
        log.info('Attempting to create user [%s].', username)
        self._users.append(User(username))
        self._userNames.append(username)
        self._set('users', 'user_names', self._userNames)
        log.info('Adding user ' + username)
        
    def removeUser(self, username):
        """Delete a user."""
        log.info('Attempting to delete user [%s].', username)
        toDelete = -1
        for index, user in enumerate(self._users):
            if user.getUserName() == username:
                if self._activeUser is user:
                    self._activeUser = None
                toDelete = index
        if toDelete >= 0:
            log.info('Deleting user ' + username)
            del self._users[toDelete]
            del self._userNames[toDelete]
            self._set('users', 'user_names', self._userNames)
            userfile = pt.unrel(CONFIG_FOLDER, _getUserFile(username))
            if os.path.exists(userfile):
                os.remove(userfile)
        else:
            log.warn('Cannot remove user [%s] because he does not exist.', 
                     username)
            
    def processChangeUserName(self, oldUserame, newUsername):
        """Change the name of a user.
        
        Note: This affects the list of user names, not the objects underlying them"""
        self._userNames = [u.getUserName() for u in self._users];
        self._set("users", "user_names", self._userNames);


class User(object):
    """A class to assist Configuration by storing per-user settings"""
    
    defaults = {('experiment_defaults', 'experiment_folder'): DEFAULT_FOLDER,
                ('file_defaults', 'data_folder'): DEFAULT_FOLDER,
                ('file_defaults', 'data_file'): 'data.dat',
                ('file_defaults', 'prepend_scan'): True,
                ('personal_settings', 'phone'): '',
                ('personal_settings', 'carrier'): '',
                ('personal_settings', 'sms_finished'): False,
                ('personal_settings', 'sms_error'): False}
    
    def __init__(self, name):
        """Initialize a new user.
        
        Create a new user object with the given ``name``. If the proper file 
        exists for the given user, the settings will be loaded from that. 
        Otherwise, a new user will be created using the default settings, and
        the correct file will be created.
        """
        userFile = pt.unrel(CONFIG_FOLDER, _getUserFile(name))
        
        self._configParser = cp.ConfigParser(userFile, cp.FORMAT_AUTO, 
                                             defaultValues=User.defaults)
        
        self._name = name
        
        self._experimentFolder = self._configParser.get('experiment_defaults',
                                                        'experiment_folder')
        
        self._dataFolder = self._configParser.get('file_defaults', 
                                                  'data_folder')
        self._dataFile = self._configParser.get('file_defaults',
                                                'data_file')
        self._prependScan = self._configParser.getBoolean('file_defaults',
                                                          'prepend_scan')
        
        self._phone = self._configParser.get('personal_settings', 'phone')
        self._carrier = self._configParser.get('personal_settings', 'carrier')
        self._smsFinished = self._configParser.getBoolean('personal_settings', 
                                                          'sms_finished')
        self._smsError = self._configParser.getBoolean('personal_settings', 
                                                       'sms_error')
            
        
    def _set(self, section, option, value):
        """Set the value associated with a specified key.
        
        This method is simply a shorthand for self._configParser.set
        
        Parameters
        ----------
        section : str
            The section in which the key is located.
        option : str
            The key whose value is to be set.
        value : variable
            The new value to associate with the given key.
        
        Returns
        -------
        variable
            The unchanged value of `value`.
        """
        return self._configParser.set(section, option, value)
        
    def getUserName(self):
        """Return the user's name."""
        return self._name
     
    def setUserName(self, newValue):
        """Set the user's name, changing the configuration file accordingly."""
        oldFilename = pt.unrel(CONFIG_FOLDER, _getUserFile(self._name))
        newFilename = pt.unrel(CONFIG_FOLDER, _getUserFile(newValue))
        
        if oldFilename == newFilename:
            return
        log.info('Changing an existing username from [%s] to [%s].',
                 self._name, newValue)
        
        with open(oldFilename, 'r') as oldFile:
            fileData = oldFile.read()
        os.remove(oldFilename)
        with open(newFilename, 'w') as newFile:
            newFile.write(fileData)
        
        self._configParser = cp.ConfigParser(newFilename, cp.FORMAT_AUTO,
                                             defaultValues=User.defaults)
        oldName = self._name
        self._name = newValue
        c.processChangeUserName(oldName, newValue)
                
    def getPhone(self):
        """Return the user's telephone number as a string."""
        return self._phone
    
    def setPhone(self, newValue):
        """Set the user's telephone number."""
        self._phone = self._set('personal_settings', 'phone', newValue)
        
    def getCarrier(self):
        """Return the user's phone carrier."""
        return self._carrier
    
    def setCarrier(self, newValue):
        """Set the user's phone carrier."""
        self._carrier = self._set('personal_settings', 'carrier', newValue)
        
    def getSmsFinished(self):
        """Return whether to text the user on experiment completion."""
        return self._smsFinished
    
    def setSmsFinished(self, newValue):
        """Set whether to text the user on experiment completion."""
        self._smsFinished = self._set('personal_settings', 'sms_finished', 
                                      _bool(newValue))
        
    def getSmsError(self):
        """Return whether to text the user on critical system errors."""
        return self._smsError
    
    def setSmsError(self, newValue):
        """Set whether to text the user on critical system errors."""
        self._smsError = self._set('personal_settings', 'sms_error', 
                                   _bool(newValue))
        
    def getExperimentFolder(self):
        """Return the user's default experiment file folder."""
        return self._experimentFolder
    
    def setExperimentFolder(self, newValue):
        """Set the user's default experiment file folder."""
        self._experimentFolder = self._set('experiment_defaults',
                                           'experiment_folder',
                                           newValue)
        
    def getDataFolder(self):
        """Return the user's default data folder."""
        return self._dataFolder
    
    def setDataFolder(self, newValue):
        """Set the user's default data folder."""
        self._dataFolder = self._set('file_defaults', 'data_folder', newValue)
    
    def getDataFile(self):
        """Return the default filename for the user's data."""
        return self._dataFile
    
    def setDataFile(self, newValue):
        """Set the default filename for the user's data."""
        self._dataFile = self._set('file_defaults', 'data_file', newValue)
        
    def getPrependScan(self):
        """Return whether the user wants to prepend scan numbers by default."""
        return self._prependScan
    
    def setPrependScan(self, newValue):
        """Set whether the user wants to prepend scan numbers by default."""
        self._prependScan = self._set('file_defaults', 'prepend_scan', 
                                      _bool(newValue))

                
def _getUserFile(username):
    """Get the appropriate filename for a specified user name.
    
    Parameters
    ----------
    username : str
        The name of the user whose configuration filename should be returned.
    
    Returns
    -------
    str
        The filename for the appropriate user's configuration file.
    """
    return 'user_' + str(username) + '.conf'
        
def which(program):
    """Return the path to a specified program, or None if the path doesn't work.
    
    Parameters
    ----------
    program : str
        The path for a program.
    
    Returns
    -------
        The input path `program` if it refers to a file which exists and can
        be accessed by the Python interpreter. Otherwise, `None`.
        
    Notes
    -----
    If `program` does not refer to an absolute path, it will be appended to
    the elements in the system path, and if any of those work, the absolute
    path formed thereby will be returned.
    """
    def isExecutable(fpath):
        """Return whether the path exists and can be accessed."""
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath = os.path.split(program)[0]
    if fpath:
        if isExecutable(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exeFile = os.path.join(path, program)
            if isExecutable(exeFile):
                return exeFile

    return None

def getEditors():
    """Return a list of text file editors.
    
    Returns
    -------
    list of str
        A list of text editors which exist in the filesystem and can be accessed
        by this software.
    """    
    editorConfig = cp.ConfigParser(EDITORS_PATH, cp.FORMAT_AUTO)
    
    goodEditors = []
    for key in editorConfig.getOptions('editors'):
        editor = editorConfig.get('editors', key)
        if isinstance(editor, list):
            editor = pt.unrel(editor)
                
        if which(editor) is not None:
            goodEditors.append(editor)
        log.info('Good editors: ' + str(goodEditors))
    return goodEditors

def openEditor(defaultText=''):
    """Open a temporary file in a text editor."""
    with TemporaryFile() as tempFile:
        name = tempFile.name + '.py'
    
    with open(name, 'w') as tempFile:
        tempFile.write(defaultText)
    
    editors = getEditors()
    for editor in editors:
        try:
            subprocess.call([editor, name], shell=False)
            break
        except OSError:
            continue

    data = open(name).read()
    os.remove(name)
    return data

c = Configuration()
