"""Host-scoped Earthdata login, with temporary domain-scoped cookies for GDAL."""
from contextlib import contextmanager
from http.cookiejar import MozillaCookieJar
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urljoin, urlsplit

import requests


DATA_HOST = "data.lpdaac.earthdatacloud.nasa.gov"
LOGIN_HOST = "urs.earthdata.nasa.gov"
ALLOWED_HOSTS = {DATA_HOST, LOGIN_HOST, "lp-prod-protected.s3.us-west-2.amazonaws.com"}


def checked_url(url):
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS
            or parsed.username or parsed.password or parsed.port not in (None, 443)):
        raise ValueError("Unsupported Earthdata asset host")
    return parsed.hostname


@contextmanager
def authenticated_options(href, session=None):
    checked_url(href)
    username, password = os.getenv("NASA_EARTHDATA_USERNAME"), os.getenv("NASA_EARTHDATA_PASSWORD")
    if not username or not password:
        raise ValueError("Earthdata credentials unavailable")
    owned_session = session is None
    session = session or requests.Session()
    # Do not let ambient .netrc configuration send credentials to another host.
    if owned_session:
        session.trust_env = False
    try:
        with TemporaryDirectory(prefix="agniview-earthdata-") as directory:
            url = href
            for _ in range(6):
                host = checked_url(url)
                with session.get(url, auth=(username, password) if host == LOGIN_HOST else None,
                                 headers={"Range": "bytes=0-0"}, stream=True,
                                 allow_redirects=False, timeout=(10, 30)) as response:
                    response.raise_for_status()
                    if response.status_code in (301, 302, 303, 307, 308):
                        url = urljoin(url, response.headers["Location"])
                        continue
                    if response.status_code not in (200, 206) or host == LOGIN_HOST:
                        raise ValueError("Earthdata login did not return a data response")
                    break
            else:
                raise ValueError("Earthdata redirect limit exceeded")
            cookie_path = str(Path(directory) / "cookies.txt")
            jar = MozillaCookieJar(cookie_path)
            for cookie in session.cookies:
                jar.set_cookie(cookie)
            jar.save(ignore_discard=True, ignore_expires=True)
            os.chmod(cookie_path, 0o600)
            yield {"GDAL_HTTP_COOKIEFILE": cookie_path, "GDAL_HTTP_COOKIEJAR": cookie_path}
    finally:
        if owned_session:
            session.close()
