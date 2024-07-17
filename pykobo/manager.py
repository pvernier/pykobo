import json
import logging
import os
import time
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

        form_list = [f for f in self._assets if f["uid"] == uid]

        if len(form_list) == 0:
            raise ValueError(f"There is no form with the uid: {uid}.")

        form = form_list[0]
        kform = self._create_koboform(form)

        return kform

    def redeploy_form(self, uid: str) -> None:
        url = f"{self.url}/api/v{self.api_version}/assets/{uid}/deployment/?format=json"
        requests.patch(url=url, headers=self.headers)

    def upload_media_from_local(
        self, uid: str, folder_path: str, file_name: str, rewrite: bool = False
    ) -> None:
        file_extension = os.path.splitext(file_name)[1]
        valid_media = [".jpeg", ".jpg", ".png", ".csv", ".JPGE", ".JPG", ".PNG"]

        if not folder_path.endswith(("/", "\\")):
            folder_path += "/"

        if file_extension not in valid_media:
            raise ValueError(
                "upload_media_from_local: file extension must be one of %r."
                % valid_media
            )

        file_path = os.path.join(folder_path, file_name)

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        self._upload_media(uid, open(file_path, "rb"), file_name, rewrite)

    def upload_media_from_server(
        self, uid: str, media_data: bytes, file_name: str, rewrite: bool = False
    ) -> None:
        self._upload_media(uid, media_data, file_name, rewrite)

    def _upload_media(
        self, uid: str, media_data: bytes, file_name: str, rewrite: bool
    ) -> None:
        url_media = f"{self.url}/api/v{self.api_version}/assets/{uid}/files"
        payload = {"filename": file_name}
        data = {
            "description": "default",
            "metadata": json.dumps(payload),
            "data_value": file_name,
            "file_type": "form_media",
        }

        res = requests.get(f"{url_media}.json", headers=self.headers)
        res.raise_for_status()
        dict_response = res.json()["results"]

        for each in dict_response:
            if each["metadata"]["filename"] == file_name:
                if rewrite:
                    del_id = each["uid"]
                    res.status_code = 403
                    while res.status_code != 204:
                        res = requests.delete(
                            f"{url_media}/{del_id}", headers=self.headers
                        )
                        time.sleep(1)
                    break
                else:
                    raise ValueError(
                        "There is already a file with the same name! Select a new name or set 'rewrite=True'"
                    )

        files = {"content": (file_name, media_data)}  # Pass media_data directly

        res = requests.post(
            url=f"{url_media}.json", data=data, files=files, headers=self.headers
        )
        res.raise_for_status()

        if res.status_code == 201:
            logging.info(f"Successfully uploaded {file_name} to {uid} form.")
        else:
            logging.error(f"Unsuccessful. Response code: {str(res.status_code)}")

    def share_project(self, uid: str, user: str, permission: str):
        """
        Share a project with a user.

        Parameters
        ----------
        uid : str
            The project's uid.
        user : str
            The user's uid.
        permission : str
            The permission to give the user.
        """

        valid_permissions = [
            "add_submissions",
            "change_asset",
            "change_submissions",
            "delete_submissions",
            "discover_asset",
            "manage_asset",
            "partial_submissions",
            "validate_submissions",
            "view_asset",
            "view_submissions",
        ]

        if permission not in valid_permissions:
            raise ValueError(
                "Permission must be one of the following: " + str(valid_permissions)
            )

        data = {
            "user": f"{self.url}/api/v{self.api_version}/users/{user}/",
            "permission": f"{self.url}/api/v{self.api_version}/permissions/{permission}/",
        }

        url = f"{self.url}/api/v{self.api_version}/assets/{uid}/permission-assignments.json"
        res = requests.post(url=url, headers=self.headers, data=data)

        if res.status_code != 201:
            raise requests.HTTPError(res.text)

    def fetch_users_with_access(self, uid: str):
        """
        Fetch the list of users who have access to a specific form, extracting usernames from URLs.
        """
        url_permissions = (
            f"{self.url}/api/v{self.api_version}/assets/{uid}/permission-assignments/"
        )
        res = requests.get(url=url_permissions, headers=self.headers)

        if res.status_code != 200:
            raise requests.HTTPError(f"Failed to fetch permissions: {res.text}")

        permissions = res.json()
        users_with_access = set()

        for permission in permissions:
            user_url = permission.get("user")
            if user_url:
                username = user_url.rstrip("/").split("/")[
                    -1
                ]  # Split to get the username from the url
                users_with_access.add(username)

        return list(users_with_access)
