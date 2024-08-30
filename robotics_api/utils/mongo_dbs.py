import os
import json
import warnings
import jsonschema
import pandas as pd
from urllib import request
from dotty_dict import dotty
from pymongo import MongoClient
from monty.json import jsanitize
import python_jsonschema_objects as pjs


def db_info_generator(db_file=None):
    """
    Get information about database connections. This function requires either a db_file argument
    or a DB_INFO_FILE environment variable. This argument or  environment variable should be a path
    to a JSON file containing connection information for the databases. The keys should be the database
    names such as `frontend`, `backend`, `expflow`, and `fireworks`.

    :param db_file: str, path to database info JSON file

    :return: JSON object containing information about database connections
    """
    db_file = db_file or os.environ.get('DB_INFO_FILE') or os.getenv('DB_INFO_FILE')
    if not db_file:
        warnings.warn("Environment variable DB_INFO_FILE not defined. Default database information is in ues. ")
        return {
            "frontend":
                {
                    "host": "mongodb://USERNAME:PASSWORD@DATABASE_IP:DATABASE_PORT/frontend",
                    "database": "ui"
                },
            "backend":
                {
                    "host": "mongodb://USERNAME:PASSWORD@DATABASE_IP:DATABASE_PORT/backend",
                    "database": "backend"
                }
        }
    with open(db_file, "r") as f:
        return json.load(f)


DB_INFO = db_info_generator()


class Schema2Class:
    """
    Get D3TaLES schema from GitHub and load it to a class
    Copyright 2021, University of Kentucky
    """

    def __init__(self, database=None, schema_name=None, schema_directory=None, named_only=False, schema_version=None):
        """

        :param database: str, database name
        :param schema_name: str, schema name
        :param schema_directory: str, schema directory
        :param named_only: If true, only properties with an actual title attribute will be included in the resulting namespace
        """

        # fetch schema
        self.database = database
        self.branch = schema_version or "main"
        self.schema_name = '{}/{}'.format(schema_directory, schema_name) if schema_directory else schema_name
        schema_url = "https://raw.githubusercontent.com/D3TaLES/schema/{}/schema_{}/{}.schema.json".format(
            self.branch, self.database, self.schema_name).replace("robotics_", "")
        # print(schema_url)
        response = request.urlopen(schema_url)
        self.schema = json.loads(response.read().decode())
        # generating classes
        builder = pjs.ObjectBuilder(self.schema)
        ns = builder.build_classes(named_only=named_only)

        # get all name space
        for name_space in dir(ns):
            setattr(self, name_space, getattr(ns, name_space))

        # # highest-level name space for validation
        # self.high_level = getattr(ns, schema_name.title().replace("_", ""))

        # required values
        if self.schema.get("required", ):
            self.required = self.schema.get("required")
        else:
            self.required = None


class DBconnector:
    """
    Class to retrieve a collection from a database and insert new entry.
    Requires a db_infos.json file with credentials
    Copyright 2021, University of Kentucky
    """

    def __init__(self, db_information: dict):
        """
        :param db_information: dictionary of database info
        """

        self.host = db_information.get("host", )
        self.password = db_information.get("admin_password", )
        self.user = db_information.get("admin_user", )
        self.port = int(db_information.get("port", 0))
        self.database = db_information.get("database", )
        self.collection = db_information.get("collection", )

    def get_database(self, **kwargs):
        """
        Returns a database object

        :return: a database object
        """
        try:
            if "@" in self.host:
                conn = MongoClient(self.host)
            else:
                conn = MongoClient(host=self.host, port=self.port,
                                   username=self.user,
                                   password=self.password, **kwargs)

            db = conn[self.database]
        except:
            raise ConnectionError

        return db

    def get_collection(self, coll_name=None):
        """
        Returns a collection from the database

        :param coll_name: name of collection
        :return: db.collection
        """
        db = self.get_database()
        if not coll_name:
            coll_name = self.collection
            if not coll_name:
                raise IOError("No collection specified")

        return db[coll_name]


