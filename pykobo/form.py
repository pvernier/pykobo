from typing import Union

import numpy as np
import pandas as pd
import requests

from .features import Question


class KoboForm:
    def __init__(self, uid: str) -> None:
        self.uid = uid
        self.headers = None
        self.metadata = {}
        self.data = None
        self.has_geo = False
        self.geo = []
        self.has_repeats = False
        self.repeats = {}
        self.__root_structure = []
        self.__repeats_structure = {}
        self.__asset = None
        self.__content = None
        self.__columns_as = "name"
        self.__choices_as = "name"
        self.naming_conflicts = None
        self.separator = "|"
        self.__initial_separator = " "

    def __repr__(self):
        return f"KoboForm('{self.uid}')"

    def fetch_data(self) -> Union[pd.DataFrame, dict]:
        """Fetch the form's data and store them as a Pandas DF in the attribute `data`.
        If the form has repeat groups, extract them as separate DFs"""

        self._get_survey()

        # It's possible for a form to have no "choices" (corresponds to
        # a XLSForm without a tab "choices"). In this case we don't call
        # the method '_get_choices'
        if "choices" in self.__content:
            self._get_choices()

        # Fetch the data
        res = requests.get(url=self.url_data, headers=self.headers)

        # If error while fetching the data, return an empty DF
        if res.status_code != 200:
            return pd.DataFrame()

        data = res.json()["results"]

        self.data = pd.DataFrame(data)

        self._remove_unused_columns()

        # For columns containing the group(s) they belong to in their name, remove it to only
        # keep the name of the column
        __dict_rename = {}
        for c in self.data.columns:
            __dict_rename[c] = c.split("/")[-1]

        self.data.rename(columns=__dict_rename, inplace=True)

        # Add a column '_index' that can be used to join the parent DF
        # with the children DFs (which have the column '_parent_index')
        self.data["_index"] = self.data.index + 1

        # If the form has at least one repeat group
        if self.has_repeats:

            self._extract_repeats(data)

            # In the parent DF delete the columns that contain the repeat groups
            # In the API there is a column with the same name as the name of
            # the repeat group + the suffix '_count' just before the repeat group.
            # We can delete it
            repeats_count = [f"{c}_count" for c in self.repeats.keys()]
            to_delete = list(self.repeats.keys()) + repeats_count

            self.data.drop(columns=to_delete, inplace=True)

        # The JSON object returned by the API containing the form data doesn't
        # have properties for empyty columns. So, here all empty columns are missing.
        # We need to add them
        for q in self.__root_structure:
            if q.name not in self.data.columns:
                self.data[q.name] = np.nan
        if self.has_repeats:
            for k, v in self.repeats.items():
                for q in self.__repeats_structure[k]["columns"]:
                    if q.name not in v.columns:
                        v[q.name] = np.nan

        if self.has_geo:
            self._split_gps_coords()

        # At this point we don't add or delete columns any more
        # so we can reorder the columns as they are in the API

        # the columns that are in the DF but not in the structure
        # will be moved to the end
        last_columns = [
            c
            for c in self.data.columns
            if c not in [q.name for q in self.__root_structure]
        ]

        columns_ordered = [q.name for q in self.__root_structure] + last_columns

        self.data = self.data[columns_ordered]

        if self.has_repeats:
            for k, v in self.repeats.items():
                columns_ordered = [
                    q.name for q in self.__repeats_structure[k]["columns"]
                ]

                # The column'_parent_index' will be in the last position
                columns_ordered.append("_parent_index")

                self.repeats[k] = self.repeats[k][columns_ordered]

        # We need to run `_change_choices` here in order to format the multiple choices
        # so that it's possible to go back and forth between name and label for the choices
        # In the Kobo API, multiple choices are seprated by ' '. We replace ' ' with self.separator
        self._change_choices(self.data, self.__root_structure, self.__choices_as)
        if self.has_repeats:
            for k, v in self.repeats.items():
                self._change_choices(
                    v, self.__repeats_structure[k]["columns"], self.__choices_as
                )
        self.__initial_separator = self.separator

    def display(self, columns_as: str = "name", choices_as: str = "name") -> None:
        """Update the DatFrames containing the data by using names or labels for
        the columns and/or the choices based on the values of the parameters `columns_as`
        and `choices_as`."""
        if columns_as not in ["name", "label"]:
            raise ValueError(
                f"'{columns_as}' is not an accepted value for the parameter 'columns_as'. Accepted values are 'name' or 'label'."
            )

        if choices_as not in ["name", "label"]:
            raise ValueError(
                f"'{choices_as}' is not an accepted value for the parameter 'choices_as'. Accepted values are 'name' or 'label'."
            )

        # Change the columns names
        if self.__columns_as != columns_as:
            self._rename_columns(self.__columns_as, columns_as)
            self.__columns_as = columns_as

        # Change the choices names
        if self.__choices_as != choices_as:
            self._change_choices(self.data, self.__root_structure, choices_as)
            if self.has_repeats:
                for k, v in self.repeats.items():
                    self._change_choices(
                        v, self.__repeats_structure[k]["columns"], choices_as
                    )
            self.__choices_as = choices_as

    def _get_survey(self) -> None:
        """Go through all the elements of the survey and build the root structure (and the structure
        of the repeat groups if any) as a list of `Question` objects. Each `Question` object has a name
        and a label so it's possible to display the data using any of the two."""

        if not self.__asset:
            self._fetch_asset()

        if "naming_conflicts" in self.__asset["summary"]:
            self.naming_conflicts = self.__asset["summary"]["naming_conflicts"]

        survey = self.__content["survey"]

        group_name = None
        group_label = None
        repeat_name = None
        repeat_label = None
        in_repeat = False

        for field in survey:

            # Identify groups and repeats if any
            if field["type"] == "begin_group":

                group_name = field["name"]
                if "label" in field:
                    group_label = field["label"]

            if field["type"] == "begin_repeat":

                repeat_name = field["name"]
                if "label" in field:
                    repeat_label = field["label"]

                in_repeat = True
                self.has_repeats = True
                self.__repeats_structure[repeat_name] = {}
                self.__repeats_structure[repeat_name]["columns"] = []
                self.__repeats_structure[repeat_name]["has_geo"] = False
                self.__repeats_structure[repeat_name]["geo"] = False

            if field["type"] == "end_group":
                group_name = None
                group_label = None

            if field["type"] == "end_repeat":
                in_repeat = False
                repeat_name = None
                repeat_label = None

            if (
                field["type"] != "begin_group"
                and field["type"] != "begin_repeat"
                and field["type"] != "end_group"
                and field["type"] != "end_repeat"
            ):

                name_q = field["name"]
                if "label" in field:
                    label_q = field["label"][0]
                else:
                    label_q = name_q

                if (
                    self.naming_conflicts
                    and name_q in self.naming_conflicts
                    and field["type"]
                    not in [
                        "start",
                        "end",
                        "today",
                        "username",
                        "deviceid",
                        "phonenumber",
                        "calculate",
                    ]
                ):
                    name_q = f"{name_q}_001"

                q = Question(name_q, field["type"], label_q)

                if field["type"] == "select_one" or field["type"] == "select_multiple":
                    q.select_from_list_name = field["select_from_list_name"]

                q.group_name = group_name
                q.group_label = group_label

                q.repeat_name = repeat_name
                q.repeat_label = repeat_label

                if in_repeat:
                    self.__repeats_structure[repeat_name]["columns"].append(q)
                    # Identify the geopoint if any
                    if field["type"] == "geopoint":
                        self.__repeats_structure[repeat_name]["has_geo"] = True
                        self.__repeats_structure[repeat_name]["geo"].append(q)
                else:
                    self.__root_structure.append(q)
                    # Identify the geopoint if any
                    if field["type"] == "geopoint":
                        self.has_geo = True
                        self.geo.append(q)

        self._rename_columns_labels_duplicates(self.__root_structure)
        if self.has_repeats:
            for k, repeat in self.__repeats_structure.items():
                self._rename_columns_labels_duplicates(repeat["columns"])

    def _get_choices(self):
        """For all the questions of type 'select_one' or 'select_multiple' assign their corresponding choices.
        Each choice has a name and label so it's possible to display the data using any of the two."""

        formatted_choices = {}
        choices = self.__content["choices"]
        for choice in choices:
            if choice["list_name"] not in formatted_choices:
                formatted_choices[choice["list_name"]] = []
            formatted_choices[choice["list_name"]].append(
                {"name": choice["name"], "label": choice["label"][0]}
            )

        for q in self.__root_structure:
            if q.type == "select_one" or q.type == "select_multiple":
                q.choices = formatted_choices[q.select_from_list_name]

        if self.has_repeats:
            for k, repeat in self.__repeats_structure.items():
                for q in repeat["columns"]:
                    if q.type == "select_one" or q.type == "select_multiple":
                        q.choices = formatted_choices[q.select_from_list_name]

    def _change_choices(
        self, df: pd.DataFrame, structure: list, choices_as: str
    ) -> None:
        """Change the choices for the columns of type 'select_one' and 'select_multiple'
        from name to label and vice versa."""
        for q in structure:
            if q.type == "select_one":
                column = getattr(q, self.__columns_as)
                for choice in q.choices:
                    df.loc[df[column] == choice[self.__choices_as], column] = choice[
                        choices_as
                    ]

            # Multiple choices
            if q.type == "select_multiple":
                column = getattr(q, self.__columns_as)
                unique_values = list(df[column].unique())

                for unique in unique_values:
                    if pd.isna(unique):
                        pass
                    else:
                        combinations = unique.split(self.__initial_separator)
                        new_choices = [
                            c[choices_as]
                            for c in q.choices
                            if c[self.__choices_as] in combinations
                        ]
                        new_choices_formatted = f"{self.separator}".join(new_choices)

                        df.loc[df[column] == unique, column] = new_choices_formatted

    def _fetch_asset(self):
        res = requests.get(url=self.url_asset, headers=self.headers)
        self.__asset = res.json()
        self.__content = res.json()["content"]

    def _extract_from_asset(self, asset: dict) -> None:
        self.metadata["name"] = asset["name"]
        self.metadata["owner"] = asset["owner__username"]
        self.metadata["date_created"] = asset["date_created"]
        self.metadata["date_modified"] = asset["date_modified"]
        self.metadata["version_id"] = asset["version_id"]
        self.metadata["has_deployment"] = asset["has_deployment"]
        self.metadata["geo"] = asset["summary"]["geo"]

        self.url_asset = asset["url"]
        self.url_data = asset["data"]
        self.base_url = "/".join(asset["url"].split("/")[:-1])

    def _rename_columns(self, old, new):
        """Used to change the columns names from name to label and vice versa"""
        dict_rename = {}
        for q in self.__root_structure:
            dict_rename[getattr(q, old)] = getattr(q, new)

        self.data.rename(columns=dict_rename, inplace=True)

        if self.has_repeats:
            for k, repeat in self.__repeats_structure.items():
                dict_rename = {}
                for q in repeat["columns"]:
                    dict_rename[getattr(q, old)] = getattr(q, new)
                self.repeats[k].rename(columns=dict_rename, inplace=True)

    def _extract_repeats(self, rows: list) -> None:
        """Extract all the questions part of repeat groups into separate DFs
        '_parent_index' is the column name used in Kobo in the child table
        when downloading the data, that allows to join the data with the parent table
        """
        repeats = {}
        for idx_parent, row in enumerate(rows):
            for column, value in row.items():
                if not column.startswith("_") and type(value) == list:
                    repeat_name = column.split("/")[-1]
                    if repeat_name not in repeats:
                        repeats[repeat_name] = []
                    for child in value:
                        child["_parent_index"] = idx_parent + 1
                    repeats[repeat_name] = repeats[repeat_name] + value

        for repeat_name, repeat_data in repeats.items():
            repeats[repeat_name] = pd.DataFrame(repeat_data)

            # If columns have a prefix composed of all their groups,
            # remove them
            dict_rename = {}
            for c in repeats[repeat_name].columns:
                dict_rename[c] = c.split("/")[-1]
            repeats[repeat_name].rename(columns=dict_rename, inplace=True)

            self.has_repeats = True
            self.repeats = repeats

    def _remove_unused_columns(self) -> None:
        """Remove the columns in the list `columns` if they are in the
        main `self.data` (before extracting the repeats)"""

        columns = [
            "_version_",
            "formhub/uuid",
            "meta/instanceID",
            "_xform_id_string",
            "_attachments",
            "meta/deprecatedID",
            "_geolocation",
        ]

        # We only try to delete the columns that are in the DataFrame
        to_delete = [c for c in columns if c in self.data.columns]

        if len(to_delete) > 0:
            self.data.drop(to_delete, axis=1, inplace=True)

    def _rename_columns_labels_duplicates(self, structure: list) -> None:
        """Identify the duplicates among the labels of all columns in ``structure`.
        In case of duplicates, rename the label by appending (x) at the end of the label.
        'x' being the number of time the duplicate has been encountered
        while going through all the columns."""
        all_labels = [q.label for q in structure]
        duplicate_labels = [l for l in all_labels if all_labels.count(l) > 1]
        duplicates_count = {}
        for d in duplicate_labels:
            duplicates_count[d] = 0

        for q in structure:
            if q.label in duplicates_count:
                duplicates_count[q.label] += 1
                q.label = f"{q.label} ({duplicates_count[q.label]})"

    def _split_gps_coords(self) -> None:
        """Split the columns of type 'geopoint' into 4 new columns
        'latitude', 'longitude', 'altitude', 'gps_precision'
        """

        base_geo_columns = ["latitude", "longitude", "altitude", "precision"]

        for g in self.geo:
            index_geo = self.__root_structure.index(g)
            new_geo_names = [f"_{g.name}_{c}" for c in base_geo_columns]
            new_geo_labels = [f"_{g.label}_{c}" for c in base_geo_columns]

            for idx, c in enumerate(new_geo_names):
                q = Question(c, "geo", new_geo_labels[idx])
                self.__root_structure.insert(index_geo + idx + 1, q)

            self.data[new_geo_names] = self.data[g.name].str.split(" ", expand=True)

        # XXX This has not been tested
        if self.has_repeats:
            for repeat_name, repeat in self.__repeats_structure.items():
                if repeat["has_geo"]:
                    for g in repeat["geo"]:
                        index_geo = repeat["columns"].index(g)
                        new_geo_names = [f"_{g.name}_{c}" for c in base_geo_columns]
                        new_geo_labels = [f"_{g.label}_{c}" for c in base_geo_columns]

                        for idx, c in enumerate(new_geo_names):
                            q = Question(c, "geo", new_geo_labels[idx])
                            repeat["columns"].append(index_geo + idx + 1, q)

                        self.data[new_geo_names] = self.repeats[repeat_name][
                            g.name
                        ].str.split(" ", expand=True)

    def download_form(self, format: str) -> None:
        """Given the uid of a form and a format ('xls' or 'xml')
        download the form in that format in the current directory"""

        if format not in ["xls", "xml"]:
            raise ValueError(
                f"The file format '{format}' is not supported. Recognized formats are 'xls' and 'xml'"
            )

        URL = f"{self.base_url}/{self.uid}.{format}"
        filename = URL.split("/")[-1]

        r = requests.get(URL, headers=self.headers)

        with open(filename, "wb") as f:
            f.write(r.content)
