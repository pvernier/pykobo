import requests
import pandas as pd
import numpy as np


class Manager:
    def __init__(self, url_api, format, token) -> None:
        self.url_api = url_api
        self.format = format
        self.token = token
        self.headers = {"Authorization": f'Token {token}'}

    def get_forms(self) -> dict:
        '''Return a dictionary of all the forms the user has access to with its token.
        The keys are the UID and the values, the name of the forms'''
        url_assets = f'{self.url_api}/assets.json'
        res = requests.get(
            url=url_assets, headers=self.headers)

        # If error while fetching the data, return an empty dict
        if res.status_code != 200:
            return {}

        forms = {}
        for form in res.json()['results']:
            forms[form['uid']] = form['name']
        return forms

    def get_url_data_form(self, uid: str) -> str:
        '''Given the uid of a form
        returns the URL of the data in JSON'''

        return f'{self.url_api}/assets/{uid}/data?format={self.format}'

    def get_url_data_metadata(self, uid: str) -> str:
        '''Given the uid of a form
        returns the URL of the metadata in JSON'''

        return f'{self.url_api}/assets/{uid}/?format={self.format}'

    def fetch_form_data(self, uid: str, with_labels: bool = False) -> pd.DataFrame:
        '''Given the uid of a form
        returns the data as a Pandas DataFrame
        The boolean `with_labels` indicates if we return the DataFrame with labels
        for the columns name and values or without (default)'''

        # Get the URL of the data for that form
        url = self.get_url_data_form(uid)

        # Fetch the data
        res = requests.get(url=url, headers=self.headers)

        # If error while fetching the data, return an empty DF
        if res.status_code != 200:
            return pd.DataFrame()

        data = res.json()['results']
        df = pd.DataFrame(data)

        if with_labels:
            self._fetch_form_labels(df, uid)

        return df

    def _fetch_form_labels(self, df: pd.DataFrame, uid: str) -> None:
        '''TO DO'''
        # Fetch the metadata
        url_meta = self.get_url_data_metadata(uid)
        res_meta = requests.get(
            url=url_meta, headers=self.headers)

        fields = res_meta.json()['content']['survey']
        form_columns = []

        # Columns labels
        for field in fields:
            try:
                name = field['name']
            except KeyError:
                name = field['$autoname']

            # The JSON object doesn't have properties for empty columns
            # so we need to add them here to do not get issues later
            if name not in df.columns:
                df[name] = np.nan

            if 'label' in field:
                label = field['label'][0]
            else:
                label = field['name']

            if field['type'] == 'select_one':
                select_one = field['select_from_list_name']
            else:
                select_one = None

            if field['type'] == 'select_multiple':
                select_multiple = field['select_from_list_name']
            else:
                select_multiple = None

            form_columns.append({'name': name, 'label': label, 'select_one': select_one,
                                'select_multiple': select_multiple})
            dict_rename = {}
            for column in form_columns:
                dict_rename[column['name']] = column['label']

        df.rename(columns=dict_rename, inplace=True)

        # Values labels
        formatted_choices = {}
        choices = res_meta.json()['content']['choices']
        for choice in choices:
            if choice['list_name'] not in formatted_choices:
                formatted_choices[choice['list_name']] = []
            formatted_choices[choice['list_name']].append(
                {'name': choice['name'], 'label': choice['label'][0]})

        for column in form_columns:
            if column['select_one'] or column['select_multiple']:
                if column['select_one']:
                    uid_choice = column['select_one']

                    for choice in formatted_choices[uid_choice]:
                        df.loc[df[column['label']] == choice['name'],
                               column['label']] = choice['label']

                else:
                    uid_choice = column['select_multiple']
                column['value_labels'] = formatted_choices[uid_choice]

        # For multiple values we have to loop again
        for column in form_columns:
            if column['select_multiple']:
                unique_values = list(df[column['label']].unique())

                for unique in unique_values:
                    if pd.isna(unique):
                        pass
                    else:
                        combinations = unique.split()
                        label = [c['label']
                                 for c in column['value_labels'] if c['name'] in combinations]
                        label_formatted = ', '.join(label)

                        df.loc[df[column['label']] == unique,
                               column['label']] = label_formatted

    def remove_metadata(self, df: pd.DataFrame) -> pd.DataFrame:
        '''Remove the metadata columns (meaning the ones starting with an '_',
        plus the 4 columns: 'formhub/uuid', 'meta/instanceID', 'start', 'end') 
        of the DataFrame'''

        metadata_columns = [
            column for column in df.columns if column.startswith('_')]

        others = ['formhub/uuid', 'meta/instanceID', 'start',
                  'end', 'today',  'username', 'deviceid']

        # We only keep the columns that are in the DataFrame
        others = [
            o for o in others if o in df.columns]

        metadata_columns = metadata_columns + others

        df.drop(metadata_columns, axis=1, inplace=True)

    def split_gps_coords(self, df: pd.DataFrame, gps_field: str) -> pd.DataFrame:

        if gps_field not in df.columns:
            raise ValueError(
                f"The DataFrame doesn't contain the column '{gps_field}'")

        df[['latitude', 'longitude', 'altitude', 'gps_precision']
           ] = df[gps_field].str.split(' ', expand=True)

        df.drop(gps_field, axis=1, inplace=True)

        return df

    def download_form(self, uid: str, format: str) -> None:
        '''Given the uid of a form and a format ('xls' or 'xml')
        download the form in that format'''

        if format not in ['xls', 'xml']:
            raise ValueError(
                f"The file format {format} is not supported. Recognized format are 'xls' and 'xml'")

        URL = f"{self.url_api}/assets/{uid}.{format}"
        filename = URL.split('/')[-1]

        r = requests.get(URL, headers=self.headers)

        with open(filename, 'wb') as f:
            f.write(r.content)
