from robotics_api.standard_variables import *
from d3tales_api.D3database.d3database import RobotStatusDB


class VialStatus(RobotStatusDB):
    """
    Class for accessing the Robot Vial Status database
    Copyright 2021, University of Kentucky
    """

    def __init__(self, _id: str = None, r_uuid: str = None, exp_name: str = None, instance: dict = None,
                 override_lists: bool = True, wflow_name: str = None):
        """
        Initiate class
        :param _id: str, _id
        :param r_uuid: str, reagent UUID
        :param exp_name: str, experiment name
        :param instance: dict, instance to insert or validate
        :param override_lists: bool,
        :param wflow_name: str, name of active workflow; checks if database instance has appropriate wflow_name if set
        """
        super().__init__(apparatus_type='vials', _id=_id, instance=instance, override_lists=override_lists)
        if r_uuid:
            self.id = self.coll.find_one({"reagent_uuid": r_uuid}).get("_id")
            if wflow_name:
                self.check_wflow_name()
        if exp_name:
            self.id = self.coll.find_one({"experiment_name": exp_name}).get("_id")
            if wflow_name:
                self.check_wflow_name()

        if self.id:
            self.home_location = self.id.split("_")
            self.home_snapshot = os.path.join(SNAPSHOT_DIR, "VialHome_{}_{:02}.json".format(self.home_location[0], int(self.home_location[1])))
            self.experiment_name = self.get_prop("experiment_name")
            self.reagent_uuid = self.get_prop("reagent_uuid")
            self.vial_content = self.get_prop("vial_content") or []
            self.capped = self.get_prop("capped")
            self.current_location = self.get_prop("current_location")
            self.location_history = self.get_prop("location_history") or []
            self.current_wflow_name = self.get_prop("current_wflow_name")

    @property
    def location_snapshot(self):
        if self.current_location == "home":
            return self.home_snapshot
        elif self.current_location == "solv":
            _, solv_idx = self.home_location  # Get solvent location
            return os.path.join(SNAPSHOT_DIR, "Solvent_{:02}.json".format(int(solv_idx)))
        return os.path.join(SNAPSHOT_DIR, "{}.json".format(self.current_location))

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
        super().__init__(apparatus_type='stations', _id=_id, instance=instance, override_lists=override_lists, wflow_name=wflow_name)
        if state_id:
            self.id = self.coll.find_one({"state": state_id}).get("_id")
            if wflow_name:
                self.check_wflow_name()

        self.available = self.get_prop("available")
        self.state = self.get_prop("state")
        self.current_content = self.get_prop("current_content")
        self.content_history = self.get_prop("content_history") or []
        self.current_wflow_name = self.get_prop("current_wflow_name")

    def update_available(self, value: bool):
        """
        Get available prop for instance with _id
        :param value: bool, available prop
        :return: prop
        """
        return self.coll.update_one({"_id": self.id}, {"$set": {"available": value}})

    def update_content(self, new_content):
        """
        Update status for a vial location or station vial
        :param new_content: str, new vial in station
        """
        self.update_status(new_content, "content")


def reset_station_db(station_name=None, reagent_locs=None, current_wflow_name=""):
    # Check reagent locations 1-to-1 status
    reagent_locs = reagent_locs or {}
    if len(reagent_locs.values()) > len(set(reagent_locs.values())):
        duplicates = {x for x in reagent_locs.values() if reagent_locs.values().count(x) > 1}
        raise ValueError("More than one reagent is assigned the same station: " + ", ".join(duplicates))
    reagent_dict = {v: r for r, v in reagent_locs.items()}

    all_stations = ["potentiostat_01", "solvent_01", "robot_grip"]
    stations = [station_name] if station_name else all_stations
    for station in stations:
        state = "down" if "potentiostat" in station else reagent_dict.get(station, "")
        StationStatus(instance={
            "_id": station,
            "current_wflow_name": current_wflow_name,
            "available": True,
            "state": state,
            "current_content": "",
            "content_history": [],
        })


def reset_vial_db(reagent_locs, experiment_locs, current_wflow_name="", capped_default=CAPPED_DEFAULT):
    # Check reagent locations 1-to-1 status
    if len(reagent_locs.values()) > len(set(reagent_locs.values())):
        duplicates = {x for x in reagent_locs.values() if reagent_locs.values().count(x) > 1}
        raise ValueError("More than one reagent is assigned the same vial(s): " + ", ".join(duplicates))
    reagent_dict = {v: r for r, v in reagent_locs.items()}
    # Check experiment locations 1-to-1 status
    if len(experiment_locs.values()) > len(set(experiment_locs.values())):
        duplicates = {x for x in experiment_locs.values() if experiment_locs.values().count(x) > 1}
        raise ValueError("More than one experiment is assigned the same vial(s): " + ", ".join(duplicates))
    exp_dict = {v: r for r, v in experiment_locs.items()}

    # Set up vial locations DB
    vial_homes = [
        "A_01", "A_02", "A_03", "A_04",
        "B_01", "B_02", "B_03", "B_04",
        "C_01", "C_02", "C_03", "C_04",
    ]
    VialStatus().coll.delete_many({})
    for vial in vial_homes:
        reagent = reagent_dict.get(vial, "")
        VialStatus(instance={
            "_id": vial,
            "current_wflow_name": current_wflow_name,
            "experiment_name": exp_dict.get(vial, ""),
            "reagent_uuid": reagent,
            "vial_content": [reagent] if reagent else [],
            "capped": capped_default,
            "current_location": "home",
            "location_history": [],
        })


if __name__ == "__main__":
    wflow_name = None # "8CVCollect_BenchmarkCV_test1_single_test"
    # reset_station_db()
    # reset_vial_db({'ae70a9cb-90f6-49ff-8b77-a192be06b703': 'A_02', 'cca7e96e-44e5-423f-9946-7fe951ab5170': 'A_03',
    #                'f3f68664-1c70-45b4-bf77-02a1364bfe89': 'A_04'})
    # VialStatus("A_02").update_location("potentiostat_01")
    # VialStatus("ae70a9cb-90f6-49ff-8b77-a192be06b703").update_capped(True)
    # StationStatus("potentiostat_01").update_available(True)
    print(VialStatus("A_02", wflow_name=wflow_name).capped)
    print(VialStatus(r_uuid="550c6dd3-af09-4351-ae1d-deea22ebc41f", wflow_name=wflow_name).capped)

