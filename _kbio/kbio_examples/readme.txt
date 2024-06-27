================================================================================
    EC-Lab Development Package: Interfacing with Python, an overview
================================================================================

To enable users a quick start building Python applications 
controlling potentiostats, we provide here two useful elements :

  * a small module layering over the EClib.dll library (kbio_api),
    which hides the low level details that this interface requires.
    
  * a set of simple, yet useful examples using this module.

The requirement on code using the kbio_api module is at least Python 3.7,
in 32b or 64b versions. The DLL will have to match the Python that you use.

////////////////////////////////////////////////////////////////////////////////

Script examples :
---------------

  * ex_api_misc.py
        This example connects to a potentiostat and provides information
        on the instrument and its channels.

  * ex_blfind.py
        This example uses the API discovery functions to list the instruments
        that the library can control.

  * ex_tech_OCV.py
        This example connects to a potentiostat, programs an OCV technique
        with a few set of parameters, then starts the experiment and displays
        experiment data.

  * ex_tech_CP.py
        This example connects to a potentiostat, programs a CP technique
        with a few set of parameters, then starts the experiment and displays
        experiment data.

These scripts require parameters which are provided at the beginning of the files,
you will need to adapt them to your configuration.


Module files :
------------

The kbio directory contains the module and ancillary files that make up the interface
to the EC-Lab library :

  * kbio_api.py
        The module that provides the interface (a Python API) to the ECLib and blfind DLL libraries.
        It is a one for one duplication of the API functions, but using either Python types or
        types defined in the package documentation. Error conditions are translated into exceptions.

  * kbio_tech.py
        Helper functions used when creating technique parameters and decoding
        experiment data.

  * kbio_types.py
        The Python types and constants that are the equivalent of those defined
        in the package documentation, plus a few helper methods/properties.

  * tech_types.py
        The technique types and constants that are the equivalent of those defined
        in the package documentation.

  * utils.py, c_utils.py
        Ancillary and low level functions used by the other Python code.
