#!/usr/bin/env bash
set -euo pipefail

echo "---------------------------------------"
echo " Inky Planner Setup"
echo "---------------------------------------"

if [[ "${EUID}" -eq 0 ]]; then
  echo "ERROR: Do not run this script with sudo."
  echo "Run: bash setup.sh"
  exit 1
fi

SETUP_BRANCH="main"
REPO_BRANCH="${INKY_PLANNER_BRANCH:-$SETUP_BRANCH}"
REPO_URL="${INKY_PLANNER_REPO_URL:-https://github.com/Canterrain/Inky-Planner.git}"
TARGET_DIR="${INKY_PLANNER_DIR:-$HOME/inky-planner}"

PROJECT_ROOT=""
SERVICE_NAME="inky-planner.service"
WEB_SERVICE_NAME="inky-planner-web.service"
LEGACY_SERVICE_NAME="family-planner-inky.service"
LEGACY_WEB_SERVICE_NAME="family-planner-inky-web.service"
RUN_USER="$(id -un)"
RUN_GROUP="$(id -gn)"
REBOOT_REQUIRED=0

require_command() {
  local command_name="$1"
  local package_hint="$2"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "ERROR: Missing required command '$command_name' ($package_hint)." >&2
    exit 1
  fi
}

has_project_checkout() {
  local candidate="$1"
  [[ -f "$candidate/app.py" ]] && \
    [[ -f "$candidate/requirements.txt" ]] && \
    [[ -f "$candidate/systemd/$SERVICE_NAME" ]] && \
    [[ -d "$candidate/config" ]]
}

package_exists() {
  local package_name="$1"
  apt-cache show "$package_name" >/dev/null 2>&1
}

append_if_available() {
  local package_name="$1"
  if package_exists "$package_name"; then
    OPTIONAL_PACKAGES+=("$package_name")
  else
    echo "Skipping unavailable package: $package_name"
  fi
}

append_first_available() {
  local chosen=""
  for package_name in "$@"; do
    if package_exists "$package_name"; then
      chosen="$package_name"
      break
    fi
  done

  if [[ -n "$chosen" ]]; then
    OPTIONAL_PACKAGES+=("$chosen")
  else
    echo "Skipping optional package group; none available: $*"
  fi
}

remove_legacy_service() {
  local legacy_name="$1"
  local legacy_target="/etc/systemd/system/$legacy_name"

  if sudo systemctl list-unit-files "$legacy_name" >/dev/null 2>&1 || [[ -f "$legacy_target" ]]; then
    echo "Removing legacy service $legacy_name"
    sudo systemctl disable --now "$legacy_name" >/dev/null 2>&1 || true
    if [[ -f "$legacy_target" ]]; then
      sudo rm -f "$legacy_target"
    fi
  fi
}

bootstrap_repo_if_needed() {
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

  if has_project_checkout "$script_dir"; then
    PROJECT_ROOT="$script_dir"
    return
  fi

  echo
  echo "Preparing Inky Planner files..."
  sudo apt-get update
  sudo apt-get install -y git ca-certificates

  if has_project_checkout "$TARGET_DIR"; then
    PROJECT_ROOT="$TARGET_DIR"
    if [[ -d "$PROJECT_ROOT/.git" ]]; then
      echo "Updating existing checkout in $PROJECT_ROOT"
      git -C "$PROJECT_ROOT" fetch origin "$REPO_BRANCH"
      git -C "$PROJECT_ROOT" checkout "$REPO_BRANCH"
      git -C "$PROJECT_ROOT" pull --ff-only origin "$REPO_BRANCH"
    else
      echo "Using existing project files in $PROJECT_ROOT"
    fi
  else
    if [[ -e "$TARGET_DIR" ]]; then
      echo "ERROR: $TARGET_DIR exists but is not a complete Inky Planner checkout." >&2
      echo "Move it aside or set INKY_PLANNER_DIR to an empty folder, then rerun setup." >&2
      exit 1
    fi

    echo "Cloning Inky Planner from GitHub..."
    git clone --branch "$REPO_BRANCH" --single-branch "$REPO_URL" "$TARGET_DIR"
    PROJECT_ROOT="$TARGET_DIR"
  fi

  echo "Re-launching setup from $PROJECT_ROOT"
  exec bash "$PROJECT_ROOT/setup.sh"
}

enable_pi_interface() {
  local name="$1"
  local getter="$2"
  local setter="$3"

  if ! sudo raspi-config nonint "$getter" >/dev/null 2>&1; then
    echo "WARNING: Could not query Raspberry Pi interface state for $name."
    echo "Make sure $name is enabled manually if setup continues."
    return
  fi

  local current_state
  current_state="$(sudo raspi-config nonint "$getter")"
  if [[ "$current_state" != "0" ]]; then
    echo "Enabling $name..."
    sudo raspi-config nonint "$setter" 0
    REBOOT_REQUIRED=1
  else
    echo "$name already enabled."
  fi
}

ensure_boot_config_line() {
  local line="$1"
  local config_file="$2"
  if ! grep -Fqx "$line" "$config_file" 2>/dev/null; then
    echo "Adding '$line' to $config_file"
    echo "$line" | sudo tee -a "$config_file" >/dev/null
    REBOOT_REQUIRED=1
  else
    echo "$line already present in $config_file"
  fi
}

require_command python3 "python3"
require_command sudo "sudo"

bootstrap_repo_if_needed

SERVICE_TEMPLATE="$PROJECT_ROOT/systemd/$SERVICE_NAME"
SERVICE_TARGET="/etc/systemd/system/$SERVICE_NAME"
WEB_SERVICE_TEMPLATE="$PROJECT_ROOT/systemd/$WEB_SERVICE_NAME"
WEB_SERVICE_TARGET="/etc/systemd/system/$WEB_SERVICE_NAME"

