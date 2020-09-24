"""A frame for displaying experiment status information."""

# pylint: disable=C0103,W0231
import wx
from wx.lib.newevent import NewEvent

from src.tools.general import Command

class StatusMonitorFrame (wx.Frame):
    """A frame for monitoring the experiment's status in real time.
    
    Parameters
    ----------
    parent : wxFrame
        The frame which is the parent of this frame.
    monitor : StatusMonitor
        The `StatusMonitor` object whose information is displayed in this 
        frame.
    """
    
    def __init__(self, parent, monitor):
        
        super(StatusMonitorFrame, self).__init__(parent, size=(600, 300))
        (self.UpdateEvent, self.EVT_UPDATE) = NewEvent()
        (self.PostEvent, self.EVT_POST) = NewEvent()
        
        mainpanel = wx.Panel(self, wx.ID_ANY)
        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainpanel.SetSizer(mainsizer)
        
        self.pastLog = wx.ListBox(mainpanel, wx.ID_ANY, style=wx.LB_BOTTOM)
        self.current = wx.TextCtrl(mainpanel, wx.ID_ANY, style=wx.TE_MULTILINE)
        mainsizer.Add(self.pastLog, 1, wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, 5)
        mainsizer.Add(self.current, 0, wx.EXPAND|wx.BOTTOM|wx.LEFT|wx.RIGHT, 5)
        self.current.SetMinSize((-1, 50))
        
        outersizer = wx.BoxSizer(wx.VERTICAL)
        outersizer.Add(mainpanel, 1, wx.EXPAND)
        
        self.Bind(wx.EVT_CLOSE, self._onClose)
        self.Bind(self.EVT_UPDATE, self._onUpdate)
        self.Bind(self.EVT_POST, self._onPost)
        
        updateCommand = UpdateCommand(self.UpdateEvent, self)
        postCommand = UpdateCommand(self.PostEvent, self)
        
        monitor.setCommands([updateCommand], [postCommand])
        
    def _onUpdate(self, event):
        """Respond to an update."""
        self.current.SetValue(event.data)
        
    def _onPost(self, event):
        """Respond to a post."""
        self.current.SetValue('')
        self.pastLog.Append(event.data)
        self.pastLog.EnsureVisible(self.pastLog.GetCount()-1)
        
    def _onClose(self, event):
        """Hide the frame."""
        self.Show(False)

class UpdateCommand(Command):
    """A Command subclass for updating the status monitor data."""
    
    def __init__(self, eventClass, window):
        self.eventClass = eventClass
        self.window = window
        
    def execute(self, *args, **kwargs):
        if 'currentMessage' in kwargs:
            data = kwargs['currentMessage']
        else:
            data = kwargs['postedMessage']
        evt = self.eventClass(data=data)
        wx.PostEvent(self.window, evt)
        