import os
import cgi
import logging
import json
import datetime
import uuid
import re
import urlparse

import dateutil.parser
import requests
from sqlalchemy import or_, and_, desc, case, func
from sqlalchemy.sql import select

from pylons import config, session

import ckan.model as model
from ckan import new_authz
import ckan.plugins as p
from ckan.lib.navl.dictization_functions import validate
import ckan.lib.dictization.model_dictize as model_dictize
from ckan.lib import helpers
import ckan.logic.action as core_actions
from ckan.logic import ActionError
import ckan.logic.schema as core_schema

import ckanext.oauth2waad.plugin as oauth2


import ckanext.glasgow.logic.schema as custom_schema


log = logging.getLogger(__name__)
requests.packages.urllib3.add_stderr_logger()

get_action = p.toolkit.get_action
check_access = p.toolkit.check_access


class ECAPIError(p.toolkit.ValidationError):
    # ActionErrors aren't actually handled by the api controller,
    # so you will receive a standard 500 if this inherited from ActionError
    pass


class ECAPINotAuthorized(p.toolkit.NotAuthorized):
    pass


class ECAPINotFound(p.toolkit.ObjectNotFound):
    pass


class ECAPIValidationError(p.toolkit.ValidationError):
    pass


def _make_uuid():
    return unicode(uuid.uuid4())


def _get_api_auth_token():
    '''
    Use the auth_token obtained when logging in with the WAAD credentials

    This is stored in the Pylons session
    TODO: refresh it when expired

    :returns: an auth_token value ready to be used in an `Authorization`
              header (ie following the Bearer scheme)
    :rtype: string

    '''

    token = ''

    try:
        token = session.get('ckanext-oauth2waad-access-token')

    except TypeError:
        # No session (eg tests or command line)
        pass

        # Allow token to be set from an env var. Useful for the tests.
        token = os.environ.get('__CKANEXT_GLASGOW_AUTH_HEADER', '')

    if token and not token.startswith('Bearer '):
        token = 'Bearer ' + token

    return token


def _get_api_endpoint(operation):
    '''
    Returns the relevant EC API endpoint for a particular operation

    Uses the 'ckanext.glasgow.ec_api' configuration option as a base.
    This function can be expanded in the future to support different APIs
    and extra endpoints

    :param operation: the operation we need to know the endpoint for
                      (eg 'dataset_request_create')
    :type operation: string

    :returns: a tuple, the first member being the HTTP method, and the
              second the URL.
    :rtype: tuple
    '''

    write_base = config.get('ckanext.glasgow.data_collection_api', '').rstrip('/')
    read_base = config.get('ckanext.glasgow.metadata_api', '').rstrip('/')
    identity_base = config.get('ckanext.glasgow.identity_api', '').rstrip('/')

    operations = {
        'dataset_show': (
            'GET',
            '/Metadata/Organisation/{organization_id}/Dataset/{dataset_id}',
            read_base),
        'dataset_request_create': (
            'POST',
            '/Datasets/Organisation/{organization_id}',
            write_base),
        'dataset_request_update': (
            'PUT',
            '/Datasets/Organisation/{organization_id}/Dataset/{dataset_id}',
            write_base),
        'file_show': (
            'GET',
            '/Metadata/Organisation/{organization_id}/Dataset/{dataset_id}/File/{file_id}',
            read_base),
        'file_request_create': (
            'POST',
            '/Files/Organisation/{organization_id}/Dataset/{dataset_id}',
            write_base),
        'file_request_update': (
            'POST',
            '/Files/Organisation/{organization_id}/Dataset/{dataset_id}/File/{file_id}',
            write_base),
        'file_version_request_create': (
            'POST',
            '/Files/Organisation/{organization_id}/Dataset/{dataset_id}/File/{file_id}',
            write_base),
        'file_version_request_update': (
            'PUT',
            '/Files/Organisation/{organization_id}/Dataset/{dataset_id}/File/{file_id}/Version/{version_id}',
            write_base),
        'file_version_request_delete': (
            'DELETE',
            '/Files/Organisation/{organization_id}/Dataset/{dataset_id}/File/{file_id}/Version/{version_id}',
            write_base),
        'file_version_show': (
            'GET',
            '/Metadata/Organisation/{organization_id}/Dataset/{dataset_id}/File/{file_id}/Version/{version_id}',
            read_base),
        'file_versions_show': (
            'GET',
            '/Metadata/Organisation/{organization_id}/Dataset/{dataset_id}/File/{file_id}/Versions',
            read_base),
        'organization_list': (
            'GET',
            '/Metadata/Organisation',
            read_base),
        'organization_show': (
            'GET',
            '/Metadata/Organisation/{organization_id}',
            read_base),
        'organization_request_create': (
            'POST',
            '/Organisations',
            write_base),
        'organization_request_update': (
            'PUT',
            '/Organisations/Organisation/{organization_id}',
            write_base),
        'request_status_show': (
            'GET',
            '/ChangeLog/RequestStatus/{request_id}',
            read_base),
        'changelog_show': (
            'GET',
            '/ChangeLog/RequestChanges',
            read_base),
        'approvals_list': (
            'GET',
            '/Approval',
            write_base),
        'approval_accept': (
            'POST',
            '/Approval/{request_id}/Accept',
            write_base),
        'approval_reject': (
            'POST',
            '/Approval/{request_id}/Reject',
            write_base),
        'approval_download': (
            'GET',
            '/Approval/{request_id}/Download',
            write_base),

        'user_role_update': (
            'PUT',
            '/UserRoles/User/{user_id}',
            write_base),
        'user_org_role_update': (
            'PUT',
            '/UserRoles/Organisation/{organization_id}/User/{user_id}',
            write_base),

        'user_show': (
            'GET',
            '/Identity/User/{username}',
            identity_base),
        'user_list': (
            'GET',
            '/Identity/User',
            identity_base),
        'user_list_for_organization': (
            'GET',
            '/Identity/Organisation/{organization_id}/User',
            identity_base),
        'user_request_create': (
            'POST',
            '/Users',
            write_base),
        'user_request_update': (
            'PUT',
            '/Users/User/{user_id}',
            write_base),
        'user_request_update_in_org': (
            'PUT',
            '/Users/Organisation/{organization_id}/User/{user_id}',
            write_base),
        'user_in_organization_request_create': (
            'POST',
            '/Users/Organisation/{organization_id}',
            write_base),
    }

    try:
        method, path, url = operations[operation]
        return method, urlparse.urljoin(url, path)
    except KeyError:
        return None, None


def _get_ec_api_org_id(ckan_org_id):
    # Get EC API id from parent organization

    try:
        org_dict = p.toolkit.get_action('organization_show')({}, {
            'id': ckan_org_id})

        return org_dict['id']
    except p.toolkit.ObjectNotFound:
        return False


@p.toolkit.side_effect_free
def pending_task_for_dataset(context, data_dict):
    '''
    Returns the most recent pending request for a particular dataset

    Returns the most recent TaskStatus with a state of 'new' or 'sent'.
    Datasets can be identified by id or name.

    :param id: Dataset id (optional if name provided)
    :type operation: string
    :param name: Dataset name (optional if id provided)
    :type operation: string

    :returns: a task status dict if found, None otherwise.
    :rtype: dict
    '''

    p.toolkit.check_access('pending_task_for_dataset', context, data_dict)

    id = data_dict.get('id') or data_dict.get('name')

    model = context.get('model')
    task = model.Session.query(model.TaskStatus) \
        .filter(model.TaskStatus.entity_type == 'dataset') \
        .filter(or_(model.TaskStatus.state == 'new',
                model.TaskStatus.state == 'sent')) \
        .filter(or_(
                model.TaskStatus.key == id,
                model.TaskStatus.entity_id == id,
                )) \
        .order_by(model.TaskStatus.last_updated.desc()) \
        .first()

    if task:
        return model_dictize.task_status_dictize(task, context)
    else:
        return None


def pending_files_for_dataset(context, data_dict):
    '''
    Returns list of pending file tasks for a dataset

    Returns the most recent TaskStatus with a state of 'new' or 'sent'.
    Datasets can be identified by id or name.

    :param id: Dataset id (optional if name provided)
    :type operation: string

    :returns: a task status dict if found, None otherwise.
    :rtype: dict
    '''

    p.toolkit.check_access('pending_task_for_dataset', context, data_dict)

    id = data_dict.get('id')
    name = data_dict.get('name')
    try:
        dataset_dict = p.toolkit.get_action('package_show')(context,
            {'name_or_id': id or name})
    except p.toolkit.NotFound:
        raise p.toolkit.ValidationError(['Dataset not found'])

    model = context.get('model')
    tasks = model.Session.query(model.TaskStatus) \
        .filter(model.TaskStatus.entity_type == 'file') \
        .filter(or_(model.TaskStatus.state == 'new',
                model.TaskStatus.state == 'sent')) \
        .filter(or_(model.TaskStatus.key.like('{0}%'.format(dataset_dict['id'])),
                model.TaskStatus.key.like('{0}%'.format(dataset_dict['name'])))) \
        .order_by(model.TaskStatus.last_updated.desc())

    results = []
    for task in tasks:
        task_dict = model_dictize.task_status_dictize(task, context)
        results.append(task_dict)
    return results


