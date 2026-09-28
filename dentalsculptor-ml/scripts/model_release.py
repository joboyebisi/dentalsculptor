"""Register, promote, or roll back immutable TRELLIS checkpoint references."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REGISTRY = Path(__file__).parents[1] / "finetune" / "config" / "model_registry.json"


def load():
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def save(data):
    REGISTRY.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    register = sub.add_parser("register")
    register.add_argument("name"); register.add_argument("--repo", required=True); register.add_argument("--revision", required=True)
    register.add_argument("--manifest", required=True); register.add_argument("--report", required=True)
    promote = sub.add_parser("promote"); promote.add_argument("name")
    sub.add_parser("rollback")
    sub.add_parser("show")
    args = parser.parse_args(); data = load()
    if args.command == "register":
        if args.name in data["models"]: raise SystemExit("Model name already exists; checkpoint registrations are immutable.")
        report = json.loads(Path(args.report).read_text(encoding="utf-8"))
        data["models"][args.name] = {"repoId": args.repo, "revision": args.revision, "status": "candidate", "datasetManifest": args.manifest, "evaluationReport": args.report, "gatesPassed": bool(report.get("gatesPassed", False))}
        save(data)
    elif args.command == "promote":
        model = data["models"].get(args.name)
        if not model or not model.get("gatesPassed"): raise SystemExit("Candidate is missing or its evaluation gates did not pass.")
        data["lastKnownGood"] = data["active"]; data["active"] = args.name; model["status"] = "production"; save(data)
    elif args.command == "rollback":
        data["active"], data["lastKnownGood"] = data["lastKnownGood"], data["active"]; save(data)
    model = data["models"][data["active"]]
    print(json.dumps({"active": data["active"], "lastKnownGood": data["lastKnownGood"], "TRELLIS_MODEL_NAME": model["repoId"], "TRELLIS_MODEL_REVISION": model["revision"]}, indent=2))


if __name__ == "__main__": main()
