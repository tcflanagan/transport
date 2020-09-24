===============================
Extending the Code: Instruments
===============================

Writing code for new instruments is usually quite straightforward (the
main exception being cryostats, which take quite a bit of work). Below
are the basic instructions for how to go about doing it and some
pitfalls which would make the code fail.

Introduction
------------

Since most instruments today follow a rather specific standard specified
by IEEE, writing code to run them is quite simple. Nearly all instruments
which can be connected to the computer via GPIB, USB, or RS232 implement
VISA standards, and so the PyVISA module does all the work. Further,
the commands follow a fairly standard form.

The first step in coding a new instrument is to create a module for it. For
everything to work, there are a few requirements, which follow.

1. The module must be placed in the :py:mod:`src.instruments` package.
2. The module must contain a class which inherits from the
   :py:class:`src.core.instrument.Instrument` class.
3. The class constructor (the :py:meth:`__init__` method) must
   have the signature of an `Instrument`, it must call the its 
   superclass constructor, and it must define all attributes of
   the class.
4. The new instrument must implement a class method
   :py:meth:`getRequiredParameters` which should return a list of
   :py:class:`src.core.instrument.InstrumentParameter` objects. Each
   of these objects indicates one attribute which must be specified in
   order for the instrument to work. For most GPIB instruments, the
   list will include only one element: the VISA resource address.
5. It must implement the methods :py:meth:`initialize`, which opens
   a communication channel with the instrument, and 
   py:meth:`finalize`, which closes said communication channel. Note
   that both of these methods are called automatically.
6. It must implement the :py:meth:`getActions` method, which returns a
   list of :py:class:`src.core.action.ActionSpec` objects indicating
   what actions the instrument can perform.

Let's consider these steps individually, with the SRS 830 Lock-In Amplifier
as an example.

Module and class creation
-------------------------

The first is fairly obvious. The module name should be 
:file:`src/instruments/srs830.py`.

The second step means that the class definition line should reference the
:py:class:`Instrument` object. The module header, of course, must import
this object::
   
   from src.core.instrument import Instrument

The class definition line should then look like this::

   class SRS830(Instrument):

The instrument specification
----------------------------

Configuring an instrument for use will often require a bit of information
about the instrument. These parameters are specified via instances of the
:py:class:`InstrumentParameter` class, which stores four attributes:

description
    A short, user-readable description of the parameter.

value
    The value of the parameter. The default is an empty string.

allowed
    The values which the parameter will accept, specified as a list
    of strings. If set to ``None``, any value will be accepted.

formatString
    A string indicating how the value should be formatted. See
    :ref:`format-string-syntax`.

For typical GPIB instruments, the only bit of such information will be
its resource address, and so the :py:meth:`getRequiredParameters`
method will return a single-element list as follows::

   @classmethod
   def getRequiredParameters(cls):
       return [
           InstrumentParameter(
	       description='Visa Address',
	       value='',
	       allowed=Instrument.getVisaAddresses,
	       formatString='%s'
           ) 
       ]

This method simply returns the default for the :py:class:`Instrument`
subclass. The actual **value** for an **instance** is stored in the
attribute :py:attr:`_spec`.

.. warning:: Specifying a value for :py:attr:`allowed` makes no sense
   unless the value is a string.

Initialization and finalization
-------------------------------

The constructor must be of the form::

   def __init__(self, experiment, name='SRS830: Lock-in', spec=None):
       super(SRS830, self).__init__(experiment, name, spec)
       self._inst = None
       self._info = None

