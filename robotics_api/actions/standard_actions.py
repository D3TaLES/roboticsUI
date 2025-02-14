import math
import time

from d3tales_api.Processors.parser_echem import ProcessChiESI
from robotics_api.utils.kinova_move import *
from robotics_api.utils.base_utils import *
from robotics_api.actions.db_manipulations import *


def station_from_name(station_name):
    if "potentiostat" in station_name:
        station = PotentiostatStation(station_name)
    elif "balance" in station_name:
        station = BalanceStation(station_name)
    elif "liquid" in station_name:
        station = LiquidStation(station_name)
    elif "stir" in station_name:
        station = StirStation(station_name)
    elif "pipette" in station_name:
        station = PipetteStation(station_name)
    else:
        station = StationStatus(station_name)

    return station


class VialMove(VialStatus):
    """
    A class for managing the movement of a vial between various stations and locations using a robot arm.

    Attributes:
        raise_amount (float): The amount to raise the robot arm when moving the vial (default is 0.1).

    Methods:
        retrieve(raise_error=True, **move_kwargs): Retrieves the vial from its current location.
        go_to_snapshot(target_location, raise_error=True, **move_kwargs): Moves the vial to the specified snapshot location.
        place_snapshot(target_location, raise_error=True, **move_kwargs): Places the vial at the specified snapshot location.
        go_to_station(station, raise_error=True): Moves the vial to the specified station.
        leave_station(station, raise_error=True): Leaves the station by placing the vial back in the robot grip.
        place_home(**kwargs): Places the vial back to its home position.
        update_position(position): Updates the current position of the vial.
        robot_available(): Checks if the robot grip is available.
    """

    def __init__(self, _id=None, raise_amount: float = 0.12, **kwargs):
        """
        Initializes a VialMove instance with an optional vial ID and raise amount.

        Args:
            _id (str, optional): The ID of the vial or reagent. Must be provided to move a vial.
            raise_amount (float): Amount to raise the vial when moving (default is 0.1).
            **kwargs: Additional keyword arguments passed to the parent class.

        Raises:
            Exception: If no vial ID, reagent UUID, or experiment name is provided.
        """
        super().__init__(_id=_id, **kwargs)
        self.raise_amount = raise_amount
        if not self.id:
            raise Exception("To move a vial, a vial ID or reagent UUID or experiment name must be provided.")

    def retrieve(self, raise_error=True):
        """
        Retrieves the vial from its current location, managing robot availability and various stations.

        Args:
            raise_error (bool): Whether to raise an error if the retrieval fails (default is True).

        Returns:
            bool: True if the vial was successfully retrieved, False otherwise.

        Raises:
            Exception: If the vial cannot be retrieved and raise_error is True.
        """
        success = True
        if self.current_location == "robot_grip":
            if StationStatus("robot_grip").current_content == self.id:
                return True
            if raise_error:
                raise Exception(f"Vial {self.id} location is listed as robot_grip, but robot grip current_content is "
                                f"listed as {StationStatus('robot_grip').current_content}.")
        elif not self.robot_available():
            robot_content = StationStatus('robot_grip').current_content
            try:
                print(f"Trying to place {robot_content} home. ")
                VialMove(_id=robot_content).place_home()
            except Exception as e:
                if raise_error:
                    raise Exception(f"Robot cannot retrieve {self.id} vial because robot is unavailable. The robot "
                                    f"currently contains {robot_content}. Tried to Place {robot_content} home. "
                                    f"Failed with exception {e}")
        if self.robot_available():
            print("Robot is available")
            if self.current_location == "home":
                print("Retrieving vial from home...")
                success &= get_place_vial(self, action_type='get', raise_error=raise_error)
                # success &= snapshot_move(SNAPSHOT_HOME)
            else:
                station = station_from_name(self.current_location)
                print(f"Retrieving vial from station {station}...")
                success &= station._retrieve_vial(self)

            if success:
                self.update_position("robot_grip")

        if raise_error and not success:
            raise Exception(f"Vial {self.id} was not successfully retrieved. Vial {self.id} is located "
                            f"at {self.current_location}. ")
        return success

    def update_position(self, position, update_vial=True):
        """
        Updates the current position of the vial.

        Args:
            position (str): The new position of the vial.
            update_vial (bool): Update vial position if true.

        Returns:
            None
        """
        if update_vial:
            self.update_location(position)
        station = StationStatus(position)
        if station.exists:
            station.update_content(self.id)
            station.update_available(False)
            print(f"Warning! Station {position} not found! Station content not updated!")
        print(f"Successfully updated vial {self} to position {position}")

    def place_home(self, raise_error=True):
        """
        Places the vial back in its home position.

        Args:
            raise_error (bool): Whether to raise an error if the retrieval fails (default is True).

        Returns:
            bool: True if the vial was successfully placed at home, False otherwise.
        """
        success = self.retrieve(raise_error=True)

        if self.current_location == "home":
            print(f"Vial {self} is already at home.")
            return True
        success &= get_place_vial(self, action_type='place', raise_error=raise_error)
        if raise_error and not success:
            raise Exception(f"Vial {self} was not successfully moved home.")

        if success:
            self.update_position("home")
            StationStatus("robot_grip").empty()

        return success

    def place_station(self, station: StationStatus, raise_error=True):
        """
        Place the vial at the specified station.

        Args:
            station (StationStatus): The station to move the vial to.
            raise_error (bool): Whether to raise an error if the movement fails (default is True).

        Returns:
            bool: True if the vial was successfully moved, False otherwise.

        Raises:
            Exception: If the movement fails and raise_error is True.
        """
        success = self.retrieve(raise_error=True)

        if station.current_content == self.id:
            success &= True
        elif station.available:
            success &= get_place_vial(station, action_type='place', raise_error=raise_error)
        else:
            success &= False

        if raise_error and not success:
            raise Exception(f"Vial {self} was not successfully moved to {station}.")

        if success:
            self.update_position(station.id)
            StationStatus("robot_grip").empty()

        return success

    def go_to_station(self, station: StationStatus, raise_error=True, pre_position_only=False):
        """
        Moves the vial to the specified station.

        Args:
            station (StationStatus): The station to move the vial to.
            raise_error (bool): Whether to raise an error if the movement fails (default is True).
            pre_position_only (bool): Only move to "above" position if True (default is True).

        Returns:
            bool: True if the vial was successfully moved, False otherwise.

        Raises:
            Exception: If the movement fails and raise_error is True.
        """
        success = self.retrieve(raise_error=True)

        if station.current_content == self.id:
            success &= True
        elif station.available:
            print("LOCATION: ", station.pre_location_snapshot)
            success &= get_place_vial(station, action_type='place', release_vial=False, leave=False,
                                      raise_error=raise_error, pre_position_only=pre_position_only)
        else:
            success &= False

        if raise_error and not success:
            raise Exception(f"Vial {self} was not successfully moved to {station}.")

        self.update_position(station.id, update_vial=False) if success else None

        return success

    @staticmethod
    def leave_station(station: StationStatus, raise_error=True):
        """
        Leaves the station by placing the vial back in the robot grip.

        Args:
            station (StationStatus): The station from which to leave.
            raise_error (bool): Whether to raise an error if the leave action fails (default is True).

        Returns:
            bool: True if the vial was successfully placed back, False otherwise.
        """
        success = get_place_vial(station, go=False, release_vial=False, raise_error=raise_error)
        station.empty()
        return success

    @staticmethod
    def robot_available():
        """
        Checks if the robot grip is available.

        Returns:
            bool: True if the robot grip is available, False otherwise.
        """
        return StationStatus("robot_grip").available


