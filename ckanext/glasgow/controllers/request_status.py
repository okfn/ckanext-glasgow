import datetime

import sqlalchemy

import ckan.model as model
from ckan.plugins import toolkit
import ckan.lib.helpers as helpers
from ckanext.glasgow.logic.action import (
    ECAPIError, 
    _expire_task_status,
)
from ckanext.glasgow.harvesters import get_task_for_request_id

class RequestStatusController(toolkit.BaseController):
    def get_status(self, request_id):
        context = {
            'model': model,
            'session': model.Session,
        }
        extra_vars = {}
        try:
            request_status = toolkit.get_action('get_change_request')(context,
                {'id': request_id})
            if not request_status:
                toolkit.abort(404, toolkit._(
                    'Request {0} not found'.format(request_id)))
            extra_vars['request_status'] = request_status
        except ECAPIError, e:
            toolkit.abort(
                502,
                'Error fetching request from CTPEC Plaftform {}'.format(str(e))
            )
        except toolkit.ValidationError, e:
            helpers.flash_error('{0}'.format(e.error_dict['message']))

        try:
            task = get_task_for_request_id(context, request_id)
            if task and request_status:
                latest = request_status[-1]
                if latest.get('operation_state') == 'Failed':
                    task.state = 'error'
                    task.last_updated = datetime.datetime.now()
                    task.save()
                    _expire_task_status(context, task.id)

        except sqlalchemy.exc.SQLAlchemyError:
            pass


        return toolkit.render('request_status.html', extra_vars=extra_vars)
