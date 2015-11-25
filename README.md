CKAN Private Datasets [![Build Status](https://build.conwet.fi.upm.es/jenkins/buildStatus/icon?job=ckan_privatedatasets-develop)](https://build.conwet.fi.upm.es/jenkins/job/ckan_privatedatasets-develop/)
=====================

This CKAN extension allows a user to create private datasets that only certain users will be able to see. When a dataset is being created, it's possible to specify the list of users that can see this dataset. In addition, the extension provides an HTTP API that allows to add users programmatically.

This project is part of [FIWARE](http://www.fiware.org).

Installation
------------
Install this extension in your CKAN instance is as easy as install any other CKAN extension.

* Activate your virtual environment
```
. /usr/lib/ckan/default/bin/activate
```
* Install the extension by running
```
pip install ckanext-privatedatasets
```
> **Note**: If you prefer, you can also download the source code and install the extension manually. To do so, execute the following commands:
> ```
> $ git clone https://github.com/conwetlab/ckanext-privatedatasets.git
> $ cd ckanext-privatedatasets
> $ python setup.py install
> ```

* Modify your configuration file (generally in `/etc/ckan/default/production.ini`) and add `privatedatasets` in the `ckan.plugins` property.
```
ckan.plugins = privatedatasets <OTHER_PLUGINS>
```
* In the same config file, specify the location of your parser by adding the `ckan.privatedatasets.parser` setting. For example, to set the [FiWareNotificationParser](https://github.com/conwetlab/ckanext-privatedatasets/blob/master/ckanext/privatedatasets/parsers/fiware.py) as notification parser, add the following line: `ckan.privatedatasets.parser = ckanext.privatedatasets.parsers.fiware:FiWareNotificationParser`.
* If you want you can also add some preferences to set if the Acquire URL should be shown when the user is to create and/or editing a dataset:
  * To show the Acquire URL when the user is **creating** a dataset, you should set the following preference: `ckan.privatedatasets.show_acquire_url_on_create = True`. By default, the value of this preference is set to `False`.
  * To show the Acquire URL when the user is **editing** a dataset, you should set the following preference: `ckan.privatedatasets.show_acquire_url_on_edit = True`. By default, the value of this preference is set to `False`.
* In some cases you will want to secure the notification callback in order to filter the entities (user, machines...) that can send them. To do so, you can follow the instructions in the section [Securing the Notification Callback](#securing-the-notification-callback).
* Restart your apache2 reserver
```
sudo service apache2 restart
```
* That's All!

Creating a notification parser
------------------------------
Since each service can send notifications in a different way, the extension allows developers to create their own notifications parser. As default, we provide you a basic parser based on the notifications sent by the [FiWare Store](https://github.com/conwetlab/wstore/).

If you want to create your own parser, you have to:

1. Create a class with a method called `parse_notification`. This method will receive one argument that will include the notification body.
2. Parse the notification as you like. You can raise a CKAN's default exception (`ValidationError`, `ObjectNotFound`, `NotAuthorized`, `ValidationError`, `SearchError`, `SearchQueryError` or `SearchIndexError`) if you find an error parsing the notification.
3. Return a dictionary with the structure attached below. The `users_datasets` is the lists of datasets available for each user (each element of this list is a dictionary with two fields: `user` and `datasets`).

```
{'users_datasets': [{'user': 'user_name', 'datasets': ['ds1', 'ds2', ...]},
                    {'user': 'user_name2', 'datasets': ['ds1', 'ds4', ...] }]}
```

Finally, you have to modify your config file and specify in the `ckan.privatedatasets.parser` the location of your own parser.

At this point, you will be able to add users via API by accessing the following URL:

```
http://<CKAN_SERVER>:<CKAN_PORT>/api/action/dataset_acquired
```

Securing the Notification Callback
-----------------------------------
In some cases, you are required to filter the entities (users, machines...) that can send notifications to the notification callback. To do so, you must relay on Client Side Verification over HTTPs, so the first step here is to deploy your CKAN instance over HTTPs. If you haven't already done it, you can use the following tutorial: [Starting CKAN over HTTPs](https://github.com/conwetlab/ckanext-oauth2/wiki/Starting-CKAN-over-HTTPs).

Once that your CKAN instance is running over HTTPs, you have to configure the Client Side Verification. To achieve this, the first thing that you must do is creating an OpenSSL config file. You can use the following one or modify it to your liking:

```
[ req ]
default_md = sha1
distinguished_name = req_distinguished_name

[ req_distinguished_name ]
countryName = Country
countryName_default = SP
countryName_min = 2
countryName_max = 2
localityName = Locality
localityName_default = Madrid
organizationName = Organization
organizationName_default = FIWARE
commonName = Common Name
commonName_max = 64

[ certauth ]
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer:always
basicConstraints = CA:true
crlDistributionPoints = @crl

[ server ]
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
nsCertType = server
crlDistributionPoints = @crl

[ client ]
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment, dataEncipherment
extendedKeyUsage = clientAuth
nsCertType = client
crlDistributionPoints = @crl

[ crl ]
URI=http://testca.local/ca.crl
```

Then, you should create your CA using the previous config file. To do so, you can execute the following line (replace `<PATH_TO_SSL_CONFIG_FILE>` by the real path of your OpenSSL config file):

```
$ openssl req -config <PATH_TO_SSL_CONFIG_FILE> -newkey rsa:2048 -nodes -keyform PEM -keyout ca.key -x509 -days 3650 -extensions certauth -outform PEM -out ca.cer
```

Afterwards, you will need to filter the notification callback to be callable only by those entities that use a valid certificate (the one signed by the CA created previously). To achieve this, edit the file `/etc/apache2/sites-available/ckan_default` and add the following lines immediately after the SSL configuration (replace `<PATH_TO_SSL_CONFIG_FILE>` by the real path of your OpenSSL config file):

```
    <Location /api/action/dataset_acquired>
        SSLCACertificateFile    <PATH_TO_THE_CA_FILE_CREATED_PREVIOUSLY>
        SSLVerifyClient         require
    </Location>
```

Finally, you must restart your Apache server. To do so, execute the following command:

```
$ sudo service apache2 restart
```

From now own, you should consider that a valid certificate will be required to call the notification callback. To generate a new certificate you can execute the following lines (replace `<PATH_TO_SSL_CONFIG_FILE>` by the real path of your OpenSSL config file):

```
$ openssl genrsa -out client.key 2048
$ openssl req -config <PATH_TO_SSL_CONFIG_FILE> -new -key client.key -out client.req
$ openssl x509 -req -in client.req -CA ca.cer -CAkey ca.key -set_serial 101 -extfile <PATH_TO_SSL_CONFIG_FILE> -extensions client -days 365 -outform PEM -out client.cer
$ openssl pkcs12 -export -inkey client.key -in client.cer -out client.p12
```

That's all! You notification callback is completely secure now! Enjoy it :)

Tests
-----
This sofware contains a set of test to detect errors and failures. You can run this tests by running the following command (this command will generate coverage reports):
```
python setup.py nosetests
```
**Note:** The `test.ini` file contains a link to the CKAN `test-core.ini` file. You will need to change that link to the real path of the file in your system (generally `/usr/lib/ckan/default/src/ckan/test-core.ini`).