class LiquidStation(StationStatus):
    """
    A class representing a solvent or liquid dispensing station.

    Attributes:
        raise_amount (float): The amount to raise or lower the vial when interacting with the station (default is -0.04).
        serial_name (str): The serial name of the station used for communication with hardware.

    Methods:
        solvent_id: Retrieves the solvent ID associated with the current station.
        place_vial(vial, raise_error=True): Places a vial at the liquid station.
        dispense_only(volume, perform_dispense=DISPENSE): Dispenses the given volume of liquid without vial interaction.
        _dispense_to_vial(vial, volume, raise_error=True): Handles vial placement and liquid dispensing.
        dispense_volume(vial, volume, raise_error=True): Dispenses a specified volume of liquid into a vial and updates the vial's reagent information.
        dispense_mass(vial, volume, raise_error=True): Dispenses a specified volume of liquid into a vial, weighing before and after to update the vial's mass.
    """

    def __init__(self, _id, raise_amount: float = -0.04, **kwargs):
        """
        Initializes a LiquidStation instance with an ID and raise amount.

        Args:
            _id (str): The ID of the liquid station.
            raise_amount (float): The amount to raise or lower the vial when interacting with the station (default is -0.04).
            **kwargs: Additional keyword arguments passed to the parent class.

        Raises:
            Exception: If no station ID is provided or if the station type is not 'solvent'.
        """
        super().__init__(_id=_id, pre_snapshot=False, **kwargs)
        if not self.id:
            raise Exception("To operate a solvent station, a solvent name must be provided.")
        if self.type != "solvent":
            raise Exception(f"Station {self.id} is not a liquid.")
        self.raise_amount = raise_amount
        self.serial_name = "L{:01d}".format(int(self.id.split("_")[-1]))

    @property
    def solvent_id(self):
        """
        Retrieves the solvent ID associated with the solvent located in the current liquid station.

        Returns:
            str: The solvent ID for the liquid at this station.

        Raises:
            ValueError: If no solvents or more than one solvent is found at this station.
        """
        all_solvents = list(MongoDatabase(database="robotics", collection_name='status_reagents').coll.find())
        potential_solvents = [s for s in all_solvents if s["location"] == self.id]
        if len(potential_solvents) > 1:
            raise ValueError(f"More than one reagents are listed as located at station {self}: {potential_solvents}.")
        elif len(potential_solvents) < 1:
            raise ValueError(f"No reagents are listed as located at station {self}.")
        return potential_solvents[0]["_id"]

    def place_vial(self, vial: VialMove, raise_error=True):
        """
        Places a vial at the liquid station.

        Args:
            vial (VialMove): The vial to be placed at the station.
            raise_error (bool): Whether to raise an error if the placement fails (default is True).

        Returns:
            bool: True if the vial was successfully placed, False otherwise.
        """
        return vial.go_to_station(self, raise_error=raise_error)

    def dispense_only(self, volume, perform_dispense=DISPENSE):
        """
        Dispenses the specified volume of liquid without interacting with a vial.

        Args:
            volume (float): The volume of liquid to dispense in mL.
            perform_dispense (bool): Whether to actually perform the dispense operation (default is DISPENSE).

        Returns:
            float: The volume of liquid dispensed.
        """
        arduino_vol = unit_conversion(volume, default_unit="mL") * 1000  # send volume in micro liter
        if perform_dispense:
            send_arduino_cmd(self.serial_name, arduino_vol)
        return volume

    def _dispense_to_vial(self, vial: VialMove, volume, raise_error=True):
        """
        Places the vial at the station, dispenses the liquid, and returns the volume dispensed.

        Args:
            vial (VialMove): The vial to be filled with liquid.
            volume (float): The volume of liquid to dispense.
            raise_error (bool): Whether to raise an error if the dispensing fails (default is True).

        Returns:
            float: The actual volume of liquid dispensed.
        """
        self.place_vial(vial, raise_error=raise_error)
        actual_volume = self.dispense_only(volume)
        vial.leave_station(self, raise_error=raise_error)
        return actual_volume

    def dispense_volume(self, vial: VialMove, volume, raise_error=True, addition_id=None):
        """
        Dispenses a specified volume of liquid into a vial and updates the vial's reagent information.

        Args:
            vial (VialMove): The vial to be filled with liquid.
            volume (float): The volume of liquid to dispense.
            raise_error (bool): Whether to raise an error if the dispensing fails (default is True).
            addition_id (str): A unique identifier for the reagent addition (Default is None)

        Returns:
            float: The actual volume of liquid dispensed.

        Raises:
            Exception: If the dispensing fails and raise_error is True.
        """
        actual_volume = self._dispense_to_vial(vial=vial, volume=volume, raise_error=raise_error)
        vial.add_reagent(self.solvent_id, amount=volume, default_unit=VOLUME_UNIT, addition_id=addition_id)
        return actual_volume

    def dispense_mass(self, vial: VialMove, volume, raise_error=True, addition_id=None):
        """
        Dispenses a specified volume of liquid into a vial and updates the vial's content with solvent mass using pre- and post-dispense weighing.

        Args:
            vial (VialMove): The vial to be filled with liquid.
            volume (float): The volume of liquid to dispense.
            raise_error (bool): Whether to raise an error if the dispensing fails (default is True).
            addition_id (str): A unique identifier for the reagent addition (Default is None)

        Returns:
            str: The mass of the liquid dispensed, in the default mass unit.

        Raises:
            Exception: If the dispensing fails or the weighing fails.
        """
        # Pre dispense weighing
        balance = BalanceStation(vial.current_location) if "balance" in vial.current_location else BalanceStation(
            StationStatus().get_first_available("balance"))
        pre_mass = balance.existing_weight(vial)

        # Dispense liquid
        self._dispense_to_vial(vial=vial, volume=volume, raise_error=raise_error)

        # Post dispense weighing
        post_mass = balance.weigh(vial)
        final_mass = post_mass - pre_mass

        # Update vial contents
        vial.add_reagent(self.solvent_id, amount=final_mass, default_unit=MASS_UNIT, addition_id=addition_id)
        vial.update_weight(post_mass)

        return f"{final_mass}{MASS_UNIT}"


