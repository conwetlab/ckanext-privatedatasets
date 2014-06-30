CKAN Private Datasets
=====================

This CKAN extension allows a user to create private datasets that only certain users will be able to see. When a dataset is being created, it's possible to specify the list of users that can see this dataset. In addition, the extension provides an HTTP API that allows to add users programatically. 

Installation
------------
Install this extension in your CKAN is instance is as easy as intall any other CKAN extension.

* Download the source from this GitHub repo.
* Activate your virtual environment (generally by running `. /usr/lib/ckan/default/bin/activate`)
* Install the extension by running `python setup.py develop`
* Modify your configuration file (generally in `/etc/ckan/default/production.ini`) and add `privatedatasets` in the `ckan.plugins` setting. 
* In the same config file, specify the location of your parser by adding the `ckan.privatedatasets.parser` setting. For example, to set the [FiWareNotificationParser](https://github.com/conwetlab/ckanext-privatedatasets/blob/master/ckanext/privatedatasets/parsers/fiware.py) as notification parser, add the following line: `ckan.privatedatasets.parser = ckanext.privatedatasets.parsers.fiware:FiWareNotificationParser`
* Restart your apache2 reserver (`sudo service apache2 restart`)
* That's All!

Creating a notification parser
------------------------------
Since each service can send notifications in a different way, the extension allows developers to create their own notifications parser. As default, we provide you a basic parser based on the notifications sent by the [FiWare Store](https://github.com/conwetlab/wstore/). 

If you want to create your own parser, you have to:

1. Create a class with a method called `parse_notification`
2. Import `request` from `ckan.common` in order to be able to read the notification: `from ckan.common import request`.
3. Parse the notification as you like. You can read the body by accesing `request.body`.
4. Return a dictionary with the following structure. The `errors` field contains the list of errors arised when the notification was parsed while the `users_datasets` is the lists of datasets available for each user (each element of this list is a dictionary with two fields: `user` and `datasets`). If the `error` field is present and it is **not** empty, the `users_datasets` field will **not** be processed.

```
{'errors': ['...', '...', '...']
 'users_datasets': [{'user': 'user_name', 'datasets': ['ds1', 'ds2', ...]},
                    {'user': 'user_name2', 'datasets': ['ds1', 'ds4', ...] }]}
```

Finally, you have to modify your config file and specify in the `ckan.privatedatasets.parser` the location of your own parser. 

Tests
-----
This sofware contains a set of test to detect errors and failures. You can run this tests by running the following command:
```
nosetests --ckan --with-pylons=test.ini ckanext/privatedatasets/tests/
```
**Note:** The `test.ini` file contains a link to the CKAN `test-core.ini` file. You will need to change that link to the real path of the file in your system (generally `/usr/lib/ckan/default/src/ckan/test-core.ini`). 

You can also generate coverage reports by running:
```
nosetests --ckan --with-xunit --with-pylons=test.ini ckanext/privatedatasets/tests/ --with-coverage --cover-package=ckanext.privatedatasets --cover-inclusive --cover-erase . --cover-xml
```

