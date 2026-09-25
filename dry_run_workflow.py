import argparse
import json
import sys
from pathlib import Path
from collections import Counter


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_firework_name(fw):
    return getattr(fw, "name", None) or getattr(fw, "_name", None) or str(fw)


def get_firework_spec(fw):
    return getattr(fw, "spec", {}) or {}


def get_task_name(task):
    return task.__class__.__name__


def validate_raw_expflow(expflow_wf):
    errors = []
    warnings = []

    experiments = expflow_wf.get("experiments", []) or []
    ids = [exp.get("_id") or exp.get("uuid") for exp in experiments]

    duplicate_ids = [x for x, n in Counter(ids).items() if x and n > 1]
    missing_ids = [i for i, x in enumerate(ids, start=1) if not x]

    if duplicate_ids:
        errors.append(f"Duplicate experiment IDs: {duplicate_ids}")

    if missing_ids:
        errors.append(f"Missing experiment IDs at positions: {missing_ids}")

    expected_order = [
        "ferrocene",
        "Tris(2,2'-bipyridine)cobalt(II) Bis(hexafluorophosphate)",
        "Co(II) Soterpy",
        "blank",
    ]

    for i, exp in enumerate(experiments, start=1):
        label = f"Experiment_{i:02d}"
        reagents = exp.get("reagents", []) or []
        workflow = exp.get("workflow", []) or []

        redox_reagents = [
            r for r in reagents
            if r.get("type") == "redox_molecule"
        ]

        redox_transfers = [
            t for t in workflow
            if t.get("name") == "transfer_solid"
            and t.get("start_type") == "redox_molecule"
        ]

        if i < 4:
            if len(redox_reagents) != 1:
                errors.append(
                    f"{label}: expected exactly 1 redox_molecule reagent, found {len(redox_reagents)}."
                )

            if len(redox_transfers) != 1:
                errors.append(
                    f"{label}: expected exactly 1 redox transfer_solid action, found {len(redox_transfers)}."
                )

            if redox_reagents and redox_transfers:
                reagent_id = redox_reagents[0].get("_id") or redox_reagents[0].get("uuid")
                transfer_id = redox_transfers[0].get("start_uuid")

                if reagent_id != transfer_id:
                    errors.append(
                        f"{label}: redox reagent id {reagent_id!r} does not match "
                        f"redox transfer start_uuid {transfer_id!r}."
                    )

                reagent_name = redox_reagents[0].get("name", "")
                expected = expected_order[i - 1]

                if reagent_name != expected:
                    warnings.append(
                        f"{label}: expected redox reagent {expected!r}, found {reagent_name!r}."
                    )

                mass_params = [
                    p for p in redox_transfers[0].get("parameters", []) or []
                    if p.get("description") == "mass"
                ]

                if not mass_params:
                    errors.append(f"{label}: redox transfer has no mass parameter.")
                else:
                    mass = mass_params[0]
                    unit = mass.get("unit")
                    value = mass.get("value")

                    if unit != "g":
                        errors.append(
                            f"{label}: redox mass unit should be 'g', found {unit!r}."
                        )

                    if value in (None, ""):
                        errors.append(f"{label}: redox mass value is blank.")

        else:
            if len(redox_reagents) != 0:
                errors.append(
                    f"{label}: blank should have zero redox_molecule reagents, found {len(redox_reagents)}."
                )

            if len(redox_transfers) != 0:
                errors.append(
                    f"{label}: blank should have zero redox transfer_solid actions, found {len(redox_transfers)}."
                )

    return errors, warnings


def validate_generated_workflow(wf):
    errors = []
    warnings = []

    fws = getattr(wf, "fws", []) or []

    if not fws:
        errors.append("Generated Workflow has zero FireWorks.")
        return errors, warnings

    names = [get_firework_name(fw) for fw in fws]
    specs = [get_firework_spec(fw) for fw in fws]

    if any("exp04_None" in name for name in names):
        errors.append("Generated FireWorks still contain 'exp04_None'. Blank naming patch is not working.")

    if not any("exp04_blank_no_redox" in name for name in names):
        warnings.append("No generated FireWork name contains 'exp04_blank_no_redox'.")

    exp_specs = {}
    for fw in fws:
        spec = get_firework_spec(fw)
        exp_name = spec.get("exp_name")
        if exp_name and exp_name not in exp_specs:
            exp_specs[exp_name] = spec

    for exp_name in ["exp01", "exp02", "exp03"]:
        spec = exp_specs.get(exp_name)
        if not spec:
            errors.append(f"No generated FireWork spec found for {exp_name}.")
            continue

        if spec.get("rom_id") in (None, "", "no_redox_mol"):
            errors.append(f"{exp_name}: rom_id is missing or no_redox_mol.")

        if spec.get("mol_id") in (None, "", "blank_no_redox"):
            errors.append(f"{exp_name}: mol_id is invalid: {spec.get('mol_id')!r}.")

        if spec.get("is_blank") is True:
            errors.append(f"{exp_name}: is_blank=True, but this should be a redox experiment.")

    blank_spec = exp_specs.get("exp04")
    if not blank_spec:
        errors.append("No generated FireWork spec found for exp04.")
    else:
        if blank_spec.get("rom_id") != "no_redox_mol":
            errors.append(f"exp04: expected rom_id='no_redox_mol', found {blank_spec.get('rom_id')!r}.")

        if blank_spec.get("mol_id") != "blank_no_redox":
            errors.append(f"exp04: expected mol_id='blank_no_redox', found {blank_spec.get('mol_id')!r}.")

        if blank_spec.get("is_blank") is not True:
            errors.append(f"exp04: expected is_blank=True, found {blank_spec.get('is_blank')!r}.")

    return errors, warnings


