"""Raspberry Pi Pico MicroPython weather station

1. Copy config_secrets.py.template to config_secrets.py and provide your
   OpenWeatherMap API key and WiFi connection details.
2. Copy config_secrets.py and main.py to your Raspberry Pi Pico
"""

# for display
import ujson
import random
import pimoroni
from picographics import PicoGraphics, DISPLAY_PICO_DISPLAY
from picoscroll import PicoScroll

# for weather
import gc
import network
import urequests

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
    "city": "Hamburg",
    "country_code": "DE",
    "url_template": "http://api.openweathermap.org/data/2.5/weather?q={city},{country_code}&appid={api_key}",
}

LOCAL_JOKE_FILE = "jokes.min.json"

LED_COLOR_IDLE = (0, 0, 10)
LED_COLOR_BUSY = (10, 5, 0)

BUTTON_A = pimoroni.Button(12)
BUTTON_B = pimoroni.Button(13)
BUTTON_X = pimoroni.Button(14)
BUTTON_Y = pimoroni.Button(15)


class Screen:
    def __init__(self, display_config):
        print("Initializing screen...")
        self.display = PicoGraphics(
            display=display_config["display"], rotate=display_config["rotate"]
        )
        self.display.set_font(display_config["font"])
        self.width, self.height = self.display.get_bounds()
        self.pen_white = self.display.create_pen(255, 255, 255)
        self.pen_black = self.display.create_pen(0, 0, 0)
        self.pen_red = self.display.create_pen(255, 0, 0)
        self.font_scale = display_config["font_scale"]
        self.log_font_scale = 0
        self.display.set_backlight(display_config["backlight"])
        self.scroll = PicoScroll()
        self.wrap_pixels = self.width
        self.log_area_height = 16
        self.log_area_y = self.height - self.log_area_height
        self._draw_log_area()

    def draw_text(self, x, y, text):
        print(f"Drawing text at {x}, {y}: {text[0:35]}...")
        self.display.set_pen(self.pen_white)
        self.display.text(text, x, y, self.wrap_pixels, self.font_scale)
        self.display.update()

    def clear(self):
        self.display.clear()

    def update(self):
        self.display.update()

    def set_backlight(self, value):
        self.display.set_backlight(value)

    def get_bounds(self):
        return self.display.get_bounds()

    def create_pen(self, r, g, b):
        return self.display.create_pen(r, g, b)

    def log(self, text):
        print(f"Drawing log text: {text}")
        self.display.set_pen(self.pen_black)
        self.display.rectangle(0, self.log_area_y, self.width, self.log_area_height)
        self.display.set_pen(self.pen_white)
        self.display.text(text, 0, self.log_area_y, self.wrap_pixels, self.log_font_scale)
        self.display.update()

    def _draw_log_area(self):
        self.display.set_pen(self.pen_white)
        self.display.line(0, self.log_area_y - 1, self.width, self.log_area_y)
        self.display.update()


#
# Screen set up, initialize the display
#
print("Starting...")
gc.collect()
screen = Screen(SCREEN_CONFIG)
led = pimoroni.RGBLED(*LED_CONFIG["pins_rgb"])
led.set_rgb(*LED_COLOR_IDLE)
screen.draw_text(0, 0, "Initializing...")


#
# Joke classes
#
class BaseJoke:
    def fetch(self):
        raise NotImplementedError

    def display(self, screen):
        raise NotImplementedError
    
    def _sanitize(self, text):
        # Attempt to convert common unicode characters to ASCII, like quotes, backticks, accents, etc.
        text = text.replace("„", "\"").replace("“", "\"").replace("‚", "'")\
            .replace("‘", "'").replace("’", "'").replace("´", "'")\
            .replace("`", "'").replace("–", "-").replace("—", "-")\
            .replace("…", "...").replace("´", "'")
        # Replace German umlauts with ASCII equivalents
        text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")\
            .replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue")\
            .replace("ß", "ss")
        # Replace french accents with ASCII equivalents
        text = text.replace("à", "a").replace("â", "a").replace("é", "e")\
            .replace("è", "e").replace("ê", "e").replace("ë", "e")\
            .replace("î", "i").replace("ï", "i").replace("ô", "o")\
            .replace("ù", "u").replace("û", "u").replace("ç", "c")
        # Replace Spanish accents with ASCII equivalents
        text = text.replace("á", "a").replace("í", "i").replace("ó", "o")\
            .replace("ú", "u").replace("ñ", "n")
        # Remove any non-ASCII characters
        text = "".join(i for i in text if ord(i) < 128)
        return text


class OnlineGermanPunchlineJoke(BaseJoke):
    """Fetches a joke from the WitzAPI."""
    def __init__(self):
        self.joke = ""
        self.url = 'https://witzapi.de/api/joke'
    
    def fetch(self):
        screen.log("Fetching witz...")
        gc.collect()
        led.set_rgb(*LED_COLOR_BUSY)
        response = urequests.get(self.url)
        json_response = response.json()
        self.joke = self._sanitize(json_response[0]["text"])
        led.set_rgb(*LED_COLOR_IDLE)
    
    def display(self, screen):
        screen.display.set_pen(screen.pen_black)
        screen.display.clear()
        screen.display.set_pen(screen.pen_white)
        screen.draw_text(0, 0, self.joke)
        screen.display.update()


