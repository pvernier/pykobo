import requests

from .form import Form


class Manager:
    def __init__(self, url_api: str, token: str) -> None:
        self.url_api = url_api
        self.token = token
        self.headers = {"Authorization": f'Token {token}'}
        self._assets = None

    def get_forms(self) -> list:
        '''Return a list of all the forms the user has access to with its token.
        The elements of that list are Form objects'''
        url_assets = f'{self.url_api}/assets.json'

        res = requests.get(
            url=url_assets, headers=self.headers)

        # If error while fetching the data, return an empty list
        if res.status_code != 200:
            return []

        self._assets = res.json()['results']

        forms = []
        for form in self._assets:
            f = Form(uid=form['uid'])
            f._extract_from_asset(form)
            f.headers = self.headers
            forms.append(f)
        return forms

    def get_form(self, uid: str) -> Form:
        if not self._assets:
            forms = self.get_forms()
        form = [f for f in forms if f.uid == uid][0]

        return form

    # def get_url_data_form(self, uid: str) -> str:
    #     '''Given the uid of a form
    #     returns the URL of the data in JSON'''

    #     return f'{self.url_api}/assets/{uid}/data?format=json'

    # def get_url_data_metadata(self, uid: str) -> str:
    #     '''Given the uid of a form
    #     returns the URL of the metadata in JSON'''

    #     return f'{self.url_api}/assets/{uid}/?format=json'
