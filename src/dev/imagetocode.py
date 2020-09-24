"""A script to convert icons in png format to code.

Icons in code format can be loaded faster and more easily shipped with compiled
code. The script here takes png images and converts them to code which can be
imported and used in various graphical interface modules.
"""

import wx.tools.img2py as itp
from src.tools import path_tools as pt
from os import path

def generateAdditional(string):
    """Create a code string for defining the helper methods."""
    subs = (string, string, string, string)
    return 'get%sBitmap = %s.GetBitmap\nget%sIcon = %s.GetIcon\n' % subs

def run():
    """Convert icon image files to wxPython-recognizable code."""
    inDir = pt.unrel('img', 'png')
    outFile = pt.unrel('src', 'gui', 'images.py')

    imgData = [('80experiment_new.png', 'ExperimentNew', False),
                 ('80experiment_open.png', 'ExperimentOpen', False),
                 ('80experiment_premade.png', 'ExperimentPremade', False),
                 ('banner_combined.png', 'Banner', False),
                 ('20ok.png', 'Ok', True),
                 ('scan_16_up.png', 'ScanUp', True),
                 ('scan_16_down.png', 'ScanDown', True),
                 ('scan_16_add.png', 'ScanAdd', True),
                 ('scan_16_insert.png', 'ScanInsert', True),
                 ('scan_16_remove.png', 'ScanRemove', True),
                 ('24experiment.png', 'ExperimentButton', True),
                 ('24constants.png', 'ConstantsButton', True),
                 ('24instruments.png', 'InstrumentsButton', True),
                 ('24graphs.png', 'GraphsButton', True),
                 ('24run.png', 'RunButton', True),
                 ('24pause.png', 'PauseButton', True),
                 ('24stop.png', 'StopButton', True),
                 ('24home.png', 'HomeButton', True),
                 ('16experiment.png', 'ExperimentIcon', True),
                 ('16constants.png', 'ConstantsIcon', True),
                 ('16instruments.png', 'InstrumentsIcon', True),
                 ('16graphs.png', 'GraphsIcon', True),
                 ('16graph_zoom.png', 'GraphZoom', True),
                 ('16graph_fit.png', 'GraphFit', True),
                 ('16graph_move.png', 'GraphMove', True),
                 ('16graph_lock.png', 'GraphLock', True),
                 ('16graph_unlock.png', 'GraphUnlock', True),
                 ('24interrupt.png', 'Interrupt', True)]

    for i, data in enumerate(imgData):
        inFile, imageName, genIcon = data
        inFile = path.join(inDir, inFile)
        itp.img2py(inFile, outFile, i > 0, imgName=imageName, icon=genIcon)
        with open(outFile, 'a') as fileObject:
            fileObject.write(generateAdditional(imageName))

    lines = ['#pylint: skip-file\n']
    with open(outFile, 'r') as fileObject:
        lines.extend(fileObject.readlines())
    with open(outFile, 'w') as fileObject:
        fileObject.write(''.join(lines))

if __name__ == '__main__':
    run()
