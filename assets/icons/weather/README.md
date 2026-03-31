# Weather Icon Assets

Place weather icon files in this directory to replace the built-in placeholder rendering.

Supported filenames:

- `clear-day.png` or `clear-day.svg`
- `clear-night.png` or `clear-night.svg`
- `partlycloudy-day.png` or `partlycloudy-day.svg`
- `partlycloudy-night.png` or `partlycloudy-night.svg`
- `cloudy.png` or `cloudy.svg`
- `fog.png` or `fog.svg`
- `rain.png` or `rain.svg`
- `showers-day.png` or `showers-day.svg`
- `showers-night.png` or `showers-night.svg`
- `thunderstorm.png` or `thunderstorm.svg`
- `snow.png` or `snow.svg`
- `sleet.png` or `sleet.svg`
- `thundersnow.png` or `thundersnow.svg`

PNG files are loaded directly. SVG files are rasterized when `cairosvg` is installed.

If an icon file is missing, the renderer falls back automatically to the existing simple placeholder icon for that icon name.
