# Robotics Databases

The robotics system relies on MongoDB databases to store and manage real-time and experimental data related to vials, stations, reagents, and workflows. These databases ensure that the robotics and lab automation systems have access to the most up-to-date information needed to carry out experiments and operations efficiently.

The databases are divided into three primary categories:

1. **Status Collections**: Tracks the real-time state of reagents, stations, and vials.
2. **Data Collections**: Stores experimental data and associated metadata.
3. **Standards Collections**: Contains standard measurements and calibration data for various processes.

## Status Collections

The **Status Collections** contain real-time information about the objects used in robotic processes. These collections help keep track of the current states and locations of vials, stations, and reagents, which are critical for ensuring the smooth operation of workflows and experiments.

>**Note**: All Status Collections contain the field `current_wflow_name`. This denotes the name of the workflow from which these collections were initialized (with the {ref}`workflow initialization firework <fireworks:fireworks>`). If a Firework tries to interact with a database document where the `current_wflow_name` does not match the Firework's workflow name, it will through an error (see {ref}`common_errors:Common Errors`).

### *status_reagents*
Stores the current state of reagents, including location, type, and any supporting notes relevant to their use in experiments.

**Example Document:**
```JSON
{
  "_id": "29690ed4-bf85-4945-9c2d-907eb942515d",
  "name": "Acetonitrile",
  "smiles": "CC#N",
  "source": "sigma_aldrich",
  "type": "solvent",
  "description": "solvent",
  "notes": "with 0.25M TEABF4 supporting electrolyte",
  "purity": "",
  "location": "solvent_01",
  "current_wflow_name": "test_workflow",
  "density": 786.0,
  "formal_potential": null
}
```

### *status_stations*
Tracks the status of different stations used in the robotics system. This includes stations such as liquid dispensing stations, potentiostat stations, and balance stations. It also manages the availability of these stations and their current contents.

**Fields of Interest**:
* `_id`: Station name defined in the {ref}`settings:settings`
* `available`: Whether or not the station is available (or in use)
* `state`: Additional state information about station (not used for most station types)

**Example Document (potentiostat station):**
```JSON
{
  "_id": "cv_potentiostat_A_01",           
  "current_wflow_name": "test_workflow",        
  "available": false,                     
  "state": "up",                           
  "current_content": "A_01",               
  "content_history": [                     
    "",
    "S_01",
    ""
  ]                        
}
```

**Example Document (robot grip):**
```JSON
{
  "_id": "robot_grip",
  "current_wflow_name": "test_workflow",
  "available": true,
  "state": "",
  "current_content": "",
  "content_history": [
    "A_01",
    "",
    "S_01",
    "",
    "S_01",
    ""
  ]
}
```

### *status_vials*
Contains information about the current state of vials being used in the system. This includes their location, contents, weight, and other relevant data necessary for tracking them throughout the workflow.

**Fields of Interest**:
* `_id`: Vial ID defined in the {ref}`settings:settings`
* `experiment_name`: When a workflows is loaded via the {ref}`Robotics App<desktop_app:loading a workflow>`, each experiment is assigned a vial. This field denotes the experiment name assigned to this vial.
* `vial_content`: List of dictionaries where each dictionary represents a different reagent in the vial. These are automatically updated any time a reagent is add to *or extracted from* the vial.
* `current_weight`: The most recent weight measurement for the vial and all its contents. Every time a reagent is added/extracted, `current_weight` is reset to `null`.

**Example Document:**
```JSON
{
  "_id": "A_01",
  "current_wflow_name": "test_workflow",
  "experiment_name": "exp01",
  "vial_content": [
    {
      "reagent_uuid": "330391e4-855b-4a1d-851e-59445c65fad0",
      "name": "TEMPO",
      "amount": "0.4682g"
    },
    {
      "reagent_uuid": "29690ed4-bf85-4945-9c2d-907eb942515d",
      "name": "Acetonitrile",
      "amount": "20.04g"
    }
  ],
  "current_weight": null,
  "weight_history": [],
  "current_location": "cv_potentiostat_A_01",
  "location_history": [
    "robot_grip",
    "home"
  ]
}
```

## Data Collections

The **Data Collections** store experimental results and related metadata. These collections ensure that the data generated from experiments are organized and easily retrievable for analysis.

### *experimentation*
This collection stores the raw data generated from experiments, including the associated metadata such as the experimental conditions and the results. Each document represents a unique experiment measurement.

