==============
 Installation
==============
The latest Windows installer can be found on PyPI:
    https://pypi.python.org/pypi?name=tdl&:action=display

Or if it's available you can use pip instead by running the command:
    pip install tdl

This module can also be manually installed by going into the "setup.py"
directory and running the command:
    python setup.py install

Already compiled libtcod libraries are included as part of the package data.
They won't need to be compiled as part of the installation, but can be replaced
with newer versions if necessary.

=======
 About
=======
TDL is a port of the C library libtcod in an attempt to make it more "Pythonic"

The library can be used for displaying tilesets (ANSI, Unicode, or graphical) in true color.

It also provides functionality to compute path-finding and field of view.

python-tdl is hosted on GitHub:
    https://github.com/HexDecimal/python-tdl

Online Documentation:
    http://pythonhosted.org/tdl/

Issue Tracker:
    https://github.com/HexDecimal/python-tdl/issues

python-tdl is a ctypes port of "libtcod".
You can find more about libtcod at http://doryen.eptalys.net/libtcod/

==============
 Requirements
==============
* Python 2.6+ or 3.x
* 32 bit Windows, 32/64 bit Linux, or Mac OS/X (64 bit architecture)

=========
 License
=========
python-tdl is distributed under the FreeBSD license, same as libtcod.
Read LICENSE.txt for more details.
