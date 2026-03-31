from pathlib import Path

from config.settings import AppSettings
from models.dashboard import DashboardData
from models.mode import AppMode
from renderer.dashboard import DashboardRenderer
from renderer.detail import DayDetailRenderer
from renderer.photo import PhotoModeRenderer
from renderer.scene import RenderedScene
from services.photo_slideshow import current_photo


def render_mode_image(
    mode: AppMode,
    data: DashboardData | None,
    settings: AppSettings,
    *,
    debug: bool = False,
    hardware_target: bool = False,
):
    if mode == AppMode.DASHBOARD:
        if data is None:
            raise ValueError("Dashboard data is required for dashboard mode")
        return DashboardRenderer(debug=debug, hardware_target=hardware_target).render(data)

    if mode == AppMode.TODAY:
        if data is None:
            raise ValueError("Dashboard data is required for today mode")
        return DayDetailRenderer(day_index=0, title_prefix="Today", debug=debug, hardware_target=hardware_target).render(data)

    if mode == AppMode.TOMORROW:
        if data is None:
            raise ValueError("Dashboard data is required for tomorrow mode")
        return DayDetailRenderer(day_index=1, title_prefix="Tomorrow", debug=debug, hardware_target=hardware_target).render(data)

    photo_path = current_photo(settings)
    if photo_path is not None:
        print(f"[photo] selected={photo_path}")
    else:
        print(f"[photo] selected=None folder={settings.photo_folder}")
    return PhotoModeRenderer(debug=debug).render(photo_path)


def render_mode_scene(
    mode: AppMode,
    data: DashboardData | None,
    settings: AppSettings,
    *,
    debug: bool = False,
    hardware_target: bool = False,
) -> RenderedScene:
    if mode == AppMode.DASHBOARD:
        if data is None:
            raise ValueError("Dashboard data is required for dashboard mode")
        return DashboardRenderer(debug=debug, hardware_target=hardware_target).render_scene(data)

    if mode == AppMode.TODAY:
        if data is None:
            raise ValueError("Dashboard data is required for today mode")
        return DayDetailRenderer(day_index=0, title_prefix="Today", debug=debug, hardware_target=hardware_target).render_scene(data)

    if mode == AppMode.TOMORROW:
        if data is None:
            raise ValueError("Dashboard data is required for tomorrow mode")
        return DayDetailRenderer(day_index=1, title_prefix="Tomorrow", debug=debug, hardware_target=hardware_target).render_scene(data)

    photo_path = current_photo(settings)
    if photo_path is not None:
        print(f"[photo] selected={photo_path}")
    else:
        print(f"[photo] selected=None folder={settings.photo_folder}")
    return RenderedScene(image=PhotoModeRenderer(debug=debug).render(photo_path))


def render_mode(
    mode: AppMode,
    data: DashboardData | None,
    settings: AppSettings,
    output_path: str | Path,
    *,
    debug: bool = False,
) -> Path:
    if mode == AppMode.DASHBOARD:
        if data is None:
            raise ValueError("Dashboard data is required for dashboard mode")
        return DashboardRenderer(debug=debug).render_to_file(data, output_path)

    if mode == AppMode.TODAY:
        if data is None:
            raise ValueError("Dashboard data is required for today mode")
        return DayDetailRenderer(day_index=0, title_prefix="Today", debug=debug).render_to_file(data, output_path)

    if mode == AppMode.TOMORROW:
        if data is None:
            raise ValueError("Dashboard data is required for tomorrow mode")
        return DayDetailRenderer(day_index=1, title_prefix="Tomorrow", debug=debug).render_to_file(data, output_path)

    photo_path = current_photo(settings)
    if photo_path is not None:
        print(f"[photo] selected={photo_path}")
    else:
        print(f"[photo] selected=None folder={settings.photo_folder}")
    return PhotoModeRenderer(debug=debug).render_to_file(photo_path, output_path)
