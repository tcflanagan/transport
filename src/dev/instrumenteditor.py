'''A program for creating and editing instrument implementations.
'''
import wx
import re
import os
import shutil
from collections import namedtuple

from src.gui import gui_helpers as gh
from src.gui.panels.keyvalpanels import KeyValPanel
from src.tools import path_tools as pt
from src.tools import instrospection as inst

from src.core.configuration import openEditor

__all__ = ['InstrumentFrame', 'InstrumentPanel', 'ActionPanel', 
           'ParameterDialog']

    
DEFAULT_BLANK_PATH = pt.unrel('src', 'instruments', 'newinstrument.py')
DEFAULT_BLANK_INSTRUMENT = """'''Some new instrument
'''
__all__ = ['NewInstrument']

from src.core.instrument import Instrument
from src.core.action import Action
from src.core.action import ActionScan
from src.core.action import Parameter
from src.instruments.pyvisa import visa


class NewInstrument(Instrument):
    
    def __init__ (self, experiment, name='Unknown Instrument', spec=None):
        super(NewInstrument,self).__init__(experiment, name, spec)
    
    def initialize (self):
        self.__instrument = visa.instrument(self.getSpecification()['Address'])
        self.__info = 'Instrument: ' + self.getName()
        self.__info += 'Unknown Instrument'
        self.__info += '\\n' + self.__instrument.ask('*IDN?')
    
    def getAddress (self):
        return self.getSpecification()['Address']
    
    def getInformation (self):
        return self.__info
        
    def getActions (self):
        return [
        ]
    #===========================================================================
    # Class methods
    #===========================================================================
    @classmethod
    def getRequiredParameters (cls):
        return { 'order'   : ['Address'],
                 'Address' : 'GPIB::9' }
"""


FORMATS = ['Exponential', 'Float', 'Integer', 'String']
TYPES = ['Column', 'Parameter', 'None']


# KNOWN ISSUES
# Deleting instrument parameters doesn't work right.
# Methd names in the aciton panel are not update to reflect changes in the
#    instrument panel

ID_ACTADD = wx.NewId()
ID_ACTEDIT = wx.NewId()
ID_ACTDEL = wx.NewId()
ID_INADD = wx.NewId()
ID_INEDIT = wx.NewId()
ID_INDEL = wx.NewId()
ID_OUTADD = wx.NewId()
ID_OUTEDIT = wx.NewId()
ID_OUTDEL = wx.NewId()

KVTuple = namedtuple('KVTuple', ['name', 'value', 'type'])

def unquote(string):
    if ((string.startswith("'") and string.endswith("'")) or
        (string.startswith('"') and string.endswith('"'))):
        return string[1:-1]
    return string
def requote(string):
    return "'" + string + "'"

def unself(string):
    if string.startswith('self.'):
        return string[5:]
    return string
def reself(string):
    return 'self.' + string
        