class PipetteStation(StationStatus):
    """
    A class representing a pipette station.

    Attributes:
        raise_amount (float): The amount to raise or lower the vial when interacting with the station
            (default is -0.08).
        serial_name (str): The serial name of the station used for communication with hardware.

    Methods:
        place_vial(vial, raise_error=True): Places a vial at the pipette station.
        pipette(volume, vial=None, raise_error=True): Pipettes a specified volume of liquid, optionally into a vial.
    """

    def __init__(self, _id, raise_amount: float = -0.05, **kwargs):
        """
        Initializes a PipetteStation instance with an ID and raise amount.

        Args:
            _id (str): The ID of the pipette station.
            raise_amount (float): The amount to raise or lower the vial when interacting with the station (default is -0.08).
            **kwargs: Additional keyword arguments passed to the parent class.

        Raises:
            Exception: If no station ID is provided or if the station type is not 'pipette'.
        """
        super().__init__(_id=_id, **kwargs)
        if not self.id:
            raise Exception("To operate a pipette station, an id must be provided.")
        if self.type != "pipette":
            raise Exception(f"Station {self.id} is not a pipette.")
        self.raise_amount = raise_amount
        self.serial_name = "P{:01d}".format(int(self.id.split("_")[-1]))

    def place_vial(self, vial: VialMove, raise_error=True):
        """
        Places a vial at the pipette station.

        Args:
            vial (VialMove): The vial to be placed at the station.
            raise_error (bool): Whether to raise an error if the placement fails (default is True).

        Returns:
            bool: True if the vial was successfully placed, False otherwise.
        """
        return vial.go_to_station(self, raise_error=raise_error)

    def pipette(self, volume: float, vial: VialMove = None, raise_error=True):
        """
        Pipettes a specified volume of liquid, optionally into a vial.

        Args:
            volume (float): The volume of liquid to pipette in mL.
            vial (VialMove, optional): The vial to pipette into (default is None).
            raise_error (bool): Whether to raise an error if the pipetting operation fails (default is True).

        Returns:
            None

        Raises:
            Exception: If the pipetting operation fails and raise_error is True.
        """
        send_arduino_cmd(self.serial_name, 0)  # Return pipette to 0 before beginning opertation
        if vial:
            self.place_vial(vial, raise_error=raise_error)

        if PIPETTE:
            vol_mL = unit_conversion(volume, default_unit="mL")
            if vol_mL > MAX_PIPETTE_VOL:
                raise ValueError(f"Cannot pipette {vol_mL} mL because it is greater than the max "
                                 f"pipette volume {MAX_PIPETTE_VOL} mL.")
            arduino_vol = vol_mL * 1000  # send volume in micro liter
            send_arduino_cmd(self.serial_name, arduino_vol)

        if vial:
            vial.update_status(None, status_name="weight")
            self.leave_station(vial, raise_error=raise_error)

    def return_soln(self, vial: VialMove, raise_error=True):
        vial.go_to_station(self, raise_error=raise_error, pre_position_only=True)

        if PIPETTE:
            send_arduino_cmd(self.serial_name, 0)

        vial.update_status(None, status_name="weight")
        vial.leave_station(self, raise_error=raise_error)

    def discard_soln(self):
        send_arduino_cmd(self.serial_name, 0)

    def leave_station(self, vial: VialMove, raise_error=True):
        """
        Leaves pipette station so extracted solution can be discarded

        Args:
            vial (VialMove, optional): The vial to pipette into (default is None).
            raise_error (bool): Whether to raise an error if the operation fails (default is True).

        Raises:
            Exception: If the operation fails and raise_error is True.
        """
        vial.leave_station(self, raise_error=raise_error)
        joint_deltas = dict(j1=-5)
        if RUN_ROBOT:
            perturb_angular(reverse=False, **joint_deltas)


