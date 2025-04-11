import sys
from configparser import ConfigParser
from datetime import datetime
from itertools import count

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from serial.serialutil import SerialException

from gauge_controller import GaugeController1, SimGaugeControllerx
from ini_reader import find_comport, find_selection, get_ini_filepath, load_ini


def init_gauge_controller(
    com_port: str,
) -> SimGaugeControllerx | GaugeController1 | None:
    if com_port == 'Sim':
        return SimGaugeControllerx()
    else:
        try:
            GaugeController1(port=com_port)
        except SerialException as se:
            print(f'{se}')
            return


def create_animation_figure() -> tuple[Figure, Axes, tuple[Line2D]]:
    fig, ax = plt.subplots(
        frameon=True, edgecolor='k', linewidth=2, figsize=(6, 4), dpi=200
    )
    (line,) = ax.plot(
        [], [], c='tab:blue', label='Pressure', linewidth=1, marker='o', markersize=2
    )

    ax.set_title('Blaster Pressure Log')
    ax.set_yscale('log')
    ax.tick_params(axis='both', which='both', labelsize=6)
    ax.set_xlabel('Time (s)', fontsize=8)
    ax.set_ylabel('Pressure (mBar)', fontsize=8)
    ax.grid(True, which='both')

    return fig, ax, (line,)


def run_animation(
    gauge_controller: GaugeController1 | SimGaugeControllerx, x_axis_window_range: int
) -> None:
    fig, ax, (line,) = create_animation_figure()
    pressure_log: list[float] = []
    time_log: list[datetime] = []
    index: count = count()
    x_vals: list[int] = []

    def animate(_) -> tuple[Line2D]:
        assert gauge_controller is not None
        pressure_reading, status = gauge_controller.pressure_gauge()
        if status[1] == 'Measurement data okay':
            pressure_log.append(float(pressure_reading))
            time_log.append(datetime.now())
            x_vals.append(next(index))
        else:
            print(
                'Pressure Measurement not recorded.\nGauge Controller Status: {status}'
            )

        # Trim data
        if len(x_vals) > x_axis_window_range:
            xdata = x_vals[-x_axis_window_range:]
            ydata = pressure_log[-x_axis_window_range:]
        else:
            xdata = x_vals
            ydata = pressure_log

        line.set_data(xdata, ydata)
        if len(x_vals) > 1:
            ax.set_xlim(max(0, x_vals[-1] - x_axis_window_range), x_vals[-1])
        else:
            ax.set_xlim(0, 1)
        if ydata:
            ax.set_ylim(0.98 * min(ydata), 1.02 * max(ydata))

        ax.tick_params(axis='both', which='both', labelsize=6)
        ax.set_xlabel('Time (s)', fontsize=8)
        ax.set_ylabel('Pressure (mBar)', fontsize=8)

        fig.tight_layout()

        return (line,)

    try:
        ani: FuncAnimation = FuncAnimation(
            fig, animate, interval=1000, cache_frame_data=False
        )
        plt.show()
    finally:
        gauge_controller.close_port()

    plot_full_log(time_log, pressure_log)


def plot_full_log(time_log: list[datetime], pressure_log: list[float]) -> None:
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


def get_user_config() -> tuple[str, int]:
    ini_filepath: str = get_ini_filepath()
    config_data: ConfigParser = load_ini(ini_filepath)
    com_port: str = find_comport(config_data, 'Pressure_Gauge')
    try:
        seconds: int = int(find_selection(config_data, 'Window_Range', 'seconds'))
        minutes: int = int(find_selection(config_data, 'Window_Range', 'minutes'))
        hours: int = int(find_selection(config_data, 'Window_Range', 'hours'))
        days: int = int(find_selection(config_data, 'Window_Range', 'days'))
    except (TypeError, ValueError) as e:
        raise ValueError(
            "Invalid input in 'Window_Range': all time values must be integers. Check configuration.ini file in the configuration folder."
        ) from e

    x_axis_window_range: float = seconds * minutes * hours * days

    return com_port, x_axis_window_range


def main() -> None:
    com_port, x_axis_window_range = get_user_config()

    gauge_controller: GaugeController1 | SimGaugeControllerx | None = (
        init_gauge_controller(com_port=com_port)
    )

    if gauge_controller is None:
        print('Could not connect to pressure gauge controller.')
        sys.exit()

    run_animation(gauge_controller, x_axis_window_range)


if __name__ == '__main__':
    main()