class MongoDatabase:
    """
    Base class for connecting to a database
    Copyright 2021, University of Kentucky
    """

    def __init__(self, database=None, collection_name=None, instance=None, schema_layer="", schema_directory=None,
                 public=None, schema_db=None, default_id=None, validate_schema=True, verbose=1, schema_version=None):
        """
        :param database: str, name of database (should be a key in the DB_INFO_FILE)
        :param collection_name: str, name of collection
        :param instance: dict, instance to insert or validate
        :param schema_layer: str, schema layer
        :param schema_directory: str, schema directory
        :param public: bool, instance is marked as public if True
        :param schema_db: str, database containing schema
        :param default_id: str, default instance ID
        :param validate_schema: bool, validate schema if True
        """
        self.collection_name = collection_name
        self.instance = {schema_layer: self.dot2dict(instance)} if schema_layer else self.dot2dict(instance)
        self.database = database
        self.verbose = verbose
        self.public = public
        self.dbc = DBconnector(DB_INFO.get(self.database))
        self.coll = self.dbc.get_collection(self.collection_name)
        schema_db = schema_db or database

        # validate
        if instance and validate_schema:
            self.instance['_id'] = self.instance.get("_id") or default_id
            self.s2c = Schema2Class(schema_name=collection_name, database=schema_db, schema_directory=schema_directory,
                                    schema_version=schema_version)
            jsonschema.validate(schema=self.s2c.schema, instance=self.instance)

    def insert(self, _id, nested=False, update_public=True, instance=None, override_lists=True):
        """
        Upserts a dictionary into a collection

        :param _id: str, _id for insertion
        :param nested: bool, insert nested attributes if True
        :param update_public: bool, update the public status if true
        :param instance: dict, instance to be inserted
        :param override_lists: bool, override existing lists in insertion if True
        """
        if not instance:
            instance = jsanitize(self.instance, allow_bson=True)

        # Update public status
        if isinstance(self.public, bool) and update_public:
            self.coll.update_one({"_id": _id}, {"$set": {"public": self.public}}, upsert=True)

        for path, v in instance.items():
            if nested and isinstance(v, dict):
                for nest_k, nest_v in v.items():
                    new_path = ".".join(path.split(".") + [nest_k])
                    self.insert(_id, nested=True, update_public=False, instance={new_path: nest_v})

            elif isinstance(v, list) and not override_lists:
                self.array_checker(path, _id)
                self.coll.update_one({"_id": _id}, {"$addToSet": {path: {"$each": v}}}, upsert=True)
            else:
                self.coll.update_one({"_id": _id}, {"$set": {path: v}}, upsert=True)

        print("{} {}... inserted into the {} database.".format(_id, str(instance)[:15],
                                                               self.database)) if self.verbose > 1 else None

    def path_insert(self, _id, path, value):
        """
        Insert a piece of data to a specific path, updating array if the path leads to an array

        :param _id: str, instance ID
        :param path: str, path to insertion
        :param value: value to insert
        """
        if isinstance(value, list):
            self.array_checker(path, _id)
            self.coll.update_one({"_id": _id}, {"$addToSet": {path: {"$each": value}}}, upsert=True)
        else:
            self.coll.update_one({"_id": _id}, {"$set": {path: value}}, upsert=True)

    def array_checker(self, field_path, _id):
        """
        Create empty array in filed if this field does not already exists. Prepare for set insertion (avoid duplicates)

        :param field_path: str, path to check
        :param _id: str, instance ID
        """
        if not self.coll.count_documents({"_id": _id, field_path: {"$exists": True}}):
            self.coll.update_one({"_id": _id}, {"$set": {field_path: []}}, upsert=True)

    def field_checker(self, entry, field):
        """
        Check if field exists and return result or {}

        :param entry: value
        :param field: field name
        :return: {} or the match
        """
        result = self.coll.find_one({field: entry})
        return result if result else {}

    def make_query(self, query: dict = None, projection: dict = None, output="pandas", multi=True, limit=200):
        """
        Make MongoDB database query

        :param query: dict, query
        :param projection: dict, projection
        :param output: str, output type
        :param multi: bool, return multiple query responses if True
        :param limit: int, limit to the number of responses the query will return
        :return: 1) A dataframe if output="pandas"
                 2) A list if multi=False and a pymongo dursor if multi=True; output != "pandas
        """
        query = query or {}
        projection = projection or {}

        if multi:
            if projection:
                cursor = self.coll.find(query, projection).limit(limit)
            else:
                cursor = self.coll.find(query).limit(limit)
        else:
            if projection:
                cursor = [self.coll.find_one(query, projection)]
            else:
                cursor = [self.coll.find_one(query)]

        if output == "pandas":
            return pd.DataFrame.from_records(cursor)
        elif output == "json":
            json_data = json.loads(json.dumps(list(cursor), ))
            return json_data
        else:
            return list(cursor)

    @staticmethod
    def dot2dict(dot_dict):
        """
        Convert a dotted dictionary to a nested dictionary

        :param dot_dict: dotted dictionary
        :return: nested final dictionary
        """
        dot_dict = dot_dict or {}
        if isinstance(dot_dict, dict):
            final_dict = {}
            for k, v in dot_dict.items():
                if isinstance(k, str) and len(k.split(".")) > 1:
                    dot = dotty()
                    dot[k] = v
                    dot_dict = dot.to_dict()
                    final_dict.update(dot_dict)
                else:
                    final_dict[k] = v
            return final_dict
        return dot_dict


