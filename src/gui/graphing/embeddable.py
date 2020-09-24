"""A panel for containing multiple graphs which can be embedded in a frame.
"""

import logging
from PIL import Image
import queue
import tempfile
import threading
import time
import wx.lib.newevent

from src.core.configuration import c
from src.core.graph import AbstractGraphManager
from src.tools.general import gridArrangement

__all__ = ['EmbeddableGraphManager', 'GraphThread']
log = logging.getLogger('transport')

ASCHECK = wx.ID_ANY
FIG_WIDTH = 380
FIG_HEIGHT = 280

UPDATE_DELAY = c.getGraphDelay()

class EmbeddableGraphManager(AbstractGraphManager):
    """A class to manage the graphs for an experiment.
    
    Parameters
    ----------
    parentFrame : wx.Window
        The frame or panel which contains the panels for the individual graphs.
    graphPanels : list of GraphPanel
        A list containing all of the `GraphPanel` objects which this
        `GraphManager` will manage. 
    """
    
    def __init__(self, parentFrame, graphPanels):
        """Instantiate a graph manager."""
        super(EmbeddableGraphManager, self).__init__(parentFrame)
        self.parentFrame = parentFrame
        self.graphPanels = graphPanels
        self.graphs = None
        self.graphThread = None
        self.figures = None
        
    def setGraphs(self, graphs):
        """Set the graphs to manage.
        
        Parameters
        ----------
        graphs : list of Graph
            A list of `Graph` objects which will send their data to this
            manager to be put into the appropriate panels.
        """
        self.graphs = graphs
        for graph, panel in zip(graphs, self.graphPanels):
            currQueue = queue.Queue()
            graph.setDataQueue(currQueue)
            panel.setDataQueue(currQueue)
        self.graphThread = GraphThread(self.parentFrame, self.graphPanels)
            
    def abort(self, timeout=10):
        """Stop the thread for updating the graphs."""
        log.info('Ending graph manager.')
        self.graphThread.abort()
        self.graphThread.join(timeout)
        self.figures = self.graphThread.getFigures()
        
        self.graphThread = None
        
    def start(self):
        """Start the thread for updating the graphs."""
        self.graphThread.start()
        
    def getGraphs(self):
        """Return the figures for the graphs so that they can be saved."""
        return self.graphThread.getFigures()
        
    def saveGraphs(self, filename):
        """Save the graphs to a file.
        
        Resize all graphs to the appropriate size. Then arrange them into a
        grid and save that grid to the file specified by `filename`.
        
        Parameters
        ----------
        filename : str
            A string pointing to which the graph images should be saved. Note 
            that all graphs go to the same file. `filename` should be a 
            complete path name, including an extension.
        """
        if __debug__:
            log.debug('Attempting to save graph to file %s', filename)
        output = []
        for figure in self.figures:
            fn = tempfile.mktemp('.png')
            output.append((figure, fn))

        #_saveSub(output, filename)
        wx.CallAfter(_saveSub, output, filename)

        
class GraphThread(threading.Thread):
    """A thread to update the graphs at regular intervals.
    
    Parameters
    ----------
    parentFrame : wx.Window
        The frame or panel which contains the panels for the individual graphs.
    graphPanels : list of GraphPanel
        A list containing all of the `GraphPanel` objects which this
        thread will manage. 
    """

    def __init__(self, parentFrame, graphPanels):
        super(GraphThread, self).__init__()
        
        self.setDaemon(True)
        
        (self.UpdateEvent, self.EVT_UPDATE_GRAPH) = wx.lib.newevent.NewEvent()
        
        self.graphPanels = graphPanels
        for graph in self.graphPanels:
            graph.Bind(self.EVT_UPDATE_GRAPH, graph.onUpdate)
        
        self.keepGoing = True
        self.running = False
        
        self.figure = None
        
        if __debug__: 
            log.debug('Graph frame shown.')
        
    def abort(self):
        """Signal that the thread should stop."""
        self.keepGoing = False

    def run(self):
        log.info('Beginning execution of graph thread.')
        self.running = True
        while self.keepGoing:
            evt = self.UpdateEvent()
            for graph in self.graphPanels:
                wx.PostEvent(graph, evt)
            time.sleep(UPDATE_DELAY)
        for graph in self.graphPanels:
            wx.PostEvent(graph, evt)
        log.info('Ending execution of graph thread.')
        self.running = False
                    
    def getFigures(self):
        figures = []
        for graph in self.graphPanels:
            figures.append(graph.fig)
        return figures
    
    def isRunning(self):
        return self.running

def _saveSub(data, outputFilename):
    filenames = []
    for fig, filename in data:
        filenames.append(filename)
        fig.savefig(filename)
    rows, cols = gridArrangement(len(filenames))
    outputImage = Image.new("RGBA", 
                            ((FIG_WIDTH+20)*cols, (FIG_HEIGHT+20)*rows))
    index = 0
    for row in range(rows):
        for col in range(cols):
            if index >= len(filenames):
                break
            curr = Image.open(filenames[index])
            curr = curr.resize((FIG_WIDTH, FIG_HEIGHT), Image.ANTIALIAS)
            x = (10 + FIG_WIDTH)*col + 10
            y = (10 + FIG_HEIGHT)*row + 10
            outputImage.paste(curr, (x, y))
            index += 1
    outputImage.save(outputFilename)
    