class ParameterDialog(gh.BaseDialog):
    
    def __init__(self, parent, parameter):
        super(ParameterDialog, self).__init__(parent, id=wx.ID_ANY)
        self.parameter = parameter
        
        parpanel = wx.Panel(self)
        parsizer = wx.FlexGridSizer(5, 2, 5, 5)
        parpanel.SetSizer(parsizer)
        
        formatpanel = wx.Panel(parpanel)
        formatsizer = wx.BoxSizer(wx.HORIZONTAL)
        formatpanel.SetSizer(formatsizer)
        
        labels = ['Name', 'Description', 'Format', 'Default Storage Name',
                  'Default Storage Type', 'Default Value', 'Allowed Values']
        
        self.name = wx.TextCtrl(parpanel, -1)
        self.description = wx.TextCtrl(parpanel, -1)
        self.format = wx.ComboBox(formatpanel, -1, value='Exponential',
                                  choices=FORMATS, style=wx.CB_READONLY)
        self.precision = wx.TextCtrl(formatpanel, -1)
        self.binname = wx.TextCtrl(parpanel, -1)
        self.bintype = wx.ComboBox(parpanel, -1, value='Column',
                                   choices=TYPES, style=wx.CB_READONLY)
        self.value = wx.TextCtrl(parpanel, -1)
        self.allowed = wx.TextCtrl(parpanel, -1, style=wx.TE_MULTILINE)
        
        formatsizer.Add(self.format, 2, wx.EXPAND)
        formatsizer.Add(wx.StaticText(formatpanel, -1, label='   Precision: '),
                        0, wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        formatsizer.Add(self.precision, 1, wx.EXPAND)
        
        controls = [self.name, self.description, formatpanel, self.binname,
                    self.bintype, self.value, self.allowed]
        
        for label, control in zip(labels, controls):
            statictext = wx.StaticText(parpanel, -1, label=label+': ')
            if control is self.allowed: AL = wx.ALIGN_TOP
            else: AL = wx.ALIGN_CENTER_VERTICAL
            parsizer.Add(statictext, 0, AL|wx.ALIGN_RIGHT)
            parsizer.Add(control, 1, wx.ALIGN_CENTER_VERTICAL|wx.EXPAND)
        
        parsizer.AddGrowableRow(6,2)

        
        self.setPanel(parpanel)
        self.insertValues()

    def insertValues(self):
        self.name.SetValue(unquote(self.parameter.name))
        self.description.SetValue(unquote(self.parameter.description))
        
        pattern = re.compile(r'%(.*)\.(\d*)(\w)')
        format_string = self.parameter.format_string
        match = pattern.search(format_string)
        if match:
            value_type = match.group(3)
            value_precision = match.group(2)
        else:
            pattern = re.compile(r'(\w)')
            match = pattern.search(format_string)
            value_type = match.group(1)
            value_precision = ''
        
        if 'd' == value_type:
            self.format.SetValue('Integer')
        elif 'e' == value_type:
            self.format.SetValue('Exponential')
        elif 'f' == value_type:
            self.format.SetValue('Float')
        else:
            self.format.SetValue('String')
        if '.' in format_string:
            self.precision.SetValue(value_precision)
        
        if self.format.GetValue() == 'String':
            self.value.SetValue(unquote(self.parameter.value))
        else:
            self.value.SetValue(self.parameter.value)
        
        bt = self.parameter.bin_type
        if bt == "'column'":
            self.bintype.SetValue('Column')
        elif bt == "'parameter'":
            self.bintype.SetValue('Parameter')
        else:
            self.bintype.SetValue('None')
        self.binname.SetValue(unquote(self.parameter.bin_name))
    
    def update(self):
        self.parameter.name = requote(self.name.GetValue())
        self.parameter.description = requote(self.description.GetValue())
        binname = self.binname.GetValue().strip()
        bintype = self.bintype.GetValue()
        if bintype == 'None':
            self.parameter.bin_name = 'None'
            self.parameter.bin_type = 'None'
            self.binname.SetValue('')
        else:
            self.parameter.bin_name = binname
            self.parameter.bin_type = bintype
        if self.format.GetValue() == 'String':
            self.parameter.value = requote(self.value.GetValue())
        else:
            self.parameter.value = self.value.GetValue()
        
        format_string = '%'
        fm = self.format.GetValue()
        pre = self.precision.GetValue()
        if fm == 'Float':
            format_string += '.' + pre + 'f'
        elif fm == 'Exponential':
            format_string += '.' + pre + 'e'
        elif fm == 'Integer':
            format_string += 'd'
        else:
            format_string += 's'
        self.parameter.format_string = requote(format_string)
        return True

class ActionPanel(wx.Panel):
    def __init__(self, parent, instr):
        super(ActionPanel, self).__init__(parent, wx.ID_ANY)
        
        self.instrument = instr
        self.actionlist = instr.actions
        self.inputlist = []
        self.outputlist = []
        
        
        mainsizer = wx.BoxSizer(wx.HORIZONTAL)
        
        browsepanel = wx.Panel(self)
        browsesizer = wx.BoxSizer(wx.VERTICAL)
        browsepanel.SetSizer(browsesizer)
        
        browsebuttonpanel = wx.Panel(browsepanel)
        browsebuttonsizer = wx.BoxSizer(wx.HORIZONTAL)
        browsebuttonpanel.SetSizer(browsebuttonsizer)
        
        actionpanel = wx.Panel(self)
        actionsizer = wx.BoxSizer(wx.VERTICAL)
        actionpanel.SetSizer(actionsizer)
                
        detailpanel = wx.Panel(actionpanel, wx.ID_ANY)
        detailsizer = wx.FlexGridSizer(3, 2, 5, 5)
        detailpanel.SetSizer(detailsizer)
        detailsizer.AddGrowableCol(1,1)
        
        bottompanel = wx.Panel(actionpanel, wx.ID_ANY)
        bottomsizer = wx.BoxSizer(wx.HORIZONTAL)
        bottompanel.SetSizer(bottomsizer)
        
        inpanel = wx.StaticBox(bottompanel, wx.ID_ANY, 'Inputs')
        insizer = wx.StaticBoxSizer(inpanel, wx.VERTICAL)
        
        inbuttonpanel = wx.Panel(bottompanel)
        inbuttonsizer = wx.BoxSizer(wx.HORIZONTAL)
        inbuttonpanel.SetSizer(inbuttonsizer)
        
        outpanel = wx.StaticBox(bottompanel, wx.ID_ANY, 'Outputs')
        outsizer = wx.StaticBoxSizer(outpanel, wx.VERTICAL)
        
        outbuttonpanel = wx.Panel(bottompanel)
        outbuttonsizer = wx.BoxSizer(wx.HORIZONTAL)
        outbuttonpanel.SetSizer(outbuttonsizer)
        
        #-----------------------------------------------------------------------
        # Create controls
        
        self.actions = wx.ListBox(browsepanel, wx.ID_ANY)
        
        # Action Type
        self.actiontype = wx.RadioBox(actionpanel, wx.ID_ANY, 'Action Type',
                                      choices=['Simple', 'Scan'],
                                      majorDimension=2,
                                      size=(200,-1))
        
        
        # Buttons
        actadd = wx.Button(browsebuttonpanel, ID_ACTADD, 'Add')
        actdel = wx.Button(browsebuttonpanel, ID_ACTDEL, 'Delete')
        
        inadd = wx.Button(inbuttonpanel, ID_INADD, 'Add')
        inedit = wx.Button(inbuttonpanel, ID_INEDIT, 'Edit')
        indel = wx.Button(inbuttonpanel, ID_INDEL, 'Delete')
        
        outadd = wx.Button(outbuttonpanel, ID_OUTADD, 'Add')
        outedit = wx.Button(outbuttonpanel, ID_OUTEDIT, 'Edit')
        outdel = wx.Button(outbuttonpanel, ID_OUTDEL, 'Delete')

        self.btns = [inadd, inedit, indel, outadd, outedit, outdel, 
                     actadd, actdel]
        
        # Data controls
        self.description = wx.TextCtrl(detailpanel, wx.ID_ANY)
        self.string = wx.TextCtrl(detailpanel, wx.ID_ANY)
        self.method = wx.ComboBox(detailpanel, wx.ID_ANY, style=wx.CB_READONLY)
        
        self.inputs = wx.ListBox(bottompanel, wx.ID_ANY)
        self.outputs = wx.ListBox(bottompanel, wx.ID_ANY)
        
        #-----------------------------------------------------------------------
        # Add bindings
        
        self.actions.Bind(wx.EVT_LISTBOX, self._onSelectAction)
        self.actiontype.Bind(wx.EVT_RADIOBOX, self._changeType)
        self.inputs.Bind(wx.EVT_LISTBOX, self._updateButtons)
        self.outputs.Bind(wx.EVT_LISTBOX, self._updateButtons)
        self.description.Bind(wx.EVT_KILL_FOCUS, self._onUpdateDescription)
        self.string.Bind(wx.EVT_KILL_FOCUS, self.saveDetails)
        self.method.Bind(wx.EVT_KILL_FOCUS, self.saveDetails)
        
        actadd.Bind(wx.EVT_BUTTON, self._onAddAction)
        actdel.Bind(wx.EVT_BUTTON, self._onRemoveAction)
        
        for btn in self.btns[0:6]:
            btn.Bind(wx.EVT_BUTTON, self._onButton)
        
        
        #-----------------------------------------------------------------------
        # Add controls to panels
        
        
        detailsizer.Add(wx.StaticText(detailpanel, label='Description:'), 
                     0, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        detailsizer.Add(self.description, 1, wx.EXPAND)
        detailsizer.Add(wx.StaticText(detailpanel, label='Template String:'),
                     0, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        detailsizer.Add(self.string, 1, wx.EXPAND)
        detailsizer.Add(wx.StaticText(detailpanel, label='Method:'),
                     0, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        detailsizer.Add(self.method, 1, wx.EXPAND)
        
        browsebuttonsizer.Add(actadd, 0, wx.ALL, 2)
        browsebuttonsizer.Add(actdel, 0, wx.ALL, 2)
        browsesizer.Add(wx.StaticText(browsepanel, label='Actions:'),
                        0, wx.ALL, 3)
        browsesizer.Add(self.actions, 1, wx.EXPAND|wx.ALL, 5)
        browsesizer.Add(browsebuttonpanel, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 5)
        
        inbuttonsizer.Add(inadd, 0, wx.ALL, 2)
        inbuttonsizer.Add(inedit, 0, wx.ALL, 2)
        inbuttonsizer.Add(indel, 0, wx.ALL, 2)
        insizer.Add(self.inputs, 1, wx.EXPAND|wx.ALL, 5)
        insizer.Add(inbuttonpanel, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 5)
        
        outbuttonsizer.Add(outadd, 0, wx.ALL, 2)
        outbuttonsizer.Add(outedit, 0, wx.ALL, 2)
        outbuttonsizer.Add(outdel, 0, wx.ALL, 2)
        outsizer.Add(self.outputs, 1, wx.EXPAND|wx.ALL, 5)
        outsizer.Add(outbuttonpanel, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 5)
        
        bottomsizer.Add(insizer, 1, wx.EXPAND|wx.ALL, 5)
        bottomsizer.Add(outsizer, 1, wx.EXPAND|wx.ALL, 5)
        
        actionsizer.Add(self.actiontype, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5)
        actionsizer.Add(detailpanel, 0, wx.ALL|wx.EXPAND, 5)
        actionsizer.Add(bottompanel, 1, wx.ALL|wx.EXPAND, 5)
        
        mainsizer.Add(browsepanel, 0, wx.ALL|wx.EXPAND, 5)
        mainsizer.Add(actionpanel, 1, wx.ALL|wx.EXPAND, 5)
        
        self.SetSizer(mainsizer)
        
        self.updateMethodList()
        self.updateActionList()
        if len(self.actionlist) > 0:
            self.currentaction = self.actionlist[0]
            self.actions.SetSelection(0)
            self.setDetails()
        
    def updateActionList(self):
        actionstrings = []
        for item in self.actionlist:
            actionstrings.append(unquote(item.description))
        self.actions.SetItems(actionstrings)
        
    def setDetails(self):
        action = self.currentaction
        
        if action.action_type == 'Scan':
            self.actiontype.SetSelection(1)
        else:
            self.actiontype.SetSelection(0)
            
        self.description.SetValue(unquote(action.description))
        self.string.SetValue(unquote(action.string))
        if action.method is None:
            self.method.SetValue('')
        else:
            self.method.SetValue(unself(action.method))
        self.inputlist = action.inputs
        self.outputlist = action.outputs
        
        inputnames = []
        outputnames = []
        for item in self.inputlist:
            inputnames.append(unquote(item.name) + ': ' + unquote(item.description))
        for item in self.outputlist:
            outputnames.append(unquote(item.name) + ': ' + unquote(item.description))
            
        self.inputs.SetItems(inputnames)
        self.outputs.SetItems(outputnames)
    
    def saveDetails(self, event=None):
        action = self.currentaction
        action.description = requote(self.description.GetValue())
        action.string = requote(self.string.GetValue())
        if self.method.GetValue() == '':
            action.method = None
        else:
            action.method = reself(self.method.GetValue())
        
        if self.actiontype.GetSelection() == 1:
            action.action_type = 'Scan'
        else:
            action.action_type = ''
    
    def updateMethodList(self):
        methods = instrument.getMethods()
        method_names = []
        for method in methods:
            method_names.append(unself(method.name))
        self.method.SetItems(method_names)
        
    def _onSelectAction(self, event):
        index = self.actions.GetSelection()
        self.currentaction = self.actionlist[index]
        self.setDetails()
        self._updateButtons()
        
    def _onUpdateDescription(self, event):
        event.Skip()
        index = self.actions.GetSelection()
        self.currentaction.description = requote(self.description.GetValue())
        self.actions.SetString(index, unquote(self.currentaction.description))
            
    def _updateButtons(self, event=None):
        btns = self.btns
        try:
            if self.actiontype.GetSelection() == 1:
                for btn in btns[2:6]:
                    btn.Enable(False)
                if len(self.inputlist) >= 1:
                    btns[0].Enable(False)
                    self.inputs.SetSelection(0)
                    btns[1].Enable()
                else:
                    btns[0].Enable(True)
                    btns[1].Enable(False)
            else:
                btns[0].Enable(True)
                if self.inputs.GetSelection() >= 0:
                    btns[1].Enable(True)
                    btns[2].Enable(True)
                else:
                    btns[1].Enable(False)
                    btns[2].Enable(False)
                btns[3].Enable(True)
                if self.outputs.GetSelection() >= 0:
                    btns[4].Enable(True)
                    btns[5].Enable(True)
                else:
                    btns[4].Enable(False)
                    btns[5].Enable(False)
        except (wx.PyDeadObjectError, wx.PyAssertionError):
            pass
        
    def _changeType(self, event):
        newtype = self.actiontype.GetSelection()
        if newtype == 1:
            if len(self.outputlist) > 0 or len(self.inputlist) > 1:
                dialog = wx.MessageDialog(self, 'Scan actions must have one ' + 
                                          'and only one input value, and ' + 
                                          'they may not have any output' + 
                                          'values.', 'Error', 
                                          style=wx.OK|wx.ICON_ERROR)
                dialog.ShowModal()
                self.actiontype.SetSelection(0)
                
                self.currentaction.action_type = 'Scan'
            else:
                self.actiontype.SetSelection(1)
                self.currentaction.action_type = 'Scan'
                self._updateButtons(None)
        else:
            self.currentaction.type = ''
            self.actiontype.SetSelection(0)
            self._updateButtons(None)
            
    def _onAddAction(self, event):
        self.instrument.addAction()
        self.updateActionList()
        self.currentaction = self.actionlist[-1]
        self.actions.SetSelection(self.actions.GetCount()-1)
        
    def _onRemoveAction(self, event):
        index = self.actions.GetSelection()
        self.instrument.removeAction(index)
        self.updateActionList()
    
    def _onButton(self, event):
        ID = event.GetId()
        if ID == ID_INDEL:
            index = self.inputs.GetSelection()
            del self.inputlist[index]
            self.setDetails()
        elif ID == ID_OUTDEL:
            index = self.outputs.GetSelection()
            del self.outputlist[index]
            self.setDetails()
        else:
            if ID == ID_INADD or ID == ID_OUTADD:
                param = inst.Parameter(None)
            elif ID == ID_INEDIT:
                param = self.inputlist[self.inputs.GetSelection()]
            elif ID == ID_OUTEDIT:
                param = self.outputlist[self.outputs.GetSelection()]
            pd = ParameterDialog(self, param)
            if ID == ID_INADD:
                if pd.ShowModal():
                    self.inputlist.append(param)
            elif ID == ID_OUTADD:
                if pd.ShowModal():
                    self.outputlist.append(param)
            else:
                pd.ShowModal()
            self.setDetails()
                

class InstrumentPanel(wx.Panel):
    def __init__(self, parent, instrument):
        super(InstrumentPanel, self).__init__(parent)

        self.instrument = instrument
        
        methpanel = wx.StaticBox(self, wx.ID_ANY, 'Methods')
        methsizer = wx.StaticBoxSizer(methpanel, wx.HORIZONTAL)
        
        methdetpanel = wx.Panel(self)
        methdetsizer = wx.BoxSizer(wx.VERTICAL)
        methdetpanel.SetSizer(methdetsizer)
        
        instpanel = wx.StaticBox(self, wx.ID_ANY, 'Instrument Settings')
        instsizer = wx.StaticBoxSizer(instpanel, wx.VERTICAL)
        
        self.methlist = wx.ListBox(self, -1)
        self.methname = wx.TextCtrl(methdetpanel, -1)
        self.methargs = KeyValPanel(methdetpanel,
                                    self.instrument.getMethods()[0].getArguments(),
                                    True)
        self.methargs.bindUpdateAction(self._onChangeMethArgs, (None, ))
        self.methname.Bind(wx.EVT_KILL_FOCUS, self._onNameMethod)
        
        methbtnpanel = wx.Panel(methdetpanel, -1)
        methbtnsizer = wx.BoxSizer(wx.HORIZONTAL)
        methbtnpanel.SetSizer(methbtnsizer)
        
        self.methadd = wx.Button(methbtnpanel, -1, 'Add Method')
        self.methdel = wx.Button(methbtnpanel, -1, 'Delete Method')
        h = self.methdel.GetSizeTuple()[1]
        ln = wx.StaticLine(methbtnpanel, -1, size=(1,h), style=wx.LI_VERTICAL)
        self.methcode = wx.Button(methbtnpanel, -1, 'Edit Code')
        self.methadd.Bind(wx.EVT_BUTTON, self._onAddMethod)
        self.methdel.Bind(wx.EVT_BUTTON, self._onRemoveMethod)
        self.methcode.Bind(wx.EVT_BUTTON, self._onEditCode)
        
        methbtnsizer.Add(self.methadd, 0, wx.ALL, 5)
        methbtnsizer.Add(self.methdel, 0, wx.ALL, 5)
        methbtnsizer.Add
        methbtnsizer.Add(ln, 0, wx.ALL, 5)
        methbtnsizer.Add(self.methcode, 0, wx.ALL, 5)
        
        
        self.instclass = wx.TextCtrl(self, -1)
        self.instname = wx.TextCtrl(self, -1)
        self.instparams = KeyValPanel(self, 
                                      self.instrument.getRequiredParameters(),
                                      False)
        self.instparams.bindUpdateAction(self._onChangeInstParams, (None,))
        self.instclass.Bind(wx.EVT_KILL_FOCUS, self._onChangeInstrumentName)
        self.instname.Bind(wx.EVT_KILL_FOCUS, self._onChangeDefaultName)
        
        instsizer.Add(wx.StaticText(self, -1, 'Instrument Class:'),
                      0, wx.ALL, 5)
        instsizer.Add(self.instclass, 0, wx.EXPAND|wx.LEFT, 10)
        instsizer.Add(wx.StaticText(self, -1, 'Default Name:'),
                      0, wx.ALL, 5)
        instsizer.Add(self.instname, 0, wx.EXPAND|wx.LEFT, 10)
        instsizer.Add(wx.StaticText(self, -1, 'Required Parameters:'),
                      0, wx.ALL, 5)
        instsizer.Add(self.instparams, 1, wx.EXPAND|wx.LEFT, 10)
        
        methdetsizer.Add(wx.StaticText(methdetpanel, -1, 'Method name: '),
                         0, wx.ALL, 5)
        methdetsizer.Add(self.methname, 0, wx.LEFT|wx.EXPAND, 10)
        methdetsizer.Add(wx.StaticText(methdetpanel, -1, 'Arguments (space-separated):'),
                         0, wx.ALL, 5)
        methdetsizer.Add(self.methargs, 1, wx.LEFT|wx.EXPAND, 10)
        methdetsizer.Add(methbtnpanel, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 5)
        
        methsizer.Add(self.methlist, 1, wx.EXPAND|wx.ALL, 5)
        methsizer.Add(methdetpanel, 2, wx.EXPAND|wx.ALL, 5)
    
    
        mainsizer = wx.BoxSizer(wx.HORIZONTAL)
        mainsizer.Add(instsizer, 2, wx.EXPAND|wx.ALL, 5)
        mainsizer.Add(methsizer, 3, wx.EXPAND|wx.ALL, 5)
        
        self.updateInstrumentData()
        self.updateMethodList()
        self.methlist.Bind(wx.EVT_LISTBOX, self._onSelectMethod)
        
        
        self.instrument = instrument
        self.methods = instrument.getMethods()
        self.currmethod = self.methods[0]
        self.updateMethodDetails()
        
        self.SetSizerAndFit(mainsizer)
        
    def updateInstrumentData(self):
        self.instclass.SetValue(self.instrument.name)
        self.instname.SetValue(self.instrument.getDefaultName())
        
    def updateMethodList(self):
        oldselection = self.methlist.GetSelection()
        self.methods = self.instrument.getMethods()
        method_strings = []
        for method in self.methods:
            method_strings.append(method.name)
        self.methlist.SetItems(method_strings)
        self.methlist.SetSelection(oldselection)
        
    def updateMethodDetails(self):
        try:
            self.methname.SetValue(self.currmethod.name)
            self.methargs.setData(self.currmethod.getArguments())
        except wx.PyDeadObjectError:
            pass
        
    def _onChangeInstParams(self, event):
        self.instrument.setRequiredParameters(self.instparams.getData())
        
    def _onChangeMethArgs(self, event):
        self.currmethod.setArguments(self.methargs.getData())
                
    def _onSelectMethod(self, event):
        self.currmethod = self.methods[self.methlist.GetSelection()]
        self.updateMethodDetails()
        
    def _onNameMethod(self, event):
        newname = self.methname.GetValue()
        index = self.methlist.GetSelection()
        if ' ' in newname:
            dialog = wx.MessageDialog(self, 'Method names may not ' + 
                                      'contain spaces', 'Error', style=wx.OK|wx.ICON_ERROR)
            dialog.ShowModal()
            self.methname.SetValue(self.currmethod.name)
        else:
            self.currmethod.name = self.methname.GetValue()
            self.methlist.SetString(index, self.currmethod.name)

        
    def _onAddMethod(self, event):
        newmethod = self.instrument.addMethod('pleaseNameMe')
        self.updateMethodList()
        self.currmethod = newmethod
        self.methlist.SetSelection(self.methods.index(newmethod))
        self.updateMethodDetails()
        
    def _onRemoveMethod(self, event):
        self.instrument.deleteMethod(self.currmethod.name)
        self.updateMethodList()
        self.currmethod = self.methods[0]
        self.methlist.SetSelection(0)
        self.updateMethodDetails()
        
    def _onEditCode(self, event):
        data = openEditor(self.currmethod.body)
        
        self.currmethod.body = data
        
    def _onChangeInstrumentName(self, event):
        newname = self.instclass.GetValue()
        self.instrument.name = newname
        self.GetParent().setAll(newname)

    def _onChangeDefaultName(self, event):
        newname = requote(self.instname.GetValue())
        self.instrument.setDefaultName(newname)

class InstrumentNotebook(wx.Notebook):
    def __init__(self, parent, module):
        super(InstrumentNotebook, self).__init__(parent, wx.ID_ANY,
                                              style=wx.BK_DEFAULT)
        
        self.module = module
        instrument = module.getInstruments()[0]
        
        insttab = InstrumentPanel(self, instrument)
        self.AddPage(insttab, 'Instrument')
        
        actiontab = ActionPanel(self, instrument)
        self.AddPage(actiontab, 'Actions')
        
    def setAll(self, newvalue):
        self.module.setAll(newvalue)
        
class InstrumentFrame(wx.Frame):
    def __init__(self, parent, module):
        super(InstrumentFrame, self).__init__(parent)
        
        self.module = module
        
        menubar = wx.MenuBar()
        
        filemenu = wx.Menu()
        fileNew = filemenu.Append(wx.ID_NEW, 'New', 'Create a new instrument.')
        fileOpen = filemenu.Append(wx.ID_OPEN, 'Open', 'Open an existing instrument.')
        filemenu.AppendSeparator()
        filePreview = filemenu.Append(wx.ID_PREVIEW, 'Preview', 'Preview the new code.')
        fileSave = filemenu.Append(wx.ID_SAVE, 'Save', 'Save the current instrument.')
        filemenu.AppendSeparator()
        fileExit = filemenu.Append(wx.ID_EXIT, 'Exit', 'Exit the instrument tool.')
        
        self.Bind(wx.EVT_MENU, self.onNew, fileNew)
        self.Bind(wx.EVT_MENU, self.onOpen, fileOpen)
        self.Bind(wx.EVT_MENU, self.onPreviewCode, filePreview)
        self.Bind(wx.EVT_MENU, self.onSave, fileSave)
        self.Bind(wx.EVT_MENU, self.onClose, fileExit)
        
        self.Bind(wx.EVT_CLOSE, self.onClose)
        
                
        menubar.Append(filemenu, 'File')
        self.SetMenuBar(menubar)
        
        notebook = InstrumentNotebook(self, module)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(notebook, 1, wx.ALL|wx.EXPAND, 5)
        
        self.SetSizerAndFit(sizer)
        
    def onPreviewCode(self, event):
        code = self.module.toCode(0)
        openEditor(code)
        
    def onOpen(self, event):
        dialog = wx.FileDialog(self, 'Open an Instrument', 
                               pt.unrel('src','instruments'), '',
                               'Instrument files (*.py)|*.py', 
                               wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
        if dialog.ShowModal() == wx.ID_OK:
            path = dialog.GetPath()
            newmodule = inst.Module(path)
            newinstrumentframe = InstrumentFrame(None, newmodule)
            newinstrumentframe.Show()
    
    def onSave(self, event):
        oldpath = self.module.path
        pathlist = pt.normalizePath(oldpath).split('/')
        newname = self.module.getInstruments()[0].name.lower() + '.py'
        newpathlist = pathlist[0:-1] + [newname]
        newpath = '/'.join(newpathlist)
        backuppath = None
        error = False
        if os.path.exists(newpath):
            backuppath = newpath[:-3]+'.bak'
            digit = 0
            while os.path.exists(backuppath):
                backuppath = newpath[:-3] + '.bak' + str(digit)
                digit += 1
            try:
                shutil.move(newpath, backuppath) 
            except (IOError, OSError), e:
                print('Cannot move ' + str(e))
                error = True
        if not error:
            with open(newpath, 'w') as f:
                f.write(self.module.toCode(0))
            print('saved')
        print(newpath)
        
    def onNew(self, event):
        with open(DEFAULT_BLANK_PATH, 'w') as f:
            f.write(DEFAULT_BLANK_INSTRUMENT)
        newmodule = inst.Module(DEFAULT_BLANK_PATH)
        newinstrumentframe = InstrumentFrame(None, newmodule)
        newinstrumentframe.Show()
        
    def onClose(self, event):
        if os.path.exists(DEFAULT_BLANK_PATH):
            os.remove(DEFAULT_BLANK_PATH)
        event.Skip()
        self.Destroy()
        
if __name__ == '__main__':
    fn = pt.unrel('src/instruments/srs830.py')
    module = inst.Module(fn)
    instrument = module.getInstruments()[0]
    actions = instrument.actions
    some_action = actions[0]
    inputs = some_action.inputs
    print(module.contents)
    some_parameter = inputs[1]
    
    app = wx.App(0)
    #pd = ParameterDialog(None, some_parameter)
    #pd.ShowModal()
    
    tf = InstrumentFrame(None, module)
    tf.Show()
    
    app.MainLoop()
