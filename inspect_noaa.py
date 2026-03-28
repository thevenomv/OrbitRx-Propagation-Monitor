import urllib.request, json
urls = [
    ('https://services.swpc.noaa.gov/products/solar-flux-5-minute.json', 'solar-flux'),
    ('https://services.swpc.noaa.gov/products/sunspot-number.json', 'sunspot')
]
for url,name in urls:
    r = urllib.request.urlopen(url).read()
    data = json.loads(r)
    print(name, 'len', len(data))
    print('first', data[0])
    print('last', data[-1])
