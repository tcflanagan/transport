"""New tools for parsing configuration files."""

import configparser as cp
import re

FORMAT_BASIC = 0
FORMAT_REPR = 1
FORMAT_AUTO = 2
_BOOLEAN_STATES = {'true': True,
                   'yes': True,
                   '1': True,
                   1: True,
                   'false': False,
                   'no': False,
                   '0': False,
                   0: False}

class ConfigParser(object):
    """A class to parse configuration files in a variety of ways.
    
    Parameters
    ----------
    filePath : string
        The absolute path to the configuration file.
    fileFormat : int
        The flag indicating the format of the configuration file. Options are
        the following:
            FORMAT_BASIC
                The file is treated as a standard configuration file. All 
                return values are strings, unless one of the specialized
                accessor methods is used.
            FORMAT_REPR
                The file consists of entries formatted according to __repr__,
                so that they can be cast back to the appropriate types using
                __eval__.
            FORMAT_AUTO
                The parser attempts to guess the format of the entries based
                on syntax.
    substitutions : dict
        A dictionary whose keys are strings. The values will be substituted
        into the file wherever the corresponding key is referenced (using the
        standard rules for string formatting).
    defaultValues : dict
        A dictionaries whose keys are tuples of strings. The first element of
        each tuple should be a section name, and the second element should be
        an option name. Whenever a section and option is requested, not 
        found in the configuration file, and found in `defaultValues`, the 
        value from `defaultValues` will be returned and written to the file in
        the appropriate place.
    preserveCase : bool
        Whether the names of the sections and options should preserve case.
    """
    
    def __init__(self, filePath, fileFormat, substitutions=None, 
                 defaultValues=None, preserveCase=True):
        self._filePath = filePath
        self._fileFormat = fileFormat
        self._defaultValues = {}
        if defaultValues is not None:
            for item in defaultValues:
                section, option = item
                if section not in self._defaultValues:
                    self._defaultValues[section] = {option: defaultValues[item]}
                else:
                    self._defaultValues[section][option] = defaultValues[item]
        if substitutions is None:
            self._configParser = cp.ConfigParser()
        else:
            self._configParser = cp.ConfigParser(substitutions)
            
        if preserveCase:
            self._configParser.optionxform = str
            
        self._configParser.read(self._filePath)
        
    def getSections(self):
        """Return a list of available sections.
        
        Returns
        -------
        list of str
            A list of strings specifying the sections included in both the
            configuration file and the dictionary of default values.
        """
        answer = self._configParser.sections()
        for item in self._defaultValues:
            if item not in answer:
                answer.append(item)
        return answer
    
    def getOptions(self, section):
        """Return a list of options under a specified section.
        
        Return a list of strings specifying the keys contained within a
        specified section, including the information from both the defaults
        dictionary and the configuration file. Each option will occur only once.
        
        Parameters
        ----------
        section : str
            The section whose options should be retrieved.
            
        Returns
        -------
        list of str
            A list of strings indicating the options listed under the specified
            section.
        """
        answer = None
        if self._configParser.has_section(section):
            answer = self._configParser.options(section)
        if section in self._defaultValues:
            if answer is None:
                answer = []
            for item in self._defaultValues[section]:
                if item not in answer:
                    answer.append(item)
        return answer
    
    def getOptionsDict(self, section):
        """Return a dictionary containing the options and values in a section.
        
        Parameters
        ----------
        section : str
            The section whose values should be returned.
        
        Returns
        -------
        dict
            A dictionary containing the names of the options in the specified 
            section and the values associated with those options.
        """
        answer = {}
        for option in self.getOptions(section):
            answer[option] = self.get(section, option)
        return answer
            
    def get(self, section, option, default=None, converter=None):
        """Read a value from the configuration file.
        
        Attempt to read a value from the configuration file under the section
        `section` and associated with the key `option`. If either of these is
        missing from the file, search the dictionary of default values. If
        either the section or the key is missing from that dictionary, also,
        return `default`.
        
        If the file format is FORMAT_BASIC and the requested item is found in
        the file, return the `string` from the file, passed through `converter`
        if it is specified.
        
        If the file format is FORMAT_REPR and the requested item is found in
        the file, return the value from the file, passed first through `eval`
        and then, if it is specified, through `converter`.
        
        If the file format is FORMAT_AUTO and the requested item is found in
        the file, attempt to guess the type of the data in the file, cast the
        data to that type, and return it, passing it through `converter` if it
        is specified.
        
        If the requested data is not found in the file, return the appropriate
        element from the dictionary of default values, passed through 
        `converter` if it is specified.
        
        If the requested data is not found in either the file or the defaults
        dictionary, return `default`, passed through `converter` if it is
        specified.
        
        Finally, after any/all conversions have taken place, write the value
        that will be returned to the configuration file and return said value.
                
        In summary,
            - `converter`, if specified, takes precedence over all other
              data type casting; and
            - the search order is (1) the configuration file, (2) the dictionary
              of default values, and (3) the default supplied to this method.
                
        Parameters
        ----------
        section : string
            The section from which the value should be read.
        option : string
            The item within the specified section whose value should be read.
        default : (variant)
            The value to return if the specified section or option does not
            exist in either the file or the dictionary of default values.
        converter : function
            A function to convert the value to the appropriate type.
            
        Returns
        -------
        (variant)
            The value associated with `section` and `option` in the 
            configuration file.
        """
        changed = False
        if not self._configParser.has_section(section):
            self._configParser.add_section(section)
            changed = True
        if self._configParser.has_option(section, option):
            value = self._configParser.get(section, option)
        elif section in self._defaultValues:
            if option in self._defaultValues[section]:
                value = self._defaultValues[section][option]
            else:
                value = default
            changed = True
                
        else:
            value = default
            changed = True
        
        if self._fileFormat == FORMAT_REPR:
            value = eval(value)
        elif self._fileFormat == FORMAT_AUTO:
            value = _parseSequence(value)
            
        if converter is not None:
            value = converter(value)
            changed = True

        if changed:
            self.set(section, option, str(value))
            
        return value
    
    def getInt(self, section, option, default=0):
        """Return a value from the configuration file as an integer.
        
        Parameters
        ----------
        section : string
            The section from which the value should be read.
        option : string
            The item within the specified section whose value should be read.
        default : int
            The value to return if the specified section or option does not
            exist in either the file or the dictionary of default values.
            
        Returns
        -------
        int
            The integer associated with the specified section and key, or
            `default` if no such entry exists.
        """
        return self.get(section, option, default, int)
    
    def getFloat(self, section, option, default=0):
        """Return a value from the configuration file as a float.
        
        Parameters
        ----------
        section : string
            The section from which the value should be read.
        option : string
            The item within the specified section whose value should be read.
        default : float
            The value to return if the specified section or option does not
            exist in either the file or the dictionary of default values.
            
        Returns
        -------
        int
            The float associated with the specified section and key, or
            `default` if no such entry exists.
        """
        return self.get(section, option, default, float)
    
    def getBoolean(self, section, option, default=False):
        """Return a value from the configuration file as a boolean.
        
        Parameters
        ----------
        section : string
            The section from which the value should be read.
        option : string
            The item within the specified section whose value should be read.
        default : bool
            The value to return if the specified section or option does not
            exist in either the file or the dictionary of default values.
            
        Returns
        -------
        bool
            The boolean associated with the specified section and key, or
            `default` if no such entry exists.
        """
        return self.get(section, option, default, _bool)
    
    
    def set(self, section, option, value):
        """Write a value to the configuration file.
        
        If the file format is FORMAT_REPR, pass `value` through the `repr`
        function before writing it.
        
        Parameters
        ----------
        section : str
            The section within the file which should contain the option
            to be written.
        option : str
            The key within `section` with which the data should be associated.
        value : (variant)
            The value to be associated with the given key in the given section.
        """
        if self._fileFormat == FORMAT_REPR:
            value = repr(value)
        else:
            value = str(value)
        
        if not self._configParser.has_section(section):
            self._configParser.add_section(section)
        self._configParser.set(section, option, value)
        
        with open(self._filePath, 'w') as configFile:
            self._configParser.write(configFile)
        
        return value
            

