"""CLI for the local LinkedIn job monitor agent."""

import argparse
import os
import subprocess
import sys
import time

from job_monitor.agent import is_agent_running, run_agent_loop
from job_monitor.monitor import run_monitor
from job_monitor.paths import CONFIG_FILE, DATA_DIR, LOG_FILE, load_local_config


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def cmd_start(_args: argparse.Namespace) -> int:
    running, pid = is_agent_running()
    if running:
        print(f"Agent already running (pid {pid})")
        return 0

    load_local_config()
    env = os.environ.copy()
    env["PYTHONPATH"] = _repo_root() + os.pathsep + env.get("PYTHONPATH", "")

    process = subprocess.Popen(
        [sys.executable, "-m", "job_monitor.agent"],
        cwd=_repo_root(),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    print(f"Local agent started (pid {process.pid})")
    print(f"Logs: {LOG_FILE}")
    return 0


def cmd_stop(_args: argparse.Namespace) -> int:
    running, pid = is_agent_running()
    if not running:
        print("Agent is not running")
        return 0
    os.kill(pid, 15)  # SIGTERM
    for _ in range(20):
        time.sleep(0.25)
        running, _ = is_agent_running()
        if not running:
            break
    print(f"Stopped agent (pid {pid})")
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    running, pid = is_agent_running()
    if running:
        print(f"Agent is running (pid {pid})")
        print(f"Data dir: {DATA_DIR}")
        print(f"Log file: {LOG_FILE}")
    else:
        print("Agent is not running")
    print(f"Config: {CONFIG_FILE}")
    return 0


def cmd_run_once(_args: argparse.Namespace) -> int:
    load_local_config()
    count = run_monitor()
    print(f"Done — {count} new job(s) found")
    return 0


def cmd_foreground(_args: argparse.Namespace) -> int:
    run_agent_loop()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Local LinkedIn job monitor agent for Senior Data Engineer roles"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("start", help="Start the agent in the background (checks every hour)")
    sub.add_parser("stop", help="Stop the background agent")
    sub.add_parser("status", help="Show whether the agent is running")
    sub.add_parser("run-once", help="Run a single check now")
    sub.add_parser(
        "foreground",
        help="Run the agent in the foreground (useful for debugging)",
    )

    args = parser.parse_args()
    commands = {
        "start": cmd_start,
        "stop": cmd_stop,
        "status": cmd_status,
        "run-once": cmd_run_once,
        "foreground": cmd_foreground,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
