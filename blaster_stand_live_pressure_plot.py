import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from datetime import datetime
from itertools import count
from matplotlib.animation import FuncAnimation
from pfeiffer_tpg26x import TPG261, SimulateTPG26x


SIMULATION: bool = True

COM_PORT: str = 'COM6'

X_AXIS_WINDOW_RANGE: float = 30*1 # seconds*minutes


def init_gauge_controller(simulation: bool=False) -> SimulateTPG26x | TPG261:
    if simulation:
        return SimulateTPG26x()
    else:
        return TPG261(port=COM_PORT)

def getPressure() -> float:
    """Gets the current pressure reading from gauge controller"""
    pressureRead, (status_code, status_string) = tpg.pressure_gauge(1)
    if status_code != 0:
        print(f'\nstatus code = {status_code}')
        print(f'\nmessage = "{status_string}"')
        print('\nSomething went wrong reading the data.')
    return pressureRead


tpg: TPG261 | SimulateTPG26x = init_gauge_controller(simulation=SIMULATION)

x_vals: list[int] = []
pressure_log: list[float] = []
time_log: list[datetime] = [] # should probably just be a list of datetime.datetime
index: count = count()

fig, ax = plt.subplots(frameon=True, edgecolor='k', linewidth=2, figsize=(4,3), dpi=290)
line, = ax.plot([], [], c='tab:blue', label='Pressure', linewidth=1, marker='o', markersize=2)

ax.set_title('Blaster Pressure Log')
ax.set_yscale('log')
ax.tick_params(axis='both', which='both', labelsize=6)
ax.set_xlabel('Time (s)', fontsize=8)
ax.set_ylabel('Pressure (mBar)', fontsize=8)
ax.grid(True, which='both')


def animate(_) -> tuple[Line2D]:
    try:
        pressure_reading = getPressure()
        pressure_log.append(float(pressure_reading))
        time_log.append(datetime.now())
        x_vals.append(next(index))
    except:
        print('Did not record pressure data.')

    # Trim data
    if len(x_vals) > X_AXIS_WINDOW_RANGE:
        xdata = x_vals[-X_AXIS_WINDOW_RANGE:]
        ydata = pressure_log[-X_AXIS_WINDOW_RANGE:]
    else:
        xdata = x_vals
        ydata = pressure_log

    line.set_data(xdata, ydata)
    if len(x_vals) > 1:
        ax.set_xlim(max(0, x_vals[-1] - X_AXIS_WINDOW_RANGE), x_vals[-1])
    else:
        ax.set_xlim(0,1)
    if ydata:
        ax.set_ylim(0.98 * min(ydata), 1.02 * max(ydata))

    ax.tick_params(axis='both', which='both', labelsize=6)
    ax.set_xlabel('Time (s)', fontsize=8)
    ax.set_ylabel('Pressure (mBar)', fontsize=8)

    fig.tight_layout()

    return line,

try:
    ani: FuncAnimation = FuncAnimation(fig, animate, interval=1000, cache_frame_data=False)
    plt.show()
finally:
    tpg.close_port()
