# -*- coding: utf-8 -*-
import calendar
import math
import sys
from datetime import datetime
from typing import Callable, Optional, TypeVar

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as tick
from matplotlib.offsetbox import AnnotationBbox, OffsetImage

RUNNER = "NAOSENSE"

T = TypeVar("T")
K = TypeVar("K")


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

        dts, accs, distances, hearts, paces = get_running_data()
        ax.plot(dts, accs, color="#d62728")
        ax2 = plt.axes([0.1, 0.80, 0.3, 0.1])
        ax2.boxplot(
            hearts,
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

        ax3 = plt.axes([0.1, 0.65, 0.3, 0.1])
        ax3.boxplot(
            [p.minute * 60 + p.second for p in paces],
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

        attendance_all, attendance_this_year = tuple(
            map(make_circular, get_attendance(dts))
        )
        feature = make_circular(
            [
                "Jan",
                "",
                "",
                "Apr",
                "",
                "",
                "Jul",
                "",
                "",
                "Oct",
                "",
                "",
            ]
        )
        angles_deg = make_circular([a for a in range(0, 360, 30)])
        angles_rad = make_circular([a * math.pi / 180 for a in range(0, 360, 30)])

        ax4 = plt.axes([0.1, 0.3, 0.25, 0.25], polar=True)
        ax4.plot(angles_rad, attendance_all, "-", linewidth=1, color="#ff7f0e")
        ax4.fill(angles_rad, attendance_all, alpha=0.15, zorder=2, color="#ff7f0e")
        ax4.plot(angles_rad, attendance_this_year, "-", linewidth=1, color="#2ca02c")
        ax4.fill(
            angles_rad, attendance_this_year, alpha=0.15, zorder=3, color="#2ca02c"
        )
        ax4.spines["polar"].set_linestyle("--")
        ax4.spines["polar"].set_linewidth(0.5)
        ax4.spines["polar"].set_color("grey")
        ax4.tick_params(axis="x", which="major", labelsize="xx-small", length=0)
        ax4.tick_params(axis="y", which="major", labelsize="xx-small", length=0)
        ax4.set_thetagrids(angles_deg, feature)
        ax4.set_yticks([20, 40, 60, 80, 100])
        ax4.set_yticklabels(["", "", "", "", "100%"])
        ax4.set_ylim(0, 100)
        ax4.grid(visible=True, lw=0.5, ls="--")

        years = dts[-1].year - dts[0].year + 1
        this_year = datetime.now().year
        distance_this_year = sum(
            [distances[i] for i, dt in enumerate(dts) if dt.year == this_year]
        )
        fig.text(
            0.97,
            0.15,
            f"{RUNNER}\n"
            f"{years} years\n"
            f"{len(dts)} times\n"
            f"total {accs[-1]:.2f}Km\n"
            f"this year {distance_this_year:.2f}Km\n"
            f"latest {dts[-1]: %Y-%m-%d} {distances[-1]:.2f}Km",
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


def pace_label_fmt(val: float, pos) -> str:
    min = val // 60
    sec = val % 60
    return f"{min:.0f}'{sec:.0f}\""


def make_circular(lst: list[T]) -> list[T]:
    if len(lst) > 1:
        lst.append(lst[0])
    return lst


def get_attendance(dts: list[datetime]) -> tuple[list[float], list[float]]:
    dts_all_monthly = groupby(dts, lambda d: d.month)
    this_year = datetime.now().year
    dts_this_year = [d for d in dts if d.year == this_year]
    dts_this_year_monthly = groupby(dts_this_year, lambda d: d.month)
    days_all_monthly = get_days_monthly(
        dts[0].year, dts[-1].year, dts[0].month, dts[-1].month
    )
    days_this_year_monthly = get_days_monthly(this_year, this_year)
    attendance_all = []
    attendance_this_year = []
    for m in range(1, 13):
        if m in dts_all_monthly:
            attendance_all.append(len(dts_all_monthly[m]) / days_all_monthly[m] * 100)
        else:
            attendance_all.append(0.0)

        if m in dts_this_year_monthly:
            attendance_this_year.append(
                len(dts_this_year_monthly[m]) / days_this_year_monthly[m] * 100
            )
        else:
            attendance_this_year.append(0.0)

    return attendance_all, attendance_this_year


def get_days_monthly(
    year_start: int,
    year_end: int,
    month_start: Optional[int] = None,
    month_end: Optional[int] = None,
) -> dict[int, int]:
    days_monthly = {}
    for y in range(year_start, year_end + 1):
        for m in range(
            month_start if month_start and y == year_start else 1,
            (month_end if month_end and y == year_end else 12) + 1,
        ):
            days = calendar.monthrange(y, m)[1]
            if m in days_monthly:
                days_monthly[m] += days
            else:
                days_monthly[m] = days
    return days_monthly


def groupby(data: list[T], key_func: Callable[[T], K]) -> dict[K, list[T]]:
    grouped_data = {}
    for item in data:
        key = key_func(item)
        if key in grouped_data:
            grouped_data[key].append(item)
        else:
            grouped_data[key] = [item]
    return grouped_data


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
    distances = []
    hearts = []
    paces = []
    for idx, (dt, distance, heart, pace) in enumerate(data):
        acc += distance
        dts.append(dt)
        accs.append(acc)
        distances.append(distance)
        if heart:
            hearts.append(heart)
        paces.append(pace)
    return dts, accs, distances, hearts, paces


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
