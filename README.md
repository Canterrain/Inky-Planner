# Inky Planner

A clean, glanceable daily planner for e-paper displays.

Designed to show exactly what matters today: your schedule, your next event, and just enough context to keep you on track without turning into a cluttered dashboard.

Built for Raspberry Pi and Pimoroni Inky displays.

## What This Is

Most digital planners try to do too much.

This one does not.

Inky Planner is built around a simple idea:

You should be able to walk by your display and immediately understand your day.

No scrolling. No interaction. No noise.

Just:

- today's date
- your events
- what's next
- and whether you actually have free time

## How It Thinks

Instead of dumping a calendar on screen, Inky Planner prioritizes information:

- Next Event stays front and center
- free time is surfaced when it matters
- weather appears when it adds value
- busy and light days are reflected without over-explaining

The goal is clarity, not completeness.

## Hardware

Designed for:

- Raspberry Pi, tested on Pi 4 and Pi Zero 2 W
- Pimoroni Inky displays in the Impression and Spectra family

Other displays may work, but this project is tuned specifically for Inky hardware.

## Features

- clean, high-contrast layouts optimized for e-paper
- dashboard, today, and tomorrow planner views
- photo slideshow mode
- local Flask config UI
- guided ICS and iCalendar calendar setup
- weather via Open-Meteo
- English, German, and French support
- automatic startup with systemd

## Installation

Recommended on Raspberry Pi:

```bash
cd ~
wget https://raw.githubusercontent.com/Canterrain/Inky-Planner/main/setup.sh -O inky-planner-setup.sh
bash inky-planner-setup.sh
```

If you prefer a full local checkout:

```bash
git clone https://github.com/Canterrain/Inky-Planner.git
cd Inky-Planner
bash setup.sh
```

The setup script will:

- download or update the project in `~/inky-planner` when run standalone
- install dependencies
- configure Raspberry Pi display support
- enable SPI and I2C if needed
- install the planner and web services
- prepare the system for auto-start

## Running

After setup, the planner runs automatically on boot.

The local settings UI is available at:

```text
http://<hostname>.local:8080/settings
```

If needed, you can manually check or restart it with:

```bash
sudo systemctl status inky-planner.service
sudo systemctl status inky-planner-web.service
sudo systemctl restart inky-planner.service
sudo systemctl restart inky-planner-web.service
```

## Philosophy

This project is intentionally opinionated.

It is not trying to be:

- a full calendar replacement
- a configurable dashboard builder
- a widget playground

It is a daily companion display.

Something you glance at while making coffee and immediately know:

"What's happening today, and what do I need to care about?"

## Related Projects

If you like this, you might also like:

- [weather-display](https://github.com/Canterrain/weather-display), an under-cabinet clock and weather dashboard
