"""Bounded page-text preparation and cancellable background speech."""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from typing import Callable, Protocol


MAX_PAGE_CHARS = 20_000
MAX_CHUNK_CHARS = 800
_TRUNCATION_MARKER = " [page text truncated]"


class SpeechBackend(Protocol):
    def speak(self, text: str) -> None: ...

    def cancel(self) -> None: ...


@dataclass(frozen=True)
class PageReadPlan:
    chunks: tuple[str, ...]
    truncated: bool


def _split_long_piece(text: str, limit: int) -> list[str]:
    pieces = []
    while len(text) > limit:
        split_at = text.rfind(" ", 0, limit + 1)
        if split_at <= 0:
            split_at = limit
        pieces.append(text[:split_at].strip())
        text = text[split_at:].strip()
    if text:
        pieces.append(text)
    return pieces


def prepare_page_text(value: object) -> PageReadPlan:
    if not isinstance(value, str):
        raise TypeError("Page text must be text")
    text = re.sub(r"\s+", " ", value).strip()
    if not text:
        raise ValueError("The active page contains no readable text")

    truncated = len(text) > MAX_PAGE_CHARS
    if truncated:
        allowed = MAX_PAGE_CHARS - len(_TRUNCATION_MARKER)
        prefix = text[:allowed].rsplit(" ", 1)[0].rstrip()
        if not prefix:
            prefix = text[:allowed]
        text = prefix + _TRUNCATION_MARKER

    chunks: list[str] = []
    current = ""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    for sentence in sentences:
        if len(sentence) > MAX_CHUNK_CHARS:
            if current:
                chunks.append(current)
                current = ""
            long_pieces = _split_long_piece(sentence, MAX_CHUNK_CHARS)
            chunks.extend(long_pieces[:-1])
            current = long_pieces[-1] if long_pieces else ""
        elif not current:
            current = sentence
        elif len(current) + 1 + len(sentence) <= MAX_CHUNK_CHARS:
            current = f"{current} {sentence}"
        else:
            chunks.append(current)
            current = sentence

    if current:
        chunks.append(current)
    return PageReadPlan(tuple(chunks), truncated)


def _default_backend_factory() -> SpeechBackend:
    from core.accessibility import Pyttsx3Backend

    return Pyttsx3Backend()


class PageSpeechWorker:
    """Speak one bounded page at a time outside the GUI thread."""

    def __init__(
        self,
        backend_factory: Callable[[], SpeechBackend] = _default_backend_factory,
        on_error: Callable[[str], None] | None = None,
        on_started: Callable[[], None] | None = None,
        on_finished: Callable[[], None] | None = None,
    ) -> None:
        self._backend_factory = backend_factory
        self._on_error = on_error or (
            lambda message: print(f"[ScreenReader] {message}", flush=True)
        )
        self._on_started = on_started or (lambda: None)
        self._on_finished = on_finished or (lambda: None)
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop_event: threading.Event | None = None
        self._backend: SpeechBackend | None = None

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._thread is not None and self._thread.is_alive()

    def start(self, page_text: object) -> PageReadPlan:
        plan = prepare_page_text(page_text)
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                raise RuntimeError("A page read is already in progress")
            stop_event = threading.Event()
            thread = threading.Thread(
                target=self._run,
                args=(plan.chunks, stop_event),
                name="jarvis-page-reader",
                daemon=True,
            )
            self._stop_event = stop_event
            self._thread = thread
            thread.start()
        return plan

    def stop(self) -> bool:
        with self._lock:
            thread = self._thread
            stop_event = self._stop_event
            backend = self._backend
        if thread is None or not thread.is_alive() or stop_event is None:
            return False
        stop_event.set()
        interruptible_speak = (
            getattr(backend, "speak_interruptibly", None) if backend else None
        )
        if backend is not None and not callable(interruptible_speak):
            backend.cancel()
        return True

    def wait(self, timeout: float | None = None) -> bool:
        """Wait for worker completion; intended for tests and non-GUI callers."""
        with self._lock:
            thread = self._thread
        if thread is None:
            return True
        thread.join(timeout)
        return not thread.is_alive()

    def _run(
        self,
        chunks: tuple[str, ...],
        stop_event: threading.Event,
    ) -> None:
        backend: SpeechBackend | None = None
        try:
            backend = self._backend_factory()
            with self._lock:
                self._backend = backend
            if stop_event.is_set():
                backend.cancel()
                return
            self._on_started()
            interruptible_speak = getattr(backend, "speak_interruptibly", None)
            for chunk in chunks:
                if stop_event.is_set():
                    break
                if callable(interruptible_speak):
                    interruptible_speak(chunk, stop_event)
                else:
                    backend.speak(chunk)
        except Exception as exc:
            self._on_error(f"Page speech failed: {exc}")
        finally:
            with self._lock:
                if self._backend is backend:
                    self._backend = None
            self._on_finished()
