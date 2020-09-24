"""A set of multi-purpose tools.

This module provides a handful of broadly-applicable functions for
formatting, and parsing. It also provides some general-purpose classes which
are not entirely necessary, but which are often helpful, for the functioning
of the software.
"""
from math import sqrt

_TOLERANCE = 1.0E-10

def frange(start, end=None, inc=None, includeEnd=True):
    """Return a list representing a range where the inputs can be floats.
    
    Parameters
    ----------
    start : float
        The first point in the list.
    end : float
        The value signaling the end of the list. 
    inc : float
        The value by which to increment.
    includeEnd : bool
        Whether the end of the range is inclusive.
        
    Returns
    -------
    list(float)
        A list of floats ranging from `start` to `end` in steps of `inc`.
    """

    if end == None:
        end = start + 0.0
        start = 0.0

    if inc == None:
        inc = 1.0

    steps = []
    while True:
        nextStep = start + len(steps) * inc
        if inc > 0 and nextStep >= end:
            break
        elif inc < 0 and nextStep <= end:
            break
        steps.append(nextStep)

    if includeEnd and abs(steps[-1] - end) > _TOLERANCE:
        steps.append(end)

    return steps

def xfrange(start, end=None, inc=None):
    """Create a generator producing a range where the inputs can be floats."""
    start = float(start)
    if end is None:
        end = start + 0.0
        start = 0.0

    if inc is None:
        inc = 1.0

    curr = start
    while curr < end:
        yield curr
        curr += inc
    return

def splitAtComma(text):
    """Split a comma-separated string of numbers into a list of floats.
    
    Take a string consisting of floating-point or integer numbers separated by 
    commas, split the string at the commas, and cast all of the numbers to
    floats. All segments which cannot be cast to a float will be ignored.
    
    Parameters
    ----------
    text : str
        The string to split. It should consist of numbers separated by commas.
    
    Returns
    -------
    list(float)
        A list of the numbers that were previously separated by commas.
    """

    ans = []
    splitList = text.split(',')
    for item in splitList:
        try:
            ans.append(float(item))
        except (ValueError, TypeError):
            pass
    return ans

def formatReSTHeading(heading, level=0):
    """Return a heading string formatted as reStructuredText.
    
    Parameters
    ----------
    heading : str
        The text of the heading.
    level : int
        The nesting depth of the section labeled by the supplied heading.
        
    Returns
    -------
    str
        The heading formatted using reStructuredText syntax.
    """
    length = len(heading)
    if level == 0:
        answer = ['#' * length, heading, '#' * length]
    elif level == 1:
        answer = ['=' * length, heading, '=' * length]
    elif level == 2:
        answer = [heading, '=' * length]
    elif level == 3:
        answer = [heading, '-' * length]
    elif level == 4:
        answer = [heading, '^' * length]
    else:
        answer = [heading, '"' * length]
    return '\n'.join(answer)

def gridArrangement(num):
    """Return the number of rows and columns needed to display elements neatly.

    Given a specified number of items, determine an acceptable way to arrange
    them in a grid. The algorithm attempts to keep the grid as square as 
    possible, subject to the condition that the number of columns is always
    greater than or equal to the number of rows.
        
    Parameters
    ----------
    num : int
        The number of elements which need to be arranged.
    
    Returns
    -------
    tuple (int, int)
        A tuple consisting of the number of rows and the number of columns
        which would be a decent arrangement of `num` items.
    """

    rows = 1
    cols = 1
    lastUpdate = 'rows'
    while True:
        if rows * cols >= num:
            break
        if lastUpdate == 'rows':
            cols += 1
            lastUpdate = 'cols'
        else:
            rows += 1
            lastUpdate = 'rows'
    return (rows, cols)


def multilineStringToList(string, removeBlanks=True):
    """Convert a multi-line string to a list of strings.
    
    Parameters
    ----------
    string : str
        The string to split.
    removeBlanks : bool
        Whether to remove all blank lines from the list.
        
    Returns
    -------
    list of str
        A list of strings, each element being one line of the input string.
    """

    rawList = string.split('\n')
    if not removeBlanks:
        return rawList

    blanksRemoved = []
    for line in rawList:
        currVal = line.strip()
        if len(currVal) != 0:
            blanksRemoved.append(currVal)
    return blanksRemoved

