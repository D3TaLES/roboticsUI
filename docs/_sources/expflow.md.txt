# ExpFlow Robotic Workflows


## Building a Template

A customizable ExpFlow Template lists the reagent types, apparatus items, instrument types, and workflow actions of an experimental protocol. A researcher uses a web-based user interface with buttons and dropdown menus to create a Template.

An ExpFlow Template converts experimental procedures into graphs that contain data provenances. The Template has categories for reagent (e.g., redox material, solvent), apparatus (e.g., beaker, electrode) and instrument (e.g., potentiostat, spectrometer). In a Template graph, nodes (the reagent, apparatus, and instrument categories) are connected by edges that correspond to actions (e.g., dispense, heat). Each action contains a start position, an end position, and action parameters (e.g., volume for dispensing liquid, temperature for heating, etc.). As the actions are sequenced, ExpFlow graphs capture the action provenances.

For example, a CV experiment to determine the diffusion coefficient might include redox-active molecule and solvent reagents, a beaker/vial apparatus, and a potentiostat (Figure 2). Workflow actions might include transferring the liquid solvent and solid solute to the beaker, heating and stirring the solution, measuring the working electrode surface area, and collecting CV data. In this example, the user might add five collect-CV-data actions because the experiment includes five CV scans, each performed at a different scan rate. Although the Template can take time and effort to produce, it can be reused for all related and subsequent experiments.

For example, a CV experiment to determine the diffusion coefficient might include `redox_molecule` and `solvent` reagents; `beaker`, and `electrochemical_cell` apparatus, and a potentiostat instrument.   Workflow actions might include `transfer_liquid` (start position = `solvent` and end position = `beaker`), transfer_solid (start position = `redox_molecule` and end position = `beaker`), heat_stir (start and end position = `beaker`), and collect_cv_data (start position = `beaker` and end position = `electrochemical_cell`). There may be multiple data collection actions. For example, in this example, the scientist might add five collect_cv_data actions because the experiment includes five CVs, each run at a different scan rate. Each action incorporates a standard action type, starting and ending positions, and a brief description. Although these templates take time and effort to produce, they can be reused for all related experiments. Additionally, an existing templated can be cloned and modified, limiting the amount of time needed to construct new templates. Templates can also be shared among ExpFlow users.


```{image} media/template_workflow.png
:alt: Templates and Workflows
```

### Add materials (reagents, apparatus, and instruments)


### Add actions


## Use Template for Robotic Workflow

### Set default parameters

### Establish variable parameters

*!! This page is in still in development*
