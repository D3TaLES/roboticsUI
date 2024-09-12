import pint
from datetime import datetime
from d3tales_api.Processors.parser_echem import *
from robotics_api.settings import *
from robotics_api.actions.db_manipulations import ReagentStatus, ChemStandardsDB


def collection_dict(coll_data: list):
    """
    Create a dictionary from a list of dictionaries based on a common key.

    Args:
        coll_data (list): List of dictionaries.

    Returns:
        dict: A dictionary with keys as unique values from the 'collect_tag' field and values as lists of dictionaries
            having the same 'collect_tag' value.
    """
    tags = set([d.get("collect_tag") for d in coll_data])
    return {tag: [d for d in coll_data if d.get("collect_tag") == tag] for tag in tags}


def get_concentration(vial_content, solute_id, solv_id, soln_density=None, precision=3, mol_fraction=False):
    """
   Calculate the concentration of a solute in a solvent based on the provided vial content.

   Args:
       vial_content (list): List of dictionaries representing the content of the vial.
       solute_id (str, optional):
       solv_id (str, optional):
       soln_density (float, optional):
       precision (int, optional):
       mol_fraction (bool, optional):

   Returns:
       str: Concentration of the solute in the solvent, expressed in molarity.
   """
    solute_masses = [r.get("amount") for r in vial_content if r.get("reagent_uuid") == solute_id]
    solv_amounts = [r.get("amount") for r in vial_content if r.get("reagent_uuid") == solv_id]
    if not solute_masses or not solv_amounts:
        if FIZZLE_CONCENTRATION_FAILURE:
            raise Exception(f"Concentration calculation did not work...check all variables: solute_id={solute_id}, "
                            f"solv_id={solv_id}, solute_mass={solute_masses}, solv_vol={solv_amounts}")
        return DEFAULT_CONCENTRATION
    if not soln_density:
        warnings.warn("No solution density provided. Using reagent density instead...this may not be accurate. ")
        soln_density = f"{ReagentStatus(_id=solute_id).density}{DENSITY_UNIT}"
    ureg = pint.UnitRegistry()
    solute_mass = sum([ureg(u) for u in solute_masses])
    solv_amt = sum([ureg(u) for u in solv_amounts])
    solute_mw = ureg(f"{ReagentStatus(_id=solute_id).molecular_weight}g/mol")
    if mol_fraction:
        solute_mols = solute_mass / solute_mw
        total_mols = 0
        for reagent in vial_content:
            r_mw = ureg(f"{ReagentStatus(_id=reagent['reagent_uuid']).molecular_weight}g/mol")
            r_mass = reagent.get["amount"]
            total_mols += r_mass/r_mw
        x = solute_mols / total_mols
        return x.magnitude
    else:
        volume_L = unit_conversion(solv_amt, default_unit="L", density=soln_density)
        volume = ureg(f"{volume_L}L")
        concentration = solute_mass / solute_mw / volume
        return "{}{}".format(round(concentration.to(CONCENTRATION_UNIT).magnitude, precision), CONCENTRATION_UNIT)


def get_kcl_conductivity(temp):
    temp_k = round(unit_conversion(temp, default_unit="K"))
    return {
        15: 1141.5,
        16: 1167.5,
        17: 1193.5,
        18: 1219.9,
        19: 1246.4,
        20: 1273.0,
        21: 1299.7,
        22: 1326.6,
        23: 1353.6,
        24: 1380.8,
        25: 1408.1,
        26: 1435.6,
        27: 1463.2,
        28: 1490.9,
        29: 1518.7,
        30: 1546.7,
    }.get(temp_k - 273)


def kcl_cell_constant(conductance_measured, temperature, di_water_conductivity=DI_WATER_COND):
    cond = unit_conversion(conductance_measured, default_unit='uS')
    di_cond = unit_conversion(di_water_conductivity, default_unit='uS')
    temp = unit_conversion(temperature, default_unit='K')
    return (get_kcl_conductivity(temp) + di_cond) / cond


def get_cell_constant(raise_error=True):
    """
    Get cell constant from conductivity calibration data for the current day.

    Args:
        raise_error (bool, optional): Whether to raise an error if calibration data is not found. Defaults to True.

    Returns:
        tuple: Tuple containing lists of measured and true conductivity calibration values.
    """
    date = CALIB_DATE or datetime.now().strftime('%Y_%m_%d')
    if KCL_CALIB:
        query = ChemStandardsDB(standards_type="CACalib").coll.find({'$and': [
            {"date_updated": date},
            {"cell_constant": {"$exists": True}},
        ]}).distinct("cell_constant")
        print(f"KCl calibrations for {date}: {query}")
        if query:
            return "{}cm^-1".format(np.mean(query))
    else:
        query = list(ChemStandardsDB(standards_type="CACalib").coll.find({'$and': [
            {"date_updated": date},
            {"cond_measured": {"$exists": True}},
            {"cond_true": {"$exists": True}}
        ]}))
        ca_calib_measured = [c.get("cond_measured") for c in query]
        ca_calib_true = [c.get("cond_true") for c in query]
        if (ca_calib_measured and ca_calib_true) and raise_error:
            return np.polyfit(ca_calib_measured, ca_calib_true, 1)[0]
    raise ValueError(f"Conductivity calibration for today, {date}, does not exist. Please run a CA calibration "
                     f"workflow today before preceding with CA experiments.")


