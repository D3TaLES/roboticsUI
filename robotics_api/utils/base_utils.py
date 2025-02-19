import pint
import time
import serial
from robotics_api.settings import *


def sig_figs(number: float or str, num_sig_figs=5):
    """
    Round a number to the specified number of significant figures.

    Args:
        number (float): The number to round.
        num_sig_figs (int): The number of significant figures to retain.

    Returns:
        float: The number rounded to the given significant figures.
    """
    if isinstance(number, str):
        ureg = pint.UnitRegistry()
        number = ureg(number).magnitude
    if number == 0:
        return 0  # Zero remains zero regardless of sig figs
    if num_sig_figs <= 0:
        raise ValueError("Number of significant figures must be greater than zero.")

    import math
    # Calculate the order of magnitude
    magnitude = math.floor(math.log10(abs(number)))
    # Scale the number to round at the desired decimal place
    scale = 10 ** (magnitude - num_sig_figs + 1)
    # Scale the number, round it, and scale it back
    rounded = round(number / scale) * scale

    # Avoid floating-point representation issues by formatting
    return float(f"{rounded:.{num_sig_figs - 1}e}")


def unit_conversion(measurement, default_unit: str, density=None, return_dict=False):
    """
    Convert a measurement into a default unit using pint.

    :param measurement: Measurements can be pint object, int or float(in which case it will be assumed to already be in the default unit), string of magnitude and unit, or a measurement dictionary (EX: {"value": 0.5, "unit": "eV"}
    :param default_unit: default unit / unit to be converted to
    :param return_dict:
    :param density: molecular density (in case needed for conversion)
    :return: float magnitude for the converted measurement
    """
    if measurement is None:
        return None
    # Set context in case conversion include mass-->volume or volume-->mass
    ureg = pint.UnitRegistry()
    c = pint.Context('mol_density')
    if density:
        c.add_transformation('[mass]', '[volume]', lambda ureg_c, x: x / ureg_c(density))
        c.add_transformation('[volume]', '[mass]', lambda ureg_c, x: x * ureg_c(density))
    ureg.add_context(c)
    # Get measurement value and unit
    if not isinstance(measurement, (str, float, int, dict)):
        value, unit = getattr(measurement, "magnitude"), getattr(measurement, "units")
    else:
        value = measurement.get("value") if isinstance(measurement, dict) else measurement
        unit = ""
        if isinstance(value, float) or str(value).replace('.', '', 1).replace('-', '', 1).isdigit():
            unit = measurement.get("unit", default_unit) if isinstance(measurement, dict) else default_unit
    # Convert measurement to default unit
    unit = default_unit if unit == "dimensionless" else unit
    pint_unit = ureg("{}{}".format(value, unit))
    if return_dict:
        return {"value": pint_unit.to(default_unit, 'mol_density').magnitude, "unit": default_unit}
    return pint_unit.to(default_unit, 'mol_density').magnitude


def write_test(file_path, test_type=""):
    """
    Writes test data to a file based on the test type.

    Args:
        file_path (str): Path to the output file.
        test_type (str): Type of test data to write. Options are "cv", "ca", or "ircomp".
    """
    test_files = {
        "cv": os.path.join(TEST_DATA_DIR, "standard_data", "CV.txt"),
        "ca": os.path.join(TEST_DATA_DIR, "standard_data", "CA.txt"),
        "ircomp": os.path.join(TEST_DATA_DIR, "standard_data", "iRComp.txt"),
    }
    test_fn = test_files.get(test_type.lower())
    if os.path.isfile(test_fn):
        with open(test_fn, 'r') as fn:
            test_text = fn.read()
    else:
        test_text = "test"
    with open(file_path, 'w+') as fn:
        fn.write(test_text)


def send_arduino_cmd(station: str, command: str or float, address: str = ARDUINO_PORT, return_txt: bool = False):
    """
    Sends a command to the Arduino controlling a specific station.

    Args:
        station (str): The station identifier (e.g., "E1", "P1").
        command (str or float): The command to send (e.g., "0", "1", "500").
        address (str): Address of the Arduino port (default is ARDUINO_PORT).
        return_txt (bool): Whether to return the Arduino response text (default is False).

    Returns:
        bool or str: True if the command succeeded, the response text if return_txt is True, otherwise False on failure.

    Raises:
        Exception: If unable to connect to the Arduino.
    """
    try:
        arduino = serial.Serial(address, 115200, timeout=.1)
    except:
        try:
            time.sleep(20)
            arduino = serial.Serial(address, 115200, timeout=.1)
        except:
            raise Exception("Warning! {} is not connected".format(address))
    time.sleep(1)  # give the connection a second to settle
    arduino.write(bytes(f"{station}_{command}", encoding='utf-8'))  # EX: E1_0 or P1_1_500
    print("Command {} given to station {} at {} via Arduino.".format(command, station, address))
    start_time = time.time()
    try:
        while True:
            print("trying to read...")
            data = arduino.readline()
            print("waiting for {} arduino results for {:.1f} seconds...".format(station, time.time() - start_time))
            if data:
                result_txt = data.decode().strip()  # strip out the old lines
                print("ARDUINO RESULT: ", result_txt)
                if "success" in result_txt:
                    return result_txt if return_txt else True
                elif "failure" in result_txt:
                    return False
            time.sleep(1)
    except KeyboardInterrupt:
        arduino.write(bytes(f"ABORT_{station}", encoding='utf-8'))
        while True:
            print("Aborted arduino. Trying to read abort message...")
            data = arduino.readline()
            if data:
                print("ARDUINO ABORT MESSAGE: ", data.decode().strip())  # strip out the old lines
                raise KeyboardInterrupt
            time.sleep(1)