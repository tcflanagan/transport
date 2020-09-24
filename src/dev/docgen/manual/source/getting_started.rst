===============
Getting Started
===============


Running from source
===================

The Python Interpreter
----------------------

The primary dependency for the system is the Python interpreter. The
code was written using **verson 2.7.5**. Note that any version greater
or equal to than 3 will **not** work, mostly because the dependencies in
the following sections have not all been updated to reflect changes in
going from 2.x to 3.x. The most significant of these (and the most
important in the context of this program) is PyVISA.

Dependencies
------------

The following packages must be installed in order to run the
program:

**wxPython** (2.8.12.1)
    wxPython_ is the graphical engine for the software. It was chosen for a number of reasons, some of which are listed below.
    #. It is fast, since it is merely a wrapper for the C-based wxWidgets library.
    #. Its API is relatively intuitive.
    #. It is popular, so it can be found in most (Debian-based) Linux repositories.

**PyVISA** (1.4)
    PyVISA_ is a library for interacting with GPIB and serial instruments.

**numpy** (1.7.1) and **scipy** (0.12.0)
    numpy_ and scipy are libraries for performing mathematical calculations. They are closely linked so downloads_ and documentation_ can usually be found together.

**matplotlib** (1.2.1)
    matplotlib_ is a plotting library which duplicates MATLAB in many ways.

.. _wxPython: http://www.wxpython.org
.. _PyVISA: https://pyvisa.readthedocs.org/en/latest/
.. _numpy: http://www.numpy.org/
.. _downloads: http://new.scipy.org/download.html
.. _documentation: http://docs.scipy.org/doc/
.. _matplotlib: http://matplotlib.org/

The numbers in parentheses are, of course, versions. They are
the versions under which the software was written and, therefore, the
most likely to work as expected. This does not necessarily mean that
other versions will not work. However, you *must* install versions
which are compatible with Python 2.7.

Tools for managing documentation
--------------------------------

As with any piece of software which multiple people may use and edit, it is essential to keep the documentation up to date and accurate. There are a number of tools which have been used to produce the documentation for this code in a clear and consistent way, and these are outlined in this section.

Python libraries
****************

**Pygments**
    Pygments_ is a package for syntax highlighting which is used by Sphinx.

.. _Pygments: http://pygments.org/

**Sphinx**
    This documentation starts out as a set of plain-text documents in the markup language reStructuredText_, or reST. It is compiled into HTML, PDF, and HTML Help files using a package called Sphinx_.

.. _reStructuredText: http://docutils.sourceforge.net/rst.html
.. _sphinx: http://sphinx-doc.org/

**sphinx_wxoptimize**
    sphinx_wxoptimize is a set of scripts for fixing the HTML Help packages produced by Sphinx so that it can be read in a reasonably decent manner by wxPython. You can find it at PyPI_.

.. _PyPI: https://pypi.python.org/pypi/sphinx_wxoptimize/

It should be noted that the first two of the above, Pygments and Sphinx, can be installed using ``pip``, while the third, the script ``sphinx_wxoptimize``, is already included in the ``src/tools/docgen/manual`` folder, so it should not need to be installed.

**numpydoc**
    The in-code documentation uses an extension to the standard Sphinx library called numpydoc_, which allows for a cleaner-looking in-code syntax. Regenerating the API will crash Sphinx if this is not installed.

.. _numpydoc: https://pypi.python.org/pypi/numpydoc


External applications
*********************

**LaTeX**
    The PDF manual is, of course, generated using ``pdflatex``, so LaTeX must be installed.

**Subversion**
    Keeping the most recent version of the software available to everybody using it is a good idea, and for this project it is facilitated by Subversion. Download it. The most popular graphical client for Windows is TortoiseSVN_. To use this software's automatic updater requires the command-line SVN tools. For Windows, the most common version is Slik Subversion, which can be downloaded here_.

.. _TortoiseSVN: http://tortoisesvn.net/
.. _here: http://www.sliksvn.com/en/download


Tools
-----

The most useful tool for this project is Eclipse, with the PyDev extension.    

Instructions for installing this are coming soon.

Testing some code
=================

Now let's test some junk.

::

   def some_function(input_parameter):
       '''Print `input_parameter`, then attempt to convert it
       to a dictionary.
       '''
       print input_parameter
       try:
           return dict(input_parameter)
       except TypeError:
           print 'Cannot do that'
	   return None
