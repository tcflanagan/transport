"""Software sources.

===========
The objects
===========

This software makes heavy use of the object-oriented paradigm. A typical
experiment consists of a sequence of commands sent to and responses read from
some collection of instruments. Each instrument is represented, naturally
enough, by an `Instrument` object, and each operation on a given instrument
is represented by an `Action` object (or an object of one of its subclasses).

============
Sub-packages
============

`core`
    The `core` package contains the modules which are primarily responsible for
    the general operation of an experiment. This includes modules defining the
    prototypical `Action` and `Experiment`.
`dev`
    The `dev` package contains a few modules which are useful for the
    development of the software, including scripts for generating the 
    documentation and updating the subversion repository. It also contains
    some components which are in the process of being written and not yet
    suitable for incorporation in the main program.
`gui`
    The `gui` package contains the components of the graphical front-end to the
    contents of the `core` package.
`instruments`
    The `instruments` package contains modules which define classes which  
    serve as explicit representations of specific instruments. Essentially,
    these classes act as high-level drivers for the instruments.
`premades`
    The `premades` package provides a collection of graphical interfaces for
    quickly configuring the system to perform common measurements, like
    magnetoresistance measurements, which are performed so frequently and in
    such a uniform manner (i.e. they are performed in essentially the same way
    every time) that dealing with the full, customizable sequence editor would
    be excessive.
`tools`
    The `tools` package consists of a number of utility modules for interacting
    with the computer or other computers, monitoring trends in data, and 
    performing calculations, among other things. 
"""