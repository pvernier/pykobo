import json

import pytest
import requests

from pykobo.form import KoboForm
from pykobo.manager import Manager

URL_KOBO = "https://kf.kobotoolbox.org/api/v2"
API_VERSION = 2
MYTOKEN = "2bc8e0201d23dac4ec1w309107698147b81517ax"
km = Manager(url=URL_KOBO, api_version=API_VERSION, token=MYTOKEN)


def test_init():
    assert km.url == URL_KOBO
    assert km.api_version == API_VERSION
    assert km.token == MYTOKEN
    assert km.headers == {"Authorization": f"Token {MYTOKEN}"}


def test_wrong_api_version():
    with pytest.raises(ValueError, match="The value of 'api_version' has to be: 2."):
        Manager(url=URL_KOBO, api_version=3, token=MYTOKEN)


with open("./tests/data_manager.json") as f:
    data_manager = json.load(f)


class MockResponse:
    def __init__(self, json_body, status_code):
        self.json_body = json_body
        self.status_code = status_code
        self.text = str(json_body)

    def json(self):
        return self.json_body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


def test_fetch_forms(monkeypatch):

    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: MockResponse(
            {"results": data_manager["input"]["results"]}, 200
        ),
    )

    assert km._fetch_forms() == data_manager["output"]["results"]


def test_fetch_forms_fail(monkeypatch):

    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: MockResponse(
            {"results": data_manager["input"]["results"]}, 500
        ),
    )

    # If we get an HTTP status code different from 200,
    # return an empty list
    assert km._fetch_forms() == []


# ---------------------------------------------------------------------------
# Shared fixture: a complete form dict that satisfies _extract_from_asset
# ---------------------------------------------------------------------------

_FORM = {
    "uid": "abc123uid",
    "name": "Test Form",
    "asset_type": "survey",
    "owner__username": "owner1",
    "date_created": "2023-01-01T00:00:00Z",
    "date_modified": "2023-01-02T00:00:00Z",
    "version_id": "v123",
    "has_deployment": True,
    "deployment__submission_count": 5,
    "summary": {"geo": False},
    "url": "https://kf.kobotoolbox.org/api/v2/assets/abc123uid.json",
    "data": "https://kf.kobotoolbox.org/api/v2/assets/abc123uid/data.json",
}

_FORM2 = {
    **_FORM,
    "uid": "xyz789uid",
    "name": "Second Form",
    "url": "https://kf.kobotoolbox.org/api/v2/assets/xyz789uid.json",
    "data": "https://kf.kobotoolbox.org/api/v2/assets/xyz789uid/data.json",
}


# ---------------------------------------------------------------------------
# get_forms / get_form
# ---------------------------------------------------------------------------


def test_get_forms_returns_koboform_instances():
    m = Manager(url=URL_KOBO, api_version=2, token=MYTOKEN)
    m._assets = [_FORM, _FORM2]
    forms = m.get_forms()

    assert len(forms) == 2
    assert all(isinstance(f, KoboForm) for f in forms)
    assert forms[0].uid == "abc123uid"
    assert forms[1].uid == "xyz789uid"


def test_get_forms_caches_assets(monkeypatch):
    """_fetch_forms should be called only once even when get_forms is called twice."""
    m = Manager(url=URL_KOBO, api_version=2, token=MYTOKEN)
    call_count = [0]

    def mock_fetch():
        call_count[0] += 1
        return [_FORM]

    monkeypatch.setattr(m, "_fetch_forms", mock_fetch)
    m.get_forms()
    m.get_forms()

    assert call_count[0] == 1


def test_get_form_found():
    m = Manager(url=URL_KOBO, api_version=2, token=MYTOKEN)
    m._assets = [_FORM, _FORM2]
    form = m.get_form("xyz789uid")

    assert isinstance(form, KoboForm)
    assert form.uid == "xyz789uid"


def test_get_form_not_found():
    m = Manager(url=URL_KOBO, api_version=2, token=MYTOKEN)
    m._assets = [_FORM]

    with pytest.raises(ValueError, match="no form with the uid"):
        m.get_form("doesnotexist")


def test_get_form_empty_assets():
    m = Manager(url=URL_KOBO, api_version=2, token=MYTOKEN)
    m._assets = []

    result = m.get_form("anyuid")
    assert result is None


def test_create_koboform():
    m = Manager(url=URL_KOBO, api_version=2, token=MYTOKEN)
    form = m._create_koboform(_FORM)

    assert isinstance(form, KoboForm)
    assert form.uid == _FORM["uid"]
    assert form.headers == m.headers
    assert form.metadata["name"] == "Test Form"


# ---------------------------------------------------------------------------
# share_project
# ---------------------------------------------------------------------------


def test_share_project_invalid_permission():
    m = Manager(url=URL_KOBO, api_version=2, token=MYTOKEN)
    with pytest.raises(ValueError, match="Permission must be one of"):
        m.share_project("uid123", "user1", "fly")


def test_share_project_valid_permission(monkeypatch):
    m = Manager(url=URL_KOBO, api_version=2, token=MYTOKEN)
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: MockResponse({}, 201),
    )
    # Should not raise
    m.share_project("uid123", "user1", "view_asset")


def test_share_project_http_error(monkeypatch):
    m = Manager(url=URL_KOBO, api_version=2, token=MYTOKEN)
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: MockResponse({"detail": "Forbidden"}, 403),
    )
    with pytest.raises(requests.HTTPError):
        m.share_project("uid123", "user1", "view_asset")


# ---------------------------------------------------------------------------
# upload_media_from_local
# ---------------------------------------------------------------------------


def test_upload_media_from_local_invalid_extension():
    m = Manager(url=URL_KOBO, api_version=2, token=MYTOKEN)
    with pytest.raises(ValueError, match="file extension"):
        m.upload_media_from_local("uid123", "/some/path", "file.pdf")


def test_upload_media_from_local_file_not_found():
    m = Manager(url=URL_KOBO, api_version=2, token=MYTOKEN)
    with pytest.raises(FileNotFoundError):
        m.upload_media_from_local("uid123", "/nonexistent/path", "file.jpg")


# ---------------------------------------------------------------------------
# fetch_users_with_access
# ---------------------------------------------------------------------------


def test_fetch_users_with_access(monkeypatch):
    permissions = [
        {"user": "https://kf.kobotoolbox.org/api/v2/users/alice/"},
        {"user": "https://kf.kobotoolbox.org/api/v2/users/bob/"},
        {"user": "https://kf.kobotoolbox.org/api/v2/users/alice/"},  # duplicate
    ]
    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: MockResponse(permissions, 200),
    )
    m = Manager(url=URL_KOBO, api_version=2, token=MYTOKEN)
    users = m.fetch_users_with_access("uid123")

    assert set(users) == {"alice", "bob"}


def test_fetch_users_with_access_http_error(monkeypatch):
    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: MockResponse("Unauthorized", 401),
    )
    m = Manager(url=URL_KOBO, api_version=2, token=MYTOKEN)
    with pytest.raises(requests.HTTPError):
        m.fetch_users_with_access("uid123")
