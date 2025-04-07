# -*- coding: utf-8 -*-
"""
Created on Fri Apr 29 08:19:45 2022

@author: Joshua
"""
#%% Import modules
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import datetime
from itertools import count
from matplotlib.animation import FuncAnimation
from pfeiffer_tpg26x import TPG261 as TPG

tpg = TPG(port='COM4')

def getPressure():
    """Gets the current pressure reading from gauge controller"""
    pressureRead, (status_code, status_string) = tpg.pressure_gauge(1)
    if status_code != 0:
        print(f'\nstatus code = {status_code}')
        print(f'\nmessage = "{status_string}"')
        print('\nSomething went wrong reading the data.')
    return pressureRead

#%% Define plotting function
x_vals = []
pressure_log = []
time_log = []
index = count()


# Initialize the figure to plot to
scale_factor = 1.23
fig = plt.figure(frameon=True, dpi=290, edgecolor='k', linewidth=2, figsize=(4*scale_factor,3*scale_factor))

# Set the plot window size
x_window = 60*10 # seconds*minutes

fig, ax = plt.subplots(figsize=(4*scale_factor, 3*scale_factor), dpi=290)
line, = ax.plot([], [], c='tab:blue', label='Pressure', linewidth=1, marker='o', markersize=2)

ax.set_title('Pressure Log')
ax.set_xlabel('Time (s)')
ax.set_ylabel('Pressure (mBar)')
ax.set_yscale('log')
ax.grid(True, which='both')

def animate(i) -> tuple[Line2D]:
    try:
        pressure_reading = getPressure()
        pressure_log.append(float(pressure_reading))
        time_log.append(datetime.datetime.now().strftime('%m/%d/%Y %I:%M:%S %p'))
        x_vals.append(next(index))
    except:
        print('Did not record pressure data.')

    # Trim data
    if len(x_vals) > x_window:
        xdata = x_vals[-x_window:]
        ydata = pressure_log[-x_window:]
    else:
        xdata = x_vals
        ydata = pressure_log

    line.set_data(xdata, ydata)
    ax.set_xlim(max(0, x_vals[-1] - x_window), x_vals[-1])
    if ydata:
        ax.set_ylim(0.98 * min(ydata), 1.02 * max(ydata))
    return line,

ani = FuncAnimation(fig, animate, interval=1000)
plt.tight_layout()
plt.show()