def pending_task_for_organization(context, data_dict):
    p.toolkit.check_access('pending_task_for_organization', context, data_dict)

    organization_id = data_dict.get('organization_id')
    p.toolkit.check_access('organization_update', context, {'id': organization_id})
    name = data_dict.get('name')

    model = context.get('model')
    task = model.Session.query(model.TaskStatus) \
        .filter(model.TaskStatus.entity_type == 'organization') \
        .filter(or_(model.TaskStatus.state == 'new',
                model.TaskStatus.state == 'sent')) \
        .filter(or_(model.TaskStatus.entity_id == organization_id,
                model.TaskStatus.entity_id == name)) \
        .order_by(model.TaskStatus.last_updated.desc()) \
        .first()

    if task:
        return model_dictize.task_status_dictize(task, context)
    else:
        return None


def pending_tasks_for_membership(context, data_dict):
    p.toolkit.check_access('pending_task_for_organization', context, data_dict)

    organization_id = data_dict.get('organization_id')
    p.toolkit.check_access('organization_update', context, {'id': organization_id})
    name = data_dict.get('name')

    model = context.get('model')
    tasks = model.Session.query(model.TaskStatus) \
        .filter(model.TaskStatus.entity_type == 'member') \
        .filter(or_(model.TaskStatus.state == 'new',
                model.TaskStatus.state == 'sent')) \
        .filter(or_(model.TaskStatus.entity_id == organization_id,
                model.TaskStatus.entity_id == name)) \
        .filter(model.TaskStatus.task_type == 'member_update') \
        .order_by(model.TaskStatus.last_updated.desc()) \

    task_dicts = []
    for task in tasks:
        context = {'model': model, 'session': model.Session}
        task_dict = model_dictize.task_status_dictize(task, context)
        task_dict['value'] = json.loads(task_dict['value'])
        task_dicts.append(task_dict)
    return task_dicts


@p.toolkit.side_effect_free
def pending_user_tasks(context, data_dict):
    p.toolkit.check_access('pending_user_tasks', context, data_dict)

    user_id = data_dict.get('id') or data_dict.get('name')

    model = context.get('model')
    tasks = model.Session.query(model.TaskStatus) \
        .filter(model.TaskStatus.entity_type == 'user') \
        .filter(or_(model.TaskStatus.state == 'new',
                model.TaskStatus.state == 'sent',
                model.TaskStatus.state == 'error')
                )
    if user_id:
        tasks = tasks.filter(or_(
                #model.TaskStatus.key == user_id,
                model.TaskStatus.entity_id == user_id,
                ))
    tasks = tasks.order_by(model.TaskStatus.last_updated.desc())

    results = []
    for task in tasks:
        task_dict = model_dictize.task_status_dictize(task, context)
        task_dict['value'] = json.loads(task_dict['value'])
        results.append(task_dict)
    return results


def package_create(context, data_dict):

    if data_dict.get('__local_action', False):
        context['local_action'] = True
        data_dict.pop('__local_action', None)

    if (context.get('local_action', False) or
            data_dict.get('type') == 'harvest'):

        return core_actions.create.package_create(context, data_dict)

    else:

        return p.toolkit.get_action('dataset_request_create')(context,
                                                              data_dict)


def dataset_request_create(context, data_dict):
    '''
    Requests the creation of a dataset to the EC Data Collection API

    This function accepts the same parameters as the default
    `package_create` and will run the same validation, but instead of
    creating the dataset in CKAN will store the submitted data in the
    `task_status` table and forward it to the Data Collection API.

    :raises: :py:exc:`~ckan.plugins.toolkit.ValidationError` if the
        validation of the submitted data didn't pass, or the EC API returned
        an error. In this case, the exception will contain the following:
        {
            'status': status_code, # HTTP status code returned by the EC API
            'content': response # JSON response returned by the EC API
        }

    :raises: :py:exc:`~ckan.plugins.toolkit.NotAuthorized` if the
        user is not authorized to perform the operaion, or the EC API returned
        an authorization error. In this case, the exception will contain the
        following:
        {
            'status': status_code, # HTTP status code returned by the EC API
            'content': response # JSON response returned by the EC API
        }


    :returns: a dictionary with the CKAN `task_id` and the EC API `request_id`
    :rtype: dictionary

    '''

    # TODO: refactor to reuse code across updates and file creation/udpate

    # Check access

    check_access('dataset_request_create', context, data_dict)

    # Validate data_dict

    context.update({'model': model, 'session': model.Session})
    create_schema = custom_schema.create_package_schema()

    validated_data_dict, errors = validate(data_dict, create_schema, context)

    if errors:
        raise p.toolkit.ValidationError(errors)

    # Get parent org EC API id
    ec_api_org_id = _get_ec_api_org_id(validated_data_dict['owner_org'])

    if not ec_api_org_id:
        raise p.toolkit.ValidationError(
            ['Could not get EC API id for parent organization'])

    # Create a task status entry with the validated data

    task_dict = _create_task_status(context,
                                    task_type='dataset_request_create',
                                    # This will be used as dataset id
                                    entity_id=_make_uuid(),
                                    entity_type='dataset',
                                    # This will be used for validating datasets
                                    key=validated_data_dict['name'],
                                    value=json.dumps(
                                        {'data_dict': data_dict})
                                    )

    # Convert payload from CKAN to EC API spec

    ec_dict = custom_schema.convert_ckan_dataset_to_ec_dataset(
        validated_data_dict)

    # Send request to EC Data Collection API

    method, url = _get_api_endpoint('dataset_request_create')

    url = url.format(
        organization_id=ec_api_org_id
    )

    headers = {
        'Authorization': _get_api_auth_token(),
        'Content-Type': 'application/json',
    }

    content = send_request_to_ec_platform(method, url,
                                          data=json.dumps(ec_dict),
                                          headers=headers,
                                          context=context,
                                          task_dict=task_dict)

    # Store data in task status table

    request_id = content.get('RequestId')
    task_dict = _update_task_status_success(context, task_dict, {
        'data_dict': data_dict,
        'request_id': request_id,
    })

    # Return task id to access it later and the request id returned by the
    # EC Metadata API

    return {
        'task_id': task_dict['id'],
        'request_id': request_id,
        # This is required by the core controller to do the redirect
        'name': validated_data_dict['name'],
    }


def resource_create(context, data_dict):

    if data_dict.get('__local_action', False):
        context['local_action'] = True
        data_dict.pop('__local_action', None)
    if context.get('local_action', False):

        return core_actions.create.resource_create(context, data_dict)

    else:

        return p.toolkit.get_action('file_request_create')(context,
                                                           data_dict)


def file_request_create(context, data_dict):
    '''
    Requests the creation of a dataset to the EC Data Collection API

    This function accepts the same parameters as the default
    `package_create` and will run the same validation, but instead of
    creating the dataset in CKAN will store the submitted data in the
    `task_status` table and forward it to the Data Collection API.

    :raises: :py:exc:`~ckan.plugins.toolkit.ValidationError` if the
        validation of the submitted data didn't pass, or the EC API returned
        an error. In this case, the exception will contain the following:
        {
            'status': status_code, # HTTP status code returned by the EC API
            'content': response # JSON response returned by the EC API
        }

    :raises: :py:exc:`~ckan.plugins.toolkit.NotAuthorized` if the
        user is not authorized to perform the operaion, or the EC API returned
        an authorization error. In this case, the exception will contain the
        following:
        {
            'status': status_code, # HTTP status code returned by the EC API
            'content': response # JSON response returned by the EC API
        }


    :returns: a dictionary with the CKAN `task_id` and the EC API `request_id`
    :rtype: dictionary

    '''

    # TODO: refactor to reuse code across updates and file creation/udpate

    # Check if parent dataset exists

    if data_dict.get('dataset_id'):
        data_dict['package_id'] = data_dict['dataset_id']
    package_id = p.toolkit.get_or_bust(data_dict, 'package_id')

    try:
        dataset_dict = p.toolkit.get_action('package_show')(context,
                                                            {'id': package_id})
    except p.toolkit.ObjectNotFound:
        raise p.toolkit.ObjectNotFound('Dataset not found')

    # Check access

    check_access('file_request_create', context, data_dict)

    # Validate data_dict

    context.update({'model': model, 'session': model.Session})
    create_schema = custom_schema.resource_schema()

    # We need the actual dataset id, not the name
    data_dict['package_id'] = dataset_dict['id']

    validated_data_dict, errors = validate(data_dict, create_schema, context)

    if errors:
        raise p.toolkit.ValidationError(errors)

    # Create a task status entry with the validated data

    key = '{0}@{1}'.format(validated_data_dict.get('package_id', 'file'),
                           datetime.datetime.now().isoformat())
    uploaded_file = data_dict.pop('upload', None)
    task_dict = _create_task_status(context,
                                    task_type='file_request_create',
                                    entity_id=_make_uuid(),
                                    entity_type='file',
                                    key=key,
                                    value=json.dumps(
                                        {'data_dict': data_dict})
                                    )

    # Convert payload from CKAN to EC API spec

    ec_dict = custom_schema.convert_ckan_resource_to_ec_file(
        validated_data_dict)

    # Send request to EC Data Collection API

    method, url = _get_api_endpoint('file_request_create')
    url = url.format(
        organization_id=dataset_dict['owner_org'],
        dataset_id=validated_data_dict['package_id'],
    )

    headers = {
        'Authorization': _get_api_auth_token(),
    }

    if isinstance(uploaded_file, cgi.FieldStorage):
        files = {
            'file': (uploaded_file.filename,
                     uploaded_file.file)
        }
        data = {
            'metadata': json.dumps(ec_dict)
        }
    else:
        headers['Content-Type'] = 'application/json'
        files = None

        # Use ExternalUrl instead of FileExternalUrl
        ec_dict['ExternalUrl'] = ec_dict.pop('FileExternalUrl', None)

        data = json.dumps(ec_dict)

    content = send_request_to_ec_platform(method, url,
                                          data=data,
                                          headers=headers,
                                          files=files,
                                          context=context,
                                          task_dict=task_dict)

    # Store data in task status table

    request_id = content.get('RequestId')

    task_dict = _update_task_status_success(context, task_dict, {
        'data_dict': data_dict,
        'request_id': request_id,
    })

    # Return task id to access it later and the request id returned by the
    # EC Metadata API

    return {
        'task_id': task_dict['id'],
        'request_id': request_id,
        'name': None,
    }


