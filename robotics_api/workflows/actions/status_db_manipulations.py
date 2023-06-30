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

        if self.id:
            self.experiment_name = self.get_prop("experiment_name")
            self.current_wflow_name = self.get_prop("current_wflow_name")
            self.home_location = self.id.split("_")
            self.home_snapshot = os.path.join(SNAPSHOT_DIR, "VialHome_{}_{:02}.json".format(self.home_location[0],
                                                                                            int(self.home_location[1])))

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
        if self.id:
            self.type = self.id.split("_")[0]
            self.current_wflow_name = self.get_prop("current_wflow_name")
            self.location_snapshot = os.path.join(SNAPSHOT_DIR, f"{self.id}.json")
            self.pre_location_snapshot = os.path.join(SNAPSHOT_DIR, f"pre_{self.id}.json")
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

    def get_all_available(self, name_str):
        """
        Get all available stations with name_str in name
        :param name_str: str, name string
        :return: prop
        """
        return self.coll.find({"_id": {"$regex": name_str}}).distinct("_id")

    def get_first_available(self, name_str, wait=True):
        """
        Get first available stations with name_str in name
        :param name_str: str, name string
        :param wait: bool, wait for available station if True
        :return: prop
        """
        available_stations = self.get_all_available(name_str)
        if not wait:
            return available_stations[0] if available_stations else None
        while not available_stations:
            available_stations = self.get_all_available(name_str)
            print(f"Waiting for available {name_str} station...")
            time.sleep(10)
        return available_stations[0]

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


def check_duplicates(test_list):
    if len(test_list) > len(set(test_list)):
        duplicates = {r for r in test_list if test_list.count(r) > 1}
        return ", ".join(duplicates)


def reset_reagent_db(reagents_list, current_wflow_name=""):
    # Check reagent locations 1-to-1 status
    reagent_locs = [r.get("location") for r in reagents_list]
    if check_duplicates(reagent_locs):
        raise ValueError("More than one reagent is assigned the same station: " + check_duplicates(reagent_locs))

    ReagentStatus().coll.delete_many({})
    for r in reagents_list:
        r.update({"current_wflow_name": current_wflow_name})
        ReagentStatus(instance=r)


def reset_station_db(current_wflow_name=""):
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


if __name__ == "__main__":
    wf_name = "8CVCollect_BenchmarkCV_test1_single_test"
    # reset_vial_db({'ae70a9cb-90f6-49ff-8b77-a192be06b703': 'A_02', 'cca7e96e-44e5-423f-9946-7fe951ab5170': 'A_03',
    #                'f3f68664-1c70-45b4-bf77-02a1364bfe89': 'A_04'})
    # VialStatus("A_02").update_location("potentiostat_01")
    # VialStatus("ae70a9cb-90f6-49ff-8b77-a192be06b703").update_capped(True)
    # StationStatus("potentiostat_01").update_available(True)
    # print(VialStatus("A_02", wflow_name=wflow_name).capped)
    # print(VialStatus(r_uuid="550c6dd3-af09-4351-ae1d-deea22ebc41f", wflow_name=wflow_name).capped)
    experiments = {
        "exp01": "A_04"
    }
    reagents = [
        {
            "_id": "550c6dd3-af09-4351-ae1d-deea22ebc41f",
            "description": "redox active molecule(s) (a.k.a. redox core)",
            "location": "experiment_vial",
            "name": "cyclopenta-1,3-diene;iron(2+)",
            "notes": "",
            "purity": "",
            "smiles": "[CH-]1C=CC=C1.[CH-]1C=CC=C1.[Fe+2]",
            "source": "sigma_aldrich",
            "type": "redox_molecule"
        },
        {
            "_id": "29690ed4-bf85-4945-9c2d-907eb942515d",
            "description": "solvent",
            "location": "solvent_01",
            "name": "Acetonitrile",
            "notes": "with 0.25M TEABF4 supporting electrolyte",
            "purity": "",
            "smiles": "CC#N",
            "source": "sigma_aldrich",
            "type": "solvent"
        }
    ]
    # reset_reagent_db(reagents, current_wflow_name=wf_name)
    # reset_vial_db(experiments, current_wflow_name=wf_name)
    # reset_station_db(current_wflow_name=wf_name)