class BalanceStation(StationStatus):
    """
    A class representing a balance station.

    Attributes:
        raise_amount (float): The amount to raise or lower the vial when interacting with the station (default is 0.05).
        serial_name (str): The serial name of the balance used for communication with hardware.
        p_address (str): The port address of the balance for serial communication.

    Methods:
        place_vial(vial, raise_error=True, **move_kwargs): Places a vial on the balance station.
        existing_weight(vial, raise_error=True): Returns the current weight of a vial if available, or weighs the vial.
        weigh(vial, raise_error=True): Weighs a vial by taring the balance and placing the vial.
        read_mass(): Reads the mass from the balance via serial communication.
        tare(): Tares the balance.
        _send_command(write_txt=None, read_response=False): Sends a command to the balance and optionally reads the response.
    """

    def __init__(self, _id, raise_amount: float = 0.05, **kwargs):
        """
        Initializes a BalanceStation instance with an ID and raise amount.

        Args:
            _id (str): The ID of the balance station.
            raise_amount (float): The amount to raise or lower the vial when interacting with the station (default is 0.05).
            **kwargs: Additional keyword arguments passed to the parent class.

        Raises:
            Exception: If no station ID is provided or if the station type is not 'balance'.
        """
        super().__init__(_id=_id, pre_snapshot=False, **kwargs)
        if not self.id:
            raise Exception("To operate a balance station, a balance name must be provided.")
        if self.type != "balance":
            raise Exception(f"Station {self.id} is not a balance.")
        self.raise_amount = raise_amount
        self.serial_name = "B_{:02d}".format(int(self.id.split("_")[-1]))
        self.p_address = BALANCE_PORT

    def place_vial(self, vial: VialMove, raise_error=True, **move_kwargs):
        """
        Places a vial on the balance station.

        Args:
            vial (VialMove): The vial to be placed on the station.
            raise_error (bool): Whether to raise an error if the placement fails (default is True).
            **move_kwargs: Additional movement options.

        Returns:
            bool: True if the vial was successfully placed, False otherwise.
        """
        vial = vial if isinstance(vial, VialMove) else VialMove(vial)
        return vial.place_station(self, raise_error=raise_error)

    def _retrieve_vial(self, vial: VialMove):
        """
        Retrieves a vial from the balance station.

        Args:
            vial (VialMove): The vial to be retrieved.

        Returns:
            bool: True if the vial was successfully retrieved, False otherwise.

        Raises:
            Exception: If the vial is not located at the balance or if the robot is unavailable.
        """
        vial_id = vial if isinstance(vial, str) else vial.id
        if self.current_content != vial_id:
            raise Exception(f"Cannot retrieve vial {vial_id} from potentiostat {self.id}"
                            f"because vial {vial_id} is not located in this potentiostat")
        if not vial.robot_available():
            raise Exception(f"Cannot retrieve vial {vial_id} from potentiostat {self.id}"
                            f"because vial robot arm is not available.")
        success = get_place_vial(self, action_type='get')
        if success:
            vial.update_position("robot_grip")
            self.empty()

        return success

    def existing_weight(self, vial: VialMove, raise_error=True):
        """
        Returns the current weight of a vial if available, or weighs the vial.

        Args:
            vial (VialMove): The vial whose weight is to be measured.
            raise_error (bool): Whether to raise an error if weighing fails (default is True).

        Returns:
            float: The current weight of the vial.
        """
        if vial.current_weight:
            print("CURRENT WEIGHT: ", vial.current_weight)
            return vial.current_weight
        return self.weigh(vial, raise_error=raise_error)

    def weigh(self, vial: VialMove, raise_error=True, max_balance_reads=MAX_BALANCE_READS):
        """
        Weighs a vial by taring the balance and placing the vial on the station.

        Args:
            vial (VialMove): The vial to be weighed.
            raise_error (bool): Whether to raise an error if weighing fails (default is True).
            max_balance_reads (int): Maximum number of balance reads

        Returns:
            float: The weight of the vial.
        """
        if not WEIGH:
            return 0
        if self.current_content == vial.id:
            vial.retrieve()
        self.tare()
        self.place_vial(vial, raise_error=raise_error)
        mass = self.try_read_mass(max_balance_reads=max_balance_reads)
        time.sleep(1)
        self._retrieve_vial(vial)
        vial.update_status(mass, "weight")
        return mass

    def try_read_mass(self, max_balance_reads=MAX_BALANCE_READS):
        """
        Trt to read the mass from the balance via serial communication.

        Returns:
            float: The mass read from the balance.
        """
        balance_reads = 0
        while True:
            try:
                mass = self.read_mass()
                return mass
            except Exception as e:
                if balance_reads > max_balance_reads:
                    raise e
                print(f"WARNING. Balance reading {balance_reads} ended in error: ", e)
                balance_reads += 1
                time.sleep(10)

    def read_mass(self):
        """
        Reads the mass from the balance via serial communication.

        Returns:
            float: The mass read from the balance.

        Raises:
            SystemError: If the balance reading fails.
        """
        result_txt = self._send_command(write_txt="S\n", read_response=True)
        result_list = result_txt.split(" ")
        response_status = result_list[1]
        if response_status == "S":
            return float(result_list[-2])
        else:
            raise SystemError(f"Balance reading returned {result_txt}")

    def tare(self):
        """
        Tares the balance, resetting the weight measurement to zero.

        Returns:
            bool: True if the taring was successful.

        Raises:
            SystemError: If taring fails and the balance does not respond correctly.
        """
        while True:
            response = self._send_command(write_txt="T\n", read_response=True)
            if "S" in response:
                print(f"Balance {self} tared.")
                return True
            elif not WAIT_FOR_BALANCE:
                raise SystemError(f"Balance reading returned {response}")
            print(f"WARNING! Balance returned {response}! Trying again...")
            time.sleep(1)

    def _send_command(self, write_txt=None, read_response=False, max_balance_read_time=100):
        """
        Sends a command to the balance via serial communication and optionally reads the response.

        Args:
            write_txt (str, optional): The command to send to the balance.
            read_response (bool, optional): Whether to read and return the response from the balance (default is False).

        Returns:
            str: The response from the balance if read_response is True, otherwise None.

        Raises:
            Exception: If the balance is not connected or an error occurs during communication.
        """
        try:
            balance = serial.Serial(self.p_address, timeout=1)
        except IOError as e:
            raise Exception("Warning! Balance {} is not connected to {} because: {}".format(self, self.p_address, e))
        time.sleep(1)  # give the connection a second to settle
        if write_txt:
            balance.write(bytes(write_txt, encoding='utf-8'))
        if read_response:
            start_time = time.time()
            while True:
                data = balance.readline()
                elapsed_time = time.time() - start_time
                if elapsed_time > max_balance_read_time:
                    raise ValueError(f"Balance failed to respond after {max_balance_read_time} s.")
                print("waiting for {} balance results for {:.1f} seconds...".format(self, elapsed_time))
                if data:
                    result_txt = data.decode().strip()  # strip out the old lines
                    print("BALANCE RESULT: ", result_txt)
                    balance.close()
                    return result_txt
                time.sleep(1)


class TemperatureStation(StationStatus):
    """
    A class representing a temperature probe.

    Attributes:
        serial_name (str): The serial name of the balance used for communication with hardware.

    Methods:
        temperature(): Gets current temperature
    """

    def __init__(self, _id="temperature_01", **kwargs):
        """
        Initializes a TemperatureStation instance with an ID and raise amount.

        Args:
            _id (str): The ID of the balance station.
            **kwargs: Additional keyword arguments passed to the parent class.

        """
        super().__init__(_id=_id, pre_snapshot=False, **kwargs)
        if self.type != "temperature":
            raise Exception(f"Station {self.id} is not a temperature probe.")
        self.serial_name = self.serial_name = "T{:01d}".format(int(self.id.split("_")[-1]))

    def temperature(self):
        """
        Gets the temperature associated with this potentiostat station.

        Returns:
            dict: A dictionary with the temperature value in Kelvin and its unit.
        """

        arduino_result = send_arduino_cmd(self.serial_name, "", return_txt=True)
        if arduino_result:
            return {"value": sig_figs(float(arduino_result.split(":")[1].strip()) + 273.15, 5), "unit": "K"}


