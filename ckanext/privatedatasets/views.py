# -*- coding: utf-8 -*-

# Copyright (c) 2018 Future Internet Consulting and Development Solutions S.L.

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

from __future__ import absolute_import, unicode_literals

from ckan import logic
from ckan.common import _, g
from ckan.lib import base
from ckan.plugins import toolkit

from ckanext.privatedatasets import constants


def acquired_datasets():
    context = {'for_view': True, 'user': g.user, 'auth_user_obj': g.userobj}
    data_dict = {'user_obj': g.userobj}
    try:
        user_dict = logic.get_action('user_show')(context, data_dict)
        acquired_datasets = toolkit.get_action(constants.ACQUISITIONS_LIST)(context, None)
    except logic.NotFound:
        base.abort(404, _('User not found'))
    except logic.NotAuthorized:
        base.abort(403, _('Not authorized to see this page'))

    extra_vars = {
        'user_dict': user_dict,
        'acquired_datasets': acquired_datasets,
    }
    return base.render('user/dashboard_acquired.html', extra_vars)
