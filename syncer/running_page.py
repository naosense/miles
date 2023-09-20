"""
Fetch running_page activities.json to get your statistics.
For more running_page information, please visit https://github.com/yihong0618/running_page
"""

from dateutil import parser
import logging
import json
import math
import os
import urllib.request
import sys

logger = logging.getLogger(__name__)
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)-7s - %(filename)s:%(lineno)4d - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(BASE_PATH, "syncer.log")),
        logging.StreamHandler(),  # console
    ],
)
logger = logging.getLogger(__name__)

def get_activities_download_path(running_page_repo: str) -> str:
  return "https://raw.githubusercontent.com/{repo}/master/src/static/activities.json".format(repo=running_page_repo)

def get_activities(running_page_repo: str) -> []:
  logger.info("getting activities from running_repo [{repo}]...".format(repo=running_page_repo))
  path = get_activities_download_path(running_page_repo)
  try:
    with urllib.request.urlopen(path) as url:
      activities = json.loads(url.read().decode())
  except:
    logger.error("[Error] failed to get activities from running_repo [{repo}]({path})".format(repo=running_page_repo, path=path))
    raise
  if isinstance(activities, list):
    logger.info("got {number} activities records".format(number=len(activities)))
    return activities
  else:
      raise TypeError("activities.json is invalid, expect list type")

def refresh_running_csv(activities: list):
  logger.info("writing records to running.csv...")
  with open("running.csv", "w") as f:
    f.write("DT,distance(Km),heart,pace\n")
    for activity in activities:
      f.write("{date},{distance:.2f},{heart},{pace}\n".format(
        date=parser.parse(activity["start_date"]).strftime("%Y-%m-%d %H:%M:%S"),
        distance=activity["distance"]/1000.,
        heart='{:.0f}'.format(activity["average_heartrate"]) if activity["average_heartrate"] else '',
        pace=get_format_pace(activity["average_speed"]),
      ))
  logger.info("done")

def get_format_pace(average_speed: float) -> str:
  pace = (1000.0 / 60.0) * (1.0 / average_speed)
  minutes = math.floor(pace)
  seconds = math.floor((pace - minutes) * 60.0)
  return "{}:{:02d}".format(minutes, seconds)

if __name__ == "__main__":
    args = sys.argv
    if len(args) != 2:
        sys.exit("args is not right, e.g. python running_page.py yihong0618/running_page")

    running_page_repo = args[1]
    activities = get_activities(running_page_repo)
    refresh_running_csv(activities)