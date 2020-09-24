"""The modules which do all the real work.

The `core` package provides the primary modules for defining and executing an
experiment. An experiment in this context means a sequence of actions 
performed on various instruments, where an instrument can be a physical 
instrument, like a voltmeter or a cryostat, or merely the computer (for example,
waiting a specified amount of time or passing multiple actions simultaneously).

Note that all modules of the `core` package have been deliberately (sometimes,
unfortunately, at the expense of clarity) kept free of all explicit reference
to the graphical interface. This decision was made to keep open the possibility
of, at some point, switching to a different graphical system or even developing
a command-line interface to the software.
"""
