import json

import pandas as pd
import pytest
import requests

from pykobo.features import Question
from pykobo.form import KoboForm

uid = "cSatm9oFcA3e9dwJdHUrBZ"
kform = KoboForm(uid=uid)


metadata_form = {
    "uid": uid,
    "name": "Form 1",
    "owner": "owner1",
    "date_created": "2022-12-05T14:36:19.800395Z",
    "date_modified": "2022-12-05T14:42:03.913134Z",
    "version_id": "sTEcVocX5XRYD5uWabjtdv",
    "has_deployment": True,
    "geo": False,
    "num_submissions": 1,
}


def test_extract_from_asset():
    with open("./tests/data_form.json") as f:
        data_form = json.load(f)

    kform._extract_from_asset(data_form)
    assert kform.metadata == metadata_form

    assert kform.url_asset == data_form["url"]
    assert kform.url_data == data_form["data"]
    assert kform.base_url == "https://kf.kobotoolbox.org/api/v2/assets"


# ---------------------------------------------------------------------------
# Helpers shared by the tests below
# ---------------------------------------------------------------------------

# Minimal asset returned by the Kobo API for a form with two fields and
# one select_multiple question.
_ASSET = {
    "summary": {},
    "content": {
        "survey": [
            {"type": "text", "$autoname": "full_name", "label": ["Full name"]},
            {
                "type": "select_one",
                "$autoname": "gender",
                "label": ["Gender"],
                "select_from_list_name": "gender_list",
            },
            {
                "type": "select_multiple",
                "$autoname": "activities",
                "label": ["Activities"],
                "select_from_list_name": "activities_list",
            },
        ],
        "choices": [
            {"list_name": "gender_list", "name": "male", "label": ["Male"]},
            {"list_name": "gender_list", "name": "female", "label": ["Female"]},
            {"list_name": "activities_list", "name": "sport", "label": ["Sport"]},
            {"list_name": "activities_list", "name": "music", "label": ["Music"]},
        ],
    },
}

_SUBMISSIONS = [
    {"full_name": "Alice", "gender": "female", "activities": "sport music"},
    {"full_name": "Bob", "gender": "male", "activities": "sport"},
]


class MockResponse:
    def __init__(self, json_body, status_code):
        self.json_body = json_body
        self.status_code = status_code

    def json(self):
        return self.json_body


def _make_form():
    """Return a fresh KoboForm with URL attributes pre-set."""
    f = KoboForm(uid="testuid")
    f.url_asset = "https://example.com/api/v2/assets/testuid.json"
    f.url_data = "https://example.com/api/v2/assets/testuid/data.json"
    f.base_url = "https://example.com/api/v2/assets"
    f.headers = {}
    return f


def _two_call_mock(asset, submissions):
    """Mock for requests.get: first call returns the asset, second returns data."""
    responses = [
        MockResponse(asset, 200),
        MockResponse({"results": submissions}, 200),
    ]
    idx = [0]

    def mock_get(*args, **kwargs):
        r = responses[idx[0]]
        idx[0] += 1
        return r

    return mock_get


# ---------------------------------------------------------------------------
# Basic API
# ---------------------------------------------------------------------------


def test_repr():
    assert repr(KoboForm("abc123")) == "KoboForm('abc123')"


def test_display_invalid_columns_as():
    f = _make_form()
    with pytest.raises(ValueError, match="columns_as"):
        f.display(columns_as="wrong")


def test_display_invalid_choices_as():
    f = _make_form()
    with pytest.raises(ValueError, match="choices_as"):
        f.display(choices_as="wrong")


def test_download_form_invalid_format():
    f = _make_form()
    with pytest.raises(ValueError, match="not supported"):
        f.download_form("pdf")


# ---------------------------------------------------------------------------
# _rename_columns_labels_duplicates
# ---------------------------------------------------------------------------


def test_rename_columns_labels_duplicates():
    structure = [
        Question("q1", "text", "Name"),
        Question("q2", "text", "Name"),
        Question("q3", "text", "Age"),
    ]
    f = _make_form()
    f._rename_columns_labels_duplicates(structure)

    assert structure[0].label == "Name (1)"
    assert structure[1].label == "Name (2)"
    assert structure[2].label == "Age"


def test_rename_columns_labels_no_duplicates():
    structure = [Question("q1", "text", "Name"), Question("q2", "text", "Age")]
    f = _make_form()
    f._rename_columns_labels_duplicates(structure)

    assert structure[0].label == "Name"
    assert structure[1].label == "Age"


# ---------------------------------------------------------------------------
# _remove_unused_columns
# ---------------------------------------------------------------------------


def test_remove_unused_columns():
    f = _make_form()
    f.data = pd.DataFrame(
        {
            "name": ["Alice"],
            "_version_": ["v1"],
            "formhub/uuid": ["uuid1"],
            "meta/instanceID": ["id1"],
            "_xform_id_string": ["xid"],
        }
    )
    f._remove_unused_columns()

    assert "name" in f.data.columns
    for col in ("_version_", "formhub/uuid", "meta/instanceID", "_xform_id_string"):
        assert col not in f.data.columns


