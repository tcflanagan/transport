"""A tool for processing information about an experiment's status."""

import logging
import textwrap
from time import strftime

log = logging.getLogger('transport')


class StatusMonitor(object):
    """A class for monitoring and displaying information to the user.
    
    Many actions performed by instruments can take a significant amount of
    execution time, and the user will typically want some information
    about what is happening at a given moment.
    
    This class allows information to be passed from the instruments (and the
    experiment or actions) and processed via `Command` objects, allowing the
    information to be redirected according to the program in question.
    """

    def __init__(self, name, timestampUpdate=False, timestampPost=True):

        self._name = name
        self._past = []
        self._current = ''

        self._timestampUpdate = timestampUpdate
        self._timestampPost = timestampPost

        self._updateCommands = []
        self._postCommands = []

    def setName(self, name):
        """Set the name of the status monitor.
        
        Parameters
        ----------
        name : str
            The new name for the status monitor.
        """
        self._name = name

    def getName(self):
        """Return the name of the status monitor.
        
        Returns
        -------
        str
            The name of the status monitor.
        """
        return self._name

    def setCommands(self, updateCommands=None, postCommands=None):
        """Set the commands which will be executed upon updates.
        
        Parameters
        ----------
        updateCommands : list of Command
            A list of `Command` objects to be executed when the `update`
            method is executed. `currentMessage`, a string, will be passed as
            a keyword argument to each `Command`.
        postCommands : list of Command
            A list of `Command` objects to be executed when the `post` method
            is executed. `postedMessage`, a string indicating the last completed
            action, will be passed as a keyword argument to each `Command`.
        """
        if updateCommands is None:
            self._updateCommands = []
        else:
            self._updateCommands = updateCommands
        if postCommands is None:
            self._postCommands = []
        else:
            self._postCommands = postCommands

    def update(self, message):
        """Update the message indicating the experiment's current state.
        
        Parameters
        ----------
        message : str
            A string indicating the experiment's current status.
        """
        self._current = message

        for command in self._updateCommands:
            command.execute(currentMessage=message)

    def post(self, message=None):
        """Update the list of messages detailing the experiment's past actions.

        Parameters
        ----------
        message : str
            A string which should be tacked onto the list of past actions. If
            `None`, the last update will be sent to the past message list.
            Regardless, the current status message will be cleared.
        """
        if message is None:
            self._past.append(strftime('%Y-%m-%d %H:%M:%S - ') + self._current)
        else:
            self._past.append(strftime('%Y-%m-%d %H:%M:%S - ') + message)
        self._current = ''

        notice = self._past[-1]
        for command in self._postCommands:
            command.execute(postedMessage=notice)

    def clear(self):
        """Clear the status monitor's information."""
        self._current = ''
        self._past = []
        self._updateCommands = []
        self._postCommands = []

class TextPrompter(object):
    """An object for prompting for user input from the command line."""
    
    def __init__(self, width=70):
        self._width = width
        
    def prompt(self, prompt, options):
        """Prompt the user for input."""
        while True:
            print(textwrap.fill(prompt, self._width))
            self._printOptions(options)
            try:
                response = int(input('Enter a selection: '))
                if 0 <= response < len(options):
                    return response
                else:
                    print('Choice %d is out of range. Try again.' % response)
            except (TypeError, ValueError):
                print('Invalid response. Try again.')
        
    def _printOptions(self, options):
        """Print the available options."""
        formatString = '%' + str(len(str(len(options))) + 2) + 'd : %s' 
        for i, item in enumerate(options):
            print(formatString % (i, item))


_STATUS_MONITORS = {}

def getStatusMonitor(name):
    """Return a status monitor, creating it if it does not exist.
    
    Parameters
    ----------
    name : str
        The name of the status monitor to get.
    
    Returns
    -------
    StatusMonitor
        The `StatusMonitor` object with the specified name.
    """
    if name in _STATUS_MONITORS:
        return _STATUS_MONITORS[name]
    newMonitor = StatusMonitor(name)
    _STATUS_MONITORS[name] = newMonitor
    return newMonitor
