from typing import Union

import requests

from .form import KoboForm


class Manager:
    def __init__(self, url: str, api_version: int, token: str) -> None:
        self.url = url.rstrip("/")
        self.api_version = api_version
        self.token = token
        self.headers = {"Authorization": f"Token {token}"}
        self._assets = None

    @property
    def api_version(self):
        return self._api_version

    @api_version.setter
    def api_version(self, value):
        if value != 2:
            raise ValueError("The value of 'api_version' has to be: 2.")
        self._api_version = value

    def _fetch_forms(self) -> None:
        """Fetch the list of forms the user has access to with its token."""
        url_assets = f"{self.url}/api/v{self.api_version}/assets.json"

        res = requests.get(url=url_assets, headers=self.headers)

        # If error while fetching the data, return an empty list
        if res.status_code != 200:
            return []

        results = res.json()["results"]

        # It seems that when uploading an XLSForm from the website to create
        # a new form and there is an issue during the upload, the form
        # will be visible in the API but not in the UI. In this case it will
        # have the property "asset_type" set to "empty" instead of "survey"
        # for a working form. We don't want to keep them so we filter them out.
        # This issue seems to be very rare.
        results = [r for r in results if r["asset_type"] != "empty"]

        return results

    def _create_koboform(self, form: dict) -> KoboForm:
        kform = KoboForm(uid=form["uid"])
        kform._extract_from_asset(form)
        kform.headers = self.headers

        return kform

    def get_forms(self) -> list:
        if not self._assets:
            self._assets = self._fetch_forms()

        kforms = []
        for form in self._assets:
            kform = self._create_koboform(form)
            kforms.append(kform)
        return kforms

    def get_form(self, uid: str) -> Union[KoboForm, None]:
        if not self._assets:
            self._assets = self._fetch_forms()

        # If no forms
        if self._assets == []:
            return None

        form = [f for f in self._assets if f["uid"] == uid][0]
        kform = self._create_koboform(form)

        return kform
