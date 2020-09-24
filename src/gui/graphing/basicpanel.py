"""A resuable panel for displaying graphs.

This module provides a panel which can be used in frames to display graphs to
the user. It uses matplotlib, and it probably is not the fastest (as in
processing speed) way to implement this, but it works for the most part.

"""

import logging
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.backends.backend_wxagg import NavigationToolbar2WxAgg
import numpy as np
import pylab
import queue
import wx

from src.core.configuration import c
from src.gui import images as img

log = logging.getLogger('transport')

COLORS = c.getGraphColors()
NUMCOL = len(COLORS)

ASCHECK = wx.ID_ANY

_ID_FIT = wx.NewId()
_ID_ZOOM = wx.NewId()
_ID_PAN = wx.NewId()
_ID_LOCK = wx.NewId()

class GraphPanel(wx.Panel):
    """A simple panel for displaying a single, multi-plot graph.
    
    This is a simple panel for displaying graphical data to the user. It
    interacts with the relevant `Experiment` and `Graph` objects through a
    `Queue` instance.
    
    Parameters
    ----------
    parent : wxWindow
        The window (frame or panel) which contains this panel.
    labels : 2-tuple of str
        A two-string sequence of strings representing the x- and y-axis labels
        for the graph.
    title : str
        If not `None`, the title that goes above the graph.
    dataQueue : Queue
        An instance of `Queue.Queue` used to transfer data between a `Graph`
        object and this panel.
    """
    
    def __init__(self, parent, labels, title=None, dataQueue=None):        
        super(GraphPanel, self).__init__(parent, wx.ID_ANY)
        self.SetMinSize((400, 300))
        
        self.dataQueue = dataQueue
        
        # The data for the CURRENT plot (numeric data)
        self.xdata = []
        self.ydata = []
        # The data for ALL plots (a list of axes objects)
        self.plotData = []
        # Which index in self.plotData the new points should be added to
        self.currentPlot = 0
        
        # Range-related data
        self.minx = None
        self.maxx = None
        self.miny = None
        self.maxy = None
        
        self.dpi = 100
        self.fig = None
        self.canvas = None
        
        self.updatesEnabled = True
        
        # Create a figure object
        try:
            self.fig = Figure((3.0, 3.0), dpi=self.dpi, tight_layout=True)
        except TypeError:
            log.error('Tight layout probably is not implemented in ' + 
                          'this version of matplotlib')
            self.fig = Figure((3.0, 3.0), dpi=self.dpi)
        backgroundColor = []
        for item in self.GetBackgroundColour().Get():
            backgroundColor.append(item/255.0)
        self.fig.patch.set_facecolor(backgroundColor)
        
        # Create an axes object by adding a "subplot" to the figure, then format
        self.axes = self.__constructInitialAxes(labels, title)

        # Create a new plot and append it to the plotData array.
        self.plotData.append(
            self.axes.plot(self.xdata, self.ydata,
                           linewidth=1, marker='s',
                           color=COLORS[0])[0])
        # Set the starting range        
        self.axes.set_xbound(lower=-0.1, upper=7)
        self.axes.set_ybound(lower=-1.1, upper=1.1)

        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        
        # Create the toolbar
        self.toolbar = self.__constructToolbar(self.canvas)
        self.toolbar.Realize()
        
        # Put it all together.
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.canvas, 1, flag=wx.LEFT | wx.TOP | wx.GROW)
        vbox.Add(self.toolbar, 0, wx.ALIGN_CENTER_HORIZONTAL, 5)
        self.SetSizer(vbox)
    
    def __constructToolbar(self, canvas):
        """Create the toolbar.
        
        Parameters
        ----------
        canvas : FigureCanvasWxAgg
            The canvas (from matplotlib) which should be controlled by the
            new toolbar.
        
        Returns
        -------
        wxToolbar
            The new toolbar.
        """
        chartToolbar = NavigationToolbar2WxAgg(canvas)
        chartToolbar.Show(False)
        myToolbar = wx.ToolBar(self)
