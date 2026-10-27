"""Where keys come from: environment variables first, then the macOS Keychain. Never a file in this repo.

Each setting NAME is looked up as the environment variable NAME, then as a Keychain generic password
with service "indie-metrics.NAME" (add one with:
    security add-generic-password -s indie-metrics.NAME -a "$USER" -w
which prompts for the value, so it never lands in your shell history).
"""
import os
import subprocess
import sys

SERVICE_PREFIX = "indie-metrics."


class MissingKey(Exception):
    """A setting is not set. The message names the setting and where to put it, never a value."""


def get(name: str, required: bool = True, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value:
        return value.strip()
    if sys.platform == "darwin":
        try:
            out = subprocess.run(
                ["/usr/bin/security", "find-generic-password", "-s", SERVICE_PREFIX + name, "-w"],
                capture_output=True, text=True, timeout=10,
            )
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
    if default is not None:
        return default
    if required:
        raise MissingKey(f"{name} is not set. Set the environment variable {name}, or add a Keychain item "
                         f"with service {SERVICE_PREFIX}{name}.")
    return None
