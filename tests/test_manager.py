import json

import requests

from pykobo.manager import Manager

URL_KOBO_API = "https://kf.kobotoolbox.org/api/v2"
MYTOKEN = "2bc8e0201d23dac4ec1w309107698147b81517ax"
km = Manager(url_api=URL_KOBO_API, token=MYTOKEN)


def test_init():
    assert km.url_api == URL_KOBO_API
    assert km.token == MYTOKEN
    assert km.headers == {"Authorization": f"Token {MYTOKEN}"}


with open("./tests/data_manager.json") as f:
    data_manager = json.load(f)


class MockResponse:
    def __init__(self, json_body, status_code):
        self.json_body = json_body
        self.status_code = status_code

    def json(self):
        return self.json_body


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
