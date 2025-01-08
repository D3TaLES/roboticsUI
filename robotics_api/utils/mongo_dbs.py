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
from robotics_api.settings import DB_INFO_FILE


def db_info_generator(db_file=DB_INFO_FILE):
    """
    Generates information about database connections.

    This function requires either a `db_file` argument or a `DB_INFO_FILE` environment variable.
    The argument or environment variable should be a path to a JSON file containing connection
    information for the databases. The keys should be the database names such as `frontend`,
    `backend`, `expflow`, and `fireworks`.

    Args:
        db_file (str, optional): Path to the database info JSON file. Defaults to None.

    Returns:
        dict: JSON object containing information about database connections.
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
print(DB_INFO)


class Schema2Class:
    """
    Get D3TaLES schema from GitHub and load it to a class
    Copyright 2021, University of Kentucky
    """

    def __init__(self, database=None, schema_name=None, schema_directory=None, named_only=False, schema_version=None):
        """
        Initializes the Schema2Class object and retrieves the schema.

        Args:
            database (str, optional): Database name. Defaults to None.
            schema_name (str, optional): Schema name. Defaults to None.
            schema_directory (str, optional): Directory of the schema. Defaults to None.
            named_only (bool, optional): If True, only properties with a title attribute will be
                included in the resulting namespace. Defaults to False.
            schema_version (str, optional): Schema version. Defaults to None.
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
        Initializes the DBconnector object with database information.

        Args:
            db_information (dict): Dictionary containing database information.
        """

        self.host = db_information.get("host", )
        self.password = db_information.get("admin_password", )
        self.user = db_information.get("admin_user", )
        self.port = int(db_information.get("port", 0))
        self.database = db_information.get("database", )
        self.collection = db_information.get("collection", )

    def get_database(self, **kwargs):
        """
        Returns a database object.

        Returns:
            pymongo.database.Database: A database object.
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
        Returns a collection from the database.

        Args:
            coll_name (str, optional): Name of the collection. Defaults to None.

        Returns:
            pymongo.collection.Collection: The collection object.
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
        Initializes the MongoDatabase object.

        Args:
            database (str, optional): Name of the database. Defaults to None.
            collection_name (str, optional): Name of the collection. Defaults to None.
            instance (dict, optional): Instance to insert or validate. Defaults to None.
            schema_layer (str, optional): Schema layer. Defaults to "".
            schema_directory (str, optional): Directory of the schema. Defaults to None.
            public (bool, optional): Marks instance as public if True. Defaults to None.
            schema_db (str, optional): Database containing the schema. Defaults to None.
            default_id (str, optional): Default instance ID. Defaults to None.
            validate_schema (bool, optional): Validates schema if True. Defaults to True.
            verbose (int, optional): Verbosity level. Defaults to 1.
            schema_version (str, optional): Version of the schema. Defaults to None.
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
        Upserts a dictionary into a MongoDB collection.

        Args:
            _id (str): ID for insertion.
            nested (bool, optional): Inserts nested attributes if True. Defaults to False.
            update_public (bool, optional): Updates the public status if True. Defaults to True.
            instance (dict, optional): Instance to be inserted. Defaults to None.
            override_lists (bool, optional): Overrides existing lists in insertion if True. Defaults to True.
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
        Inserts a value at a specific path in the collection.

        Args:
            _id (str): Instance ID.
            path (str): Path for insertion.
            value: Value to insert.
        """
        if isinstance(value, list):
            self.array_checker(path, _id)
            self.coll.update_one({"_id": _id}, {"$addToSet": {path: {"$each": value}}}, upsert=True)
        else:
            self.coll.update_one({"_id": _id}, {"$set": {path: value}}, upsert=True)

    def array_checker(self, field_path, _id):
        """
        Checks if the field at the path is an array and prepares for set insertion.

        Args:
            field_path (str): Path to check.
            _id (str): Instance ID.
        """
        if not self.coll.count_documents({"_id": _id, field_path: {"$exists": True}}):
            self.coll.update_one({"_id": _id}, {"$set": {field_path: []}}, upsert=True)

    def field_checker(self, entry, field):
        """
        Checks if a field exists in the collection and returns the result.

        Args:
            entry: Value to check.
            field (str): Name of the field.

        Returns:
            bool: True if the field exists, False otherwise.
        """
        result = self.coll.find_one({field: entry})
        return result if result else {}

    def make_query(self, query: dict = None, projection: dict = None, output="pandas", multi=True, limit=200):
        """
        Executes a MongoDB database query.

        Args:
            query (dict, optional): Query parameters. Defaults to an empty dictionary.
            projection (dict, optional): Fields to include or exclude. Defaults to an empty dictionary.
            output (str, optional): Output type, can be "pandas", "json", or list. Defaults to "pandas".
            multi (bool, optional): If True, returns multiple query responses. If False, returns a single result.
                Defaults to True.
            limit (int, optional): Maximum number of responses to return. Defaults to 200.

        Returns:
            1) A dataframe if output="pandas"
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
        Converts dot notation keys to nested dictionary.

        Args:
            dot_not (dict): Dictionary with dot notation keys.

        Returns:
            dict: Nested dictionary.
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
    Provides access to the Robot Status database.

    This class is used to interact with the status database for a specific type of apparatus.
    Copyright 2021, University of Kentucky.
    """

    def __init__(self, apparatus_type: str, _id: str = None, instance: dict = None,
                 override_lists: bool = True, wflow_name: str = None, validate_schema=False):
        """
        Initializes the RobotStatusDB class.

        Args:
            apparatus_type (str): Name of the apparatus.
            _id (str, optional): Unique identifier for the status entry. Defaults to None.
            instance (dict, optional): Instance to insert or validate in the database. Defaults to None.
            override_lists (bool, optional): Whether to override existing lists in the database. Defaults to True.
            wflow_name (str, optional): Name of the active workflow. If set, verifies that the instance has the
                appropriate workflow name. Defaults to None.
            validate_schema (bool, optional): If True, validates the instance against the schema. Defaults to False.

        Raises:
            IOError: If no ID is provided for the status database insertion.
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
        """Checks if an entry with the given ID exists in the database.

        Returns:
            bool: True if the entry exists, False otherwise.
        """
        return bool(self.coll.find_one({"_id": self.id}))

    def check_wflow_name(self):
        """Checks if the workflow name matches the instance's current workflow name.

        Raises:
            NameError: If the workflow name does not match the current instance's workflow name.
        """
        print("ID", self.id)
        current_wflow = self.coll.find_one({"_id": self.id}).get("current_wflow_name")
        if current_wflow == self.wflow_name:
            return True
        raise NameError("Argument wflow_name ({}) does not match instance current_wflow_name {}. "
                        "Make sure that only one workflow is initialized.".format(self.wflow_name, current_wflow))

    def get_prop(self, prop: str):
        """
        Retrieves a property from the database for the instance with the given ID.

        Args:
            prop (str): Name of the property to retrieve.

        Returns:
            Any: The value of the property, or None if the property does not exist.
        """
        return (self.coll.find_one({"_id": self.id}) or {}).get(prop)

    def update_status(self, new_status, status_name: str = "location"):
        """
        Updates the status for a vial location or station vial.

        Args:
            new_status (str): New status, such as the new vial location or new vial in the station.
            status_name (str, optional): Name of the status property. Defaults to "location".
        """
        current_status = self.get_prop("current_" + status_name)
        history = self.get_prop(status_name + "_history") or []
        history.append(current_status)
        self.insert(self.id, override_lists=True, instance={
            "current_" + status_name: new_status,
            status_name + "_history": history
        })
