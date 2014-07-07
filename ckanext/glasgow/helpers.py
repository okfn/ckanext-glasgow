import json
from ckan import model
import ckan.lib.helpers as helpers
import ckan.plugins.toolkit as toolkit

def get_licenses():

    return [('', '')] + model.Package.get_license_options()

def get_resource_versions(dataset_id, resource_id):
    try:
        context = {
            'model': model,
            'session': model.Session,
            'user': toolkit.c.user,
        }
        resource_versions_show = toolkit.get_action('resource_version_show')
        return resource_versions_show(context, {
            'package_id': dataset_id,
            'resource_id': resource_id,
        })
    except (toolkit.ValidationError, toolkit.NotAuthorized, toolkit.ObjectNotFound), e:

        helpers.flash_error('{0}'.format(e.error_dict['message']))
        return []
