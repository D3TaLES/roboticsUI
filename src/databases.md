# Robotics Databases


## Status Collections


### *status_reagents*

**Example document:**
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

**Example Document (potentiostat station):**
```JSON
{
  "_id": "cv_potentiostat_A_01",
  "current_wflow_name": "test_workflow",
  "available": true,
  "state": "down",
  "current_content": "",
  "content_history": []
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
  "content_history": []
}
```


### *status_vials*

**Example document:**
```JSON
{
  "_id": "A_01",
  "current_wflow_name": "test_workflow",
  "experiment_name": "exp01",
  "vial_content": [],
  "current_weight": null,
  "current_location": "home",
  "weight_history": [],
  "location_history": []
}
```


## Data Collections


### *experimentation*

**Example document:**
```JSON
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

**Example document:**
```JSON
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


### *standards_CACalib*

**Example document:**
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
