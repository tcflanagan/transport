'''Scripts for converting HTML containing CSS to plain HTML

The current GUI implementation of this software is done using wxPython. wxPython
includes panels and frames for displaying HTML, including the Microsoft
HTML Help Workshop format. However, such HTML-displaying tools do not work for
CSS. Mostly, this isn't a real problem, but the HTML Help is much easier to read
if code snippets are highlighted by syntax. This module converts the CSS-ridden
HTML output by Pygments into plain HTML.

'''

import re


css = '''
td.linenos { background-color: #f0f0f0; padding-right: 10px; }
span.lineno { background-color: #f0f0f0; padding: 0 5px 0 5px; }
pre { line-height: 125%; }
body .hll { background-color: #ffffcc }
body  { background: #f8f8f8; }
body .c { color: #8f5902; font-style: italic } /* Comment */
body .err { color: #a40000; border: 1px solid #ef2929 } /* Error */
body .g { color: #000000 } /* Generic */
body .k { color: #204a87; font-weight: bold } /* Keyword */
body .l { color: #000000 } /* Literal */
body .n { color: #000000 } /* Name */
body .o { color: #ce5c00; font-weight: bold } /* Operator */
body .x { color: #000000 } /* Other */
body .p { color: #000000; font-weight: bold } /* Punctuation */
body .cm { color: #8f5902; font-style: italic } /* Comment.Multiline */
body .cp { color: #8f5902; font-style: italic } /* Comment.Preproc */
body .c1 { color: #8f5902; font-style: italic } /* Comment.Single */
body .cs { color: #8f5902; font-style: italic } /* Comment.Special */
body .gd { color: #a40000 } /* Generic.Deleted */
body .ge { color: #000000; font-style: italic } /* Generic.Emph */
body .gr { color: #ef2929 } /* Generic.Error */
body .gh { color: #000080; font-weight: bold } /* Generic.Heading */
body .gi { color: #00A000 } /* Generic.Inserted */
body .go { color: #000000; font-style: italic } /* Generic.Output */
body .gp { color: #8f5902 } /* Generic.Prompt */
body .gs { color: #000000; font-weight: bold } /* Generic.Strong */
body .gu { color: #800080; font-weight: bold } /* Generic.Subheading */
body .gt { color: #a40000; font-weight: bold } /* Generic.Traceback */
body .kc { color: #204a87; font-weight: bold } /* Keyword.Constant */
body .kd { color: #204a87; font-weight: bold } /* Keyword.Declaration */
body .kn { color: #204a87; font-weight: bold } /* Keyword.Namespace */
body .kp { color: #204a87; font-weight: bold } /* Keyword.Pseudo */
body .kr { color: #204a87; font-weight: bold } /* Keyword.Reserved */
body .kt { color: #204a87; font-weight: bold } /* Keyword.Type */
body .ld { color: #000000 } /* Literal.Date */
body .m { color: #0000cf; font-weight: bold } /* Literal.Number */
body .s { color: #4e9a06 } /* Literal.String */
body .na { color: #c4a000 } /* Name.Attribute */
body .nb { color: #204a87 } /* Name.Builtin */
body .nc { color: #000000 } /* Name.Class */
body .no { color: #000000 } /* Name.Constant */
body .nd { color: #5c35cc; font-weight: bold } /* Name.Decorator */
body .ni { color: #ce5c00 } /* Name.Entity */
body .ne { color: #cc0000; font-weight: bold } /* Name.Exception */
body .nf { color: #000000 } /* Name.Function */
body .nl { color: #f57900 } /* Name.Label */
body .nn { color: #000000 } /* Name.Namespace */
body .nx { color: #000000 } /* Name.Other */
body .py { color: #000000 } /* Name.Property */
body .nt { color: #204a87; font-weight: bold } /* Name.Tag */
body .nv { color: #000000 } /* Name.Variable */
body .ow { color: #204a87; font-weight: bold } /* Operator.Word */
body .w { color: #f8f8f8; text-decoration: underline } /* Text.Whitespace */
body .mf { color: #0000cf; font-weight: bold } /* Literal.Number.Float */
body .mh { color: #0000cf; font-weight: bold } /* Literal.Number.Hex */
body .mi { color: #0000cf; font-weight: bold } /* Literal.Number.Integer */
body .mo { color: #0000cf; font-weight: bold } /* Literal.Number.Oct */
body .sb { color: #4e9a06 } /* Literal.String.Backtick */
body .sc { color: #4e9a06 } /* Literal.String.Char */
body .sd { color: #8f5902; font-style: italic } /* Literal.String.Doc */
body .s2 { color: #4e9a06 } /* Literal.String.Double */
body .se { color: #4e9a06 } /* Literal.String.Escape */
body .sh { color: #4e9a06 } /* Literal.String.Heredoc */
body .si { color: #4e9a06 } /* Literal.String.Interpol */
body .sx { color: #4e9a06 } /* Literal.String.Other */
body .sr { color: #4e9a06 } /* Literal.String.Regex */
body .s1 { color: #4e9a06 } /* Literal.String.Single */
body .ss { color: #4e9a06 } /* Literal.String.Symbol */
body .bp { color: #3465a4 } /* Name.Builtin.Pseudo */
body .vc { color: #000000 } /* Name.Variable.Class */
body .vg { color: #000000 } /* Name.Variable.Global */
body .vi { color: #000000 } /* Name.Variable.Instance */
body .il { color: #0000cf; font-weight: bold } /* Literal.Number.Integer.Long */
'''

