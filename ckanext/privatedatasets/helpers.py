# -*- coding: utf-8 -*-

# Copyright (c) 2014-2015 CoNWeT Lab., Universidad Politécnica de Madrid

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

import ckan.model as model
import ckan.plugins.toolkit as tk
import db

from pylons import config

from ckan.common import request

import logging
log = logging.getLogger(__name__)


def is_dataset_acquired(pkg_dict):

    db.init_db(model)

    if tk.c.user:
        return len(db.AllowedUser.get(package_id=pkg_dict['id'], user_name=tk.c.user)) > 0
    else:
        return False


def is_owner(pkg_dict):
    if tk.c.userobj is not None:
        return tk.c.userobj.id == pkg_dict['creator_user_id']
    else:
        return False


def get_allowed_users_str(users):
    if users:
        return ','.join([user for user in users])
    else:
        return ''


def can_read(pkg_dict):
    try:
        context = {'user': tk.c.user, 'userobj': tk.c.userobj, 'model': model}
        return tk.check_access('package_show', context, pkg_dict)
    except tk.NotAuthorized:
        return False


def get_config_bool_value(config_name, default_value=False):
    value = config.get(config_name, default_value)
    value = value if type(value) == bool else value != 'False'
    return value


def show_acquire_url_on_create():
    return get_config_bool_value('ckan.privatedatasets.show_acquire_url_on_create')


def show_acquire_url_on_edit():
    return get_config_bool_value('ckan.privatedatasets.show_acquire_url_on_edit')


def acquire_button(package):
    '''
    Return a Get Access button for the given package id when the dataset has
    an acquisition URL.

    :param package: the the package to request access when the get access
        button is clicked
    :type package: Package

    :returns: a get access button as an HTML snippet
    :rtype: string

    '''

    if 'acquire_url' in package and request.path.startswith('/dataset')\
            and package['acquire_url'] != '':
        url_dest = package['acquire_url']
        data = {'url_dest': url_dest}
        return tk.render_snippet('snippets/acquire_button.html', data)
    else:
        return ''
