"""A basic, standalone, single-graph frame for displaying data.
"""

import logging
from PIL import Image
import queue
import tempfile
import time
import threading
import wx
from wx.lib import newevent

from src.core.configuration import c
from src.core.graph import AbstractGraphManager
from src.gui.graphing.basicpanel import GraphPanel
from src.tools.general import gridArrangement

__all__ = ['StandardGraphManager', 'GraphThread', 'GraphFrame']
log = logging.getLogger('transport')

ASCHECK = wx.ID_ANY
FIG_WIDTH = 380
FIG_HEIGHT = 280

UPDATE_DELAY = c.getGraphDelay()

class StandardGraphManager(AbstractGraphManager):
    """A class for sending data from experiments to GUI panels.
    
    Parameters
    ----------
    parentFrame : wx.Window
        The frame which will be used as the parent for the `GraphFrame` objects
        spawned by this manager.
    """
    
    def __init__(self, parentFrame):
        """Instantiate a graph manager."""
        super(StandardGraphManager, self).__init__(parentFrame)
        self.parentFrame = parentFrame
            
    def setGraphs(self, graphs):
        """Set the graphs which will be managed.
        
        Parameters
        ----------
        graphs : list of Graph
            The `Graph` objects which will send their data to the frames
            managed by this object.
        """
        self.__graphs = graphs
        self.__dataQueues = []
        self.__graphThreads = []
        self.__figures = []
        for g in self.__graphs:
            currdq = queue.Queue()
            self.__dataQueues.append(currdq)
            g.setDataQueue(currdq)
            currgt = GraphThread(self.parentFrame, currdq, g.getColumns())
            self.__graphThreads.append(currgt)
        
    def abort(self, timeout=10):
        """Abort the update threads."""
        log.info('Ending graph manager.')
        for gt in self.__graphThreads:
            gt.abort()
        for gt in self.__graphThreads:
            gt.join(timeout)
            self.__figures.append(gt.getFigure())
        self.__dataQueues = []
        self.__graphThreads = []
        
    def start(self):
        """Start the update threads."""
        for gt in self.__graphThreads:
            gt.start()
    
    def getGraphs(self):
        """Return the figures from the graphing panels."""
        figs = []
        for figthread in self.__graphThreads:
            figs.append(figthread.getFigure())
        return figs
        
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
            log.debug('Preparing to save graphs to file %s...', filename)
        output = []
        for figure in self.__figures:
            subFile = tempfile.mktemp('.png')
            output.append((figure, subFile))
        if len(output) > 0:
            log.debug('Attempting to save graphs to file %s...', filename)
            wx.CallAfter(_saveSub, output, filename)
        else:
            log.debug('No graphs present; aborting the save operation.')

        
class GraphThread(threading.Thread):
    """A thread to update a particular graph at regular intervals.
    
    Parameters
    ----------
    parentFrame : wx.Window
        The frame or panel which will contain the Frame managed by this thread.
    dataQueue : Queue
        The `Queue` object which will move data from the `Graph` object to the
        `GraphFrame` associated with this thread (and, therefore, to the
        `GraphPanel`.
    columns : 2-tuple of str
        Strings representing the column names which provide the x- and y-values
        for the graph. These strings will label the axes in the `GraphPanel`.
    """

    def __init__(self, parentFrame, dataQueue, columns):
        super(GraphThread, self).__init__()
        
        self.setDaemon(True)
        
        (self.UpdateEvent, self.EVT_UPDATE_GRAPH) = newevent.NewEvent()
        
        graphFrame = GraphFrame(parentFrame, dataQueue, self, columns)
        graphFrame.Show()
        self.graphPanel = graphFrame.graphPanel
        self.graphPanel.Bind(self.EVT_UPDATE_GRAPH, self.graphPanel.onUpdate)
        
        self.keepGoing = True
        self.running = False
        
        self.figure = None
        
        if __debug__: 
            log.debug('Graph frame shown.')
        
    def abort(self):
        self.keepGoing = False

    def run(self):
        log.info('Beginning execution of graph thread.')
        self.running = True
        while self.keepGoing:
            evt = self.UpdateEvent()
            wx.PostEvent(self.graphPanel, evt)
            time.sleep(UPDATE_DELAY)
        wx.PostEvent(self.graphPanel, evt)
        log.info('Ending execution of graph thread.')
        self.running = False
                    
    def getFigure(self):
        return self.graphPanel.fig
    
    def isRunning(self):
        return self.running


class GraphFrame(wx.Frame):
    """A frame for containing a single graph.
    
    Parameters
    ----------
    parent : Frame
        This frame's parent (so that if the parent is closed, this will also
        be closed).
    dataQueue : Queue
        The `Queue.Queue` object which will be passed to the panel for 
        transferring data from the `Graph`.
    thread : Thread
        The `threading.Thread` object in which the graph will run.
    columns : iterable
        A list or tuple containing the names of the columns relevent to this
        graph. In order, they are the x-column, the y-column, and the column
        which triggers new plots.
    """
        
    __all__ = ['update', 'getFigure']
    
    def __init__(self, parent, dataQueue, thread, columns):
        super(GraphFrame, self).__init__(parent, wx.ID_ANY)
        
        self.SetTitle('%s vs %s' % (columns[1], columns[0]))

        self.thread = thread
        
        self.SetSize((400,350))
        self.SetMinSize((400,300))
        
        self.Bind(wx.EVT_CLOSE, self.onClose)
        
        self.graphPanel = GraphPanel(self, columns, None, dataQueue)
        mainbox = wx.BoxSizer(wx.VERTICAL)
        mainbox.Add(self.graphPanel, proportion=1, flag=wx.EXPAND)
         
        self.SetAutoLayout(True)
        self.SetSizer(mainbox)
        self.Layout()
        
        if __debug__: 
            log.debug('GraphFrame created: ' + self.GetTitle())
        
    def getFigure(self):
        return self.graphPanel.fig
                
    def onClose(self, event):
        if self.thread.isRunning():
            self.thread.abort()
        self.thread.join()
        self.Show(False)


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
    