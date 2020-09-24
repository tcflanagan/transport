"""A container for graphical data.

A `Graph` is an object to facilitate interactions between an `Experiment`
and an actual GUI implementation of graphing.

This module provides the following classes:

Graph: 
    An interface for passing data from an experiment to a visual graph.
AbstractGraphManager: 
    An interface for spawning graph threads; it (and all its methods) must be 
    overridden to actually see anything.
"""

from abc import ABCMeta, abstractmethod
import logging
import xml.etree.ElementTree as ET

from src.tools.parsing import escapeXML

log = logging.getLogger('transport')


#------------------------------------------------------- Graph manager interface

class AbstractGraphManager(object, metaclass=ABCMeta):
    """An abstract manager for graphs. 
    
    The purpose of a `GraphManager` is to take as input a list of `Graph` 
    objects and, as the experiment is preparing to run, create a frame or 
    frames to hold the graphical representation of the graphs and start 
    threads to update them as data become available.
    
    Parameters
    ----------
    parentFrame
        A GUI frame to pass as the parent of each graph frame.
    """
    
    @abstractmethod
    def __init__(self, parentFrame):
        """Initialize a GraphManager."""
        
    @abstractmethod
    def setGraphs(self, graphs):
        """Set the graphs to be managed.

        Parameters
        ----------
        graphs : list of `Graph`
            A list of `Graph` objects.
        """
        
    @abstractmethod
    def abort(self, timeout=10.0):
        """Stop graphing.
        
        Command all `Graph` objects to stop taking new data.
        
        Parameters
        ----------
        timeout : float
            The maximum time to wait for the threads to join.
        """
        
    @abstractmethod
    def start(self):
        """Start graphing.
        
        Start a thread for each `Graph` object. These should be spawned as 
        'daemon' threads, so that if the program is exited, the threads all 
        stop.
        """
        
    @abstractmethod
    def saveGraphs(self, filename):
        """Save the graphs to a file or files.
        
        Parameters
        ----------
        filename : str or list
            The output file(s) to which the graph(s) should be saved. 
            Implementations may require either a string or a list of strings.
        """


#------------------------------------------------------------------- Graph class

