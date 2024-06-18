"""Raspberry Pi Pico MicroPython weather station

1. Copy config_secrets.py.template to config_secrets.py and provide your
   OpenWeatherMap API key and WiFi connection details.
2. Copy config_secrets.py and main.py to your Raspberry Pi Pico
"""
# Openweather never actually worked, so using open-meteo instead
import ujson
import random
import pimoroni
import gc
import network
import urequests
import uasyncio
from picographics import PicoGraphics, DISPLAY_PICO_DISPLAY

SCREEN_CONFIG = {
    "display": DISPLAY_PICO_DISPLAY,
    "rotate": 0,
    "backlight": 0.5,
    "font_scale": 2,
    "font": "bitmap6",
}

LED_CONFIG = {
    "pins_rgb": (6, 7, 8),
}

WEATHER_CONFIG = {
    "lat": 53.55,  # Latitude of Hamburg
    "lon": 9.99,   # Longitude of Hamburg
    "current": "temperature_2m,weather_code",
    "hourly": "temperature_2m,precipitation_probability,precipitation,weather_code",
    "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_hours,precipitation_probability_max",
    "timezone": "Europe/Berlin",
    "forecast_days": 1,
    "url_template": "https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current={current}&hourly={hourly}&daily={daily}&timezone={timezone}&forecast_days={forecast_days}",
}

LOCAL_JOKE_FILE = "jokes.min.json"

LED_COLOR_IDLE = (0, 0, 10)
LED_COLOR_BUSY = (10, 5, 0)

BUTTON_A = pimoroni.Button(12)
BUTTON_B = pimoroni.Button(13)
BUTTON_X = pimoroni.Button(14)
BUTTON_Y = pimoroni.Button(15)

# Initialize display
display = PicoGraphics(display=SCREEN_CONFIG["display"], rotate=SCREEN_CONFIG["rotate"])
display.set_font(SCREEN_CONFIG["font"])
display.set_backlight(SCREEN_CONFIG["backlight"])
width, height = display.get_bounds()
pen_white = display.create_pen(255, 255, 255)
pen_black = display.create_pen(0, 0, 0)
pen_red = display.create_pen(255, 0, 0)
font_scale = SCREEN_CONFIG["font_scale"]

# Initialize LED
led = pimoroni.RGBLED(*LED_CONFIG["pins_rgb"])
led.set_rgb(*LED_COLOR_IDLE)


def draw_text(x, y, text):
    display.set_pen(pen_white)
    display.text(text, x, y, width, font_scale)
    display.update()


def clear_screen():
    display.set_pen(pen_black)
    display.clear()
    display.update()


def log(text):
    print(f"LOG: {text}")
    display.set_pen(pen_black)
    display.rectangle(0, height - 16, width, 16)
    display.set_pen(pen_white)
    display.text(text, 0, height - 16, width, 1)
    display.update()


class Echo:
    def __init__(self):
        self.url = "https://echo.free.beeceptor.com"
        self.error = None
        self.response = None

    async def fetch(self):
        gc.collect()
        led.set_rgb(*LED_COLOR_BUSY)
        try:
            response = await uasyncio.get_event_loop().create_task(self.fetch_url())
            self.response = response.text
        except Exception as e:
            self.error = e
        finally:
            led.set_rgb(*LED_COLOR_IDLE)

    async def fetch_url(self):
        log(f"Fetching {self.url}")
        response = urequests.get(self.url)
        return response
    
    def display(self):
        clear_screen()
        if self.error:
            draw_text(0, 0, f"Error: {self.error}")
            log(f"Error: {self.error}")
            return
        draw_text(0, 0, self.response.text if self.response else "No response")