The requirement concerning the signature is, of course, implemented in
the first line. Notice that all but :py:attr:`experiment` are optional (they
have default values specified). The second line calls the parent class's
constructor, and the third and fourth lines create the class's attributes,
which will be assigned actual values when the instrument is initialized (at
the beginning of the experiment's execution), as will be described next.

The fourth step requires that the instrument implement the
:py:meth:`initialize` and :py:meth:`finalize` methods, which run at the
beginning and the end of the experiment. Examples are the following::

   def initialize (self):
       """Initialize the lock-in."""
       self._inst = visa.instrument(self._spec[0])
       info = ['Instrument: ' + self._name,
               'SRS 830: Lock-in amplifier',
	       self._inst.ask('*IDN?')]
       self._info = '\n'.join(info)

   def finalize (self):
       """Finalize the lock-in."""
       self._inst.close()

In the :py:meth:`initialize` method, the :py:attr:`_inst` attribute is
set to a :py:class:`pyvisa.visa.Instrument` object. The argument to
the constructor is the VISA resource address. The :py:attr:`_info`
attribute is set to a three-line string describing the instrument,
including its user-defined name, its model, and what it knows about
itself.

In the :py:meth:`finalize` method, the instrument communication channel
is closed to free system resources.


Actions
-------

Most instruments implement two types of actions: simple actions, which can
set or read values, and scans, which repeat a simple action with multiple
values. Regardless of its type, the action must define the following values:

experiment
    The :py:class:`Experiment` object which owns the
    instrument. This will nearly always be the :py:class:`Experiment` which
    owns the instrument, and so you can pass the attribute
    :py:attr:`self._expt`.

instrument 
    The :py:class:`Instrument` object which owns the
    action. This should nearly always be :py:attr:`self`.

description
    A short phrase describing the action in a way that users can understand.

inputs
    A list of parameters which will be sent to the instrument when it's
    time for it to perform the action.

outputs
    A list of parameters which the instrument will return once it has 
    finished performing the action.

string
    A template string which will be filled in for turning the complete
    action sequence into strings for conveying information to the user.

method
    The (bound) method  which will carry out the action. This will be
    discussed further later.

An action will be specified through a :py:mod:`collections.namedtuple`
instance, :py:class:`ActionSpec`, which has three attributes:
:py:attr:`name`, a one-word name for the action, mainly for lookup 
purposes; :py:attr:`cls`, the :py:class:`Action` class, or one of its
subclasses, which will be used to construct the object; and 
:py:attr:`args`, a dictionary containing the keys listed above and their
respective values.

An :py:class:`ActionScan` object must have **one and only one** input, which
should be a list of three-element tuples specifying the default range
over which some quantity is varied. This range will be expanded, and the
values will be passed sequentially to the method specified in the
:py:class:`ActionSpec`.

Parameters
----------

Parameters are specified through a
:py:mod:`collections.namedtuple` instance, :py:class:`ParameterSpec`,
which has attributes :py:attr:`name` and :py:attr:`args`. The first
should be a short, single-word string to specify the parameter, and the
second is a dictionary containing the following properties:

experiment
    The :py:class:`src.core.experiment.Experiment` object which owns
    the action which owns the parameter.

description
    A short phrase describing the parameter in a way that users can
    understand.

value
    The default value for the parameter. It should be of the correct data
    type.

    .. note:: If the action is an :py:class:`ActionScan`, the value
       should be specified as a list of tuples indicating the default
       scan components. For example, ``'value': [(0.0, 1.0, 0.1),
       (1.0, 2.0, 0.5)]`` would by default scan from 0.0 to 1.0 in
       steps of 0.1 and then from 1.0 to 2.0 in steps of 0.5.

binName
    The default name for the data storage bin to which the value will
    be saved, or ``None`` if it will not be saved by default.

binType
    The default type of data bin (either 'column' or 'parameter', or ``None``
    if the data will not be saved by default).

formatString
    A string indicating how the value should be formatted. See 
    :ref:`format-string-syntax`.
    
    .. note:: If the action is an :py:class:`ActionScan`, the formatString
       should end with '[]'

allowed
    A list containing the allowed values for the parameter. This only makes
    sense if the data type is a string.

The action syntax
-----------------

The :py:meth:`getActions` method should return a list of
:py:class:`ActionSpec` objects specifying all the actions which the
instrument can perform (or, at least, all the actions which users of the
instrument will *want* to perform).

The syntax for defining such an :py:class:`ActionSpec` is as follows ::

    ActionSpec(
        name='set_vref', 
	cls=Action, 
	args={
	    'experiment': self._expt, 
            'instrument': self, 
            'description': 'Set reference voltage',
            'inputs': [
                ParameterSpec(
	            name='vref', 
                    args={
                       'experiment': self._expt,
                       'description': 'Vref', 
                       'formatString': '%.4f', 
                       'binName': 'Vref', 
                       'binType': 'parameter', 
                       'value': 0, 
                       'allowed': None, 
                       'instantiate': False
  	            }
                )
            ],
            'string': 'Set the sine-out voltage to $vref.',
            'method': self.setReferenceVoltage
        }
    )

The :py:attr:`name` values are very important. The name of 
the input parameter here is 'vref', and you can see that the same value
occurs in the 'string' value for the :py:class:`ActionSpec`. This is
not a coincidence. When the software attempts to create informative
strings about a given action, it will fill in the 'string' value,
replacing all occurances of "${name}" with the value of the parameter
specified by ``{name}``.

.. warning:: The values of :py:attr:`name` **must not contain spaces or
   special characters other than underscores**.

In the above code, the 'method' entry is set to 
:py:meth:`self.setReferenceVoltage`. This is class method bound to the
instance of the class whose :py:meth:`getActions()` method is called.
Note the lack of parentheses at the end. This means that it is the
**method itself**, and *not* the return value of the method, which is
being put in that slot.

Defining the methods
--------------------

Now, of course, to pass the :py:meth:`setReferenceVoltage` to anything, the
method must be defined in the class. 

The first step in defining such a method is to find out the command
which will induce the instrument to do what the :py:class:`Action`
wants. Referring to the manual for the SRS 830, we find that the command to
set the reference voltage is "SLVL". Then the method to perform the 
action could be written like this::

    def setReferenceVoltage (self, vref):
        self._inst.write('SLVL %.4f' % vref)
	return ()

The arguments to the method are ``self``, which is required in all
methods, and ``vref``, which is the desired value for the reference voltage.

.. warning:: There are some important things to remember about the
   ``vref`` argument. 

   1. It has the same name as one of the :py:class:`ParameterSpec` objects
      defined in the :py:meth:`getActions` method above. It is the value
      of that parameter which will be substituted into this method, so if
      the names of the arguments to the method are not **exactly the same**
      as the names of the :py:class:`ParameterSpec` objects defined in the
      'inputs' bin of the relevant :py:class:`ActionSpec`, the  **software 
      will crash**.
   2. It is passed in whatever type is natural to the parameter. Since the
      reference voltage is a floating-point number, ``vref`` will be passed
      as a ``float``. Therefore, since the SRS830 accepts ASCII string
      commands, the value must be turned into a string. That is why the
      string substitution occurs in the :py:meth:`write` call above.
   3. If the method is bound to the :py:class:`ActionSpec` of an
      :py:class:`ActionScan`, the method must have **one and only one**
      argument.

.. _format-string-syntax:

Format string syntax
--------------------

Format strings follow format which is fairly standardized (it's actually the
same as in LabVIEW). Such a string begins with the percent symbol. The
final character depends on the data type:

=========== =========
type        character
=========== =========
integer     "d"
string      "s"
float       "f"
exponential "e"
=========== =========

For the last two data types, both floating-point, the precision is
specified by a period followed by the number of digits which should be
printed after the decimal point. This bit should be between the
percent sign and the data-type indicator.  For example, to the format
a number into a string of the form "2.012592e+02", use "%.6e".

There are actually considerably more options for customizing the
string formatting, but they are less frequently used. More information
can be found in a variety of places. For examples in the Python
language specifically, see `the official documentation
<http://docs.python.org/2/library/stdtypes.html#string-formatting-operations>`_

Summary of potential problems
-----------------------------

Here is a recap of the simple mistakes which would cause the program to
crash.

1. The names of the :py:class:`ParameterSpec` objects defined under
   'inputs' for the relevant :py:class:`ActionSpec` must **precisely
   match** the names of the arguments to the 'method' defined by said
   :py:class:`ActionSpec`.
2. The names of :py:class:`ParameterSpec` objects must also **precisely
   match** the values of the substitution strings (indicated by a dollar
   sign followed by the name) in the 'string' slot of the relevant
   :py:class:`ActionSpec`.
3. The value of each argument to an instrument method needs to be 
   converted to an appropriately formatted string if the natural type of 
   the value is not already a string.
4. The value of 'allowed' for some :py:class:`ParameterSpec` or
   :py:class:`InstrumentParameter` should be ``None`` unless the
   value of the parameter should be a string and only certain
   values are allowed for that string, in which case 'allowed' should be
   a list of strings.
5. Values of the :py:attr:`name` attribute of instances of
   :py:class:`ActionSpec` or :py:class:`ParameterSpec` must **not** contain
   spaces or special characters (except the underscore).
6. For :py:class:`ActionScan` objects, the 'formatString' of the
   :py:class:`ParameterSpec` should end with "[]"
7. An :py:class:`ActionScan` must have **one and only one** input, whose
   value is a list of three-element tuples which will be expanded into a
   range whose values will be passed sequentially into the method.
