# -*- coding: utf-8 -*-
import sys
from datetime import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as tick
from matplotlib.offsetbox import AnnotationBbox, OffsetImage

RUNNER = "NAOSENSE"


def number_label_fmt(val: float, pos) -> str:
    if val > 1000000:
        return f"{val / 1000000:.0f}M"
    elif val > 1000:
        return f"{val / 1000:.0f}K"
    else:
        return f"{val:.0f}"


def plot_running() -> None:
    with plt.xkcd():
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.spines[["top", "right"]].set_visible(False)
        locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
        formatter = mdates.ConciseDateFormatter(locator)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)
        ax.yaxis.set_major_formatter(tick.FuncFormatter(number_label_fmt))
        ax.tick_params(axis="x", which="major", length=5)
        ax.tick_params(axis="x", which="minor", length=5)
        ax.tick_params(axis="y", which="major", length=5)
        ax.tick_params(axis="y", which="minor", length=5)
        ax.set_title("Running is not a sport for health, it is a way of life!")
        xs, ys, ds = get_running_data()
        ax.plot(
            xs,
            ys,
            color="#CC5135",
            label=f"latest running: {xs[-1]: %Y-%m-%d} {ds[-1]:.2f}Km",
        )

        years = xs[-1].year - xs[0].year + 1
        this_year = datetime.now().year
        distance_this_year = sum(
            [ds[i] for i, dt in enumerate(xs) if dt.year == this_year]
        )
        fig.text(
            0.95,
            0.20,
            f"{RUNNER}\n"
            f"{years} years\n"
            f"{len(xs)} times\n"
            f"total {ys[-1]:.2f}Km\n"
            f"this year {distance_this_year:.2f}Km\n"
            f"latest {xs[-1]: %Y-%m-%d} {ds[-1]:.2f}Km",
            ha="right",
            va="bottom",
            fontsize="small",
            linespacing=1.5,
        )
        img = plt.imread("runner.png")
        ax.add_artist(
            AnnotationBbox(
                OffsetImage(img, zoom=0.03),
                (0.95, 0.05),
                xycoords="axes fraction",
                frameon=False,
            )
        )
        # ax.legend(loc="lower right")
        ax.set_ylabel("Distance (Km)")
        fig.tight_layout()
        fig.savefig("miles.svg")


def get_running_data() -> tuple[list[datetime], list[float], list[float]]:
    data = []
    with open("running.csv") as file:
        for line in file:
            cols = line.rstrip().split(",")
            if cols[0] == "DT":
                continue
            dt = datetime.strptime(cols[0], "%Y-%m-%d %H:%M:%S")
            distance = float(cols[1])
            data.append((dt, distance))
    data.sort(key=lambda t: t[0])
    acc = 0.0
    xs = []
    ys = []
    ds = []
    for idx, (dt, distance) in enumerate(data):
        acc += distance
        xs.append(dt)
        ys.append(acc)
        ds.append(distance)
    return xs, ys, ds


def sync_data(dt_str: str, distance_str: str) -> bool:
    dts = dt_str.split(",")
    distances = distance_str.split(",")
    if len(dts) != len(distances):
        print("dt len not equal distance len")
        return False
    xs, _, _ = get_running_data()
    if xs:
        latest = xs[-1]
        new_data = [
            (dt, distances[i])
            for i, dt in enumerate(dts)
            if datetime.strptime(dt, "%Y-%m-%d %H:%M:%S") > latest
        ]
        if new_data:
            for dt, distance in sorted(new_data, key=lambda t: t[0]):
                with open("running.csv", "a") as f:
                    f.write(dt + "," + distance + "\n")
        else:
            print("no new data")
            return False
    else:
        for i, dt in enumerate(dts):
            with open("running.csv", "a") as f:
                f.write(dt + "," + distances[i] + "\n")
    return True


if __name__ == "__main__":
    args = sys.argv
    if len(args) < 2:
        sys.exit("args is not right, e.g. python main.py http 2022-01-02 12:00:21")
    op = args[1]
    if op != "http" and op != "push":
        sys.exit("op must be http or push")
    if op == "http":
        if sync_data(args[2], args[3]):
            plot_running()
    elif op == "push":
        plot_running()
    else:
        sys.exit("args is not right, e.g. python main.py http 2022-01-02 12:00:21")
