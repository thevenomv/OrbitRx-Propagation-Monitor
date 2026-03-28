import tkinter as tk
import urllib.request
import json
import math
import datetime
from PIL import Image, ImageTk

# --- NOAA SATELLITE DATA ---
def get_space_weather():
    try:
        btn_refresh.config(text="Fetching Satellite Data...")
        window.update()

        url = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
        response = urllib.request.urlopen(url)
        data = json.loads(response.read())
        
        latest_data = data[-1] 
        time_utc = latest_data[0]
        kp_index = float(latest_data[1])
        
        if kp_index <= 3: status = "🟢 GOOD: Stable Ionosphere."
        elif kp_index <= 5: status = "🟡 FAIR: Minor Geomagnetic Activity."
        else: status = "🔴 POOR: Geomagnetic Storm. HF blackouts likely."

        lbl_kp.config(text=f"Current Kp Index: {kp_index}")
        lbl_status.config(text=status)
        lbl_time.config(text=f"Last NOAA Update: {time_utc} UTC")
        
        # Fetch Solar Flux
        try:
            url2 = "https://services.swpc.noaa.gov/products/solar-flux-5-minute.json"
            response2 = urllib.request.urlopen(url2)
            data2 = json.loads(response2.read())
            latest2 = data2[-1]
            flux = float(latest2[1])
            lbl_solar.config(text=f"Solar Flux: {flux}")
        except:
            lbl_solar.config(text="Solar Flux: --")
        
        # Fetch Sunspot Number
        try:
            url3 = "https://services.swpc.noaa.gov/products/sunspot-number.json"
            response3 = urllib.request.urlopen(url3)
            data3 = json.loads(response3.read())
            latest3 = data3[-1]
            sunspots = int(latest3[1])
            lbl_sunspot.config(text=f"Sunspot Number: {sunspots}")
        except:
            lbl_sunspot.config(text="Sunspot Number: --")
        
        # Determine Band Conditions
        try:
            if kp_index <= 3 and flux > 120:
                bands = "🟢 EXCELLENT: All HF bands open for DX"
            elif kp_index <= 5 and flux > 100:
                bands = "🟡 GOOD: Most HF bands workable"
            else:
                bands = "🔴 POOR: Limited HF propagation"
            lbl_bands.config(text=f"Band Conditions: {bands}")
        except:
            lbl_bands.config(text="Band Conditions: --")
        
    except Exception as e:
        lbl_status.config(text=f"Error connecting: {e}")
        lbl_solar.config(text="Solar Flux: --")
        lbl_sunspot.config(text="Sunspot Number: --")
        lbl_bands.config(text="Band Conditions: --")
    finally:
        btn_refresh.config(text="Refresh Space Weather")

# --- GREYLINE MATH & DRAWING ---
def draw_greyline():
    canvas.delete("all")
    width = 400
    height = 200
    
    # 1. Check if we have the map image, otherwise draw the dark grid
    if map_image:
        # Place the image exactly in the center of the canvas (200, 100)
        canvas.create_image(200, 100, image=map_image)
    else:
        # Fallback if the image isn't found
        canvas.create_rectangle(0, 0, width, height, fill="#101820") 
        canvas.create_line(0, height/2, width, height/2, fill="#333", dash=(4,4))
        canvas.create_line(width/2, 0, width/2, height, fill="#333", dash=(4,4))
    
    # 2. Get Time and Math Setup
    now = datetime.datetime.now(datetime.timezone.utc)
    day_of_year = now.timetuple().tm_yday
    hour_utc = now.hour + now.minute / 60.0
    
    declination_deg = -23.44 * math.cos(math.radians((360/365.25) * (day_of_year + 10)))
    declination_rad = math.radians(declination_deg)
    
    sun_lon_deg = 180 - (hour_utc * 15)
    sun_lon_rad = math.radians(sun_lon_deg)
    
    # 3. Plot the Wave
    points = []
    for x in range(width + 1):
        lon_deg = (x / width) * 360 - 180
        lon_rad = math.radians(lon_deg)
        
        tan_dec = math.tan(declination_rad)
        if abs(tan_dec) < 0.0001: tan_dec = 0.0001 
        
        tan_lat = -math.cos(lon_rad - sun_lon_rad) / tan_dec
        lat_deg = math.degrees(math.atan(tan_lat))
        
        y = height/2 - (lat_deg / 90) * (height/2)
        points.extend((x, y))
        
    # Draw the blazing neon orange terminator line on top of the map
    canvas.create_line(points, fill="#FF4500", width=2, smooth=True)
    
    # Draw a little text box background so the time is readable over the map
    canvas.create_rectangle(5, 5, 175, 25, fill="#101820", outline="")
    canvas.create_text(10, 10, anchor="nw", text=f"Greyline Calculated @ {now.strftime('%H:%M UTC')}", fill="white", font=("Arial", 8))

# --- AUTO-REFRESH TIMER ---
def auto_refresh():
    get_space_weather()
    draw_greyline()
    window.after(60000, auto_refresh)

# --- USER INTERFACE (UI) SETUP ---
window = tk.Tk()
window.title("Ham Radio Space Weather App")
window.geometry("450x650") 
window.config(padx=20, pady=20, bg="#101820")

# Load the image into memory right as the window is created
try:
    map_image = ImageTk.PhotoImage(Image.open("world_map.jpg"))
except:
    map_image = None
    print("Could not find world_map.jpg. Make sure it is saved in the same folder as app.py!")

lbl_title = tk.Label(window, text="Radio Propagation Tracker", font=("Arial", 14, "bold"), bg="#101820", fg="white")
lbl_title.pack(pady=(0, 10))

lbl_kp = tk.Label(window, text="Current Kp Index: --", font=("Arial", 12), bg="#101820", fg="white")
lbl_kp.pack(pady=5)

lbl_solar = tk.Label(window, text="Solar Flux: --", font=("Arial", 12), bg="#101820", fg="white")
lbl_solar.pack(pady=5)

lbl_sunspot = tk.Label(window, text="Sunspot Number: --", font=("Arial", 12), bg="#101820", fg="white")
lbl_sunspot.pack(pady=5)

lbl_bands = tk.Label(window, text="Band Conditions: --", font=("Arial", 12), bg="#101820", fg="white")
lbl_bands.pack(pady=5)

lbl_status = tk.Label(window, text="Click refresh to load live satellite data.", font=("Arial", 11, "italic"), bg="#101820", fg="white")
lbl_status.pack(pady=5)

lbl_time = tk.Label(window, text="Last NOAA Update: --", font=("Arial", 9), fg="#CCCCCC", bg="#101820")
lbl_time.pack(pady=5)

btn_refresh = tk.Button(window, text="Refresh Space Weather", command=auto_refresh, bg="#0078D7", fg="white", font=("Arial", 10, "bold"))
btn_refresh.pack(pady=15)

canvas = tk.Canvas(window, width=400, height=200, bg="#101820", highlightthickness=0)
canvas.pack(pady=10)

lbl_note = tk.Label(window, text="Red line: Greyline (day-night boundary) - optimal for HF radio propagation", font=("Arial", 9), bg="#101820", fg="#CCCCCC")
lbl_note.pack(pady=(5,0))

auto_refresh()

window.mainloop()