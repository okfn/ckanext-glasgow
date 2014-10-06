import logging

import ckan.plugins as p

from ckanext.harvest.plugin import Harvest
from ckan.lib.plugins import DefaultOrganizationForm

import ckanext.glasgow.logic.schema as custom_schema
import ckanext.glasgow.model as custom_model

log = logging.getLogger(__name__)


class GlasgowSchemaPlugin(p.SingletonPlugin, p.toolkit.DefaultDatasetForm):

    p.implements(p.IRoutes, inherit=True)
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IDatasetForm, inherit=True)
    p.implements(p.IActions, inherit=True)
    p.implements(p.IAuthFunctions, inherit=True)
    p.implements(p.ITemplateHelpers, inherit=True)

    # IRoutes

    def before_map(self, map):

        controller = 'ckanext.glasgow.controllers.dataset:DatasetController'

        map.connect('add dataset', '/dataset/new', controller=controller,
                    action='new')
        map.connect('/dataset/new_resource/{id}', controller=controller,
                    action='new_resource')
        map.connect('dataset_read', '/dataset/{id}',
                    controller=controller,
                    action='read',
                    ckan_icon='sitemap'
                    )

        map.connect('/dataset/{dataset}/resource/{resource}/version/new',
                    controller=controller,
                    action='resource_version_new')

        map.connect('resource_versions_latest', '/dataset/{dataset}/resource/{resource}/version',
                    controller=controller,
                    action='resource_versions', version=None)
        map.connect('resource_versions', '/dataset/{dataset}/resource/{resource}/version/{version}',
                    controller=controller,
                    action='resource_versions')


        map.connect('/dataset/{dataset}/resource/{resource}/version/{version}/delete',
                    controller=controller,
                    action='resource_version_delete')

        map.connect('dataset_change_requests', '/dataset/change_requests/{dataset_name}',
                    controller=controller, action='dataset_change_requests')

        map.connect('approvals_list', '/approvals',
                    controller=controller, action='approvals')
        map.connect('approval_accept', '/approvals/{id}/accept',
                    controller=controller, action='approval_act', accept=True)
        map.connect('approval_reject', '/approvals/{id}/reject',
                    controller=controller, action='approval_act', accept=False)
        map.connect('approval_download', '/approvals/{id}/download',
                    controller=controller, action='approval_download')



        status_ctl = 'ckanext.glasgow.controllers.request_status:RequestStatusController'
        map.connect('/request/{request_id}', controller=status_ctl,
                    action='get_status')


        org_controller = 'ckanext.glasgow.controllers.organization:OrgController'
        map.connect('/organization/new',
                    controller=org_controller, action='new')
        map.connect('/organization/member_delete/{id}',
                    controller=org_controller, action='member_delete')
        map.connect('organization_pending_members', '/organization/pending_members/{organization_id}',
                    controller=org_controller, action='pending_member_requests_list')
        map.connect('organization_change_requests', '/organization/change_requests/{organization_name}',
                    controller=org_controller, action='organization_change_requests')
        map.connect('/organization/{organization_id}',
                    controller=org_controller, action='read')

        map.connect('create_platform_users', '/create_users',
                    controller='ckanext.glasgow.controllers.create_user:CreateUsersController',
                    action='create_users')
        map.connect('change_user_role', '/change_user_role',
                    controller='ckanext.glasgow.controllers.create_user:CreateUsersController',
                    action='change_user_role')
        map.connect('pending_user_requests', '/pending_user_requests',
                    controller='ckanext.glasgow.controllers.create_user:CreateUsersController',
                    action='pending_users')
        map.connect('pending_user_update', '/user/pending_updates/{id}',
                    controller='ckanext.glasgow.controllers.create_user:CreateUsersController',
                    action='pending_user_update')
        return map

    # IConfigurer

    def update_config(self, config):

        # Check that we are running the correct CKAN version
        p.toolkit.requires_ckan_version('2.2')

        # Register the public folder
        p.toolkit.add_public_directory(config, 'theme/public')

        # Register the extension template dir
        p.toolkit.add_template_directory(config, 'theme/templates')

        # Create the extension DB tables if not there
        custom_model.setup()

    # IDatasetForm

    def package_types(self):
        return ['dataset']

    def is_fallback(self):
        return True

    def create_package_schema(self):
        return custom_schema.create_package_schema()

    def update_package_schema(self):
        return custom_schema.update_package_schema()

    def show_package_schema(self):
        return custom_schema.show_package_schema()

    # IActions

    def get_actions(self):
        import ckanext.glasgow.logic.action as custom_actions

        function_names = (
            'package_create',
            'package_update',
            'resource_create',
            'resource_update',
            'resource_delete',
            'organization_create',
            'organization_update',
            'organization_request_create',
            'organization_request_update',
            'organization_member_create',
            'organization_member_delete',
            'organization_list_for_user',
            'user_role_update',
            'user_role_delete',
            'user_list',
            'user_update',
            'ec_user_show',
            'ec_user_list',
            'ec_user_create',
            'ec_superadmin_create',
            'ec_organization_list',
            'dataset_request_create',
            'file_request_create',
            'file_request_update',
            'file_request_delete',
            'file_version_request_create',
            'dataset_request_update',
            'pending_task_for_dataset',
            'pending_files_for_dataset',
            'pending_task_for_organization',
            'pending_tasks_for_membership',
            'pending_user_tasks',
            'resource_versions_show',
            'check_for_task_status_update',
            'get_change_request',
            'changelog_show',
            'approvals_list',
            'approval_act',
            'approval_download',
        )
        return _get_module_functions(custom_actions, function_names)

    # IAuthFunctions

    def get_auth_functions(self):
        import ckanext.glasgow.logic.auth as custom_auth

        function_names = (
            'package_create',
            'package_update',
            'dataset_request_create',
            'file_request_create',
            'file_request_update',
            'file_request_delete',
            'file_version_request_create',
            'dataset_request_update',
            'pending_task_for_dataset',
            'pending_task_for_organization',
            'pending_user_tasks',
            'organization_create',
            'organization_request_create',
            'task_status_show',
            'get_change_request',
            'changelog_show',
            'approvals_list',
            'approval_act',
            'approval_download',
            'ec_user_create',
            'ec_superadmin_create',
        )
        return _get_module_functions(custom_auth, function_names)

    # ITemplateHelpers

    def get_helpers(self):
        import ckanext.glasgow.helpers as custom_helpers

        function_names = (
            'get_licenses',
            'get_resource_versions',
            'get_pending_files_for_dataset',
            'get_pending_task_for_dataset',
            'get_datetime_from_ec_iso',
            'parse_metadata_string',
            'get_resource_ec_extra_fields',
            'get_ec_api_metadata_link',
            'show_int_value',
        )
        return _get_module_functions(custom_helpers, function_names)


