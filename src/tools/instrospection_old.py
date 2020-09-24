'''A tool for reading instrument code files and extracting their structure.
'''

from collections import namedtuple
import re

__all__ = ['Module', 'Instrument', 'Method', 'Action']

LineTuple = namedtuple('LineTuple', ['indent', 'text'])
ArgTuple = namedtuple('ArgTuple', ['keyword', 'value', 'spec'])

def splitLine(line):
    '''
    Split a line of text into a LineTuple.
    '''
    line = line.rstrip().replace('\t', '    ')
    pattern = re.compile(r'( *)(.*)')
    match = pattern.match(line)
    return LineTuple(len(match.group(1)), match.group(2).strip())

def clean(text, something=''):
    '''Find the minimum indentation level in chunk of text, and subtract that
    indentation from every line.'''        
    min_indent = None
    if not isinstance(text, list):
        text = text.split('\n')
    for line in text:
        line_tuple = splitLine(line)
        if len(line_tuple.text) == 0:
            continue
        if min_indent is None:
            min_indent = line_tuple.indent
        elif line_tuple.indent < min_indent:
            min_indent = line_tuple.indent
    
    new_lines = []
    for line in text:
        ls = line.strip()
        if len(ls) > 0:
            new_lines.append(line[min_indent:])
    
    return ('\n'.join(new_lines)).strip()
    
def tokenize(text):
    '''Break a line of text into tokens by comma, ignoring the comma if it
    appears in a string (that is, the text itself contains quotation marks).''' 
    tokens = []
    
    opensq = False
    opendq = False
    ld = 0
    current_token = ''
    for char in text:
        if char == ',':
            if (not opensq) and (not opendq) and (ld == 0):
                tokens.append(current_token.strip())
                current_token = ''
            else:
                current_token += char
        else:
            if char == "'":
                if opensq:
                    opensq = False
                else:
                    opensq = True
            elif char == '"':
                if opendq:
                    opendq = False
                else:
                    opendq = True
            elif char == '[':
                ld += 1
            elif char == ']':
                ld -= 1
            current_token += char
    if len(current_token) > 0:
        tokens.append(current_token.strip())
    return tokens

def glob(lines, level):
    '''Break a list into sublists. A new element is started whenever
    the indentation of the first line of the input list's indentation is less
    than or equal to the first line of the previous.'''
    ans = []
    current_glob = []
    for line in lines:
        if len(line.strip()) > 0 and splitLine(line).indent == level:
            if len(current_glob) > 0:
                ans.append(current_glob)
            current_glob = [line]
        else:
            current_glob.append(line)
    if len(current_glob) > 0:
        ans.append(current_glob)
    return ans

def applyIndent(text, indent):
    '''Take a multi-line string or list and apply `indent` to each line.'''
    full_list = []
    if isinstance(text, list):
        for line in text:
            full_list.extend(line.split('\n'))
    else:
        full_list = text.split('\n')
    code_list_out = []
    for line in full_list:
        code_list_out.append(' '*indent + line)
    return '\n'.join(code_list_out)
        

#===============================================================================
# Module class
#===============================================================================

