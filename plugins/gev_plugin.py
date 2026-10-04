"""Lifecycle and MCP bridge for a local God's Eye View checkout."""

from __future__ import annotations

import atexit
from collections import deque
import math
import os
from pathlib import Path
import socket
import subprocess
import threading
import time
from urllib.error import URLError
from urllib.request import urlopen

from plugins._gev_mcp_client import (
    McpClientError,
    McpStdioClient,
    to_gemini_schema,
    tool_result_text,
)

GEV_DIR = Path(__file__).resolve().parents[3] / "gods-eye-view-main" / "_gev-clone"
GEV_PORT = 4173
GEV_NODE_DIR = GEV_DIR / ".node"
GEV_HEALTH_URL = f"http://127.0.0.1:{GEV_PORT}/"
STARTUP_TIMEOUT_SEC = 60
INSTALL_TIMEOUT_SEC = 600
STOP_TIMEOUT_SEC = 5
GEV_LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "gev.log"
_MAX_SAFE_JS_INTEGER = 2**53 - 1

_process: subprocess.Popen[str] | None = None
_process_lock = threading.Lock()
_started = False
_ui = None
_output_lines: deque[str] = deque(maxlen=200)
_output_lock = threading.Lock()
_output_reader: threading.Thread | None = None
_job_handle = None
_job_kernel = None
_mcp_client: McpStdioClient | None = None
_mcp_start_error: str | None = None
_startup_finished = threading.Event()

