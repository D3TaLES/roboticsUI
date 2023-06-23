from robotics_api.standard_variables import *
from d3tales_api.D3database.d3database import RobotStatusDB


class VialStatus(RobotStatusDB):
    """
    Class for accessing the Robot Vial Status database
    Copyright 2021, University of Kentucky
    """

    def __init__(self, _id: str = None, r_uuid: str = None, instance: dict = None, override_lists: bool = True):
        """
        Initiate class
        :param _id: str, _id
        :param instance: dict, instance to insert or validate
        :param override_lists: bool,
        """
        super().__init__(apparatus_type='vials', _id=_id, instance=instance, override_lists=override_lists)
        if r_uuid:
            self.id = self.coll.find_one({"reagent_uuid": r_uuid}).get("_id")

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
        vial_content = self.get_prop("vial_content")
        vial_content.append(new_content)
        self.insert(self.id, override_lists=True, instance={
            "vial_content": vial_content
        })


class StationStatus(RobotStatusDB):
    """
    Class for accessing the Robot Vial Status database
    Copyright 2021, University of Kentucky
    """

    def __init__(self, _id: str = None, instance: dict = None, override_lists: bool = True):
        """
        Initiate class
        :param _id: str, _id
        :param instance: dict, instance to insert or validate
        :param override_lists: bool,
        """
        super().__init__(apparatus_type='stations', _id=_id, instance=instance, override_lists=override_lists)

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


def reset_station_db(station_name=None):
    all_stations = ["potentiostat_01", ]
    stations = [station_name] if station_name else all_stations
    for station in stations:
        StationStatus(instance={
            "_id": station,
            "available": True,
            "current_content": "",
            "content_history": [],
        })


def reset_vial_db(reagent_locations, capped_default=CAPPED_DEFAULT):
    if len(reagent_locations.values()) > len(set(reagent_locations.values())):
        duplicates = {x for x in reagent_locations.values() if reagent_locations.values().count(x) > 1}
        raise ValueError("More than one reagent is assigned the same vial(s): " + ", ".join(duplicates))
    vial_dict = {v: r for r, v in reagent_locations.items()}
    vial_homes = [
        "A_01", "A_02", "A_03", "A_04",
        "B_01", "B_02", "B_03", "B_04",
        "C_01", "C_02", "C_03", "C_04",
    ]
    for vial in vial_homes:
        VialStatus(instance={
            "_id": vial,
            "reagent_uuid": vial_dict.get(vial, ""),
            "vial_content": [],
            "capped": capped_default,
            "current_location": "home",
            "location_history": [],
        })


if __name__ == "__main__":
    # reset_station_db()
    # reset_vial_db({'ae70a9cb-90f6-49ff-8b77-a192be06b703': 'A_02', 'cca7e96e-44e5-423f-9946-7fe951ab5170': 'A_03',
    #                'f3f68664-1c70-45b4-bf77-02a1364bfe89': 'A_04'})
    # VialStatus("A_02").update_location("potentiostat_01")
    # VialStatus("ae70a9cb-90f6-49ff-8b77-a192be06b703").update_capped(True)
    # StationStatus("potentiostat_01").update_available(True)
    print(VialStatus("A_02").get_prop("capped"))
    print(VialStatus(r_uuid="ae70a9cb-90f6-49ff-8b77-a192be06b703").get_prop("capped"))

