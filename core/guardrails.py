"""Central security policy for command, path, plugin, and memory guards."""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Sequence

BASE_DIR = Path(__file__).resolve().parent.parent
POLICY_PATH = BASE_DIR / "regole e vincoli" / "regole e vincoli.md"

_BLOCKED_COMMAND = re.compile(
    r"(?:rm\s+-rf|sudo\b|chmod\b|curl\s*\|\s*bash|invoke-webrequest|remove-item\s+-recurse|format[- ]volume|diskpart|del\s+/[fsq])",
    re.IGNORECASE,
)
_SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|password|passwd|secret|token|authorization)(\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"\b(?:sk|ghp|xox[baprs])-?[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
)
_ALLOWED_EXECUTABLES = {
    "brightnessctl", "ffmpeg", "ffprobe", "ollama", "open", "osascript",
    "cmd", "cmd.exe", "netsh", "pactl", "powershell", "powershell.exe",
    "python", "python.exe", "steam", "steam.exe", "tasklist", "wmctrl",
    "which", "xrandr", "pgrep", "xdg-open", "gtk-launch", "notepad.exe",
    "code", "shutdown", "systemctl", "schtasks", "launchctl", "crontab",
    "ufw", "firewall-cmd", "iptables", "pkexec", "sudo", "nmcli", "xset",
    "networksetup", "pmset", "msg",
}


def _is_launcher_game_executable(command: Sequence[object]) -> bool:
    """Allow only executables inside conventional Steam/Epic game libraries."""
    if not command:
        return False
    raw = Path(str(command[0]))
    if not raw.is_absolute() or raw.suffix.lower() != ".exe":
        return False
    try:
        path = raw.resolve()
        parts = {part.casefold() for part in path.parts}
        return "steamapps" in parts and "common" in parts or "epic games" in parts
    except OSError:
        return False

def require_policy_file() -> str:
    """Load the user policy before any assistant work starts."""
    if not POLICY_PATH.is_file():
        raise RuntimeError(f"Security policy missing: {POLICY_PATH}")
    return POLICY_PATH.read_text(encoding="utf-8")


def append_rule(rule: str) -> None:
    """Persist a newly supplied rule in the canonical policy file."""
    text = require_policy_file()
    normalized = rule.strip()
    if normalized and normalized not in text:
        with POLICY_PATH.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(f"\n- {normalized}\n")


def _command_text(command: Sequence[object] | str) -> str:
    if isinstance(command, str):
        return command
    return " ".join(str(part) for part in command)


def validate_command(command: Sequence[object] | str, *, shell: bool = False) -> None:
    text = _command_text(command)
    if shell:
        raise PermissionError("Blocked: shell execution is disabled by the security policy")
    if _BLOCKED_COMMAND.search(text):
        raise PermissionError("Blocked: dangerous command rejected by the security policy")
    if isinstance(command, (list, tuple)) and command:
        executable = Path(str(command[0])).name.lower()
        if executable not in _ALLOWED_EXECUTABLES and not _is_launcher_game_executable(command):
            raise PermissionError(f"Blocked: executable '{executable}' is not whitelisted")


def guarded_run(command, *args, **kwargs):
    validate_command(command, shell=bool(kwargs.get("shell", False)))
    return subprocess._original_run(command, *args, **kwargs)


def guarded_popen(command, *args, **kwargs):
    validate_command(command, shell=bool(kwargs.get("shell", False)))
    return subprocess._original_popen(command, *args, **kwargs)


def install_subprocess_guards() -> None:
    if not hasattr(subprocess, "_original_run"):
        subprocess._original_run = subprocess.run
    if not hasattr(subprocess, "_original_popen"):
        subprocess._original_popen = subprocess.Popen
    subprocess.run = guarded_run
    subprocess.Popen = guarded_popen


def resolve_safe_path(raw_path: str | Path, *, allow_policy_file: bool = False,
                      allow_plugin_dir: bool = False) -> Path:
    normalized = os.path.expandvars(os.fspath(raw_path)).strip().strip('"')
    return Path(normalized).expanduser().resolve()


def redact_sensitive(value):
    if isinstance(value, dict):
        return {key: redact_sensitive(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if not isinstance(value, str):
        return value
    redacted = value
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub(lambda match: (
            f"{match.group(1)}{match.group(2)}[REDACTED]"
            if match.lastindex and match.lastindex >= 2
            else "[REDACTED]"
        ), redacted)
    return redacted


def redact_memory_file(path: Path) -> None:
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps(redact_sensitive(data), indent=2, ensure_ascii=False), encoding="utf-8")