def _create_task_status(context, task_type, entity_id, entity_type, key,
                        value):

    context.update({'ignore_auth': True})

    if not isinstance(value, basestring):
        value = json.dumps(value)

    task_dict = {
        'task_type': task_type,
        'entity_id': entity_id,
        'entity_type': entity_type,
        'key': key,
        'value': value,
        'state': 'new',
        'last_updated': datetime.datetime.now(),
    }
    task_dict = get_action('task_status_update')(context, task_dict)

    return task_dict


def resource_update(context, data_dict):

    if data_dict.get('__local_action', False):
        context['local_action'] = True
        data_dict.pop('__local_action', None)
    if context.get('local_action', False):

        return core_actions.update.resource_update(context, data_dict)

    else:

        return p.toolkit.get_action('file_request_update')(context,
                                                           data_dict)


def _update_task_status_success(context, task_dict, value):

    context.update({'ignore_auth': True})

    if not isinstance(value, basestring):
        value = json.dumps(value)

    task_dict['state'] = 'sent'
    task_dict['value'] = value
    task_dict['last_updated'] = datetime.datetime.now()

    task_dict = get_action('task_status_update')(context, task_dict)

    _expire_task_status(context, task_dict['id'])

    return task_dict


def file_request_update(context, data_dict):
    '''
    Requests the update of a file to the EC Data Collection API

    This function accepts the same parameters as the default
    `package_create` and will run the same validation, but instead of
    creating the dataset in CKAN will store the submitted data in the
    `task_status` table and forward it to the Data Collection API.

    :raises: :py:exc:`~ckan.plugins.toolkit.ValidationError` if the
        validation of the submitted data didn't pass, or the EC API returned
        an error. In this case, the exception will contain the following:
        {
            'status': status_code, # HTTP status code returned by the EC API
            'content': response # JSON response returned by the EC API
        }

    :raises: :py:exc:`~ckan.plugins.toolkit.NotAuthorized` if the
        user is not authorized to perform the operaion, or the EC API returned
        an authorization error. In this case, the exception will contain the
        following:
        {
            'status': status_code, # HTTP status code returned by the EC API
            'content': response # JSON response returned by the EC API
        }


    :returns: a dictionary with the CKAN `task_id` and the EC API `request_id`
    :rtype: dictionary

    '''

    # TODO: refactor to reuse code across updates and file creation/udpate

    # Check if parent dataset exists

    if data_dict.get('dataset_id'):
        data_dict['package_id'] = data_dict['dataset_id']
    package_id = p.toolkit.get_or_bust(data_dict, 'package_id')

    try:
        dataset_dict = p.toolkit.get_action('package_show')(context,
                                                            {'id': package_id})
        # We need to get the version id from the existing resource
        version_id = None
        for resource in dataset_dict.get('resources', []):
            if resource['id'] == data_dict['id']:
                version_id = resource.get('ec_api_version_id')
        if not version_id:
            raise p.toolkit.ObjectNotFound('No version id found for resource')
    except p.toolkit.ObjectNotFound:
        raise p.toolkit.ObjectNotFound('Dataset not found')

    # Check access

    check_access('file_request_update', context, data_dict)

    # We need the actual dataset id, not the name
    data_dict['package_id'] = dataset_dict['id']

    # Validate data_dict

    context.update({'model': model, 'session': model.Session})
    create_schema = custom_schema.resource_schema()

    validated_data_dict, errors = validate(data_dict, create_schema, context)
    if errors:
        for error in errors.get('extras', []):
            if error:
                errors.update(error)
        errors.pop('extras', None)

        raise p.toolkit.ValidationError(errors)

    # Convert payload from CKAN to EC API spec

    ec_dict = custom_schema.convert_ckan_resource_to_ec_file(
        validated_data_dict)

    # Store data in task status table
    # Create a task status entry with the validated data
    key = '{0}@{1}'.format(validated_data_dict.get('package_id', 'file'),
                           datetime.datetime.now().isoformat())

    uploaded_file = data_dict.pop('upload', None)
    task_dict = _create_task_status(context,
                                    task_type='file_request_update',
                                    entity_id=validated_data_dict['package_id'],
                                    entity_type='file',
                                    key=key,
                                    value=json.dumps(
                                        {'data_dict': data_dict})
                                    )

    # Send request to EC Data Collection API

    method, url = _get_api_endpoint('file_version_request_update')
    url = url.format(
        organization_id=dataset_dict['owner_org'],
        dataset_id=validated_data_dict['package_id'],
        file_id=validated_data_dict['id'],
        version_id=version_id,
    )

    headers = {
        'Authorization': _get_api_auth_token(),
    }

    if isinstance(uploaded_file, cgi.FieldStorage):
        files = {
            'file': (uploaded_file.filename,
                     uploaded_file.file)
        }
        data = {
            'metadata': json.dumps(ec_dict)
        }
    else:
        headers['Content-Type'] = 'application/json'
        files = None

        # Check if the URL provided is actually the same file (using
        # the platform download URL)

        if (ec_dict['FileExternalUrl'].startswith('{0}/Download'.format(
                config.get('ckanext.glasgow.metadata_api', '').rstrip('/')))
             and validated_data_dict['id'] in ec_dict['FileExternalUrl']):
            ec_dict.pop('FileExternalUrl', None)

        data = json.dumps(ec_dict)
    content = send_request_to_ec_platform(method, url, data, headers,
                                          files=files,
                                          context=context,
                                          task_dict=task_dict)

    try:
        request_id = content['RequestId']
    except KeyError:
        error_dict = {
            'message': ['RequestId not in response from EC Platform'],
            'content': [json.dumps(content)],
        }
        raise p.toolkit.ValidationError(error_dict)


    request_id = content.get('RequestId')
    task_dict = _update_task_status_success(context, task_dict, {
        'data_dict': data_dict,
        'request_id': request_id,
    })

    # Return task id to access it later and the request id returned by the
    # EC Metadata API

    return {
        'task_id': task_dict['id'],
        'request_id': request_id,
        'name': None,
    }


def _update_task_status_error(context, task_dict, value):

    context.update({'ignore_auth': True})

    if not isinstance(value, basestring):
        value = json.dumps(value)

    task_dict['state'] = 'error'
    task_dict['value'] = value
    task_dict['last_updated'] = datetime.datetime.now()

    task_dict = get_action('task_status_update')(context, task_dict)

    _expire_task_status(context, task_dict['id'])

    return task_dict


def _expire_task_status(context, task_id):
    '''Expires a TaskStatus object from the current Session

    TaskStatus are generally updated twice in the same Session (first in
    `_create_task_status` and then in either `_update_task_status_error`
    or `_update_task_status_succes`. If we want functions calling the
    `dataset_request_create` action to access the latest version, we need to
    expire the object currently held in the Session.
    '''
    if not context.get('model'):
        return

    model = context['model']

    task = model.Session.query(model.TaskStatus).get(task_id)
    if task:
        model.Session.expire(task)


def package_update(context, data_dict):

    if data_dict.get('__local_action', False):
        context['local_action'] = True
        data_dict.pop('__local_action', None)

    if (context.get('local_action', False) or
            data_dict.get('type') == 'harvest' or
            data_dict.get('source_type')):

        return core_actions.update.package_update(context, data_dict)

    else:

        return p.toolkit.get_action('dataset_request_update')(context,
                                                              data_dict)