def _get_module_functions(module, function_names):
    functions = {}
    for f in function_names:
        functions[f] = module.__dict__[f]

    return functions


class CustomHarvestPlugin(Harvest):
    '''
    We override the default harvest plugin to tweak the schema used when
    creating harvest sources. We basically don't need sources to belong to
    an org, but the rest of datasets should follow the owner_org validation.
    '''

    def create_package_schema(self):

        schema = super(CustomHarvestPlugin, self).create_package_schema()

        schema['owner_org'] = [p.toolkit.get_validator('ignore_missing'),
                               p.toolkit.get_validator('ignore_empty'),
                               p.toolkit.get_validator('owner_org_validator'),
                               unicode]

        return schema

    def update_package_schema(self):

        schema = super(CustomHarvestPlugin, self).update_package_schema()

        schema['owner_org'] = [p.toolkit.get_validator('ignore_missing'),
                               p.toolkit.get_validator('ignore_empty'),
                               p.toolkit.get_validator('owner_org_validator'),
                               unicode]

        return schema


class GlasgowOrganizationPlugin(p.SingletonPlugin, DefaultOrganizationForm):
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IGroupForm, inherit=True)

    def group_types(self):
        return ['organization']

    def form_to_db_schema(self):
        return custom_schema.update_organization_schema()

    def db_to_form_schema(self):
        return custom_schema.show_group_schema()
