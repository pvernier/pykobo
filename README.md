# pykobo

Pykobo is a Python module to retrieve forms built on a [KoboToolBox](https://www.kobotoolbox.org/) like server and their data created with the mobile data collection application [KoboCollect](https://play.google.com/store/apps/details?id=org.koboc.collect.android).

To fetch the data, pykobo uses the Kobo API.

The form's data is returned as a pandas DataFrame making it easy to integrate in your workflow for further cleaning, filtering, aggregatation, etc...  

## Note
Pykobo only fetches data. It doesn't update, delete data on the Kobo server.

## Functionalities
For an identified user, pykobo can:
* Retrieve the list of forms 
* Download a form in XLS or XML format
* Fetch the data of a form (with names of labels) as a pandas DataFrame

...and more, see the examples below for more details


## Requirements
* requests
* pandas
* numpy

## Examples

### How to start

To get your API token, see [here](https://support.kobotoolbox.org/api.html#getting-your-api-token).

```python
import pykobo

URL_KOBO_API = "https://example.com/api/v2"
MYTOKEN = "123456789"

# Initialize the Manager object
km = pykobo.Manager(url_api=URL_KOBO_API, token=MYTOKEN)
```

### Retrieve the list of forms you have access to

```python
myforms = km.get_forms()

```
This returns a Python dictionary where keys are the UID of the forms and values the names of the forms

```python
print(myforms)

{   'cXb2wBK6f7Fp4JpRfCCEfT': 'Name of form 1',
    'cQLZapErE5UqqG7Avntkhd': 'Name of form 2',
    'whT5oWi2CTnmdmKU86Sark': 'Name of form 3',
    'vicdpNoH9KZTDP7YBQj6vW': 'Name of form 4'}
```
### Download a form in XLS or XML format

```python
uid = 'cXb2wBK6f7Fp4JpRfCCEfT'
km.download_form(uid, 'xls')
```

This downloads the XLSForm `cXb2wBK6f7Fp4JpRfCCEfT.xls` in the current working directory

### Fetch the data of a form

```python
data = km.fetch_form_data(uid)
# `data` is a pandas DataFrame

print(data.columns)

Index(['zone_sante', 'aire_sante', 'village', 'date', 'code', 'gps'],
      dtype='object')
```

The names of the columns and the values correspond to the content of the column `name` in the XLSForm.

It's also possible to retrieve the data and their labels.

### Fetch the data of a form with their labels

```python
# We set the optional argument `with_labels` to True
data = km.fetch_form_data(uid, with_labels=True)

print(data.columns)

Index(['Zone de Santé', 'Aire de Santé', 'Village ou Quartier', 'Date', 'Code', 'Coordonnées GPS'],
      dtype='object')
```

### Remove the metadata columns

If you don't need all the columns containing metadata, you can delete them.
Metadata columns include:
* All columns which name starts with '_'
* 'formhub/uuid'
* 'meta/instanceID'
* 'start'
* 'end'
* 'today'
* 'username'
* 'deviceid'

```python
km.remove_metadata(data)
```

### Format the GPS coordinates into 4 columns

The Kobo API stores the GPS coordinates in a single column which contains the longitude, latitude, altitude and the precision of the coordinates.

We can split this content into 4 separate columns called 'latitude', 'longitude', 'altitude', 'gps_precision'
```python
data = km.split_gps_coords(data, 'Coordonnées GPS')

print(data.columns)

Index(['Zone de Santé', 'Aire de Santé', 'Village ou Quartier', 'Date', 'Code', 'latitude', 'longitude', 'altitude', 'gps_precision'],
      dtype='object')
```
The coordinates have been splitted into 4 separate columns and the column 'Coordonnées GPS' has been deleted.

## Also
Pykobo has a bunch of utility methods that make easy to clean you data (not documented yet).