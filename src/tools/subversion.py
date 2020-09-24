"""A class to represent a subversion repository.
"""

from src.tools import general
from src.tools.commandline import Environment


class SVNRepository(object):
    """An object to represent an SVN repository."""
    
    def __init__(self, repositoryHome):
        self.env = Environment()
        self.env.changeDirectory(repositoryHome)
        
    def checkout(self, url):
        """Check out an SVN repository specified by URL.
        
        Parameters
        ----------
        url : str
            The web address of the repository to check out.
        """
        return self.env.communicate('svn checkout ' + url)
        
    def getContentsString(self, recursive=True):
        """Get the contents of the repository as a single string.
        
        Parameters
        ----------
        recursive : bool
            Whether to scan the repository tree recursively. If `True`, 
            include all elements of the repository, regardless of depth. If 
            `False`, include only the top-level elements.

        Returns
        -------
        str
            A string containing each item in the repository on one line.
        """
        if recursive:
            command = 'svn list -R'
        else:
            command = 'svn list'
        return self.env.communicate(command)
    
    def getContentsList(self, recursive=True):
        """Get a list of the contents of the repository.
        
        Parameters
        ----------
        recursive : bool
            Whether to scan the repository tree recursively. If `True`, 
            include all elements of the repository, regardless of depth. If 
            `False`, include only the top-level elements.

        Returns
        -------
        list of str
            A list of strings, where each string represents a single item in
            the repository.
        """
        contentsString = self.getContentsString(recursive)
        return general.multilineStringToList(contentsString, True)
    
    def getStatusString(self):
        """Get the status of the SVN repository.
        
        Returns
        -------
        str 
            A many-line string indicating the status of the repository (each
            line corresponds to a file, and "status" includes information about
            whether the file should be added or removed or whether there are
            conflicts.
        """
        command = 'svn status'
        response = self.env.communicate(command)
        return response
        
    def getStatusList(self):
        """Get the status list of the SVN repository.
        
        Returns
        -------
        list of str
            A list of strings indicating the status of the repository (each
            string corresponds to a file, and "status" contains information 
            about whether the file should be added or removed or whether there 
            are conflicts.
        """
        response = self.getStatusString()
        return general.multilineStringToList(response)
        
    def markUnknowns(self):
        """Update the repository to reflect changes in the local filesystem.
        
        When files are added to or removed from the folder tree where the
        working copy is stored, the repository does not know what to do with
        them. To keep the entire tree properly versioned, mark every missing
        element as "deleted" and every new ("unversioned") element as "added."
        """
        statusCommand = 'svn status'
        response = self.env.communicate(statusCommand)
        lines = general.multilineStringToList(response, True)
        for item in lines:
            filename = item[8:]
            mod = item[0]
            conflict = item[6]
            if mod == 'C' or conflict != ' ':
                raise Exception('Conflict with ' + filename)
            
            if mod == '?':
                self.add(filename)
            elif mod == '!':
                self.remove(filename)
            elif mod == '~':
                self.repairObstruction(filename)
    
    def add(self, item):
        """Mark an item for addition to the repository."""
        command = 'svn add %s'
        self.env.communicate(command % item)
    
    def remove(self, item):
        """Mark an item for removal from the repository."""
        command = 'svn remove %s'
        self.env.communicate(command % item)
    
    def repairObstruction(self, item):
        """Attempt to repair obstructions, usually without success."""
        command = 'svn update --force %s'
        self.env.communicate(command % item)
        self.env.communicate(command % item)
        self.add(item)
        
    def getRevision(self):
        """Get the current revision of the repository.
        
        Returns
        -------
        int
            The current revision of the repository.
        """
        command = 'svn info'
        response = self.env.communicate(command)
        splitResponse = general.multilineStringToList(response)
        for line in splitResponse:
            if line.startswith('Revision:'):
                line = line[len('Revision:'):].strip()
                revision = int(line)
                return revision
        return 0
    
    def getLog(self):
        """Get the repository's change log."""
        command = 'svn log'
        response = self.env.communicate(command)
        return general.multilineStringToList(response)
    
    def update(self):
        """Update the working copy to accord with the repository."""
        command = 'svn update'
        response = self.env.communicate(command)
        return response
    
    def commit(self, message):
        """Upload a working copy to the repository."""
        command = 'svn commit -m "%s"' % message
        return self.env.communicate(command)
