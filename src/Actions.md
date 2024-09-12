# Actions Module

## Overview

The **actions** module consists of classes and functions that manage and track robotic actions related to **vials**, **stations**, and **standards**.  It interacts directly with the MongoDB robotics database collections (for more, see {ref}`Databases`) to store and retrieve these items' status, positions, and contents. Its modular design facilitates precise handling and tracking of items during robotic operations. It is the second level of abstraction between the [](Utils) and [](Fireworks) modules.

The module consists of three files:

1. **db_manipulations.py**: Defines classes that manage database entries, allowing for reading and writing of vial, station, or standard data.
2. **standard_actions.py**: Provides a set of classes for managing the real-time operations (e.g., movement, positioning) of vials and stations.
3. **system_tests.py**: Contains several tests for the robotic system software and hardware.

The classes defined in `db_manipulations.py` and `standard_actions.py` work together to manage both the **status and physical handling** of vials and stations, integrating with the robotic systems in use. The MongoDB-based database keeps track of real-time information, ensuring data persistence for vial status, position, and any experimental or standard data tied to those items. Ultimately, it abstracts complex interactions with hardware and databases, allowing higher-level systems and users to focus on overarching goals, such as experiment design and execution, without needing to worry about the underlying mechanics of status updates, position tracking, or data integrity.


### High-Level Workflow

The strength of the actions module lies in how the two components (db_manipulations and standard_actions) work together. While db_manipulations ensures that data is accurately reflected in the database, standard_actions ensures that physical operations are seamlessly executed and tracked. This integration ensures real-time synchronization between the physical world and the database, a critical aspect of robotics and lab automation.

1. **Database Interaction**:
   Use classes in `db_manipulations.py` to create, update, and retrieve information about vials and stations from the MongoDB database.

2. **Physical Manipulation**:
   Use classes in `standard_actions.py` to control the real-time robotic actions, such as moving vials between stations or adjusting their positions within stations.

3. **System Testing**:
   The `system_tests.py` file provides a way to validate these actions, ensuring that both the database interactions and the robotic movements are working as expected.

For each vial, station, or standard object, there exists a base class in db_manipulations for interacting with the database and an action class in standard_actions for performing actions. For instance, consider solvent is dispensed into a vial at a liquid dispensing station. The `VialMove` class from standard_actions ensures the vial is located at the desired liquid dispensing station and `VialStatus` from db_manipulations updates the vial contents with the dispensed solvent. At the same time, the standard_actions class `LiquidStation` handles the actual movement, while the db_manipulations base class `StationStatus` updates the MongoDB database with the station's new position and the db_manipulations base class `ReagentStatus` provides information about the solvent. More information

> **Note**: Database interaction classes from db_manipulations serve as base classes for all standard_action classes, and standard_action methods use the db_manipulation base methods to update databases when needed. As a result, **db_manipulations classes are rarely called independently.** Rather, when methods from standard_action classes are used for actions, the database update methods should be initiated automatically.



## 1. DB Manipulations

### Purpose:
This file contains classes that manage the **database interactions** related to vials, stations, and standards. The primary goal is to **store and retrieve vial and station information** about the status and properties of these objects, ensuring data persistence and facilitating operations within the robotics system. The db_manipulations classes are invoked when the system needs to log the status of a new vial or station, update the position of an entity, or retrieve detailed information on a particular standard or item. However, as noted above, db_manipulation classes are rarely called independently because they serve as base classes for the standard_action classes.

### Core Components:
- **VialStatus**: This class is responsible for accessing the database and managing vial-related data, such as its ID, experiment name, and other metadata. It extends from `RobotStatusDB`, which provides database access methods tailored for robotic status information.
- **StationStatus**: Similar to `VialStatus`, but focused on the stations where vials are stored or processed. This class also extends `RobotStatusDB` and helps track information such as which vials are at which station and what actions have been performed on them.

These classes provide the foundational data structures to **store and retrieve vial and station information** from MongoDB. They ensure that when a robotic operation occurs, the system knows the current status and position of vials and stations, allowing for accurate operations.



## 2. Standard Actions

### Purpose:
This file contains the operational logic to manage the **real-time status and positioning** of vials and stations. It builds on the foundation set by `db_manipulations.py` to execute the robotic operations required to manipulate these objects. These classes abstract away the complexities involved in controlling hardware, tracking vial positions, or updating the status of stations and standards. In practical terms, standard_actions is used whenever the system needs to perform an action on a physical entity such as a vial or station. For example, if a vial needs to be moved to a new position or its contents processed in a station, this file would handle those operations while keeping the database updated with the latest state information.

### Core Components:
- **VialMove**: A class designed to handle the physical movement of vials between positions in the robotic system.
- **LiquidStation**: A class designed to handle the status, content, and operation of a liquid dispensing station.
- **BalanceStation**: A class designed to handle the status, content, and operation of a balance station.
- **PotentiostatStation**: A **base** class designed to handle the status, content, and operation of a potentiostat station, including its vial elevator. Usable classes using `PotentiostatStation` as a base include `CVPotentiostatStation` and `CAPotentiostatStation`.
- **Perturbed Snapshot**: A method for adjusting positions based on perturbations, which may be used in calibration or experimental testing.
- etc.

This module interfaces with the robotics system to **physically manage vial or station operations**, ensuring that robotic movements are tracked and that the current state is accurately reflected in the database.

> **Note**: No standard_action class (or db_manipulations class for that matter) refers to a specific vial or station. When a standard_action class is initiated, the `_id` argument specifies the specific item. For example, `LiquidStation` is a class for handling any liquid dispensing station, while `Liquidstation(_id="solvent_01")` handles dispensing station 1.

### Example Usage:
Here’s an example of how `VialMove` could be used to move a vial from one location to another:

```python
from robotics_api.actions.standard_actions import VialMove

# Initialize a VialMove object for a specific vial
test_vial = VialMove(_id="A_01")

# Retrieve the vial so it is held by the robotic arm
test_vial.retrieve()

# Home the vial to its home position
test_vial.place_home()
```

The next example moves the vial `A_01` to potentiostat `cv_potentiostat_A_01` and moves the vial elevator up.
```python
from robotics_api.actions.standard_actions import *

# Initialize vial and potentiostat objects
test_vial = VialMove(_id="A_01")
test_potent = PotentiostatStation("ca_potentiostat_B_01")  

# Retrieve the vial and place it at the potentiostat
test_potent.place_vial(test_vial)

# Move potentiostat elevator up  
test_potent.move_elevator(endpoint="down")

```

## 3. System Tests

Many more example usages can be found in **system_test.py**. Under the `if __name__ == "__main__":` portion of the file contains many tests that are commented out. To run one of these tests, simply uncomment that line and run the files by running `python system_test.py` in your terminal while located in the `actions` directory.
