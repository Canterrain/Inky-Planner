from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from config.settings import AppSettings, load_settings
from hardware.conversion import prepare_hardware_image, prepare_passthrough_image
from hardware.display import DisplayUpdateResult, InkyDisplayOutput
from models.dashboard import DashboardData
from models.mode import AppMode
from renderer.mode_dispatch import render_mode, render_mode_image, render_mode_scene
from services.dashboard_cache import get_dashboard_data_cached
from services.mode_state import build_mode_state
from services.mode_state_store import load_persisted_mode_state, resolve_and_persist_mode, save_mode_state


@dataclass
class RefreshResult:
    mode: AppMode
    preview_paths: list[Path]
    display_result: DisplayUpdateResult | None


def refresh_app(
    settings_path: str | Path,
    *,
    mode_override: AppMode | None = None,
    persist_override: bool = False,
    preview_only: bool = False,
    force_hardware: bool = False,
    output_dir: str | Path | None = None,
) -> RefreshResult:
    settings = load_settings(settings_path)
    now = datetime.now(ZoneInfo(settings.weather.timezone))
    output_root = Path(output_dir) if output_dir else settings.project_root / "output"

    if mode_override is not None:
        state = build_mode_state(settings, mode_override, now)
        if persist_override:
            save_mode_state(settings, state)
    else:
        state = load_persisted_mode_state(settings, now)
        state = resolve_and_persist_mode(settings, state, now)
        save_mode_state(settings, state)

    data: DashboardData | None = None
    if state.current_mode != AppMode.PHOTO:
        data = get_dashboard_data_cached(settings_path)

    scene = render_mode_scene(
        state.current_mode,
        data,
        settings,
        debug=False,
        hardware_target=(settings.hardware_display_enabled or force_hardware) and not preview_only,
    )
    image = scene.image
    planner_spectra_mode = settings.spectra_mode if settings.spectra_mode != "off" else "atkinson"
    active_spectra_mode = "inky_auto" if state.current_mode == AppMode.PHOTO else planner_spectra_mode
    print(f"[render] mode={state.current_mode.value} spectra_mode={active_spectra_mode}")
    preview_paths: list[Path] = []

    if settings.preview_output_enabled:
        preview_paths.append(render_mode(state.current_mode, data, settings, output_root / "preview.png", debug=False))
        preview_paths.append(render_mode(state.current_mode, data, settings, output_root / "preview_debug.png", debug=True))
        print(f"[preview] wrote={','.join(str(path) for path in preview_paths)}")
    else:
        print("[preview] skipped (preview_output_enabled=false)")

    if settings.palette_debug_enabled:
        if state.current_mode == AppMode.PHOTO:
            debug_conversion = prepare_passthrough_image(
                image,
                target_size=(800, 480),
                output_dir=output_root,
                palette_debug_enabled=True,
            )
        else:
            debug_conversion = prepare_hardware_image(
                image,
                target_size=(800, 480),
                output_dir=output_root,
                spectra_mode=planner_spectra_mode,
                palette_debug_enabled=True,
                weather_overlay=scene.weather_overlay,
            )
        print(f"[spectra] wrote={','.join(str(path) for path in debug_conversion.artifacts.written_paths())}")

    display_result = None
    if (settings.hardware_display_enabled or force_hardware) and not preview_only:
        print("[display] attempting hardware update")
        display = InkyDisplayOutput(
            spectra_mode=planner_spectra_mode,
            palette_debug_enabled=settings.palette_debug_enabled,
            output_dir=output_root,
        )
        if state.current_mode == AppMode.PHOTO:
            display_result = display.show_photo_image(image, saturation=0.5)
        else:
            display_result = display.show_image(image, weather_overlay=scene.weather_overlay)
        print(f"[display] updated={display_result.updated} reason={display_result.reason}")
    elif (settings.hardware_display_enabled or force_hardware) and preview_only:
        print("[display] skipped (preview-only mode)")
    else:
        print("[display] skipped (hardware_display_enabled=false)")

    return RefreshResult(mode=state.current_mode, preview_paths=preview_paths, display_result=display_result)
