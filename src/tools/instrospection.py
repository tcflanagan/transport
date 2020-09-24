"""A tool for parsing instrument modules."""

import re

from src.tools import path_tools as pt

PATTERN_DOCSTRING1 = re.compile(r'"""(.*?)"""', re.DOTALL)
PATTERN_DOCSTRING2 = re.compile(r"'''(.*?)'''", re.DOTALL)
PATTERN_IMPORT1 = re.compile(r'from +([\.\w_]+) +import +([\.\w_, ]+)\s*\n')
PATTERN_IMPORT2 = re.compile(r'from +([\.\w_]+) +import +'
                             r'([\.\w_]+) +as +([\.\w_]+)\s*\n')
PATTERN_IMPORT3 = re.compile(r'^import +([\.\w_]+)\s*\n', re.M)
PATTERN_IMPORT4 = re.compile(r'^import +([\.\w_]+) +as +([\.\w_]+)\s*\n', re.M)

class Module(object):
    """The class containing the entire contents of the module."""
    
    def __init__(self, filename):
        with open(filename) as fileobject:
            text = fileobject.read()
        self.docstring = Docstring(text)
        self.imports = Imports(text)
        
        
class Docstring(object):
    """A class to contain docstrings.
    
    Parameters
    ----------
    text : str
        The text for the docstring.
    """
    
    def __init__(self, text):
        match = PATTERN_DOCSTRING1.search(text)
        if match:
            textList = match.group(1).split('\n')
            print(repr(textList))
            
            self.summary = textList[0]
            info = textList[1:]
            if len(info) == 0:
                info = ['']
            while len(info[0].strip()) == 0 and len(info) > 1:
                del info
            while len(info[-1].strip()) == 0 and len(info) > 1:
                del info[-1]
            
            self.information = '\n'.join(info)
    
    def toCode(self):
        """Return the text of the docstring.
        
        Returns
        -------
        str
            The new docstring.
        """
        answer = '\n'.join([self.summary, self.information])
        answer = '"""' + answer + '\n"""'
        return answer
        
class Imports(object):
    """The collection of imports."""
    
    def __init__(self, text):
        imports = []
        matches = PATTERN_IMPORT1.findall(text)
        for match in matches:
            imports.append(Import((0, match)))
        matches = PATTERN_IMPORT2.findall(text)
        for match in matches:
            imports.append(Import((1, match)))
        matches = PATTERN_IMPORT3.findall(text)
        for match in matches:
            imports.append(Import((2, (match,))))
        matches = PATTERN_IMPORT4.findall(text)
        for match in matches:
            imports.append(Import((3, match)))
            
        self.standards = []
        self.locals = []
        for item in imports:
            if item.importData[0].startswith('src'):
                self.locals.append(item)
            else:
                self.standards.append(item)
        self.toCode()
        
    def toCode(self):
        self.standards.sort(Import.cmp)
        self.locals.sort(Import.cmp)
        
        ans = []
        for item in Imports.rejoin(self.standards):
            if item not in ans:
                ans.append(item)
        ans.append('')
        for item in Imports.rejoin(self.locals):
            if item not in ans:
                ans.append(item)
        print('\n'.join(ans))
        
    @classmethod
    def rejoin(cls, lst):
        ans = []
        for item in lst:
            kind = item.importType
            data = item.importData
            if kind == 0:
                ans.append('from %s import %s' % data)
            elif kind == 1:
                ans.append('from %s import %s as %s' % data)
            elif kind == 2:
                ans.append('import %s' % data[0])
            else:
                ans.append('import %s as %s' % data)
        return ans
    
class Import(object):
    """A single import command."""
    
    def __init__(self, information):
        self.importType = information[0]
        self.importData = information[1]
        
    def __lt__(self, other):
        """Return whether this import is "less than" some other."""
        mine = self.importData[0]
        his = other.importData[0]
        
        value = compare(mine, his)
        if value == 0:
            return self.importData[1] < other.importData[1]
        return value == -1

    #FIXME Combine this with the compare function from below.
    @classmethod
    def cmp(cls, itemA, itemB):
        mine = itemA.importData[0]
        his = itemB.importData[0]
        
        value = compare(mine, his)
        if value == 0:
            if itemA.importData[1] < itemB.importData[1]:
                return -1
            if itemA.importData[1] > itemB.importData[1]:
                return 1
            return 0
        return value
        
    
class Constants(object):
    """The constants defined in the module."""
    
class Instrument(object):
    """An instrument class"""
    
class Function(object):
    """A module-level function."""
    

def compare(stringA, stringB):
    """Compare two import strings for sorting.
    
    Parameters
    ----------
    stringA : str
        The first import string.
    stringB : str
        The import string to compare with the first.
    
    Returns
    -------
    int
        An integer representing how the first import string compares to the
        second. If the first is smaller, the returned value is -1. If the
        two are the same, 0 is returned. Otherwise, +1 is returned.
    """
    
    stringListA = stringA.split('.')
    stringListB = stringB.split('.')
    for itemA, itemB in zip(stringListA, stringListB):
        if itemA < itemB:
            return -1
        elif itemA > itemB:
            return 1
    equal = True
    if len(stringListA) == len(stringListB):
        for itemA, itemB in zip(stringListA, stringListB):
            if itemA != itemB:
                equal = False
        if equal:
            return 0
    if len(stringListA) < len(stringListB):
        return -1
    return 1
   
if __name__ == '__main__':
    modfile = pt.unrel('src', 'gui', 'gui_helpers.py')
    mod = Module(modfile)
    