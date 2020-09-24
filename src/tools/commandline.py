"""A collection of tools for interacting with the command line.

Notes
-----
The contents of this module have not been tested in Windows.
"""
import subprocess
import sys
import os
from src.tools import path_tools as pt
from src.tools import general

__all__ = ['Environment']
        
if sys.platform.startswith('win'):
    WIN = True
    COMMAND_LINE = ['cmd', '/k']
    PATH_SEP = ';'
    CMD_RM = 'del'
    CMD_MV = 'move'
    CMD_CP = 'copy'
#     PATH_SET = 'set %(name)s=%(value)s'
#     PATH_EXTEND_START = 'set %(name)s=%%%(name)s%%;%(value)s'
    #PATH_READ = 'echo %(name)
else:
    WIN = False
    COMMAND_LINE = ['/bin/bash']
    PATH_SEP = ':'
    CMD_RM = 'rm'
    CMD_MV = 'mv'
    CMD_CP = 'cp'
#     PATH_SET = 'export %(name)s=%(value)s'
#     PATH_EXTEND_END = 'export %(name)s=%(value)s:$%(name)s'
    PATH_READ = 'echo $%(name)s'
    
class Environment(object):
    """A class representing a shell session.
    
    In its present implementation, this class can only be expected to work
    properly in Linux.
    """
    def __init__(self):
        """Constructor."""
        self._env = os.environ.copy()
        self._cwd = pt.unrel()
        self._outputs = []
            
    def extendPath(self, name, value, start=True, forceReplace=False):
        """Extend a path-like environment variable.
        
        Parameters
        ----------
        name : str
            The name of the environment variable to extend. In this application,
            it will often be "PYTHONPATH".
        value : str
            The value to append to the path.
        start : bool
            Whether to prepend the new component to the variable. If `False`, 
            the new component will be appended.
        forceReplace : bool
            Whether to change the variable if it already has a value set.
        """
        if name in self._env and not forceReplace:
            oldval = self._env[name]
            if start:
                newval = PATH_SEP.join([value, oldval])
            else:
                newval = PATH_SEP.join([oldval, value])
        else:
            newval = value
        self._env[name] = newval
        return newval
    
    def setPath(self, name, value):
        """Set a path-like variable.
        
        Parameters
        ----------
        name : str
            The name of the environment variable to extend. In this application,
            it will often be "PYTHONPATH".
        value : str
            The value to append to the path.
        """
        response = self.extendPath(name, value, True, True)
        return response
        
    def changeDirectory(self, directory):
        """Change the working directory.
        
        Parameters
        ----------
        directory : str
            The new working directory as a string.
        """
        self._cwd = directory
        
    def removeDirectory(self, directory, recursive=True):
        """Remove a directory.
        
        Parameters
        ----------
        directory : str
            The path of the directory to remove.
        recursive : bool
            Whether to recursively remove all sub-materials.
        """
        opts = ' -f '
        if recursive:
            opts = ' -Rf '
        self.communicate(CMD_RM + opts + directory)
        
    def removeDirectoryContents(self, directory, filesOnly=True, 
                                ignoreHidden=True):
        """Remove the contents of a directory.
        
        Parameters
        ----------
        directory : str
            The path of the directory whose contents should be removed.
        filesOnly : bool
            Whether to delete only regular files (i.e. ignore subfolders). The
            default is `True`.
        ignoreHidden : bool
            Whether to ignore hidden files and folders. The default is `True`.
        """
        command = 'ls -a %s'
        contents = self.communicate(command % directory)
        contentsList = general.multilineStringToList(contents)
        if '.' in contentsList:
            contentsList.remove('.')
        if '..' in contentsList:
            contentsList.remove('..')
        newList = []
        for item in contentsList:
            if not ignoreHidden or not item.startswith('.'):
                newList.append(os.path.join(directory, item))
                
        if filesOnly:
            for item in newList:
                itemtest = pt.unrel(item)
                if os.path.isdir(itemtest):
                    self.removeDirectoryContents(item, filesOnly, ignoreHidden)
                elif os.path.isfile(itemtest):
                    self.remove(item)
                else:
                    print('unknown: ' + item)
        else:
            for item in newList:
                self.removeDirectory(directory, True)
            
            
    def remove(self, fileName):
        """Remove a regular file.
        
        Parameters
        ----------
        fileName : str
            The path of the file to delete.
        """
        self.communicate(CMD_RM + ' ' + fileName)
        
    def move(self, source, target, force=False):
        """Move a file or folder.
        
        Parameters
        ----------
        source : str
            The path of the file or folder to move.
        target : str
            Where the file or folder should be moved.
        force : bool
            Whether to overwrite files without prompting or failing. The default
            is `False`.
        """
        if force:
            command = 'mv -f %s %s'
        else:
            command = 'mv %s %s'
        self.communicate(command % (source, target))
    
    def moveDirectoryContents(self, source, target, force=False):
        """Move the contents of a directory from one location to another.
        
        Parameters
        ----------
        source : str
            The path of the folder whose contents should be moved.
        target : str
            The path of the folder into which the files should be moved.
        force : bool
            Whether to automatically overwrite file conflicts. The default is
            `False`.
        """
        if source.endswith('/') or source.endswith('\\'):
            source += '*'
        else:
            source += os.path.sep + '*'
        if force:
            command = 'mv -f %s %s'
        else:
            command = 'mv %s %s'
        self.communicate(command % (source, target))
            
        
    def copy(self, source, target, recursive=True):
        """Copy a file or folder.
        
        Parameters
        ----------
        source : str
            The path of the file or folder to copy.
        target : str
            The path to which the file should be copied.
        recursive : bool
            If `source` is a folder, whether to copy all of its contents
            recursively.
            
        Notes
        -----
        If `recursive` is not set and `source` is a folder with contents, the
        operation will fail.
        """
        if recursive:
            command = 'cp -R %s %s'
        else:
            command = 'cp %s %s'
        self.communicate(command % (source, target))
    
    def communicate(self, command, shell=True):
        """Send a command and read the response.
        
        Parameters
        ----------
        command : str
            The command to execute.
        shell : bool
            Whether to run in the system shell.
            
        Returns
        -------
        str
            The standard output (STDOUT) for the process.
        """
        result = subprocess.check_output(command,
                                         cwd = self._cwd,
                                         env = self._env,
                                         stderr=subprocess.STDOUT,
                                         shell = shell)
        self._outputs.append(result)
        return result
    
    @classmethod
    def isWindows(cls):
        """Determine whether the operating system is Windows."""
        return WIN


if __name__ == '__main__':
    ENV = Environment()
    ENV.changeDirectory('/home/thomas/Documents/Projects/Transport/')
    print(ENV.removeDirectoryContents('doc/htmlhelp'))
    #print(e.communicate('svn log'))
