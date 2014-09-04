import ckan.model as model
from ckan.plugins import toolkit
import ckan.lib.helpers as helpers
from ckanext.glasgow.logic.action import ECAPIError

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
            extra_vars['request_status'] = request_status,
        except ECAPIError, e:
            helpers.flash_error('{0}'.format(e.error_dict['message']))
            toolkit.abort(
                502,
                'Error fetching request from CTPEC Plaftform {}'.format(str(e))
            )
        except toolkit.ValidationError, e:
            helpers.flash_error('{0}'.format(e.error_dict['message']))
        return toolkit.render('request_status.html', extra_vars=extra_vars)
