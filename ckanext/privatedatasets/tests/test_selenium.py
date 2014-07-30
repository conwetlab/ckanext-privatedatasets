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
import time


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
        self.verificationErrors = []
        self.accept_next_alert = True

    def tearDown(self):
        self.clearBBDD()
        self.driver.quit()
        self.assertEqual([], self.verificationErrors)

    def assert_fields_disabled(self, fields):
        for field in fields:
            self.assertFalse(self.driver.find_element_by_id(field).is_enabled())

    def logout(self):
        self.driver.find_element_by_css_selector('i.icon-signout').click()

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

    def create_ds_first_page(self, name, description, tags, private, searchable, allowed_users, adquire_url):
        # FIRST PAGE: Dataset properties
        driver = self.driver
        driver.get(self.base_url)
        driver.find_element_by_link_text('Datasets').click()
        driver.find_element_by_link_text('Add Dataset').click()
        driver.find_element_by_id('field-title').clear()
        driver.find_element_by_id('field-title').send_keys(name)
        driver.find_element_by_id('field-notes').clear()
        driver.find_element_by_id('field-notes').send_keys(description)
        driver.find_element_by_id('field-tags').clear()
        driver.find_element_by_id('field-tags').send_keys(','.join(tags))
        Select(driver.find_element_by_id('field-private')).select_by_visible_text('Private' if private else 'Public')

        # If the dataset is private, we should complete the fields
        # If the dataset is public, these fields will be disabled (we'll check it)
        if private:
            Select(driver.find_element_by_id('field-searchable')).select_by_visible_text('True' if searchable else 'False')
            driver.find_element_by_id('field-allowed_users_str').clear()
            driver.find_element_by_id('field-allowed_users_str').send_keys(','.join(allowed_users))
            driver.find_element_by_id('field-adquire_url').clear()
            if adquire_url:
                driver.find_element_by_id('field-adquire_url').send_keys(adquire_url)
        else:
            self.assert_fields_disabled(['field-searchable', 'field-allowed_users_str', 'field-adquire_url'])

        driver.find_element_by_name('save').click()

    def create_ds(self, name, description, tags, private, searchable, allowed_users, adquire_url, resource_url, resource_name, resource_description, resource_format):
        driver = self.driver
        self.create_ds_first_page(name, description, tags, private, searchable, allowed_users, adquire_url)

        # SECOND PAGE: Add Resources
        try:
            # The link button is only clicked if it's present
            driver.find_element_by_link_text('Link').click()
        except Exception:
            pass

        # THIRD PAGE: Metadata
        driver.find_element_by_id('field-image-url').clear()
        driver.find_element_by_id('field-image-url').send_keys(resource_url)
        driver.find_element_by_id('field-name').clear()
        driver.find_element_by_id('field-name').send_keys(resource_name)
        driver.find_element_by_id('field-description').clear()
        driver.find_element_by_id('field-description').send_keys(resource_description)
        driver.find_element_by_id('s2id_autogen1').clear()
        driver.find_element_by_id('s2id_autogen1').send_keys(resource_format)
        driver.find_element_by_xpath('(//button[@name=\'save\'])[4]').click()
        driver.find_element_by_xpath('(//button[@name=\'save\'])[4]').click()

    def check_ds_values(self, url, private, searchable, allowed_users, adquire_url):
        driver = self.driver
        driver.get(self.base_url + 'dataset/edit/' + url)
        self.assertEqual('Private' if private else 'Public', Select(driver.find_element_by_id('field-private')).first_selected_option.text)

        if private:
            adquire_url_final = '' if adquire_url is None else adquire_url
            self.assertEqual(adquire_url_final, driver.find_element_by_id('field-adquire_url').get_attribute('value'))
            self.assertEqual('True' if searchable else 'False', Select(driver.find_element_by_id('field-searchable')).first_selected_option.text)
            
            # Test that the allowed users lists is as expected (order is not important)
            current_users = driver.find_element_by_css_selector('#s2id_field-allowed_users_str > ul.select2-choices').text.split('\n')
            # ''.split('\n') ==> ['']
            if len(current_users) == 1 and current_users[0] == '':
                current_users = []
            # Check the array
            self.assertEquals(len(allowed_users), len(current_users))
            for user in current_users:
                self.assertIn(user, allowed_users)
        else:
            self.assert_fields_disabled(['field-searchable', 'field-allowed_users_str', 'field-adquire_url'])

    def check_user_access(self, dataset, dataset_url, owner, adquired, private, searchable, adquire_url=None):
        driver = self.driver
        driver.find_element_by_link_text('Datasets').click()

        if searchable:
            xpath = '//div[@id=\'content\']/div[3]/div/section/div/ul/li/div/h3/span'

            # Check the label
            if not adquired and private:
                self.assertEqual('PRIVATE', driver.find_element_by_xpath(xpath).text)
            elif adquired and not owner and private:
                self.assertEqual('ADQUIRED', driver.find_element_by_xpath(xpath).text)
            elif owner:
                self.assertEqual('OWNER', driver.find_element_by_xpath(xpath).text)

            # Access the dataset
            driver.find_element_by_link_text(dataset).click()

        else:
            # If the dataset is not searchable, a link to it could not be found in the dataset search page
            self.assertEquals(None, re.search(dataset_url, driver.page_source))

            # Access the dataset
            driver.get(self.base_url + 'dataset/' + dataset_url)

        if not adquired and private:
            xpath = '//div[@id=\'content\']/div/div'
            buy_msg = 'This private dataset can be adquired. To do so, please click here'
            if adquire_url is not None:
                self.assertTrue(driver.find_element_by_xpath(xpath).text.startswith(buy_msg))
                self.assertEquals(adquire_url, driver.find_element_by_link_text('here').get_attribute('href'))
                xpath += '[2]'  # The unauthorized message is in a different Path
            else:
                src = driver.page_source
                self.assertEquals(None, re.search(buy_msg, src))

            self.assertTrue('/user/login' in driver.current_url)
            self.assertTrue(driver.find_element_by_xpath(xpath).text.startswith('Unauthorized to read package %s' % dataset_url))

        else:
            self.assertEquals(self.base_url + 'dataset/%s' % dataset_url, driver.current_url)

    def check_adquired(self, dataset, dataset_url, adquired, private):
        driver = self.driver
        driver.get(self.base_url + 'dashboard')
        driver.find_element_by_link_text('Adquired Datasets').click()

        if adquired and private:
            driver.find_element_by_link_text(dataset).click()
            self.assertEquals(self.base_url + 'dataset/%s' % dataset_url, driver.current_url)
        else:
            # If the user has not adquired the dataset, a link to this dataset could not be in the adquired dataset list
            self.assertEquals(None, re.search(dataset_url, driver.page_source))

    def default_register(self, user):
        self.register(user, user, '%s@conwet.com' % user, user)

    @parameterized.expand([
        (['user1', 'user2', 'user3'],          True,  True,  ['user2'],          'http://store.conwet.com/'),
        (['user1', 'user2', 'user3'],          True,  True,  ['user3']),
        (['user1', 'user2', 'user3'],          False, True,  ['user3']),
        (['user1', 'user2', 'user3'],          True,  False, ['user2']),
        (['user1', 'user2', 'user3'],          True,  True,  [],                 'http://store.conwet.com/'),
        (['user1', 'user2', 'user3'],          True,  True,  []),
        (['user1', 'user2', 'user3'],          False, True,  []),
        (['user1', 'user2', 'user3'],          True,  False, []),
        (['user1', 'user2', 'user3', 'user4'], True,  True,  ['user2', 'user4'], 'http://store.conwet.com/'),
        (['user1', 'user2', 'user3', 'user4'], True,  True,  ['user3', 'user4']),
        (['user1', 'user2', 'user3', 'user4'], False, True,  ['user3', 'user4']),
        (['user1', 'user2', 'user3', 'user4'], True,  False, ['user2', 'user4']),
    ])
    def test_basic(self, users, private, searchable, allowed_users, adquire_url=None):
        # Create users
        for user in users:
            self.default_register(user)

        # The first user creates a dataset
        self.login(users[0], users[0])
        pkg_name = 'Dataset 1'
        url = get_dataset_url(pkg_name)
        self.create_ds(pkg_name, 'Example description', ['tag1', 'tag2', 'tag3'], private, searchable,
                       allowed_users, adquire_url, 'http://upm.es', 'UPM Main', 'Example Description', 'CSV')
        self.check_ds_values(url, private, searchable, allowed_users, adquire_url)
        self.check_user_access(pkg_name, url, True, True, private, searchable, adquire_url)
        self.check_adquired(pkg_name, url, False, private)

        # Rest of users
        rest_users = users[1:]
        for user in rest_users:
            self.logout()
            self.login(user, user)
            adquired = user in allowed_users
            self.check_user_access(pkg_name, url, False, adquired, private, searchable, adquire_url)
            self.check_adquired(pkg_name, url, adquired, private)

    @parameterized.expand([
        (['a']  ,          'http://upm.es',      'Allowed users: Name must be at least 2 characters long'),
        (['a a'],          'http://upm.es',      'Allowed users: Url must be purely lowercase alphanumeric (ascii) characters and these symbols: -_'),
        (['upm', 'a'],     'http://upm.es',      'Allowed users: Name must be at least 2 characters long'),
        (['upm', 'a a a'], 'http://upm.es',      'Allowed users: Url must be purely lowercase alphanumeric (ascii) characters and these symbols: -_'),
        (['upm', 'a?-vz'], 'http://upm.es',      'Allowed users: Url must be purely lowercase alphanumeric (ascii) characters and these symbols: -_'),
        (['thisisaveryveryveryveryveryveryveryveryveryveryveryveryveryveryveryveryveryveryveryveryveryveryveryverylongname'],
                           'http://upm.es',      'Allowed users: Name must be a maximum of 100 characters long'),
        (['conwet'],       'ftp://google.es',    'Adquire URL: The URL "ftp://google.es" is not valid.'),
        (['conwet'],       'http://google*.com', 'Adquire URL: The URL "http://google*.com" is not valid.'),
        (['conwet'],       'http://google+.com', 'Adquire URL: The URL "http://google+.com" is not valid.'),
        (['conwet'],       'http://google/.com', 'Adquire URL: The URL "http://google/.com" is not valid.'),
        (['conwet'],       'google',             'Adquire URL: The URL "google" is not valid.'),
        (['conwet'],       'http://google',      'Adquire URL: The URL "http://google" is not valid.'),
        (['conwet'],       'http://google:es',   'Adquire URL: The URL "http://google:es" is not valid.'),
        (['conwet'],       'www.google.es',      'Adquire URL: The URL "www.google.es" is not valid.')

    ])
    def test_invalid_fields(self, allowed_users, adquire_url, expected_msg):
        # Create a default user
        user = 'user1'
        self.default_register(user)

        # Create the dataset
        self.login(user, user)
        pkg_name = 'Dataset 2'
        self.create_ds_first_page(pkg_name, 'Example description', ['tag1'], True, True, allowed_users, adquire_url)

        # Check the error message
        msg_error = self.driver.find_element_by_xpath('//div[@id=\'content\']/div[3]/div/section/div/form/div/ul/li').text
        self.assertEquals(expected_msg, msg_error)

    @parameterized.expand([
        ('Adquire Dataset',  'dataset'),
        ('Adquire one now?', 'dataset')
    ])
    def test_dashboard_basic_links(self, link, expected_url):
        # Create a default user
        user = 'user1'
        self.default_register(user)
        self.login(user, user)

        # Enter the adquired dataset tab
        driver = self.driver
        driver.get(self.base_url + 'dashboard/adquired')
        driver.find_element_by_link_text(link).click()
        self.assertEquals(self.base_url + 'dataset', self.base_url + expected_url)

    @parameterized.expand([

        # Allowed users contains just one user
        ([{'private': True,  'searchable': True,  'allowed_users': ['user1']}],          ['user2']),
        ([{'private': False, 'searchable': True,  'allowed_users': ['user1']}],          ['user2']),
        ([{'private': True,  'searchable': False, 'allowed_users': ['user1']}],          ['user2']),
        ([{'private': False, 'searchable': False, 'allowed_users': ['user1']}],          ['user2']),

        # Allowed users contains more than one user
        ([{'private': True,  'searchable': True,  'allowed_users': ['user1', 'user2']}], ['user3']),
        ([{'private': False, 'searchable': True,  'allowed_users': ['user1', 'user2']}], ['user3']),
        ([{'private': True,  'searchable': False, 'allowed_users': ['user1', 'user2']}], ['user3']),
        ([{'private': False, 'searchable': False, 'allowed_users': ['user1', 'user2']}], ['user3']),

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

        adquire_url = 'http://upm.es'
        dataset_default_name = 'Dataset %d'

        # Create the dataset
        for i, dataset in enumerate(datasets):
            pkg_name = dataset_default_name % i
            self.create_ds(pkg_name, 'Example description', ['tag1'], dataset['private'], dataset['searchable'],
                           dataset['allowed_users'], adquire_url, 'http://upm.es', 'UPM Main', 'Example Description', 'CSV')

        # Make the requests
        for user in users_via_api:

            resources = []
            for i, dataset in enumerate(datasets):
                resources.append({'url': self.base_url + 'dataset/' + get_dataset_url(dataset_default_name % i)})

            content = {'customer_name': user, 'resources': resources}
            req = requests.post(self.base_url + 'api/action/package_adquired', data=json.dumps(content),
                                headers={'content-type': 'application/json'})

            result = json.loads(req.text)['result']
            for i, dataset in enumerate(datasets):
                if not dataset['private']:
                    url_path = get_dataset_url(dataset_default_name % i)
                    self.assertIn('Unable to upload the dataset %s: It\'s a public dataset' % url_path, result['warns'])

        # Check the dataset
        for i, dataset in enumerate(datasets):

            if dataset['private']:
                final_users = list(dataset['allowed_users'])
                for user in users_via_api:
                    if user not in final_users:
                        final_users.append(user)
            else:
                final_users = []

            pkg_name = dataset_default_name % i
            url_path = get_dataset_url(pkg_name)
            self.check_ds_values(url_path, dataset['private'], dataset['searchable'], final_users, adquire_url)