class Graph(object):
    """A `Graph` is an object for managing interactions between an 
    `Experiment` and some graphical interface for actually displaying the 
    data. It effects the data transfer by pushing data points onto a `Queue`
    object.
    
    Parameters
    ----------
    experiment : Experiment
        The `Experiment` object which owns this `Graph`.
    colx : str
        The name of the column from which the x coordinates come.
    coly : str
        The name of the column from which the y coordinates come.
    colAdd : str
        The name of the column which, when updated, should signal that the next
        point added to the graph should begin a new plot.

    Notes
    -----
    The `Graph` object does not actually store all of the data---it only keeps 
    track of the latest point. The reason is that nearly every GUI 
    implementation of graphing needs to keep track of all of the data, so
    `Graph` and the graphing panel/frame contain it would double the 
    memory used with no real advantage.
    """
    
    def __init__(self, experiment, colX, colY, colAdd):
        """Create a new graph."""

        self._expt = experiment

        self._nx = None
        self._ny = None
         
        self._flagNew = False
         
        self._colX = colX
        self._colY = colY
        self._colAdd = colAdd
        
        self._dataQueue = None
         
        self._minX = None
        self._maxX = None
        self._minY = None
        self._maxY = None
        
        self._enabled = True
        
        if __debug__:
            log.debug('Creating a new graph: %s vs %s.', colY, colX)
        
    def setEnabled(self, enabled):
        """Set whether this graph is enabled.
        
        The enabled state determines only whether or not the experiment adds
        it to the manager. The `Graph` object itself does not use the flag at 
        all.
        
        Parameters
        ----------
        enabled : bool
            Whether the graph should be enabled.
        """
        self._enabled = enabled
        
    def isEnabled(self):
        """Return whether the graph is enabled.
        
        The enabled state determines only whether or not the experiment adds
        it to the manager. The `Graph` object itself does not use the flag at 
        all.
        
        Returns
        -------
        bool
            Whether the graph is enabled.
        """
        return self._enabled
        
    def setDataQueue(self, queue):
        """Set the queue to pass data to the UI.
        
        A queue is used to pass data from this graph object to the graphical
        component which actually displays the data.
        
        Parameters
        ----------
        queue : Queue.Queue
            The queue to pass data to the user interface.
        """
        self._dataQueue = queue
         
    def flagNewPlot(self):
        """Indicate that the next point should go into a new plot."""
        self._flagNew = True
        
    def clear(self):
        """Reset the graph data."""
        self._minX = None
        self._maxX = None
        self._minY = None
        self._maxY = None
        self._nx = None
        self._ny = None
        self._flagNew = False
        
    def addX(self, newx):
        """Add the x-coordinate of the next point to the graph.
        
        Parameters
        ----------
        newx : float
            The new x-value to add to the graph. If it is an integer or a
            string, it will be coerced to a float.
        """
        self._nx = float(newx)
        if self._minX == None:
            self._minX = self._nx-0.2
            self._maxX = self._nx+0.2
        elif self._nx > self._maxX:
            self._maxX = self._nx
        elif self._nx < self._minX:
            self._minX = self._nx
        self.checkPoint()
     
    def addY(self, newy):
        """Add the y-coordinate of the next point to the graph.
        
        Parameters
        ----------
        newy : float
            The new y-value to add to the graph. If it is an integer or a
            string, it will be coerced to a float.
        """
        self._ny = float(newy)
        if self._minY == None:
            self._minY = self._ny-0.2
            self._maxY = self._ny+0.2
        elif self._ny > self._maxY:
            self._maxY = self._ny
        elif self._ny < self._minY:
            self._minY = self._ny
        self.checkPoint()
         
    def checkPoint(self):
        """Add a point to the graph, if appropriate.
        
        Check whether there is both an x- and a y-coordinate available. If so,
        add a tuple to the queue, where the tuple contains the following
        elements in order:
            - New x-coordinate
            - New y-coordinate
            - Minimum x-coordinate for the graph
            - Maximum x-coordinate for the graph
            - Minimum y-coordinate for the graph
            - Maximum y-coordinate for the graph
            - Whether this point goes into a new plot
        
        Then reset the graph's fields.
        """
        
        if (self._nx is not None and 
                    self._ny is not None and 
                    self._dataQueue is not None):
            self._dataQueue.put((self._nx, self._ny, 
                                          self._minX, self._maxX, 
                                          self._minY, self._maxY, 
                                          self._flagNew))
            self._flagNew = False
            self._ny = None

    def getColumns(self):
        """Return the column names which will provide data to this graph.
        
        Returns
        -------
        tuple of str
            A 3-tuple whose contents are, in order, the names of the x data
            column, the y data column, and the column to trigger new plots on
            the graph.
        """
        return (self._colX, self._colY, self._colAdd)
     
    def setColumns(self, cols):
        """Set the names of the columns which will provide data to this graph.
        
        Parameters
        ----------
        cols : tuple of str
            A 3-tuple whose contents indicate the names of the x-column, the
            y-column, and the column which should trigger new plots on the
            graph, in that order.
        """
        if __debug__: 
            log.debug('Setting columns to ' + str(cols))
        self._colX = cols[0]
        self._colY = cols[1]
        self._colAdd = cols[2]
        
    def getTitle(self):
        """Get the title of the graph ("y name vs. x name").
        
        Returns
        -------
        str
            The name of the graph, in the form "y-column name vs. x-column 
            name".
        """
        title = self._colY + ' vs. ' + self._colX
        return title
         
    def __str__(self):
        """Get the title of the graph ("y name vs. x name").
        
        Returns
        -------
        str
            The name of the graph, in the form "y-column name vs. x-column 
            name".
        """
        return self.getTitle()
        
    def updateColumnsIfNecessary(self, oldcol, newcol):
        """Update graph labels to reflect changes in column names.
        
        Parameters
        ----------
        oldcol : str
            The name of the column from which the graph previously received
            data.
        newcol : str
            The name of the column from which the graph should now receive
            data.
        """
        if self._colX == oldcol:
            self._colX = newcol
        if self._colY == oldcol:
            self._colY = newcol
        if self._colAdd == oldcol:
            self._colAdd = newcol


    #---------------------------------------------------- Graph data persistence
    
    def __getstate__(self):
        """Return the parts of the `Graph` which are important when saving.
        
        Returns
        -------
        dict
            The data dictionary of the `Graph` object with the un-picklable
            (and otherwise undesired) elements removed.
        """
        odict = self.__dict__.copy()
        odict['_dataQueue'] = None
        return odict
    
    def getXML(self, parent):
        """Add XML to the tree."""
        graph = ET.SubElement(parent, 'graph')
        graph.set('xcol', self._colX)
        graph.set('ycol', self._colY)
        graph.set('addcol', self._colAdd)
        graph.set('enabled', repr(self._enabled))
    
