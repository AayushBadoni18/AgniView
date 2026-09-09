from contextlib import contextmanager

import pytest
import requests

from agniview.earthdata import authenticated_options


ASSET = "https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/example.tif"
LOGIN = "https://urs.earthdata.nasa.gov/oauth/authorize"


class Session:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []
        self.cookies = requests.cookies.RequestsCookieJar()

    @contextmanager
    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        status, location = next(self.responses)
        response = requests.Response()
        response.status_code = status
        if location:
            response.headers["Location"] = location
        yield response


def test_password_is_sent_only_to_earthdata_login(monkeypatch):
    monkeypatch.setenv("NASA_EARTHDATA_USERNAME", "test-user")
    monkeypatch.setenv("NASA_EARTHDATA_PASSWORD", "test-only-value")
    session = Session([(302, LOGIN), (302, ASSET), (206, None)])
    with authenticated_options(ASSET, session=session) as options:
        assert options["GDAL_HTTP_COOKIEFILE"] == options["GDAL_HTTP_COOKIEJAR"]
        assert "GDAL_HTTP_USERPWD" not in options
    assert [call[1]["auth"] for call in session.calls] == [None, ("test-user", "test-only-value"), None]


def test_untrusted_redirect_never_receives_credentials(monkeypatch):
    monkeypatch.setenv("NASA_EARTHDATA_USERNAME", "test-user")
    monkeypatch.setenv("NASA_EARTHDATA_PASSWORD", "test-only-value")
    session = Session([(302, "https://untrusted.example/steal")])
    with pytest.raises(ValueError, match="host"):
        with authenticated_options(ASSET, session=session):
            pass
    assert len(session.calls) == 1


def test_authentication_failure_preserves_status_without_secret_text(monkeypatch):
    monkeypatch.setenv("NASA_EARTHDATA_USERNAME", "test-user")
    monkeypatch.setenv("NASA_EARTHDATA_PASSWORD", "test-only-value")
    session = Session([(302, LOGIN), (401, None)])
    with pytest.raises(requests.HTTPError) as caught:
        with authenticated_options(ASSET, session=session):
            pass
    assert caught.value.response.status_code == 401
    assert "test-only-value" not in str(caught.value)
