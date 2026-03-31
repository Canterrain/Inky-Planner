# Inky Planner

Python project for rendering a static 800x480 planner dashboard for the Pimoroni Inky Impression 7.3. The app can show a 5-day calendar and forecast dashboard, detail views, and a photo-mode slideshow on the device.

## Current State

The project now includes:

- Raspberry Pi setup via `setup.sh`
- a systemd-managed planner service
- a local Flask config UI at `http://<hostname>.local:8080/settings`
- guided ICS calendar feed setup for Google, Apple, Outlook, and similar providers
- weather setup with Open-Meteo geocoding
- photo uploads and slideshow mode
- settings export/import with automatic pre-import backups

If live calendar or weather fetches fail, the app falls back to local sample data so preview and development workflows still keep working.

## Project Structure

- `app.py`: entry point for render flow, hardware refreshes, and button mode changes
- `config/layout.py`: layout and color constants
- `config/settings.py`: settings loader and validation
- `config/settings.json`: example local configuration
- `hardware/`: Inky display, button, palette, and conversion helpers
- `models/`: typed data models
- `renderer/`: dashboard, detail, and photo rendering
- `scripts/run_app.sh`: stable app launcher
- `scripts/run_web.sh`: stable web UI launcher
- `services/calendar_service.py`: ICS loading, recurrence expansion, and calendar feed testing
- `services/dashboard_data.py`: combines settings, live services, and fallback behavior
- `services/geocoding_service.py`: Open-Meteo location search and matching
- `services/mock_data.py`: fallback sample data
- `services/mode_state.py`: persisted current-mode helpers
- `services/photo_service.py`: uploaded photo storage and management
- `services/photo_slideshow.py`: slideshow order and timing state
- `services/refresh_requests.py`: bridge between the web UI and running planner service
- `services/runtime.py`: render and hardware refresh orchestration
- `services/weather_service.py`: Open-Meteo forecast fetching
- `services/weather_icons.py`: icon naming aligned to local assets
- `systemd/inky-planner.service`: planner service template
- `systemd/inky-planner-web.service`: web UI service template
- `web/`: local Flask config UI
- `assets/icons/weather/`: weather icon assets
- `assets/photos/`: photo-mode image folder
- `assets/sample_family_calendar.ics`: sample calendar feed for local preview
- `tests/`: unit tests

## Key Settings

`config/settings.json` includes:

- `dashboard_title`
- `language`
- `calendar_sources`
- `weather`
- `photo_folder`
- `photo_interval_seconds`
- `photo_shuffle_enabled`
- `refresh_interval_minutes`
- `default_preview_mode`
- `spectra_mode`

Notes:

- `calendar_sources` supports multiple ICS / iCalendar feed URLs.
- `ics_url` still exists for backward compatibility and mirrors the first enabled calendar feed.
- `spectra_mode` defaults to `atkinson` for planner screens.
- photo mode uses its own photo-specific hardware path.
- weather setup can be driven from the web UI using city/state/country lookup.
- preview/debug output generation is off by default for normal Pi use.

## Raspberry Pi Install

On a Raspberry Pi with the Inky Impression attached:

```bash
cd ~
wget https://raw.githubusercontent.com/Canterrain/Inky-Planner/main/setup.sh -O inky-planner-setup.sh
bash inky-planner-setup.sh
```

What `setup.sh` does:

- downloads or updates the project in `~/inky-planner`
- installs required system packages
- creates or updates `.venv`
- installs Python dependencies plus `inky` and `gpiod`
- enables SPI and I2C when needed
- installs and enables `avahi-daemon`
- adds `dtoverlay=spi0-0cs` to `/boot/firmware/config.txt` when needed
- installs and enables the planner and web UI services
- prompts for reboot if hardware changes require it

If you prefer a manual repo checkout for development:

```bash
git clone https://github.com/Canterrain/Inky-Planner.git
cd Inky-Planner
bash setup.sh
```

After reboot, the config UI should be reachable at:

```text
http://<current-hostname>.local:8080/settings
```

For example:

```text
http://inkycal.local:8080/settings
```

Check status:

```bash
sudo systemctl status inky-planner.service
sudo systemctl status inky-planner-web.service
journalctl -u inky-planner.service -n 100 --no-pager
journalctl -u inky-planner-web.service -n 100 --no-pager
```

Restart manually:

```bash
sudo systemctl restart inky-planner.service
sudo systemctl restart inky-planner-web.service
```

## Local Preview Setup

1. Create and activate the virtual environment if needed:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Update `config/settings.json` or use the local web UI to configure:

- calendar feeds
- weather location
- photo folder/slideshow settings
- optional settings export/import backups

4. Generate previews:

```bash
python app.py
```

Useful commands:

```bash
python app.py --mode today
python app.py --mode tomorrow
python app.py --mode photo
python app.py --preview-only
python app.py --render-all
python -m web.app
```

Generated outputs can include:

- `output/preview.png`
- `output/preview_debug.png`
- `output/preview_dashboard.png`
- `output/preview_today.png`
- `output/preview_tomorrow.png`
- `output/preview_photo.png`
- `output/layout_render.png`
- `output/quantized_render.png`
- `output/dithered_render.png`
- `output/hardware_final.png`

Preview/debug images are mainly for development. If you want them during local work, enable:

- `preview_output_enabled`
- `palette_debug_enabled`

5. Run tests:

```bash
python -m unittest discover -s tests
```

## Calendar Setup

The web UI uses ICS / iCalendar feed URLs.

Typical sources:

- Google Calendar: use the calendar's secret iCal address
- Apple Calendar: use a published or shared iCalendar link
- Outlook: publish the calendar and copy the ICS subscription link

Each feed can be:

- labeled
- enabled or disabled
- tested individually

## Weather Setup

The web UI supports:

- city/state/country search
- choosing from multiple geocoding matches
- saving resolved latitude, longitude, and timezone
- testing weather without leaving the settings page

Weather data is fetched from Open-Meteo.

## Photo Mode

Photo mode supports:

- browser uploads
- multiple stored photos
- slideshow interval control
- optional shuffle

When real uploaded photos exist, the sample photo is removed from the active photo folder.

## Config Safety

The web UI action area supports:

- exporting the current settings as JSON
- importing a saved settings JSON file

When settings are imported, the previous config is backed up to `config/backups/` before the new file is applied.
