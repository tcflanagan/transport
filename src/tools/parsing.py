"""Tools for parsing strings and extracting certain types of information.
"""
import src.core


def findClosingParenthesis(expression, start=0):
    """Find a matching parenthesis in an expression.
    
    Parameters
    ----------
    expression : str
        The expression in which the closing parenthesis is sought.
    start : int
        The position of the first character **after** the opening parenthesis
        in the expression.
    
    Returns
    -------
    int
        The position of the closing parenthesis, or -1 if no closing 
        parenthesis is found.
        
    Examples
    --------
    >>> findClosingParenthesis("3 + @(cat) + @(dog)", 6)
    9
    """
    depth = 1
    position = start
    keepGoing = True
    
    while keepGoing and position <= len(expression):
        currChar = expression[position]
        if currChar == '(':
            depth += 1
        elif currChar == ')':
            depth -= 1
            if depth == 0:
                return position
        position += 1
    return -1

def extractNamesOfType(expression, marker):
    """Extract the names of bins which begin with a given character.
    
    Parameters
    ----------
    expression : str
        The expression from which to extract the names of the bins of the
        desired type.
    marker : str
        The character or string which indicates the beginning of a bin name
        of the desired type.
    
    Returns
    -------
    list of str
        A list of strings indicating the names of the bins of the relevant 
        type.
        
    Examples
    --------
    >>> extractNamesOfType("3 + @(cat)*$(fish) + @(dog)/#(mouse)", "@")
    ['cat', 'dog']
    """
    index = 0
    result = []
    matchString = marker + '('
    length = len(matchString)
    
    while index < len(expression):
        index = expression.find(matchString, index)
        if index < 0:
            return result
        endPos = findClosingParenthesis(expression, index+length)
        if endPos < 0:
            return result
        else:
            result.append(expression[index+length:endPos])
            index = endPos
    return result

def extractNames(expression):
    """Extract the names of all data bins in some expression.
    
    Parameters
    ----------
    expression : str
        The expression from which to extract the names of data bins.
        
    Returns
    -------
    tuple of list of str
        A tuple of lists of strings. The first list contains the names of
        all constants used in the expression. The second contains the names of
        columns, and the third contains the names of parameters.
    
    Examples
    --------
    >>> extractNames("3 + @(cat) + @(dog)")
    (['cat', 'dog'], [], [])
    
    >>> extractNames("3 + @(cat)*$(fish) + @(dog)/#(mouse)")
    (['cat', 'dog'], ['mouse'], ['fish'])
    """
    constants = extractNamesOfType(expression, 
                                   src.core.experiment.MARK_CONSTANT)
    columns = extractNamesOfType(expression, 
                                 src.core.experiment.MARK_COLUMN)
    parameters = extractNamesOfType(expression, 
                                    src.core.experiment.MARK_PARAMETER)
    return (constants, columns, parameters)


def tokenize(string, delimiter=','):
    """Split the string at the specified delimiter.
    
    This function works similar to the built-in string function `split` except
    that it takes into account the possibility that the delimiter occurs 
    inside some grouping construction (for example, quotation marks or list
    brackets) which should prevent splitting.
    
    Parameters
    ----------
    string : str
        The string to split. If this string begins with a character which
        marks the start of a group, the matching closing character will end
        the tokenized list.
    delimiter : str
        The mark at which to split.
        
    Returns
    -------
    list of str
        The list of tokens in the string.
    str
        The contents of the string following the group-closing character which
        matches the character with which the input string started.
    """
    
    tokens = []    # All tokens in the string
    token = ''     # The token currently being filled
    
    dqo = False    # Double quotes open
    sqo = False    # Single quotes open
    paren = 0      # Depth of parentheses
    brace = 0      # Depth of curly braces
    brack = 0      # Depth of square brackets
    
    if not (string.startswith('(') or string.startswith('[') or
            string.startswith('{') or string.startswith('"') or 
            string.startswith("'")):
        paren += 1
    
    def getLevel():
        """Get the current next level."""
        return int(dqo) + int(sqo) + paren + brack + brace
    
    index = 0
    length = len(string)
    while index < length :
        char = string[index]
        if char == delimiter and getLevel() == 1:
            tokens.append(token.strip())
            token = ''
            index += 1
            continue
        
        if char == ')':
            paren -= 1
        elif char == ']':
            brack -= 1
        elif char == '}':
            brace -= 1
            
        if getLevel() > 1 or (getLevel() > 0 and char != delimiter):
            token += char
            
        if char == '(':
            paren += 1
        elif char == '[':
            brack += 1
        elif char == '{':
            brace += 1
            
        elif char == '"':
            if dqo:
                dqo = False
            else:
                dqo = True
        elif char == "'":
            if sqo:
                sqo = False
            else:
                sqo = True
                
        index += 1
        
        if getLevel() == 0:
            break
        
    tokens.append(token.strip())
    return (tokens, string[index:])

def escapeXML(string):
    """Return an XML compliant string.
    
    Parameters
    ----------
    string : str
        A string which may or may not contain characters which would be invalid
        in an XML document.
        
    Returns
    -------
    str
        The input string with all improper characters replaced with appropriate
        escape sequences.
    """
    string = str(string)
    for i, j in [('&', '&amp;'), ('"', '&quot;'), ("'", '&apos;'), 
                 ('>', '&gt;'), ('<', '&lt;')]:
        string = string.replace(i, j)
    return string
