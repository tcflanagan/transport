import wx
from src.core import experiment
MARK_CONSTANT = experiment.MARK_CONSTANT
MARK_COLUMN = experiment.MARK_COLUMN
MARK_PARAMETER = experiment.MARK_PARAMETER

class CalculateDialog(wx.Dialog):
    def __init__(self, parent, experiment):
        super(CalculateDialog,self).__init__(parent)
        
        self.e = experiment
        self.__makeUi()
        self.__addBindings()
        
    def __makeUi(self):
        
        data = self.e.getStorageBinNames()
        
        directions = 'Enter an expression. Expressions may include the ' + \
        'standard mathematical functions and any constants, parameters, or ' + \
        'columns you have defined. Names of constants should be surrounded ' + \
        'by ' + MARK_CONSTANT + 's; Names of parameters should be surrounded ' + \
        'by ' + MARK_PARAMETER + 's; and names of columns should be surrounded ' + \
        'by ' + MARK_COLUMN + 's.'
        
        dirpanel = wx.Panel(self)
        dirsizer = wx.BoxSizer(wx.VERTICAL)
        dirpanel.SetSizer(dirsizer)
        
        dirtext = wx.StaticText(dirpanel, label = directions)
        dirtext.Wrap(self.GetSizeTuple()[0]*0.85)
        dirsizer.Add(dirtext, flag=wx.ALL, border=5)
        
        exprpanel = wx.Panel(self)
        exprsizer = wx.StaticBoxSizer( wx.StaticBox( exprpanel, wx.ID_ANY, "Expression" ), wx.VERTICAL )
        exprpanel.SetSizer(exprsizer)
        
        self.exprbox = wx.TextCtrl(wx.TE_MULTILINE)
        exprsizer.Add(self.exprbox, proportion=1, flag=wx.EXPAND)
        
        bottompanel = wx.Panel(self)
        bottomsizer = wx.BoxSizer(wx.HORIZONTAL)
        bottompanel.SetSizer(bottomsizer)
        
        constpanel = wx.Panel(bottompanel)
        constsizer = wx.StaticBoxSizer( wx.StaticBox( constpanel, wx.ID_ANY, "Constants" ), wx.VERTICAL )
        constpanel.SetSizer(constsizer)
        
        self.constbox = wx.ListBox(constpanel)
        self.constbox.SetItems(data[0])
        constsizer.Add(self.constbox, proportion=1, flag=wx.EXPAND)
        bottomsizer.Add(constpanel)
        
        colpanel = wx.Panel(bottompanel)
        colsizer = wx.StaticBoxSizer( wx.StaticBox( colpanel, wx.ID_ANY, "Columns" ), wx.VERTICAL )
        colpanel.SetSizer(colsizer)
        
        self.colbox = wx.ListBox(colpanel)
        self.colbox.SetItems(data[1])
        colsizer.Add(self.colbox, proportion=1, flag=wx.EXPAND)
        bottomsizer.Add(colpanel)
        
        parampanel = wx.Panel(bottompanel)
        paramsizer = wx.StaticBoxSizer( wx.StaticBox( parampanel, wx.ID_ANY, "Parameters" ), wx.VERTICAL )
        parampanel.SetSizer(paramsizer)
        
        self.parambox = wx.ListBox(parampanel)
        self.parambox.SetItems(data[2])
        paramsizer.Add(self.parambox, proportion=1, flag=wx.EXPAND)
        bottomsizer.Add(parampanel)
        
        bpanel = wx.Panel(self, wx.ID_ANY)
        bsizer = wx.BoxSizer(wx.HORIZONTAL)
        bpanel.SetSizer(bsizer)
 
        self.btnOk = wx.Button(bpanel, wx.ID_OK, label="OK")
        self.btnCancel = wx.Button(bpanel, wx.ID_CANCEL, label="Cancel", id=wx.ID_CANCEL)
        bsizer.Add(self.btnOk, proportion=0, flag=wx.ALL, border=5)
        bsizer.Add(self.btnCancel, proportion=0, flag=wx.ALL, border=5)
        self.btnOk.Bind(wx.EVT_BUTTON, self.onClose)
        self.btnCancel.Bind(wx.EVT_BUTTON, self.onClose)
        
        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainsizer.Add(dirpanel, proportion=0, flag=wx.ALL, border=5)
        mainsizer.Add(exprpanel, proportion=1, flag=wx.EXPAND|wx.ALL, border=5)
        mainsizer.Add(bottompanel, proportion=1, flag=wx.EXPAND|wx.ALL, border=5)
        mainsizer.Add(bpanel, proportion=0, flag=wx.ALL, border=5)
        
        
        self.AutoLayout(True)
        self.SetSizer(mainsizer)
        self.Layout()
        
    def __addBindings(self):
        self.Bind(wx.EVT_CLOSE, self.__onClose)
        self.Bind(wx.EVT_BUTTON, self.__onClose, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.__onClose, id=wx.ID_CANCEL)
        
    
    def __onClose(self, evt):
        self.EndModal(evt.GetId())
        self.Destroy()