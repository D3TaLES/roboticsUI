import time
from rdkit.Chem import MolFromSmiles
from rdkit.Chem.rdMolDescriptors import CalcExactMolWt
from robotics_api.standard_variables import *
from d3tales_api.Calculators.utils import unit_conversion
from d3tales_api.D3database.d3database import RobotStatusDB


class VialStatus(RobotStatusDB):
    """
    Class for accessing the Robot Vial Status database
    Copyright 2021, University of Kentucky
    """

    def __init__(self, _id: str = None, exp_name: str = None, **kwargs):
        """
        Initiate class
        :param _id: str, _id
        :param exp_name: str, experiment name
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
        self.home_snapshot = os.path.join(
            SNAPSHOT_DIR, f"VialHome_{self.home_location[0]}_{self.home_location[1]:02}.json") if self.id else None

    @property
    def vial_content(self):
        return self.get_prop("vial_content") or []

    @property
    def capped(self):
        return self.get_prop("capped") or []

    @property
    def current_location(self):
        return self.get_prop("current_location") or []

    @property
    def location_history(self):
        return self.get_prop("location_history") or []

    @property
    def current_station(self):
        return StationStatus(_id=self.current_location)

    def update_capped(self, value: bool):
        """
        Get capped prop for instance with _id
        :param value: bool, capped prop
        :return: prop
        """
        return self.coll.update_one({"_id": self.id}, {"$set": {"capped": value}})

    def update_location(self, new_location):
        """
        Update status for a vial location or station vial
        :param new_location: str, new vial location
        """
        self.update_status(new_location, "location")

    def update_vial_content(self, new_content):
        """
        Update status for a vial location or station vial
        :param new_content: dict, new vial content
        """
        self.vial_content.append(new_content)
        self.insert(self.id, override_lists=True, instance={"vial_content": self.vial_content})

    def clear_vial_content(self):
        """
        Clear vial content
        """
        self.insert(self.id, override_lists=True, instance={"vial_content": []})

    def add_reagent(self, reagent, amount, default_unit):
        """
        Update status for a vial location or station vial
        :param reagent: str or obj, new reagent for vial content
        :param amount: str or float, amount for new reagent
        :param default_unit: str, default unit for reagent amount
        """
        reagent = ReagentStatus(_id=reagent) if isinstance(reagent, str) else reagent
        if not reagent:
            raise NameError("No reagent {} exists in the reagent database.".format(reagent))
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
        self.insert(self.id, override_lists=True, instance={
            "vial_content": other_reagents + new_vial_content
        })


class StationStatus(RobotStatusDB):
    """
    Class for accessing the Robot Vial Status database
    Copyright 2021, University of Kentucky
    """

    def __init__(self, _id: str = None, state_id: str = None, **kwargs):
        """
        Initiate class
        :param _id: str, _id
        """
        super().__init__(apparatus_type='stations', _id=_id, **kwargs)
        if state_id:
            self.id = self.coll.find_one({"state": state_id}).get("_id")
            if kwargs.get("wflow_name"):
                self.check_wflow_name()
        self.type = self.id.split("_")[0] if self.id else None
        self.current_wflow_name = self.get_prop("current_wflow_name") if self.id else None
        self.location_snapshot = os.path.join(SNAPSHOT_DIR, f"{self.id}.json") if self.id else None
        self.pre_location_snapshot = os.path.join(SNAPSHOT_DIR, f"pre_{self.id}.json") if self.id else None
        self.raise_amount = RAISE_AMOUNT

    @property
    def available(self):
        return self.get_prop("available")

    @property
    def state(self):
        return self.get_prop("state")

    @property
    def current_content(self):
        return self.get_prop("current_content")

    @property
    def content_history(self):
        return self.get_prop("content_history")

    def place_vial(self, vial, **kwargs):
        return

    def retrieve_vial(self, vial, **kwargs):
        return

    def get_all_available(self, name_str, exp_name=None):
        """
        Get all available stations with name_str in name
        :param name_str: str, name string
        :param exp_name: str, experiment name
        :return: prop
        """
        if exp_name:
            return self.coll.find({
                "_id": {"$regex": name_str},
                "available": True,
                "$or": [
                    {"current_experiment": exp_name},
                    {"current_experiment": None},
                ]
            }).distinct("_id")
        else:
            return self.coll.find({"_id": {"$regex": name_str}, "available": True}).distinct("_id")

    def get_first_available(self, name_str, wait=True, max_time=MAX_WAIT_TIME, **kwargs):
        """
        Get first available stations with name_str in name
        :param name_str: str, name string
        :param wait: bool, wait for available station if True
        :param max_time: int, maximum time to wait in seconds
        :return: prop
        """
        available_stations = self.get_all_available(name_str, **kwargs)
        if not wait:
            return available_stations[0] if available_stations else None
        total_time = 0
        while not available_stations:
            available_stations = self.get_all_available(name_str)
            print(f"Waiting for available {name_str} station...")
            if not self.wait_interval(total_time, 10, max_time=max_time):
                return None
        return available_stations[0]

    def wait_till_available(self, max_time=MAX_WAIT_TIME):
        """
        Wait until station is available
        :param max_time: int, maximum time to wait in seconds
        """
        total_time = 0
        while not self.available:
            print(f"Waiting for station {self} to become available...")
            if not self.wait_interval(total_time, 10, max_time=max_time):
                return False
        return True

    def wait_interval(self, total_time, wait_time, max_time=MAX_WAIT_TIME):
        time.sleep(wait_time)
        total_time += wait_time
        if max_time and (total_time >= max_time):
            print(f"Waited for {total_time} seconds and {self.type} station is still not available.")
            return False
        return True

    def update_available(self, value: bool):
        """
        Get available prop for instance with _id
        :param value: bool, available prop
        :return: prop
        """
        return self.coll.update_one({"_id": self.id}, {"$set": {"available": value}})

    def update_state(self, new_state):
        """
        Update status for a vial location or station vial
        :param new_state: str, new state for station
        """
        self.coll.update_one({"_id": self.id}, {"$set": {"state": new_state}})

    def update_content(self, new_content):
        """
        Update status for a vial location or station vial
        :param new_content: str, new vial in station
        """
        self.update_status(new_content, "content")

    def empty(self):
        """
        Empty station content and update availability
        """
        self.update_status("", "content")
        self.update_available(True)


class ReagentStatus(RobotStatusDB):
    """
    Class for accessing the Robot Reagent Status database
    Copyright 2021, University of Kentucky
    """

    def __init__(self, r_name=None, r_smiles=None, **kwargs):
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
        self.smiles = self.get_prop("smiles")
        self.source = self.get_prop("source")
        self.type = self.get_prop("type")
        self.current_wflow_name = self.get_prop("current_wflow_name")

    @property
    def molecular_weight(self):
        if not self.smiles:
            raise Exception(f"Cannot calculate molecular weight because no SMILES is associated with {self}.")
        rdkmol = MolFromSmiles(self.smiles)
        return CalcExactMolWt(rdkmol)


def check_duplicates(test_list, exemptions=None):
    for e in exemptions or [""]:
        test_list = [t for t in test_list if e not in t]
    if len(test_list) > len(set(test_list)):
        duplicates = {r for r in test_list if test_list.count(r) > 1}
        return ", ".join(duplicates)


def reset_reagent_db(reagents_list, current_wflow_name=""):
    # Check reagent locations 1-to-1 status
    reagent_locs = [r.get("location") for r in reagents_list]
    duplicate_reagents = check_duplicates(reagent_locs, exemptions=["experiment_vial", "solvent"])
    if duplicate_reagents:
        raise ValueError("More than one reagent is assigned the same station: " + duplicate_reagents)

    ReagentStatus().coll.delete_many({})
    for r in reagents_list:
        r.update({"current_wflow_name": current_wflow_name})
        ReagentStatus(instance=r)


def reset_station_db(current_wflow_name=""):
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


def reset_vial_db(experiment_locs, current_wflow_name="", capped_default=CAPPED_DEFAULT):
    # Check experiment locations 1-to-1 status
    experiment_locs.update(SOLVENT_VIALS)
    if check_duplicates(experiment_locs.values()):
        raise ValueError(
            "More than one experiment is assigned the same vial(s): " + check_duplicates(experiment_locs.values()))
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
            "capped": capped_default,
            "current_location": "home",
            "location_history": [],
        })


def reset_test_db():
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
        'exp02': 'A_02'
    }
    reset_reagent_db(reagents, current_wflow_name=wflow_name)
    reset_vial_db(experiments, current_wflow_name=wflow_name)
    reset_station_db(current_wflow_name=wflow_name)


if __name__ == "__main__":
    # reset_test_db()
    StationStatus().get_first_available("cv", exp_name="exp01")
