# -*- coding: utf-8 -*-
import sys
from datetime import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as tick
from matplotlib.offsetbox import AnnotationBbox, OffsetImage

RUNNER = "NAOSENSE"


def pace_label_fmt(val: float, pos) -> str:
    min = val // 60
    sec = val % 60
    return f"{min:.0f}'{sec:.0f}\""


def plot_running() -> None:
    with plt.xkcd():
        fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
        ax.spines[["top", "right"]].set_visible(False)
        locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
        formatter = mdates.ConciseDateFormatter(locator)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)
        ax.tick_params(axis="both", which="major", labelsize="small", length=5)
        ax.tick_params(axis="both", which="minor", labelsize="small", length=5)
        ax.set_title("Running is not a sport for health, it is a way of life!")

        xs, ys, ds, hs, ps = get_running_data()
        ax.plot(xs, ys, color="#CC5135")
        ax2 = plt.axes([0.1, 0.75, 0.3, 0.1])
        ax2.boxplot(
            hs,
            labels=["H"],
            vert=False,
            showfliers=False,
            meanline=True,
            showmeans=True,
            widths=0.25,
        )
        ax2.spines[["top", "right", "left", "bottom"]].set_visible(False)
        ax2.tick_params(axis="x", which="major", labelsize="xx-small", length=2)
        ax2.tick_params(axis="y", which="major", labelsize="xx-small", length=0)

        ax3 = plt.axes([0.1, 0.6, 0.3, 0.1])
        ax3.boxplot(
            [p.minute * 60 + p.second for p in ps],
            labels=["P"],
            vert=False,
            showfliers=False,
            meanline=True,
            showmeans=True,
            widths=0.25,
        )
        ax3.spines[["top", "right", "left", "bottom"]].set_visible(False)
        ax3.tick_params(axis="x", which="major", labelsize="xx-small", length=2)
        ax3.tick_params(axis="y", which="major", labelsize="xx-small", length=0)
        ax3.xaxis.set_major_locator(tick.MaxNLocator(6))
        ax3.xaxis.set_major_formatter(tick.FuncFormatter(pace_label_fmt))

        years = xs[-1].year - xs[0].year + 1
        this_year = datetime.now().year
        distance_this_year = sum(
            [ds[i] for i, dt in enumerate(xs) if dt.year == this_year]
        )
        fig.text(
            0.97,
            0.15,
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
        fig.savefig("miles.svg")


def get_running_data() -> (
    tuple[list[datetime], list[float], list[float], list[int], list[datetime]]
):
    data = []
    with open("running.csv") as file:
        for line in file:
            cols = line.rstrip().split(",")
            if cols[0] == "DT":
                continue
            dt = datetime.strptime(cols[0], "%Y-%m-%d %H:%M:%S")
            distance = float(cols[1])
            heart = int(cols[2]) if cols[2].isdecimal() else None
            pace = datetime.strptime(cols[3], "%M:%S")
            if distance <= 0.0:
                continue
            data.append((dt, distance, heart, pace))
    data.sort(key=lambda t: t[0])
    acc = 0.0
    dts = []
    accs = []
    ds = []
    hs = []
    ps = []
    for idx, (dt, distance, heart, pace) in enumerate(data):
        acc += distance
        dts.append(dt)
        accs.append(acc)
        ds.append(distance)
        if heart: hs.append(heart)
        ps.append(pace)
    return dts, accs, ds, hs, ps


def sync_data(dt_str: str, distance_str: str, heart_str: str, pace_str: str) -> bool:
    dt_strs = dt_str.split(",")
    distances = distance_str.split(",")
    hearts = heart_str.split(",")
    paces = pace_str.split(",")
    n = len(dt_strs)
    if len(distances) != n:
        print("distance length not equal dt length")
        return False
    elif len(hearts) != n:
        print("heart rate length not equal dt length")
        return False
    elif len(paces) != n:
        print("pace length not equal dt length")
        return False
    dts, _, _, _, _ = get_running_data()
    if dts:
        latest = dts[-1]
        new_data = [
            (dt_str, distances[i], hearts[i], paces[i])
            for i, dt_str in enumerate(dt_strs)
            if datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S") > latest
        ]
        if new_data:
            with open("running.csv", "a") as f:
                for dt_str, distance, heart, pace in sorted(
                    new_data, key=lambda t: t[0]
                ):
                    f.write(f"{dt_str},{distance},{heart},{pace}\n")
        else:
            print("no new data")
            return False
    else:
        with open("running.csv", "a") as f:
            for i, dt_str in enumerate(dt_strs):
                f.write(f"{dt_str},{distances[i]},{hearts[i]},{paces[i]}\n")
    return True


if __name__ == "__main__":
    args = sys.argv
    if len(args) < 2:
        sys.exit(
            "args is not right, e.g. python main.py http 2022-01-02 12:00:21 140 4:56"
        )
    op = args[1]
    if op != "http" and op != "push":
        sys.exit("op must be http or push")
    if op == "http":
        if sync_data(args[2], args[3], args[4], args[5]):
            plot_running()
    elif op == "push":
        plot_running()
    else:
        sys.exit("args is not right, e.g. python main.py http 2022-01-02 12:00:21")
