import requests

from .form import KoboForm


class Manager:
    def __init__(self, url_api: str, token: str) -> None:
        self.url_api = url_api
        self.token = token
        self.headers = {"Authorization": f"Token {token}"}
        self._assets = None

    def _fetch_forms(self) -> None:
        """Fetch the list of forms the user has access to with its token."""
        url_assets = f"{self.url_api}/assets.json"

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

        self._assets = results

    def _create_koboform(self, form: dict) -> KoboForm:
        kform = KoboForm(uid=form["uid"])
        kform._extract_from_asset(form)
        kform.headers = self.headers

        return kform

    def get_forms(self) -> list[KoboForm]:
        if not self._assets:
            self._fetch_forms()

        kforms = []
        for form in self._assets:
            kform = self._create_koboform(form)
            kforms.append(kform)
        return kforms

    def get_form(self, uid: str) -> KoboForm:
        if not self._assets:
            self._fetch_forms()

        form = [f for f in self._assets if f["uid"] == uid][0]
        kform = self._create_koboform(form)

        return kform
