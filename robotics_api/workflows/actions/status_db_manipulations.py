from robotics_api.standard_variables import *
from d3tales_api.D3database.d3database import RobotStatusDB


class VialStatus(RobotStatusDB):
    """
    Class for accessing the Robot Vial Status database
    Copyright 2021, University of Kentucky
    """

    def __init__(self, _id: str = None, exp_name: str = None, instance: dict = None,
                 override_lists: bool = True, wflow_name: str = None):
        """
        Initiate class
        :param _id: str, _id
        :param exp_name: str, experiment name
        :param instance: dict, instance to insert or validate
        :param override_lists: bool,
        :param wflow_name: str, name of active workflow; checks if database instance has appropriate wflow_name if set
        """
        super().__init__(apparatus_type='vials', _id=_id, instance=instance, override_lists=override_lists)
        if exp_name:
            self.id = self.coll.find_one({"experiment_name": exp_name}).get("_id")
            if wflow_name:
                self.check_wflow_name()

        if self.id:
            self.home_location = self.id.split("_")
            self.home_snapshot = os.path.join(SNAPSHOT_DIR, "VialHome_{}_{:02}.json".format(self.home_location[0],
                                                                                            int(self.home_location[1])))
            self.experiment_name = self.get_prop("experiment_name")
            self.reagent_uuid = self.get_prop("reagent_uuid")
            self.vial_content = self.get_prop("vial_content") or []
            self.capped = self.get_prop("capped")
            self.current_location = self.get_prop("current_location")
            self.location_history = self.get_prop("location_history") or []
            self.current_wflow_name = self.get_prop("current_wflow_name")

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

    def update_content(self, new_content):
        """
        Update status for a vial location or station vial
        :param new_content: str, new vial content
        """
        vial_content = self.vial_content
        vial_content.append(new_content)
        self.insert(self.id, override_lists=True, instance={
            "vial_content": vial_content
        })


class StationStatus(RobotStatusDB):
    """
    Class for accessing the Robot Vial Status database
    Copyright 2021, University of Kentucky
    """

    def __init__(self, _id: str = None, state_id: str = None, instance: dict = None, override_lists: bool = True,
                 wflow_name: str = None):
        """
        Initiate class
        :param _id: str, _id
        :param instance: dict, instance to insert or validate
        :param override_lists: bool,
        :param wflow_name: str, name of active workflow; checks if database instance has appropriate wflow_name if set
        """
        super().__init__(apparatus_type='stations', _id=_id, instance=instance, override_lists=override_lists,
                         wflow_name=wflow_name)
        if state_id:
            self.id = self.coll.find_one({"state": state_id}).get("_id")
            if wflow_name:
                self.check_wflow_name()
        if self.id:
            self.type = self.id.split("_")[0]
            self.available = self.get_prop("available")
            self.state = self.get_prop("state")
            self.current_content = self.get_prop("current_content")
            self.content_history = self.get_prop("content_history") or []
            self.current_wflow_name = self.get_prop("current_wflow_name")

            self.location_snapshot = os.path.join(SNAPSHOT_DIR, f"{self.id}.json")
            self.pre_location_snapshot = os.path.join(SNAPSHOT_DIR, f"pre_{self.id}.json")
            self.raise_amount = RAISE_AMOUNT

    def get_available(self, name_str):
        """
        Get available prop for instance with _id
        :param name_str: str, name string
        :return: prop
        """
        return self.coll.find({"_id": {"$regex": name_str}}).distinct("_id")

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


class ReagentStatus(RobotStatusDB):
    """
    Class for accessing the Robot Reagent Status database
    Copyright 2021, University of Kentucky
    """

    def __init__(self, _id: str = None, instance: dict = None, wflow_name: str = None):
        """
        Initiate class
        :param _id: str, _id
        :param instance: dict, instance to insert or validate
        :param wflow_name: str, name of active workflow; checks if database instance has appropriate wflow_name if set
        """
        super().__init__(apparatus_type='reagents', _id=_id, instance=instance, wflow_name=wflow_name)

        self.description = self.get_prop("description")
        self.location = self.get_prop("location")
        self.name = self.get_prop("name")
        self.notes = self.get_prop("notes")
        self.purity = self.get_prop("purity")
        self.smiles = self.get_prop("smiles")
        self.source = self.get_prop("source")
        self.type = self.get_prop("type")
        self.current_wflow_name = self.get_prop("current_wflow_name")


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
    if check_duplicates(experiment_locs.values()):
        raise ValueError(
            "More than one experiment is assigned the same vial(s): " + check_duplicates(experiment_locs.values()))
    exp_dict = {v: r for r, v in experiment_locs.items()}

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
    wflow_name = ""  # "8CVCollect_BenchmarkCV_test1_single_test"
    # reset_station_db()
    # reset_vial_db({'ae70a9cb-90f6-49ff-8b77-a192be06b703': 'A_02', 'cca7e96e-44e5-423f-9946-7fe951ab5170': 'A_03',
    #                'f3f68664-1c70-45b4-bf77-02a1364bfe89': 'A_04'})
    # VialStatus("A_02").update_location("potentiostat_01")
    # VialStatus("ae70a9cb-90f6-49ff-8b77-a192be06b703").update_capped(True)
    # StationStatus("potentiostat_01").update_available(True)
    # print(VialStatus("A_02", wflow_name=wflow_name).capped)
    # print(VialStatus(r_uuid="550c6dd3-af09-4351-ae1d-deea22ebc41f", wflow_name=wflow_name).capped)
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
    reset_reagent_db(reagents, current_wflow_name=wflow_name)
