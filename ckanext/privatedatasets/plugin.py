# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2017 CoNWeT Lab., Universidad Politécnica de Madrid

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

import ckan.lib.search as search
import ckan.model as model
import ckan.plugins as p
import ckan.plugins.toolkit as tk

from ckan.lib.plugins import DefaultPermissionLabels

import auth
import actions
import constants
import converters_validators as conv_val
import db
import helpers as helpers


HIDDEN_FIELDS = [constants.ALLOWED_USERS, constants.SEARCHABLE]


class PrivateDatasets(p.SingletonPlugin, tk.DefaultDatasetForm, DefaultPermissionLabels):

    p.implements(p.IDatasetForm)
    p.implements(p.IAuthFunctions)
    p.implements(p.IConfigurer)
    p.implements(p.IRoutes, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IPackageController, inherit=True)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IPermissionLabels)

    ######################################################################
    ############################ DATASET FORM ############################
    ######################################################################

    def __init__(self, name=None):
        self.indexer = search.PackageSearchIndex()

    def _modify_package_schema(self):
        return {
            # remove datasets_with_no_organization_cannot_be_private validator
            'private': [tk.get_validator('ignore_missing'),
                        tk.get_validator('boolean_validator')],
            constants.ALLOWED_USERS_STR: [tk.get_validator('ignore_missing'),
                                          conv_val.private_datasets_metadata_checker],
            constants.ALLOWED_USERS: [conv_val.allowed_users_convert,
                                      tk.get_validator('ignore_missing'),
                                      conv_val.private_datasets_metadata_checker],
            constants.ACQUIRE_URL: [tk.get_validator('ignore_missing'),
                                    conv_val.private_datasets_metadata_checker,
                                    conv_val.url_checker,
                                    tk.get_converter('convert_to_extras')],
            constants.SEARCHABLE: [tk.get_validator('ignore_missing'),
                                   conv_val.private_datasets_metadata_checker,
                                   tk.get_converter('convert_to_extras'),
                                   tk.get_validator('boolean_validator')]
        }

    def create_package_schema(self):
        # grab the default schema in our plugin
        schema = super(PrivateDatasets, self).create_package_schema()
        schema.update(self._modify_package_schema())
        return schema

    def update_package_schema(self):
        # grab the default schema in our plugin
        schema = super(PrivateDatasets, self).update_package_schema()
        schema.update(self._modify_package_schema())
        return schema

    def show_package_schema(self):
        schema = super(PrivateDatasets, self).show_package_schema()
        schema.update({
            constants.ALLOWED_USERS: [conv_val.get_allowed_users,
                                      tk.get_validator('ignore_missing')],
            constants.ACQUIRE_URL: [tk.get_converter('convert_from_extras'),
                                    tk.get_validator('ignore_missing')],
            constants.SEARCHABLE: [tk.get_converter('convert_from_extras'),
                                   tk.get_validator('ignore_missing')]
        })
        return schema

    def is_fallback(self):
        # Return True to register this plugin as the default handler for
        # package types not handled by any other IDatasetForm plugin.
        return True

    def package_types(self):
        # This plugin doesn't handle any special package types, it just
        # registers itself as the default (above).
        return []

    ######################################################################
    ########################### AUTH FUNCTIONS ###########################
    ######################################################################

    def get_auth_functions(self):
        auth_functions = {'package_show': auth.package_show,
                          'package_update': auth.package_update,
                          # 'resource_show': auth.resource_show,
                          constants.PACKAGE_ACQUIRED: auth.package_acquired,
                          constants.ACQUISITIONS_LIST: auth.acquisitions_list,
                          constants.PACKAGE_DELETED: auth.revoke_access}

        # resource_show is not required in CKAN 2.3 because it delegates to
        # package_show
        if not tk.check_ckan_version(min_version='2.3'):
            auth_functions['resource_show'] = auth.resource_show

        return auth_functions

    ######################################################################
    ############################ ICONFIGURER #############################
    ######################################################################

    def update_config(self, config):
        # Add this plugin's templates dir to CKAN's extra_template_paths, so
        # that CKAN will use this plugin's custom templates.
        tk.add_template_directory(config, 'templates')

        # Register this plugin's fanstatic directory with CKAN.
        tk.add_resource('fanstatic', 'privatedatasets')

    ######################################################################
    ############################## IROUTES ###############################
    ######################################################################

    def before_map(self, m):
        # DataSet acquired notification
        m.connect('user_acquired_datasets', '/dashboard/acquired', ckan_icon='shopping-cart',
                  controller='ckanext.privatedatasets.controllers.ui_controller:AcquiredDatasetsControllerUI',
                  action='user_acquired_datasets', conditions=dict(method=['GET']))

        return m

    

    ######################################################################
    ############################## IACTIONS ##############################
    ######################################################################

    def get_actions(self):
        return {
            constants.PACKAGE_ACQUIRED: actions.package_acquired,
            constants.ACQUISITIONS_LIST: actions.acquisitions_list,
            constants.PACKAGE_DELETED: actions.revoke_access
        }

    ######################################################################
    ######################### IPACKAGECONTROLLER #########################
    ######################################################################

    def _delete_pkg_atts(self, pkg_dict, attrs):
        for attr in attrs:
            if attr in pkg_dict:
                del pkg_dict[attr]

    def before_index(self, pkg_dict):

        if 'extras_' + constants.SEARCHABLE in pkg_dict:
            if pkg_dict['extras_searchable'] == 'False':
                pkg_dict['capacity'] = 'private'
            else:
                pkg_dict['capacity'] = 'public'

        return pkg_dict

    def after_create(self, context, pkg_dict):
        session = context['session']
        update_cache = False

        db.init_db(context['model'])

        # Get the users and the package ID
        if constants.ALLOWED_USERS in pkg_dict:

            allowed_users = pkg_dict[constants.ALLOWED_USERS]
            package_id = pkg_dict['id']

            # Get current users
            users = db.AllowedUser.get(package_id=package_id)

            # Delete users and save the list of current users
            current_users = []
            for user in users:
                current_users.append(user.user_name)
                if user.user_name not in allowed_users:
                    session.delete(user)
                    update_cache = True

            # Add non existing users
            for user_name in allowed_users:
                if user_name not in current_users:
                    out = db.AllowedUser()
                    out.package_id = package_id
                    out.user_name = user_name
                    out.save()
                    session.add(out)
                    update_cache = True

            session.commit()

            # The cache should be updated. Otherwise, the system may return
            # outdated information in future requests
            if update_cache:
                new_pkg_dict = tk.get_action('package_show')(
                    {'model': context['model'],
                     'ignore_auth': True,
                     'validate': False,
                     'use_cache': False},
                    {'id': package_id})

                # Prevent acquired datasets jumping to the first position
                revision = tk.get_action('revision_show')({'ignore_auth': True}, {'id': new_pkg_dict['revision_id']})
                new_pkg_dict['metadata_modified'] = revision.get('timestamp', '')
                self.indexer.update_dict(new_pkg_dict)

        return pkg_dict

    def after_update(self, context, pkg_dict):
        return self.after_create(context, pkg_dict)

    def after_show(self, context, pkg_dict):

        user_obj = context.get('auth_user_obj')
        updating_via_api = context.get(constants.CONTEXT_CALLBACK, False)

        # allowed_users and searchable fileds can be only viewed by (and only if the dataset is private):
        # * the dataset creator
        # * the sysadmin
        # * users allowed to update the allowed_users list via the notification API
        if pkg_dict.get('private') is False or not updating_via_api and (not user_obj or (pkg_dict['creator_user_id'] != user_obj.id and not user_obj.sysadmin)):
            # The original list cannot be modified
            attrs = list(HIDDEN_FIELDS)
            self._delete_pkg_atts(pkg_dict, attrs)

        return pkg_dict

    def after_delete(self, context, pkg_dict):
        session = context['session']
        package_id = pkg_dict['id']

        # Get current users
        db.init_db(context['model'])
        users = db.AllowedUser.get(package_id=package_id)

        # Delete all the users
        for user in users:
            session.delete(user)
        session.commit()

        return pkg_dict

    def after_search(self, search_results, search_params):
        for result in search_results['results']:
            # Extra fields should not be returned 
            # The original list cannot be modified
            attrs = list(HIDDEN_FIELDS)

            # Additionally, resources should not be included if the user is not allowed
            # to show the resource
            context = {
                'model': model,
                'session': model.Session,
                'user': tk.c.user,
                'user_obj': tk.c.userobj
            }

            try:
                tk.check_access('package_show', context, result)
            except tk.NotAuthorized:
                # NotAuthorized exception is risen when the user is not allowed
                # to read the package.
                attrs.append('resources')

            # Delete
            self._delete_pkg_atts(result, attrs)

        return search_results

    ####

    def get_dataset_labels(self, dataset_obj):
        labels = super(PrivateDatasets, self).get_dataset_labels(
            dataset_obj)

        if getattr(dataset_obj, 'searchable', False):
            labels.append('searchable')

        return labels

    def get_user_dataset_labels(self, user_obj):
        labels = super(PrivateDatasets, self).get_user_dataset_labels(
            user_obj)

        labels.append('searchable')
        return labels

    ######################################################################
    ######################### ITEMPLATESHELPER ###########################
    ######################################################################

    def get_helpers(self):
        return {'is_dataset_acquired': helpers.is_dataset_acquired,
                'get_allowed_users_str': helpers.get_allowed_users_str,
                'is_owner': helpers.is_owner,
                'can_read': helpers.can_read,
                'show_acquire_url_on_create': helpers.show_acquire_url_on_create,
                'show_acquire_url_on_edit': helpers.show_acquire_url_on_edit,
                'acquire_button': helpers.acquire_button
                }