#         myToolbar.AddTool(_ID_FIT, 'Fit data', img.getGraphFitBitmap(), 
#                           shortHelpString='Fit data')
        myToolbar.AddTool(_ID_FIT, 'Fit Data', img.getGraphFitBitmap())
        myToolbar.AddSeparator()
        myToolbar.AddRadioTool(_ID_ZOOM, 'Zoom Graph', img.getGraphZoomBitmap(),
                                    shortHelp='Zoom')
        myToolbar.AddRadioTool(_ID_PAN, 'Pan Graph', img.getGraphMoveBitmap(),
                                    shortHelp='Pan')
        myToolbar.ToggleTool(_ID_PAN, True)
        chartToolbar.pan()
        myToolbar.AddSeparator()
        myToolbar.AddCheckTool(_ID_LOCK, 'Enable/Disable Updates', img.getGraphUnlockBitmap(), 
                                    img.getGraphLockBitmap(),
                                    'Enable/disable updates.')
        self.Bind(wx.EVT_TOOL, self.drawPlot, id=_ID_FIT)
        self.Bind(wx.EVT_TOOL, chartToolbar.zoom, id=_ID_ZOOM)
        self.Bind(wx.EVT_TOOL, chartToolbar.pan, id=_ID_PAN)
        self.Bind(wx.EVT_TOOL, self.toggleUpdates, id=_ID_LOCK)
        
        return myToolbar
        
    def __constructInitialAxes(self, labels, title=None):
        """Construct axes.
        Parameters
        ----------
        labels : tuple of str
            A tuple of two strings specifying the labels for the x- and y-axes,
            respectively.
        title : str
            The title for the graph. If `None` (the default), no title will be
            shown.
            
        Returns
        -------
        axes
            A newly created matplotlib axes object.
        """
        axes = self.fig.add_subplot(111)
        axes.set_facecolor('black')
        axes.grid(True, color='gray')
        axes.set_xlabel(labels[0], fontsize=9)
        axes.set_ylabel(labels[1], fontsize=9)
        if title is not None:
            axes.set_title(title, fontsize=9)
        pylab.setp(axes.get_xticklabels(), fontsize=8)
        pylab.setp(axes.get_yticklabels(), fontsize=8)
        return axes
        
    def toggleUpdates(self, event=None):
        """Enable updates to the graph."""
        newState = not self.toolbar.GetToolState(_ID_LOCK)
        if newState:
            self.toolbar.SetToolNormalBitmap(_ID_LOCK, 
                                               img.getGraphUnlockBitmap())
            self.updatesEnabled = True
            self.onUpdate(None)
        else:
            self.toolbar.SetToolNormalBitmap(_ID_LOCK, 
                                               img.getGraphLockBitmap())
            self.updatesEnabled = False
        
    def setDataQueue(self, dataQueue):
        """Set the data queue."""
        self.dataQueue = dataQueue
      
    def onUpdate(self, event):
        """Update the plot.
        
        Query the queue, popping points from it, until it is empty. Then draw
        the graph with the new data.
        """
        if self.updatesEnabled:
            try:
                while not self.dataQueue.empty():
                    newpoint = self.dataQueue.get()
                    self.addPoint(newpoint)
                self.drawPlot()
            except queue.Empty:
                pass
        
    def drawPlot(self, event=None):
        """Redraw the plot."""
        if self.minx is not None:
            padx = (self.maxx - self.minx)*0.05
            pady = (self.maxy - self.miny)*0.05
            self.axes.set_xbound(lower=self.minx-padx, upper=self.maxx+padx)
            self.axes.set_ybound(lower=self.miny-pady, upper=self.maxy+pady)
                
        pylab.setp(self.axes.get_xticklabels(), visible=True)
        
        self.plotData[self.currentPlot].set_xdata(np.array(self.xdata))
        self.plotData[self.currentPlot].set_ydata(np.array(self.ydata))
        
        self.canvas.draw()
        
    def addPoint(self, data):
        """Add a new point to the graph.
        
        Parameters
        ----------
        data : 6-tuple of float
            A tuple which consists of the following values (all floats) in
            order:
                - the x-value of the point to add,
                - the y-value of the point to add,
                - the minimum x-value in the graph,
                - the maximum x-value in the graph,
                - the minimum y-value in the graph, and
                - the maximum y-value in the graph.
        """
        if data[-1]:
            self.addPlot()
        self.xdata.append(data[0])
        self.ydata.append(data[1])
        self.minx = data[2]
        self.maxx = data[3]
        self.miny = data[4]
        self.maxy = data[5]
        
    def addPlot(self):
        """Add a new plot to the current graph."""
        self.xdata = []
        self.ydata = []
        self.currentPlot += 1
        self.plotData.append(
            self.axes.plot(self.xdata, self.ydata,
                           linewidth=1, marker='s',
                           color=COLORS[self.currentPlot%NUMCOL])[0])
    
    def onExit(self, event):
        """Destroy the panel."""
        self.Destroy()
