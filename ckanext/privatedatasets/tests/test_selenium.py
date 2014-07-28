
from nose_parameterized import parameterized
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from subprocess import Popen

import ckan.model as model
import ckanext.privatedatasets.db as db
import os
import unittest
import re


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
    
    def setUp(self):
        # Clean the database
        model.repo.rebuild_db()

        # Delete previous users
        db.init_db(model)
        users = db.AllowedUser.get()
        for user in users:
            model.Session.delete(user)
        model.Session.commit()

        self.driver = webdriver.Firefox()
        self.driver.implicitly_wait(5)
        self.driver.set_window_size(1024, 768)
        self.base_url = "http://127.0.0.1:5000/"
        self.verificationErrors = []
        self.accept_next_alert = True

    def tearDown(self):
        self.driver.quit()
        self.assertEqual([], self.verificationErrors)

    def assert_fields_disabled(self, fields):
        for field in fields:
            self.assertFalse(self.driver.find_element_by_id(field).is_enabled())

    def logout(self):
        self.driver.find_element_by_css_selector("i.icon-signout").click()

    def register(self, username, fullname, mail, password):
        driver = self.driver
        driver.get(self.base_url)
        driver.find_element_by_link_text("Register").click()
        driver.find_element_by_id("field-username").clear()
        driver.find_element_by_id("field-username").send_keys(username)
        driver.find_element_by_id("field-fullname").clear()
        driver.find_element_by_id("field-fullname").send_keys(fullname)
        driver.find_element_by_id("field-email").clear()
        driver.find_element_by_id("field-email").send_keys(mail)
        driver.find_element_by_id("field-password").clear()
        driver.find_element_by_id("field-password").send_keys(password)
        driver.find_element_by_id("field-confirm-password").clear()
        driver.find_element_by_id("field-confirm-password").send_keys(password)
        driver.find_element_by_name("save").click()
        self.logout()

    def login(self, username, password):
        driver = self.driver
        driver.get(self.base_url)
        driver.find_element_by_link_text("Log in").click()
        driver.find_element_by_id("field-login").clear()
        driver.find_element_by_id("field-login").send_keys(username)
        driver.find_element_by_id("field-password").clear()
        driver.find_element_by_id("field-password").send_keys(password)
        driver.find_element_by_id("field-remember").click()
        driver.find_element_by_css_selector("button.btn.btn-primary").click()

    def create_ds(self, name, description, tags, private, searchable, allowed_users, adquire_url, resource_url, resource_name, resource_description, resource_format):
        driver = self.driver
        driver.get(self.base_url)
        driver.find_element_by_link_text("Datasets").click()
        driver.find_element_by_link_text("Add Dataset").click()
        driver.find_element_by_id("field-title").clear()
        driver.find_element_by_id("field-title").send_keys(name)
        driver.find_element_by_id("field-notes").clear()
        driver.find_element_by_id("field-notes").send_keys(description)
        driver.find_element_by_id("field-tags").clear()
        driver.find_element_by_id("field-tags").send_keys(','.join(tags))
        Select(driver.find_element_by_id("field-private")).select_by_visible_text("Private" if private else "Public")

        # If the dataset is private, we should complete the fields
        # If the dataset is public, these fields should be disabled
        if private:
            Select(driver.find_element_by_id("field-searchable")).select_by_visible_text("True" if searchable else "False")
            driver.find_element_by_id("field-allowed_users_str").clear()
            driver.find_element_by_id("field-allowed_users_str").send_keys(','.join(allowed_users))
            driver.find_element_by_id("field-adquire_url").clear()
            if adquire_url:
                driver.find_element_by_id("field-adquire_url").send_keys(adquire_url)
        else:
            self.assert_fields_disabled(['field-searchable', 'field-allowed_users_str', 'field-adquire_url'])

        driver.find_element_by_name("save").click()

        # The link button is only clicked if it's present
        try:
            driver.find_element_by_link_text("Link").click()
        except Exception:
            pass

        driver.find_element_by_id("field-image-url").clear()
        driver.find_element_by_id("field-image-url").send_keys(resource_url)
        driver.find_element_by_id("field-name").clear()
        driver.find_element_by_id("field-name").send_keys(resource_name)
        driver.find_element_by_id("field-description").clear()
        driver.find_element_by_id("field-description").send_keys(resource_description)
        driver.find_element_by_id("s2id_autogen1").clear()
        driver.find_element_by_id("s2id_autogen1").send_keys(resource_format)
        driver.find_element_by_xpath("(//button[@name='save'])[4]").click()
        driver.find_element_by_xpath("(//button[@name='save'])[4]").click()

    def check_ds_values(self, name, private, searchable, allowed_users, adquire_url):
        driver = self.driver
        driver.get(self.base_url + "dataset/edit/dataset-1")
        self.assertEqual("Private" if private else "Public", Select(driver.find_element_by_id("field-private")).first_selected_option.text)

        if private:
            adquire_url_final = '' if adquire_url is None else adquire_url
            self.assertEqual(adquire_url_final, driver.find_element_by_id("field-adquire_url").get_attribute("value"))
            self.assertEqual("True" if searchable else "False", Select(driver.find_element_by_id("field-searchable")).first_selected_option.text)
            self.assertEqual('\n'.join(allowed_users), driver.find_element_by_css_selector("#s2id_field-allowed_users_str > ul.select2-choices").text)
        else:
            self.assert_fields_disabled(['field-searchable', 'field-allowed_users_str', 'field-adquire_url'])

    def check_user_access(self, dataset, dataset_url, owner, adquired, private, searchable, adquire_url=None):
        driver = self.driver
        driver.find_element_by_link_text("Datasets").click()

        if searchable:
            xpath = "//div[@id='content']/div[3]/div/section/div/ul/li/div/h3/span"

            # Check the label
            if not adquired and private:
                self.assertEqual("PRIVATE", driver.find_element_by_xpath(xpath).text)
            elif adquired and not owner and private:
                self.assertEqual("ADQUIRED", driver.find_element_by_xpath(xpath).text)
            elif owner:
                self.assertEqual("OWNER", driver.find_element_by_xpath(xpath).text)

            # Access the dataset
            driver.find_element_by_link_text(dataset).click()

            if not adquired and private:
                xpath = "//div[@id='content']/div/div"
                buy_msg = 'This private dataset can be adquired. To do so, please click here'
                if adquire_url is not None:
                    self.assertTrue(driver.find_element_by_xpath(xpath).text.startswith(buy_msg))
                    self.assertEquals(adquire_url, driver.find_element_by_link_text("here").get_attribute('href'))
                    xpath += "[2]"  # The unauthorized message is in a different Path
                else:
                    src = driver.page_source
                    self.assertEquals(None, re.search(buy_msg, src))

                self.assertTrue('/user/login' in driver.current_url)
                self.assertTrue(driver.find_element_by_xpath(xpath).text.startswith('Unauthorized to read package %s' % dataset_url))

            else:
                self.assertEquals(self.base_url + 'dataset/%s' % dataset_url, driver.current_url)
        else:
            # If the dataset is not searchable, a link to it could not be found in the dataset search page
            self.assertEquals(None, re.search(dataset_url, driver.page_source))

    def check_adquired(self, dataset, dataset_url, adquired, private):
        driver = self.driver
        driver.get(self.base_url + "dashboard")
        driver.find_element_by_link_text("Adquired Datasets").click()

        print adquired, private

        if adquired and private:
            driver.find_element_by_link_text(dataset).click()
            self.assertEquals(self.base_url + 'dataset/%s' % dataset_url, driver.current_url)
        else:
            # If the user has not adquired the dataset, a link to this dataset could not be in the adquired dataset list
            self.assertEquals(None, re.search(dataset_url, driver.page_source))


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
            self.register(user, user, '%s@conwet.com' % user, user)

        # The first creates a dataset
        self.login(users[0], users[0])
        original_name = 'Dataset 1'
        url_name = original_name.replace(' ', '-').lower()
        self.create_ds(original_name, 'Example description', ['tag1', 'tag2', 'tag3'], private, searchable, allowed_users, adquire_url, 'http://upm.es', 'UPM Main', 'Example Description', 'CSV')
        self.check_ds_values(url_name, private, searchable, allowed_users, adquire_url)
        self.check_user_access(original_name, url_name, True, True, private, searchable, adquire_url)
        self.check_adquired(original_name, url_name, False, private)

        # Rest of users
        rest_users = users[1:]
        for user in rest_users:
            self.logout()
            self.login(user, user)
            adquired = user in allowed_users
            self.check_user_access(original_name, url_name, False, adquired, private, searchable, adquire_url)
            self.check_adquired(original_name, url_name, adquired, private)
