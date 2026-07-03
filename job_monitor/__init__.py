"""LinkedIn job monitor for Senior Data Engineer roles."""

__all__ = ["run_monitor"]


def __getattr__(name):
    if name == "run_monitor":
        from job_monitor.monitor import run_monitor
        return run_monitor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