**Example Document:**
```
{
  "_id": "30ded3c7-8ba0-4bab-b390-fb624223dd98",
  "mol_id": "11ZHCX",
  "submission_info": {},
  "data": {
    "file_name": "\\home.iowa.uiowa.edu\nstumme\documents\summer 2020\200727\01 gc we pt…",
    "header": "",
    "note": "",
    "date_recorded": "2020-07-27T17:10:46",
    "data_points_per_scan": 1000,
    "segment": 6,
    "sample_interval": {<data>},
    "quiet_time": {<data>},
    "sensitivity": {<data>},
    "comp_r": {<data>},
    "scan_data" : [<data>],
    "forward": [<data>],
    "reverse": [<data>],
    "conditions": {<data>},
    "plot_data": [<data>],
    "reversibility": [<data>],
    "e_half": [<data>],
    "peak_splittings": [<data>],
    "middle_sweep": [<data>],
  }
}
```

### *metadata*
Contains metadata calculated from from multiple experiment measurements, such as oxidation potentials, diffusion coefficients, and charge transfer rates.

**Example Document:**
```
{
  "_id": "2fadd2f9-453f-4cf7-a29e-63c921029cde",
  "metadata": {
    "oxidation_potential": [
      { <oxidation potential data>  }
    ],
    "diffusion_coefficient": [
      { <diffusion coefficient data>  }
    ],
    "charge_transfer_rate": [
      { <charge transfer rate data>  }
    ]
  }
}
```

## Standards Collections

The **Standards Collections** hold reference data used for calibration and verification of robotic processes.

### *standards_CACalib*
Contains calibration data for chronoamperometry (CA) experiments.

**Example Document:**
```JSON
{
  "_id": "298fb9b4-a7b4-4a58-a55c-431cce6fe93c",
  "mol_id": "11JNLU",
  "date_updated": "2024_09_13",
  "cond_measured": {
    "value": 0.00001722937373737374,
    "unit": "S"
  },
  "res_measured": {
    "value": 58040.41488930109,
    "unit": "Ohm"
  },
  "temperature": {
    "value": 294.18,
    "unit": "K"
  },
  "cell_constant": 76.01553138051766
}
```

---

This database structure ensures the smooth operation of the robotics system by keeping track of real-time information on reagents, stations, and vials, as well as storing experimental data and calibration standards needed for accurate and consistent experimentation.
=======
# Robotics Databases

The robotics system relies on MongoDB databases to store and manage real-time and experimental data related to vials, stations, reagents, and workflows. These databases ensure that the robotics and lab automation systems have access to the most up-to-date information needed to carry out experiments and operations efficiently.

The databases are divided into three primary categories:

1. **Status Collections**: Tracks the real-time state of reagents, stations, and vials.
2. **Data Collections**: Stores experimental data and associated metadata.
3. **Standards Collections**: Contains standard measurements and calibration data for various processes.

## Status Collections

The **Status Collections** contain real-time information about the objects used in robotic processes. These collections help keep track of the current states and locations of vials, stations, and reagents, which are critical for ensuring the smooth operation of workflows and experiments.

>**Note**: All Status Collections contain the field `current_wflow_name`. This denotes the name of the workflow from which these collections were initialized (with the {ref}`workflow initialization firework <fireworks:fireworks>`). If a Firework tries to interact with a database document where the `current_wflow_name` does not match the Firework's workflow name, it will through an error (see {ref}`common_errors:Common Errors`).

### *status_reagents*
Stores the current state of reagents, including location, type, and any supporting notes relevant to their use in experiments.

**Example Document:**
```JSON
{
  "_id": "29690ed4-bf85-4945-9c2d-907eb942515d",
  "name": "Acetonitrile",
  "smiles": "CC#N",
  "source": "sigma_aldrich",
  "type": "solvent",
  "description": "solvent",
  "notes": "with 0.25M TEABF4 supporting electrolyte",
  "purity": "",
  "location": "solvent_01",
  "current_wflow_name": "test_workflow",
  "density": 786.0,
  "formal_potential": null
}
```

### *status_stations*
Tracks the status of different stations used in the robotics system. This includes stations such as liquid dispensing stations, potentiostat stations, and balance stations. It also manages the availability of these stations and their current contents.

**Fields of Interest**:
* `_id`: Station name defined in the {ref}`settings:settings`
* `available`: Whether or not the station is available (or in use)
* `state`: Additional state information about station (not used for most station types)

**Example Document (potentiostat station):**
```JSON
{
  "_id": "cv_potentiostat_A_01",           
  "current_wflow_name": "test_workflow",        
  "available": false,                     
  "state": "up",                           
  "current_content": "A_01",               
  "content_history": [                     
    "",
    "S_01",
    "",
  ]                        
}
```