class BaseJoke:
    def __init__(self):
        pass

    async def fetch(self):
        raise NotImplementedError

    def display(self):
        raise NotImplementedError

    def _sanitize(self, text):
        # Attempt to convert common unicode characters to ASCII, like quotes, backticks, accents, etc.
        replacements = {
            "–": "-", "—": "-", "…": "...", "‘": "'", "’": "'", "‚": "'",
            "“": '"', "„": '"', "`": "'", "´": "'",
            "á": "a", "à": "a", "â": "a", "ä": "ae", "Ä": "Ae", "ç": "c",
            "é": "e", "è": "e", "ê": "e", "ë": "e", "í": "i", "î": "i",
            "ï": "i", "ñ": "n", "ó": "o", "ô": "o", "ö": "oe", "Ö": "Oe",
            "ß": "ss", "ú": "u", "ù": "u", "û": "u", "ü": "ue", "Ü": "Ue",
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        return "".join(i for i in text if ord(i) < 128)


class OnlineGermanPunchlineJoke(BaseJoke):
    def __init__(self):
        super().__init__()
        self.joke = None
        self.url = "https://witzapi.de/api/joke"
        self.error = None

    async def fetch_url(self):
        response = urequests.get(self.url)
        return response

    async def fetch(self):
        gc.collect()
        led.set_rgb(*LED_COLOR_BUSY)
        try:
            log(f"Fetching {self.url}")
            response = await uasyncio.get_event_loop().create_task(self.fetch_url())
            json_response = ujson.loads(response.text)
            self.joke = self._sanitize(json_response[0]["text"])
        except Exception as e:
            self.error = e
        finally:
            led.set_rgb(*LED_COLOR_IDLE)

    def display(self):
        clear_screen()
        if self.error:
            draw_text(0, 0, f"Error: {self.error}")
            log(f"Error: {self.error}")
            return
        draw_text(0, 0, self.joke)


class LocalPunchlineJoke(BaseJoke):
    def __init__(self, filename):
        super().__init__()
        self.setup = ""
        self.punchline = ""
        self.filename = filename
        self.error = None

    async def fetch(self):
        gc.collect()
        log("Reading local joke...")
        led.set_rgb(*LED_COLOR_BUSY)
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                jokes = [line.strip() for line in f]
            random_joke = random.choice(jokes)
            joke = ujson.loads(random_joke)
            self.setup = self._sanitize(joke[0])
            self.punchline = self._sanitize(joke[1])
        except Exception as e:
            self.error = e
        finally:
            led.set_rgb(*LED_COLOR_IDLE)

    def display(self):
        clear_screen()
        if self.error:
            draw_text(0, 0, f"Error: {self.error}")
            log(f"Error: {self.error}")
            return
        draw_text(0, 0, self.setup + "\n---\n" + self.punchline)


class Weather:
    def __init__(self, config):
        self.config = config
        self.url_template = config["url_template"]
        self.url = self.url_template.format(**config)
        self.weather_data = None
        self.request_headers = {"User-Agent": "curl/8.6.0"}
        self.error = None

    async def fetch_url(self):
        log(f"Fetching {self.url}")
        response = urequests.get(self.url, headers=self.request_headers)
        return response
    
    async def fetch(self):
        gc.collect()
        led.set_rgb(*LED_COLOR_BUSY)
        try:
            response = await uasyncio.get_event_loop().create_task(self.fetch_url())
            self.weather_data = ujson.loads(response.text)
        except Exception as e:
            self.error = e
        finally:
            led.set_rgb(*LED_COLOR_IDLE)

    def display(self):
        clear_screen()
        if self.error:
            draw_text(0, 0, f"Error: {self.error}")
            log(f"Error: {self.error}")
            return
        draw_text(0, 0, f"{self.weather_data["current"]["time"]}")
        draw_text(0, 16, self._wmo_weather_code_string(self.weather_data["current"]["weather_code"]))
        draw_text(0, 32, f"Temp: {self.weather_data["current"]["temperature_2m"]}°C")
        draw_text(0, 48, f"Rain: {self.weather_data["daily"]["precipitation_hours"][0]}mm")
        draw_text(0, 64, f"Rain: {self.weather_data["daily"]["precipitation_probability_max"][0]}%")
        display.update()

    @staticmethod
    def _wmo_weather_code_string(code):
        codes = {
            0: "Clear",
            1: "Partly Cloudy",
            2: "Cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Fog+",
            51: "Light Showers",
            53: "Showers",
            55: "Heavy Showers",
            56: "Freezing drizzle",
            57: "Freezing drizzle+",
            61: "Light rain",
            63: "Rain",
            65: "Heavy rain",
            66: "Freezing rain",
            67: "Freezing rain+",
            71: "Light snow showers",
            73: "Snow showers",
            75: "Heavy snow showers",
            77: "Sleet showers",
            80: "Light snow",
            81: "Snow",
            83: "Heavy snow",
            85: "Sleet",
            86: "Sleet+",
            95: "Thunderstorm",
            96: "Thunderstorm hail",
            99: "Thunderstorm hail+",
        }
        return codes.get(code, f"Unknown weather code ({code})")


async def connect_wifi():
    log("Reading secrets")
    led.set_rgb(*LED_COLOR_BUSY)
    try:
        from config_secrets import WIFI_SSID, WIFI_PASS
    except ImportError as exc:
        log(
            "Error: Please provide your WiFi connection details in config_secrets.py"
        )
        raise ImportError from exc

    station = network.WLAN(network.STA_IF)
    station.active(True)
    log(f"Connecting to WiFi {WIFI_SSID}")
    station.connect(WIFI_SSID, WIFI_PASS)

    while not station.isconnected():
        await uasyncio.sleep(1)

    log(f"Connected to WiFi {WIFI_SSID}")
    log(str(station.ifconfig()))
    led.set_rgb(*LED_COLOR_IDLE)


async def main():
    local_joke = LocalPunchlineJoke(LOCAL_JOKE_FILE)
    online_german_joke = OnlineGermanPunchlineJoke()
    weather = Weather(WEATHER_CONFIG)
    echo = Echo()

    await local_joke.fetch()
    local_joke.display()

    wifi_task = uasyncio.get_event_loop().create_task(connect_wifi())
    network_connected = False

    while True:
        if BUTTON_Y.read():
            await local_joke.fetch()
            local_joke.display()
        elif BUTTON_X.read() and network_connected:
            await online_german_joke.fetch()
            online_german_joke.display()
        elif BUTTON_A.read() and network_connected:
            await weather.fetch()
            weather.display()
        elif BUTTON_B.read() and network_connected:
            await echo.fetch()
            echo.display()

        if not network_connected and wifi_task.done():
            network_connected = True

        await uasyncio.sleep(0.2)


try:
    uasyncio.run(main())
except KeyboardInterrupt:
    pass