class StirStation(StationStatus):
    """
    A class representing a stir station for stirring vials.

    Attributes:
        raise_amount (float): The amount to raise or lower the vial when interacting with the station (default is 0.1).
        serial_name (str): The serial name of the stir station used for communication with hardware.

    Methods:
        place_vial(vial, raise_error=True): Places a vial on the stir station.
        stir(stir_time=None, stir_cmd="off", move_sleep=3): Operates the stirring mechanism.
        stir_vial(vial, stir_time=None, **kwargs): Places a vial, stirs it, and retrieves it from the station.
    """

    def __init__(self, _id, raise_amount: float = 0.1, **kwargs):
        """
        Initializes a StirStation instance with an ID and raise amount.

        Args:
            _id (str): The ID of the stir station.
            raise_amount (float): The amount to raise or lower the vial when interacting with the station
                (default is 0.1).
            **kwargs: Additional keyword arguments passed to the parent class.

        Raises:
            Exception: If no station ID is provided or if the station type is not 'stir'.
        """
        super().__init__(_id=_id, pre_snapshot=False, **kwargs)
        if not self.id:
            raise Exception("To operate the Stir-Heat station, a Stir-Heat name must be provided.")
        if self.type != "stir":
            raise Exception(f"Station {self.id} is not a potentiostat.")
        self.serial_name = "S{:1d}".format(int(self.id.split("_")[-1]))
        self.raise_amount = raise_amount

    def place_vial(self, vial: VialMove, raise_error=True):
        """
        Places a vial on the stir station.

        Args:
            vial (VialMove): The vial to be placed on the station.
            raise_error (bool): Whether to raise an error if the placement fails (default is True).

        Returns:
            bool: True if the vial was successfully placed, False otherwise.
        """
        return vial.go_to_station(self, raise_error=raise_error)

    def stir(self, stir_time=None, stir_cmd="off", move_sleep=1, joint_deltas=None):
        """
        Operates the stirring mechanism.

        Args:
            stir_time (int, optional): The time in seconds to stir. If None, defaults to implementing stir_cmd.
            stir_cmd (str, optional): Command for stir plate; only used if stir_time is None.
                                      Can be 'on'/'off' or 1/0 (default is 'off').
            move_sleep (float, optional): Time in seconds for robot to sleep between stirring moves (default is 3).
            joint_deltas (dict, optional): Key word arguments

        Returns:
            bool: True if the stir action was successful, False otherwise.

        Raises:
            TypeError: If an invalid stir command is provided.
        """
        if stir_time:
            seconds = unit_conversion(stir_time, default_unit='s') if STIR else 5
            success = False
            success &= send_arduino_cmd(self.serial_name, 1) if STIR else True
            print(f"Stirring for {seconds} seconds...")
            start_time = time.time()
            time.sleep(5)
            end_time = time.time()
            while (end_time - start_time) < seconds:
                # Move vial around stir plate center
                joint_deltas = joint_deltas or dict(j6=7)
                perturb_angular(reverse=False, wait_time=move_sleep, **joint_deltas)
                perturb_angular(reverse=True, wait_time=0, **joint_deltas)
                perturb_angular(reverse=True, wait_time=move_sleep, **joint_deltas)
                perturb_angular(reverse=False, wait_time=0, **joint_deltas)
                end_time = time.time()
            success &= send_arduino_cmd(self.serial_name, 0) if STIR else True
            return success

        # If stir_time not provided, default to implementing stir_cmd
        stir_cmd = 0 if stir_cmd == "off" or str(stir_cmd) == "0" else stir_cmd
        stir_cmd = 1 if stir_cmd == "on" or str(stir_cmd) == "1" else stir_cmd
        if stir_cmd not in [0, 1]:
            raise TypeError("Arg 'stir' must be 11 or 10, OR it must be 'up' or 'down'.")
        return send_arduino_cmd(self.serial_name, stir_cmd)

    def stir_vial(self, vial: VialMove, stir_time=None, **kwargs):
        """
        Places a vial on the station, stirs it, and retrieves it.

        Args:
            vial (VialMove): The vial to be stirred.
            stir_time (int, optional): The time in seconds to stir (default is None).
            **kwargs: Additional keyword arguments for vial placement and retrieval.

        Returns:
            bool: True if the vial was successfully stirred and retrieved, False otherwise.
        """
        success = vial.go_to_station(self, **kwargs)
        success &= self.stir(stir_time=stir_time)
        success &= vial.leave_station(self)
        return success