class Command(object):
    """A container for runtime-specified commands.
    
    In many situations in this software, there arise situations in which
    one of the `core` classes needs to send output back to some graphical
    entity. This class provides a container in which the graphical objects
    can store some method or function which the `core` class will execute
    at the appropriate time.
    
    Parameters
    ----------
    method : method or function
        A method (bound to some object) or a function which may be executed
        at some later specified time.
    args : positional arguments
        Comma-separated arguments which will be substituted into the method
        at execution time.
    kwargs : keyword arguments
        Keyword arguments which will be substituted into the method at
        execution time.
    """

    def __init__(self, method, *args, **kwargs):
        """Create a new Command."""
        self.method = method
        self.args = args
        self.kwargs = kwargs

    def execute(self, *args, **kwargs):
        """Execute the command contained within this class.
        
        Parameters
        ----------
        kwargs : keyword arguments
            Additional keyword arguments which will be passed to the method at
            the time it is executed.
        """
        newArgs = self.args + args
        newKwargs = dict(list(self.kwargs.items()) + list(kwargs.items()))
        self.method(*newArgs, **newKwargs)

    def toString(self):
        """Convert the command into an explicit string.
        
        Print the function or method in a way which looks (in most cases)
        the way the command would look if printed explicitly (i.e. they
        way you would write it to execute it immediately), with the
        positional and keyword arguments written in.
        """

        arguments = []
        for arg in self.args:
            arguments.append(str(arg))
        for arg in self.kwargs:
            arguments.append(arg + '=' + repr(self.kwargs[arg]))

        substitution = ', '.join(arguments)
        return '%s(%s)' % (self.method.__name__, substitution)

    def __str__(self):
        """Convert the command into an explicit string.
        
        Print the function or method in a way which looks (in most cases)
        the way the command would look if printed explicitly (i.e. they
        way you would write it to execute it immediately), with the
        positional and keyword arguments written in.
        """
        return self.toString()


def prompt(string, choices=None):
    """Present a user with options.
    
    Parameters
    ----------
    string : str
        A string to tell the user what he is choosing.
    choices : list of str
        A list of strings representing the available choices. If `None`, the
        default list will be `['OK', 'Cancel']`.
        
    Returns
    -------
    int
        The index of the selected option within the `choices` list. Note that
        for this purpose, the list is zero-indexed.
    """
    if choices is None:
        choices = ['OK', 'Cancel']

    width = str(len(choices) + 2)
    formatString = '  %' + width + 'd: %s'
    print(string)
    for i, item in enumerate(choices):
        print(formatString % (i + 1, item))

    while True:
        answer = input('Selection: ')
        try:
            sel = int(answer) - 1
            if 0 <= sel < len(choices):
                return sel
            print('Selection out of range.')
        except (ValueError, TypeError):
            print('Invalid selection.')


def simpleLinearRegression(xPoints, yPoints):
    """Perform a simple linear regression on data.
    
    Parameters
    ----------
    xPoints : list of float
        The list of x-values of the points to fit.
    yPoints : list of float
        The list of y-values of the points to fit.
    
    Returns
    -------
    float
        The slope of the trend line.
    float
        The y-intercept of the trend line.
    float
        The correlation coefficient (usually denoted by *R*) of the trend
        line.
    float
        The minimum y-value in the data set.
    float
        The maximum y-value in the data set.
    """
    length = len(xPoints)
    if length <= 1:
        return (0.0, 0.0, 0.0)
    xTot = 0.0
    yTot = 0.0
    xSquareTot = 0.0
    ySquareTot = 0.0
    xyTot = 0.0
    maxVal = float('-inf')
    minVal = float('inf')
    for xPoint, yPoint in zip(xPoints, yPoints):
        xTot += xPoint
        yTot += yPoint
        xSquareTot += xPoint * xPoint
        ySquareTot += yPoint * yPoint
        xyTot += xPoint * yPoint
        if yPoint > maxVal:
            maxVal = yPoint
        if yPoint < minVal:
            minVal = yPoint
    numerator = (xyTot - xTot * yTot / length)
    try:
        slope = numerator / (xSquareTot - xTot * xTot / length)
    except ZeroDivisionError:
        slope = float('inf')
    try:
        coefficient = (numerator / sqrt((xSquareTot - xTot * xTot / length) *
                                      (ySquareTot - yTot * yTot / length)))
    except ZeroDivisionError:
        coefficient = 0.0

    return (slope, (yTot - slope * xTot) / length, coefficient, minVal, maxVal)