PLUGIN = {
    "name": "gev",
    "description": (
        "Controlla God's Eye View, il globo 3D con aerei, navi e satelliti. "
        "Azioni disponibili: open (apri il globo), track (target_type e target_id), "
        "layer (layer ed enabled), reset (ripristina la vista), annotate (lat, lon e text), "
        "historical_map (mostra o anima confini storici disponibili). "
        "Per ricerche, rotte e altri strumenti usa le funzioni MCP gev_mcp_*."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Azione GEV prevista: open, track, layer, reset, annotate oppure historical_map.",
                "enum": ["open", "track", "layer", "reset", "annotate", "historical_map"],
            },
            "target_type": {
                "type": "STRING",
                "description": "Per track: tipo di oggetto tracciabile (flight o satellite).",
                "enum": ["flight", "satellite"],
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
            "command": {
                "type": "STRING",
                "description": "Per historical_map: show, animate, stop oppure clear.",
                "enum": ["show", "animate", "stop", "clear"],
            },
            "year": {
                "type": "INTEGER",
                "description": "Per historical_map show: anno richiesto; verrà scelto lo snapshot disponibile più vicino.",
            },
            "start_year": {
                "type": "INTEGER",
                "description": "Per historical_map animate: anno iniziale richiesto.",
            },
            "end_year": {
                "type": "INTEGER",
                "description": "Per historical_map animate: anno finale richiesto.",
            },
            "speed": {
                "type": "NUMBER",
                "description": "Per animate: secondi per snapshot (da 0.5 a 30).",
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


def _attach_to_existing_job(process: subprocess.Popen[str]) -> None:
    """Keep the MCP Node child in the same kill-on-close job as Vite."""
    if os.name != "nt" or _job_handle is None or _job_kernel is None:
        return
    import ctypes
    from ctypes import wintypes

    _job_kernel.AssignProcessToJobObject.argtypes = [
        wintypes.HANDLE,
        wintypes.HANDLE,
    ]
    _job_kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    process_handle = wintypes.HANDLE(int(process._handle))
    if not _job_kernel.AssignProcessToJobObject(_job_handle, process_handle):
        raise ctypes.WinError(ctypes.get_last_error())


def _close_job_handle() -> None:
    global _job_handle, _job_kernel
    if _job_handle is not None and _job_kernel is not None:
        _job_kernel.CloseHandle(_job_handle)
    _job_handle = None
    _job_kernel = None


# GEV lifecycle hook
def start() -> None:
    _startup_finished.clear()
    try:
        _start_runtime()
    finally:
        _startup_finished.set()


def _start_runtime() -> None:
    """Install GEV dependencies if needed and start its local Vite server."""
    global _output_reader, _process, _started, _mcp_client, _mcp_start_error

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
        _mcp_start_error = None
        mcp_cli = GEV_DIR / "server" / "mcp" / "stdio.js"
        if not mcp_cli.is_file():
            _mcp_start_error = f"GEV MCP entrypoint not found: {mcp_cli}"
            _log(f"GEV MCP: avvio non riuscito: {_mcp_start_error}")
        else:
            try:
                mcp_client = McpStdioClient(
                    [node_exe, str(mcp_cli), "--api-base", GEV_HEALTH_URL],
                    GEV_DIR,
                    _log,
                    process_started=_attach_to_existing_job,
                )
                mcp_client.start()
                _mcp_client = mcp_client
            except Exception as exc:
                _mcp_start_error = str(exc)
                _log(f"GEV MCP: avvio non riuscito: {_mcp_start_error}")
        _log(f"GEV: pronto su {GEV_HEALTH_URL}")


# GEV lifecycle hook
def stop() -> None:
    """Stop the local GEV subprocess; repeated calls are harmless."""
    global _process, _started, _output_reader, _mcp_client

    with _process_lock:
        mcp_client = _mcp_client
        _mcp_client = None
        if mcp_client is not None:
            try:
                mcp_client.stop()
            except Exception as exc:
                _log(f"GEV MCP: arresto non riuscito: {exc}")
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


def get_extra_tool_declarations() -> list[dict]:
    """Expose the local GEV MCP catalog as separate Gemini function tools."""
    if not _startup_finished.wait(INSTALL_TIMEOUT_SEC + STARTUP_TIMEOUT_SEC + 30):
        raise TimeoutError("GEV MCP startup did not finish before the declaration deadline")
    if _mcp_client is None:
        if _mcp_start_error:
            raise RuntimeError(f"GEV MCP unavailable: {_mcp_start_error}")
        return []

    declarations = []
    for tool in _mcp_client.tools:
        try:
            parameters = to_gemini_schema(tool["inputSchema"])
            declarations.append({
                "name": f"gev_mcp_{tool['name']}",
                "description": tool["description"],
                "parameters": parameters,
            })
        except (KeyError, TypeError, ValueError) as exc:
            _log(f"GEV MCP: schema non esposto per '{tool.get('name')}': {exc}")
    return declarations


def run_extra_tool(tool_name: str, parameters: dict, player=None) -> str:
    """Call one namespaced GEV MCP tool and return its summary and data."""
    prefix = "gev_mcp_"
    if not isinstance(tool_name, str) or not tool_name.startswith(prefix):
        raise ValueError(f"Invalid GEV MCP tool name: {tool_name!r}")
    if not isinstance(parameters, dict):
        raise TypeError("GEV MCP arguments must be an object")
    client = _mcp_client
    if client is None:
        detail = _mcp_start_error or "MCP client is not running"
        raise McpClientError(f"GEV MCP unavailable: {detail}")

    mcp_tool_name = tool_name[len(prefix):]
    if not any(tool["name"] == mcp_tool_name for tool in client.tools):
        raise McpClientError(f"Unknown GEV MCP tool: {mcp_tool_name}")
    try:
        result = client.call_tool(mcp_tool_name, parameters)
    except (McpClientError, TimeoutError) as exc:
        _log(f"GEV MCP: chiamata '{mcp_tool_name}' fallita: {exc}")
        return f"GEV non è riuscito a eseguire '{mcp_tool_name}': {exc}"
    return tool_result_text(mcp_tool_name, result)


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

    allowed_actions = {"open", "track", "layer", "reset", "annotate", "historical_map"}
    if action not in allowed_actions:
        log_message(f"GEV: azione sconosciuta '{action}'")
        return f"Non riconosco l'azione GEV '{action}', signore."

    params: dict[str, object]
    if action in {"open", "reset"}:
        params = {}
    elif action == "track":
        target_type = parameters.get("target_type")
        if not isinstance(target_type, str) or target_type not in {"flight", "satellite"}:
            return "Per tracciare un oggetto mi serve il tipo (flight o satellite), signore."
        target_id = parameters.get("target_id")
        if not isinstance(target_id, str) or not target_id.strip():
            target_description, missing = {
                "flight": ("un volo", "il codice"),
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
    elif action == "historical_map":
        command = parameters.get("command")
        if command == "show":
            year = parameters.get("year")
            if (
                not isinstance(year, int)
                or isinstance(year, bool)
                or abs(year) > _MAX_SAFE_JS_INTEGER
            ):
                return "Per mostrare una mappa storica mi serve un anno intero, signore."
            params = {"command": "show", "year": year}
        elif command == "animate":
            start_year = parameters.get("start_year")
            end_year = parameters.get("end_year")
            if any(
                not isinstance(value, int) or isinstance(value, bool)
                or abs(value) > _MAX_SAFE_JS_INTEGER
                for value in (start_year, end_year)
            ):
                return "Per avviare l'animazione mi servono anno iniziale e finale, signore."
            speed = parameters.get("speed", 3)
            if (
                not isinstance(speed, (int, float))
                or isinstance(speed, bool)
                or not 0.5 <= speed <= 30
                or not math.isfinite(speed)
            ):
                return "La velocità deve essere compresa tra 0.5 e 30 secondi per snapshot, signore."
            if start_year > end_year:
                return "L'anno iniziale non può essere successivo a quello finale, signore."
            params = {
                "command": "animate",
                "start_year": start_year,
                "end_year": end_year,
                "speed": speed,
            }
        elif command in {"stop", "clear"}:
            params = {"command": command}
        else:
            return "Per la mappa storica scelga show, animate, stop oppure clear, signore."
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
    elif action == "historical_map":
        details = f" (command={params['command']})"
    log_message(f"GEV: invio azione '{action}'{details}")

    if action == "open":
        return "Apro God's Eye View, signore."
    if action == "track":
        target_name = {
            "flight": "il volo",
            "satellite": "il satellite",
        }[params["target_type"]]
        return f"Traccio {target_name} {params['target_id']}, signore."
    if action == "layer":
        verb = "Attivo" if params["enabled"] else "Disattivo"
        return f"{verb} il layer {params['layer']}, signore."
    if action == "reset":
        return "Resetto la vista di God's Eye View, signore."
    if action == "historical_map":
        return f"Richiesta mappa storica '{params['command']}' inviata, signore."
    return f"Aggiungo un'annotazione a ({params['lat']}, {params['lon']}), signore."


# GEV lifecycle hook
atexit.register(stop)