class PotentiostatStation(StationStatus):
    """
    A class representing a potentiostat station, used for performing electrochemical experiments.

    Attributes:
        current_experiment (str or None): The current experiment being performed at this station.
        pot_model (str): The model of the potentiostat.
        serial_name (str): The serial name for the elevator control.
        raise_amount (float): The amount to raise or lower the vial when interacting with the station.

    Methods:
        initiate_pot(vial): Prepares the potentiostat by raising the elevator if needed.
        end_pot(): Concludes the potentiostat operation by lowering the elevator.
        place_vial(vial, raise_error=True, **move_kwargs): Places a vial in the potentiostat.
        move_elevator(endpoint, raise_error=True): Moves the elevator to a specified position.
        get_temperature(): Retrieves the temperature associated with this station.
    """

    def __init__(self, _id, raise_amount: float = 0.028, **kwargs):
        """
        Initializes a PotentiostatStation instance with an ID and raise amount.

        Args:
            _id (str): The ID of the potentiostat station.
            raise_amount (float): The amount to raise or lower the vial when interacting with the station (default is 0.028).
            **kwargs: Additional keyword arguments passed to the parent class.

        Raises:
            Exception: If no station ID is provided or if the station is not a potentiostat.
        """
        super().__init__(_id=_id, **kwargs)
        self.current_experiment = self.get_prop("current_experiment") or None
        if not self.id:
            raise Exception("To operate a potentiostat, a potentiostat name must be provided.")
        if "potentiostat" not in self.id:
            raise Exception(f"Station {self.id} is not a potentiostat.")
        self.method, _, self.pot, self.p_channel = self.id.split("_")
        self.p_address = self.settings("address")
        self.p_exe_path = self.settings("exe_path")
        self.pot_model = self.p_exe_path.split("\\")[-1].split(".")[0]

        elevator = ELEVATOR_DICT.get(f"{self.pot}_{self.p_channel}")
        self.serial_name = f"E{elevator:1d}"
        self.raise_amount = raise_amount

        self.electrode_radius = self.settings("working_electrode_radius", raise_error=False)
        if self.electrode_radius:
            self.micro_electrode = True if self.electrode_radius <= ULTRA_MICRO_ELECTRODES_MAX_RADIUS else False

    @property
    def _settings_dict(self):
        settings_dict = POTENTIOSTAT_SETTINGS.get(self.id, {})
        if not settings_dict:
            raise KeyError(f"No settings set for potentiostat {self}. Please add settings for {self} in settings.py.")
        return settings_dict

    def settings(self, settings_name, raise_error=True):
        if self._settings_dict.get(settings_name) is not None:
            return self._settings_dict[settings_name]
        if raise_error:
            raise KeyError(f"Potentiostat {self} does not have default condition {settings_name}. You must either set "
                           f"condition {settings_name} in the ExpFlow robotic workflow or set a default condition in "
                           f"the settings file (settings.py).")

    def update_experiment(self, experiment: str or None):
        """
        Updates the current experiment for this potentiostat.

        Args:
            experiment (str or None): The current experiment.

        Returns:
            pymongo.results.UpdateResult: Result of the update operation.
        """
        return self.coll.update_one({"_id": self.id}, {"$set": {"current_experiment": experiment}})

    def initiate_pot(self, vial: VialMove or str = None):
        """
        Initiates the potentiostat by ensuring the vial is placed and the elevator is up.

        Args:
            vial (VialMove or str, optional): The vial to be used. If str, it's the ID of the vial.

        Raises:
            Exception: If the vial is not currently located in the potentiostat or does not match the current content.

        Returns:
            bool: True if the potentiostat is successfully initiated.
        """
        if vial:
            vial = VialMove(_id=vial) if isinstance(vial, str) else vial
            if not vial.current_location == self.id:
                raise Exception(f"Vial {vial.id} is not currently located in potentiostat {self.id}. "
                                f"It is located at {vial.current_location}")
            if not self.current_content == vial.id:
                raise Exception(f"Potentiostat {self.id} does not currently contain vial {vial.id}. "
                                f"It contains {self.current_content}")

        if self.state == "up":
            return True
        elif self.state == "down":
            if self.move_elevator(endpoint="up"):
                time.sleep(5)
                self.update_clean(False)
                return True

    def end_pot(self):
        """
        Ends the potentiostat operation by lowering the elevator.

        Returns:
            bool: True if the elevator is successfully lowered.
        """
        if self.state == "down":
            return True
        elif self.state == "up":
            if self.move_elevator(endpoint="down"):
                return True

    def _retrieve_vial(self, vial: VialMove):
        """
        Retrieves the vial from the potentiostat station.

        Args:
            vial (VialMove): The vial to retrieve.

        Raises:
            Exception: If the vial is not located in the potentiostat.

        Returns:
            bool: True if the vial is successfully retrieved.
        """
        vial_id = vial if isinstance(vial, str) else vial.id
        if self.current_content != vial_id:
            raise Exception(f"Cannot retrieve vial {vial_id} from potentiostat {self.id}"
                            f"because vial {vial_id} is not located in this potentiostat")
        success = self.end_pot()
        # success &= snapshot_move(SNAPSHOT_HOME)
        success &= get_place_vial(self, action_type='get')
        if success:
            vial.update_position("robot_grip")
            self.empty()
        # success &= snapshot_move(SNAPSHOT_HOME)
        return success

    def place_vial(self, vial: VialMove, raise_error=True, **move_kwargs):
        """
        Places a vial on the potentiostat station.

        Args:
            vial (VialMove): The vial to be placed.
            raise_error (bool, optional): Whether to raise an error if the placement fails (default is True).
            **move_kwargs: Additional arguments for vial placement.

        Raises:
            Exception: If the placement is unsuccessful and raise_error is True.

        Returns:
            bool: True if the vial is successfully placed, False otherwise.
        """
        vial = vial if isinstance(vial, VialMove) else VialMove(vial)
        if self.available:
            success = True
            if self.state == "up":
                success &= self.move_elevator(endpoint="down")
            success &= vial.retrieve(raise_error=True)
            # success &= snapshot_move(SNAPSHOT_HOME)
            success &= vial.place_station(self, raise_error=raise_error)

            return success

    def move_elevator(self, endpoint="down", raise_error=True):
        """
        Moves the potentiostat elevator to the specified endpoint.

        Args:
            endpoint (str or int, optional): The endpoint for the elevator; must be 1 (up) or 0 (down), or 'up'/'down' (default is 'down').
            raise_error (bool, optional): Whether to raise an error if the movement fails (default is True).

        Raises:
            TypeError: If an invalid endpoint is provided.
            Exception: If the elevator movement is not successful and raise_error is True.

        Returns:
            bool: True if the elevator movement is successful.
        """
        if MOVE_ELEVATORS:
            endpoint = 0 if endpoint == "down" or str(endpoint) == "0" else endpoint
            endpoint = 1 if endpoint == "up" or str(endpoint) == "1" else endpoint
            if endpoint not in [0, 1]:
                raise TypeError("Arg 'endpoint' must be 1 or 0, OR it must be 'up' or 'down'.")

            success = send_arduino_cmd(self.serial_name, endpoint)
        else:
            success = True
            warnings.warn("Elevators NOT moving because MOVE_ELEVATORS is False")

        if success:
            self.update_state("up") if endpoint == 1 else self.update_state("down")
        if (not success) and raise_error:
            raise Exception(f"Potentiostat {self} elevator not successfully raised")
        return success

    @staticmethod
    def generate_volts(voltage_sequence: str, volt_unit="V"):
        """
        Converts a sequence of voltages into the specified voltage unit.

        Args:
            voltage_sequence (str): A comma-separated string of voltages.
            volt_unit (str, optional): The desired voltage unit (default is "V").

        Returns:
            list: A list of voltages converted to the specified unit.
        """
        ureg = pint.UnitRegistry()
        voltages = voltage_sequence.split(',')
        voltage_units = ureg(voltages[-1]).units
        print(voltage_units)
        for i, v in enumerate(voltages):
            v_unit = "{}{}".format(v, voltage_units) if v.replace(".", "").replace("-", "").strip(
                " ").isnumeric() else v
            v_unit = ureg(v_unit)
            voltages[i] = v_unit.to(volt_unit).magnitude

        return voltages

    def generate_col_params(self, voltage_sequence: str, scan_rate: str, volt_unit="V", scan_unit="V/s"):
        """
        Generates collection parameters based on voltage sequence and scan rate.

        Args:
            voltage_sequence (str): A comma-separated string of voltages.
            scan_rate (str): The scan rate in string format.
            volt_unit (str, optional): The unit for voltages (default is "V").
            scan_unit (str, optional): The unit for scan rate (default is "V/s").

        Returns:
            list: A list of dictionaries containing voltage and scan rate parameters.
        """
        # Get voltages with appropriate units
        voltages = self.generate_volts(voltage_sequence=voltage_sequence, volt_unit=volt_unit)

        # Get scan rate with appropriate units
        ureg = pint.UnitRegistry()
        scan_rate = ureg(scan_rate).to(scan_unit).magnitude
        return [dict(voltage=v, scan_rate=scan_rate) for v in voltages]

    @staticmethod
    def check_data_path(datapath="", raise_error=True):
        if os.path.isfile(datapath):
            print(f"Datafile {datapath} found. ")
            return True
        else:
            if raise_error:
                raise FileNotFoundError(f"The datafile {datapath} was not found.")
            return False


