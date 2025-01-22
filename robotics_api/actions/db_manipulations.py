import time
import uuid
import warnings

from rdkit.Chem import MolFromSmiles
from rdkit.Chem.rdMolDescriptors import CalcExactMolWt
from robotics_api.settings import *
from robotics_api.utils.base_utils import unit_conversion
from robotics_api.utils.mongo_dbs import RobotStatusDB, MongoDatabase


class VialStatus(RobotStatusDB):
    """
    Class for accessing the Robot Vial Status database
    Copyright 2024, University of Kentucky
    """

    def __init__(self, _id: str = None, exp_name: str = None, **kwargs):
        """
        Initialize class instance.

        Args:
            _id (str, optional): The ID. Defaults to None.
            exp_name (str, optional): The experiment name. Defaults to None.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(apparatus_type='vials', _id=_id, **kwargs)
        if exp_name:
            print(exp_name)
            self.id = (self.coll.find_one({"experiment_name": exp_name}) or {}).get("_id")
            if not self.id:
                raise NameError(f"No vial is associated with experiment name {exp_name}.")
            if kwargs.get("wflow_name"):
                self.check_wflow_name()

        self.experiment_name = self.get_prop("experiment_name") if self.id else None
        self.current_wflow_name = self.get_prop("current_wflow_name") if self.id else None
        self.home_location = self.id.split("_") if self.id else None
        self.home_snapshot = os.path.join(SNAPSHOT_DIR, "VialHome_{}_{}.json".format(*self.home_location)) if self.id else None

    @property
    def vial_content(self):
        """
        Get the vial content.

        Returns:
            list: The vial content.
        """
        return self.get_prop("vial_content") or []

    @property
    def content_history(self):
        """
        Get the vial content.

        Returns:
            list: The vial content.
        """
        return self.get_prop("content_history") or []

    @property
    def current_weight(self):
        """
        Get the current weight.

        Returns:
            str: The current weight.
        """
        return self.get_prop("current_weight")

    @property
    def current_location(self):
        """
        Get the current location.

        Returns:
            str: The current location.
        """
        return self.get_prop("current_location") or []

    @property
    def location_history(self):
        """
        Get the location history.

        Returns:
            list: The location history.
        """
        return self.get_prop("location_history") or []

    @property
    def current_station(self):
        """
        Get the current station.

        Returns:
            StationStatus: The current station status.
        """
        return StationStatus(_id=self.current_location)

    def update_weight(self, new_weight: float):
        """
        Update the vial location or station vial status.

        Args:
            new_weight (str): weight
        """
        self.update_status(new_weight, "weight")

    def update_location(self, new_location: str):
        """
        Update the vial location or station vial status.

        Args:
            new_location (str): The new vial location.
        """
        self.update_status(new_location, "location")

    def update_vial_content(self, new_content):
        """
        Update the vial content.

        Args:
            new_content (dict): The new vial content.
        """
        self.vial_content.append(new_content)
        self.insert(self.id, override_lists=True, instance={"vial_content": self.vial_content})

    def clear_vial_content(self):
        """Clear the vial content."""
        self.insert(self.id, override_lists=True, instance={"vial_content": []})

    def add_reagent(self, reagent, amount, default_unit, addition_id=None):
        """
        Add a reagent to the vial content.

        Args:
            reagent (str or obj): The reagent ID or instance.
            amount (str or float or dict): The amount of the reagent.
            default_unit (str): The default unit for the reagent amount.
            addition_id (str): A unique identifier for the reagent addition (Default is None)

        Raises:
            NameError: If the reagent does not exist in the reagent database.
        """
        # Check if reagent exists
        reagent = ReagentStatus(_id=reagent) if isinstance(reagent, str) else reagent
        if not reagent:
            raise NameError("No reagent {} exists in the reagent database.".format(reagent))

        # Get new vial contents
        existing_reagent = [i for i in self.vial_content if i.get("reagent_uuid") == reagent.id]
        other_reagents = [i for i in self.vial_content if i.get("reagent_uuid") != reagent.id]
        if existing_reagent:
            old_amount = unit_conversion(existing_reagent[0].get("amount"), default_unit=default_unit)
            new_amount = old_amount + unit_conversion(amount, default_unit=default_unit)
        else:
            new_amount = unit_conversion(amount, default_unit=default_unit)
        new_vial_content = [{
            "reagent_uuid": reagent.id,
            "name": reagent.name,
            "amount": f"{new_amount}{default_unit}"
        }]

        # Update database
        current_addition = {
            "addition_id": addition_id,
            "reagent_uuid": reagent.id,
            "name": reagent.name,
            "amount": amount
        }
        history = self.get_prop("content_history") or []
        history.append(current_addition)
        self.insert(self.id, override_lists=True, instance={
            "vial_content": other_reagents + new_vial_content,
            "content_history": history
        })
        self.update_status(None, "weight")

    def check_addition_id(self, addition_id):
        """
        Check if this addition has already been made
        Args:
            addition_id (str): A unique identifier for the reagent addition (Default is None)

        Raises:
            boolean: If the reagent does not exist in the reagent database.
        """
        history = self.get_prop("content_history") or []
        existing_addition_ids = [a["addition_id"] for a in history]
        if addition_id in existing_addition_ids:
            return False
        return True

    def extract_soln(self, extracted_mass, default_mass_unit=MASS_UNIT):
        """
        Add a reagent to the vial content.

        Args:
            extracted_mass (str or obj): Mass extracted from solution
            default_mass_unit (str): The default mass unit for the reagent amount.

        Raises:
            NameError: If the reagent does not exist in the reagent database.
        """
        original_mass = sum([unit_conversion(r["amount"], default_unit=default_mass_unit) for r in self.vial_content])
        if original_mass > 0:
            extract_perc = extracted_mass / original_mass
            new_vial_content = []
            for r_dict in self.vial_content:
                reagent = ReagentStatus(_id=r_dict.get("reagent_uuid"))
                if not reagent:
                    raise NameError("No reagent {} exists in the reagent database.".format(reagent))
                old_amount = unit_conversion(r_dict.get("amount"), default_unit=default_mass_unit)
                new_amount = old_amount * (1-extract_perc)
                new_vial_content.append({
                    "reagent_uuid": reagent.id,
                    "name": reagent.name,
                    "amount": f"{new_amount}{default_mass_unit}"
                })
            self.insert(self.id, override_lists=True, instance={
                "vial_content": new_vial_content,
            })
            print(f"Successfully extracted {extract_perc*100:.2f}% of the mass from vial {self}.")


class StationStatus(RobotStatusDB):
    """
    Class for accessing the Robot Vial Status database
    Copyright 2024, University of Kentucky
    """

    def __init__(self, _id: str = None, state_id: str = None, pre_snapshot=True, **kwargs):
        """
        Initialize class instance.

        Args:
            _id (str, optional): The ID. Defaults to None.
            state_id (str, optional): The state ID. Defaults to None.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(apparatus_type='stations', _id=_id, **kwargs)
        if state_id:
            self.id = self.coll.find_one({"state": state_id}).get("_id")
            if kwargs.get("wflow_name"):
                self.check_wflow_name()
        self.type = self.id.split("_")[0] if self.id else None
        self.current_wflow_name = self.get_prop("current_wflow_name") if self.id else None
        self.location_snapshot = os.path.join(SNAPSHOT_DIR, f"{self.id}.json") if self.id else None
        self.pre_location_snapshot = os.path.join(SNAPSHOT_DIR, f"pre_{self.id}.json") if self.id and pre_snapshot else None
        self.raise_amount = 0

    @property
    def available(self):
        """
        Get the availability status.

        Returns:
            bool: The availability status.
        """
        return self.get_prop("available")

    @property
    def state(self):
        """
        Get the state.

        Returns:
            str: The state.
        """
        return self.get_prop("state")

    @property
    def current_content(self):
        """
        Get the current content.

        Returns:
            str: The current content.
        """
        return self.get_prop("current_content")

    @property
    def content_history(self):
        """
        Get the content history.

        Returns:
            list: The content history.
        """
        return self.get_prop("content_history")

    def place_vial(self, vial, **kwargs):
        """
        Placeholder method for placing a vial.

        Args:
            vial: The vial to place.
            **kwargs: Additional keyword arguments.
        """
        raise NotImplementedError

    def _retrieve_vial(self, vial):
        """
        Placeholder method for retrieving a vial.

        Args:
            vial: The vial to retrieve.
        """
        raise NotImplementedError

    def get_all_available(self, name_str: str, exp_name=None):
        """
        Get all available stations with a specified name string.

        Args:
            name_str (str): The name string to search for.
            exp_name (str, optional): The experiment name. Defaults to None.

        Returns:
            list: List of available station IDs.
        """
        if exp_name:
            return self.coll.find({
                "_id": {"$regex": name_str},
                "available": True,
                # "$or": [
                #     {"current_experiment": exp_name},
                #     {"current_experiment": None},
                # ]
            }).distinct("_id")
        else:
            return self.coll.find({"_id": {"$regex": name_str}, "available": True}).distinct("_id")

    def get_first_available(self, name_str, wait=True, max_time=MAX_DB_WAIT_TIME, wait_interval=2, **kwargs):
        """
        Get the first available station with a specified name string.

        Args:
            name_str (str): The name string to search for.
            wait (bool, optional): Whether to wait for an available station. Defaults to True.
            max_time (int, optional): The maximum time to wait in seconds. Defaults to MAX_DB_WAIT_TIME.
            wait_interval (int, optional): The interval between wait checks in seconds. Defaults to 2.
            **kwargs: Additional keyword arguments.

        Returns:
            str: The ID of the first available station.
        """
        available_stations = self.get_all_available(name_str, **kwargs)
        if not wait:
            return available_stations[0] if available_stations else None
        total_time = 0
        while not available_stations:
            print(f"Waited for {total_time} seconds, and a {name_str} station is still not available.")
            time.sleep(wait_interval)
            total_time += wait_interval
            if max_time and (total_time >= max_time):
                return None
            available_stations = self.get_all_available(name_str)
        return available_stations[0]

    def wait_till_available(self, max_time=MAX_DB_WAIT_TIME, wait_interval=2):
        """
        Wait until the station is available.

        Args:
            max_time (int, optional): The maximum time to wait in seconds. Defaults to MAX_DB_WAIT_TIME.
            wait_interval (int, optional): The interval between wait checks in seconds. Defaults to 2.

        Returns:
            bool: True if the station becomes available, False otherwise.
        """
        total_time = 0
        while not self.available:
            print(f"Waited for {total_time} seconds and {self} station is still not available.")
            time.sleep(wait_interval)
            total_time += wait_interval
            if max_time and (total_time >= max_time):
                print(f"{self} is not available. ")
                return False
        print(f"{self} is available!")
        return True

    def update_available(self, value: bool):
        """
        Update the availability status.

        Args:
            value (bool): The new availability status.

        Returns:
            prop: The updated availability status.
        """
        return self.coll.update_one({"_id": self.id}, {"$set": {"available": value}})

    def update_state(self, new_state: str):
        """
        Update the station state.

        Args:
            new_state (str): The new state for the station.
        """
        self.coll.update_one({"_id": self.id}, {"$set": {"state": new_state}})

    def update_content(self, new_content):
        """
        Update the station content.

        Args:
            new_content: The new content in the station.
        """
        self.update_status(new_content, "content")

    def empty(self):
        """Empty the station content and update availability."""
        self.update_status("", "content")
        self.update_available(True)
        print(f"Successfully emptied station {self}")


