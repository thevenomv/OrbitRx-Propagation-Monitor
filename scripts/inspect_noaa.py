"""One-off NOAA API probe for development."""

import json
import urllib.request

URLS = [
    ("https://services.swpc.noaa.gov/products/solar-flux-5-minute.json", "solar-flux"),
    ("https://services.swpc.noaa.gov/products/sunspot-number.json", "sunspot"),
]

for url, name in URLS:
    data = json.loads(urllib.request.urlopen(url).read())
    print(name, "len", len(data))
    print("first", data[0])
    print("last", data[-1])
