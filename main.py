import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from urllib.request import urlopen
import Adafruit_DHT
import smbus
from ctypes import c_short
import time

# Device I2C address for BMP180
DEVICE = 0x77
bus = smbus.SMBus(1)

# ThingSpeak API Key and URL
WRITE_API = "O4EU8Y7VGZP5GDW8"
BASE_URL = "https://api.thingspeak.com/update?api_key={}".format(WRITE_API)

# DHT11 Sensor setup
SENSOR_PIN = 4
SENSOR_TYPE = Adafruit_DHT.DHT11

# Tkinter root setup
root = tk.Tk()
root.title("Live Weather Station")

# Labels for displaying live data
temp_label_var = tk.StringVar(value="N/A")
hum_label_var = tk.StringVar(value="N/A")
pres_label_var = tk.StringVar(value="N/A")
alt_label_var = tk.StringVar(value="N/A")

ttk.Label(root, text="Temperature (°C):").grid(row=0, column=0, padx=10, pady=5)
ttk.Label(root, textvariable=temp_label_var).grid(row=0, column=1, padx=10, pady=5)
ttk.Label(root, text="Humidity (%):").grid(row=1, column=0, padx=10, pady=5)
ttk.Label(root, textvariable=hum_label_var).grid(row=1, column=1, padx=10, pady=5)
ttk.Label(root, text="Pressure (Pa):").grid(row=2, column=0, padx=10, pady=5)
ttk.Label(root, textvariable=pres_label_var).grid(row=2, column=1, padx=10, pady=5)
ttk.Label(root, text="Altitude (m):").grid(row=3, column=0, padx=10, pady=5)
ttk.Label(root, textvariable=alt_label_var).grid(row=3, column=1, padx=10, pady=5)

# Matplotlib figure for live plotting
fig = Figure(figsize=(8, 4), dpi=100)
ax = fig.add_subplot(111)
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().grid(row=4, column=0, columnspan=2, padx=10, pady=10)

# Lists to store live data for plotting
time_data = []
temp_data = []
hum_data = []

# Function to return two bytes as a signed 16-bit value
def getShort(data, index):
return c_short((data[index] << 8) + data[index + 1]).value

# Function to return two bytes as an unsigned 16-bit value
def getUshort(data, index):
return (data[index] << 8) + data[index + 1]

# Function to read BMP180 data
def readBmp180(addr=DEVICE):
REG_CALIB = 0xAA
REG_MEAS = 0xF4
REG_MSB = 0xF6
CRV_TEMP = 0x2E
CRV_PRES = 0x34
OVERSAMPLE = 3

cal = bus.read_i2c_block_data(addr, REG_CALIB, 22)
AC1 = getShort(cal, 0)
AC2 = getShort(cal, 2)
AC3 = getShort(cal, 4)
AC4 = getUshort(cal, 6)
AC5 = getUshort(cal, 8)
AC6 = getUshort(cal, 10)
B1 = getShort(cal, 12)
B2 = getShort(cal, 14)
MB = getShort(cal, 16)
MC = getShort(cal, 18)
MD = getShort(cal, 20)

bus.write_byte_data(addr, REG_MEAS, CRV_TEMP)
time.sleep(0.005)
(msb, lsb) = bus.read_i2c_block_data(addr, REG_MSB, 2)
UT = (msb << 8) + lsb

bus.write_byte_data(addr, REG_MEAS, CRV_PRES + (OVERSAMPLE << 6))
time.sleep(0.04)
(msb, lsb, xsb) = bus.read_i2c_block_data(addr, REG_MSB, 3)
UP = ((msb << 16) + (lsb << 8) + xsb) >> (8 - OVERSAMPLE)

X1 = ((UT - AC6) * AC5) >> 15
X2 = (MC << 11) / (X1 + MD)
B5 = X1 + X2
temperature = ((int(B5) + 8) >> 4) / 10.0

B6 = int(B5 - 4000)
X1 = (int(B2) * ((B6 * B6) >> 12)) >> 11
X2 = (int(AC2) * B6) >> 11
X3 = X1 + X2
B3 = (((int(AC1) * 4 + X3) << OVERSAMPLE) + 2) >> 2

X1 = (int(AC3) * B6) >> 13
X2 = (int(B1) * ((B6 * B6) >> 12)) >> 16
X3 = ((X1 + X2) + 2) >> 2
B4 = (int(AC4) * (X3 + 32768)) >> 15
B7 = (UP - B3) * (50000 >> OVERSAMPLE)

P = (B7 * 2) // B4
X1 = (int(P) >> 8) * (int(P) >> 8)
X1 = (X1 * 3038) >> 16
X2 = (-7357 * int(P)) >> 16
pressure = int(P + ((X1 + X2 + 3791) >> 4))
altitude = 44330.0 * (1.0 - pow(pressure / 101325.0, (1.0 / 5.255)))

return temperature, pressure, altitude

# Function to send data to ThingSpeak
def send_data_to_thingspeak(temperature_dht11, humidity_dht11, temperature_bmp180, pressure, altitude):
thingspeak_url = BASE_URL + "&field1={:.2f}".format(temperature_dht11) + \
"&field2={:.2f}".format(humidity_dht11) + \
"&field3={:.2f}".format(pressure) + \
"&field4={:.2f}".format(altitude)
try:
conn = urlopen(thingspeak_url)
print("Response: {}\n\n\n".format(conn.read()))
conn.close()
except Exception as e:
print("Error sending data to ThingSpeak: ", e)

# Function to update data in GUI and plot live
def update_live_data():
global time_data, temp_data, hum_data

humidity, temp_dht = Adafruit_DHT.read_retry(SENSOR_TYPE, SENSOR_PIN)
temp_bmp, pressure, altitude = readBmp180()

if humidity is not None and temp_dht is not None:
temp_label_var.set(f"{temp_dht:.2f} °C")
hum_label_var.set(f"{humidity:.2f} %")
pres_label_var.set(f"{pressure:.2f} Pa")
alt_label_var.set(f"{altitude:.2f} m")

send_data_to_thingspeak(temp_dht, humidity, temp_bmp, pressure, altitude)

current_time = time.strftime("%H:%M:%S")
time_data.append(current_time)
temp_data.append(temp_dht)
hum_data.append(humidity)

if len(time_data) > 10:
time_data.pop(0)
temp_data.pop(0)
hum_data.pop(0)

ax.clear()
ax.plot(time_data, temp_data, label="Temperature (°C)", color="red")
ax.plot(time_data, hum_data, label="Humidity (%)", color="blue")
ax.legend()
ax.set_title("Live Temperature and Humidity")
ax.set_xlabel("Time")
ax.set_ylabel("Value")
ax.tick_params(axis="x", rotation=45)

canvas.draw()

root.after(15000, update_live_data)

# Start the live update
update_live_data()

# Tkinter main loop
root.mainloop()