class RobotStatusDB(MongoDatabase):
    """
    Class for accessing the Robot Status database
    Copyright 2021, University of Kentucky
    """

    def __init__(self, apparatus_type: str, _id: str = None, instance: dict = None, override_lists: bool = True,
                 wflow_name: str = None, validate_schema=False):
        """
        Initiate class
        :param apparatus_type: str, name of apparatus
        :param _id: str, _id
        :param instance: dict, instance to insert or validate
        :param override_lists: bool,
        :param wflow_name: str, name of active workflow; checks if database instance has appropriate wflow_name if set
        """
        super().__init__("robotics", 'status_' + apparatus_type, instance, schema_db='robot',
                         validate_schema=validate_schema)
        self.id = _id or self.instance.get("_id")
        self.wflow_name = wflow_name
        if instance:
            instance["_id"] = self.id
            if not self.id:
                raise IOError("ID is required for {} status database insertion.".format(apparatus_type))
            self.insert(self.id, override_lists=override_lists)
        if wflow_name and self.id:
            self.check_wflow_name()

    def __str__(self):
        return self.id

    @property
    def exists(self):
        return True if self.coll.find_one({"_id": self.id}) else False

    def check_wflow_name(self):
        print("ID", self.id)
        current_wflow = self.coll.find_one({"_id": self.id}).get("current_wflow_name")
        if current_wflow == self.wflow_name:
            return True
        raise NameError("Argument wflow_name ({}) does not match instance current_wflow_name {}. Make sure that "
                        "only one workflow is initialized.".format(self.wflow_name, current_wflow))

    def get_prop(self, prop: str):
        """
        Get database prop for instance with _id
        :param prop: str, property name
        :return: prop
        """
        return (self.coll.find_one({"_id": self.id}) or {}).get(prop)

    def update_status(self, new_status, status_name="location"):
        """
        Update status for a vial location or station vial
        :param new_status: str, new vial location or new vial in station
        :param status_name: str, name for status properties
        """
        current_status = self.get_prop("current_" + status_name)
        history = self.get_prop(status_name + "_history") or []
        history.append(current_status)
        self.insert(self.id, override_lists=True, instance={
            "current_" + status_name: new_status,
            status_name + "_history": history
        })

