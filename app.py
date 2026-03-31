import argparse
from datetime import datetime
from pathlib import Path
from time import monotonic
from zoneinfo import ZoneInfo

from config.settings import load_settings
from hardware.buttons import ButtonController
from models.mode import AppMode
from renderer.mode_dispatch import render_mode
from services.dashboard_data import build_dashboard_data
from services.mode_state import build_mode_state
from services.mode_state_store import load_persisted_mode_state, save_mode_state
from services.photo_slideshow import advance_photo_if_due, reset_slideshow_timer
from services.refresh_requests import consume_refresh_request
from services.runtime import refresh_app, should_refresh_dashboard_on_idle


def main() -> None:
    parser = argparse.ArgumentParser(description="Render Inky Planner preview images")
    parser.add_argument("--mode", choices=[mode.value for mode in AppMode], help="Render a specific mode")
    parser.add_argument("--render-all", action="store_true", help="Render named previews for all modes")
    parser.add_argument("--preview-only", action="store_true", help="Disable hardware display output even if enabled in settings")
    parser.add_argument("--listen-buttons", action="store_true", help="Listen for GPIO button presses and refresh when mode changes")
    args = parser.parse_args()

    project_root = Path(__file__).parent
    output_dir = project_root / "output"
    settings_path = project_root / "config" / "settings.json"
    settings = load_settings(settings_path)

    should_run_button_listener = (
        args.listen_buttons
        or (
            not args.preview_only
            and not args.mode
            and not args.render_all
        )
    )

    if not args.mode and not args.render_all and not should_run_button_listener:
        refresh_app(settings_path, preview_only=args.preview_only, output_dir=output_dir)
        return

    data = build_dashboard_data(settings_path)
    now = datetime.now(ZoneInfo(settings.weather.timezone))
    selected_mode = AppMode(args.mode) if args.mode else settings.default_preview_mode
    mode_state = build_mode_state(settings, selected_mode, now)
    active_mode = mode_state.resolve_active_mode(now)

    render_mode(active_mode, data, settings, output_dir / "preview.png", debug=False)
    render_mode(active_mode, data, settings, output_dir / "preview_debug.png", debug=True)

    if args.render_all:
        for mode in AppMode:
            render_mode(mode, data, settings, output_dir / f"preview_{mode.value}.png", debug=False)
            render_mode(mode, data, settings, output_dir / f"preview_{mode.value}_debug.png", debug=True)

    if should_run_button_listener:
        last_refresh_at_monotonic = 0.0

        def safe_refresh(*, preview_only: bool, force_hardware: bool) -> bool:
            nonlocal last_refresh_at_monotonic
            try:
                result = refresh_app(
                    settings_path,
                    preview_only=preview_only,
                    force_hardware=force_hardware,
                    output_dir=output_dir,
                )
                last_refresh_at_monotonic = monotonic()
                return True
            except Exception as exc:
                print(f"[app] refresh failed: {exc}")
                return False

        safe_refresh(
            preview_only=args.preview_only,
            force_hardware=not args.preview_only,
        )

        def handle_mode(mode: AppMode) -> None:
            current_time = datetime.now(ZoneInfo(settings.weather.timezone))
            state = build_mode_state(settings, mode, current_time)
            save_mode_state(settings, state)
            if mode == AppMode.PHOTO:
                reset_slideshow_timer(load_settings(settings_path))
            print(f"[buttons] mode change -> {mode.value}")
            print(f"[buttons] refresh starting mode={mode.value}; display update may take a while")
            safe_refresh(
                preview_only=args.preview_only,
                force_hardware=not args.preview_only,
            )

        def handle_idle() -> None:
            current_settings = load_settings(settings_path)
            if consume_refresh_request(current_settings):
                print("[refresh] external request received")
                safe_refresh(preview_only=False, force_hardware=True)
                return

            if args.preview_only:
                return

            now = datetime.now(ZoneInfo(current_settings.weather.timezone))
            mode_state = load_persisted_mode_state(current_settings, now)
            active_mode = mode_state.resolve_active_mode(now)

            if active_mode != mode_state.current_mode:
                print(f"[mode] auto-return -> {active_mode.value}")
                safe_refresh(preview_only=False, force_hardware=True)
                return

            if active_mode == AppMode.PHOTO and advance_photo_if_due(current_settings):
                print("[photo] advance=next")
                safe_refresh(preview_only=False, force_hardware=True)
                return

            if should_refresh_dashboard_on_idle(
                current_settings,
                active_mode,
                last_refresh_monotonic=last_refresh_at_monotonic,
                now_monotonic=monotonic(),
            ):
                print(
                    "[refresh] scheduled dashboard refresh"
                    f" interval_minutes={current_settings.refresh_interval_minutes}"
                )
                safe_refresh(preview_only=False, force_hardware=True)

        controller = ButtonController(on_mode_selected=handle_mode, on_idle=handle_idle)
        started = controller.start()
        if not started:
            print("GPIO button handling unavailable; running without button listener.")
            return
        if not args.listen_buttons:
            print("[buttons] auto-listen enabled for hardware run")
        try:
            controller.run_forever()
        finally:
            controller.close()


if __name__ == "__main__":
    main()