**Example Document (robot grip):**
```JSON
{
  "_id": "robot_grip",
  "current_wflow_name": "test_workflow",
  "available": true,
  "state": "",
  "current_content": "",
  "content_history": [
    "A_01",
    "",
    "S_01",
    "",
    "S_01",
    "",
  ]
}
```

### *status_vials*
Contains information about the current state of vials being used in the system. This includes their location, contents, weight, and other relevant data necessary for tracking them throughout the workflow.

**Fields of Interest**:
* `_id`: Vial ID defined in the {ref}`settings:settings`
* `experiment_name`: When a workflows is loaded via the {ref}`Robotics App<desktop_app:loading a workflow>`, each experiment is assigned a vial. This field denotes the experiment name assigned to this vial.
* `vial_content`: List of dictionaries where each dictionary represents a different reagent in the vial. These are automatically updated any time a reagent is add to *or extracted from* the vial.
* `current_weight`: The most recent weight measurement for the vial and all its contents. Every time a reagent is added/extracted, `current_weight` is reset to `null`.

**Example Document:**
```JSON
{
  "_id": "A_01",
  "current_wflow_name": "test_workflow",
  "experiment_name": "exp01",
  "vial_content": [
    {
      "reagent_uuid": "330391e4-855b-4a1d-851e-59445c65fad0",
      "name": "TEMPO",
      "amount": "0.4682g"
    },
    {
      "reagent_uuid": "29690ed4-bf85-4945-9c2d-907eb942515d",
      "name": "Acetonitrile",
      "amount": "20.04g"
    }
  ],
  "current_weight": null,
  "weight_history": [],
  "current_location": "cv_potentiostat_A_01",
  "location_history": [
    "robot_grip",
    "home",
  ]
}
```

## Data Collections

The **Data Collections** store experimental results and related metadata. These collections ensure that the data generated from experiments are organized and easily retrievable for analysis.

### *experimentation*
This collection stores the raw data generated from experiments, including the associated metadata such as the experimental conditions and the results. Each document represents a unique experiment measurement.

**Example Document:**
```
{
  "_id": "30ded3c7-8ba0-4bab-b390-fb624223dd98",
  "mol_id": "11ZHCX",
  "submission_info": {},
  "data": {
    "file_name": "\\home.iowa.uiowa.edu\nstumme\documents\summer 2020\200727\01 gc we pt…",
    "header": "",
    "note": "",
    "date_recorded": "2020-07-27T17:10:46",
    "data_points_per_scan": 1000,
    "segment": 6,
    "sample_interval": {<data>},
    "quiet_time": {<data>},
    "sensitivity": {<data>},
    "comp_r": {<data>},
    "scan_data" : [<data>],
    "forward": [<data>],
    "reverse": [<data>],
    "conditions": {<data>},
    "plot_data": [<data>],
    "reversibility": [<data>],
    "e_half": [<data>],
    "peak_splittings": [<data>],
    "middle_sweep": [<data>],
  }
}
```

### *metadata*
Contains metadata calculated from from multiple experiment measurements, such as oxidation potentials, diffusion coefficients, and charge transfer rates.

**Example Document:**
```
{
  "_id": "2fadd2f9-453f-4cf7-a29e-63c921029cde",
  "metadata": {
    "oxidation_potential": [
      { <oxidation potential data>  }
    ],
    "diffusion_coefficient": [
      { <diffusion coefficient data>  }
    ],
    "charge_transfer_rate": [
      { <charge transfer rate data>  }
    ]
  }
}
```

## Standards Collections

The **Standards Collections** hold reference data used for calibration and verification of robotic processes.

### *standards_CACalib*
Contains calibration data for chronoamperometry (CA) experiments.

**Example Document:**
```JSON
{
  "_id": "298fb9b4-a7b4-4a58-a55c-431cce6fe93c",
  "mol_id": "11JNLU",
  "date_updated": "2024_09_13",
  "cond_measured": {
    "value": 0.00001722937373737374,
    "unit": "S"
  },
  "res_measured": {
    "value": 58040.41488930109,
    "unit": "Ohm"
  },
  "temperature": {
    "value": 294.18,
    "unit": "K"
  },
  "cell_constant": 76.01553138051766
}
```

---

This database structure ensures the smooth operation of the robotics system by keeping track of real-time information on reagents, stations, and vials, as well as storing experimental data and calibration standards needed for accurate and consistent experimentation.
