import pint


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