def dataset_request_update(context, data_dict):
    '''
    Requests the update of a dataset to the EC Data Collection API

    This function accepts the same parameters as the default
    `package_update` and will run the same validation, but instead of
    creating the dataset in CKAN will store the submitted data in the
    `task_status` table and forward it to the Data Collection API.

    :raises: :py:exc:`~ckan.plugins.toolkit.ValidationError` if the
        validation of the submitted data didn't pass, or the EC API returned
        an error. In this case, the exception will contain the following:
        {
            'status': status_code, # HTTP status code returned by the EC API
            'content': response # JSON response returned by the EC API
        }

    :raises: :py:exc:`~ckan.plugins.toolkit.NotAuthorized` if the
        user is not authorized to perform the operaion, or the EC API returned
        an authorization error. In this case, the exception will contain the
        following:
        {
            'status': status_code, # HTTP status code returned by the EC API
            'content': response # JSON response returned by the EC API
        }


    :returns: a dictionary with the CKAN `task_id` and the EC API `request_id`
    :rtype: dictionary

    '''

    # TODO: refactor to reuse code across updates and file creation/udpate

    # Check access

    check_access('dataset_request_update', context, data_dict)

    try:
        dataset_dict = p.toolkit.get_action('package_show')(context,
                                                            {'id': data_dict.get('id')})
    except p.toolkit.objectnotfound:
        raise p.toolkit.objectnotfound('dataset not found')

    # We want the actual id, not the name
    data_dict['id'] = dataset_dict['id']

    # Validate data_dict

    context.update({'model': model, 'session': model.Session})
    create_schema = custom_schema.update_package_schema()

    validated_data_dict, errors = validate(data_dict, create_schema, context)

    if errors:
        raise p.toolkit.ValidationError(errors)


    # Convert payload from CKAN to EC API spec

    ec_dict = custom_schema.convert_ckan_dataset_to_ec_dataset(
        validated_data_dict)

    # Create a task status entry with the validated data
    # and store data in task status table

    key = '{0}@{1}'.format(validated_data_dict.get('name', data_dict['id']),
                           datetime.datetime.now().isoformat())

    task_dict = _create_task_status(context,
                                    task_type='dataset_request_update',
                                    # This will be used as dataset id
                                    entity_id=validated_data_dict['id'],
                                    entity_type='dataset',
                                    key=key,
                                    value=json.dumps(
                                        {'data_dict': validated_data_dict})
                                    )

    # Send request to EC Data Collection API

    method, url = _get_api_endpoint('dataset_request_update')

    url = url.format(
        organization_id=validated_data_dict['owner_org'],
        dataset_id=validated_data_dict['id'],
    )

    content = send_request_to_ec_platform(method, url,
                                          data=json.dumps(ec_dict),
                                          context=context,
                                          task_dict=task_dict)
    try:
        request_id = content['RequestId']
    except KeyError:
        error_dict = {
            'message': ['RequestId not in response from EC Platform'],
            'content': [json.dumps(content)],
        }
        raise p.toolkit.ValidationError(error_dict)

    task_dict = _update_task_status_success(context, task_dict, {
        'data_dict': validated_data_dict,
        'request_id': request_id,
    })

    # Return task id to access it later and the request id returned by the
    # EC Metadata API

    # _save_edit requires this key even though we have not actually created
    # a Package object. Model in context is horrible anyway.
    context['package'] = None

    return {
        'task_id': task_dict['id'],
        'request_id': request_id,
        # This is required by the core controller to do the redirect
        'name': validated_data_dict['name'],
    }


def resource_versions_show(context, data_dict):
    '''Show files versions as listed on EC API'''
    try:
        resource_id = data_dict['resource_id']
        package_id = data_dict['package_id']
        #version_id = data_dict['version_id']
    except KeyError, e:
        raise p.toolkit.ValidationError(['No {0} provided'.format(e.msg)])

    resource = p.toolkit.get_action('resource_show')(context,
                                                     {'id': resource_id})
    package_show = p.toolkit.get_action('package_show')
    dataset = package_show(context, {'name_or_id': package_id})

    organisation = p.toolkit.get_action('organization_show')(
        context, {'id': dataset['owner_org']})

    method, url = _get_api_endpoint('file_versions_show')

    url = url.format(
        organization_id=organisation['id'],
        dataset_id=package_id,
        file_id=resource_id,
    )

    content = send_request_to_ec_platform(method, url, authorize=False)

    res_ec_to_ckan = custom_schema.convert_ec_file_to_ckan_resource
    try:
        metadata = content['MetadataResultSet']
    except IndexError:
        return []

    versions = []
    if metadata:
        for version in metadata:
            ckan_resource = res_ec_to_ckan(version['FileMetadata'])
            ckan_resource['version'] = version['Version']
            versions.append(ckan_resource)
    return versions


def check_for_task_status_update(context, data_dict):
    '''Checks the EC Platform for updates and updates the TaskStatus'''
    # TODO check access
    try:
        task_id = data_dict['task_id']
    except KeyError:
        raise p.toolkit.ValidationError(['No task_id provided'])

    task_status = p.toolkit.get_action('task_status_show')(context,
        {'id': task_id})

    try:
        request_dict = json.loads(task_status.get('value', ''))
        method, url = _get_api_endpoint('request_status_show')
        url = url.format(request_id=request_dict['request_id'])
    except ValueError:
        raise p.toolkit.ValidationError(
            ['task_status value is not valid JSON'])
    except KeyError:
        raise p.toolkit.ValidationError(['no request_id in task_status value'])

    headers = {
        'Authorization': _get_api_auth_token(),
        'Content-Type': 'application/json',
    }

    verify_ssl = p.toolkit.asbool(
        config.get('ckanext.glasgow.verify_ssl_certs', True)
    )
    response = requests.request(method, url, headers=headers,
                                verify=verify_ssl)
    if response.status_code == requests.codes.ok:
        try:
            result = response.json()
        except ValueError:
            raise ECAPIValidationError(['EC API Error: response not JSON'])

        latest = result['Operations'][-1]
        latest_timestamp = dateutil.parser.parse(latest['Timestamp'],
                                                 yearfirst=True)

        task_status_timestamp = dateutil.parser.parse(
            task_status['last_updated'])


        if latest_timestamp > task_status_timestamp:
            if latest['OperationState'] == 'InProgress':

               task_status['state'] = 'in_progress'
               request_dict['ec_api_message'] = latest['Message']

            elif latest['OperationState'] == 'Failed':

               task_status['state'] = 'error'
               task_status['error'] = latest['Message']


            elif latest['OperationState'] == 'Succeeded':
                task_status['state'] = 'succeeded'
                request_dict['ec_api_message'] = latest['Message']

                # call dataset_create/user_create/etc
                try:
                    on_task_status_success(context, task_status)
                except NoSuchTaskType, e:
                    task_status['state'] = 'error'
                    # todo: fix abuse of task_status.value
                    request_dict['ec_api_message'] = e.message

            task_status.update({
                'value': json.dumps(request_dict),
                'last_updated': latest['Timestamp'],
            })

            return  p.toolkit.get_action('task_status_update')(context,
                                                               task_status)
    else:
        raise ECAPIError(['EC API returned an error: {0} - {1}'.format(
            response.status_code, url)])


class NoSuchTaskType(Exception):
    pass


def on_task_status_success(context, task_status_dict):
    def on_dataset_request_create():
        request_dict = json.loads(task_status_dict['value'])
        ckan_data_dict = request_dict['data_dict']

        # TODO: the package should be owned by the user that created the
        #       request
        site_user = p.toolkit.get_action('get_site_user')(context, {})
        pkg_create_context = {
            'local_action': True,
            'user': site_user['name'],
            'model': model,
            'session': model.Session,
            'schema': custom_schema.ec_create_package_schema()
        }

        #todo update extras from successs

        #todo error handling
        p.toolkit.get_action('package_create')(pkg_create_context,
                                           ckan_data_dict)

    functions = {
        'dataset_request_create': on_dataset_request_create,
    }

    task_type = task_status_dict['task_type']
    try:
        functions[task_type]()
    except KeyError:
        raise NoSuchTaskType('no such task type {0}'.format(task_type))


@p.toolkit.side_effect_free
def get_change_request(context, data_dict):
    p.toolkit.check_access('get_change_request', context, data_dict)
    try:
        request_id = data_dict['id']
    except KeyError:
        raise p.toolkit.ValidationError(['id missing'])

    method, url = _get_api_endpoint('request_status_show')
    url = url.format(request_id=request_id)

    import ckanext.oauth2waad.plugin as oauth2waad_plugin
    try:
        access_token = oauth2waad_plugin.service_to_service_access_token('metadata')
        if not access_token.startswith('Bearer '):
            access_token = 'Bearer ' + access_token
        headers = {
            'Authorization': access_token,
            'Content-Type': 'application/json',
        }
    except oauth2waad_plugin.ServiceToServiceAccessTokenError, e:
        raise ECAPIError(['EC API Error: Failed to get service auth {0}'.format(e.message)])

    verify_ssl = p.toolkit.asbool(
        config.get('ckanext.glasgow.verify_ssl_certs', True)
    )
    response = requests.request(method, url, headers=headers, 
                                verify=verify_ssl)
    if response.status_code == requests.codes.ok:
        try:
            results = response.json()
        except ValueError:
            raise ECAPIError(['EC API Error: could no decode response as JSON'])

        # change all the keys from CamelCase
        for result in results:
            for key in result.keys():
                key_underscore = re.sub('(?!^)([A-Z]+)', r'_\1', key).lower()
                result[key_underscore] = result.pop(key)

        return results

    else:
        raise ECAPIError(['EC API Error: {0} - {1}'.format(
            response.status_code, response.content)])