def print_prop(prop_dict):
    if prop_dict:
        return "{} {}".format(prop_dict.get("value", prop_dict), prop_dict.get("unit", ""))
    return ""


def all_cvs_data(multi_data, verbose=1):
    """
    Get data from all single CVs and calculate additional properties.

    Args:
        multi_data (list): List of dictionaries representing data from multiple CVs.
        verbose (int, optional): Verbosity level. Defaults to 1.

    Returns:
        list: List containing strings of data from all single CVs.
    """
    connector = {
        "A": "data.conditions.working_electrode_surface_area",
        "v": "data.conditions.scan_rate",
        "C": "data.conditions.redox_mol_concentration",
        "scan_data": "data.middle_sweep"
    }

    single_cvs = []
    for i, i_data in enumerate(multi_data):
        if verbose:
            print("Getting data for {} CV...".format(i + 1))
        single_cvs.append("\n---------- CV {} ----------".format(i + 1))
        [single_cvs.append("{}: \t{}".format(prop, i_data.get("data", {}).get(prop))) for prop in
         i_data.get("data", {}).keys()]
        for prop in ['e_half', 'middle_sweep', 'peak_splittings.py', 'peaks', 'reversibility']:
            try:
                value = getattr(CVDescriptorCalculator(connector=connector), prop)(i_data)
                single_cvs.append("{}: \t{}".format(prop, value))
            except:
                pass
    return single_cvs


def print_cv_analysis(multi_data, metadata, run_anodic=RUN_ANODIC, **kwargs):
    """
    Generate text analysis of CV data.

    Args:
        multi_data (list): List of dictionaries representing data from multiple CVs.
        metadata (dict): Metadata for the CV analysis.
        run_anodic (bool, optional): Whether to run anodic analysis. Defaults to RUN_ANODIC.

    Returns:
        str: Text analysis of the CV data.
    """
    e_halfs = metadata.get("oxidation_potential", [])

    out_txt = ""

    for i, e_half in enumerate(e_halfs):
        out_txt += "\n------------- Metadata for Oxidation {} -------------\n".format(i + 1)
        cond = e_half.get("conditions", {})
        redox_conc, se_conc = cond.get("redox_mol_concentration"), cond.get("electrolyte_concentration")
        out_txt += "Redox Mol Conc:  {}\n".format(print_prop(redox_conc))
        out_txt += "SE Conc:         {}\n".format(print_prop(se_conc))
        out_txt += "E1/2 at {}: \t{}\n".format(print_prop(cond.get("scan_rate", {})), print_prop(e_half))

        diff_coef = prop_by_order(metadata.get("diffusion_coefficient"), order=i + 1, notes="cathodic")
        out_txt += "\nCathodic Diffusion Coefficient (fitted): \t{}\n".format(print_prop(diff_coef))
        trans_rate = prop_by_order(metadata.get("charge_transfer_rate"), order=i + 1, notes="cathodic")
        out_txt += "Cathodic Charge Transfer Rate: \t\t\t{} \n".format(print_prop(trans_rate))

        if run_anodic:
            diff_coef = prop_by_order(metadata.get("diffusion_coefficient"), order=i + 1, notes="anodic")
            out_txt += "\nAnodic Diffusion Coefficient (fitted): \t{}\n".format(print_prop(diff_coef))
            trans_rate = prop_by_order(metadata.get("charge_transfer_rate"), order=i + 1, notes="anodic")
            out_txt += "Anodic Charge Transfer Rate: \t\t\t{}\n".format(print_prop(trans_rate))

    out_txt += "\n\n------------- Processing IDs -------------\n"
    for d in multi_data:
        out_txt += d.get("_id") + '\n'

    out_txt += "\n------------- Single CVs Analysis -------------\n"
    out_txt += '\n'.join(all_cvs_data(multi_data, **kwargs))
    out_txt += '\n'

    return str(out_txt)


