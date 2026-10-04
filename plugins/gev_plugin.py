"""Lifecycle bridge for a local God's Eye View checkout.

The GEV actions are intentionally placeholders in this first integration step.
"""

from __future__ import annotations

import atexit
from collections import deque
import os
from pathlib import Path
import socket
import subprocess
import threading
import time
from urllib.error import URLError
from urllib.request import urlopen

GEV_DIR = Path(__file__).resolve().parents[3] / "gods-eye-view-main" / "_gev-clone"
GEV_PORT = 4173
GEV_NODE_DIR = GEV_DIR / ".node"
GEV_HEALTH_URL = f"http://127.0.0.1:{GEV_PORT}/"
STARTUP_TIMEOUT_SEC = 60
INSTALL_TIMEOUT_SEC = 600
STOP_TIMEOUT_SEC = 5
GEV_LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "gev.log"

_process: subprocess.Popen[str] | None = None
_process_lock = threading.Lock()
_started = False
_ui = None
_output_lines: deque[str] = deque(maxlen=200)
_output_lock = threading.Lock()
_output_reader: threading.Thread | None = None
_job_handle = None
_job_kernel = None

PLUGIN = {
    "name": "gev",
    "description": (
        "Controlla God's Eye View, il globo 3D con aerei, navi e satelliti. "
        "Azioni disponibili: open (apri il globo), track (target_type e target_id), "
        "layer (layer ed enabled), reset (ripristina la vista), annotate (lat, lon e text)."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Azione GEV prevista: open, track, layer, reset oppure annotate.",
                "enum": ["open", "track", "layer", "reset", "annotate"],
            },
            "target_type": {
                "type": "STRING",
                "description": "Per track: tipo di oggetto da tracciare (flight, vessel, satellite).",
                "enum": ["flight", "vessel", "satellite"],
            },
            "target_id": {
                "type": "STRING",
                "description": "Per track: identificativo dell'oggetto da tracciare (es. codice volo, MMSI, NORAD ID).",
            },
            "layer": {
                "type": "STRING",
                "description": "Per layer: nome del layer da attivare o disattivare (flights, vessels, satellites, earthquakes, fires, cctv, ...).",
            },
            "enabled": {
                "type": "BOOLEAN",
                "description": "Per layer: true per attivare, false per disattivare.",
            },
            "lat": {
                "type": "NUMBER",
                "description": "Per annotate: latitudine del punto.",
            },
            "lon": {
                "type": "NUMBER",
                "description": "Per annotate: longitudine del punto.",
            },
            "text": {
                "type": "STRING",
                "description": "Per annotate: testo dell'annotazione.",
            },
        },
        "required": ["action"],
    },
}


def _log(message: str) -> None:
    print(message, flush=True)
    try:
        GEV_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with GEV_LOG_PATH.open("a", encoding="utf-8") as log_file:
            log_file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")
    except OSError:
        pass


def _read_output(process: subprocess.Popen[str]) -> None:
    stream = process.stdout
    if stream is None:
        return
    try:
        for line in stream:
            text = line.rstrip()
            if not text:
                continue
            with _output_lock:
                _output_lines.append(text)
            _log(f"GEV subprocess: {text}")
    finally:
        stream.close()


def _process_output() -> str:
    with _output_lock:
        return "\n".join(_output_lines)


def _captured_text(output: str | bytes | None) -> str:
    if output is None:
        return ""
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return output


def _port_is_listening() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", GEV_PORT), timeout=0.25):
            return True
    except OSError:
        return False


def _terminate_process(process: subprocess.Popen[str]) -> None:
    try:
        process.terminate()
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=STOP_TIMEOUT_SEC)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=2.0)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            pass
    except ProcessLookupError:
        pass


def _gev_runtime() -> tuple[dict[str, str], str, str]:
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join(
        part for part in (str(GEV_NODE_DIR), env.get("PATH", "")) if part
    )
    expected = GEV_NODE_DIR / "node.exe"
    node_exe = expected.resolve()
    if not node_exe.is_file():
        raise FileNotFoundError(f"GEV: runtime Node portatile non trovato: {node_exe}")

    # GEV security: invoca solo il node.exe del runtime portatile, mai un node arbitrario.
    if node_exe != expected.absolute():
        raise PermissionError(
            f"GEV: node.exe risolto in {node_exe}, atteso {expected.absolute()}"
        )

    npm_cli = GEV_NODE_DIR / "node_modules" / "npm" / "bin" / "npm-cli.js"
    if not npm_cli.is_file():
        raise FileNotFoundError(f"GEV: npm-cli.js non trovato: {npm_cli}")
    return env, str(node_exe), str(npm_cli)