@p.toolkit.side_effect_free
def changelog_show(context, data_dict):
    '''
    Requests audit entries to the EC API Changelog API

    :param audit_id: The starting audit_id to return a set of changelog
                     records for. All records created since this audit_id
                     are returned (up until `top`)
                     If omitted then the single most recent changelog
                     record is returned.
    :type audit_id: string
    :param top: Number of records to return (defaults to 20)
    :type top: int
    :param object_type: Limit records to this particular type (valid values
                        are `Dataset`, `File` or `Organisation`)
    :type object_type: string

    :returns: a list with the returned audit objects
    :rtype: list
    '''

    p.toolkit.check_access('changelog_show', context, data_dict)

    audit_id = data_dict.get('audit_id')
    top = data_dict.get('top')
    object_type = data_dict.get('object_type')

    # Send request to EC Audit API

    method, url = _get_api_endpoint('changelog_show')

    if audit_id:
        url += '/{0}'.format(audit_id)

    params = {}
    if top:
        params['$top'] = top
    if object_type:
        params['$ObjectType'] = object_type

    # Get Service to Service auth token

    try:
        access_token = oauth2.service_to_service_access_token('metadata')
    except oauth2.ServiceToServiceAccessTokenError:
        log.warning('Could not get the Service to Service auth token')
        access_token = None

    headers = {
        'Authorization': 'Bearer {0}'.format(access_token),
        'Content-Type': 'application/json',
    }

    verify_ssl = p.toolkit.asbool(
        config.get('ckanext.glasgow.verify_ssl_certs', True)
    )
    response = requests.request(method, url, headers=headers, params=params,
                                verify=verify_ssl)

    content = response.json()

    # Check status codes

    status_code = response.status_code

    if status_code != 200:
        error_dict = {
            'message': ['The CTPEC API returned an error code'],
            'status': [status_code],
            'content': [content],
        }
        if status_code == 401:
            raise ECAPINotAuthorized('CTPEC API returned an authentication failure: {0}'.format(response.content))
        else:
            raise p.toolkit.ValidationError(error_dict)

    return content


def organization_create(context, data_dict):

    if data_dict.get('__local_action', False):
        context['local_action'] = True

    if (context.get('local_action', False) or
            data_dict.get('type') == 'harvest'):
        return core_actions.create.organization_create(context, data_dict)
    else:
        return p.toolkit.get_action('organization_request_create')(context,
                                                                   data_dict)


def organization_request_create(context, data_dict):
    check_access('organization_request_create', context, data_dict)

    context.update({'model': model, 'session': model.Session})
    create_schema = custom_schema.create_group_schema()

    validated_data_dict, errors = validate(data_dict, create_schema, context)

    if errors:
        raise p.toolkit.ValidationError(errors)

    ec_dict = custom_schema.convert_ckan_organization_to_ec_organization(
        validated_data_dict)

    task_dict = _create_task_status(context,
                                    task_type='organization_request_create',
                                    entity_id=validated_data_dict['name'],
                                    entity_type='organization',
                                    key=validated_data_dict['name'],
                                    value=json.dumps({
                                        'data_dict': data_dict,
                                    }))

    method, url = _get_api_endpoint('organization_request_create')

    content = send_request_to_ec_platform(method, url,
                                          data=json.dumps(ec_dict),
                                          context=context,
                                          task_dict=task_dict)
    try:
        request_id = content['RequestId']
    except KeyError:
        error_dict = {
            'message': ['RequestId not in response from EC Platform'],
            'content': [json.dumps(content)],
        }
        raise p.toolkit.ValidationError(error_dict)

    task_dict = _update_task_status_success(context, task_dict, {
        'data_dict': validated_data_dict,
        'request_id': request_id,
    })

    return {
        'task_id': task_dict['id'],
        'request_id': request_id,
        'name': validated_data_dict['name'],
        'type': 'organization',
    }


def organization_update(context, data_dict):
    if data_dict.get('__local_action', False):

        context['local_action'] = True
        data_dict.pop('__local_action', None)

    if (context.get('local_action', False) or
            data_dict.get('type') == 'harvest' or
            data_dict.get('source_type')):

        return core_actions.update.organization_update(context, data_dict)

    else:

        return p.toolkit.get_action('organization_request_update')(context,
                                                                   data_dict)


def organization_request_update(context, data_dict):
    check_access('organization_update', context, data_dict)
    context.update({'model': model, 'session': model.Session})
    update_schema = custom_schema.update_organization_schema()

    try:
        # group_name_validator is horrible and looks for groups in the context
        # this puts the current group object into the context. Eww.
        org_dict = p.toolkit.get_action('organization_show')(context,
                                                  {'id': data_dict['id']})
    except p.toolkit.ObjectNotFound, e:
        raise p.toolkit.ValidationError(['could not find organization'])

    # We want the actual id, not the name
    data_dict['id'] = org_dict['id']

    validated_data_dict, errors = validate(data_dict, update_schema, context)
    if errors:
        raise p.toolkit.ValidationError(errors)

    task_dict = _create_task_status(context,
                                    task_type='organization_request_update',
                                    entity_id=validated_data_dict['id'],
                                    entity_type='organization',
                                    key=validated_data_dict['name'],
                                    value=json.dumps(
                                        {'data_dict': data_dict}))

    ec_dict = custom_schema.convert_ckan_organization_to_ec_organization(
        validated_data_dict)

    method, url = _get_api_endpoint('organization_request_update')

    url = url.format(
        organization_id=validated_data_dict['id'],
    )

    content = send_request_to_ec_platform(method, url,
                                          data=json.dumps(ec_dict),
                                          context=context,
                                          task_dict=task_dict)
    try:
        request_id = content['RequestId']
    except KeyError:
        error_dict = {
            'message': ['RequestId not in response from EC Platform'],
            'content': [json.dumps(content)],
        }
        raise p.toolkit.ValidationError(error_dict)

    task_dict = _update_task_status_success(context, task_dict, {
        'data_dict': validated_data_dict,
        'request_id': request_id,
    })

    return {
        'task_id': task_dict['id'],
        'request_id': request_id,
        'name': validated_data_dict['name'],
        'type': 'organization',
    }


def send_request_to_ec_platform(method, url, data=None, headers=None,
                                authorize=True, **kwargs):

    task_dict = kwargs.pop('task_dict', None)
    context = kwargs.pop('context', None)

    if not headers:
        headers = {
            'Content-Type': 'application/json',
        }
        if authorize:
            headers['Authorization'] = _get_api_auth_token()

    try:
        verify_ssl = p.toolkit.asbool(
            config.get('ckanext.glasgow.verify_ssl_certs', True)
        )
        response = requests.request(method, url,
                                    data=data,
                                    headers=headers,
                                    verify=verify_ssl,
                                    timeout=50,
                                    **kwargs
                                    )

        log.debug('request data: {0}'.format(str(data)))
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        error_dict = {
            'message': ['The CTPEC API returned an error code'],
            'status': [response.status_code],
            'content': [response.content],
        }
        if task_dict:
            task_dict = _update_task_status_error(context, task_dict, {
                'data_dict': data,
                'error': error_dict
            })

        if response.status_code == requests.codes.unauthorized:
            raise ECAPINotAuthorized('CTPEC API returned an authentication failure: {0}'.format(response.content))
        elif response.status_code == requests.codes.not_found:
            raise ECAPINotFound('CTPEC API returned a 404: {0}'.format(response.content))

        log.debug('request url: {0} - {1}'.format(method, url))
        raise ECAPIError(['The CTPEC API returned an error code: {0} : {1}'.format(response.status_code,
                                                                                  response.content)])
    except requests.exceptions.RequestException, e:
        error_dict = {
            'message': ['Request exception: {0}'.format(e)],
        }

        if task_dict:
            task_dict = _update_task_status_error(context, task_dict, {
                'data_dict': data,
                'error': error_dict
            })
        raise p.toolkit.ValidationError(error_dict)

    try:
        content = response.json()
    except ValueError:
        error_dict = {
            'message': ['Error decoding JSON from EC Platform response'],
            'content': [response.content],
        }
        raise p.toolkit.ValidationError(error_dict)

    return content