class Module(object):
    
    def __init__(self, path):
        self.path = path
        self.contents = []
        
        module_text = self.loadFile()
        #self.extractInstruments(module_text)
        self.contents = self.processModule(module_text)
    
    def loadFile(self, join=False):
        '''Read the module file and return the full text.'''
        lines = []
        with open(self.path, 'rU') as module:
            for line in module:
                lines.append(line.rstrip())
        if join:
            return '\n'.join(lines)
        return lines
    
    def setAll(self, newvalue):
        for item in self.contents:
            if isinstance(item, ModuleConstant):
                if item.name == '__all__':
                    item.value = '[\'' + newvalue + '\']'
                    

    
    def processModule(self, lines):
        '''Scan through the module, creating objects for the elements.'''
        sections = glob(lines, 0)
        
        ans = []
        
        pat_inst = re.compile(r'class *(\w*)\s*\(\s*Instrument\s*\)\s*:')
        pat_subclass = re.compile(r'class *(\w*)\s*\(\s*([\w_]*)\s*\)\s*:')
        pat_class = re.compile(r'class *(\w*)\s*:')
        pat_importA = re.compile(r'from *([\w_\.]+) +import *([\w_\.]+)')
        pat_importB = re.compile(r'import *([\w_\.]+)')
        pat_const = re.compile(r'([\w_]+) *= *(.+)')
        pat_docstring = re.compile(r"'{3}", re.S)
        pat_comment = re.compile(r'\s*#')
        
        ds = []
        dsopen = False
        for section in sections:
            top = section[0]
            match = pat_inst.search(top)
            if match:
                ans.append(Instrument(match.group(1), section[1:]))
                continue
            match = pat_subclass.search(top)
            if match:
                ans.append(Class(match.group(1), match.group(2), section[1:]))
                continue
            match = pat_class.search(top)
            if match:
                ans.append(Class(match.group(1), '', section[1:]))
                continue
            if pat_importA.search(top) or pat_importB.search(top):
                ans.append(ModuleImport(section[0]))
                continue
            match = pat_const.search(top)
            if match:
                val = [match.group(2)]
                if len(section) > 1:
                    val.extend(section[1:])
                ans.append(ModuleConstant(match.group(1), val))
                continue
            match = pat_comment.search(top)
            if match:
                ans.append(Comment(top.strip()))
                continue
            match = pat_docstring.match(top)
            if match:
                if dsopen:
                    ans.append(ModuleDocstring('\n'.join(ds)))
                    ds = []
                    dsopen = False
                else:
                    dsopen = True
                continue
            if dsopen:
                ds.append(top)
                continue
                    
            print('UNKNOWN ' + str(section))
        return ans  

    def getInstruments(self):
        ans = []
        for item in self.contents:
            if isinstance(item, Instrument):
                ans.append(item)
        return ans
    
    def toCode(self, min_indent=0):
        ans = []
        for item in self.contents:
            ans.append(item.toCode(0))
        return '\n'.join(ans)
        

class ModuleDocstring(object):
    def __init__(self, text):
        '''Takes a multi-line string.'''
        self.text = text
        
    def __str__(self):
        return "\'\'\'" + self.text + '\n\'\'\''
    
    def toCode(self, min_indent):
        return applyIndent(str(self), min_indent)

class ModuleImport(object):
    def __init__(self, text):
        '''Takes a single-line string.'''
        self.text = text
        
    def toCode(self, min_indent):
        return applyIndent(self.text, min_indent)

