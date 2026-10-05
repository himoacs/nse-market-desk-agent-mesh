#!/usr/bin/env python3
"""Configure the NSE-only SAM Desktop instance end to end with the sam CLI.

1. `sam config apply` for everything declarative (models, connectors,
   toolsets, skills, agents) from manifest.yaml.
2. `sam api` for the two things sam config has no resource kind for:
   the chat Project (instance/project.json) and the scheduled tasks
   (instance/scheduled-tasks.json). Both are upserted by name, so re-running
   is safe; agent names are resolved to their runtime ids (agent_<uuid>).

Safety: by default it refuses to run unless the running SAM Desktop was
launched with the NSE home (scripts/sam-desktop.sh nse), so the NSE resources
never land in another instance that happens to be listening on the same port.

Usage:
    scripts/sam-desktop.sh nse                  # macOS: launch the NSE-only instance
    scripts/bootstrap.py                        # apply config + project + scheduled tasks
    scripts/bootstrap.py --remove-builtins      # ...and delete SAM's Orchestrator/Activity Monitor
    scripts/bootstrap.py --use-running-instance # target whatever SAM instance is running
    scripts/bootstrap.py --skip-apply           # only project + scheduled tasks
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NSE_SAM_HOME = Path(os.environ.get("NSE_SAM_HOME", Path.home() / "sam-homes" / "nse-desk"))
# SAM's built-in agents that are not part of the desk. The Builder is kept.
BUILTIN_AGENTS_TO_REMOVE = ("Orchestrator", "Activity Monitor")
TARGET_HOME = None  # set in main(): the SAM_HOME the sam CLI should use (None = CLI default)


def running_sam_home():
    """SAM_HOME of the running sam-desktop process ('' = default home, None = not running)."""
    pids = subprocess.run(["pgrep", "-x", "sam-desktop"], capture_output=True, text=True).stdout.split()
    if not pids:
        return None
    env = subprocess.run(["ps", "eww", "-p", pids[0]], capture_output=True, text=True).stdout
    for token in env.split():
        if token.startswith("SAM_HOME="):
            return token.split("=", 1)[1]
    return ""


def sam_env():
    env = dict(os.environ)
    if TARGET_HOME:
        env["SAM_HOME"] = TARGET_HOME
    else:
        env.pop("SAM_HOME", None)
    return env


def sam_api(method, path, body=None):
    cmd = ["sam", "api", "-X", method, path, "--target", "desktop", "--insecure"]
    tmp = None
    if body is not None:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(body, tmp)
        tmp.close()
        cmd += ["--input", tmp.name]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, env=sam_env())
    finally:
        if tmp:
            os.unlink(tmp.name)
    if out.returncode != 0:
        raise SystemExit(f"sam api {method} {path} failed:\n{out.stdout}\n{out.stderr}")
    text = out.stdout.strip()
    return json.loads(text) if text else None


def runtime_names():
    agents = sam_api("GET", "/api/v1/platform/agents")["data"]
    return {a["name"]: "agent_" + a["id"].replace("-", "_") for a in agents}


def upsert_project(spec, names):
    body = {"name": spec["name"], "description": spec.get("description", ""),
            "defaultAgentId": names[spec["defaultAgent"]]}
    if spec.get("systemPrompt"):
        body["systemPrompt"] = spec["systemPrompt"]
    existing = {p["name"]: p for p in sam_api("GET", "/api/v1/projects").get("data", [])}
    if spec["name"] in existing:
        sam_api("PUT", f"/api/v1/projects/{existing[spec['name']]['id']}", body)
        print(f"project  ~ {spec['name']} (default agent {spec['defaultAgent']})")
    else:
        sam_api("POST", "/api/v1/projects", body)
        print(f"project  + {spec['name']} (default agent {spec['defaultAgent']})")


def remove_builtins():
    for agent in sam_api("GET", "/api/v1/platform/agents")["data"]:
        if agent["name"] in BUILTIN_AGENTS_TO_REMOVE:
            sam_api("DELETE", f"/api/v1/platform/agents/{agent['id']}")
            print(f"agent    - {agent['name']} (SAM built-in)")


def upsert_tasks(specs, names):
    existing = {t["name"]: t for t in sam_api("GET", "/api/v1/scheduledTasks/").get("data", [])}
    for spec in specs:
        body = {k: v for k, v in spec.items() if k != "targetAgent"}
        body["targetAgentName"] = names[spec["targetAgent"]]
        body.setdefault("targetType", "agent")
        if spec["name"] in existing:
            res = sam_api("PATCH", f"/api/v1/scheduledTasks/{existing[spec['name']]['id']}", body)
            verb = "~"
        else:
            res = sam_api("POST", "/api/v1/scheduledTasks/", body)
            verb = "+"
        print(f"schedule {verb} {spec['name']}: {spec['scheduleExpression']} {spec['timezone']} "
              f"-> {spec['targetAgent']} (next run {res.get('nextRunTime') or 'pending'})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-apply", action="store_true", help="skip sam config apply")
    ap.add_argument("--use-running-instance", action="store_true",
                    help="configure whichever SAM Desktop is running (its own home), instead of requiring the NSE home")
    ap.add_argument("--remove-builtins", action="store_true",
                    help="delete SAM's built-in Orchestrator and Activity Monitor agents (the Builder is kept)")
    args = ap.parse_args()

    global TARGET_HOME
    home = running_sam_home()
    if args.use_running_instance:
        TARGET_HOME = home or os.environ.get("SAM_HOME") or None
    else:
        if home is None:
            raise SystemExit("SAM Desktop is not running. Start the NSE instance: scripts/sam-desktop.sh nse\n"
                             "(or start SAM yourself and pass --use-running-instance)")
        if Path(home or "/nonexistent").expanduser().resolve() != NSE_SAM_HOME.resolve():
            raise SystemExit(f"The running SAM Desktop uses SAM_HOME={home or '<default>'}, not {NSE_SAM_HOME}.\n"
                             "Refusing to configure it. Switch first (scripts/sam-desktop.sh nse), or pass\n"
                             "--use-running-instance to configure the running instance on purpose.")
        TARGET_HOME = str(NSE_SAM_HOME)

    if not args.skip_apply:
        print(f"sam config apply --target desktop  (SAM_HOME={TARGET_HOME or '<sam default>'})")
        rc = subprocess.run(["sam", "config", "apply", "--target", "desktop"], cwd=ROOT, env=sam_env()).returncode
        if rc != 0:
            raise SystemExit("sam config apply reported failures; fix them and re-run")

    if args.remove_builtins:
        remove_builtins()
    names = runtime_names()
    upsert_project(json.loads((ROOT / "instance" / "project.json").read_text()), names)
    upsert_tasks(json.loads((ROOT / "instance" / "scheduled-tasks.json").read_text()), names)


if __name__ == "__main__":
    sys.exit(main())
