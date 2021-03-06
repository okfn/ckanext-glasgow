import ckan.logic.auth as auth_core


def package_create(context, data_dict):

    if context.get('local_action', False):
        return {'success': False,
                'msg': 'Only sysadmins can create datasets directly into CKAN'
                }
    else:

        return dataset_request_create(context, data_dict)


def package_update(context, data_dict):
    if context.get('local_action', False):
        return {'success': False,
                'msg': 'Only sysadmins can update datasets directly into CKAN'
                }
    else:
        return dataset_request_update(context, data_dict)


def dataset_request_create(context, data_dict):

    return auth_core.create.package_create(context, data_dict)


def dataset_request_update(context, data_dict):

    return auth_core.update.package_update(context, data_dict)


def file_request_create(context, data_dict):

    # Forward auth check to the dataset level
    return dataset_request_create(context, data_dict)


def file_version_request_create(context, data_dict):

    # Forward auth check to the dataset level
    return dataset_request_create(context, data_dict)


def file_request_update(context, data_dict):

    # Forward auth check to the dataset level
    return dataset_request_update(context, data_dict)


def file_request_delete(context, data_dict):

    # Forward auth check to the dataset level
    return dataset_request_update(context, data_dict)

def organization_create(context, data_dict):
    # Only sysadmins can create orgs
    return {'success': False}

def organization_request_create(context, data_dict):
    # Only sysadmins can create orgs
    return {'success': False}

def get_change_request(context, data_dict):

    # Forward auth check to the dataset level
    return dataset_request_create(context, data_dict)


def task_status_show(context, data_dict):
    return approvals_list(context, data_dict)


def pending_task_for_dataset(context, data_dict):
    return auth_core.update.package_update(context, data_dict)


def pending_task_for_organization(context, data_dict):
    return approvals_list(context, data_dict)


def pending_user_tasks(context, data_dict):
    return approvals_list(context, data_dict)


def changelog_show(context, data_dict):
    return {'success': False,
            'msg': 'Only sysadmins can see the change log'}


def approvals_list(context, data_dict):

    # Check if the user has admin rights in some org
    from ckan import new_authz

    user_name = context.get('user')

    if user_name:
        check = new_authz.has_user_permission_for_some_org(user_name, 'admin')
        if check:
            return {'success': True}

    return {'success': False}


def approval_act(context, data_dict):
    return approvals_list(context, data_dict)


def approval_download(context, data_dict):
    return approvals_list(context, data_dict)


def ec_user_create(context, data_dict):
    return approvals_list(context, data_dict)


def ec_superadmin_create(context, data_dict):
    return {'success': False,
            'msg': 'must be a sysadmin'}