class LocalPunchlineJoke(BaseJoke):
    """Reads a local JSON file for a joke.
    
    Expected format: [["setup", "punchline"], ...]
    """
    def __init__(self, filename):
        self.setup = ""
        self.punchline = ""
        self.filename = filename

    def fetch(self):
        gc.collect()
        screen.log("Reading local joke...")
        led.set_rgb(*LED_COLOR_BUSY)
        with open(self.filename, 'r', encoding="utf-8") as f:
            count_lines = sum(1 for _ in f)
        random_line_number = random.randint(1, count_lines)
        print(f"Reading line {random_line_number} / {count_lines}")
        with open(self.filename, 'r') as f:
            for current_line_number, line in enumerate(f, start=1):
                if current_line_number == random_line_number:
                    joke = ujson.loads(line)
                    self.setup = self._sanitize(joke[0])
                    self.punchline = self._sanitize(joke[1])
                    led.set_rgb(*LED_COLOR_IDLE)
                    break

    def display(self, screen):
        screen.display.set_pen(screen.pen_black)
        screen.display.clear()
        screen.display.set_pen(screen.pen_white)
        screen.draw_text(0, 0, self.setup + "\n---\n" + self.punchline)
        screen.display.update()

#
# Weather class
#
class Weather:
    def __init__(self, config, api_key):
        self.city = config["city"]
        self.country_code = config["country_code"]
        self.url_template = config["url_template"]
        self.api_key = api_key
        self.weather_data = None

    def get_weather(self, screen):
        """ Get weather data from OpenWeatherMap"""
        # Sample response:
        #   {
        #     "coord": {"lon": 10, "lat": 53.55},
        #     "weather": [
        #       { "id": 800, "main": "Clear", "description": "clear sky", "icon": "01d" }
        #     ],
        #     "base": "stations",
        #     "main": {
        #       "temp": 283.56,
        #       "feels_like": 282.8,
        #       "temp_min": 282.56,
        #       "temp_max": 284.98,
        #       "pressure": 1017,
        #       "humidity": 82
        #     },
        #     "visibility": 10000,
        #     "wind": {"speed": 3.6, "deg": 250},
        #     "clouds": {"all": 0},
        #     "dt": 1718259937,
        #     "sys": { "type": 1, "id": 1263, "country": "DE", "sunrise": 1718247029, "sunset": 1718308194 },
        #     "timezone": 7200,
        #     "id": 2911298,
        #     "name": "Hamburg",
        #     "cod": 200
        #   }
        url = self.url_template.format(
            city=self.city,
            country_code=self.country_code,
            api_key=self.api_key,
        )
        redacted_url = url.replace(self.api_key, "<REDACTED>")
        screen.log(f"Requesting weather data from {redacted_url}")
        try:
            gc.collect()
            response = urequests.get(url)
        except Exception as e:
            screen.log(f"Error: {e}")
            return
        print(response)
        return response.json()

    def display(self, screen):
        screen.display.clear()
        screen.draw_text(0, 0, "Location: " + self.weather_data['name'])
        screen.draw_text(0, 16, "Temperature: " + str(self.weather_data['main']['temp']) + "°C")
        screen.draw_text(0, 32, "Humidity: " + str(self.weather_data['main']['humidity']) + "%")
        screen.draw_text(0, 48, "Pressure: " + str(self.weather_data['main']['pressure']) + " hPa")
        screen.display.update()


# weather = Weather(WEATHER_CONFIG, OPENWEATHERMAP_API_KEY)
# weather.get_weather(screen)
# weather.display(screen)

# Initial joke fetch
online_german_joke = OnlineGermanPunchlineJoke()
local_joke = LocalPunchlineJoke(LOCAL_JOKE_FILE)
local_joke.fetch()
local_joke.display(screen)

#
# WiFi setup
#
screen.log("Reading secrets")
led.set_rgb(*LED_COLOR_BUSY)
try:
    from config_secrets import OPENWEATHERMAP_API_KEY, WIFI_SSID, WIFI_PASS
except ImportError as exc:
    print(
        "Error: Please provide your OpenWeatherMap API key and WiFi connection details in config_secrets.py"
    )
    raise ImportError from exc

station = network.WLAN(network.STA_IF)
station.active(True)
screen.log(f"Connecting to WiFi {WIFI_SSID}")
station.connect(WIFI_SSID, WIFI_PASS)

while station.isconnected() is False:
    pass

screen.log(f"Connected to WiFi {WIFI_SSID}")
screen.log(str(station.ifconfig()))
led.set_rgb(*LED_COLOR_IDLE)

# Main loop
while True:
    if BUTTON_Y.read():
        local_joke.fetch()
        local_joke.display(screen)
    if BUTTON_X.read():
        online_german_joke.fetch()
        online_german_joke.display(screen)


# TODO: Sleep most of the time, wake up every hour to fetch data
# TODO: Refresh weather on Y
# TODO: Turn screen on for a bit on any button press
# TODO: Rotate screen on A or B