class ReagentStatus(RobotStatusDB):
    """
    Class for accessing the Robot Reagent Status database
    Copyright 2024, University of Kentucky
    """

    def __init__(self, r_name=None, r_smiles=None, **kwargs):
        """
        Initialize class instance.

        Args:
            r_name (str, optional): The name of the reagent. Defaults to None.
            r_smiles (str, optional): The SMILES representation of the reagent. Defaults to None.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(apparatus_type='reagents', **kwargs)
        if r_name:
            self.id = (self.coll.find_one({"name": r_name}) or {}).get("_id")
            if not self.id:
                raise NameError(f"No reagent is associated with name {r_name}.")
        elif r_smiles:
            self.id = (self.coll.find_one({"smiles": r_smiles}) or {}).get("_id")
            if not self.id:
                raise NameError(f"No reagent is associated with smiles {r_smiles}.")
        if self.id and kwargs.get("wflow_name"):
            self.check_wflow_name()

        self.description = self.get_prop("description")
        self.location = self.get_prop("location")
        self.name = self.get_prop("name")
        self.notes = self.get_prop("notes")
        self.purity = self.get_prop("purity")
        self.formal_potential = self.get_prop("formal_potential")
        self.density = self.get_prop("density")
        self.smiles = self.get_prop("smiles")
        self.source = self.get_prop("source")
        self.type = self.get_prop("type")
        self.current_wflow_name = self.get_prop("current_wflow_name")

    @property
    def molecular_weight(self):
        """
        Calculate the molecular weight of the reagent.

        Returns:
            float: The molecular weight of the reagent.
        """
        if not self.smiles:
            raise Exception(f"Cannot calculate molecular weight because no SMILES is associated with {self}.")
        rdkmol = MolFromSmiles(self.smiles)
        return CalcExactMolWt(rdkmol)


class ChemStandardsDB(MongoDatabase):
    """
    Class for accessing the Chem Standards database for robotic fireworks
    Copyright 2024, University of Kentucky
    """

    def __init__(self, standards_type: str, _id: str = None, instance: dict = None, override_lists: bool = True):
        """
        Initialize class instance.

        Args:
            standards_type (str): The type of chemistry standard.
            _id (str, optional): The ID of the standard. Defaults to None.
            instance (dict, optional): The instance to insert or validate. Defaults to None.
            override_lists (bool, optional): Whether to override existing lists. Defaults to True.
        """
        self.db_name = 'standards_' + standards_type
        super().__init__(database="robotics", collection_name=self.db_name, instance=instance, validate_schema=False)
        self.id = _id or self.instance.get("_id", str(uuid.uuid4()))
        if instance:
            instance["_id"] = self.id
            self.insert(self.id, override_lists=override_lists)

    def __str__(self):
        """
        Return a string representation of the ChemStandardsDB instance.

        Returns:
            str: A string representation of the instance.
        """
        return self.db_name

    @property
    def exists(self):
        """
        Check if the standard exists in the database.

        Returns:
            bool: True if the standard exists, False otherwise.
        """
        return True if self.coll.find_one({"_id": self.id}) else False

    def get_prop(self, prop: str):
        """
        Get a property of the standard from the database.

        Args:
            prop (str): The property to retrieve.

        Returns:
            Any: The value of the property.
        """
        return (self.coll.find_one({"_id": self.id}) or {}).get(prop)


def check_duplicates(test_list, exemptions=None):
    """
    Check for duplicates in a list, excluding specified exemptions.

    Args:
        test_list (list): The list to check for duplicates.
        exemptions (list, optional): Items to exclude from duplicate checking. Defaults to None.

    Returns:
        str: A comma-separated string of duplicate items, or None if no duplicates are found.
    """
    for e in exemptions or [""]:
        test_list = [t for t in test_list if e not in t]
    if len(test_list) > len(set(test_list)):
        duplicates = {r for r in test_list if test_list.count(r) > 1}
        return ", ".join(duplicates)


def reset_reagent_db(reagents_list, current_wflow_name="", solvent_densities=SOLVENT_DENSITIES, potentials_dict=FORMAL_POTENTIALS):
    """
    Reset the reagent database with the provided list of reagents.

    Args:
        reagents_list (list): List of dictionaries representing reagents.
        current_wflow_name (str, optional): Name of the current workflow. Defaults to "".
        solvent_densities (dict, optional): Dictionary with solvent SMILES and densities
    """
    # Check reagent locations 1-to-1 status
    reagent_locs = [r.get("location") for r in reagents_list]
    duplicate_reagents = check_duplicates(reagent_locs, exemptions=["experiment_vial", "solvent"])
    if duplicate_reagents:
        raise ValueError("More than one reagent is assigned the same station: " + duplicate_reagents)

    ReagentStatus().coll.delete_many({})
    for r in reagents_list:
        smiles = r.get("smiles", "")
        r.update({"current_wflow_name": current_wflow_name,
                  "density": unit_conversion(solvent_densities.get(smiles), default_unit=DENSITY_UNIT),
                  "formal_potential": unit_conversion(potentials_dict.get(smiles), default_unit=POTENTIAL_UNIT)})
        ReagentStatus(instance=r)


def reset_station_db(current_wflow_name=""):
    """
    Reset the station database.

    Args:
        current_wflow_name (str, optional): Name of the current workflow. Defaults to "".
    """
    StationStatus().coll.delete_many({})
    for station in STATIONS:
        state = "down" if "potentiostat" in station else ""
        StationStatus(instance={
            "_id": station,
            "current_wflow_name": current_wflow_name,
            "available": True,
            "state": state,
            "current_content": "",
            "content_history": [],
        })


def reset_vial_db(experiment_locs: dict, current_wflow_name=""):
    """
    Reset the vial database with the provided experiment locations.

    Args:
        experiment_locs (dict): Dictionary mapping vial IDs to experiment names.
        current_wflow_name (str, optional): Name of the current workflow. Defaults to "".
    """
    # Check experiment locations 1-to-1 status
    experiment_locs.update(RINSE_VIALS)
    if check_duplicates(list(experiment_locs.values())):
        raise ValueError(
            "More than one experiment is assigned same vial(s): " + check_duplicates(list(experiment_locs.values())))
    exp_dict = {v: r for r, v in experiment_locs.items()}
    print("EXPERIMENT DICT: ", exp_dict)

    # Set up vial locations DB
    VialStatus().coll.delete_many({})
    for vial in VIALS:
        VialStatus(instance={
            "_id": vial,
            "current_wflow_name": current_wflow_name,
            "experiment_name": exp_dict.get(vial, ""),
            "vial_content": [],
            "current_weight": None,
            "current_location": "home",
            "weight_history": [],
            "location_history": [],
        })


def reset_test_db():
    """
    Reset the test database with default configurations.
    """
    wflow_name = "test_workflow"
    reagents = [
        {
            '_id': '3d5f63fd-a6b0-4cc0-922c-befbeeb3577a',
            'name': '10-[2-(2-methoxyethoxy)ethyl]phenothiazine',
            'smiles': 'COCCOCCN1C2=C(C=CC=C2)SC3=C1C=CC=C3',
            'source': 'sigma_aldrich', 'type': 'redox_molecule',
            'description': 'redox active molecule(s) (a.k.a. redox core)',
            'notes': '', 'purity': '', 'location': 'experiment_vial'},
        {
            '_id': '29690ed4-bf85-4945-9c2d-907eb942515d',
            'name': 'Acetonitrile',
            'smiles': 'CC#N',
            'source': 'sigma_aldrich',
            'type': 'solvent',
            'description': 'solvent',
            'notes': 'with 0.25M TEABF4 supporting electrolyte',
            'purity': '',
            'location': 'solvent_01'
        },
        {
            '_id': 'c1727c49-8cb3-4b83-a672-7b218a51d845',
            'name': '1,4-ditert-butyl-2,5-bis(2-methoxyethoxy)benzene',
            'smiles': 'CC(C)(C)C1=C(OCCOC)C=C(C(C)(C)C)C(OCCOC)=C1',
            'source': 'sigma_aldrich',
            'type': 'redox_molecule',
            'description': 'redox active molecule(s) (a.k.a. redox core)',
            'notes': '',
            'purity': '',
            'location': 'experiment_vial'
        },
        {
            '_id': '29690ed4-bf85-4945-9c2d-907eb942515d',
            'name': 'Acetonitrile',
            'smiles': 'CC#N',
            'source': 'sigma_aldrich',
            'type': 'solvent',
            'description': 'solvent',
            'notes': 'with 0.25M TEABF4 supporting electrolyte',
            'purity': '',
            'location': 'solvent_01'
        }
    ]

    experiments = {
        'exp01': 'A_01',
        'exp02': 'A_02',
        'exp03': 'A_03',
        'exp04': 'A_04',
    }
    reset_reagent_db(reagents, current_wflow_name=wflow_name)
    reset_vial_db(experiments, current_wflow_name=wflow_name)
    reset_station_db(current_wflow_name=wflow_name)


def setup_status_db(wflow_name, experiments, reagents):
    reset_reagent_db(reagents, current_wflow_name=wflow_name)
    reset_vial_db(experiments, current_wflow_name=wflow_name)
    reset_station_db(current_wflow_name=wflow_name)


if __name__ == "__main__":
    # reset_test_db()
    # StationStatus().get_first_available("cv", exp_name="exp01")
    # setup_formal_potentials()
    # test_calib()

    setup_status_db("Cond3_all_TEMPO_",
                    {
                        "exp01": "A_01",
                        "exp02": "A_02"
                    },
                    [{
                        "_id": "29690ed4-bf85-4945-9c2d-907eb942515d",
                        "description": "solvent",
                        "location": "solvent_01",
                        "name": "Acetonitrile",
                        "notes": "",
                        "purity": "",
                        "smiles": "CC#N",
                        "source": "sigma_aldrich",
                        "type": "solvent"
                    }, {
                        "_id": "f12e7ae7-e893-44b9-8fee-51787f23fbdb",
                        "description": "supporting electrolyte",
                        "location": "experiment_vial",
                        "name": "TBAPF6",
                        "notes": "",
                        "purity": "",
                        "smiles": " F[P-](F)(F)(F)(F)F.CCCC[N+](CCCC)(CCCC)CCCC",
                        "source": "sigma_aldrich",
                        "type": "electrolyte"
                    }, {
                        "_id": "330391e4-855b-4a1d-851e-59445c65fad0",
                        "description": "redox active molecule(s) (a.k.a. redox core)",
                        "location": "experiment_vial",
                        "name": "TEMPO",
                        "notes": "",
                        "purity": "",
                        "smiles": "CC1(C)CCCC(C)(C)N1[O]",
                        "source": "uk_lab",
                        "type": "redox_molecule"
                    }, {
                        "_id": "29690ed4-bf85-4945-9c2d-907eb942515d",
                        "description": "solvent",
                        "location": "solvent_01",
                        "name": "Acetonitrile",
                        "notes": "",
                        "purity": "",
                        "smiles": "CC#N",
                        "source": "sigma_aldrich",
                        "type": "solvent"
                    }, {
                        "_id": "f12e7ae7-e893-44b9-8fee-51787f23fbdb",
                        "description": "supporting electrolyte",
                        "location": "experiment_vial",
                        "name": "TBAPF6",
                        "notes": "",
                        "purity": "",
                        "smiles": " F[P-](F)(F)(F)(F)F.CCCC[N+](CCCC)(CCCC)CCCC",
                        "source": "sigma_aldrich",
                        "type": "electrolyte"
                    }, {
                        "_id": "330391e4-855b-4a1d-851e-59445c65fad0",
                        "description": "redox active molecule(s) (a.k.a. redox core)",
                        "location": "experiment_vial",
                        "name": "TEMPO",
                        "notes": "",
                        "purity": "",
                        "smiles": "CC1(C)CCCC(C)(C)N1[O]",
                        "source": "uk_lab",
                        "type": "redox_molecule"
                    }]
                    )
