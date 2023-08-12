# -*- coding: utf-8 -*-
def parse_garmin_export_data() -> None:
    with open("Activities.csv") as source:
        with open("running.csv", "a") as target:
            for line in reversed(list(source)):
                cols = line.rstrip().split(",")
                if cols[0] == "活动类型":
                    continue
                distance = cols[4][1:-1]
                if float(distance) <= 0.0:
                    continue
                target.write(f"{cols[1]},{distance},{cols[7][1:-1]},{cols[11][1:-1]}\n")


if __name__ == "__main__":
    parse_garmin_export_data()
