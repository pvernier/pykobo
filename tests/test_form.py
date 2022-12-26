import json

from pykobo.form import KoboForm

uid = "cSatm9oFcA3e9dwJdHUrBZ"
kform = KoboForm(uid=uid)


metadata_form = {
    "name": "Form 1",
    "owner": "owner1",
    "date_created": "2022-12-05T14:36:19.800395Z",
    "date_modified": "2022-12-05T14:42:03.913134Z",
    "version_id": "sTEcVocX5XRYD5uWabjtdv",
    "has_deployment": True,
    "geo": False,
}


def test_extract_from_asset():
    with open("./tests/data_form.json") as f:
        data_form = json.load(f)

    kform._extract_from_asset(data_form)
    assert kform.metadata == metadata_form

    assert kform.url_asset == data_form["url"]
    assert kform.url_data == data_form["data"]
    assert kform.base_url == "https://kf.kobotoolbox.org/api/v2/assets"
