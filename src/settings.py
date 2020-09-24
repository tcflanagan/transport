"""A module containing general settings. It will eventually be replaced."""


# Instrument driver locations; each is a list of path components relative to
# the project home.
DIR_INSTRUMENT_DRIVERS = ['src', 'instruments']

# Order of preference for instrument driver modules
INST_PREFERENCE_ORDER = ['py', 'pyc', 'pyo']

# File extensions
EXTS_EXPERIMENT = ['xpt', 'expt']
EXTS_DATA = ['xdat', 'dat', 'txt']
EXTS_PARAMETERS = ['xprm', 'param']
EXTS_IMAGE = ['png', 'jpg']