def organization_member_create(context, data_dict):
    if data_dict.get('__local_action', False):
        context['local_action'] = True
        data_dict.pop('__local_action', None)

    if (context.get('local_action', False) or
            data_dict.get('type') == 'harvest' or
            data_dict.get('source_type')):
        return core_actions.create.organization_member_create(context, data_dict)
    else:
        check_access('organization_member_create', context, data_dict)
        create_schema = core_schema.member_schema()
        validated_data_dict, errors = validate(data_dict, create_schema, context)

        if errors:
            raise p.toolkit.ValidationError(errors)

        try:
            # check if the user is a CTPEC user
            ec_user = p.toolkit.get_action('ec_user_show')(
                context,
                {'ec_username': validated_data_dict['username']}
            )
        except ECAPINotFound:
            ec_user = None

        # ckan only users can only be members, CTPEC users can only be
        # editors/admins. If it's a ckan member assignment, use the core
        # action, if it's a CTPEC user send it to CTPEC
        if validated_data_dict.get('role') == 'member' and not ec_user:
                return core_actions.create.organization_member_create(context,
                                                                      data_dict)

        elif validated_data_dict.get('role') != 'member' and ec_user:
            if ec_user.get('OrganisationId'):
                validated_data_dict['current_organization'] = ec_user['OrganisationId']

            return p.toolkit.get_action('user_role_update')(
                context,
                validated_data_dict)

        elif validated_data_dict.get('role') != 'member' and not ec_user:
            raise p.toolkit.ValidationError(['a non CTPEC user can only be a member'])

        elif validated_data_dict.get('role') == 'member' and ec_user:
            raise p.toolkit.ValidationError(['a CTPEC user cannot be a member'])


def user_role_update(context, data_dict):
    context.update({'model': model, 'session': model.Session})

    ec_dict = custom_schema.convert_ckan_member_to_ec_member(data_dict)

    key = '{0}@{1}'.format(data_dict.get('name', data_dict['id']),
                           datetime.datetime.now().isoformat())

    task_dict = _create_task_status(context,
                                    task_type='member_update',
                                    entity_id=data_dict['id'],
                                    entity_type='member',
                                    key=key,
                                    value=json.dumps(
                                        {'data_dict': data_dict})
                                    )

    user = p.toolkit.get_action('user_show')(
        context,
        {'id': data_dict['username']}
    )

    if data_dict.get('current_organization'):
        method, url = _get_api_endpoint('user_org_role_update')
        url = url.format(
            organization_id=data_dict.pop('current_organization'),
            user_id=user['id']
        )
    else:
        method, url = _get_api_endpoint('user_role_update')
        url = url.format(
            user_id=user['id']
        )


    content = send_request_to_ec_platform(method, url,
                                          data=json.dumps(ec_dict),
                                          context=context,
                                          task_dict=task_dict)

    try:
        request_id = content['RequestId']
    except KeyError:
        error_dict = {
            'message': ['RequestId not in response from EC Platform'],
            'content': [json.dumps(content)],
        }
        raise p.toolkit.ValidationError(error_dict)

    task_dict = _update_task_status_success(context, task_dict, {
        'data_dict': data_dict,
        'request_id': request_id,
    })

    helpers.flash_success('user update has been requested with request id {0}'.format(request_id))

    return {
        'task_id': task_dict['id'],
        'request_id': request_id,
    }


def ec_superadmin_create(context, data_dict):
    check_access('ec_superadmin_create',context, data_dict)
    context.update({'model': model, 'session': model.Session})

    key = '{0}@{1}'.format(data_dict.get('name', data_dict['user']),
                           datetime.datetime.now().isoformat())


    request_params = {
        'NewOrganisationId': None,
        'UserRoles': [ 'SuperAdmin' ],
    }

    task_dict = _create_task_status(context,
                                    task_type='user_update',
                                    entity_id=data_dict['user'],
                                    entity_type='member',
                                    key=key,
                                    value=json.dumps({})
                                    )

    user = p.toolkit.get_action('user_show')(
        context,
        {'id': data_dict['user'] }
    )

    method, url = _get_api_endpoint('user_role_update')
    url = url.format(
        user_id=user['id']
    )

    content = send_request_to_ec_platform(method, url,
                                          data=json.dumps(request_params),
                                          context=context,
                                          task_dict=task_dict)

    try:
        request_id = content['RequestId']
    except KeyError:
        error_dict = {
            'message': ['RequestId not in response from EC Platform'],
            'content': [json.dumps(content)],
        }
        raise p.toolkit.ValidationError(error_dict)

    task_dict = _update_task_status_success(context, task_dict, {
        'data_dict': data_dict,
        'request_id': request_id,
    })

    helpers.flash_success('user update has been requested with request id {0}'.format(request_id))

    return {
        'task_id': task_dict['id'],
        'request_id': request_id,
    }


def organization_member_delete(context, data_dict):
    if data_dict.get('__local_action', False):
        context['local_action'] = True
        data_dict.pop('__local_action', None)

    if (context.get('local_action', False) or
            data_dict.get('type') == 'harvest' or
            data_dict.get('source_type')):
        return core_actions.delete.organization_member_delete(context, data_dict)
    else:
        check_access('organization_member_delete', context, data_dict)

        group_id = p.toolkit.get_or_bust(data_dict, 'id')
        user_id = data_dict.get('username')
        user_id = data_dict.get('user_id') if user_id is None else user_id

        if not user_id:
            raise p.toolkit.ValidationError(['user_id is required'])

        ckan_user = p.toolkit.get_action('user_show')(context, {'id': user_id})
        try:
            # check if the user is a CTPEC user
            ec_user = p.toolkit.get_action('ec_user_show')(
                context,
                {'ec_username': ckan_user['name']}
            )
        except ECAPINotFound:
            ec_user = None

        if not ec_user:
            return core_actions.delete.organization_member_delete(
                context,
                data_dict,
            )
        else:
            return user_role_delete(context, ckan_user['id'], group_id)


def user_role_delete(context, user, user_organization=None):
    context.update({'model': model, 'session': model.Session})


    ckan_user = p.toolkit.get_action('user_show')(context, {'id': user})

    key = '{0}@{1}'.format(user, datetime.datetime.now().isoformat())

    task_dict = _create_task_status(context,
                                    task_type='user_update',
                                    entity_id=ckan_user['id'],
                                    entity_type='member',
                                    key=key,
                                    value=None
                                    )


    if user_organization:
        method, url = _get_api_endpoint('user_org_role_update')
        url = url.format(
            organization_id=user_organization,
            user_id=user
        )
    else:
        method, url = _get_api_endpoint('user_role_update')
        url = url.format(user)

    ec_dict = {
        'NewOrganisationId': None,
        'UserRoles': []
    }

    content = send_request_to_ec_platform(method, url,
                                          data=json.dumps(ec_dict),
                                          context=context,
                                          task_dict=task_dict)

    try:
        request_id = content['RequestId']
    except KeyError:
        error_dict = {
            'message': ['RequestId not in response from EC Platform'],
            'content': [json.dumps(content)],
        }
        raise p.toolkit.ValidationError(error_dict)

    task_dict = _update_task_status_success(context, task_dict, {
        'data_dict': None,
        'request_id': request_id,
    })

    helpers.flash_success(
        'user organization removal has been requested with request id {0}'.format(request_id)
    )

    return {
        'task_id': task_dict['id'],
        'request_id': request_id,
    }

@p.toolkit.side_effect_free
def ec_user_show(context, data_dict):
    '''proxy a request to ec platform for user details'''
    check_access('user_show',context, data_dict)
    username = p.toolkit.get_or_bust(data_dict, 'ec_username')

    method, url = _get_api_endpoint('user_show')
    url = url.format(username=username)

    try:
        access_token = oauth2.service_to_service_access_token('identity')
    except oauth2.ServiceToServiceAccessTokenError:
        log.warning('Could not get the Service to Service auth token')
        access_token = None

    headers = {
        'Authorization': 'Bearer {0}'.format(access_token),
        'Content-Type': 'application/json',
    }

    return send_request_to_ec_platform(method, url, headers=headers)


@p.toolkit.side_effect_free
def ec_user_list(context, data_dict):
    '''proxy a request to ec platform for user list'''
    check_access('user_list',context, data_dict)
    organization_id = data_dict.get('organization_id')
    if organization_id:
        method, url = _get_api_endpoint('user_list_for_organization')
        url = url.format(organization_id=organization_id)
    else:
        method, url = _get_api_endpoint('user_list')


    top = data_dict.get('top')
    skip = data_dict.get('skip')
    params = {}
    if top:
        params['$top'] = top
    if skip:
        params['$skip'] = skip

    try:
        access_token = oauth2.service_to_service_access_token('identity')
    except oauth2.ServiceToServiceAccessTokenError:
        log.warning('Could not get the Service to Service auth token')
        access_token = None

    headers = {
        'Authorization': 'Bearer {0}'.format(access_token),
        'Content-Type': 'application/json',
    }

    return send_request_to_ec_platform(method, url, headers=headers,
                                       params=params)


@p.toolkit.side_effect_free
def ec_organization_list(context, data_dict):
    '''proxy a request to ec platform for user list'''
    check_access('organization_list',context, data_dict)
    organization_id = data_dict.get('organization_id')
    if organization_id:
        method, url = _get_api_endpoint('organization_show')
        url = url.format(organization_id=organization_id)
    else:
        method, url = _get_api_endpoint('organization_list')

    top = data_dict.get('top')
    skip = data_dict.get('skip')
    params = {}
    if top:
        params['$top'] = top
    if skip:
        params['$skip'] = skip
    try:
        access_token = oauth2.service_to_service_access_token('metadata')
    except oauth2.ServiceToServiceAccessTokenError:
        log.warning('Could not get the Service to Service auth token')
        access_token = None

    headers = {
        'Authorization': 'Bearer {0}'.format(access_token),
        'Content-Type': 'application/json',
    }

    return send_request_to_ec_platform(method, url, headers=headers,
                                       params=params)


