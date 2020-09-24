# transport
A Python program for collecting data from scientific laboratory instruments

I started writing this to collect data without relying on LabVIEW. Nobody else in my research group seemed interested, and eventually I had to put it aside to work on other things. The interface is functional, and it should work with a handful of different instruments. Implementing new instruments is straightforward. One need only follow the pattern of the existing ones (or follow instructions in the manual) and put them into the `/lib/instruments` folder.
