"""
Python 3 API wrapper for Garmin Connect to get your statistics.
Copy most code from https://github.com/cyberjunky/python-garminconnect
Copy most code from https://github.com/yihong0618/running_page
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, date, timedelta

import cloudscraper
import garth
import httpx

GITHUB_WORKFLOW_ID = "65380959"

GARMIN_USERNAME = os.getenv("GARMIN_USERNAME")
GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD")
GITHUB_TOKEN = os.getenv("GH_TOKEN")

GITHUB_WORKFLOW_URL = (
    "https://api.github.com/repos/naosense/miles/actions/workflows/%s/dispatches"
    % GITHUB_WORKFLOW_ID
)

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

TIME_OUT = httpx.Timeout(240.0, connect=360.0)
GARMIN_COM_URL_DICT = {
    "BASE_URL": "https://connectapi.garmin.com",
    "SSO_URL_ORIGIN": "https://sso.garmin.com",
    "SSO_URL": "https://sso.garmin.com/sso",
    "MODERN_URL": "https://connectapi.garmin.com",
    "SIGNIN_URL": "https://sso.garmin.com/sso/signin",
    "CSS_URL": "https://static.garmincdn.com/com.garmin.connect/ui/css/gauth-custom-v1.2-min.css",
    "UPLOAD_URL": "https://connectapi.garmin.com/upload-service/upload/.gpx",
    "ACTIVITY_URL": "https://connectapi.garmin.com/activity-service/activity/{activity_id}",
}

GARMIN_CN_URL_DICT = {
    "BASE_URL": "https://connectapi.garmin.cn",
    "SSO_URL_ORIGIN": "https://sso.garmin.com",
    "SSO_URL": "https://sso.garmin.cn/sso",
    "MODERN_URL": "https://connect.garmin.cn",
    "MODERN_URL": "https://connectapi.garmin.cn",
    "SIGNIN_URL": "https://sso.garmin.cn/sso/signin",
    "CSS_URL": "https://static.garmincdn.cn/cn.garmin.connect/ui/css/gauth-custom-v1.2-min.css",
    "UPLOAD_URL": "https://connectapi.garmin.cn/upload-service/upload/.gpx",
    "ACTIVITY_URL": "https://connectapi.garmin.cn/activity-service/activity/{activity_id}",
}


def notice_github(dts: str, distances: str, hearts: str, paces: str) -> bool:
    logger.debug(f"send notice github {dts} {distances} {hearts} {paces}")
    r = httpx.post(
        GITHUB_WORKFLOW_URL,
        json={
            "inputs": {
                "dt": dts,
                "distance": distances,
                "heart": hearts,
                "pace": paces,
            },
            "ref": "master",
        },
        headers={"Authorization": ("token %s" % GITHUB_TOKEN)},
    )
    logger.debug(f"response {r.status_code}: {r.content}")
    return r.status_code == 204


class Garmin:
    def __init__(self, secret_string, auth_domain, is_only_running=False):
        """
        Init module
        """
        self.email = email
        self.password = password
        self.req = httpx.AsyncClient(timeout=TIME_OUT)
        self.cf_req = cloudscraper.CloudScraper()
        self.URL_DICT = (
            GARMIN_CN_URL_DICT
            if auth_domain and str(auth_domain).upper() == "CN"
            else GARMIN_COM_URL_DICT
        )
        self.modern_url = self.URL_DICT.get("MODERN_URL")
        garth.client.loads(secret_string)
        if garth.client.oauth2_token.expired:
            garth.client.refresh_oauth2()

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36",
            "origin": self.URL_DICT.get("SSO_URL_ORIGIN"),
            "nk": "NT",
            "Authorization": str(garth.client.oauth2_token),
        }
        self.is_only_running = is_only_running
        self.upload_url = self.URL_DICT.get("UPLOAD_URL")
        self.activity_url = self.URL_DICT.get("ACTIVITY_URL")

    async def fetch_data(self, url, retrying=False):
        """
        Fetch and return data
        """
        try:
            response = await self.req.get(url, headers=self.headers)
            if response.status_code == 429:
                raise GarminConnectTooManyRequestsError("Too many requests")
            logger.debug(f"fetch_data got response code {response.status_code}")
            response.raise_for_status()
            return response.json()
        except Exception as err:
            if retrying:
                logger.debug(
                    "Exception occurred during data retrieval, relogin without effect: %s"
                    % err
                )
                raise GarminConnectConnectionError("Error connecting") from err
            else:
                logger.debug(
                    "Exception occurred during data retrieval - perhaps session expired - trying relogin: %s"
                    % err
                )
                self.login()
                await self.fetch_data(url, retrying=True)

    async def get_activities(self, start, limit, start_date=None):
        """
        Fetch available activities
        """
        logger.debug(f"get activities by {start} {limit} {start_date}")
        url = f"{self.modern_url}/activitylist-service/activities/search/activities?start={start}&limit={limit}"
        if start_date:
            url = url + f"&startDate={start_date}"
        if self.is_only_running:
            url = url + "&activityType=running"
        return await self.fetch_data(url)


class GarminConnectConnectionError(Exception):
    """Raised when communication ended in error."""

    def __init__(self, status):
        """Initialize."""
        super(GarminConnectConnectionError, self).__init__(status)
        self.status = status


class GarminConnectTooManyRequestsError(Exception):
    """Raised when rate limit is exceeded."""

    def __init__(self, status):
        """Initialize."""
        super(GarminConnectTooManyRequestsError, self).__init__(status)
        self.status = status


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("email", nargs="?", help="email of garmin")
    parser.add_argument("password", nargs="?", help="password of garmin")
    parser.add_argument(
        "--is-cn",
        dest="is_cn",
        action="store_true",
        help="if garmin accout is cn",
    )
    parser.add_argument(
        "--only-run",
        dest="only_run",
        action="store_true",
        help="if is only for running",
    )
    options = parser.parse_args()
    email = options.email
    password = options.password
    auth_domain = "CN" if options.is_cn else None
    is_only_running = options.only_run
    if not email or not password:
        logger.error("Missing email or password")
        sys.exit(1)
    if options.is_cn:
        garth.configure(domain="garmin.cn")
    garth.login(email, password)
    secret_string = garth.client.dumps()
    client = Garmin(secret_string, auth_domain, is_only_running)
    today = date.today()
    yesterday = today - timedelta(days=1)
    if sys.version_info < (3, 10):
        loop = asyncio.get_event_loop()
    else:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    runs = loop.run_until_complete(
        client.get_activities(0, 20, start_date=f"{yesterday:%Y-%m-%d}")
    )
    if runs:
        new_data = [
            (
                dt_str,
                dt,
                distance,
                heart,
                f"{(pace_in_seconds := duration / distance) // 60:.0f}:{pace_in_seconds % 60:02.0f}",
            )
            for run in runs
            if (
                dt := datetime.strptime(
                    dt_str := run["startTimeLocal"], "%Y-%m-%d %H:%M:%S"
                )
            )
            > yesterday
            and (distance := run["distance"] / 1000) > 0
            and (heart := run["averageHR"])
            and (duration := run["duration"])
        ]
        new_data.sort(key=lambda t: t[1])
        if new_data:
            dts = [dt_str for dt_str, _, _, _, _ in new_data]
            distances = [f"{distance:.2f}" for _, _, distance, _, _ in new_data]
            hearts = [f"{heart:.0f}" for _, _, _, heart, _ in new_data]
            paces = [pace for _, _, _, _, pace in new_data]
            logger.info(f"got new data {dts} {distances} {hearts} {paces}")
            if notice_github(
                ",".join(dts), ",".join(distances), ",".join(hearts), ",".join(paces)
            ):
                logger.info("notice github success")
            else:
                logger.error("notice github fail")
        else:
            logger.info("no new data")

    else:
        logger.info("no data")
