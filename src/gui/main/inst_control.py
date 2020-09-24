"""Tools for loading instrument controllers."""

import imp
import os
import wx

from src.tools import path_tools as pt

_PREFER_COMPILED = False

DIR = pt.unrel('src', 'gui', 'instruments')

class ControllerFrame(wx.Frame):
    """A frame for introspection."""
    MODEL = 'Unknown'
    def __init__(self, *args, **kwargs):
        super(ControllerFrame, self).__init__(*args, **kwargs)
        
def _loadInstrumentControllers():
    """Load the functions available to the postprocessor environment.
    
    Returns
    -------
    dict
        A dictionary in which the keys are the names of the various instruments
        and the values are the graphical controller frame objects.
    """
    controllers = {}
    data = pt.getSourceFiles(DIR)
    for modname in data:
        fname = os.path.join(DIR, modname)
        module = None
        if _PREFER_COMPILED:
            if data[modname]['.pyo']:
                module = imp.load_compiled(modname, fname + '.pyo')
            elif data[modname]['.pyc']:
                module = imp.load_compiled(modname, fname + '.pyc')
            elif data[modname]['.py']:
                module = imp.load_source(modname, fname + '.py')
        else:
            if data[modname]['.py']:
                module = imp.load_source(modname, fname + '.py')
            elif data[modname]['.pyo']:
                module = imp.load_compiled(modname, fname + '.pyo')
            elif data[modname]['.pyc']:
                module = imp.load_compiled(modname, fname + '.pyc')
                
        if module is None:
            continue
        
        for item in module.__dict__:
            curr = getattr(module, item)
            if (isinstance(curr, type) and 
                    curr is not ControllerFrame and
                    issubclass(curr, ControllerFrame)):
                controllers[curr.MODEL] = curr
    return controllers

INSTRUMENT_CONTROLLERS = _loadInstrumentControllers()