class ModuleConstant(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value
        
    def toCode(self, level):
        
        if isinstance(self.value, list):
            val = '\n'.join(self.value)
        else:
            val = self.value
        return applyIndent(self.name + ' = ' + val, level)
        
class Comment(object):
    def __init__(self, text):
        '''Takes a string.'''
        self.text = text
        self.name = ''
        
    def toCode(self, min_indent=0):
        return applyIndent(self.text, min_indent)


#===============================================================================
# Class level
#===============================================================================
class Class(object):
    def __init__(self, name, bases, lines):
        self.name = name
        self.bases = bases
        self.contents = self.processClass(lines)
        
    def toCode(self, min_indent):
        contents_list = ['class %s(%s):']
        for item in self.contents:
            contents_list.append(item.toCode(min_indent+4))
            
        return '\n'.join(contents_list)
    
    def processClass(self, lines):
        ans = []

        pat_action = re.compile(r'    def +([_\w]+) *\((.*?)\):', re.S)
        #pat_action = re.compile(r'    def +([_\w]+) *\(([, _\w=\'\":-]*?)\):', re.S)
        pat_decorator = re.compile(r'    @([_\w]+)')
        pat_comment = re.compile(r'\s*#')
        
        sections = glob(lines, 4)
        decorator = ''
        for section in sections:
            top = section[0]
            match = pat_decorator.search(top)
            if match:
                decorator = match.group(1)
                continue
            match = pat_action.search(top)
            if match:
                name = match.group(1)
                args = match.group(2)
                ans.append(Method(name, args, section[1:], decorator))
                decorator = ''
                continue
            match = pat_comment.search(top)
            if match:
                ans.append(Comment(top.strip()))
                continue
            joined = '\n'.join(section)
            match = pat_action.search('\n'.join(section))
            if match:
                name = match.group(1)
                args = match.group(2)
                rest = joined[match.end(0)+1:].split('\n')
                ans.append(Method(name, args, rest, decorator))
                decorator = ''
            print('UNKNOWN ' + str(section))
        return ans
            
                
class Instrument(Class):
    def __init__(self, name, lines):
        super(Instrument, self).__init__(name, 'Instrument', lines)
        self.name = name
        self.lines = lines
        self.actions = []
        self.extractActions()
        
        for index, item in enumerate(self.contents):
            if isinstance(item, Method) and item.name == '__init__':
                self.init = item
                del self.contents[index]
    
    def getMethod(self, name):
        for item in self.contents:
            if isinstance(item, Method) and item.name == name:
                return item
        return None
    
    def getMethods(self):
        ans = []
        for item in self.contents:
            if isinstance(item, Method):
                ans.append(item)
        return ans
    
    def addMethod(self, name):
        newmethod = Method(name, '', '', '')
        pos = 0
        for item in self.contents:
            if isinstance(item, Method) and not item.name == 'getActions':
                pos += 1
                
        self.contents.insert(pos-1, newmethod)
        return newmethod
        
    def deleteMethod(self, name):
        to_delete = -1
        for index, item in enumerate(self.contents):
            if isinstance(item, Method):
                if item.name == name:
                    to_delete = index
                    break
        if to_delete >= 0:
            del self.contents[to_delete]
        
    def addAction(self):
        self.actions.append(Action('', None))
        
    def removeAction(self, index):
        del self.actions[index]
    
    def getAction(self, description):
        for item in self.actions:
            if item.description == description:
                return item
        return None
    
    def getDefaultName(self):
        args = tokenize(self.init.args)
        pattern = re.compile(r'name *= *\'(.*?)\'')
        for arg in args:
            match = pattern.match(arg)
            if match:
                return match.group(1)
        return ''
    
    def setDefaultName(self, newname):
        args = tokenize(self.init.args)
        pattern = re.compile(r'name *= *\'(.*?)\'')
        new_args = []
        for arg in args:
            match = pattern.match(arg)
            if match:
                new_args.append('name=' + newname)
            else:
                new_args.append(arg)
        self.init.args = ', '.join(new_args)
        
        
    
    def getRequiredParameters(self):
        reqparams = self.getMethod('getRequiredParameters')
        body = reqparams.body
        pattern = re.compile(r'({.*})', re.S)
        match = pattern.search(body)
        paramdict = eval(match.group(1))
        order = paramdict['order']
        del paramdict['order']
        ans = []
        for item in order:
            val = paramdict[item]
            if val is None:
                kind = 'None'
                val = 'None'
            elif isinstance(val, str):
                kind = 'String'
            else:
                kind = 'Number'
                val = str(val)
            ans.append([item, val, kind])
        return ans
    
    def setRequiredParameters(self, new_params):
        strs = []
        items = []
        for item in new_params:
            key = item[0]
            items.append(key)
            val = item[1]
            kind = item[2]
            if kind == 'String':
                val = "'" + val + "'"
            strs.append(' '*8 + '\'' + key + '\': ' + val)
        
        output = 'return {' + '\'order\': ' + str(items) + ',\n'
        output += ',\n'.join(strs)
        output += '}'
        
        reqparams = self.getMethod('getRequiredParameters')
        reqparams.body = output
    
    def extractActions(self):
        text = self.getMethod('getActions').body
        pat_return = re.compile('\s*return\s*\[(.+)\]', re.S)
        mat_return = pat_return.search(text)
        text = clean(mat_return.group(1))
        
        pat_act = re.compile('\s*Action(\w*) *\(')
        mat_act = pat_act.search(text)
        if mat_act is None:
            return
        finished = False
        while not finished:
            current_type = mat_act.group(1)
            next_start_position = mat_act.end()
            mat_act = pat_act.search(text, next_start_position)
            if mat_act:
                current_text = text[next_start_position:mat_act.start()]
            else:
                current_text = text[next_start_position:]
                finished = True
            current_text = current_text.strip()
            if current_text.endswith(','):
                current_text = current_text[:-1]
            if current_text.endswith(')'):
                current_text = current_text[:-1]
            self.actions.append(Action(current_type, current_text))
    
    def updateInit(self):
        curr = self.init.body
        pattern = re.compile('super\((\w*)\s*,\s*self\)')
        match = pattern.search(curr)
        curr = curr[0:match.start(1)] + self.name + curr[match.end(1):]
        self.init.body = curr
                                                    
        
    def toCode(self, min_indent):
        self.updateInit()
        self.contents.insert(0, self.init)
        contents_list = ['class %s(%s):' % (self.name, self.bases)]
        for item in self.contents:
            if item.name == 'getActions':
                contents_list.append(item.toCode(min_indent+4,self.actions))
            else:
                contents_list.append(item.toCode(min_indent+4))
        del self.contents[0]
        return '\n'.join(contents_list)
    
    
class Method(object):
    
    def __init__(self, name, args, lines, decorator):
        self.name = name
        self.args = args
        self.body = clean('\n'.join(lines), ['@classmethod', '#'])
        self.class_method = decorator
        
    def getArguments(self):
        tokens = tokenize(self.args)
        output = []
        for item in tokens[1:]:
            index = item.find('=')
            if index > 0:
                name = item[:index].strip()
                val = item[index+1:].strip()
                if val.startswith("'") and val.endswith("'"):
                    vtype = 'String'
                elif val == 'None':
                    vtype = 'None'
                else:
                    vtype = 'Number'
            else:
                name = item
                val = ''
                vtype = 'No Default'
            output.append([name, val, vtype])
        return output
    
    def setArguments(self, newargs):
        strings = []
        for item in newargs:
            if item[2] == 'No Default':
                strings.append(item[0])
            elif item[2] == 'String':
                strings.append(item[0] + '=\'' + item[1] + '\'')
            else:
                strings.append(item[0] + '=' + item[1])
        self.args = ', '.join(strings)
        self.args = 'self, ' + self.args
    def toCode(self, min_indent=0, actions=None):
        pre_text = ''
        if self.class_method:
            pre_text = '@classmethod'
        header_text = 'def %s (%s):' % (self.name, self.args)
        if actions:
            body_temp = []
            body_temp.append('return [')
            for index, a in enumerate(actions):
                body_temp.append(a.toCode(4))
                if index < len(actions)-1:
                    body_temp[-1] = body_temp[-1] + ','
            body_temp.append(']')
        else:
            body_temp = self.body.split('\n')
        return applyIndent([pre_text, header_text, 
                            applyIndent(body_temp, 4)], min_indent)

    
class Action(object):
    DEFAULTS = {'experiment': 'self._expt',
                'instrument': 'self',
                'description': '',
                'inputs': None,
                'outputs': None,
                'string': '',
                'method': None
                }
    ORDER = ['experiment', 'instrument', 'description', 'inputs', 'outputs',
             'string', 'method']
    
    def __init__(self, action_type, text):
        if text is not None:
            self.args = self.loadContents(text)
        else:
            self.args = Action.DEFAULTS.copy()
        self.action_type = action_type
        self.description = self.args['description']
        self.inputs = self.parseParameters(self.args['inputs'])
        self.outputs = self.parseParameters(self.args['outputs'])
        self.string = self.args['string']
        self.method = self.args['method']
    
    def updateDictionary(self):
        self.args['description'] = self.description
        self.args['inputs'] = self.inputs
        self.args['outputs'] = self.outputs
        self.args['string'] = self.string
        self.args['method'] = self.method
        
    def loadContents(self, text):
        '''Convert the text from the module into a dictionary of arguments.'''
        args = Action.DEFAULTS.copy()
        
        tokens = tokenize(text)
        kw_started = False
        
        kw_pat = re.compile(r'(\w+)\s*=(.+)', re.S)
        for keyword, token in zip(self.ORDER, tokens):
            match = kw_pat.match(token)
            if match:
                kw_started = True
                args[match.group(1)] = match.group(2)
            elif kw_started:
                print('ERROR PARSING!!!! pos after kw')
            else:
                args[keyword] = token
        return args
    
    
    def parseParameters(self, text):
        '''Take a list of strings and parse it into a list of parameters.'''
        if text is None: return []
        params = []
        text = text.strip()
        if text.startswith('['):
            text = text[1:].strip()
        if text.endswith(','):
            text = text[:-1].strip()
        if text.endswith(']'):
            text = text[:-1].strip()
        pat_param = re.compile('\s*Parameter *\(')
        mat_param = pat_param.search(text)
        if not mat_param:
            return []
        finished = False
        while not finished:
            next_start_position = mat_param.end()
            mat_param = pat_param.search(text, next_start_position)
            if mat_param:
                current_text = text[next_start_position:mat_param.start()]
            else:
                current_text = text[next_start_position:]
                finished = True
            current_text = current_text.strip()
            if current_text.endswith(','):
                current_text = current_text[:-1]
            if current_text.endswith(')'):
                current_text = current_text[:-1]
            params.append(Parameter(current_text))
        return params
    
    def toCode(self, min_indent=0):
        self.updateDictionary()
        output_lines = []
        first_line = ('Action' + self.action_type + '(' +
                      ', '.join([self.args['experiment'],
                                 self.args['instrument'],
                                 self.args['description']]) + ',')
        output_lines.append(first_line)
        inner_lines = []
        #inputs = ['inputs = [']
        if len(self.inputs) > 0:
            inputs = []
            for item in self.inputs:
                curr = item.toCode(4)
                inputs.append(curr)
            inner_lines.append('\n'.join(['inputs = [', ',\n'.join(inputs), ']']))
        if len(self.outputs) > 0:
            outputs = []
            for item in self.outputs:
                outputs.append(item.toCode(4))
            inner_lines.append('\n'.join(['outputs = [', ',\n'.join(outputs), ']']))
        inner_lines.append('string = ' + self.string)
        inner_lines.append('method = ' + self.method)
        output_lines.append(applyIndent(',\n'.join(inner_lines), 4))
        output_lines.append(')')
        return applyIndent(output_lines, min_indent)
        
        
class Parameter(object):
    DEFAULTS = {'experiment': 'self._expt',
                'name': '',
                'description': '',
                'formatString': '%.6e',
                'binName': 'None',
                'binType': 'None',
                'value': '0',
                'allowed': 'None',
                'instantiate': False 
                }
    ORDER = ['experiment', 'name', 'description', 'formatString', 'binName',
             'binType', 'value', 'allowed', 'instantiate']

    def __init__(self, text):
        if text is not None:
            self.args = self.getArgumentDictionary(text)
        else:
            self.args = Parameter.DEFAULTS.copy()
        self.name = self.args['name']
        self.description = self.args['description']
        self.format_string = self.args['formatString']
        self.bin_name = str(self.args['binName'])
        self.bin_type = self.args['binType']
        self.value = self.args['value']
        self.allowed = self.args['allowed']
        
    def updateDictionary(self):
        self.args['name'] = self.name
        self.args['description'] = self.description
        self.args['formatString'] = self.format_string
        self.args['binName'] = self.bin_name
        self.args['binType'] = self.bin_type
        self.args['value'] = self.value
        self.args['allowed'] = self.allowed
        
    def getArgumentDictionary(self, text):
        args = Parameter.DEFAULTS.copy()
        
        tokens = tokenize(text)
        
        kw_started = False
        
        kw_pat = re.compile(r'(\w+)\s*=(.+)')
        for keyword, token in zip(self.ORDER, tokens):
            match = kw_pat.match(token)
            if match:
                kw_started = True
                args[match.group(1)] = match.group(2)
            elif kw_started:
                print('ERROR PARSING!!!! pos after kw')
            else:
                args[keyword] = token
        return args

    def __str__(self):
        ans_list = []
        for item in self.ORDER:
            ans_list.append(item + '=' + str(self.args[item]))
        return ', '.join(ans_list)
    
    def toCode(self, min_indent=0):
        self.updateDictionary()
        ans_list = []
        for item in self.ORDER:
            ans_list.append(item + '=' + str(self.args[item]))
        
        new_ans_list = []
        running = 'Parameter('
        length = len(running)
        for item in ans_list:
            newlen = len(item)
            if length + newlen + 2 < 60:
                new_ans_list.append(item)
                running = running + item + ', '
                length += newlen + 2
            else:
                new_ans_list.append('\n    ' + item)
                running = item + ', '
                length += newlen + 2 

        return applyIndent('Parameter(' + ', '.join(new_ans_list) + ')', min_indent)
