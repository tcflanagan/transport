"""A frame for getting information about various experiment properties.

This exists for testing purposes.
"""

import functools
import wx

class TestingFrame(wx.Frame):
    
    def __init__(self, parent, experiment):
        
        super(TestingFrame, self).__init__(parent, title='Testing Frame')
        self.experiment = experiment
        
        mainpanel = wx.Panel(self)
        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainpanel.SetSizer(mainsizer)
        
        self.textControl = wx.TextCtrl(mainpanel, -1, 
                                       style=wx.TE_MULTILINE|wx.TE_DONTWRAP)
        font = wx.Font(10, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Monospace')
        self.textControl.SetFont(font)
        self.textControl.SetMinSize((400, 400))
        mainsizer.Add(self.textControl, 1, wx.EXPAND|wx.ALL, 5)
        
        buttonpanel = wx.Panel(mainpanel)
        buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonpanel.SetSizer(buttonsizer)
        mainsizer.Add(buttonpanel, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        
        addButton = functools.partial(createButton, buttonpanel, buttonsizer)
        addButton('Clear', self.__onClear)
        addButton('Print Sequence', self.__onSequence)
        addButton('Print Column Details', self.__onColumns)
        addButton('Print XML', self.__onXML)
        addButton('Print bin names', self.__onBinNames)
        
        outersizer = wx.BoxSizer(wx.VERTICAL)
        outersizer.Add(mainpanel, 1, wx.EXPAND)
        self.SetSizerAndFit(outersizer)
    
    def __appendText(self, text):
        """Append text to the control."""
        self.textControl.SetValue(self.textControl.GetValue() + '\n' + text)
        
    def __onClear(self, event):
        """Clear the text."""
        self.textControl.SetValue('')
        
    def __onSequence(self, event):
        """Show the sequence text."""
        self.__appendText(self.experiment.getActionRoot().getTreeString())
        
    def __onColumns(self, event):
        """Show details about the columns."""
        self.__appendText(self.experiment.getColumnDetails())
        
    def __onXML(self, event):
        """Show the experiment's XML data."""
        self.__appendText(self.experiment.getXML())
        
    def __onBinNames(self, event):
        self.__appendText(self.experiment.getStorageBinNamesString())
                
        
def createButton(panel, sizer, label, handler):
    """Create a wxButton and add it to the appropriate sizer."""
    newButton = wx.Button(panel, wx.ID_ANY, label)
    sizer.Add(newButton, 0, wx.ALL, 2)
    newButton.Bind(wx.EVT_BUTTON, handler)
    return newButton

if __name__ == '__main__':
    app = wx.App(0)
    frame = TestingFrame(None, None)
    frame.Show()
    app.MainLoop()
    
    