#-------------------------------------------------------------- Helper functions

def _bool(value):
    """Return the specified value as a boolean.
    
    Parameters
    ----------
    value : (variant)
        The value which should be converted to a boolean.
    
    Returns
    -------
    bool
        The `value`, cast to a boolean if possible, or `None` otherwise.
    """
    if isinstance(value, bool):
        return value;
    
    if isinstance(value, str):
        value = value.strip()
    
    if value.lower() in _BOOLEAN_STATES:
        return _BOOLEAN_STATES[value.lower()]
    return None

def _parseSingle(string):
    """Convert a single element into the appropriate type."""
    string = string.strip()
    
    if len(string) == 0:
        return ''
    
    pattern = re.compile(r'[^0-9]')
    if not pattern.search(string):
        return int(string)
    pattern = re.compile(r'[^0-9\.eE]')
    if not pattern.search(string):
        if (string.count('.') <= 1 and 
            (string.count('e') + string.count('E') <= 1)):
            return float(string)
        
    boolValue = _bool(string)
    if boolValue is not None:
        return boolValue
                
    if string[0] == string[-1]:
        if string[0] == '"' or string[0] == "'":
            return string[1:-1]
    elif string[1] == string[-1]:
        if ((string[0] == 'u' or string[0] == 'r') and 
            (string[1] == '"' or string[1] == "'")):
            return string[2:-1]
        
    if string == 'None':
        return None
        
    return string
    
def _parseSequence(string, delimiter=','):
    """Convert a string to a sequence of items."""
    if not isinstance(string, str):
        return string
    string = string.strip()
    if string.startswith('[') and string.endswith(']'):
        sequenceType = 'list'
    elif string.startswith('(') and string.endswith(')'):
        sequenceType = 'tuple'
    else:
        return _parseSingle(string)
    
    string = string[1:-1]
    
    tokens = []
    current = []
    
    plev = 0
    blev = 0
    sqopen = False
    dqopen = False
    
    for char in string:
        if char == '[':
            blev += 1
            current.append(char)
        elif char == ']':
            blev -= 1
            current.append(char)
        elif char == '(':
            plev += 1
            current.append(char)
        elif char == ')':
            plev -= 1
            current.append(char)
        elif char == '"':
            dqopen = not dqopen
            current.append(char)
        elif char == "'":
            sqopen = not sqopen
            current.append(char)
        elif (char == delimiter and plev == 0 and blev == 0 and 
              not sqopen and not dqopen):
            tokens.append(_parseSequence(''.join(current).strip()))
            current = []
        else:
            current.append(char)
            
    if len(current) > 0:
        tokens.append(_parseSequence(''.join(current)))
    
    if sequenceType == 'tuple':
        tokens = tuple(tokens)    
    return tokens

    