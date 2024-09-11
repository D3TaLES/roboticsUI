from robotics_api.actions.standard_actions import *


def check_usb():
    # list connection ports
    from serial.tools.list_ports import comports
    for port, desc, hw_id in sorted(comports()):
        print("{}: {} [{}]".format(port, desc, hw_id))


def vial_col_test(col):
    # Move a vial to and from every vial home location in column 'col' in the vial holding grid station.
    snapshot_move(snapshot_file=SNAPSHOT_HOME)
    get_place_vial(VialMove(_id=col + "_04").home_snapshot, action_type='get', raise_error=True, raise_amount=0.1)
    get_place_vial(VialMove(_id=col + "_03").home_snapshot, action_type='place', raise_error=True, raise_amount=0.1)
    get_place_vial(VialMove(_id=col + "_03").home_snapshot, action_type='get', raise_error=True, raise_amount=0.1)
    get_place_vial(VialMove(_id=col + "_02").home_snapshot, action_type='place', raise_error=True, raise_amount=0.1)
    get_place_vial(VialMove(_id=col + "_02").home_snapshot, action_type='get', raise_error=True, raise_amount=0.1)
    get_place_vial(VialMove(_id=col + "_01").home_snapshot, action_type='place', raise_error=True, raise_amount=0.1)
    snapshot_move(snapshot_file=SNAPSHOT_HOME)


def reset_stations(end_home=False):
    # Rest all stations
    snapshot_move(snapshot_file=SNAPSHOT_HOME)
    if MOVE_ELEVATORS:
        PotentiostatStation("cv_potentiostat_A_01").move_elevator(endpoint="down")
        PotentiostatStation("ca_potentiostat_B_01").move_elevator(endpoint="down")
    if PIPETTE:
        PipetteStation("pipette_01").pipette(volume=0)
    if end_home:
        snapshot_move(target_position=10)
        snapshot_move(snapshot_file=SNAPSHOT_END_HOME, target_position=10)


def flush_solvent(volume, vial_id="S_01", solv_id="solvent_01", go_home=True):
    # Flush 'volume' mL of solvent through solvent station with id 'solv_id' into vial with id 'vial_id'.
    vial = VialMove(_id=vial_id)
    solv_stat = LiquidStation(_id=solv_id)

    print("Actual Volume:  ", solv_stat._dispense_to_vial(vial, volume))

    if go_home:
        vial.leave_station(solv_stat)
        vial.place_home()


if __name__ == "__main__":
    """
    The code below contains test functions for all stations. To implement a test, uncomment the line with 
    the test you'd like to implement. Then run this file: `python system_tests.py`. 
    """

    test_vial = VialMove(_id="B_01")
    test_potent = PotentiostatStation("ca_potentiostat_B_01")  # cv_potentiostat_A_01, ca_potentiostat_B_01
    test_bal = BalanceStation("balance_01")
    test_solv = LiquidStation("solvent_01")
    test_pip = PipetteStation("pipette_01")
    test_stir = StirStation("stir_01")
    d_path = os.path.join(TEST_DATA_DIR, "PotentiostatStation_Test.csv")

    # RESET TESTING
    # reset_test_db()
    # reset_stations(end_home=True)
    # snapshot_move(SNAPSHOT_HOME)
    # snapshot_move(SNAPSHOT_END_HOME)
    # snapshot_move(target_position=60)

    # VIAL TESTING
    # vial_col_test("B")
    # test_vial.place_home()
    # test_vial.retrieve()
    # get_place_vial(VialMove(_id="S_02").home_snapshot, action_type='get', raise_error=True, raise_amount=0.1)
    # test_vial.extract_soln(extracted_mass=0.506)

    # POTENTIOSTAT TESTING
    # test_potent.place_vial(test_vial)
    # test_potent.move_elevator(endpoint="down")
    # test_potent.move_elevator(endpoint="up")
    # test_potent.run_cv(d_path, voltage_sequence="0, 0.5, 0V", scan_rate=0.1)

    # SOLVENT TESTING
    # vol = test_solv.dispense(test_vial, 0)
    # mass = test_solv.dispense_mass(test_vial, 5)
    # flush_solvent(8, vial_id="C_04", solv_id="solvent_02", go_home=False)
    # LiquidStation("solvent_02").dispense_only(2)

    # OTHER STATION TESTING
    # print(send_arduino_cmd("P1", "0", address=ARDUINO_PORT, return_txt=True))
    # print(test_potent.get_temperature())
    # test_pip.pipette(volume=0.5, vial=test_vial)  # mL
    # test_pip.pipette(volume=0)  # mL
    # test_pip.pipette(volume=0.5)  # mL
    # test_stir.perform_stir(test_vial, stir_time=30)
    # test_bal.weigh(test_vial)
    # test_vial.update_weight(14.0)
    # test_bal.existing_weight(test_vial)
    # check_usb()
