# -*- coding: utf-8 -*-

# Copyright (c) 2014 CoNWeT Lab., Universidad Politécnica de Madrid

# This file is part of CKAN Private Dataset Extension.

# CKAN Private Dataset Extension is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# CKAN Private Dataset Extension is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with CKAN Private Dataset Extension.  If not, see <http://www.gnu.org/licenses/>.

from nose_parameterized import parameterized
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from subprocess import Popen

import ckan.lib.search.index as search_index
import ckan.model as model
import ckanext.privatedatasets.db as db
import json
import os
import unittest
import re
import requests


def get_dataset_url(dataset_name):
    return dataset_name.replace(' ', '-').lower()


class TestSelenium(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        env = os.environ.copy()
        env['DEBUG'] = 'True'
        env['OAUTHLIB_INSECURE_TRANSPORT'] = 'True'
        cls._process = Popen(['paster', 'serve', 'test.ini'], env=env)

    @classmethod
    def tearDownClass(cls):
        cls._process.terminate()

    def clearBBDD(self):
        # Clean Solr
        search_index.clear_index()

        # Clean the database
        model.repo.rebuild_db()

        # Delete previous users
        db.init_db(model)
        users = db.AllowedUser.get()
        for user in users:
            model.Session.delete(user)
        model.Session.commit()

    def setUp(self):
        self.clearBBDD()

        self.driver = webdriver.Firefox()
        self.driver.implicitly_wait(5)
        self.driver.set_window_size(1024, 768)
        self.base_url = 'http://127.0.0.1:5000/'

    def tearDown(self):
        self.clearBBDD()
        self.driver.quit()

    def assert_fields_disabled(self, fields):
        for field in fields:
            self.assertFalse(self.driver.find_element_by_id(field).is_enabled())

    def logout(self):
        self.driver.delete_all_cookies()
        self.driver.get(self.base_url)

    def register(self, username, fullname, mail, password):
        driver = self.driver
        driver.get(self.base_url)
        driver.find_element_by_link_text('Register').click()
        driver.find_element_by_id('field-username').clear()
        driver.find_element_by_id('field-username').send_keys(username)
        driver.find_element_by_id('field-fullname').clear()
        driver.find_element_by_id('field-fullname').send_keys(fullname)
        driver.find_element_by_id('field-email').clear()
        driver.find_element_by_id('field-email').send_keys(mail)
        driver.find_element_by_id('field-password').clear()
        driver.find_element_by_id('field-password').send_keys(password)
        driver.find_element_by_id('field-confirm-password').clear()
        driver.find_element_by_id('field-confirm-password').send_keys(password)
        driver.find_element_by_name('save').click()
        self.logout()

    def login(self, username, password):
        driver = self.driver
        driver.get(self.base_url)
        driver.find_element_by_link_text('Log in').click()
        driver.find_element_by_id('field-login').clear()
        driver.find_element_by_id('field-login').send_keys(username)
        driver.find_element_by_id('field-password').clear()
        driver.find_element_by_id('field-password').send_keys(password)
        driver.find_element_by_id('field-remember').click()
        driver.find_element_by_css_selector('button.btn.btn-primary').click()

    def create_organization(self, name, description, users):
        driver = self.driver
        driver.get(self.base_url)
        driver.find_element_by_link_text('Organizations').click()
        driver.find_element_by_link_text('Add Organization').click()
        driver.find_element_by_id('field-name').clear()
        driver.find_element_by_id('field-name').send_keys(name)
        driver.find_element_by_id('field-description').clear()
        driver.find_element_by_id('field-description').send_keys(description)
        driver.find_element_by_name('save').click()

        # Add users
        driver.find_element_by_link_text('Manage').click()
        driver.find_element_by_link_text('Members').click()
        for user in users:
            driver.find_element_by_link_text('Add Member').click()
            driver.find_element_by_id('username').send_keys(user)
            driver.find_element_by_name('submit').click()

    def fill_ds_general_info(self, name, description, tags, private, searchable, allowed_users, acquire_url):
        # FIRST PAGE: Dataset properties
        driver = self.driver
        driver.find_element_by_id('field-title').clear()
        driver.find_element_by_id('field-title').send_keys(name)
        driver.find_element_by_id('field-notes').clear()
        driver.find_element_by_id('field-notes').send_keys(description)
        driver.find_element_by_id('field-tags').clear()
        driver.find_element_by_id('field-tags').send_keys(','.join(tags))
        Select(driver.find_element_by_id('field-private')).select_by_visible_text('Private' if private else 'Public')
        # WARN: The organization is set by default

        # If the dataset is private, we should complete the fields
        # If the dataset is public, these fields will be disabled (we'll check it)
        if private:
            Select(driver.find_element_by_id('field-searchable')).select_by_visible_text('True' if searchable else 'False')
            driver.find_element_by_id('field-allowed_users_str').clear()
            driver.find_element_by_id('field-allowed_users_str').send_keys(','.join(allowed_users))
            driver.find_element_by_id('field-acquire_url').clear()
            if acquire_url:
                driver.find_element_by_id('field-acquire_url').send_keys(acquire_url)
        else:
            self.assert_fields_disabled(['field-searchable', 'field-allowed_users_str', 'field-acquire_url'])

        driver.find_element_by_name('save').click()

    def create_ds(self, name, description, tags, private, searchable, allowed_users, acquire_url, resource_url, resource_name, resource_description, resource_format):
        driver = self.driver
        driver.get(self.base_url)
        driver.find_element_by_link_text('Datasets').click()
        driver.find_element_by_link_text('Add Dataset').click()
        self.fill_ds_general_info(name, description, tags, private, searchable, allowed_users, acquire_url)

        # SECOND PAGE: Add Resources
        try:
            # The link button is only clicked if it's present
            driver.find_element_by_link_text('Link').click()
        except Exception:
            pass

        driver.find_element_by_id('field-image-url').clear()
        driver.find_element_by_id('field-image-url').send_keys(resource_url)
        driver.find_element_by_id('field-name').clear()
        driver.find_element_by_id('field-name').send_keys(resource_name)
        driver.find_element_by_id('field-description').clear()
        driver.find_element_by_id('field-description').send_keys(resource_description)
        driver.find_element_by_id('s2id_autogen1').clear()
        driver.find_element_by_id('s2id_autogen1').send_keys(resource_format)
        driver.find_element_by_css_selector('button.btn.btn-primary').click()

    def modify_ds(self, url, name, description, tags, private, searchable, allowed_users, acquire_url):
        driver = self.driver
        driver.get('%sdataset/edit/%s' % (self.base_url, url))
        self.fill_ds_general_info(name, description, tags, private, searchable, allowed_users, acquire_url)

    def check_ds_values(self, url, private, searchable, allowed_users, acquire_url):
        driver = self.driver
        driver.get(self.base_url + 'dataset/edit/' + url)
        self.assertEqual('Private' if private else 'Public', Select(driver.find_element_by_id('field-private')).first_selected_option.text)

        if private:
            acquire_url_final = '' if acquire_url is None else acquire_url
            self.assertEqual(acquire_url_final, driver.find_element_by_id('field-acquire_url').get_attribute('value'))
            self.assertEqual('True' if searchable else 'False', Select(driver.find_element_by_id('field-searchable')).first_selected_option.text)

            # Test that the allowed users lists is as expected (order is not important)
            current_users = driver.find_element_by_css_selector('#s2id_field-allowed_users_str > ul.select2-choices').text.split('\n')
            current_users = current_users[0:-1]
            # ''.split('\n') ==> ['']
            # if len(current_users) == 1 and current_users[0] == '':
            #     current_users = []
            # Check the array
            self.assertEquals(len(allowed_users), len(current_users))
            for user in current_users:
                self.assertIn(user, allowed_users)
        else:
            self.assert_fields_disabled(['field-searchable', 'field-allowed_users_str', 'field-acquire_url'])

    def check_user_access(self, dataset, dataset_url, owner, acquired, in_org, private, searchable, acquire_url=None):
        driver = self.driver
        driver.find_element_by_link_text('Datasets').click()

        if searchable:
            xpath = '//div[@id=\'content\']/div[3]/div/section/div/ul/li/div/h3/span'

            # Check the label
            if not acquired and private and not in_org:
                self.assertEqual('PRIVATE', driver.find_element_by_xpath(xpath).text)
            elif acquired and not owner and private:
                self.assertEqual('ACQUIRED', driver.find_element_by_xpath(xpath).text)
            elif owner:
                self.assertEqual('OWNER', driver.find_element_by_xpath(xpath).text)

            # When a user cannot access a dataset, the link is no longer provided
        else:
            # If the dataset is not searchable, a link to it could not be found in the dataset search page
            self.assertEquals(None, re.search(dataset_url, driver.page_source))

        # Access the dataset
        driver.get(self.base_url + 'dataset/' + dataset_url)

        if not acquired and private and not in_org:
            xpath = '//div[@id=\'content\']/div/div'
            buy_msg = 'This private dataset can be acquired. To do so, please click here'
            if acquire_url is not None:
                self.assertTrue(driver.find_element_by_xpath(xpath).text.startswith(buy_msg))
                self.assertEquals(acquire_url, driver.find_element_by_link_text('here').get_attribute('href'))
                xpath += '[2]'  # The unauthorized message is in a different Path
            else:
                src = driver.page_source
                self.assertEquals(None, re.search(buy_msg, src))

            self.assertTrue('/user/login' in driver.current_url)
            self.assertTrue(driver.find_element_by_xpath(xpath).text.startswith('Unauthorized to read package %s' % dataset_url))

        else:
            self.assertEquals(self.base_url + 'dataset/%s' % dataset_url, driver.current_url)

    def check_acquired(self, dataset, dataset_url, acquired, private):
        driver = self.driver
        driver.get(self.base_url + 'dashboard')
        driver.find_element_by_link_text('Acquired Datasets').click()

        if acquired and private:
            # This message could not be shown when the user has acquired at least one dataset
            self.assertEquals(None, re.search('You haven\'t acquired any datasets.', driver.page_source))
            # Access the dataset
            driver.find_element_by_link_text(dataset).click()
            self.assertEquals(self.base_url + 'dataset/%s' % dataset_url, driver.current_url)
        else:
            # If the user has not acquired the dataset, a link to this dataset could not be in the acquired dataset list
            self.assertEquals(None, re.search(dataset_url, driver.page_source))
            # When a user has not acquired any dataset, a message will be shown to inform the user
            self.assertNotEquals(None, re.search('You haven\'t acquired any datasets.', driver.page_source))

    def default_register(self, user):
        self.register(user, user, '%s@conwet.com' % user, user)

    @parameterized.expand([
        # (['user1', 'user2', 'user3'],          True,  True,  ['user2'],          'http://store.conwet.com/'),
        # (['user1', 'user2', 'user3'],          True,  True,  ['user3']),
        # (['user1', 'user2', 'user3'],          False, True,  ['user3']),
        # (['user1', 'user2', 'user3'],          True,  False, ['user2']),
        (['user1', 'user2', 'user3'],          True,  True,  [],                 'http://store.conwet.com/'),
        (['user1', 'user2', 'user3'],          True,  True,  []),
        (['user1', 'user2', 'user3'],          False, True,  []),
        (['user1', 'user2', 'user3'],          True,  False, []),
        (['user1', 'user2', 'user3', 'user4'], True,  True,  ['user2', 'user4'], 'http://store.conwet.com/'),
        (['user1', 'user2', 'user3', 'user4'], True,  True,  ['user3', 'user4']),
        (['user1', 'user2', 'user3', 'user4'], False, True,  ['user3', 'user4']),
        (['user1', 'user2', 'user3', 'user4'], True,  False, ['user2', 'user4']),
    ])
    def test_basic(self, users, private, searchable, allowed_users, acquire_url=None):
        # Create users
        for user in users:
            self.default_register(user)

        # The first user creates a dataset
        self.login(users[0], users[0])
        pkg_name = 'Dataset 1'
        url = get_dataset_url(pkg_name)
        self.create_ds(pkg_name, 'Example description', ['tag1', 'tag2', 'tag3'], private, searchable,
                       allowed_users, acquire_url, 'http://upm.es', 'UPM Main', 'Example Description', 'CSV')
        self.check_ds_values(url, private, searchable, allowed_users, acquire_url)
        self.check_user_access(pkg_name, url, True, True, False, private, searchable, acquire_url)
        self.check_acquired(pkg_name, url, False, private)

        # Rest of users
        rest_users = users[1:]
        for user in rest_users:
            self.logout()
            self.login(user, user)
            acquired = user in allowed_users
            self.check_user_access(pkg_name, url, False, acquired, False, private, searchable, acquire_url)

            # The user is logged out when they try to access a private dataset and they are not included
            # in the list of allowed users.
            if not acquired and private:
                self.login(user, user)

            self.check_acquired(pkg_name, url, acquired, private)

    @parameterized.expand([
        # (['a']  ,          'http://upm.es',      'Allowed users: Name must be at least 2 characters long'),
        # (['a a'],          'http://upm.es',      'Allowed users: Url must be purely lowercase alphanumeric (ascii) characters and these symbols: -_'),
        (['upm', 'a'],     'http://upm.es',      'Allowed users: Must be at least 2 characters long'),
        (['upm', 'a a a'], 'http://upm.es',      'Allowed users: Must be purely lowercase alphanumeric (ascii) characters and these symbols: -_'),
        (['upm', 'a?-vz'], 'http://upm.es',      'Allowed users: Must be purely lowercase alphanumeric (ascii) characters and these symbols: -_'),
        (['thisisaveryveryveryveryveryveryveryveryveryveryveryveryveryveryveryveryveryveryveryveryveryveryveryverylongname'],
                           'http://upm.es',      'Allowed users: Name must be a maximum of 100 characters long'),
        (['conwet'],       'ftp://google.es',    'Acquire URL: The URL "ftp://google.es" is not valid.'),
        # (['conwet'],       'http://google*.com', 'Acquire URL: The URL "http://google*.com" is not valid.'),
        # (['conwet'],       'http://google+.com', 'Acquire URL: The URL "http://google+.com" is not valid.'),
        # (['conwet'],       'http://google/.com', 'Acquire URL: The URL "http://google/.com" is not valid.'),
        (['conwet'],       'google',             'Acquire URL: The URL "google" is not valid.'),
        (['conwet'],       'http://google',      'Acquire URL: The URL "http://google" is not valid.'),
        # (['conwet'],       'http://google:es',   'Acquire URL: The URL "http://google:es" is not valid.'),
        (['conwet'],       'www.google.es',      'Acquire URL: The URL "www.google.es" is not valid.')

    ])
    def test_invalid_fields(self, allowed_users, acquire_url, expected_msg):

        # Create a default user
        user = 'user1'
        self.default_register(user)

        # Create the dataset
        self.login(user, user)
        pkg_name = 'Dataset 2'

        # Go the page to create the dataset
        driver = self.driver
        driver.get(self.base_url)
        driver.find_element_by_link_text('Datasets').click()
        driver.find_element_by_link_text('Add Dataset').click()

        # Fill the requested information
        self.fill_ds_general_info(pkg_name, 'Example description', ['tag1'], True, True, allowed_users, acquire_url)

        # Check the error message
        msg_error = self.driver.find_element_by_xpath('//div[@id=\'content\']/div[3]/div/section/div/form/div/ul/li').text
        self.assertEquals(expected_msg, msg_error)

    @parameterized.expand([
        ('Acquire Dataset',  'dataset'),
        ('Acquire one now?', 'dataset')
    ])
    def test_dashboard_basic_links(self, link, expected_url):
        # Create a default user
        user = 'user1'
        self.default_register(user)
        self.login(user, user)

        # Enter the acquired dataset tab
        driver = self.driver
        driver.get(self.base_url + 'dashboard/acquired')
        driver.find_element_by_link_text(link).click()
        self.assertEquals(self.base_url + 'dataset', self.base_url + expected_url)

    @parameterized.expand([

        # Allowed users contains just one user
        # ([{'private': True,  'searchable': True,  'allowed_users': ['user1']}],          ['user2']),
        # ([{'private': False, 'searchable': True,  'allowed_users': ['user1']}],          ['user2']),
        # ([{'private': True,  'searchable': False, 'allowed_users': ['user1']}],          ['user2']),
        # ([{'private': False, 'searchable': False, 'allowed_users': ['user1']}],          ['user2']),

        # Allowed users contains more than one user
        # ([{'private': True,  'searchable': True,  'allowed_users': ['user1', 'user2']}], ['user3']),
        # ([{'private': False, 'searchable': True,  'allowed_users': ['user1', 'user2']}], ['user3']),
        # ([{'private': True,  'searchable': False, 'allowed_users': ['user1', 'user2']}], ['user3']),
        # ([{'private': False, 'searchable': False, 'allowed_users': ['user1', 'user2']}], ['user3']),

        # User added is already in the list
        ([{'private': True,  'searchable': True,  'allowed_users': ['user1', 'user2']}], ['user2']),
        ([{'private': True,  'searchable': False, 'allowed_users': ['user1', 'user2']}], ['user2']),

        # Some users
        ([{'private': True,  'searchable': True,  'allowed_users': ['user1', 'user2']}], ['user3', 'user4']),
        ([{'private': False, 'searchable': True,  'allowed_users': ['user1', 'user2']}], ['user3', 'user4']),
        ([{'private': True,  'searchable': False, 'allowed_users': ['user1', 'user2']}], ['user3', 'user4']),
        ([{'private': False, 'searchable': False, 'allowed_users': ['user1', 'user2']}], ['user3', 'user4']),
        # Complex test
        ([{'private': True,  'searchable': False, 'allowed_users': ['user1', 'user2']},
          {'private': True,  'searchable': True,  'allowed_users': ['user5', 'user6']},
          {'private': True,  'searchable': True,  'allowed_users': ['user7', 'user8']},
          {'private': False, 'searchable': True,  'allowed_users': ['user9', 'user1']}], ['user3', 'user4'])

    ])
    def test_add_users_via_api_action(self, datasets, users_via_api):
        # Create a default user
        user = 'user1'
        self.default_register(user)
        self.login(user, user)

        acquire_url = 'http://upm.es'
        dataset_default_name = 'Dataset %d'

        # Create the dataset
        for i, dataset in enumerate(datasets):
            pkg_name = dataset_default_name % i
            self.create_ds(pkg_name, 'Example description', ['tag1'], dataset['private'], dataset['searchable'],
                           dataset['allowed_users'], acquire_url, 'http://upm.es', 'UPM Main', 'Example Description', 'CSV')

        # Make the requests
        for user in users_via_api:

            resources = []
            for i, dataset in enumerate(datasets):
                resources.append({'url': self.base_url + 'dataset/' + get_dataset_url(dataset_default_name % i)})

            content = {'customer_name': user, 'resources': resources}
            req = requests.post(self.base_url + 'api/action/package_acquired', data=json.dumps(content),
                                headers={'content-type': 'application/json'})

            result = json.loads(req.text)['result']
            for i, dataset in enumerate(datasets):
                if not dataset['private']:
                    url_path = get_dataset_url(dataset_default_name % i)
                    self.assertIn('Unable to upload the dataset %s: It\'s a public dataset' % url_path, result['warns'])

        # Check the dataset
        for i, dataset in enumerate(datasets):

            if dataset['private']:
                final_users = set(dataset['allowed_users'])
                final_users.update(users_via_api)
            else:
                final_users = []

            url_path = get_dataset_url(dataset_default_name % i)
            self.check_ds_values(url_path, dataset['private'], dataset['searchable'], final_users, acquire_url)

    @parameterized.expand([
        # (['user1', 'user2', 'user3'], [{'name': 'CoNWeT', 'users': ['user2']}], True,  True,  [],        'http://store.conwet.com/'),
        # (['user1', 'user2', 'user3'], [{'name': 'CoNWeT', 'users': ['user2']}], True,  True,  []),
        # (['user1', 'user2', 'user3'], [{'name': 'CoNWeT', 'users': ['user2']}], False, True,  []),
        # (['user1', 'user2', 'user3'], [{'name': 'CoNWeT', 'users': ['user2']}], True,  False, []),
        # (['user1', 'user2', 'user3'], [{'name': 'CoNWeT', 'users': ['user2']}], True,  True,  ['user3'], 'http://store.conwet.com/'),
        # (['user1', 'user2', 'user3'], [{'name': 'CoNWeT', 'users': ['user2']}], True,  True,  ['user3']),
        # (['user1', 'user2', 'user3'], [{'name': 'CoNWeT', 'users': ['user2']}], False, True,  ['user3']),
        # (['user1', 'user2', 'user3'], [{'name': 'CoNWeT', 'users': ['user2']}], True,  False, ['user3']),

        # More complex
        # (['user1', 'user2', 'user3', 'user4', 'user5', 'user6'], [{'name': 'CoNWeT', 'users': ['user2', 'user3']}], True,  True,  ['user4', 'user5'], 'http://store.conwet.com/'),
        # (['user1', 'user2', 'user3', 'user4', 'user5', 'user6'], [{'name': 'CoNWeT', 'users': ['user2', 'user3']}], True,  True,  ['user4', 'user5']),
        # (['user1', 'user2', 'user3', 'user4', 'user5', 'user6'], [{'name': 'CoNWeT', 'users': ['user2', 'user3']}], False, True,  ['user4', 'user5']),
        # (['user1', 'user2', 'user3', 'user4', 'user5', 'user6'], [{'name': 'CoNWeT', 'users': ['user2', 'user3']}], True,  False, ['user4', 'user5']),

        # Even if user6 is in another organization, he/she won't be able to access the dataset
        (['user1', 'user2', 'user3', 'user4', 'user5', 'user6'], [{'name': 'CoNWeT', 'users': ['user2', 'user3']}, 
                                                                  {'name': 'UPM',    'users': ['user6']}],            True,  True,  ['user4', 'user5'], 'http://store.conwet.com/'),
        (['user1', 'user2', 'user3', 'user4', 'user5', 'user6'], [{'name': 'CoNWeT', 'users': ['user2', 'user3']}, 
                                                                  {'name': 'UPM',    'users': ['user6']}],            True,  True,  ['user4', 'user5']),
        (['user1', 'user2', 'user3', 'user4', 'user5', 'user6'], [{'name': 'CoNWeT', 'users': ['user2', 'user3']}, 
                                                                  {'name': 'UPM',    'users': ['user6']}],            True,  False, ['user4', 'user5']),
        (['user1', 'user2', 'user3', 'user4', 'user5', 'user6'], [{'name': 'CoNWeT', 'users': ['user2', 'user3']}, 
                                                                  {'name': 'UPM',    'users': ['user6']}],            False, True,  ['user4', 'user5']),
    ])
    def test_organization(self, users, orgs, private, searchable, adquiring_users, acquire_url=None):
        # Create users
        for user in users:
            self.default_register(user)

        self.login(users[0], users[0])

        # Create the organizations
        for org in orgs:
            self.create_organization(org['name'], 'Example Description', org['users'])

        # Create the dataset
        pkg_name = 'Dataset 1'
        url = get_dataset_url(pkg_name)
        self.create_ds(pkg_name, 'Example description', ['tag1', 'tag2', 'tag3'], private, searchable,
                       adquiring_users, acquire_url, 'http://upm.es', 'UPM Main', 'Example Description', 'CSV')
        self.check_ds_values(url, private, searchable, adquiring_users, acquire_url)
        self.check_user_access(pkg_name, url, True, True, True, private, searchable, acquire_url)
        self.check_acquired(pkg_name, url, False, private)

        # Rest of users
        rest_users = users[1:]
        for user in rest_users:
            self.logout()
            self.login(user, user)
            acquired = user in adquiring_users
            in_org = user in orgs[0]['users']
            self.check_user_access(pkg_name, url, False, acquired, in_org, private, searchable, acquire_url)

            # The user is logged out when they try to access a private dataset and they are not included
            # in the list of allowed users.
            if not acquired and private and not in_org:
                self.login(user, user)

            self.check_acquired(pkg_name, url, acquired, private)

    def test_bug_16(self):
        """
        Private datasets cannot be turned to public datasets when the Acquisition URL is set
        """
        user = 'user1'
        self.default_register(user)

        # The user creates a dataset
        self.login(user, user)
        pkg_name = 'Dataset 1'
        description = 'Example Description'
        tags = ['tag1', 'tag2', 'tag3']
        url = get_dataset_url(pkg_name)
        self.create_ds(pkg_name, 'Example description', ['tag1', 'tag2', 'tag3'], True, True,
                       [], 'http://example.com', 'http://upm.es', 'UPM Main', 'Example Description', 'CSV')

        self.modify_ds(url, pkg_name, description, tags, False, None, None, None)
        expected_url = 'dataset/%s' % url
        current_url = self.driver.current_url
        self.assertIn(expected_url, current_url)    # Maybe the current URL include some parameters
