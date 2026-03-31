from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from flask import Flask, flash, get_flashed_messages, redirect, render_template, request, send_file, send_from_directory, session, url_for

from config.settings import load_settings, parse_settings
from services.calendar_service import fetch_calendar_days, inspect_calendar_sources
from services.config_backups import create_settings_backup, export_settings_filename, import_settings_backup
from services.config_service import apply_geocoding_result, build_web_settings_update, load_raw_settings, save_raw_settings
from services.geocoding_service import GeocodingResult, search_locations
from services.photo_service import delete_all_photos, delete_photo, list_photos, resolve_photo_folder, save_uploaded_photos
from services.refresh_requests import request_refresh
from services.text import translate
from services.weather_service import fetch_weather_days


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates")
    app.secret_key = "inky-planner-local-config"
    project_root = Path(__file__).resolve().parent.parent
    settings_path = project_root / "config" / "settings.json"
    photo_page_size = 12
    hostname = os.uname().nodename.split(".")[0]
    access_url = f"http://{hostname.lower()}.local:8080"

    def settings_language(settings) -> str:
        return str(getattr(settings, "language", "en") or "en")

    def render_settings_page(
        *,
        message: str | None = None,
        error: str | None = None,
        settings_override: dict | None = None,
        geocode_results: list[GeocodingResult] | None = None,
        pending_settings_json: str | None = None,
        calendar_test_results=None,
        photo_page: int = 1,
    ):
        raw_settings = settings_override or load_raw_settings(settings_path)
        language = str(raw_settings.get("language", "en"))
        calendar_test_results = calendar_test_results or []
        calendar_test_status_by_id = {result.get("source_id", ""): result for result in calendar_test_results if result.get("source_id")}
        photo_files = list_photos(raw_settings.get("photo_folder", "assets/photos"), project_root)
        total_photo_pages = max(1, ((len(photo_files) - 1) // photo_page_size) + 1) if photo_files else 1
        current_photo_page = min(max(photo_page, 1), total_photo_pages)
        start_index = (current_photo_page - 1) * photo_page_size
        end_index = start_index + photo_page_size
        return render_template(
            "settings.html",
            settings=raw_settings,
            message=message,
            error=error,
            flashes=get_flashed_messages(with_categories=True),
            geocode_results=geocode_results or [],
            pending_settings_json=pending_settings_json,
            calendar_test_results=calendar_test_results,
            calendar_test_status_by_id=calendar_test_status_by_id,
            photo_files=photo_files,
            photo_files_preview=photo_files[start_index:end_index],
            photo_page=current_photo_page,
            total_photo_pages=total_photo_pages,
            hostname=hostname,
            access_url=access_url,
            t=lambda key, **kwargs: translate(language, key, **kwargs),
        )

    @app.get("/")
    def index():
        return redirect(url_for("settings_page"))

    @app.get("/settings")
    def settings_page():
        parsed_results = session.pop("calendar_test_results", [])
        message = session.pop("calendar_test_message", None)
        preview_settings_json = session.pop("preview_settings_json", None)
        geocode_results_raw = session.pop("geocode_results", [])
        geocode_results = [
            GeocodingResult(
                name=str(item.get("name", "")).strip(),
                latitude=float(item.get("latitude", 0)),
                longitude=float(item.get("longitude", 0)),
                timezone=str(item.get("timezone", "")).strip() or None,
                country=str(item.get("country", "")).strip() or None,
                admin1=str(item.get("admin1", "")).strip() or None,
                country_code=str(item.get("country_code", "")).strip() or None,
            )
            for item in geocode_results_raw
        ]
        pending_settings_json = session.pop("pending_settings_json", None)
        photo_page = max(1, int(session.pop("photo_page", 1) or 1))
        settings_override = json.loads(preview_settings_json) if preview_settings_json else None
        return render_settings_page(
            message=message,
            settings_override=settings_override,
            calendar_test_results=parsed_results,
            geocode_results=geocode_results,
            pending_settings_json=pending_settings_json,
            photo_page=photo_page,
        )

    @app.get("/photos/file/<path:filename>")
    def photo_file(filename: str):
        raw_settings = load_raw_settings(settings_path)
        folder = resolve_photo_folder(raw_settings.get("photo_folder", "assets/photos"), project_root, create=False)
        if folder is None:
            return ("Not found", 404)
        return send_from_directory(folder, Path(filename).name)

    @app.get("/config/export")
    def export_config():
        backup_path = create_settings_backup(settings_path, reason="manual-export")
        return send_file(
            backup_path,
            mimetype="application/json",
            as_attachment=True,
            download_name=export_settings_filename(),
        )

    @app.post("/config/import")
    def import_config():
        try:
            upload = request.files.get("settings_file")
            if upload is None or not upload.filename:
                return render_settings_page(error=translate(load_raw_settings(settings_path).get("language", "en"), "ui.error.import_choose_file"))
            backup_path = import_settings_backup(upload.stream, settings_path)
            language = load_raw_settings(settings_path).get("language", "en")
            flash(
                translate(language, "ui.message.import_success", name=backup_path.name),
                "message",
            )
            return redirect(url_for("settings_page"))
        except Exception as exc:
            return render_settings_page(error=translate(load_raw_settings(settings_path).get("language", "en"), "ui.error.import_failed", error=exc))

    @app.post("/settings")
    def save_settings():
        try:
            raw_settings = load_raw_settings(settings_path)
            updated = build_web_settings_update(raw_settings, request.form)
            save_raw_settings(settings_path, updated)
            settings = load_settings(settings_path)
            request_refresh(settings)
        except Exception as exc:
            return render_settings_page(error=translate(str(load_raw_settings(settings_path).get("language", "en")), "ui.error.save_settings", error=exc))
        flash(translate(settings_language(settings), "ui.message.settings_saved"), "message")
        return redirect(url_for("settings_page"))

    @app.post("/actions/preview-language")
    def action_preview_language():
        try:
            raw_settings = load_raw_settings(settings_path)
            updated = build_web_settings_update(raw_settings, request.form)
            session["preview_settings_json"] = json.dumps(updated)
            session["photo_page"] = max(1, int(request.form.get("photo_page", "1") or "1"))
            return redirect(url_for("settings_page"))
        except Exception as exc:
            language = str(request.form.get("language", "en") or "en")
            return render_settings_page(error=translate(language, "ui.error.save_settings", error=exc))

    @app.post("/actions/refresh")
    def action_refresh():
        try:
            settings = load_settings(settings_path)
            request_refresh(settings)
            flash(translate(settings_language(settings), "ui.message.refresh_requested"), "message")
            return redirect(url_for("settings_page"))
        except Exception as exc:
            return render_settings_page(error=translate(load_raw_settings(settings_path).get("language", "en"), "ui.error.refresh", error=exc))

    @app.post("/actions/test-calendar")
    def action_test_calendar():
        try:
            if request.form:
                settings = parse_settings(build_web_settings_update(load_raw_settings(settings_path), request.form), settings_path)
            else:
                settings = load_settings(settings_path)
            now = datetime.now()
            days = fetch_calendar_days(settings, now.date())
            source_results = inspect_calendar_sources(settings, now.date())
            session["calendar_test_message"] = translate(settings_language(settings), "ui.message.calendar_ok", count=len(days))
            session["calendar_test_results"] = [
                {
                    "label": result.label,
                    "source_type": result.source_type,
                    "source_url": result.source_url,
                    "success": result.success,
                    "event_count": result.event_count,
                    "preview_lines": result.preview_lines,
                    "error": result.error,
                }
                for result in source_results
            ]
            return redirect(url_for("settings_page"))
        except Exception as exc:
            return render_settings_page(error=translate(load_raw_settings(settings_path).get("language", "en"), "ui.error.calendar_test", error=exc))

    @app.post("/actions/test-calendar-feed")
    def action_test_calendar_feed():
        try:
            source_id = request.form.get("test_source_id", "").strip()
            settings = parse_settings(build_web_settings_update(load_raw_settings(settings_path), request.form), settings_path)
            now = datetime.now()
            source_results = inspect_calendar_sources(settings, now.date(), source_id=source_id)
            if not source_results:
                return render_settings_page(error=translate(settings_language(settings), "ui.error.calendar_feed_missing"))
            result = source_results[0]
            status = translate(settings_language(settings), "ui.status.ok") if result.success else translate(settings_language(settings), "ui.problem")
            session["calendar_test_message"] = translate(settings_language(settings), "ui.message.feed_status", label=result.label, status=status)
            session["calendar_test_results"] = [
                {
                    "source_id": result.source_id,
                    "label": result.label,
                    "source_type": result.source_type,
                    "source_url": result.source_url,
                    "success": result.success,
                    "event_count": result.event_count,
                    "preview_lines": result.preview_lines,
                    "error": result.error,
                }
            ]
            return redirect(url_for("settings_page"))
        except Exception as exc:
            return render_settings_page(error=translate(load_raw_settings(settings_path).get("language", "en"), "ui.error.calendar_feed_test", error=exc))

    @app.post("/actions/test-weather")
    def action_test_weather():
        try:
            settings = load_settings(settings_path)
            days = fetch_weather_days(settings)
            flash(translate(settings_language(settings), "ui.message.weather_ok", count=len(days)), "message")
            return redirect(url_for("settings_page"))
        except Exception as exc:
            return render_settings_page(error=translate(load_raw_settings(settings_path).get("language", "en"), "ui.error.weather_test", error=exc))

    @app.post("/actions/geocode")
    def action_geocode():
        try:
            raw_settings = load_raw_settings(settings_path)
            updated = build_web_settings_update(raw_settings, request.form)
            weather = updated.get("weather", {})
            query = str(weather.get("location_query", "")).strip()
            country_code = str(weather.get("country_code", "")).strip()
            results = search_locations(query, language=str(updated.get("language", "en")), country_code=country_code, count=5)
            session["calendar_test_results"] = []
            session["calendar_test_message"] = translate(str(updated.get("language", "en")), "ui.message.geocode_found", count=len(results))
            session["geocode_results"] = [
                {
                    "name": result.name,
                    "latitude": result.latitude,
                    "longitude": result.longitude,
                    "timezone": result.timezone,
                    "country": result.country,
                    "admin1": result.admin1,
                    "country_code": result.country_code,
                }
                for result in results
            ]
            session["pending_settings_json"] = json.dumps(updated)
            return redirect(url_for("settings_page"))
        except Exception as exc:
            return render_settings_page(error=translate(load_raw_settings(settings_path).get("language", "en"), "ui.error.location_lookup", error=exc))

    @app.post("/actions/apply-geocode")
    def action_apply_geocode():
        try:
            pending_settings_json = request.form.get("pending_settings_json", "").strip()
            if pending_settings_json:
                updated = json.loads(pending_settings_json)
            else:
                updated = load_raw_settings(settings_path)

            weather = updated.get("weather", {})
            query = str(weather.get("location_query", "")).strip()
            country_code = str(weather.get("country_code", "")).strip()
            encoded_result = request.form.get("geocode_result_json", "").strip()
            result_payload = json.loads(encoded_result) if encoded_result else {
                "name": str(request.form.get("result_name", "")).strip(),
                "latitude": float(request.form.get("result_latitude", "")),
                "longitude": float(request.form.get("result_longitude", "")),
                "timezone": str(request.form.get("result_timezone", "")).strip() or None,
                "country": str(request.form.get("result_country", "")).strip() or None,
                "admin1": str(request.form.get("result_admin1", "")).strip() or None,
                "country_code": str(request.form.get("result_country_code", "")).strip() or None,
            }
            result = GeocodingResult(
                name=str(result_payload.get("name", "")).strip(),
                latitude=float(result_payload.get("latitude", 0)),
                longitude=float(result_payload.get("longitude", 0)),
                timezone=str(result_payload.get("timezone", "")).strip() or None,
                country=str(result_payload.get("country", "")).strip() or None,
                admin1=str(result_payload.get("admin1", "")).strip() or None,
                country_code=str(result_payload.get("country_code", "")).strip() or None,
            )
            updated = apply_geocoding_result(
                updated,
                location_query=query,
                country_code=country_code,
                result=result,
            )
            save_raw_settings(settings_path, updated)
            language = str(updated.get("language", "en"))
            flash(
                translate(language, "ui.message.location_selected", display_name=result.display_name, latitude=result.latitude, longitude=result.longitude),
                "message",
            )
            return redirect(url_for("settings_page"))
        except Exception as exc:
            return render_settings_page(error=translate(load_raw_settings(settings_path).get("language", "en"), "ui.error.apply_location", error=exc))

    @app.post("/photos/upload")
    def upload_photos():
        try:
            settings = load_settings(settings_path)
            saved = save_uploaded_photos(request.files.getlist("photos"), settings.photo_folder, settings.project_root)
            if not saved:
                return render_settings_page(error=translate(settings.language, "ui.error.no_photo_upload"))
            flash(translate(settings_language(settings), "ui.message.photo_uploaded", count=len(saved)), "message")
            session["photo_page"] = 1
            return redirect(url_for("settings_page"))
        except Exception as exc:
            return render_settings_page(error=translate(load_raw_settings(settings_path).get("language", "en"), "ui.error.photo_upload", error=exc))

    @app.post("/photos/delete")
    def remove_photo():
        try:
            settings = load_settings(settings_path)
            filename = request.form.get("filename", "")
            photo_page = max(1, int(request.form.get("photo_page", "1") or "1"))
            if not delete_photo(settings.photo_folder, settings.project_root, filename):
                return render_settings_page(error=translate(settings_language(settings), "ui.error.photo_delete_one"))
            flash(translate(settings_language(settings), "ui.message.photo_deleted", name=Path(filename).name), "message")
            session["photo_page"] = photo_page
            return redirect(url_for("settings_page"))
        except Exception as exc:
            return render_settings_page(error=translate(load_raw_settings(settings_path).get("language", "en"), "ui.error.photo_delete", error=exc))

    @app.post("/photos/delete-all")
    def remove_all_photos():
        try:
            settings = load_settings(settings_path)
            removed = delete_all_photos(settings.photo_folder, settings.project_root)
            if removed == 0:
                return render_settings_page(error=translate(settings_language(settings), "ui.error.photo_none_to_delete"))
            flash(translate(settings_language(settings), "ui.message.photo_deleted_all", count=removed), "message")
            return redirect(url_for("settings_page"))
        except Exception as exc:
            return render_settings_page(error=translate(load_raw_settings(settings_path).get("language", "en"), "ui.error.photo_delete_all", error=exc))

    @app.post("/photos/page")
    def set_photo_page():
        try:
            photo_page = max(1, int(request.form.get("photo_page", "1") or "1"))
            session["photo_page"] = photo_page
            return redirect(url_for("settings_page"))
        except Exception as exc:
            return render_settings_page(error=translate(load_raw_settings(settings_path).get("language", "en"), "ui.error.photo_page", error=exc))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
