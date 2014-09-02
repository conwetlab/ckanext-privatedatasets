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

import ckan.lib.base as base
import ckan.model as model
import ckan.plugins as plugins
import ckanext.privatedatasets.db as db
import logging

from ckan.common import _

log = logging.getLogger(__name__)


class AcquiredDatasetsControllerUI(base.BaseController):

    def user_acquired_datasets(self):

        db.init_db(model)

        c = plugins.toolkit.c
        context = {
            'model': model,
            'session': model.Session,
            'user': plugins.toolkit.c.user,
        }

        # Get user information
        try:
            c.user_dict = plugins.toolkit.get_action('user_show')(context.copy(), {'user_obj': c.userobj})
            c.user_dict['acquired_datasets'] = []
        except plugins.toolkit.ObjectNotFound:
            plugins.toolkit.abort(404, _('User not found'))
        except plugins.toolkit.NotAuthorized:
            plugins.toolkit.abort(401, _('Not authorized to see this page'))

        # Get the datasets acquired by the user
        query = db.AllowedUser.get(user_name=context['user'])

        # Get the datasets
        for dataset in query:
            try:
                dataset_dict = plugins.toolkit.get_action('package_show')(context.copy(), {'id': dataset.package_id})
                # Only packages with state == 'active' can be shown
                if dataset_dict.get('state', None) == 'active':
                    c.user_dict['acquired_datasets'].append(dataset_dict)
            except Exception:
                continue

        return plugins.toolkit.render('user/dashboard_acquired.html')
