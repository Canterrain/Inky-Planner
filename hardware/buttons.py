from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from models.mode import AppMode


BUTTON_PIN_MAP = {
    5: ("A", AppMode.DASHBOARD),
    6: ("B", AppMode.TODAY),
    16: ("C", AppMode.TOMORROW),
    24: ("D", AppMode.PHOTO),
}


@dataclass
class ButtonController:
    on_mode_selected: Callable[[AppMode], None]
    on_idle: Callable[[], None] | None = None
    chip_name: str = "/dev/gpiochip4"
    debounce_seconds: float = 0.2
    _running: bool = field(default=False, init=False)
    _request: object | None = field(default=None, init=False)
    _last_press_at: dict[int, float] = field(default_factory=dict, init=False)
    _gpiod: object | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self.available = False
        try:
            import gpiod  # type: ignore
        except ImportError:
            self._gpiod = None
            return

        self._gpiod = gpiod
        self.available = True

    def start(self) -> bool:
        if not self.available or self._gpiod is None:
            print("[buttons] gpiod unavailable; buttons disabled")
            return False

        try:
            settings = self._line_settings()
            config = {line: settings for line in BUTTON_PIN_MAP}
            self._request = self._gpiod.request_lines(
                self.chip_name,
                consumer="inky-planner",
                config=config,
            )
        except Exception as exc:
            print(f"[buttons] failed to request lines on {self.chip_name}: {exc}")
            self._request = None
            return False

        self._running = True
        print(f"[buttons] listening on {self.chip_name} for {len(BUTTON_PIN_MAP)} buttons")
        return True

    def run_forever(self) -> None:
        if not self._running or self._request is None:
            return

        while self._running:
            try:
                if not self._request.wait_edge_events(timeout=1.0):
                    if self.on_idle is not None:
                        self.on_idle()
                    continue

                for event in self._request.read_edge_events():
                    self._handle_event(event)
            except Exception as exc:
                print(f"[buttons] event loop error: {exc}")
                time.sleep(0.5)

    def close(self) -> None:
        self._running = False
        request = self._request
        self._request = None
        if request is not None:
            request.release()

    def _handle_event(self, event) -> None:
        line = int(event.line_offset)
        if line not in BUTTON_PIN_MAP:
            return

        now = time.monotonic()
        last = self._last_press_at.get(line, 0.0)
        if now - last < self.debounce_seconds:
            return
        self._last_press_at[line] = now

        button_name, mode = BUTTON_PIN_MAP[line]
        print(f"[buttons] pressed button={button_name} gpio={line}")
        self.on_mode_selected(mode)
        self._discard_queued_events()

    def _line_settings(self):
        assert self._gpiod is not None
        return self._gpiod.LineSettings(
            direction=self._gpiod.line.Direction.INPUT,
            bias=self._gpiod.line.Bias.PULL_UP,
            edge_detection=self._gpiod.line.Edge.FALLING,
        )

    def _discard_queued_events(self) -> None:
        if self._request is None:
            return

        discarded = 0
        try:
            while self._request.wait_edge_events(timeout=0):
                events = list(self._request.read_edge_events())
                discarded += len(events)
        except Exception as exc:
            print(f"[buttons] queue drain error: {exc}")
            return

        if discarded > 0:
            print(f"[buttons] ignored queued presses count={discarded}")