def _creation_options() -> dict[str, int]:
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


def _attach_kill_on_close_job(process: subprocess.Popen[str]) -> None:
    """On Windows, terminate GEV and its descendants if Jarvis exits abruptly."""
    global _job_handle, _job_kernel
    if os.name != "nt":
        return

    import ctypes
    from ctypes import wintypes

    class IoCounters(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class BasicLimitInformation(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class ExtendedLimitInformation(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", BasicLimitInformation),
            ("IoInfo", IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD
    ]
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL

    job = kernel.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())

    limits = ExtendedLimitInformation()
    limits.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel.SetInformationJobObject(
        job, 9, ctypes.byref(limits), ctypes.sizeof(limits)
    ):
        error = ctypes.get_last_error()
        kernel.CloseHandle(job)
        raise ctypes.WinError(error)

    process_handle = wintypes.HANDLE(int(process._handle))
    if not kernel.AssignProcessToJobObject(job, process_handle):
        error = ctypes.get_last_error()
        kernel.CloseHandle(job)
        raise ctypes.WinError(error)

    _job_handle = job
    _job_kernel = kernel


def _close_job_handle() -> None:
    global _job_handle, _job_kernel
    if _job_handle is not None and _job_kernel is not None:
        _job_kernel.CloseHandle(_job_handle)
    _job_handle = None
    _job_kernel = None


# GEV lifecycle hook
def start() -> None:
    """Install GEV dependencies if needed and start its local Vite server."""
    global _output_reader, _process, _started

    with _process_lock:
        if _started:
            return
        if not GEV_DIR.is_dir():
            raise FileNotFoundError(f"GEV: checkout non trovata: {GEV_DIR}")

        if _port_is_listening():
            message = f"GEV: conflitto, la porta {GEV_PORT} è già occupata; non termino il processo esistente."
            _log(message)
            raise RuntimeError(message)

        env, node_exe, npm_cli = _gev_runtime()
        creation_options = _creation_options()

        if not (GEV_DIR / "node_modules").is_dir():
            _log("GEV: primo avvio, eseguo npm install via node.exe (può durare minuti)...")
            try:
                result = subprocess.run(
                    [node_exe, npm_cli, "install"],
                    cwd=GEV_DIR,
                    env=env,
                    timeout=INSTALL_TIMEOUT_SEC,
                    capture_output=True,
                    text=True,
                    **creation_options,
                )
            except subprocess.TimeoutExpired as exc:
                output = "\n".join(
                    part for part in (
                        _captured_text(exc.stdout),
                        _captured_text(exc.stderr),
                    ) if part
                )
                raise TimeoutError(
                    f"GEV: npm install superato il timeout di {INSTALL_TIMEOUT_SEC}s.\n{output}"
                ) from exc
            if result.returncode != 0:
                output = "\n".join(part for part in (result.stdout, result.stderr) if part)
                raise RuntimeError(f"GEV: npm install fallito (exit {result.returncode}).\n{output}")

        with _output_lock:
            _output_lines.clear()

        vite_cli = GEV_DIR / "node_modules" / "vite" / "bin" / "vite.js"
        if not vite_cli.is_file():
            raise FileNotFoundError(f"GEV: vite.js non trovato dopo install: {vite_cli}")

        command = [
            node_exe,
            str(vite_cli),
            "--host", "127.0.0.1",
            "--port", str(GEV_PORT),
            "--strictPort",
        ]
        try:
            _process = subprocess.Popen(
                command,
                cwd=GEV_DIR,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                **creation_options,
            )
            _attach_kill_on_close_job(_process)
            _output_reader = threading.Thread(
                target=_read_output,
                args=(_process,),
                name="gev-output",
                daemon=True,
            )
            _output_reader.start()

            deadline = time.monotonic() + STARTUP_TIMEOUT_SEC
            while True:
                if _process.poll() is not None:
                    raise RuntimeError(
                        f"GEV: il server è terminato con exit {_process.returncode}.\n{_process_output()}"
                    )
                try:
                    with urlopen(GEV_HEALTH_URL, timeout=2) as response:
                        if response.status == 200:
                            break
                except (URLError, TimeoutError, OSError):
                    pass
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"GEV: health check non riuscito entro {STARTUP_TIMEOUT_SEC}s.\n{_process_output()}"
                    )
                time.sleep(1)
        except Exception:
            if _process is not None:
                _terminate_process(_process)
            _close_job_handle()
            _process = None
            _started = False
            raise

        _started = True
        _log(f"GEV: pronto su {GEV_HEALTH_URL}")


# GEV lifecycle hook
def stop() -> None:
    """Stop the local GEV subprocess; repeated calls are harmless."""
    global _process, _started, _output_reader

    with _process_lock:
        if not _started and _process is None:
            return
        process = _process
        if process is None or process.poll() is not None:
            _started = False
            _process = None
            _close_job_handle()
            return

        try:
            _terminate_process(process)
        finally:
            _close_job_handle()
            _started = False
            _process = None
            _output_reader = None
        _log("GEV: fermato")


def run(parameters: dict, player=None) -> str:
    """Validate an action and forward its abstract message to the UI bridge."""
    if not isinstance(parameters, dict):
        parameters = {}

    action = parameters.get("action", "")
    if not isinstance(action, str):
        action = ""
    action = action.strip()

    write_log = getattr(player, "write_log", None) if player is not None else None

    def log_message(message: str) -> None:
        if callable(write_log):
            try:
                write_log(message)
                return
            except Exception:
                pass
        _log(message)

    allowed_actions = {"open", "track", "layer", "reset", "annotate"}
    if action not in allowed_actions:
        log_message(f"GEV: azione sconosciuta '{action}'")
        return f"Non riconosco l'azione GEV '{action}', signore."

    params: dict[str, object]
    if action in {"open", "reset"}:
        params = {}
    elif action == "track":
        target_type = parameters.get("target_type")
        if not isinstance(target_type, str) or target_type not in {"flight", "vessel", "satellite"}:
            return "Per tracciare un oggetto mi serve il tipo (flight, vessel o satellite), signore."
        target_id = parameters.get("target_id")
        if not isinstance(target_id, str) or not target_id.strip():
            target_description, missing = {
                "flight": ("un volo", "il codice"),
                "vessel": ("una nave", "l'MMSI"),
                "satellite": ("un satellite", "il NORAD ID"),
            }[target_type]
            return f"Per tracciare {target_description} mi serve {missing}, signore."
        target_id = target_id.strip()
        params = {"target_type": target_type, "target_id": target_id}
    elif action == "layer":
        layer = parameters.get("layer")
        if not isinstance(layer, str) or not layer.strip():
            return "Per modificare un layer mi serve il nome del layer, signore."
        enabled = parameters.get("enabled")
        if not isinstance(enabled, bool):
            return "Per il layer mi dica se devo attivarlo o disattivarlo, signore."
        params = {"layer": layer.strip(), "enabled": enabled}
    else:
        lat = parameters.get("lat")
        lon = parameters.get("lon")
        if not isinstance(lat, (int, float)) or isinstance(lat, bool) or not -90 <= lat <= 90:
            return "Per annotare mi serve una latitudine valida, signore."
        if not isinstance(lon, (int, float)) or isinstance(lon, bool) or not -180 <= lon <= 180:
            return "Per annotare mi serve una longitudine valida, signore."
        text = parameters.get("text")
        if not isinstance(text, str) or not text.strip():
            return "Per annotare mi serve il testo dell'annotazione, signore."
        params = {"lat": lat, "lon": lon, "text": text.strip()}

    message = {"action": action, "params": params}
    send_to_gev = getattr(player, "send_to_gev", None) if player is not None else None
    if not callable(send_to_gev):
        log_message(f"GEV: UI non pronta, azione '{action}' non inviata")
        return (
            f"Signore, non posso eseguire l'azione GEV '{action}': "
            "l'interfaccia non è ancora pronta."
        )

    try:
        send_to_gev(message)
    except Exception as exc:
        log_message(f"GEV: invio fallito per '{action}': {exc}")
        return f"Signore, l'invio dell'azione GEV '{action}' è fallito: {exc}"

    details = ""
    if action == "track":
        details = f" (target_type={params['target_type']}, target_id={params['target_id']})"
    elif action == "layer":
        details = f" (layer={params['layer']}, enabled={params['enabled']})"
    elif action == "annotate":
        details = f" (lat={params['lat']}, lon={params['lon']})"
    log_message(f"GEV: invio azione '{action}'{details}")

    if action == "open":
        return "Apro God's Eye View, signore."
    if action == "track":
        target_name = {
            "flight": "il volo",
            "vessel": "la nave",
            "satellite": "il satellite",
        }[params["target_type"]]
        return f"Traccio {target_name} {params['target_id']}, signore."
    if action == "layer":
        verb = "Attivo" if params["enabled"] else "Disattivo"
        return f"{verb} il layer {params['layer']}, signore."
    if action == "reset":
        return "Resetto la vista di God's Eye View, signore."
    return f"Aggiungo un'annotazione a ({params['lat']}, {params['lon']}), signore."


# GEV lifecycle hook
atexit.register(stop)
