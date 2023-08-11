"""
Python 3 API wrapper for Garmin Connect to get your statistics.
Copy most code from https://github.com/cyberjunky/python-garminconnect
Copy most code from https://github.com/yihong0618/running_page
"""

import argparse
import asyncio
import logging
import os
import re
import sys
from datetime import datetime, timedelta

import cloudscraper
import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

GITHUB_WORKFLOW_ID = ""

GITHUB_TOKEN = ""

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
    "BASE_URL": "https://connect.garmin.com",
    "SSO_URL_ORIGIN": "https://sso.garmin.com",
    "SSO_URL": "https://sso.garmin.com/sso",
    # "MODERN_URL": "https://connect.garmin.com/modern",
    "MODERN_URL": "https://connect.garmin.com",
    "SIGNIN_URL": "https://sso.garmin.com/sso/signin",
    "CSS_URL": "https://static.garmincdn.com/com.garmin.connect/ui/css/gauth-custom-v1.2-min.css",
    "UPLOAD_URL": "https://connect.garmin.com/modern/proxy/upload-service/upload/.gpx",
    "ACTIVITY_URL": "https://connect.garmin.com/proxy/activity-service/activity/{activity_id}",
}

GARMIN_CN_URL_DICT = {
    "BASE_URL": "https://connect.garmin.cn",
    "SSO_URL_ORIGIN": "https://sso.garmin.com",
    "SSO_URL": "https://sso.garmin.cn/sso",
    # "MODERN_URL": "https://connect.garmin.cn/modern",
    "MODERN_URL": "https://connect.garmin.cn",
    "SIGNIN_URL": "https://sso.garmin.cn/sso/signin",
    "CSS_URL": "https://static.garmincdn.cn/cn.garmin.connect/ui/css/gauth-custom-v1.2-min.css",
    "UPLOAD_URL": "https://connect.garmin.cn/modern/proxy/upload-service/upload/.gpx",
    "ACTIVITY_URL": "https://connect.garmin.cn/proxy/activity-service/activity/{activity_id}",
}


def notice_github(dts: str, distances: str) -> bool:
    logger.debug(f"send notice github {dts} {distances}")
    r = httpx.post(
        GITHUB_WORKFLOW_URL,
        json={
            "inputs": {"dt": f"{dts}", "distance": f"{distances}"},
            "ref": "master",
        },
        headers={"Authorization": ("token %s" % GITHUB_TOKEN)},
    )
    logger.debug(f"response {r.status_code}: {r.content}")
    return r.status_code == 204


class Garmin:
    def __init__(self, email, password, auth_domain, is_only_running=False):
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

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36",
            "origin": self.URL_DICT.get("SSO_URL_ORIGIN"),
            "nk": "NT",
        }
        self.is_only_running = is_only_running
        self.upload_url = self.URL_DICT.get("UPLOAD_URL")
        self.activity_url = self.URL_DICT.get("ACTIVITY_URL")
        self.is_login = False

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(30))
    def login(self):
        """
        Login to portal
        """
        params = {
            "webhost": self.URL_DICT.get("BASE_URL"),
            "service": self.modern_url,
            "source": self.URL_DICT.get("SIGNIN_URL"),
            "redirectAfterAccountLoginUrl": self.modern_url,
            "redirectAfterAccountCreationUrl": self.modern_url,
            "gauthHost": self.URL_DICT.get("SSO_URL"),
            "locale": "en_US",
            "id": "gauth-widget",
            "cssUrl": self.URL_DICT.get("CSS_URL"),
            "clientId": "GarminConnect",
            "rememberMeShown": "true",
            "rememberMeChecked": "false",
            "createAccountShown": "true",
            "openCreateAccount": "false",
            "usernameShown": "false",
            "displayNameShown": "false",
            "consumeServiceTicket": "false",
            "initialFocus": "true",
            "embedWidget": "false",
            "generateExtraServiceTicket": "false",
        }

        data = {
            "username": self.email,
            "password": self.password,
            "embed": "true",
            "lt": "e1s1",
            "_eventId": "submit",
            "displayNameRequired": "false",
        }

        try:
            self.cf_req.get(
                self.URL_DICT.get("SIGNIN_URL"), headers=self.headers, params=params
            )
            response = self.cf_req.post(
                self.URL_DICT.get("SIGNIN_URL"),
                headers=self.headers,
                params=params,
                data=data,
            )
        except Exception as err:
            raise GarminConnectConnectionError("Error connecting") from err
        response_url = re.search(r'"(https:[^"]+?ticket=[^"]+)"', response.text)

        if not response_url:
            raise GarminConnectAuthenticationError("Authentication error")

        response_url = re.sub(r"\\", "", response_url.group(1))
        try:
            response = self.cf_req.get(response_url)
            self.req.cookies = self.cf_req.cookies
            if response.status_code == 429:
                raise GarminConnectTooManyRequestsError("Too many requests")
            response.raise_for_status()
            self.is_login = True
        except Exception as err:
            raise GarminConnectConnectionError("Error connecting") from err

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
        if not self.is_login:
            self.login()
        url = f"{self.modern_url}/proxy/activitylist-service/activities/search/activities?start={start}&limit={limit}"
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


class GarminConnectAuthenticationError(Exception):
    """Raised when login returns wrong result."""

    def __init__(self, status):
        """Initialize."""
        super(GarminConnectAuthenticationError, self).__init__(status)
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
    if email is None or password is None:
        logger.error("Missing argument nor valid configuration file")
        sys.exit(1)
    client = Garmin(email, password, auth_domain, is_only_running)
    client.login()
    loop = asyncio.get_event_loop()
    if not os.path.exists("latest"):
        logger.error("no latest file")
        sys.exit(-1)
    with open("latest", "r") as f:
        latest_dt = datetime.strptime(f.readline(), "%Y-%m-%d %H:%M:%S")
    start_date = latest_dt.date() + timedelta(days=1)
    runs = loop.run_until_complete(
        client.get_activities(0, 20, start_date=f"{start_date:%Y-%m-%d}")
    )
    if runs:
        new_data = [
            (
                dt_str,
                dt,
                distance,
            )
            for run in runs
            if (
                dt := datetime.strptime(
                    dt_str := run["startTimeLocal"], "%Y-%m-%d %H:%M:%S"
                )
            )
            > latest_dt
            and (distance := run["distance"]) > 0
        ]
        new_data.sort(key=lambda t: t[1])
        if new_data:
            dts = [dt_str for dt_str, _, _ in new_data]
            distances = [f"{distance / 1000:.2f}" for _, _, distance in new_data]
            logger.info(f"got new data {dts} {distances}")
            if notice_github(",".join(dts), ",".join(distances)):
                logger.info("notice github success")
                with open("latest", "w") as f:
                    f.write(dts[-1])
            else:
                logger.error("notice github fail")
        else:
            logger.info("no new data")

    else:
        logger.info("no data")
