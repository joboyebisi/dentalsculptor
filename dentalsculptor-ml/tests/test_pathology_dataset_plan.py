import json
from pathlib import Path


def test_pathology_plan_keeps_modalities_out_of_external_anatomy_mix():
    plan_path = Path(__file__).parents[1] / "finetune" / "config" / "pathology_dataset_plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    assert plan["status"] == "research-plan-no-downloads-authorized"
    assert "must not enter" in plan["separationPolicy"]["rule"]
    assert all("external-photo-to-mesh-finetune" in dataset.get("prohibitedUse", []) or
               "external-surface-generator" in dataset.get("prohibitedUse", []) or
               "3D-depth-supervision" in dataset.get("prohibitedUse", [])
               for dataset in plan["datasets"])

    routes = {item["case"]: item for item in plan["caseRouting"]}
    assert routes["cusp-fracture"]["datasetDependency"] == "none"
    assert "required" in routes["endodontic-access"]["datasetDependency"]
