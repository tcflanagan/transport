"""Basic information about the program and changes to it."""

APP_NAME = 'Transport'
APP_FOLDER = 'Transport1'
DATA_FOLDER = 'transport'

VERSIONS = [[(0, 8, 0), '2020-07-17', '13:05',
             ['Updated the program to use Python 3.']],
            [(0, 7, 1), '2015-04-22', '07:07',
             ['Fixed a bug in the Vector Magnet controller frame.']],
            [(0, 7, 0), '2014-07-02', '14:02',
             ['Changed a bunch of loops to comprehensions in action.py.',
              'Created methods for generating controllers in inst_manager.py.',
              'Added methods and attributes for instruments to track whether '
              'they have been initialized.',
              'Began writing a lock-in controller frame.',
              'Developed a new FormPanel helper class in gui_helpers.py.',
              'Developed a way to access instrument controllers from a menu '
              '(the controllers are dynamically loaded).',
              'Rearranged the file hierarchy for controllers somewhat.']],
            [(0, 6, 0), '2014-06-27', '18:41',
             ['Overhauled the vector magnet control frame, and wrote the '
              'actual controller object.',
              'Performed some efficiency enhancement in configuration.py.']],
            [(0, 5, 1), '2014-06-26', '10:11',
             ['Fixed some issues with dialogs defaulting to the appropriate '
              'folders.',
              'Fixed some configuration dialog sizing issues.']],
            [(0, 5, 0), '2014-06-16', '07:45',
             ['Changed how file extensions work---now using parameters '
              'defined in settings.py.',
              'Added classes for handling getting run-time information from '
              'the user.']],
            [(0, 4, 0), '2014-05-30', '19:40',
             ['Rewrote the instrument loader to use Python introspection '
              'features rather than regular expression parsing.',
              'Removed some junk from the class hierarchy for instruments, '
              'including all abstract base classes, which were rendered '
              'superfluous by the change to proper introspection.',
              'Modified the experiment open and save feature to use XML files '
              'instead of pickle files.']],
            [(0, 3, 1), '2014-04-24', '11:32',
             ['Cleaned up some code in experiment.py, removing duplication '
              'with expression/conditional evaluation and deleting methods '
              'which are never used.',
              'Began writing a controller frame for the vector magnet.',
              'Fixed some problems with opening and saving experiments.']],
            [(0, 3, 0), '2014-04-19', '19:45',
             ['Created a basic system for defining postprocessor functions ' 
              'and a new Action subclass to go with it.',
              'Created a frame for displaying experiment info on request.',
              'Fixed a bug triggered when double-clicking on the end-of-'
              'container lines in the Sequence Editor.',
              'Wrote code for turning an experiment into XML and began ' 
              'writing a script to convert it back.',
              'Modified the method for setting experiment interaction '
              'parameters to accept only keyword arguments (eliminating the '
              'method for clearing said parameters).']],
            [(0, 2, 0), '2014-04-07', '14:48',
             ['Removed seconds from the changelog timestamps.',
              'Fixed some docstrings to be in accord with recent changes.',
              'Changed the logging system to show only a single character for' 
              'the logging level.',
              'Wrote some summary-level docstrings for the src package.',
              'Made oxford_common.py load visa from instrument.py rather '
              'than from pyvisa directly.',
              'Removed the oxford_common_fake garbage.',
              'Changed the formatting of the logging system slightly.',
              'Significantly expanded the available lock-in amplifier ' 
              'methods and actions to the point of possible usefulness.']],
            [(0, 1, 5), '2014-03-27', '17:52',
             ['Made it so that moving things in the SequenceFrame does not '
              'affect the clipboard.',
              'Fixed Parameter cloning behavior so that the instantiate '
              'attribute is set to False for clones.',
              'Fixed some silly sizing issues in the filename panel for '
              'premades.',
              'Rewrote the versioning system to make the changelog an in-code '
              'system.',
              'Reformatted the log file header',
              'Modified the SVN update system so that the message comes '
              'from the in-code changelog rather than from a dialog. The '
              'update no longer affects anything locally---it only updates '
              'the repository. It may still optionally update documentation.',
              'Removed versioning.py.']],
            [(0, 1, 4), '2014-03-09', '12:32',
             ['Fixed a problem with the sizing on the while-loop dialogs.']],
            [(0, 1, 3), '2014-03-05', '09:24',
             ['Started writing some dummy Oxford classes for testing '
              'purposes.']],
            [(0, 1, 2), '2014-02-19', '12:00',
             ['Made progress on single, unified configuration parser, and set '
              'it up for use in base_premade.py and configuration.py',
              'Made the help data be loaded on use rather than on '
              'initialization.']],
            [(0, 1, 1), '2014-02-07', '10:33',
             ['Got sizing working properly on the custom grid (scan) panel',
              'Reorganized things slightly.']],
            [(0, 1, 0), '2014-02-04', '09:18',
             ['Added a way to interrupt manual loop actions in the ' 
              'SequenceFrame',
              'Added a basic way to prompt for user input from the command '
              'line.',
              'Renamed status_monitor.py to progress.py.',
              'Put basic version information into an about.py module.',
              'Moved file-naming stuff into appropriate modules---'
              'file_naming.py and instrument.py, under System---out of '
              'pathtools.py.',
              'Got rid of some pointless methods regarding forcing lengths to '
              'three in path_tools.py.',
              'Moved stability checkers from general.py to stability.py.']],
            [(0, 0, 8), '2014-01-27', '15:41',
             ['Minor changes to the organization, moving all development-'
              'related things into a separate dev package.']],
            [(0, 0, 7), '2014-01-23', '11:31',
             ['Began writing a new scrolled grid panel.']],
            [(0, 0, 6), '2014-01-22', '11:31',
             ['Finished the dialog for auto-naming files. Wrote a panel for '
              'displaying the results. Changed the auto-naming data storage to '
              'use a specialized container class.']],
            [(0, 0, 5), '2014-01-21', '20:14',
             ['Made minor modifications to the SVN Updater dialog.']],
            [(0, 0, 4), '2014-01-21', '20:11',
             ['Wrote a dialog to take parameters for generating filenames '
              'according to group customs.']],
            [(0, 0, 3), '2014-01-20', '09:06',
             ['Fixed a bug related to disabled graphs being improperly '
              're-enabled.',
              'Stopped trying to save graphs when none have been defined and '
              'enabled.',
              'Cleaned up the handling of displaying graph information ' 
              'slightly, so that experiment.py can give a list of tuples '
              'consisting of graph title and enabled state.',
              'Changed SequenceFrame to never show the extension for '
              'experiment filenames.',
              'Got rid of unusedbutpossiblyuseful.']],
            [(0, 0, 2), '2014-01-20', '06:29',
             ['Changed experiment.py to do calculations using the math module '
              'rather than the numpy module; it is significantly faster.',
              'Changed the format of log messages somewhat in experiment.py.',
              'Recompiled the documentation.',
              'Made other minor stylistic changes.']],
            [(0, 0, 1), '2014-01-19', '20:25',
             ['Refactored data saving in experiment.py, inlining stuff and '
              'switching to a list comprehension. Timed it to make sure it was '
              'in fact faster. Removed some short, single-line methods.',
              'Experiment objects now can return only single graph objects and '
              'lists of the names of graphs, rather than full lists of graph '
              'objects.',
              'Fixed a bug where children inserted in some ways would not be'
              'properly instantiated.',
              'Moved the junk specific to ExperimentEditor experiments into'
              'expt_editor.py out of base_experiment.py (mostly stuff '
              'involving menus, toolbars, and copy-and-paste).',
              'Fixed a bug where graphs would not work when trying to run the '
              'same experiment a second time.',
              'Made the graphs clear their extrema at the end of each run.',
              'Made the GraphPanel toolbar work the way I wanted---buttons '
              'now are Zoom, Pan, Fit, and Toggle Updates.']],
            [(0, 0, 0), '2014-01-13', '09:58',
             ['Starting point (the end of version 0)']]]

