![PyPI](https://img.shields.io/pypi/v/pykobo)

# pykobo

Pykobo is a Python module that fetches data from [Kobo](https://www.kobotoolbox.org/) forms via the [Kobo API](https://support.kobotoolbox.org/api.html).

The data is returned as a [pandas](https://pandas.pydata.org/) DataFrame making it easy to integrate in your workflow for further cleaning, filtering, aggregatation, etc...  

## Functionalities
Pykobo can:
* Get the list of forms a user has access to 
* Fetch the data of a form (with names or labels for the columns and choices) as a pandas DataFrame
* Download a form in XLS or XML format

## Install

```bash
$ pip install pykobo
```

## Examples

### How to start

NB: The example below uses [kf.kobotoolbox.org](https://kf.kobotoolbox.org/) but pykobo also works with [kobo.humanitarianresponse.info](https://kobo.humanitarianresponse.info/) and any other Kobo server.

To get your API token, see [here](https://support.kobotoolbox.org/api.html#getting-your-api-token).

```python
import pykobo


URL_KOBO = "https://kf.kobotoolbox.org/"
API_VERSION = 2
MYTOKEN = "2bc8e0201d23dac4ec1c334107698147b81513a2"

# Initialize the Manager object
km = pykobo.Manager(url=URL_KOBO, api_version=API_VERSION, token=MYTOKEN)
```

### Get the list of forms you have access to

```python
my_forms = km.get_forms()

```
This returns a Python list of KoboForm objetcs

```python
print(my_forms)

[   KoboForm('tpz2buHAdXxcN0JVrZaSdk'),
    KoboForm('vyARFbyE8Gv3RUvXNfdTRj'),
    KoboForm('wogyYJzUu2ZFVnzqGg8K7q'),
    KoboForm('bQLZapErE3UqqG9Avntkhd')]

# Each form contains metadata
for f in my_forms:
      print(f.metadata)

{   'date_created': '2022-07-14T20:44:11.929901Z',
    'date_modified': '2022-10-02T07:49:19.714891Z',
    'geo': True,
    'has_deployment': True,
    'name': 'Household survey',
    'owner': 'pvernier',
    'version_id': 'aqUMoSqANiEgH3j4Nn3Cr7'}
{   'date_created': '2022-07-14T12:41:14.665314Z',
    'date_modified': '2022-09-28T11:55:15.408542Z',
    'geo': True,
    'has_deployment': True,
    'name': 'Health facilities monitoring',
    'owner': 'pvernier',
    'version_id': 'abLugnJGURSyyZ8RZxC0wQ'}
{   'date_created': '2022-07-14T13:40:32.033446Z',
    'date_modified': '2022-09-28T09:19:20.691620Z',
    'geo': False,
    'has_deployment': True,
    'name': 'Post emergency evaluation',
    'owner': 'pvernier',
    'version_id': 'aQQUmPns7xLUL4Ro0amqwS'}
{   'date_created': '2022-09-14T16:54:06.990672Z',
    'date_modified': '2022-09-20T13:27:52.410261Z',
    'geo': True,
    'has_deployment': True,
    'name': 'Identification of burnt areas',
    'owner': 'pvernier',
    'version_id': 'xes8JkQRpbDcbct9sqmCYZ'}  
```

### Fetch a single form with its uid.

```python
uid = 'tpz2buHAdXxcN0JVrZaSdk'

my_form = km.get_form(uid)

print(my_form.metadata)

{   'date_created': '2022-07-14T20:44:11.929901Z',
    'date_modified': '2022-10-02T07:49:19.714891Z',
    'geo': True,
    'has_deployment': True,
    'name': 'Household survey',
    'owner': 'pvernier',
    'version_id': 'aqUMoSqANiEgH3j4Nn3Cr7'}

```


### Fetch the data of a form

```python
my_form.fetch_data()

# The data is accessible via the `data` attribute as a pandas DataFrame

print(my_form.data)
                             start                            end       today         username                  deviceid            phonenumber  ...     _submission_time _tags _notes _validation_status    _submitted_by _index
0    2022-09-01T15:47:55.797+02:00  2022-09-01T15:51:48.302+02:00  2022-09-01  surveyer_1  collect:4vUec4gLVJx3GP1D                    NaN  ...  2022-09-01T13:52:04    []     []                 {}  surveyer_1      1
1    2022-09-01T15:58:08.251+02:00  2022-09-01T16:08:14.548+02:00  2022-09-01  surveyer_1  collect:Xk9Z5f1VTW5nig68                    NaN  ...  2022-09-01T14:08:46    []     []                 {}  surveyer_1      2
2    2022-09-01T14:05:08.484+02:00  2022-09-01T16:17:59.305+02:00  2022-09-01  surveyer_1  collect:0Y8Cozz5fzI8jczs                    NaN  ...  2022-09-01T14:18:36    []     []                 {}  surveyer_1      3
3    2022-09-01T16:20:39.699+02:00  2022-09-01T16:32:03.393+02:00  2022-09-01  surveyer_1  collect:MPi52tvGiPY6AuK3                    NaN  ...  2022-09-01T14:32:27    []     []                 {}  surveyer_1      4
...
...
[595 rows x 38 columns]

print(type(my_form.data))

<class 'pandas.core.frame.DataFrame'>

# The method `fetch_data` returns the data using the Kobo columns and choices names

print(my_form.data.columns)

Index(['start', 'end', 'today', 'username', 'deviceid', 'phonenumber', 'date',
       'health_area', 'village_name', 'team_number', 'cluster_number',
       'household_number', 'gps', '_gps_latitude', '_gps_longitude',
       '_gps_altitude', '_gps_precision', 'hhh_present',
       'age_hhh', 'consent', 'number_children',
       '__version__', '_id', '_uuid', '_status', '_submission_time',
       '_tags', '_notes', '_validation_status', '_submitted_by', '_index'],
      dtype='object')
```

### Display the data using Kobo labels for columns and/or choices


```python
my_form.display(columns_as='label', choices_as='label')

print(my_form.data.columns)

Index(['start', 'end', 'today', 'username', 'deviceid', 'phonenumber',
       'Date of the survey', 'Health zone', 'Name of the village', 'team number',
       'Cluster number', 'Household number', 'GPS Coordinates',
       '_GPS Coordinates_latitude', '_GPS Coordinates_longitude',
       '_GPS Coordinates_altitude', '_GPS Coordinates_precision',
       'Head of the household present?',
       'Age of the head of the household ',
       'Consent obtained',
       'Number of children in the household',
       '__version__', '_id', '_uuid', '_status', '_submission_time', '_tags',
       '_notes', '_validation_status', '_submitted_by', '_index'],
      dtype='object')


# You can go back and forth between names and labels as much as you want 
my_form.display(columns_as='label', choices_as='name')
my_form.display(columns_as='name', choices_as='label')
my_form.display(columns_as='name', choices_as='name')
my_form.display(columns_as='label', choices_as='label')

```
#### Note
* For questions of type `select_multiple` the different answers are separated by a '|'.

* If a form contains `n` columns with the same label, a suffix `(1)` to `(n)` will be added to each of the columns.

### Repeats

[Repeats](https://xlsform.org/en/#repeats) are supported (only one level, not repeats inside repeats).
In this case data of the repeat groups are separated from the 'main' data and accessible via the 'repeats' attribute
which returns a Python dictionary

```python

print(my_form.has_repeats)

True
# This means that the form has at least 1 repeat group

print(my_form.repeats.keys())

dict_keys(['children_questions'])
# The form has 1 repeat group called 'children_questions'


print(my_form.repeats['children_questions'])


     index_repeat Sex of the child Age of the child  ... Going to school?  _parent_index
0               1                           Male              No                    2
1               2                           Female            No                    2
2               1                           Female            No                    4
3               1                           Female            Yes                   5
4               2                           Female            No                    5
...
...
[1040 rows x 27 columns]

```
The column `_index` in the main DataFrame (my_form.data) and the column `_parent_index` in the DatFrame of the repeat
group can be used to join the 2 DataFrames.

```python

df_join = pd.merge(
    my_form.data,
    my_form.repeats['groupe_questions_enfants'],
    how="left",
    left_on='_index',
    right_on='_parent_index'
)

```
### Save the data to file

Because the data is a pandas DataFrame, we can take advantage of the [many](https://pandas.pydata.org/docs/user_guide/io.html) pandas methods to export it to a file.

```python
# CSV
df_join.to_csv('household_survey.csv', index=False)

# Excel
df_join.to_excel('household_survey.xlsx', index=False)
```

### Download a form in XLS or XML format

```python
my_form.download_form('xls')
```
This downloads the XLSForm `tpz2buHAdXxcN0JVrZaSdk.xls` in the current working directory

## Also
Pykobo has a bunch of utility methods that make easy to clean you data (not documented yet).

## Note
Pykobo only reads and fetches data from Kobo forms. It doesn't update or delete the forms and their data on the Kobo server.

## Dependencies
* requests
* pandas
* numpy

## TO DO
* Add possibility to display group name as a prefix
* Add method to download media files
* Clean and document utility functions
* Be more consistent and robust in case of errors
* Calculate stats on forms time duration