class CVPotentiostatStation(PotentiostatStation):
    """
    A class representing a cyclic voltammetry (CV) potentiostat station, which runs CV experiments and
    iR compensation tests.

    Inherits from PotentiostatStation.

    Methods:
        run_cv(data_path, voltage_sequence=None, scan_rate=None, resistance=0, sample_interval=None, sens=None, **kwargs):
            Runs a CV experiment and saves the data.

        run_ircomp_test(data_path, e_ini=0, low_freq=None, high_freq=None, amplitude=None, sens=None):
            Runs an iR compensation test to determine the solution resistance.
    """

    def __init__(self, _id, raise_amount: float = 0.028, **kwargs):
        """
        Initializes a CVPotentiostatStation instance.

        Args:
            _id (str): The ID of the potentiostat station.
            raise_amount (float): The amount to raise or lower the vial when interacting with the station (default is 0.028).
            **kwargs: Additional keyword arguments passed to the parent class.

        Raises:
            Exception: If no station ID is provided or if the station is not a potentiostat.
        """
        super().__init__(_id=_id, raise_amount=raise_amount, **kwargs)

    def run_cv(self, data_path, voltage_sequence=None, scan_rate=None, resistance=0,
               sample_interval=None, sens=None, quiet_time=None, **kwargs):
        """
        Runs a cyclic voltammetry (CV) experiment with the potentiostat and saves the data.

        Args:
            data_path (str): The output data file path where results will be saved.
            voltage_sequence (str, optional): A comma-separated list of voltage points (e.g., '0.1,0.2,0.3').
            scan_rate (str, optional): The scan rate of the experiment (e.g., '0.1 V/s').
            resistance (float, optional): The solution resistance for iR compensation (default is 0, in Ohms).
            sample_interval (float, optional): The potential increment (default is CV_SAMPLE_INTERVAL, in Volts).
            sens (float, optional): The current sensitivity (default is CV_SENSITIVITY, in A/V).
            quiet_time (float, optional): Quiet time before run (in s)
            **kwargs: Additional arguments for running the experiment (e.g., potentiostat-specific parameters).

        Returns:
            bool: True if the experiment is successfully run.

        Raises:
            Exception: If the potentiostat model is unsupported for the CV experiment.
        """
        data_path = str(data_path) if data_path else None
        voltage_sequence = voltage_sequence or self.settings("voltage_sequence")
        sample_interval = unit_conversion(sample_interval or self.settings("sample_interval"), default_unit="V")
        quiet_time = unit_conversion(quiet_time or self.settings("quiet_time"), default_unit="s")
        sens = unit_conversion(sens or self.settings("sensitivity"), default_unit="A/V")
        if not RUN_POTENT:
            print(
                f"CV is NOT running because RUN_POTENT is set to False. Observing the {POT_DELAY * 2} second CV_DELAY.")
            write_test(data_path, test_type="cv")
            time.sleep(POT_DELAY * 5)
            return True
        # Benchmark CV for voltage range
        print(f"RUN CV WITH {voltage_sequence} VOLTAGES AT {scan_rate} SCAN RATE {sens} SENSITIVITY WITH {resistance} SOLN RESISTANCE")
        if "EC" in self.pot_model:
            warnings.warn("WARNING! Kbio potentiostat command is DEPRECATED! Use with caution! ")
            from robotics_api.utils._depriciated.potentiostat_kbio import CvExperiment, voltage_step
            # Set up CV parameters and KBIO CVExperiment object
            collect_params = self.generate_col_params(voltage_sequence, scan_rate)
            expt = CvExperiment([voltage_step(**p) for p in collect_params], record_every_de=sample_interval,
                                potentiostat_address=self.p_address, potentiostat_channel=int(self.p_channel),
                                exe_path=self.p_exe_path, run_iR=True, qt=quiet_time **kwargs)
            # Run CV and save data
            expt.run_experiment()
            time.sleep(self.settings("time_after"))
            expt.to_txt(data_path)
        elif "chi" in self.pot_model:
            if not resistance:
                warnings.warn("Warning. Resistance is 0 so IR compensation is not in use.")
            import hardpotato as hp
            # Set CV parameters
            out_folder = "/".join(data_path.split("\\")[:-1])
            f_name = data_path.split("\\")[-1].split(".")[0]
            volts = self.generate_volts(voltage_sequence=voltage_sequence, volt_unit="V")
            nSweeps = math.ceil((len(volts) - 2) / 2)
            print("N_SWEEPS: ", nSweeps)
            sr = unit_conversion(scan_rate or self.settings("scan_rate"), default_unit="V/s")

            # Install potentiostat and run CV
            hp.potentiostat.Setup(self.pot_model, self.p_exe_path, out_folder, port=self.p_address)
            soln_resistance = resistance * self.settings("rcomp_level") if self.settings("ir_comp") else None
            cv = hp.potentiostat.CV(Eini=volts[0], Ev1=max(volts), Ev2=min(volts), Efin=volts[-1], sr=sr,
                                    nSweeps=nSweeps, dE=sample_interval, sens=sens,
                                    fileName=f_name, header="CV " + f_name,
                                    resistance=soln_resistance)
            cv.run()
            time.sleep(self.settings("time_after"))
        else:
            raise Exception(f"CV not performed. No procedure for running a CV on {self.pot_model} model.")

        self.check_data_path(data_path)

        return True

    def run_ircomp_test(self, data_path, e_ini=0, low_freq=None, high_freq=None,
                        amplitude=None, sens=None, quiet_time=None):
        """
        Runs an iR compensation test to determine the solution resistance and saves the data.

        Args:
            data_path (str): The output data file path where results will be saved.
            e_ini (float, optional): The initial voltage (default is 0V).
            low_freq (float, optional): The low frequency for the test (default is INITIAL_FREQUENCY).
            high_freq (float, optional): The high frequency for the test (default is FINAL_FREQUENCY).
            amplitude (float, optional): The amplitude of the AC signal (default is AMPLITUDE, in Volts).
            sens (float, optional): The current sensitivity (default is CV_SENSITIVITY, in A/V).
            quiet_time (float, optional): Quiet time before run (in s)

        Returns:
            bool: True if the test is successfully run.

        Raises:
            Exception: If the potentiostat model is unsupported for the iR compensation test.
        """
        data_path = str(data_path) if data_path else None
        if not RUN_POTENT:
            print(f"iR Comp Test is NOT running because RUN_POTENT is set to False. "
                  f"Observing the {POT_DELAY} second CV_DELAY.")
            write_test(data_path, test_type="iRComp")
            time.sleep(POT_DELAY)
            return True

        if not self.settings("ir_comp"):
            print(f"iR Comp Test is NOT running because ir_comp in settings for {self} is False. "
                  f"Resistance of 0 is in use.")
            return 0

        # Benchmark CV for voltage range
        print(f"RUN IR COMP TEST")
        if "chi" in self.pot_model:
            import hardpotato as hp
            # Set CV parameters
            out_folder = "/".join(data_path.split("\\")[:-1])
            f_name = data_path.split("\\")[-1].split(".")[0]

            # Install potentiostat and run CV
            hp.potentiostat.Setup(self.pot_model, self.p_exe_path, out_folder, port=self.p_address)
            eis = hp.potentiostat.EIS(Eini=e_ini, low_freq=low_freq or self.settings("low_freq"),
                                      high_freq=high_freq or self.settings("high_freq"),
                                      qt=quiet_time or self.settings("quiet_time"),
                                      amplitude=amplitude or self.settings("amplitude"),
                                      sens=sens or self.settings("sensitivity"), fileName=f_name,
                                      header="iRComp " + f_name)
            eis.run()
            self.check_data_path(data_path)

            # Load recently acquired data
            data = ProcessChiESI(os.path.join(out_folder, f_name + ".txt"))
            time.sleep(self.settings("time_after"))

            print(data.resistance)
            return data.resistance


