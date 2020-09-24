import logging.config
import time
from src import about
from src.tools import path_tools as pt

_LINE_LENGTH = 70

def initialize():
    confFile = pt.unrel('etc', 'logging.conf')
    logFile = pt.unrel('log', time.strftime(r'expt%Y-%m-%d.log'), sep='/')
    logging.config.fileConfig(confFile, {'default_file': logFile})
    
    infoString = '%s  %s' % (about.APP_NAME, about.getVersion())
    
    logging.info('')

    logging.info('=' * _LINE_LENGTH)
    extraSpace = _LINE_LENGTH - len(infoString) - 4
    padLeft = extraSpace // 2
    padRight = extraSpace // 2
    if extraSpace % 2 == 1:
        padRight += 1
    logging.info('=' * padLeft + '  ' + infoString + '  ' + '=' * padRight)
    logging.info('=' * _LINE_LENGTH)
