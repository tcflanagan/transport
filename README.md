# transport
A Python program for collecting data from scientific laboratory instruments

I started writing this to collect data without relying on LabVIEW. Nobody else in my research group seemed interested, and eventually I had to put it aside to work on other things. 

The interface is functional, and it should work with a handful of different instruments. Implementing new instruments is straightforward. One need only follow the pattern of the existing ones (or follow instructions in the manual) and put them into the `/lib/instruments` folder.

## Dependencies
The project uses Python 3. Below, I list things which are required but not part of a standard Python installation.

The following Python packages are available from PyPI or Conda repositories (some of them are installed by default if you installed Python through an Anaconda distribution).
* NumPy
* SciPy
* Matplotlib
* wxPython
* PyVISA

To actually communicate with instruments using the program, you will also need VISA drivers (the most popular are produced by National Instruments and can be downloaded from https://www.ni.com/en-us/support/downloads/drivers/download.ni-visa.html).

