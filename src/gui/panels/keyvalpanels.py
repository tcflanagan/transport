'''A panel for configuring the key-value pairs.
'''

import wx
from src.gui import gui_helpers as gh

class KeyValPanel(wx.Panel):
    '''The `ScanPanel` is a graphical way of specifying the points at which an
    `ActionScan` should stop to execute its children.
    
    Parameters
    ----------
    parent : wx.Frame
        The frame which owns the `ScanPanel`.
    initialData : iterable, optional
        The initial array of data points. The format is a sequence of 
        sequences, where each sub-sequence contains three elements: a start 
        point, an end point, and a step size.
    '''
    
    def __init__(self, parent, initialData, noDefault=False):
        super(KeyValPanel, self).__init__(parent)
        
        mainsizer = wx.BoxSizer(wx.HORIZONTAL)
        
        
        self.data = initialData
        self.noDefault = noDefault

        listpanel = wx.Panel(self, wx.ID_ANY)
        listsizer = wx.BoxSizer(wx.VERTICAL)
        listpanel.SetSizer(listsizer)
        
        self.list = gh.KeyValListCtrl(listpanel)
        if len(self.data) > 0:
            self.setData(self.data)

        listsizer.Add(self.list, proportion=1, flag=wx.EXPAND|wx.ALL, border=5)

        navsizer = wx.BoxSizer(wx.VERTICAL)
        navpanel = wx.Panel(self, wx.ID_ANY)
        navpanel.SetSizer(navsizer)
        
        self.navUp = wx.Button(navpanel, id=wx.ID_ANY, label="Up")
        self.navDown = wx.Button(navpanel, id=wx.ID_ANY, label="Down")
        self.navAdd = wx.Button(navpanel, id=wx.ID_ANY, label="Add")
        self.navInsert = wx.Button(navpanel, id=wx.ID_ANY, label="Insert")
        self.navRemove = wx.Button(navpanel, id=wx.ID_ANY, label="Remove")
        
        navsizer.Add(self.navUp, proportion=0, flag=wx.ALL, border=2)
        navsizer.Add(self.navDown, proportion=0, flag=wx.ALL, border=2)
        navsizer.Add(self.navAdd, proportion=0, flag=wx.ALL, border=2)
        navsizer.Add(self.navInsert, proportion=0, flag=wx.ALL, border=2)
        navsizer.Add(self.navRemove, proportion=0, flag=wx.ALL, border=2)
        
        self.navUp.Bind(wx.EVT_BUTTON, self.onMoveUp)
        self.navDown.Bind(wx.EVT_BUTTON, self.onMoveDown)
        self.navAdd.Bind(wx.EVT_BUTTON, self.onAdd)
        self.navInsert.Bind(wx.EVT_BUTTON, self.onInsert)
        self.navRemove.Bind(wx.EVT_BUTTON, self.onRemove)
        self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.onEdit)

        mainsizer.Add(listpanel, proportion=1, flag=wx.EXPAND)
        mainsizer.Add(navpanel, proportion=0, flag=wx.ALL, border=3)
        
        self.SetAutoLayout(True)
        self.SetSizer(mainsizer)
        self.Layout()

    def onMoveUp(self, evt):
        index = self.list.GetFocusedItem()
        if index > 0:
            cpos = self.list.GetFocusedItem()
            self.data.insert(cpos-1, self.data.pop(cpos))
            self.setData(self.data)
            self.list.Focus(cpos-1)
            self.list.Select(cpos-1)
        
        
    def onMoveDown(self, evt):
        index = self.list.GetFocusedItem()
        if index < len(self.data)-1:
            self.data.insert(index+1, self.data.pop(index))
            self.setData(self.data)
            self.list.Focus(index+1)
            self.list.Select(index+1)

        
    def onAdd(self, evt):
        self.data.append(['', '', 'String'])
        self.setData(self.data)
        self.list.Focus(len(self.data)-1)
        self.list.Select(len(self.data)-1)
        self.onEdit(None)

    def onInsert(self, evt):
        cpos = self.list.GetFocusedItem()
        self.data.insert(cpos, ['', '', 'String'])
        self.setData(self.data)
        self.list.Focus(cpos)
        self.list.Select(cpos)
        self.onEdit(None)