def write_report(path, expflow_wf, wf, raw_errors, raw_warnings, gen_errors, gen_warnings):
    fws = getattr(wf, "fws", []) or []

    with open(path, "w", encoding="utf-8") as out:
        out.write("DRY RUN WORKFLOW REPORT\n")
        out.write("=======================\n\n")

        out.write(f"Workflow name from JSON: {expflow_wf.get('name')}\n")
        out.write(f"Number of experiments in JSON: {len(expflow_wf.get('experiments', []) or [])}\n")
        out.write(f"Number of generated FireWorks: {len(fws)}\n\n")

        out.write("RAW JSON VALIDATION\n")
        out.write("-------------------\n")
        if raw_errors:
            out.write("ERRORS:\n")
            for e in raw_errors:
                out.write(f"  - {e}\n")
        else:
            out.write("No raw JSON errors found.\n")

        if raw_warnings:
            out.write("WARNINGS:\n")
            for w in raw_warnings:
                out.write(f"  - {w}\n")
        else:
            out.write("No raw JSON warnings found.\n")

        out.write("\nGENERATED FIREWORKS VALIDATION\n")
        out.write("------------------------------\n")
        if gen_errors:
            out.write("ERRORS:\n")
            for e in gen_errors:
                out.write(f"  - {e}\n")
        else:
            out.write("No generated FireWorks errors found.\n")

        if gen_warnings:
            out.write("WARNINGS:\n")
            for w in gen_warnings:
                out.write(f"  - {w}\n")
        else:
            out.write("No generated FireWorks warnings found.\n")

        out.write("\nGENERATED FIREWORKS\n")
        out.write("-------------------\n")

        for i, fw in enumerate(fws, start=1):
            name = get_firework_name(fw)
            spec = get_firework_spec(fw)
            tasks = getattr(fw, "tasks", []) or []

            out.write(f"\nFW {i}: {name}\n")
            out.write(f"  exp_name: {spec.get('exp_name')}\n")
            out.write(f"  full_name: {spec.get('full_name')}\n")
            out.write(f"  mol_id: {spec.get('mol_id')}\n")
            out.write(f"  rom_id: {spec.get('rom_id')}\n")
            out.write(f"  rom_name: {spec.get('rom_name')}\n")
            out.write(f"  solv_id: {spec.get('solv_id')}\n")
            out.write(f"  elect_id: {spec.get('elect_id')}\n")
            out.write(f"  is_blank: {spec.get('is_blank')}\n")
            out.write(f"  experiment_kind: {spec.get('experiment_kind')}\n")
            out.write("  tasks:\n")
            for task in tasks:
                out.write(f"    - {get_task_name(task)}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("workflow_json", help="Path to ExpFlow workflow JSON")
    parser.add_argument("--name-tag", default="dryrun", help="Name tag passed to run_expflow_wf")
    parser.add_argument("--out", default="dry_run_report.txt", help="Report output path")
    args = parser.parse_args()

    workflow_path = Path(args.workflow_json)
    expflow_wf = load_json(workflow_path)

    raw_errors, raw_warnings = validate_raw_expflow(expflow_wf)

    from robotics_api.fireworks.Workflow_Writer import run_expflow_wf

    exp_params = {
        "dry_run": True,
        "test_mode": True,
    }

    wf = run_expflow_wf(
        expflow_wf,
        name_tag=args.name_tag,
        exp_params=exp_params,
        data_type="cv",
    )

    gen_errors, gen_warnings = validate_generated_workflow(wf)

    write_report(args.out, expflow_wf, wf, raw_errors, raw_warnings, gen_errors, gen_warnings)

    print(f"Wrote report: {args.out}")

    total_errors = len(raw_errors) + len(gen_errors)
    total_warnings = len(raw_warnings) + len(gen_warnings)

    print(f"Errors: {total_errors}")
    print(f"Warnings: {total_warnings}")

    if total_errors:
        print("Dry run failed validation.")
        sys.exit(1)

    print("Dry run passed validation. No hardware was run.")


if __name__ == "__main__":
    main()