#!/usr/bin/env python3
"""Set up the NSE Market Desk on a running SAM Desktop, using only the sam CLI.

What it does:
  1. Checks your LLM settings in .env (copy .env.example to .env first).
  2. Finds the running SAM Desktop and, if that instance already has other
     agents, asks before adding the desk next to them (nothing is deleted).
  3. `sam config apply` for everything declarative: model, connectors,
     toolsets, skills and the five agents (manifest.yaml).
  4. `sam api` for the two things sam config has no resource kind for: the
     "NSE Market Desk" chat project (instance/project.json) and two scheduled
     tasks (instance/scheduled-tasks.json). Both are upserted by name, so
     re-running is safe. The scheduled tasks are created DISABLED, so nothing
     calls your LLM on a timer until you turn them on (--enable-schedules, or
     the Schedules page in SAM).

Usage:
    python3 scripts/bootstrap.py                    # the normal run
    python3 scripts/bootstrap.py --enable-schedules # ...and switch the schedules on
    python3 scripts/bootstrap.py --builtin-models   # ...also point SAM's own general/planning
                                                    #    models at your LLM (overwrites them)
    python3 scripts/bootstrap.py --remove-builtins  # ...also delete SAM's Orchestrator and
                                                    #    Activity Monitor (Builder is kept)
    python3 scripts/bootstrap.py --yes              # don't ask about existing agents
    python3 scripts/bootstrap.py --skip-apply       # only the project and scheduled tasks
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

OUR_AGENT_PREFIX = "nse_"
SAM_BUILTIN_AGENTS = {"Orchestrator", "Activity Monitor", "Builder"}
REMOVABLE_BUILTINS = ("Orchestrator", "Activity Monitor")  # the Builder is always kept
PLACEHOLDER_MARKERS = ("replace-me", "example.com", "your-", "sk-...")

TARGET_HOME = None  # the SAM_HOME the sam CLI should use (None = the CLI's default home)


# ---------------------------------------------------------------- LLM settings

def read_dotenv(path):
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def check_llm_settings():
    """Fail early, with a clear message, if .env is missing or still has placeholder values."""
    env_file = ROOT / ".env"
    values = {**read_dotenv(env_file), **{k: v for k, v in os.environ.items() if k.startswith("LLM_")}}
    if not env_file.exists() and not any(k.startswith("LLM_") for k in os.environ):
        raise SystemExit("No .env file found. Create it from the template and fill in your LLM details:\n"
                         "    cp .env.example .env        (Windows: copy .env.example .env)\n"
                         "then edit .env and run this script again.")
    provider = values.get("LLM_PROVIDER", "custom")
    required = ["LLM_MODEL_NAME", "LLM_API_KEY"] + (["LLM_API_BASE"] if provider == "custom" else [])
    missing = [k for k in required if not values.get(k)]
    if missing:
        raise SystemExit(f".env is missing: {', '.join(missing)}. See .env.example for what each one means.")
    filled = [k for k in ("LLM_MODEL_NAME", "LLM_API_KEY", "LLM_API_BASE") if values.get(k)]
    placeholders = [k for k in filled if any(m in values[k].lower() for m in PLACEHOLDER_MARKERS)]
    if placeholders:
        raise SystemExit(f".env still has placeholder values for: {', '.join(placeholders)}.\n"
                         "Edit .env and put in your real LLM endpoint, model and key.")


# ------------------------------------------------------------------ the sam CLI

def find_sam_cli():
    if not shutil.which("sam"):
        raise SystemExit("The `sam` CLI was not found on your PATH. Install it first (README, step 1),\n"
                         "then open a new terminal and check that `sam --version` works.")


def detect_running_sam():
    """Return (state, home): state is 'running', 'not-running' or 'unknown' (no pgrep/ps, e.g. Windows);
    home is the running app's SAM_HOME ('' means its default home)."""
    try:
        pids = subprocess.run(["pgrep", "-x", "sam-desktop"], capture_output=True, text=True).stdout.split()
        if not pids:
            return "not-running", None
        env = subprocess.run(["ps", "eww", "-p", pids[0]], capture_output=True, text=True).stdout
    except OSError:
        return "unknown", None
    for token in env.split():
        if token.startswith("SAM_HOME="):
            return "running", token.split("=", 1)[1]
    return "running", ""


def sam_env():
    env = dict(os.environ)
    if TARGET_HOME:
        env["SAM_HOME"] = TARGET_HOME
    else:
        env.pop("SAM_HOME", None)
    return env


def sam_api(method, path, body=None, *, hint=""):
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
        raise SystemExit(f"sam api {method} {path} failed:\n{out.stdout}{out.stderr}{hint}")
    text = out.stdout.strip()
    return json.loads(text) if text else None


def list_agents(hint=""):
    return sam_api("GET", "/api/v1/platform/agents", hint=hint)["data"]