def test_remove_unused_columns_none_present():
    """Should not raise when none of the system columns are in the DF."""
    f = _make_form()
    f.data = pd.DataFrame({"name": ["Alice"]})
    f._remove_unused_columns()
    assert list(f.data.columns) == ["name"]


# ---------------------------------------------------------------------------
# _extract_repeats
# ---------------------------------------------------------------------------


def test_extract_repeats():
    rows = [
        {
            "name": "Alice",
            "children": [
                {"child_name": "Charlie"},
                {"child_name": "Diana"},
            ],
        },
        {
            "name": "Bob",
            "children": [{"child_name": "Eve"}],
        },
    ]
    f = _make_form()
    f._extract_repeats(rows)

    assert f.has_repeats is True
    assert "children" in f.repeats
    df = f.repeats["children"]
    assert len(df) == 3
    assert list(df["child_name"]) == ["Charlie", "Diana", "Eve"]
    assert list(df["_parent_index"]) == [1, 1, 2]


def test_extract_repeats_strips_group_prefix():
    """Column names with a group/repeat prefix should be reduced to the last segment."""
    rows = [
        {
            "grp/kids": [
                {"grp/kids/age": "5"},
            ]
        }
    ]
    f = _make_form()
    f._extract_repeats(rows)

    df = f.repeats["kids"]
    assert "age" in df.columns


# ---------------------------------------------------------------------------
# fetch_data
# ---------------------------------------------------------------------------


def test_fetch_data_api_error(monkeypatch):
    """A non-200 response from the data endpoint should return an empty DataFrame."""
    f = _make_form()
    responses = [MockResponse(_ASSET, 200), MockResponse({}, 500)]
    idx = [0]

    def mock_get(*args, **kwargs):
        r = responses[idx[0]]
        idx[0] += 1
        return r

    monkeypatch.setattr(requests, "get", mock_get)
    result = f.fetch_data()

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0


def test_fetch_data_columns_and_index(monkeypatch):
    f = _make_form()
    monkeypatch.setattr(requests, "get", _two_call_mock(_ASSET, _SUBMISSIONS))
    f.fetch_data()

    assert f.data is not None
    assert len(f.data) == 2
    for col in ("full_name", "gender", "activities", "_index"):
        assert col in f.data.columns
    assert list(f.data["_index"]) == [1, 2]


def test_fetch_data_select_one_values(monkeypatch):
    f = _make_form()
    monkeypatch.setattr(requests, "get", _two_call_mock(_ASSET, _SUBMISSIONS))
    f.fetch_data()

    assert list(f.data["gender"]) == ["female", "male"]


def test_fetch_data_select_multiple_separator(monkeypatch):
    """After fetch_data the space-separator from the API is replaced with '|'."""
    f = _make_form()
    monkeypatch.setattr(requests, "get", _two_call_mock(_ASSET, _SUBMISSIONS))
    f.fetch_data()

    assert f.data["activities"].tolist() == ["sport|music", "sport"]


def test_fetch_data_missing_columns_added(monkeypatch):
    """Columns present in the survey but absent from the API response are added as NaN."""
    submissions_missing_col = [{"full_name": "Alice"}]
    f = _make_form()
    monkeypatch.setattr(
        requests, "get", _two_call_mock(_ASSET, submissions_missing_col)
    )
    f.fetch_data()

    assert "gender" in f.data.columns
    assert "activities" in f.data.columns


# ---------------------------------------------------------------------------
# display
# ---------------------------------------------------------------------------


def test_display_columns_as_label(monkeypatch):
    f = _make_form()
    monkeypatch.setattr(requests, "get", _two_call_mock(_ASSET, _SUBMISSIONS))
    f.fetch_data()
    f.display(columns_as="label")

    assert "Full name" in f.data.columns
    assert "Gender" in f.data.columns
    assert "Activities" in f.data.columns
    assert "full_name" not in f.data.columns


def test_display_choices_as_label(monkeypatch):
    f = _make_form()
    monkeypatch.setattr(requests, "get", _two_call_mock(_ASSET, _SUBMISSIONS))
    f.fetch_data()
    f.display(choices_as="label")

    assert list(f.data["gender"]) == ["Female", "Male"]
    assert f.data["activities"].tolist() == ["Sport|Music", "Sport"]


def test_display_roundtrip(monkeypatch):
    """Switching to labels and back to names should restore original values."""
    f = _make_form()
    monkeypatch.setattr(requests, "get", _two_call_mock(_ASSET, _SUBMISSIONS))
    f.fetch_data()
    f.display(columns_as="label", choices_as="label")
    f.display(columns_as="name", choices_as="name")

    assert "full_name" in f.data.columns
    assert list(f.data["gender"]) == ["female", "male"]
    assert f.data["activities"].tolist() == ["sport|music", "sport"]


def test_display_noop_when_already_set(monkeypatch):
    """Calling display with the current settings should not change the DataFrame."""
    f = _make_form()
    monkeypatch.setattr(requests, "get", _two_call_mock(_ASSET, _SUBMISSIONS))
    f.fetch_data()
    cols_before = list(f.data.columns)
    f.display(columns_as="name", choices_as="name")
    assert list(f.data.columns) == cols_before
