"""
Download and use a realistic satellite world map from Natural Earth Data
"""

from PIL import Image
Image.MAX_IMAGE_PIXELS = None
import urllib.request
import io

def generate_world_map(width=1600, height=800):
    """
    Download the exact map from Wikimedia URL and save as world_map.jpg.
    """
    map_url = 'https://upload.wikimedia.org/wikipedia/commons/f/f2/Large_World_Map_bright.jpg'
    try:
        print('[*] Downloading requested map from Wikimedia...')
        req = urllib.request.Request(map_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as response:
            img_data = response.read()
        img = Image.open(io.BytesIO(img_data))
        img = img.resize((width, height), Image.Resampling.LANCZOS)
        img.save('world_map.jpg', 'JPEG', quality=95)
        print('[OK] Downloaded and saved world_map.jpg from exact URL')
        return img
    except Exception as e:
        print(f'[ERROR] Could not download the exact map URL: {e}')
        print('[INFO] Falling back to synthetic map generation')
        return generate_synthetic_map(width, height)

def generate_synthetic_map(width=1600, height=800):
    """
    Fallback synthetic map generation with better colors matching satellite imagery.
    """
    from PIL import ImageDraw
    
    # Create ocean background with gradient effect
    img = Image.new('RGB', (width, height), color=(25, 85, 150))  # Ocean blue (satellite style)
    draw = ImageDraw.Draw(img, 'RGBA')
    
    # Better land colors matching satellite imagery
    forest_green = (34, 93, 34)      # Dark forest
    leaf_green = (76, 153, 0)        # Medium green
    tan = (210, 180, 100)            # Deserts/arid regions
    light_green = (144, 193, 82)     # Grasslands
    
    def latlon_to_pixel(lat, lon):
        x = int((lon + 180) / 360.0 * width)
        y = int((height / 2) - (lat / 90.0) * (height / 2))
        return (x, y)
    
    # NORTH AMERICA (with vegetation shading)
    na_points = [
        latlon_to_pixel(70, -130),
        latlon_to_pixel(75, -95),
        latlon_to_pixel(60, -60),
        latlon_to_pixel(45, -50),
        latlon_to_pixel(40, -75),
        latlon_to_pixel(25, -80),
        latlon_to_pixel(20, -85),
        latlon_to_pixel(20, -110),
        latlon_to_pixel(35, -120),
        latlon_to_pixel(50, -125),
        latlon_to_pixel(70, -130),
    ]
    draw.polygon(na_points, fill=leaf_green, outline=(100, 140, 60))
    
    # SOUTH AMERICA
    sa_points = [
        latlon_to_pixel(15, -80),
        latlon_to_pixel(10, -60),
        latlon_to_pixel(0, -55),
        latlon_to_pixel(-5, -40),
        latlon_to_pixel(-15, -60),
        latlon_to_pixel(-30, -65),
        latlon_to_pixel(-45, -72),
        latlon_to_pixel(-30, -75),
        latlon_to_pixel(-10, -75),
        latlon_to_pixel(5, -75),
        latlon_to_pixel(15, -80),
    ]
    draw.polygon(sa_points, fill=forest_green, outline=(100, 140, 60))
    
    # GREENLAND
    greenland_points = [
        latlon_to_pixel(82, -40),
        latlon_to_pixel(80, -15),
        latlon_to_pixel(60, -10),
        latlon_to_pixel(59, -40),
        latlon_to_pixel(82, -40),
    ]
    draw.polygon(greenland_points, fill=light_green, outline=(80, 120, 40))
    
    # EUROPE
    europe_points = [
        latlon_to_pixel(71, -10),
        latlon_to_pixel(70, 20),
        latlon_to_pixel(60, 30),
        latlon_to_pixel(55, 35),
        latlon_to_pixel(50, 35),
        latlon_to_pixel(45, 25),
        latlon_to_pixel(40, 20),
        latlon_to_pixel(40, 5),
        latlon_to_pixel(42, -5),
        latlon_to_pixel(45, -10),
        latlon_to_pixel(50, -5),
        latlon_to_pixel(55, -3),
        latlon_to_pixel(60, 5),
        latlon_to_pixel(71, -10),
    ]
    draw.polygon(europe_points, fill=leaf_green, outline=(100, 140, 60))
    
    # AFRICA (with desert regions)
    africa_points = [
        latlon_to_pixel(38, -5),
        latlon_to_pixel(35, 5),
        latlon_to_pixel(35, 15),
        latlon_to_pixel(30, 25),
        latlon_to_pixel(20, 35),
        latlon_to_pixel(10, 40),
        latlon_to_pixel(5, 35),
        latlon_to_pixel(0, 30),
        latlon_to_pixel(-5, 25),
        latlon_to_pixel(-10, 20),
        latlon_to_pixel(-20, 25),
        latlon_to_pixel(-30, 20),
        latlon_to_pixel(-35, 25),
        latlon_to_pixel(-25, 35),
        latlon_to_pixel(-15, 40),
        latlon_to_pixel(-5, 35),
        latlon_to_pixel(5, 30),
        latlon_to_pixel(10, 15),
        latlon_to_pixel(20, 5),
        latlon_to_pixel(35, 0),
        latlon_to_pixel(38, -5),
    ]
    draw.polygon(africa_points, fill=tan, outline=(150, 120, 60))
    
    # ASIA (with varied terrain)
    asia_points = [
        latlon_to_pixel(72, 40),
        latlon_to_pixel(75, 100),
        latlon_to_pixel(72, 160),
        latlon_to_pixel(65, 180),
        latlon_to_pixel(55, 160),
        latlon_to_pixel(50, 140),
        latlon_to_pixel(45, 135),
        latlon_to_pixel(30, 120),
        latlon_to_pixel(25, 115),
        latlon_to_pixel(15, 105),
        latlon_to_pixel(8, 100),
        latlon_to_pixel(5, 95),
        latlon_to_pixel(10, 90),
        latlon_to_pixel(15, 75),
        latlon_to_pixel(25, 70),
        latlon_to_pixel(35, 70),
        latlon_to_pixel(45, 75),
        latlon_to_pixel(50, 85),
        latlon_to_pixel(55, 95),
        latlon_to_pixel(60, 105),
        latlon_to_pixel(72, 40),
    ]
    draw.polygon(asia_points, fill=leaf_green, outline=(100, 140, 60))
    
    # AUSTRALIA
    australia_points = [
        latlon_to_pixel(-10, 113),
        latlon_to_pixel(-12, 125),
        latlon_to_pixel(-20, 150),
        latlon_to_pixel(-30, 155),
        latlon_to_pixel(-35, 150),
        latlon_to_pixel(-37, 140),
        latlon_to_pixel(-32, 115),
        latlon_to_pixel(-20, 113),
        latlon_to_pixel(-10, 113),
    ]
    draw.polygon(australia_points, fill=tan, outline=(150, 120, 60))
    
    # NEW ZEALAND
    draw.ellipse([
        latlon_to_pixel(-34, 165),
        latlon_to_pixel(-48, 178)
    ], fill=light_green, outline=(80, 120, 40))
    
    # ANTARCTICA
    draw.rectangle([
        (0, int(height * 0.85)),
        (width, height)
    ], fill=(200, 200, 200), outline=(150, 150, 150))
    
    # Gridlines
    line_color = (50, 80, 120, 60)
    for lat in range(-90, 91, 15):
        y = int((height / 2) - (lat / 90.0) * (height / 2))
        draw.line([(0, y), (width, y)], fill=line_color, width=1)
    
    for lon in range(-180, 180, 15):
        x = int((lon + 180) / 360.0 * width)
        draw.line([(x, 0), (x, height)], fill=line_color, width=1)
    
    # Highlighted equator and prime meridian
    equator_y = height // 2
    pm_x = width // 2
    draw.line([(0, equator_y), (width, equator_y)], fill=(100, 200, 255), width=2)
    draw.line([(pm_x, 0), (pm_x, height)], fill=(100, 200, 255), width=2)
    
    img.save('world_map.jpg', 'JPEG', quality=95)
    print(f"[OK] Generated synthetic satellite-style map: {width}x{height} pixels")
    return img

def generate_detailed_map(width=1600, height=800):
    """
    Generate a detailed procedural map that actually looks like Earth.
    Uses proper coastline approximations and geographic accuracy.
    """
    # Create ocean background
    img = Image.new('RGB', (width, height), color=(20, 45, 80))  # Ocean blue
    draw = ImageDraw.Draw(img, 'RGBA')
    
    land_color = (46, 125, 50)  # Forest green
    coast_outline = (80, 140, 60)  # Lighter green outline
    
    def latlon_to_pixel(lat, lon):
        """Convert latitude/longitude to pixel coordinates."""
        x = int((lon + 180) / 360.0 * width)
        y = int((height / 2) - (lat / 90.0) * (height / 2))
        return (x, y)
    
    # NORTH AMERICA (more detailed polygon)
    na_points = [
        latlon_to_pixel(70, -130),      # NW Canada
        latlon_to_pixel(75, -95),       # Arctic
        latlon_to_pixel(60, -60),       # Labrador
        latlon_to_pixel(45, -50),       # Maritime
        latlon_to_pixel(40, -75),       # East Coast
        latlon_to_pixel(25, -80),       # Florida
        latlon_to_pixel(20, -85),       # Mexico
        latlon_to_pixel(20, -110),      # Southwest US
        latlon_to_pixel(35, -120),      # California
        latlon_to_pixel(50, -125),      # Pacific Northwest
        latlon_to_pixel(70, -130),      # Back to start
    ]
    draw.polygon(na_points, fill=land_color, outline=coast_outline)
    
    # SOUTH AMERICA
    sa_points = [
        latlon_to_pixel(15, -80),       # Northern coast
        latlon_to_pixel(10, -60),       # Brazil
        latlon_to_pixel(0, -55),        # Amazon
        latlon_to_pixel(-5, -40),       # Central Brazil
        latlon_to_pixel(-15, -60),      # Southern Brazil
        latlon_to_pixel(-30, -65),      # Argentina
        latlon_to_pixel(-45, -72),      # Patagonia
        latlon_to_pixel(-30, -75),      # Southern Andes
        latlon_to_pixel(-10, -75),      # Peru
        latlon_to_pixel(5, -75),        # Colombia
        latlon_to_pixel(15, -80),       # Back to start
    ]
    draw.polygon(sa_points, fill=land_color, outline=coast_outline)
    
    # GREENLAND
    greenland_points = [
        latlon_to_pixel(82, -40),
        latlon_to_pixel(80, -15),
        latlon_to_pixel(60, -10),
        latlon_to_pixel(59, -40),
        latlon_to_pixel(82, -40),
    ]
    draw.polygon(greenland_points, fill=land_color, outline=coast_outline)
    
    # EUROPE
    europe_points = [
        latlon_to_pixel(71, -10),       # Norway North
        latlon_to_pixel(70, 20),        # Far North
        latlon_to_pixel(60, 30),        # Russia begins
        latlon_to_pixel(55, 35),        # Russia
        latlon_to_pixel(50, 35),        # Ukraine
        latlon_to_pixel(45, 25),        # SE Europe
        latlon_to_pixel(40, 20),        # Greece
        latlon_to_pixel(40, 5),         # Mediterranean
        latlon_to_pixel(42, -5),        # Spain
        latlon_to_pixel(45, -10),       # Bay of Biscay
        latlon_to_pixel(50, -5),        # France
        latlon_to_pixel(55, -3),        # Britain
        latlon_to_pixel(60, 5),         # Scandinavia
        latlon_to_pixel(71, -10),       # Back to start
    ]
    draw.polygon(europe_points, fill=land_color, outline=coast_outline)
    
    # AFRICA
    africa_points = [
        latlon_to_pixel(38, -5),        # Morocco
        latlon_to_pixel(35, 5),         # Northern Africa
        latlon_to_pixel(35, 15),        # Libya/Egypt
        latlon_to_pixel(30, 25),        # Red Sea
        latlon_to_pixel(20, 35),        # Ethiopia
        latlon_to_pixel(10, 40),        # East Africa
        latlon_to_pixel(5, 35),         # Central Africa
        latlon_to_pixel(0, 30),         # DRC
        latlon_to_pixel(-5, 25),        # Angola
        latlon_to_pixel(-10, 20),       # Zambia
        latlon_to_pixel(-20, 25),       # Zimbabwe
        latlon_to_pixel(-30, 20),       # South Africa
        latlon_to_pixel(-35, 25),       # South Africa East
        latlon_to_pixel(-25, 35),       # Mozambique
        latlon_to_pixel(-15, 40),       # Tanzania
        latlon_to_pixel(-5, 35),        # Uganda
        latlon_to_pixel(5, 30),         # Congo
        latlon_to_pixel(10, 15),        # Nigeria/Mali
        latlon_to_pixel(20, 5),         # Sahara border
        latlon_to_pixel(35, 0),         # Mauritania
        latlon_to_pixel(38, -5),        # Back to start
    ]
    draw.polygon(africa_points, fill=land_color, outline=coast_outline)
    
    # ASIA (Massive continent)
    asia_points = [
        latlon_to_pixel(72, 40),        # Arctic Russia
        latlon_to_pixel(75, 100),       # Far North Siberia
        latlon_to_pixel(72, 160),       # Arctic Far East
        latlon_to_pixel(65, 180),       # Bering Strait
        latlon_to_pixel(55, 160),       # Kamchatka
        latlon_to_pixel(50, 140),       # Japan region
        latlon_to_pixel(45, 135),       # Japan
        latlon_to_pixel(30, 120),       # China South
        latlon_to_pixel(25, 115),       # Vietnam
        latlon_to_pixel(15, 105),       # Thailand
        latlon_to_pixel(8, 100),        # Myanmar
        latlon_to_pixel(5, 95),         # India South
        latlon_to_pixel(10, 90),        # Indian Ocean
        latlon_to_pixel(15, 75),        # India West
        latlon_to_pixel(25, 70),        # Pakistan
        latlon_to_pixel(35, 70),        # Afghanistan
        latlon_to_pixel(45, 75),        # Central Asia
        latlon_to_pixel(50, 85),        # Kazakhstan/Mongolia
        latlon_to_pixel(55, 95),        # Southern Siberia
        latlon_to_pixel(60, 105),       # Siberia
        latlon_to_pixel(72, 40),        # Back to start
    ]
    draw.polygon(asia_points, fill=land_color, outline=coast_outline)
    
    # AUSTRALIA
    australia_points = [
        latlon_to_pixel(-10, 113),
        latlon_to_pixel(-12, 125),
        latlon_to_pixel(-20, 150),
        latlon_to_pixel(-30, 155),
        latlon_to_pixel(-35, 150),
        latlon_to_pixel(-37, 140),
        latlon_to_pixel(-32, 115),
        latlon_to_pixel(-20, 113),
        latlon_to_pixel(-10, 113),
    ]
    draw.polygon(australia_points, fill=land_color, outline=coast_outline)
    
    # NEW ZEALAND (small islands)
    draw.ellipse([
        latlon_to_pixel(-34, 165),
        latlon_to_pixel(-48, 178)
    ], fill=land_color, outline=coast_outline)
    
    # ANTARCTICA (bottom continent)
    draw.rectangle([
        (0, int(height * 0.85)),
        (width, height)
    ], fill=land_color, outline=coast_outline)
    
    # Draw gridlines for reference
    line_color = (40, 60, 100, 80)  # Semi-transparent blue
    
    # Latitude lines (every 15 degrees)
    for lat in range(-90, 91, 15):
        y = int((height / 2) - (lat / 90.0) * (height / 2))
        draw.line([(0, y), (width, y)], fill=line_color, width=1)
    
    # Longitude lines (every 15 degrees)
    for lon in range(-180, 180, 15):
        x = int((lon + 180) / 360.0 * width)
        draw.line([(x, 0), (x, height)], fill=line_color, width=1)
    
    # Equator and Prime Meridian (highlighted)
    equator_y = height // 2
    pm_x = width // 2
    draw.line([(0, equator_y), (width, equator_y)], fill=(100, 180, 220), width=2)
    draw.line([(pm_x, 0), (pm_x, height)], fill=(100, 180, 220), width=2)
    
    # Save the map
    img.save('world_map.jpg', 'JPEG', quality=95)
    print(f"[OK] Generated detailed world map: {width}x{height} pixels with proper coastlines")
    return img

if __name__ == "__main__":
    generate_world_map()