def print_ca_analysis(multi_data, verbose=1):
    """
    Generate text analysis of CA data.

    Args:
        multi_data (list): List of dictionaries representing data from multiple CA experiments.
        verbose (int, optional): Verbosity level. Defaults to 1.

    Returns:
        str: Text analysis of the CA data.
    """
    out_txt = ""

    out_txt += "\n------------- Single CAs Analysis -------------\n"
    for i, i_data in enumerate(multi_data):
        if verbose:
            print("Getting data for {} CA...".format(i + 1))
        data_dict = i_data.get("data", {})
        cond = data_dict.get("conditions", {})
        out_txt += "\n---------- CA {} ----------\n".format(i + 1)
        redox_conc, se_conc = cond.get("redox_mol_concentration"), cond.get("electrolyte_concentration")
        out_txt += "Redox Mol Conc:  {}\n".format(print_prop(redox_conc))
        out_txt += "SE Conc:         {}\n".format(print_prop(se_conc))
        out_txt += "\nConductivity: \t{}".format(print_prop(data_dict.get("conductivity")))
        out_txt += "\nMeasured Conductance: \t{}".format(print_prop(data_dict.get("measured_conductance")))
        out_txt += "\nMeasured Resistance: \t{}".format(print_prop(data_dict.get("measured_resistance")))

    out_txt += "\n\n------------- Processing IDs -------------\n"
    for i_data in multi_data:
        out_txt += i_data.get("_id") + '\n'

    return str(out_txt)


def prop_by_order(prop_list, order=1, notes=None):
    """
    Retrieve a property from a list based on order and optional notes.

    Args:
        prop_list (list): List of property dictionaries.
        order (int, optional): Order of the property. Defaults to 1.
        notes (str, optional): Notes associated with the property. Defaults to None.

    Returns:
        dict: Property dictionary matching the specified order and notes.
    """
    result_prop = [p for p in prop_list if p.get("order") == order]
    if notes:
        result_prop = [p for p in result_prop if notes in p.get("notes")]
    if result_prop:
        if len(result_prop) > 1:
            warnings.warn("WARNING! More than one meta property has order {} and notes {}".format(order, notes))
        return result_prop[0]


def processing_test(cv_loc_dir="C:\\Users\\Lab\\D3talesRobotics\\data\\cv_exp01_robot_diffusion_2\\20230209\\",
                    submission_info: dict = None, metadata: dict = None):
    """
    FOR TESTING ONLY
    Perform processing of cyclic voltammetry (CV) data.

    Args:
        cv_loc_dir (str, optional): Directory path containing CV data files. Defaults to specified directory.
        submission_info (dict, optional): Information about the submission. Defaults to None.
        metadata (dict, optional): Metadata for the CV analysis. Defaults to None.
    """
    cv_locations = [os.path.join(cv_loc_dir, f) for f in os.listdir(cv_loc_dir) if f.endswith(".csv")]
    processed_data = []
    for cv_location in cv_locations:
        # Process data file
        print("Data File: ", cv_location)
        data = ProcessChiCV(cv_location, _id="test", submission_info=submission_info, metadata=metadata).data_dict
        processed_data.append(data)

        # Plot CV
        image_path = ".".join(cv_location.split(".")[:-1]) + "_plot.png"
        CVPlotter(connector={"scan_data": "data.middle_sweep"}).live_plot(data, fig_path=image_path,
                                                                          title=f"CV Plot for Test",
                                                                          xlabel=MULTI_PLOT_XLABEL,
                                                                          ylabel=MULTI_PLOT_YLABEL)
    # multi_path = os.path.join("\\".join(cv_locations[0].split("\\")[:-1]), "multi_cv_plot.png")
    # CVPlotter(connector={"scan_data": "data.middle_sweep", "variable_prop": "data.conditions.scan_rate.value"
    #                      }).live_plot_multi(processed_data, fig_path=multi_path, self_standard=True,
    #                                         title=f"Multi CV Plot for Test", xlabel=MULTI_PLOT_XLABEL,
    #                                         ylabel=MULTI_PLOT_YLABEL, legend_title=MULTI_PLOT_LEGEND)
    # from d3tales_api.Processors.back2front import CV2Front
    # metadata_dict = CV2Front(backend_data=processed_data, run_anodic=RUN_ANODIC, insert=False).meta_dict
    # p = print_cv_analysis(processed_data, metadata_dict)
    # print(p)


if __name__ == "__main__":
    meta_data = {"redox_mol_concentration": DEFAULT_CONCENTRATION, "temperature": DEFAULT_TEMPERATURE,
                 "working_electrode_radius": DEFAULT_WORKING_ELECTRODE_RADIUS}
    cv_dir = "C:\\Users\\Lab\\D3talesRobotics\\data\\8CVCollect_BenchmarkCV_test1_trial2\\20230525\\exp06_06QGQH"
    processing_test(cv_dir, metadata=meta_data)