#         self.list.InsertStringItem(cpos, '')
#         self.list.SetStringItem(cpos,1,'')
#         self.list.SetStringItem(cpos,2,'')
#         self.list.Focus(cpos)
#         self.list.Select(cpos)
        
    def onRemove(self, evt):
        pos = self.list.GetFocusedItem()
        del self.data[pos]
        self.setData(self.data)
        self.updateCommand(*self.updateArgs)
        
    def onEdit(self, evt):
        pos = self.list.GetFocusedItem()
        keyval = self.data[pos]
        dialog = KeyValDialog(self, keyval, self.noDefault)
        if dialog.ShowModal():
            self.setData(self.data)
            self.updateCommand(*self.updateArgs) 

    
    def setData(self, data):
        self.data = data
        self.list.setValues(data)
        
    def getData(self):
        dat = []
        for row in range(self.list.GetItemCount()):
            c1 = self.list.GetItem(row,col=0).GetText()
            c2 = self.list.GetItem(row,col=1).GetText()
            c3 = self.list.GetItem(row,col=2).GetText()
            dat.append( [c1,c2,c3] )
        return dat

    def bindUpdateAction(self, command, args=()):
        self.updateCommand = command
        self.updateArgs = args

class KeyValDialog(gh.BaseDialog):
    TYPES = ['Number', 'String', 'None']
    TYPES_WITH_NODEFAULT = ['Number', 'String', 'None', 'No Default']
    
    def __init__(self, parent, keyval, noDefault=False):
        super(KeyValDialog, self).__init__(parent)
        
        if noDefault:
            types = KeyValDialog.TYPES_WITH_NODEFAULT
        else:
            types = KeyValDialog.TYPES
            
        self.keyval = keyval
        
        mainpanel = gh.Panel(self, 'flex_grid', None, 3, 2, 5, 5)
        mainsizer = wx.BoxSizer(wx.VERTICAL)
        mainpanel.SetSizer(mainsizer)
        
        sizer = wx.FlexGridSizer(3, 2, 5, 5)
        
        
        self.name = wx.TextCtrl(self, -1)
        self.val = wx.TextCtrl(self, -1)
        self.type = wx.ComboBox(self, -1, style=wx.CB_READONLY, choices=types)
        
        sizer.Add(wx.StaticText(self, -1, 'Name: '), 0, 
                  wx.LEFT|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, 5)
        sizer.Add(self.name, 1, wx.RIGHT|wx.TOP|wx.BOTTOM| wx.EXPAND, 5)
        sizer.Add(wx.StaticText(self, -1, 'Value: '), 0,
                  wx.LEFT|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, 5)
        sizer.Add(self.val, 1, wx.RIGHT|wx.TOP|wx.BOTTOM|wx.EXPAND, 5)
        sizer.Add(wx.StaticText(self, -1, 'Type: '), 0,
                  wx.LEFT|wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT, 5)
        sizer.Add(self.type, 1, wx.RIGHT|wx.TOP|wx.BOTTOM|wx.EXPAND, 5)
        
        self.name.SetValue(self.keyval[0])
        self.val.SetValue(self.keyval[1])
        self.type.SetValue(self.keyval[2])
        
        mainsizer.Add(sizer, 1, wx.EXPAND|wx.ALL, 5)
        
        self.setPanel(mainpanel)
        
    def update(self):
        self.keyval[0] = self.name.GetValue()
        self.keyval[1] = self.val.GetValue()
        self.keyval[2] = self.type.GetValue()
            
        return True
    
        