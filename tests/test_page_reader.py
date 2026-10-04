import ast
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from core.page_reader import (
    MAX_CHUNK_CHARS,
    MAX_PAGE_CHARS,
    PageSpeechWorker,
    prepare_page_text,
)


def test_prepare_page_text_rejects_empty_or_non_text():
    with pytest.raises(ValueError, match="no readable text"):
        prepare_page_text(" \n\t ")
    with pytest.raises(TypeError, match="Page text must be text"):
        prepare_page_text(None)


def test_prepare_page_text_collapses_whitespace_and_splits_chunks():
    plan = prepare_page_text("First\tparagraph.\n\n" + "word " * 300)

    assert len(plan.chunks) > 1
    assert all(0 < len(chunk) <= MAX_CHUNK_CHARS for chunk in plan.chunks)
    assert "  " not in " ".join(plan.chunks)
    assert not plan.truncated


def test_prepare_page_text_caps_extremely_long_pages():
    plan = prepare_page_text("word " * 10_000)

    assert plan.truncated
    assert sum(map(len, plan.chunks)) <= MAX_PAGE_CHARS
    assert all(len(chunk) <= MAX_CHUNK_CHARS for chunk in plan.chunks)
    assert "page text truncated" in " ".join(plan.chunks)


def test_page_speech_worker_stops_active_backend_promptly():
    started = threading.Event()
    cancelled = threading.Event()

    class BlockingBackend:
        def speak(self, text):
            started.set()
            cancelled.wait(3)

        def cancel(self):
            cancelled.set()

    worker = PageSpeechWorker(backend_factory=BlockingBackend)
    worker.start("A page with enough readable text.")
    assert started.wait(1)

    start_time = time.monotonic()
    assert worker.stop()
    assert worker.wait(2)

    assert time.monotonic() - start_time < 2
    assert cancelled.is_set()
    assert not worker.is_running


def test_pyttsx3_backend_cancel_does_not_wait_for_speak_lock():
    from core.accessibility import Pyttsx3Backend

    started = threading.Event()
    cancelled = threading.Event()

    class EngineRecorder:
        def say(self, text):
            pass

        def runAndWait(self):
            started.set()
            cancelled.wait(0.8)

        def stop(self):
            cancelled.set()

    backend = Pyttsx3Backend.__new__(Pyttsx3Backend)
    backend._engine = EngineRecorder()
    thread = threading.Thread(target=backend.speak, args=("test",), daemon=True)
    thread.start()
    assert started.wait(1)

    start_time = time.monotonic()
    backend.cancel()
    elapsed = time.monotonic() - start_time
    thread.join(1)

    assert elapsed < 0.5
    assert cancelled.is_set()
    assert not thread.is_alive()


def test_pyttsx3_interruptible_loop_keeps_engine_calls_on_worker_thread():
    from core.accessibility import Pyttsx3Backend

    started = threading.Event()
    stop_event = threading.Event()
    owner_threads = []

    class ExternalLoopEngine:
        def __init__(self):
            self.busy = True

        def _record(self):
            owner_threads.append(threading.get_ident())

        def say(self, text):
            self._record()

        def startLoop(self, use_driver_loop):
            self._record()

        def isBusy(self):
            self._record()
            return self.busy

        def iterate(self):
            self._record()
            started.set()

        def stop(self):
            self._record()
            self.busy = False

        def endLoop(self):
            self._record()

    backend = Pyttsx3Backend.__new__(Pyttsx3Backend)
    backend._engine = ExternalLoopEngine()
    thread = threading.Thread(
        target=backend.speak_interruptibly,
        args=("test", stop_event),
        daemon=True,
    )
    thread.start()
    assert started.wait(1)
    stop_event.set()
    thread.join(1)

    assert not thread.is_alive()
    assert len(set(owner_threads)) == 1


def test_page_speech_worker_rejects_overlapping_reads():
    started = threading.Event()
    cancelled = threading.Event()

    class BlockingBackend:
        def speak(self, text):
            started.set()
            cancelled.wait(3)

        def cancel(self):
            cancelled.set()

    worker = PageSpeechWorker(backend_factory=BlockingBackend)
    worker.start("First page.")
    assert started.wait(1)
    with pytest.raises(RuntimeError, match="already in progress"):
        worker.start("Second page.")
    worker.stop()
    assert worker.wait(2)


def test_page_speech_worker_surfaces_backend_initialization_errors():
    errors = []

    def fail_factory():
        raise RuntimeError("speech engine unavailable")

    worker = PageSpeechWorker(backend_factory=fail_factory, on_error=errors.append)
    worker.start("A readable page.")

    assert worker.wait(2)
    assert errors == ["Page speech failed: speech engine unavailable"]


def test_page_speech_worker_signals_audio_arbitration_lifecycle():
    states = []

    class ImmediateBackend:
        def speak(self, text):
            pass

        def cancel(self):
            pass

    worker = PageSpeechWorker(
        backend_factory=ImmediateBackend,
        on_started=lambda: states.append(True),
        on_finished=lambda: states.append(False),
    )
    worker.start("A page.")

    assert worker.wait(2)
    assert states == [True, False]


def test_ui_page_read_and_stop_requests_use_qt_signals():
    from ui import JarvisUI

    class SignalRecorder:
        def __init__(self):
            self.emitted = 0

        def emit(self):
            self.emitted += 1

    read_signal = SignalRecorder()
    stop_signal = SignalRecorder()
    ui = JarvisUI.__new__(JarvisUI)
    ui._win = SimpleNamespace(
        _browser_read_page_sig=read_signal,
        _browser_stop_reading_sig=stop_signal,
    )

    ui.read_page_aloud()
    ui.stop_reading()

    assert read_signal.emitted == 1
    assert stop_signal.emitted == 1


def test_read_page_slot_extracts_dom_text_asynchronously():
    from ui import MainWindow

    browser_panel = object()
    calls = []

    class StackRecorder:
        def currentWidget(self):
            return browser_panel

    class PageRecorder:
        def runJavaScript(self, script, callback):
            calls.append((script, callback))

    def page_text_callback(value):
        return value

    audio_states = []

    class SignalRecorder:
        def emit(self, value):
            audio_states.append(value)

    logs = []
    window = SimpleNamespace(
        _main_content_stack=StackRecorder(),
        _browser_panel=browser_panel,
        _browser_page=PageRecorder(),
        _on_browser_page_text=page_text_callback,
        _page_read_pending=False,
        _page_reader=SimpleNamespace(is_running=False),
        _page_reader_audio_sig=SignalRecorder(),
        _log_sig=SimpleNamespace(emit=logs.append),
    )

    MainWindow._read_page_aloud(window)

    assert calls[0][0] == (
        "document.body ? document.body.innerText.slice(0, 20001) : ''"
    )
    assert calls[0][1] is page_text_callback
    assert window._page_read_pending
    assert audio_states == [True]

    MainWindow._stop_page_reading(window)
    calls[0][1]("late page result")
    assert not window._page_read_pending
    assert audio_states == [True, False]


def test_page_reader_tools_are_declared_with_empty_argument_sets():
    main_file = Path(__file__).resolve().parents[1] / "main.py"
    module = ast.parse(main_file.read_text(encoding="utf-8"))
    declarations_assignment = next(
        node
        for node in module.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "TOOL_DECLARATIONS"
            for target in node.targets
        )
    )
    tools = {
        item["name"]: item for item in ast.literal_eval(declarations_assignment.value)
    }

    assert tools["read_page"]["parameters"]["required"] == []
    assert tools["stop_reading"]["parameters"]["required"] == []
