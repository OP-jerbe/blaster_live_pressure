import sys
from datetime import datetime
from itertools import count

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.lines import Line2D
from serial.serialutil import SerialException

from gauge_controller import GaugeController1, SimGaugeControllerx

SIMULATION: bool = True

COM_PORT: str = 'COM6'  # 'COM6' for AGC-100, 'COM4' for pfeiffer

SECONDS: int = 10
MINUTES: int = 1
HOURS: int = 1
X_AXIS_WINDOW_RANGE: float = (
    SECONDS * MINUTES * HOURS
)  # ex: 60*1*1 = one minute; 60*60*1 = one hour; 60*60*6 = six hours


def init_gauge_controller(
    simulation: bool,
) -> SimGaugeControllerx | GaugeController1 | None:
    if simulation:
        return SimGaugeControllerx()
    else:
        try:
            GaugeController1(port=COM_PORT)
        except SerialException as se:
            print(f'{se}')
            return


gauge_controller: GaugeController1 | SimGaugeControllerx | None = init_gauge_controller(
    simulation=SIMULATION
)


if gauge_controller is None:
    print('Could not connect to pressure gauge controller.')
    sys.exit()


x_vals: list[int] = []
pressure_log: list[float] = []
time_log: list[datetime] = []
index: count = count()

fig, ax = plt.subplots(
    frameon=True, edgecolor='k', linewidth=2, figsize=(6, 4), dpi=200
)
(line,) = ax.plot(
    [], [], c='tab:blue', label='Pressure', linewidth=1, marker='o', markersize=2
)

if SIMULATION:
    ax.set_title('Simulated Blaster Pressure Log')
else:
    ax.set_title('Blaster Pressure Log')
ax.set_yscale('log')
ax.tick_params(axis='both', which='both', labelsize=6)
ax.set_xlabel('Time (s)', fontsize=8)
ax.set_ylabel('Pressure (mBar)', fontsize=8)
ax.grid(True, which='both')


def animate(_) -> tuple[Line2D]:
    assert gauge_controller is not None
    pressure_reading, status = gauge_controller.pressure_gauge()
    if status[1] == 'Measurement data okay':
        pressure_log.append(float(pressure_reading))
        time_log.append(datetime.now())
        x_vals.append(next(index))
    else:
        message = (
            'Pressure Measurement not recorded.\nGauge Controller Status: {status}'
        )
        print(message)

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
        ax.set_xlim(0, 1)
    if ydata:
        ax.set_ylim(0.98 * min(ydata), 1.02 * max(ydata))

    ax.tick_params(axis='both', which='both', labelsize=6)
    ax.set_xlabel('Time (s)', fontsize=8)
    ax.set_ylabel('Pressure (mBar)', fontsize=8)

    fig.tight_layout()

    return (line,)


def plot_full_log(event=None) -> None:
    if not time_log or not pressure_log:
        print('No data to plot.')
        return

    time_numeric = mdates.date2num(time_log)
    fig2, ax2 = plt.subplots(figsize=(6, 4), dpi=200)
    fig2.autofmt_xdate()
    ax2.plot(
        time_numeric,
        pressure_log,
        c='tab:blue',
        linewidth=1,
        marker='o',
        markersize=2,
    )
    ax2.set_title('Full Pressure Log')
    ax2.tick_params(axis='both', which='both', labelsize=6)
    ax2.xaxis_date()
    ax2.set_xlabel('Time (s)', fontsize=8)
    ax2.set_ylabel('Pressure (mBar)', fontsize=8)
    ax2.set_yscale('log')
    ax2.grid(True, which='both')
    plt.tight_layout()
    plt.show()


if gauge_controller is not None:
    try:
        ani: FuncAnimation = FuncAnimation(
            fig, animate, interval=10, cache_frame_data=False
        )
        fig.canvas.mpl_connect('close_event', plot_full_log)
        plt.show()
    finally:
        gauge_controller.close_port()
