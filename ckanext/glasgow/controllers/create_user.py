import collections

import pylons

import ckan.model as model
import ckan.new_authz as new_authz
import ckan.plugins.toolkit as toolkit
import ckan.lib.helpers as helpers

from ckanext.glasgow.logic.action import ECAPINotFound, ECAPINotAuthorized


Option = collections.namedtuple('Option', ['text', 'value'])


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
                confirm = params.pop('confirm-password')
                if confirm != params['Password']:
                    raise toolkit.ValidationError({'Password': 'passwords do not match'})

                context = {'model': model, 'session': model.Session}
                data_dict = params.copy()
                data_dict['IsRegisteredUser'] = False

                request = toolkit.get_action('ec_user_create')(context, data_dict)
                extra_vars['data'] = None
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

    def change_user_role(self):
        context = {'model': model,
                   'user': toolkit.c.user, 'auth_user_obj': toolkit.c.userobj}
        try:
            toolkit.check_access('sysadmin', context, {})
        except toolkit.NotAuthorized:
            toolkit.abort(401, toolkit._('Need to be system administrator to make users super admins'))
        extra_vars = {
            'errors': {},
        }

        try:
            result = toolkit.get_action('ec_user_list')(context, {})
            users = [ Option(text=i['UserName'].lower(), value=i['UserId']) for i 
                      in result ]
        except (toolkit.ValidationError, KeyError):
            users =  toolkit.get_action('user_list')(context, {})
            users = [ Option(text=i['name'], value=i['id']) for i in users ]
        extra_vars['users'] = users
        
        if toolkit.request.method == 'POST':
            request_params = dict(toolkit.request.params)
            try:
                user = toolkit.get_action('user_show')(
                    context, {'id': request_params['user']})

                ec_user = toolkit.get_action('ec_user_show')(
                    context, {'ec_username': user['name']})
                request_params['id'] = user['id']

                request = toolkit.get_action('ec_superadmin_create')(context,
                    request_params)
            except toolkit.NotAuthorized:
                toolkit.abort(401, toolkit._('Not authorized'))
            except toolkit.ObjectNotFound, e:
                toolkit.abort(404, 'Object not found: {}'.format(str(e)))
            except toolkit.ValidationError, e:
                extra_vars['errors'] = e.error_dict
                helpers.flash_error('The platform returned an error: {}'.format(e))
        return toolkit.render('create_users/change_role.html', extra_vars=extra_vars)


    def pending_users(self):
        context = {'model': model,
                   'user': toolkit.c.user, 'auth_user_obj': toolkit.c.userobj}
        try:
            toolkit.check_access('ec_user_create', context, {})
        except toolkit.NotAuthorized:
            toolkit.abort(401, toolkit._('Need to be organization administrator to see pending users'))

        user_requests = toolkit.get_action('pending_user_tasks')(context, {})

        extra_vars = {
            'requests': user_requests
        }
        return toolkit.render('create_users/pending.html', extra_vars=extra_vars)


    def pending_user_update(self, id): 
        context = {'model': model,
                   'user': toolkit.c.user, 'auth_user_obj': toolkit.c.userobj}
        try:
            toolkit.check_access('user_update', context, {})
        except toolkit.NotAuthorized:
            toolkit.abort(401, toolkit._('Not authorized to see user updates'))

        requests = toolkit.get_action('pending_user_tasks')(context, {'id': id})
        user = toolkit.get_action('user_show')(context, {'id': id})

        toolkit.c.user_dict = user

        extra_vars = {
            'requests': requests,
            'user': user,
        }
        return toolkit.render('user/pending_update.html', extra_vars=extra_vars)