class CAPotentiostatStation(PotentiostatStation):
    """
    A class representing a chronoamperometry (CA) potentiostat station, which runs CA experiments.

    Inherits from PotentiostatStation.

    Methods:
        run_ca(data_path, voltage_sequence=None, si=None, pw=None, sens=None, steps=None,
               volt_min=MIN_CA_VOLT, volt_max=MAX_CA_VOLT):
            Runs a CA experiment and saves the data.
    """

    def __init__(self, _id, raise_amount: float = 0.028, **kwargs):
        """
        Initializes a CAPotentiostatStation instance.

        Args:
            _id (str): The ID of the potentiostat station.
            raise_amount (float): The amount to raise or lower the vial when interacting with the station (default is 0.028).
            **kwargs: Additional keyword arguments passed to the parent class.

        Raises:
            Exception: If no station ID is provided or if the station is not a potentiostat.
        """
        super().__init__(_id=_id, raise_amount=raise_amount, **kwargs)

    def run_ca(self, data_path, voltage_sequence=None, si=None, pw=None, sens=None,
               steps=None, volt_min=None, volt_max=None, quiet_time=None):
        """
        Runs a chronoamperometry (CA) experiment with the potentiostat and saves the data.

        Args:
            data_path (str): The output data file path where results will be saved.
            voltage_sequence (str, optional): A comma-separated list of voltage points (e.g., '0.1,0.2,0.3').
            si (float, optional): The sample interval in seconds (default is CA_SAMPLE_INTERVAL).
            pw (float, optional): The pulse width in seconds (default is CA_PULSE_WIDTH).
            sens (float, optional): The current sensitivity (default is CA_SENSITIVITY, in A/V).
            steps (float, optional): The number of steps to run in the experiment (default is CA_STEPS).
            volt_min (float, optional): The minimum voltage for the CA experiment (default is MIN_CA_VOLT).
            volt_max (float, optional): The maximum voltage for the CA experiment (default is MAX_CA_VOLT).
            quiet_time (float, optional): Quiet time before run (in s)

        Returns:
            bool: True if the experiment is successfully run.

        Raises:
            Exception: If the potentiostat model is unsupported for the CA experiment.
        """
        data_path = str(data_path) if data_path else None
        si = unit_conversion(si or self.settings("sample_interval"), default_unit="s")
        sens = unit_conversion(sens or self.settings("sensitivity"), default_unit="A/V")
        pw = unit_conversion(pw or self.settings("pulse_width"), default_unit="s")
        steps = steps or self.settings("steps")
        volt_min = volt_min or self.settings("volt_min")
        volt_max = volt_max or self.settings("volt_max")
        quiet_time = unit_conversion(quiet_time or self.settings("quiet_time"), default_unit="s")
        voltage_sequence = voltage_sequence or self.settings("voltage_sequence")

        if not RUN_POTENT:
            print(f"CA is NOT running because RUN_POTENT is set to False. Observing the {POT_DELAY} second delay.")
            write_test(data_path, test_type="ca")
            time.sleep(POT_DELAY)
            return True
        # Benchmark CV for voltage range
        print(f"RUN CA WITH {voltage_sequence} VOLTAGES.")
        if "chi" in self.pot_model:
            import hardpotato as hp
            # Set CV parameters
            f_name = data_path.split("\\")[-1].split(".")[0]
            out_folder = "/".join(data_path.split("\\")[:-1])
            volts = self.generate_volts(voltage_sequence=voltage_sequence, volt_unit="V")
            max_volt = min((max(volts), volt_max)) if volt_max else max(volts)
            min_volt = max((min(volts), volt_min)) if volt_min else min(volts)

            # Install potentiostat and run CA
            hp.potentiostat.Setup(self.pot_model, self.p_exe_path, out_folder, port=self.p_address)
            ca = hp.potentiostat.CA(Eini=0, Ev1=max_volt, Ev2=min_volt, dE=si, nSweeps=steps, pw=pw,
                                    sens=sens, fileName=f_name, header="CA " + f_name, qt=quiet_time)
            ca.run()
            time.sleep(self.settings("time_after"))
        else:
            raise Exception(f"CV not performed. No procedure for running a CV on {self.pot_model} model.")

        self.check_data_path(data_path)

        return True
