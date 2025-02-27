from robotics_api.actions.standard_actions import *
import matplotlib.pyplot as plt
from datetime import datetime
import pandas as pd


def check_usb():
    # list connection ports
    from serial.tools.list_ports import comports
    for port, desc, hw_id in sorted(comports()):
        print("{}: {} [{}]".format(port, desc, hw_id))


def vial_col_test(col, vial_id: str = None, ascending=True):
    # Move a vial to and from every vial home location in column 'col' in the vial holding grid station.
    vial = VialMove(_id=vial_id or f"{col}_04")
    vial.retrieve()
    for row in [1, 2, 3, 4][::1 if ascending else -1]:
        get_place_vial(VialMove(f"{col}_{row:02}"), action_type="place")
        get_place_vial(VialMove(f"{col}_{row:02}"), action_type="get")
    vial.place_home()


def reset_stations(end_home=False):
    # Rest all stations
    snapshot_move(snapshot_file=SNAPSHOT_HOME)
    for station in MEASUREMENT_STATIONS:
        if "potentiostat" in station and MOVE_ELEVATORS:
            PotentiostatStation(station).move_elevator(endpoint="down")
        if "pipette" in station and PIPETTE:
            PipetteStation(station).pipette(volume=0)
    if end_home:
        snapshot_move(target_position=10)
        snapshot_move(snapshot_file=SNAPSHOT_HOME)
        snapshot_move(snapshot_file=SNAPSHOT_END_HOME, target_position=10)


def flush_solvent(volume, vial_id="S_01", solv_id="solvent_01", go_home=True):
    # Flush 'volume' mL of solvent through solvent station with id 'solv_id' into vial with id 'vial_id'.
    snapshot_move(SNAPSHOT_HOME)
    vial = VialMove(_id=vial_id)
    solv_stat = LiquidStation(_id=solv_id)

    print("Actual Volume:  ", solv_stat._dispense_to_vial(vial, volume))

    if go_home:
        vial.leave_station(solv_stat)
        vial.place_home()


def density_test(volume, pipette_id="pipette_01", vial_id="S_01", return_mass=False):
    bal_station = BalanceStation(StationStatus().get_first_available("balance"))
    pipette_station = PipetteStation(pipette_id)
    vial = VialMove(_id=vial_id)

    # Get initial mass
    initial_mass = bal_station.existing_weight(vial)
    # Extract solution
    pipette_station.pipette(volume=volume, vial=vial)
    # Get final mass
    final_mass = bal_station.weigh(vial)

    # Calculate solution density
    extracted_mass = initial_mass - final_mass
    raw_density = f"{extracted_mass / volume} {MASS_UNIT}/{VOLUME_UNIT}"
    soln_density = "{:.3f}{}".format(unit_conversion(raw_density, default_unit=DENSITY_UNIT), DENSITY_UNIT)
    print(f"Raw Density: {extracted_mass:.3f} / {volume:.3f} {MASS_UNIT}/{VOLUME_UNIT}")
    print(f"--> SOLUTION DENSITY: {soln_density} {DENSITY_UNIT}")

    # Return extracted solution
    pipette_station.return_soln(vial=vial)

    return (extracted_mass / volume, extracted_mass) if return_mass else soln_density


def generate_calibration_curve(calibration_df: pd.DataFrame, plot: bool = False):
    """
    Generate a calibration curve from the calibration data and calculate correction factor.

    :param calibration_df: DataFrame containing calibration data
    :param plot: Whether to save create and save a calibration plot
    :return: Correction factor
    """
    expected_volumes = calibration_df["Expected Volume (L)"]
    extracted_volumes = calibration_df["Extracted Volume (L)"]

    correction_factor = (expected_volumes / extracted_volumes).mean()

    if plot:
        plt.figure(figsize=(8, 6))
        plt.scatter(expected_volumes, extracted_volumes, label="Calibration Data")
        plt.plot(expected_volumes * (1/correction_factor), expected_volumes, label="Best Fit", linestyle="--", color="red")
        plt.xlabel("Expected Volume (L)")
        plt.ylabel("Extracted Volume (L)")
        plt.title("Pipette Calibration Curve")
        plt.legend()

        plt.savefig(TEST_DATA_DIR / "calibration_curve.png")

    return correction_factor