class Stack:
    '''This is a simple FILO stack implementation.'''
    
    def __init__(self):
        '''Create a new stack.'''
        self.data = []
        
    def push(self, item):
        '''Add an item to the top of the stack.'''
        self.data.append(item)
    
    def pop(self):
        '''Remove and return the item from the top of the stack.'''
        if self.isEmpty():
            return False
        return self.data.pop()
    
    def peek(self):
        '''Return the item on the top of the stack without removing it.'''
        return self.data[-1]
    
    def size(self):
        '''Return the number of elements on the stack.'''
        return len(self.data)
    
    def isEmpty(self):
        '''Return True if the stack contains no elements.'''
        return self.size() == 0
    
class HTMLHelper:
    
    def __init__(self):
        self.cssdict = {}
        namepattern = re.compile(r'\.([A-Za-z0-9]+) ')
        datapattern = re.compile(r' \{ (.+) \}')
        for line in css.splitlines():
            match = re.search(namepattern, line)
            matchdat = re.search(datapattern, line)
            key = None
            val = None
            if match:
                key = match.group(1)
                if key.startswith('span.'):
                    key = key[5:]
            if matchdat:
                val = self.toTuples(matchdat.group(1))
            if key and val:
                self.cssdict[key] = val
        
    
    def toTuples(self, data):
        items = data.split(';')
        opentags = ''
        closetags = ''
        for item in items:
            split = item.split(':')
            if len(split) == 2:
                key = split[0].strip()
                val = split[1].strip()
                if key == 'color':
                    tagopen = '<font color="' + val + '">'
                    tagclose = '</font>'
                elif key == 'font-weight' and val == 'bold':
                    tagopen = '<b>'
                    tagclose = '</b>'
                elif key == 'font-style' and val == 'italic':
                    tagopen = '<i>'
                    tagclose = '</i>'
                elif key == 'text-decoration' and val == 'underline':
                    tagopen = '<u>'
                    tagclose = '</u>'
                elif key == 'padding':
                    tagopen = '&nbsp;'
                    tagclose = '&nbsp;&nbsp;&nbsp;'
                else:
                    tagopen = ''
                    tagclose = ''
                opentags = opentags + tagopen
                closetags = tagclose + closetags
                
        return (opentags, closetags)
        
    def formatHTML(self, txt):
        '''Replace all CSS tags in `txt` with pure HTML equivalents.'''
        stack = Stack()
        pattern = re.compile('<span class="(.*)">')
        while len(txt) > 0:
            if txt.startswith('</span>'):
                tempstack = Stack()
                curr = stack.pop()
                found = False
                while not found:
                    match = re.search(pattern, curr)
                    if match:
                        matchstring = match.group(1)
                        itemstring = self.cssdict[matchstring][0]
                        item = tempstack.pop()
                        while item:
                            itemstring = itemstring + item
                            item = tempstack.pop()
                        stack.push(itemstring + self.cssdict[matchstring][1])
                        found = True
                    else:
                        tempstack.push(curr)
                        curr = stack.pop()
                txt = txt[7:]
            elif txt.startswith('<span class='):
                endpos = txt.find('>')
                stack.push(txt[0:endpos+1])
                txt = txt[endpos+1:]
            else:
                stack.push(txt[0])
                txt = txt[1:]
                
        ans = ''
        while not stack.isEmpty():
            ans = stack.pop() + ans
        return ans
    
    def formatHTMLString(self, match):
        return self.formatHTML(match.group(1))
    
    def scanFileForCode(self, filename):
        '''Search the specified file for Python code snippets and fix them.
        
        Read in the specified file and search through it for bits of Python
        code. Whenever any such code is found, replace all the CSS in it with
        pure HTML, and write the file back to the disk.
        '''
        full_string = ''
        with open(filename, 'r') as f:
            for line in f:
                full_string += line
        
        ans = full_string
        pattern = re.compile('<div class="highlight">(.*?)</div>', re.DOTALL)
        match_text = []
        matches = re.finditer(pattern, full_string)
        for match in matches:
            match_text.append(match.group(1))
        for match in match_text:
            ans = pattern.sub(self.formatHTMLString, full_string)
            
        with open(filename, 'w') as f:
            f.write(ans)
        