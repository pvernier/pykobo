from typing import Union

import requests
import pandas as pd
import numpy as np

from .types import Question


class KoboForm:
    def __init__(self, uid: str) -> None:
        self.uid = uid
        self.metadata = {}
        self.data = None
        self.has_geo = False
        self.geo = False
        self.has_repeats = False
        self.repeats = {}
        self.__root_structure = []
        self.__repeats_structure = {}
        self.__content = None
        self.__columns_as = 'name'
        self.__choices_as = 'name'

    def __repr__(self):
        return f"KoboForm('{self.uid}')"

    def fetch_data(self) -> Union[pd.DataFrame, dict]:
        '''Fetch the form's data and store them as a Pandas DF in the attribute `data`.
        If the form has repeat groups, extract them as separate DFs'''

        self._get_survey()
        self._get_choices()

        # Fetch the data
        res = requests.get(url=self.__url_data, headers=self.headers)

        # If error while fetching the data, return an empty DF
        if res.status_code != 200:
            return pd.DataFrame()

        data = res.json()['results']

        self.data = pd.DataFrame(data)

        # Rename columns to remove the prefix composed of the groups in which
        # the question is.
        __dict_rename = {}
        for c in self.data.columns:
            __dict_rename[c] = c.split('/')[-1]

        self.data.rename(columns=__dict_rename, inplace=True)

        # If the form has at least one repeat group
        if self.has_repeats:

            self._extract_repeats(data)

            # Add a column '_index' that can be used to join with the parent DF
            # with the children DFs (which have the column '_parent_index')
            self.data['_index'] = self.data.index + 1

            # Move column '_index' to the first position
            col_idx_parent = self.data.pop('_index')
            self.data.insert(0, col_idx_parent.name, col_idx_parent)

            # In the parent DF delete the columns that contain the repeat groups
            # In the API there is a column with the same name as the name of
            # the repeat group + the suffix '_count' just before the repeat group.
            # We can delete it
            repeats_count = [f'{c}_count' for c in self.repeats.keys()]
            to_delete = list(self.repeats.keys()) + repeats_count

            self.data.drop(columns=to_delete, inplace=True)

            if self.has_geo:
                self._split_gps_coords()

    def display(self, columns_as: str = 'name', choices_as: str = 'name') -> None:
        pass

    def _fetch_asset(self):
        res = requests.get(
            url=self.__url_asset, headers=self.headers)
        self.__content = res.json()['content']

    def _get_survey(self) -> None:
        '''Go through all the elements of the survey and build the root structure (and the structure
        of the repeat groups if any) as a list of `Question` objects. Each `Question` object has a name
        and a label so it's possible to display the data using any of the two.'''

        if not self.__content:
            self._fetch_asset()

        survey = self.__content['survey']

        group_name = None
        group_label = None
        repeat_name = None
        repeat_label = None
        in_repeat = False

        for idx, field in enumerate(survey):

            # Identify groups and repeats if any
            if field['type'] == 'begin_group':

                group_name = field['name']
                if 'label' in field:
                    group_label = field['label']

            if field['type'] == 'begin_repeat':

                repeat_name = field['name']
                if 'label' in field:
                    repeat_label = field['label']

                in_repeat = True
                self.has_repeats = True
                self.__repeats_structure[repeat_name] = []

            if field['type'] == 'end_group':
                group_name = None
                group_label = None

            if field['type'] == 'end_repeat':
                in_repeat = False
                repeat_name = None
                repeat_label = None

            if field['type'] != 'begin_group' and field['type'] != 'begin_repeat' and field['type'] != 'end_group' and field['type'] != 'end_repeat':
                name_q = field['name']
                if 'label' in field:
                    label_q = field['label'][0]
                else:
                    label_q = name_q
                q = Question(idx, name_q, field['type'], label_q)

                if field['type'] == 'select_one' or field['type'] == 'select_multiple':
                    q.select_from_list_name = field['select_from_list_name']

                q.group_name = group_name
                q.group_label = group_label

                q.repeat_name = repeat_name
                q.repeat_label = repeat_label

                # Identify the geopoint if any
                if field['type'] == 'geopoint':
                    self.has_geo = True
                    self.geo = q

                if in_repeat:
                    self.__repeats_structure[repeat_name].append(q)
                else:
                    self.__root_structure.append(q)

    def _get_choices(self):
        '''For all the questions of type 'select_one' or 'select_multiple' assign their corresponding choices.
        Each choice has a name and label so it's possible to display the data using any of the two.'''

        formatted_choices = {}
        choices = self.__content['choices']
        for choice in choices:
            if choice['list_name'] not in formatted_choices:
                formatted_choices[choice['list_name']] = []
            formatted_choices[choice['list_name']].append(
                {'name': choice['name'], 'label': choice['label'][0]})

        for q in self.__root_structure:
            if q.type == 'select_one' or q.type == 'select_multiple':
                q.choices = formatted_choices[q.select_from_list_name]

        if self.has_repeats:
            for k, repeat in self.__repeats_structure.items():
                for q in repeat:
                    if q.type == 'select_one' or q.type == 'select_multiple':
                        q.choices = formatted_choices[q.select_from_list_name]

    def _extract_from_asset(self, asset: dict) -> None:
        self.metadata['name'] = asset['name']
        self.metadata['owner'] = asset['owner__username']
        self.metadata['date_created'] = asset['date_created']
        self.metadata['date_modified'] = asset['date_modified']

        self.__url_asset = asset['url']
        self.__url_data = asset['data']
        self.__base_url = '/'.join(asset['downloads']
                                   [0]['url'].split('/')[:-1])

    def _rename_columns(self, df, old, new):
        dict_rename = {}
        for q in self.questions:
            dict_rename[getattr(q, old)] = getattr(q, new)
        df.rename(columns=dict_rename, inplace=True)

    def _extract_repeats(self, rows: list) -> None:
        '''Extract all the questions part of repeat groups into separate DFs
         (on eper repat group).
        '_parent_index' is the column name used in Kobo in the child table
        when downloading the data, that allow to join the data with the parent table
        '''
        repeats = {}
        for idx_parent, row in enumerate(rows):
            for column, value in row.items():
                if not column.startswith('_') and type(value) == list:
                    repeat_name = column.split('/')[-1]
                    if repeat_name not in repeats:
                        repeats[repeat_name] = []
                    for child in value:
                        child['_parent_index'] = idx_parent + 1
                    repeats[repeat_name] = repeats[repeat_name] + value

        for repeat_name, repeat_data in repeats.items():
            repeats[repeat_name] = pd.DataFrame(repeat_data)

            # If columns have a prefix composed of all their groups,
            # remove them
            dict_rename = {}
            for c in repeats[repeat_name].columns:
                dict_rename[c] = c.split('/')[-1]
            repeats[repeat_name].rename(columns=dict_rename, inplace=True)

            # Move column "_parent_index" to the first position
            col_idx_join = repeats[repeat_name].pop('_parent_index')
            repeats[repeat_name].insert(0, col_idx_join.name, col_idx_join)

            self.has_repeats = True
            self.repeats = repeats

    def _remove_metadata(self) -> pd.DataFrame:
        '''Remove the metadata columns (meaning the ones starting with an '_',
        plus the 4 columns: 'formhub/uuid', 'meta/instanceID', 'start', 'end') 
        of the DataFrame'''

        self._delete_columns_in_df(self.data)

        if self.has_repeats:
            for k, v in self.repeats.items():
                self._delete_columns_in_df(v)

    def _delete_columns_in_df(self, df: pd.DataFrame) -> None:

        metadata_columns = [
            column for column in df.columns if column.startswith('_')]

        # If we have repeat groups, keep the columns that make the join
        # possible between the parent and children DFs
        if self.has_repeats:
            if '_index' in df.columns:
                metadata_columns.remove('_index')
            if '_parent_index' in df.columns:
                metadata_columns.remove('_parent_index')

        others = ['formhub/uuid', 'meta/instanceID', 'start',
                  'end', 'today',  'username', 'deviceid']

        # We only keep the columns that are in the DataFrame
        others = [
            o for o in others if o in df.columns]

        metadata_columns = metadata_columns + others

        df.drop(metadata_columns, axis=1, inplace=True)

    def _split_gps_coords(self) -> None:
        '''Split the column of type 'geopoint' into 4 columns
        'latitude', 'longitude', 'altitude', 'gps_precision'
        XXX It assumes this column is in the parent DF (self.data)
        not in a repeat group. TO IMPROVE
        '''

        geo_column = getattr(self.geo, self.__columns_as)

        base_geo_columns = ['latitude', 'longitude', 'altitude', 'precision']

        new_geo_columns = [f'_{geo_column}_{c}' for c in base_geo_columns]

        if geo_column in self.data.columns:

            self.data[new_geo_columns
                      ] = self.data[geo_column].str.split(' ', expand=True)

            # self.data.drop(geo_column, axis=1, inplace=True)

    def download_form(self, format: str) -> None:
        '''Given the uid of a form and a format ('xls' or 'xml')
        download the form in that format in the current directory'''

        if format not in ['xls', 'xml']:
            raise ValueError(
                f"The file format '{format}' is not supported. Recognized formats are 'xls' and 'xml'")

        URL = f"{self.__base_url}/{self.uid}.{format}"
        filename = URL.split('/')[-1]

        r = requests.get(URL, headers=self.headers)

        with open(filename, 'wb') as f:
            f.write(r.content)