@p.toolkit.side_effect_free
def approvals_list(context, data_dict):
    '''
    Requests a list of pending approvals to EC API Data collection API

    :param top: Number of records to return
    :type top: int
    :param skip: Number of records to skip
    :type skip: int

    :returns: a list with the returned audit objects
    :rtype: list
    '''

    p.toolkit.check_access('approvals_list', context, data_dict)

    top = data_dict.get('top')
    skip = data_dict.get('skip')

    # Send request to EC Audit API

    method, url = _get_api_endpoint('approvals_list')


    params = {}
    if top:
        params['$top'] = top
    if skip:
        params['$skip'] = skip

    verify_ssl = p.toolkit.asbool(
        config.get('ckanext.glasgow.verify_ssl_certs', True)
    )

    headers = {
        'Authorization': _get_api_auth_token(),
        'Content-Type': 'application/json',
    }

    response = requests.request(method, url, headers=headers, params=params,
                                verify=verify_ssl)

    content = response.json()

    # Check status codes

    status_code = response.status_code

    if status_code != 200:
        error_dict = {
            'message': ['The CTPEC API returned an error code'],
            'status': [status_code],
            'content': [content],
        }
        if status_code == 401:
            raise ECAPINotAuthorized('CTPEC API returned an authentication failure: {0}'.format(response.content))
        else:
            raise p.toolkit.ValidationError(error_dict)

    return content


def approval_act(context, data_dict):
    '''
    Act upon a pending approval

    :param request_id: Request id to act upon
    :type top: string
    :param accept: Whether to accept the request or not
    :type top: bool

    :returns: True if the request was successful
    :rtype: bool
    '''

    p.toolkit.check_access('approval_act', context, data_dict)

    request_id = data_dict.get('request_id', False)
    accept = data_dict.get('accept', False)

    # Send request to EC Audit API

    if accept:
        method, url = _get_api_endpoint('approval_accept')
    else:
        method, url = _get_api_endpoint('approval_reject')

    url = url.format(
        request_id=request_id,
    )

    headers = {
        'Authorization': _get_api_auth_token(),
    }

    verify_ssl = p.toolkit.asbool(
        config.get('ckanext.glasgow.verify_ssl_certs', True)
    )

    response = requests.request(method, url, headers=headers,
                                verify=verify_ssl)

    # Check status codes

    status_code = response.status_code

    if status_code != 200:

        content = response.json()
        error_dict = {
            'message': ['The CTPEC API returned an error code'],
            'status': [status_code],
            'content': [content],
        }
        if status_code == 401:
            raise ECAPINotAuthorized('CTPEC API returned an authentication failure: {0}'.format(response.content))
        else:
            raise p.toolkit.ValidationError(error_dict)

    return True


def approval_download(context, data_dict):
    '''
    Download a file pending approval

    :param request_id: Request id to act upon
    :type top: string

    '''

    p.toolkit.check_access('approval_download', context, data_dict)

    request_id = data_dict.get('request_id', False)

    # Send request to EC Audit API

    method, url = _get_api_endpoint('approval_download')

    url = url.format(
        request_id=request_id,
    )

    headers = {
        'Authorization': _get_api_auth_token(),
    }

    verify_ssl = p.toolkit.asbool(
        config.get('ckanext.glasgow.verify_ssl_certs', True)
    )

    response = requests.request(method, url, headers=headers,
                                verify=verify_ssl)

    # Check status codes

    status_code = response.status_code

    if status_code != 200:

        content = response.json()
        error_dict = {
            'message': ['The CTPEC API returned an error code'],
            'status': [status_code],
            'content': [content],
        }
        if status_code == 401:
            raise ECAPINotAuthorized('CTPEC API returned an authentication failure: {0}'.format(response.content))
        else:
            raise p.toolkit.ValidationError(error_dict)

    return {
        'headers': response.headers,
        'content': response.content,
    }


def organization_list_for_user(context, data_dict):
    '''Return the list of organizations that the user is a member of.

    :param permission: the permission the user has against the returned organizations
      (optional, default: ``edit_group``)
    :type permission: string

    :param user: the id or username of the user.
      (optional, default: current logged in user)

    :returns: list of dictized organizations that the user is authorized to edit
    :rtype: list of dicts

    '''
    model = context['model']
    user = data_dict.get('user')
    if not data_dict.get('user'):
        user = context['user']

    p.toolkit.check_access('organization_list_for_user',context, data_dict)
    sysadmin = new_authz.is_sysadmin(user)

    orgs_q = model.Session.query(model.Group) \
        .filter(model.Group.is_organization == True) \
        .filter(model.Group.state == 'active')

    if not sysadmin:
        # for non-Sysadmins check they have the required permission

        permission = data_dict.get('permission', 'edit_group')

        roles = new_authz.get_roles_with_permission(permission)

        if not roles:
            return []
        user_id = new_authz.get_user_id_for_username(user, allow_none=True)
        if not user_id:
            return []

        q = model.Session.query(model.Member.group_id) \
            .filter(model.Member.table_name == 'user') \
            .filter(model.Member.capacity.in_(roles)) \
            .filter(model.Member.table_id == user_id)

        group_ids = []
        for row in q.all():
            group_ids.append(row.group_id)

        if not group_ids:
            return []

        orgs_q = orgs_q.filter(model.Group.id.in_(group_ids))

    orgs_list = model_dictize.group_list_dictize(orgs_q.all(), context)
    return orgs_list


def resource_delete(context, data_dict):

    if data_dict.get('__local_action', False):
        context['local_action'] = True
        data_dict.pop('__local_action', None)
    if context.get('local_action', False):

        return core_actions.delete.resource_delete(context, data_dict)

    else:

        return p.toolkit.get_action('file_request_delete')(context,
                                                           data_dict)


def file_request_delete(context, data_dict):

    # TODO: refactor to reuse code across updates and file creation/udpate

    if not data_dict.get('id'):
        raise p.toolkit.ValidationError({'id': ['Missing resource id']})

    resource_id = data_dict.get('id')

    try:
        resource_dict = p.toolkit.get_action('resource_show')(context,
                                                              {'id': resource_id})

        # Add some extra fields needed to display the pending deletion on the frontend

        dataset_id = (resource_dict.get('package_id') or
                      resource_dict.get('DataSetId') or
                      resource_dict.get('dataset_id'))
        if not dataset_id:
            raise p.toolkit.ObjectNotFound('Dataset not found')

        # Check if parent dataset exists
        try:
            dataset_dict = p.toolkit.get_action('package_show')(context,
                                                                {'id': dataset_id})

            data_dict['package_id'] = dataset_dict['id']
        except p.toolkit.ObjectNotFound:
            raise p.toolkit.ObjectNotFound('Dataset not found')

        # We need to get the version id from the existing resource
        if not data_dict.get('version_id'):
            version_id = resource_dict.get('ec_api_version_id')
            data_dict['version_id'] = version_id

        if not data_dict.get('version_id'):
            raise p.toolkit.ObjectNotFound('No version id found for resource')

        versions = p.toolkit.get_action('resource_versions_show')(context,
            {'package_id': dataset_id, 'resource_id': resource_id})
        
        version = None
        for v in versions:
            if v['version'] == data_dict['version_id']:
                version = v
                break

        data_dict['name'] = version['name']
        data_dict['description'] = version['description']

    except p.toolkit.ObjectNotFound:
        raise p.toolkit.ObjectNotFound('Resource not found')

    # Check access

    check_access('file_request_delete', context, data_dict)

    # Validate data_dict



    # Store data in task status table
    # Create a task status entry with the validated data
    key = '{0}@{1}'.format(data_dict.get('package_id', 'file'),
                           datetime.datetime.now().isoformat())

    task_dict = _create_task_status(context,
                                    task_type='file_request_delete',
                                    entity_id=data_dict['package_id'],
                                    entity_type='file',
                                    key=key,
                                    value=json.dumps(
                                        {'data_dict': data_dict})
                                    )

    # Send request to EC Data Collection API

    method, url = _get_api_endpoint('file_version_request_delete')
    url = url.format(
        organization_id=dataset_dict['owner_org'],
        dataset_id=dataset_dict['id'],
        file_id=data_dict['id'],
        version_id=data_dict['version_id'],
    )

    headers = {
        'Authorization': _get_api_auth_token(),
    }

    context.update({'model': model, 'session': model.Session})
    data = None

    content = send_request_to_ec_platform(method, url, data, headers,
                                          files=None,
                                          context=context,
                                          task_dict=task_dict)

    try:
        request_id = content['RequestId']
    except KeyError:
        error_dict = {
            'message': ['RequestId not in response from EC Platform'],
            'content': [json.dumps(content)],
        }
        raise p.toolkit.ValidationError(error_dict)

    request_id = content.get('RequestId')
    task_dict = _update_task_status_success(context, task_dict, {
        'data_dict': data_dict,
        'request_id': request_id,
    })

    # Return task id to access it later and the request id returned by the
    # EC Metadata API

    return {
        'task_id': task_dict['id'],
        'request_id': request_id,
        'name': None,
    }