def pipette_calibration(test_vols: list, expected_density: float,
                        trials_per_vol: int = 6, pipette_id="pipette_01", vial_id="S_01",
                        return_dataframe: bool = True):
    """
    Perform a calibration for a pipette and return a correction factor.
    Optionally, return all calibration data as a pandas DataFrame.

    :param test_vols: List of test volumes in L
    :param expected_density: Expected density in g/L
    :param trials_per_vol: Number of trials per volume
    :param pipette_id: Identifier for the pipette
    :param vial_id: Identifier for the vial
    :param return_dataframe: Whether to return calibration data as a DataFrame
    :return: Correction factor (float) or calibration data (DataFrame)
    """
    result_data = []
    for vol in test_vols:
        for _ in range(0, trials_per_vol):
            expected_mass = vol * expected_density
            soln_density, extracted_mass = density_test(vol, pipette_id=pipette_id, vial_id=vial_id, return_mass=True)
            print(f"\n\n\n DONE. Tried to extract {vol}. Expected mass was {expected_mass}, while extracted mass was "
                  f"{extracted_mass}. Calculated solution density was {soln_density}. \n\n\n")
            measurement_data = {
                "date_collected": datetime.now().strftime('%Y_%m_%d'),  # Day
                "Expected Volume (L)": vol,
                "Extracted Volume (L)": extracted_mass / expected_density,
                "Expected Mass (g)": expected_mass,
                "Extracted Mass (g)": extracted_mass,
                "Measured Density (g/L)": soln_density,
            }
            ChemStandardsDB(standards_type="PipetteCalib", instance=measurement_data)
            result_data.append(measurement_data)

    result_df = pd.DataFrame(result_data)
    result_df.to_csv(TEST_DATA_DIR / "pipette_calibration.csv")
    correction_factor = generate_calibration_curve(result_df, plot=True)
    print("CALCULATED CORRECTION FACTOR: ", correction_factor)

    return correction_factor, result_df if return_dataframe else correction_factor


if __name__ == "__main__":
    """
    The code below contains test functions for all stations. To implement a test, uncomment the line with 
    the test you'd like to implement. Then run this file: `python system_tests.py`. 
    """

    test_vial = VialMove(_id="A_01")
    cvUM_potent = CVPotentiostatStation("cvUM_potentiostat_A_01")
    cv_potent = CVPotentiostatStation("cv_potentiostat_B_01")
    ca_potent = CAPotentiostatStation("ca_potentiostat_C_01")
    test_bal = BalanceStation("balance_01")
    test_solv = LiquidStation("solvent_01")
    test_pip = PipetteStation("pipette_01")
    test_stir = StirStation("stir_01")

    # RESET TESTING
    # reset_test_db()
    # reset_stations(end_home=True)
    # snapshot_move(SNAPSHOT_HOME)
    # snapshot_move(SNAPSHOT_END_HOME)
    # snapshot_move(target_position=VIAL_GRIP_TARGET)

    # VIAL TESTING
    # test_bal.place_vial(test_vial)
    # test_vial.place_home()
    # vial_col_test("B", vial_id="A_02")
    # test_vial.retrieve()
    # get_place_vial(VialMove(_id="S_02"), action_type='get', raise_error=True)
    # test_vial.extract_soln(extracted_mass=0.506)

    # POTENTIOSTAT TESTING
    # ca_potent.place_vial(test_vial)
    # ca_potent.move_elevator(endpoint="down")
    # ca_potent.move_elevator(endpoint="up")
    # cvUM_potent.move_elevator(endpoint="up")
    # resistance = cv_potent.run_ircomp_test(TEST_DATA_DIR / "cv_testing/CV_ircomp_tempo_test03.csv")
    # cv_potent.run_cv(TEST_DATA_DIR / "cv_testing/CV_tempo_test03.csv", voltage_sequence="0, 0.7, 0V", scan_rate=0.1,
    #                  resistance=resistance)
    # cvUM_potent.run_cv(TEST_DATA_DIR/"cv_testing/CVUM_Fc_test01.csv", voltage_sequence="0, 0.5, -0.2V", scan_rate=0.1)
    # ca_potent.run_ca(os.path.join(TEST_DATA_DIR, "CA_Test_43.csv"))

    # SOLVENT TESTING
    # vol = test_solv.dispense_volume(test_vial, 0)
    # mass = test_solv.dispense_mass(test_vial, 5)
    # flush_solvent(8, vial_id="A_03", solv_id="solvent_02", go_home=True)
    # LiquidStation("solvent_02").dispense_only(1)

    # OTHER STATION TESTING
    # print(send_arduino_cmd("P1", "0", address=ARDUINO_PORT, return_txt=True))
    # print(TemperatureStation().temperature())
    # test_pip.pipette(volume=0.5, vial=test_vial)  # mL
    # test_pip.pipette(volume=0)  # mL
    # test_pip.pipette(volume=0.5)  # mL
    # print(density_test(0.5, pipette_id="pipette_01", vial_id="B_02"))
    # pipette_calibration([0.5], trials_per_vol=4, expected_density=0.786, vial_id="A_01")
    # test_stir.stir(stir_time=15)
    # print(test_bal.read_mass())
    # test_bal.weigh(test_vial)
    # test_vial.update_weight(14.0)
    # test_bal.existing_weight(test_vial)
    # check_usb()

    # joint_deltas = dict(j1=0, j6=7)
    # perturb_angular(reverse=False, wait_time=1, **joint_deltas)
    # perturb_angular(reverse=True, wait_time=1, **joint_deltas)
    # perturb_angular(reverse=True, wait_time=1, **joint_deltas)
    # perturb_angular(reverse=False, wait_time=1, **joint_deltas)
