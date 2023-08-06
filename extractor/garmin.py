# -*- coding: utf-8 -*-
def parse_garmin_export_data() -> None:
    with open("Activities.csv") as source:
        with open("../running.csv", "a") as target:
            for line in reversed(list(source)):
                cols = line.rstrip().split(",")
                if cols[0] == "活动类型":
                    continue
                target.write(cols[1] + "," + cols[4][1:-1] + "\n")


if __name__ == "__main__":
    parse_garmin_export_data()