def runtime_names():
    return {a["name"]: "agent_" + a["id"].replace("-", "_") for a in list_agents()}


# --------------------------------------------------------------------- steps

def choose_target_and_confirm(assume_yes):
    global TARGET_HOME
    state, home = detect_running_sam()
    if state == "not-running":
        raise SystemExit("SAM Desktop is not running. Start the app, wait until its chat screen appears,\n"
                         "then run this script again.")
    TARGET_HOME = (home or None) if state == "running" else (os.environ.get("SAM_HOME") or None)
    print(f"Target SAM instance: {TARGET_HOME or 'default home'}")

    agents = list_agents(hint="\nCould not reach SAM Desktop. Is it fully started (chat screen visible)?\n"
                              "If you started it with a custom SAM_HOME, export the same SAM_HOME in this terminal.\n")
    others = sorted(a["name"] for a in agents
                    if a["name"] not in SAM_BUILTIN_AGENTS and not a["name"].startswith(OUR_AGENT_PREFIX))
    if others and not assume_yes:
        print(f"\nThis SAM instance already has other agents: {', '.join(others)}")
        print("The desk adds its own agents (nse_*), connectors, toolsets and skills next to them;\n"
              "nothing existing is deleted or changed.")
        if not sys.stdin.isatty():
            raise SystemExit("Re-run with --yes to continue.")
        if input("Continue? [y/N] ").strip().lower() not in ("y", "yes"):
            raise SystemExit("Stopped; nothing was changed.")


def run_apply(manifest=None):
    cmd = ["sam", "config", "apply", "--target", "desktop"] + (["-m", manifest] if manifest else [])
    print("\n$ " + " ".join(cmd))
    if subprocess.run(cmd, cwd=ROOT, env=sam_env()).returncode != 0:
        raise SystemExit("sam config apply reported failures; see the output above, fix the cause and re-run.")


def remove_builtins():
    for agent in list_agents():
        if agent["name"] in REMOVABLE_BUILTINS:
            sam_api("DELETE", f"/api/v1/platform/agents/{agent['id']}")
            print(f"agent    - {agent['name']} (SAM built-in)")


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


def upsert_tasks(specs, names, enable):
    existing = {t["name"]: t for t in sam_api("GET", "/api/v1/scheduledTasks/").get("data", [])}
    for spec in specs:
        body = {k: v for k, v in spec.items() if k != "targetAgent"}
        body["targetAgentName"] = names[spec["targetAgent"]]
        body.setdefault("targetType", "agent")
        if spec["name"] in existing:
            # Never change on/off through the update call (SAM rejects it, and a re-run
            # must not undo a choice the user made); on/off has its own endpoint below.
            body.pop("enabled", None)
            res = sam_api("PATCH", f"/api/v1/scheduledTasks/{existing[spec['name']]['id']}", body)
            verb = "~"
        else:
            res = sam_api("POST", "/api/v1/scheduledTasks/", body)
            verb = "+"
        if enable and not res.get("enabled"):
            sam_api("POST", f"/api/v1/scheduledTasks/{res['id']}/enable")
            res["enabled"] = True
        state = "enabled" if res.get("enabled") else "disabled"
        print(f"schedule {verb} {spec['name']}: {spec['scheduleExpression']} {spec['timezone']} "
              f"-> {spec['targetAgent']} ({state})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-apply", action="store_true", help="skip `sam config apply`")
    ap.add_argument("--yes", action="store_true", help="don't ask before adding the desk to an instance that has other agents")
    ap.add_argument("--enable-schedules", action="store_true", help="switch the two scheduled tasks on (they are created disabled)")
    ap.add_argument("--builtin-models", action="store_true",
                    help="also point SAM's own general/planning models at your LLM (overwrites them)")
    ap.add_argument("--remove-builtins", action="store_true",
                    help="delete SAM's built-in Orchestrator and Activity Monitor agents (the Builder is kept)")
    args = ap.parse_args()
    sys.stdout.reconfigure(line_buffering=True)  # keep our lines in order with the sam CLI's output

    find_sam_cli()
    if not args.skip_apply:
        check_llm_settings()
    choose_target_and_confirm(args.yes)

    if not args.skip_apply:
        run_apply()
        if args.builtin_models:
            run_apply("manifests/builtin-models.yaml")
    if args.remove_builtins:
        remove_builtins()

    names = runtime_names()
    print()
    upsert_project(json.loads((ROOT / "instance" / "project.json").read_text()), names)
    upsert_tasks(json.loads((ROOT / "instance" / "scheduled-tasks.json").read_text()), names, args.enable_schedules)

    print("\nDone. In SAM Desktop open Projects > NSE Market Desk (or start a new chat) and try a prompt.")


if __name__ == "__main__":
    sys.exit(main())