def ec_user_create(context, data_dict):
    check_access('ec_user_create', context, data_dict)
    context.update({'model': model, 'session': model.Session})
    create_schema = custom_schema.ec_create_user_schema()

    validated_data_dict, errors = validate(data_dict, create_schema, context)

    if errors:
        raise p.toolkit.ValidationError(errors)

    task_dict = _create_task_status(context,
                                    task_type='user_request_create',
                                    entity_id=_make_uuid(),
                                    entity_type='user',
                                    # This will be used for validating datasets
                                    key=validated_data_dict['UserName'],
                                    value=json.dumps({}))

    organization_id = validated_data_dict.pop('OrganisationId', None)
    if organization_id:
        method, url = _get_api_endpoint('user_in_organization_request_create')
        url = url.format(organization_id=organization_id)
    else:
        method, url = _get_api_endpoint('user_request_create')

    try:
        access_token = oauth2.service_to_service_access_token('data_collection')
    except oauth2.ServiceToServiceAccessTokenError:
        log.warning('Could not get the Service to Service auth token')
        access_token = None

    headers = {
        'Authorization': 'Bearer {}'.format(access_token),
        'Content-Type': 'application/json',
    }


    content = send_request_to_ec_platform(method, url,
                                          data=json.dumps(validated_data_dict),
                                          headers=headers,
                                          context=context,
                                          task_dict=task_dict)


    request_id = content.get('RequestId')
    task_dict = _update_task_status_success(context, task_dict, {
        'data_dict': data_dict,
        'request_id': request_id,
    })

    return {
        'task_id': task_dict['id'],
        'request_id': request_id,
    }


def file_version_request_create(context, data_dict):
    check_access('file_version_request_create', context, data_dict)
    context.update({'model': model, 'session': model.Session})
    create_schema = custom_schema.resource_schema()

    validated_data_dict, errors = validate(data_dict, create_schema, context)

    if errors:
        raise p.toolkit.ValidationError(errors)

    dataset = p.toolkit.get_action('package_show')(context,
        {'id': data_dict['package_id']})

    ec_dict = custom_schema.convert_ckan_resource_to_ec_file(validated_data_dict)
    ec_dict.pop('DatasetId', None)

    method, url = _get_api_endpoint('file_version_request_create')
    url = url.format(organization_id=dataset['owner_org'],
                     dataset_id=dataset['id'],
                     file_id=data_dict['resource_id'])

    headers = {
        'Authorization': _get_api_auth_token()
    }

    uploaded_file = data_dict.pop('upload', None)

    if isinstance(uploaded_file, cgi.FieldStorage):
        files = {
            'file': (uploaded_file.filename,
                     uploaded_file.file)
        }
        data = {
            'metadata': json.dumps(ec_dict)
        }
    else:
        headers['Content-Type'] = 'application/json'
        files = None

        # Use ExternalUrl instead of FileExternalUrl
        ec_dict['ExternalUrl'] = ec_dict.pop('FileExternalUrl', None)

        data = json.dumps(ec_dict)

    key = '{0}@{1}'.format(validated_data_dict.get('package_id', 'file'),
                           datetime.datetime.now().isoformat())

    task_dict = _create_task_status(context,
                                    task_type='file_version_request_update',
                                    entity_id=validated_data_dict['package_id'],
                                    entity_type='file',
                                    key=key,
                                    value=json.dumps(
                                        {'data_dict': data_dict})
                                    )

    request = send_request_to_ec_platform(method, url, headers=headers,
                                          data=data, files=files)

    task_dict = _update_task_status_success(context, task_dict, {
        'data_dict': data_dict,
        'request_id': request['RequestId'],
    })

    return {
        'request_id': request['RequestId'],
        'task_id': task_dict['id'],
    }


def user_update(context, data_dict):
    if data_dict.get('__local_action', False):
        context['local_action'] = True
        data_dict.pop('__local_action', None)

    if (context.get('local_action', False) or
            data_dict.get('type') == 'harvest' or
            data_dict.get('source_type')):
        return core_actions.update.user_update(context, data_dict)
    else:
        check_access('user_update', context, data_dict)
        user_id  = p.toolkit.get_or_bust(data_dict, 'id')

        if not user_id:
            raise p.toolkit.ValidationError(['id is required'])

        ckan_user = p.toolkit.get_action('user_show')(context, {'id': user_id})
        try:
            # check if the user is a CTPEC user
            ec_user = p.toolkit.get_action('ec_user_show')(
                context,
                {'ec_username': ckan_user['name']}
            )
        except ECAPINotFound:
            ec_user = None

        if not ec_user:
            return core_actions.update.user_update(context, data_dict)
        else:
            return ec_user_update(context, data_dict)
            


def ec_user_update(context, data_dict):
    ec_dict = custom_schema.convert_ckan_user_to_ec_user(data_dict)
    ec_user = p.toolkit.get_action('ec_user_show')(
        context,
        {'ec_username': data_dict['name']},
    )

    keys = set(['UserName', 'IsRegistered', 'Email', 'FirstName',
                'LastName', 'DisplayName', 'About'])

    required = set(['UserName', 'Email', 'FirstName', 'LastName',
                    'DisplayName'])
    current_dict = dict((k, v) for (k, v) in ec_user.items() if k in keys)
    update_dict = dict((k, v) for (k, v) in ec_dict.items() if k in keys)
    update_dict.pop('UserName', None)

    current_dict.update(update_dict)
    current_dict['IsRegisteredUser'] = current_dict.pop('IsRegistered', False)

    for k in required:
        if not current_dict.get(k, None):
            current_dict[k] = 'None'

    key = '{0}@{1}'.format(data_dict.get('name', data_dict['id']),
                           datetime.datetime.now().isoformat())

    task_context = {'model': model, 'session': model.Session}
    task_dict = _create_task_status(task_context,
                                task_type='user_request_update',
                                entity_id=data_dict['id'],
                                entity_type='user',
                                key=key,
                                value=json.dumps({}),
                                )

    if ec_user.get('OrganisationId'):
        method, url = _get_api_endpoint('user_request_update_in_org')
        url = url.format(organization_id=ec_user['OrganisationId'],
                         user_id=ec_user['UserId'])
    else:
        method, url = _get_api_endpoint('user_request_update')
        url = url.format(user_id=ec_user['UserId'])

    content = send_request_to_ec_platform(method, url,
                                          data=json.dumps(current_dict),
                                          context=task_context,
                                          task_dict=task_dict)
    try:
        request_id = content['RequestId']
    except KeyError:
        error_dict = {
            'message': ['RequestId not in response from EC Platform'],
            'content': [json.dumps(content)],
        }
        raise p.toolkit.ValidationError(error_dict)

    task_dict = _update_task_status_success(task_context, task_dict, {
        'request_id': request_id,
    })
    helpers.flash_success('user update has been requested with request id {0}'.format(request_id))

    return {
        'task_id': task_dict['id'],
        'request_id': request_id,
        'name': data_dict['name'],
    }



def user_list(context, data_dict):
    '''Return a list of the site's user accounts.

    :param q: restrict the users returned to those whose names contain a string
      (optional)
    :type q: string
    :param order_by: which field to sort the list by (optional, default:
      ``'name'``)
    :type order_by: string

    :rtype: list of dictionaries

    '''
    model = context['model']

    p.toolkit.check_access('user_list',context, data_dict)

    q = data_dict.get('q','')
    order_by = data_dict.get('order_by','name')


    query = model.Session.query(
        model.User,
        model.User.name.label('name'),
        model.User.fullname.label('fullname'),
        model.User.about.label('about'),
        model.User.about.label('email'),
        model.User.created.label('created'),
        select([func.count(model.Revision.id)], or_(
                model.Revision.author==model.User.name,
                model.Revision.author==model.User.openid
                )
        ).label('number_of_edits'),
        select([func.count(model.UserObjectRole.id)], and_(
            model.UserObjectRole.user_id==model.User.id,
            model.UserObjectRole.context=='Package',
            model.UserObjectRole.role=='admin'
            )
        ).label('number_administered_packages')
    )

    if q:
        query = model.User.search(q, query, user_name=context.get('user'))

    if order_by == 'edits':
        query = query.order_by(desc(
            select([func.count(model.Revision.id)], or_(
                model.Revision.author==model.User.name,
                model.Revision.author==model.User.openid
                ))
        ))
    else:
        query = query.order_by(
            case([(or_(model.User.fullname == None, model.User.fullname == ''),
                   model.User.name)],
                 else_=model.User.fullname)
        )

    # Filter deleted users
    query = query.filter(model.User.state != model.State.DELETED)

    # If you're not a sysadmin, filter out the sysadmin users
    user = context.get('user')
    sysadmin = new_authz.is_sysadmin(user)
    if not sysadmin:
        query = query.filter(model.User.sysadmin==False)

    ## hack for pagination
    if context.get('return_query'):
        return query

    users_list = []

    for user in query.all():
        result_dict = model_dictize.user_dictize(user[0], context)
        users_list.append(result_dict)

    return users_list