def getVersion():
    """Return a string representing the current version."""
    return '%d.%d.%d' % VERSIONS[0][0]

def getLatestMessage():
    """Get a string representing the latest change information."""
    text = VERSIONS[0][3]
    return '\n'.join(text)
    
def getChangelog(lineLength=50):
    """Return the change log.
    
    Parameters
    ----------
    lineLength : int
        The maximum number of characters per line in the changelog string.
        
    Returns
    -------
    str
        A string indicating all recorded changes to the software.
    """
    answer = []
    for item in VERSIONS:
        version, date, time, text = item
        major, minor, rev = version
        answer.append('v%d.%d.%d  |  %s  |  %s' % 
                      (major, minor, rev, date, time))
        for line in text:
            logLines = []
            current = '  -'
            for word in line.split():
                if len(current + ' ' + word) < lineLength:
                    current += ' ' + word
                else:
                    logLines.append(current)
                    current = '    ' + word
            logLines.append(current)
            answer.append('\n'.join(logLines))
        answer.append('-' * lineLength) 
    return '\n'.join(answer)

def writeChangelog(logFile, lineLength=80):
    """Write the change log to a file.
    
    Parameters
    ----------
    logFile : str
        The path to which the change log should be written.
    lineLength : int
        The maximum number of columns in a single line of text.
    """
    with open(logFile, 'w') as outputFile:
        outputFile.write(getChangelog(lineLength))
