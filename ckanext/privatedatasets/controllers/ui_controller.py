import ckan.lib.base as base
import ckan.model as model
import ckan.plugins as plugins
import ckanext.privatedatasets.db as db
import logging

from ckan.common import _

log = logging.getLogger(__name__)


class AdquiredDatasetsControllerUI(base.BaseController):

    def user_adquired_datasets(self):

        if db.package_allowed_users_table is None:
            db.init_db(model)

        c = plugins.toolkit.c
        context = {
            'model': model,
            'session': model.Session,
            'user': plugins.toolkit.c.user
        }

        # Get user information
        try:
            c.user_dict = plugins.toolkit.get_action('user_show')(context, {'user_obj': c.userobj})
            c.user_dict['adquired_datasets'] = []
        except plugins.toolkit.ObjectNotFound:
            plugins.toolkit.abort(404, _('User not found'))
        except plugins.toolkit.NotAuthorized:
            plugins.toolkit.abort(401, _('Not authorized to see this page'))

        # Get the datasets adquired by the user
        query = db.AllowedUser.get(user_name=context['user'])

        # Get the datasets
        for dataset in query:
            try:
                dataset_dict = plugins.toolkit.get_action('package_show')(context, {'id': dataset.package_id})
                c.user_dict['adquired_datasets'].append(dataset_dict)
            except Exception:
                continue

        return plugins.toolkit.render('user/dashboard_adquired.html')
