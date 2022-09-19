from typing import Union

import requests
import pandas as pd
import numpy as np

from .types import Group, Question, Repeat


class Form:
    def __init__(self, uid: str) -> None:
        self.uid = uid
        self.metadata = {}
        self.data = None
        self.__structure_content = None
        self.has_geo = False
        self.geo = None
        self.__columns_as = None

    def __repr__(self):
        return f"Form('{self.uid}')"

    def _extract_from_asset(self, asset: dict) -> None:
        self.metadata['name'] = asset['name']
        self.metadata['owner'] = asset['owner__username']
        self.metadata['date_created'] = asset['date_created']
        self.metadata['date_modified'] = asset['date_modified']
        self.structure = []
        self.questions = []

        self.__url_structure = asset['url']
        self.__url_data = asset['data']
        self.__base_url = '/'.join(asset['downloads']
                                   [0]['url'].split('/')[:-1])

    def fetch_data(self, columns_as: str = 'name', answers_as: str = 'name') -> Union[pd.DataFrame, dict]:
        '''
        XXX TO DO'''
        if columns_as not in ['name', 'label']:
            raise ValueError(
                "The accepted values for the attribute 'columns_as' are 'name' or 'label'.")

        if answers_as not in ['name', 'label']:
            raise ValueError(
                "The accepted values for the attribute 'answers_as' are 'name' or 'label'.")

        self.__columns_as = columns_as

        self._get_questions()

        # Fetch the data
        res = requests.get(url=self.__url_data, headers=self.headers)

        # If error while fetching the data, return an empty DF
        if res.status_code != 200:
            return pd.DataFrame()

        data = res.json()['results']

        self.data = pd.DataFrame(data)

        # Add the groups name as prefix to the columns name
        # if there are any group
        self._rename_columns(self.data, 'name', 'name_with_prefix')

        self.has_repeats = False

        self._extract_repeats(data)

        # If the form has at least one repeat group
        if self.has_repeats:

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

        if columns_as == 'label':
            self._rename_columns(self.data, 'name_with_prefix', 'label')
            # if self.has_repeats:
            #     for repeat_name, repeat_data in self.repeats.items():
            #         print(repeat_data.columns)
            #         self._rename_columns(
            #             repeat_data, 'name_with_prefix', 'label')
            #         print(repeat_data.columns)

        self._split_gps_coords()

        self._remove_metadata()

    def _fetch_structure_content(self):
        res = requests.get(
            url=self.__url_structure, headers=self.headers)
        self.__structure_content = res.json()['content']

    def _get_questions(self) -> None:
        '''TO DO'''

        if not self.__structure_content:
            self._fetch_structure_content()

        fields = self.__structure_content['survey']
        prefix_name = ''
        prefix_label = ''
        for idx, field in enumerate(fields):
            if field['type'] == 'begin_group' or field['type'] == 'begin_repeat':
                if prefix_name == '':
                    prefix_name = field['name']
                    if 'label' in field:
                        prefix_label = field['label']
                    else:
                        prefix_label = prefix_name
                else:
                    prefix_name = f"{prefix_name}/{field['name']}"
                    if 'label' in field:
                        prefix_label = f"{prefix_label}/{field['label']}"
                    else:
                        prefix_label = prefix_name
            if field['type'] == 'end_group' or field['type'] == 'end_repeat':
                prefix_name = '/'.join(prefix_name.split('/')[0: -1])
                prefix_label = '/'.join(prefix_label.split('/')[0: -1])

            if field['type'] != 'note' and field['type'] != 'begin_group' and field['type'] != 'begin_repeat' and field['type'] != 'end_group' and field['type'] != 'end_repeat':
                name_q = field['name']
                if 'label' in field:
                    label_q = field['label'][0]
                else:
                    label_q = name_q
                q = Question(idx, name_q, field['type'], label_q)
                if prefix_name == '':
                    q.name_with_prefix = name_q
                    q.label_with_prefix = label_q
                else:
                    q.name_with_prefix = f'{prefix_name}/{name_q}'
                    q.label_with_prefix = f'{prefix_label}/{label_q}'

                self.questions.append(q)

                # Identify the geopoint if any
                if field['type'] == 'geopoint':
                    self.has_geo = True
                    self.geo = q

        for q in self.questions:
            print(q)

    def _rename_columns(self, df, old, new):
        dict_rename = {}
        for q in self.questions:
            dict_rename[getattr(q, old)] = getattr(q, new)
        df.rename(columns=dict_rename, inplace=True)

    # def _answers_as_label(self) -> None:

    #     if not self.__structure_content:
    #         self._fetch_structure_content()

    #     df = self.data

    #     formatted_choices = {}
    #     choices = self.__structure_content['choices']
    #     for choice in choices:
    #         if choice['list_name'] not in formatted_choices:
    #             formatted_choices[choice['list_name']] = []
    #         formatted_choices[choice['list_name']].append(
    #             {'name': choice['name'], 'label': choice['label'][0]})

    #     for column in form_columns:
    #         if column['select_one'] or column['select_multiple']:
    #             if column['select_one']:
    #                 uid_choice = column['select_one']

    #                 for choice in formatted_choices[uid_choice]:
    #                     df.loc[df[column['label']] == choice['name'],
    #                            column['label']] = choice['label']

    #             else:
    #                 uid_choice = column['select_multiple']
    #             column['value_labels'] = formatted_choices[uid_choice]

    #     # For multiple values we have to loop again
    #     for column in form_columns:
    #         if column['select_multiple']:
    #             unique_values = list(df[column['label']].unique())

    #             for unique in unique_values:
    #                 if pd.isna(unique):
    #                     pass
    #                 else:
    #                     combinations = unique.split()
    #                     label = [c['label']
    #                              for c in column['value_labels'] if c['name'] in combinations]
    #                     label_formatted = ', '.join(label)

    #                     df.loc[df[column['label']] == unique,
    #                            column['label']] = label_formatted

    def _extract_repeats(self, rows: list) -> None:
        '''TO DO

        '_parent_index' is the column name used in Kobo in the child table
        when downloading the data, that allow to join the data with the parent table
        '''
        repeats = {}
        for idx_parent, row in enumerate(rows):
            for column, value in row.items():
                if not column.startswith('_') and type(value) == list:
                    if column not in repeats:
                        repeats[column] = []
                    for child in value:
                        child['_parent_index'] = idx_parent + 1
                    repeats[column] = repeats[column] + value

        if repeats:
            for repeat_name, repeat_data in repeats.items():
                print(repeat_name)
                repeats[repeat_name] = pd.DataFrame(repeat_data)

                # In the repeat groups the columns names have the
                # name of their repeat group has a prefix.
                # This is not necessary, we remove the prefix
                dict_rename = {}
                for c in repeats[repeat_name].columns:
                    dict_rename[c] = c.replace(f'{repeat_name}/', '')
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

        if geo_column in self.data.columns:

            self.data[['latitude', 'longitude', 'altitude', 'gps_precision']
                      ] = self.data[geo_column].str.split(' ', expand=True)

            self.data.drop(geo_column, axis=1, inplace=True)

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