require_command git "git"

echo
echo "Installing system packages..."
sudo apt-get update

REQUIRED_PACKAGES=(
  git \
  python3 \
  python3-pip \
  python3-venv \
  python3-libgpiod \
  python3-spidev \
  python3-smbus \
  python3-numpy \
  i2c-tools \
  avahi-daemon \
  avahi-utils \
  liblcms2-2 \
  libcairo2 \
  libgdk-pixbuf-2.0-0 \
  libffi8 \
  libjpeg62-turbo \
  libwebp7 \
  zlib1g \
  libharfbuzz0b \
  libfribidi0 \
  shared-mime-info \
  fonts-dejavu-core
)

OPTIONAL_PACKAGES=()
append_first_available libgpiod3 libgpiod2
append_first_available libopenjp2-7
append_first_available libtiff6 libtiff5
append_first_available libfreetype6 libfreetype6-dev libfreetype-dev

sudo apt-get install -y "${REQUIRED_PACKAGES[@]}" "${OPTIONAL_PACKAGES[@]}"

require_command raspi-config "raspi-config"

echo
echo "Enabling Raspberry Pi interfaces..."
enable_pi_interface "SPI" get_spi do_spi
enable_pi_interface "I2C" get_i2c do_i2c

BOOT_CONFIG="/boot/firmware/config.txt"
if [[ -f "$BOOT_CONFIG" ]]; then
  ensure_boot_config_line "dtoverlay=spi0-0cs" "$BOOT_CONFIG"
else
  echo "WARNING: $BOOT_CONFIG not found. If Inky reports chip-select conflicts,"
  echo "add 'dtoverlay=spi0-0cs' manually after setup."
fi

echo
echo "Preparing Python environment..."
chmod +x "$PROJECT_ROOT/setup.sh" "$PROJECT_ROOT/scripts/run_app.sh" "$PROJECT_ROOT/scripts/run_web.sh"
sudo chmod 755 "$PROJECT_ROOT/scripts/run_app.sh" "$PROJECT_ROOT/scripts/run_web.sh"
if [[ ! -d "$PROJECT_ROOT/.venv" ]]; then
  python3 -m venv --system-site-packages "$PROJECT_ROOT/.venv"
else
  echo "Reusing existing virtual environment."
fi

source "$PROJECT_ROOT/.venv/bin/activate"
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r "$PROJECT_ROOT/requirements.txt"
python -m pip install inky gpiod

echo
echo "Creating runtime directories..."
mkdir -p "$PROJECT_ROOT/output" "$PROJECT_ROOT/state"

if [[ ! -f "$PROJECT_ROOT/config/settings.json" ]]; then
  echo "ERROR: Missing config/settings.json" >&2
  exit 1
fi

echo
echo "Installing systemd service..."
if [[ ! -f "$SERVICE_TEMPLATE" ]]; then
  echo "ERROR: Missing service template at $SERVICE_TEMPLATE" >&2
  exit 1
fi
if [[ ! -f "$WEB_SERVICE_TEMPLATE" ]]; then
  echo "ERROR: Missing web service template at $WEB_SERVICE_TEMPLATE" >&2
  exit 1
fi

remove_legacy_service "$LEGACY_SERVICE_NAME"
remove_legacy_service "$LEGACY_WEB_SERVICE_NAME"

tmp_service="$(mktemp)"
sed \
  -e "s|__PROJECT_ROOT__|$PROJECT_ROOT|g" \
  -e "s|__RUN_USER__|$RUN_USER|g" \
  -e "s|__RUN_GROUP__|$RUN_GROUP|g" \
  "$SERVICE_TEMPLATE" > "$tmp_service"
sudo cp "$tmp_service" "$SERVICE_TARGET"
rm -f "$tmp_service"

tmp_web_service="$(mktemp)"
sed \
  -e "s|__PROJECT_ROOT__|$PROJECT_ROOT|g" \
  -e "s|__RUN_USER__|$RUN_USER|g" \
  -e "s|__RUN_GROUP__|$RUN_GROUP|g" \
  "$WEB_SERVICE_TEMPLATE" > "$tmp_web_service"
sudo cp "$tmp_web_service" "$WEB_SERVICE_TARGET"
rm -f "$tmp_web_service"

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl enable avahi-daemon
sudo systemctl enable "$WEB_SERVICE_NAME"

if [[ "$REBOOT_REQUIRED" -eq 0 ]]; then
  echo "Starting service now..."
  sudo systemctl restart "$SERVICE_NAME"
  sudo systemctl restart avahi-daemon
  sudo systemctl restart "$WEB_SERVICE_NAME"
else
  echo "Services enabled. They will start automatically after reboot."
fi

echo
echo "Setup complete."
echo "Project root: $PROJECT_ROOT"
echo "Service name: $SERVICE_NAME"
echo "Web service name: $WEB_SERVICE_NAME"
echo "Config file: $PROJECT_ROOT/config/settings.json"
echo "Web UI: http://$(hostname).local:8080"
echo
echo "Important settings to review:"
echo "  - calendar feed URLs in the Calendars section"
echo "  - weather location / timezone / temperature unit"
echo "  - photo_folder"
echo "  - language"
echo

if [[ "$REBOOT_REQUIRED" -eq 1 ]]; then
  echo "A reboot is required to finish enabling SPI/I2C and boot config changes."
  read -r -p "Reboot now? [y/N] " reboot_reply
  case "$reboot_reply" in
    [Yy]|[Yy][Ee][Ss])
      sudo reboot
      ;;
    *)
      echo "Reboot later with: sudo reboot"
      ;;
  esac
else
  echo "No reboot required."
  echo "Check service status with: sudo systemctl status $SERVICE_NAME"
fi
