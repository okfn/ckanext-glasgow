import pylons

import ckan.model as model
import ckan.new_authz as new_authz
import ckan.plugins.toolkit as toolkit
import ckan.lib.helpers as helpers

from ckanext.glasgow.logic.action import ECAPINotFound, ECAPINotAuthorized

class CreateUsersController(toolkit.BaseController):
    def create_users(self):

        # extra_vars has to contain 'data' or the template will crash.
        # Replace data with a non-empty dict to pre-fill the form fields.
        extra_vars = {'data': {}}

        if toolkit.request.method == 'POST':
            params = dict(toolkit.request.params)
            data = params.copy()
            data.pop('Password')
            data.pop('confirm-password')
            extra_vars['data'] = data

            try:
                organization_id = params.get('OrganisationId', None)

                if organization_id:
                    organization_id = toolkit.get_action('organization_show')(
                        context={}, data_dict={'id': organization_id})['id']

                confirm = params.pop('confirm-password')
                if confirm != params['Password']:
                    raise toolkit.ValidationError({'Password': 'passwords do not match'})

                context = {'model': model, 'session': model.Session}
                data_dict = params.copy()
                data_dict['IsRegisteredUser'] = False

                request = toolkit.get_action('ec_user_create')(context, data_dict)
            except toolkit.ObjectNotFound:
                helpers.flash_error('Organization {} not found'.format(
                    organization_id))
            except ECAPINotFound, e:
                helpers.flash_error('Error CTPEC platform returned an error: {}'.format(str(e)))
            except ECAPINotAuthorized, e:
                helpers.flash_error('Error CTPEC platform returned an authorization error: {}'.format(str(e)))
            except toolkit.NotAuthorized, e:
                helpers.flash_error('Not authorized to add users')
            except toolkit.ValidationError, e:
                helpers.flash_error('Error validating fields {}'.format(str(e)))
                extra_vars['errors'] = e.error_dict
            else:
                helpers.flash_success('A request to create user {} was sent, your request id is {}'.format(params['UserName'], request['request_id']))

        user = toolkit.c.user
        extra_vars['is_sysadmin'] = new_authz.is_sysadmin(user)

        if extra_vars['is_sysadmin']:
            extra_vars['organisation_names'] = toolkit.get_action(
                'organization_list')(context={}, data_dict={})
        else:
            context = {
                'model': model,
                'session': model.Session,
                'user': toolkit.c.user,
            }
            orgs = toolkit.get_action('organization_list_for_user')(context, {})
            extra_vars['organisation_names'] = ([o['name'] for o in orgs])

        return toolkit.render('create_users/create_users.html', extra_vars=extra_vars)
