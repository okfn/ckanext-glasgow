import logging
import json

from pylons import config
import requests
from sqlalchemy.sql import update, bindparam

import ckan.model as model
import ckan.plugins.toolkit as toolkit

from ckanext.harvest.model import HarvestJob, HarvestObject, HarvestObjectExtra

import ckanext.glasgow.logic.schema as glasgow_schema
from ckanext.glasgow.harvesters import (
    EcHarvester,
    get_initial_dataset_name,
    get_org_name,
)


log = logging.getLogger(__name__)


class EcApiException(Exception):
    pass


def _fetch_from_ec(request):
    if request.status_code != requests.codes.ok:
        raise EcApiException(
            'Unable to get content for URL: {0}:'.format(request.url))

    try:
        result = request.json()
    except ValueError:
        raise EcApiException('Not a JSON response: {0}:'.format(request.url))

    if result.get('IsErrorResponse', False):
        raise EcApiException(
            'EC API Error: {0}:'.format(result.get('ErrorMessage', '')))

    return result


def ec_api(endpoint):
    skip = 0

    while True:
        verify_ssl = toolkit.asbool(
            config.get('ckanext.glasgow.verify_ssl_certs', True)
        )
        request = requests.get(endpoint, params={'$skip': skip},
                               verify=verify_ssl)
        result = _fetch_from_ec(request)

        if not result.get('MetadataResultSet'):
            raise StopIteration

        try:
            for i in result['MetadataResultSet']:
                yield i
        except KeyError:
            raise EcApiException('No MetadataResultSet in JSON response')

        skip += len(result['MetadataResultSet'])


class EcInitialHarvester(EcHarvester):

    def _create_orgs(self):
        api_url = config.get('ckanext.glasgow.metadata_api', '').rstrip('/')
        api_endpoint = '{0}/Metadata/Organisation'.format(api_url)
        done = []
        duplicates = []
        for org in ec_api(api_endpoint):

            context = {
                'model': model,
                'session': model.Session,
                'user': self._get_site_user()['name']
            }
            data_dict = glasgow_schema.convert_ec_organization_to_ckan_organization(org)
            org_name = get_org_name(org, 'Title')
            data_dict['name'] = org_name

            try:
                if org['Title'] in done:
                    duplicates.append(org['Title'])

                toolkit.get_action('organization_show')(context, {'id': org_name})
                log.debug('Organization {0} ({1}) exists, skipping...'.format(org['Title'].encode('utf8'), org_name))
                done.append(org['Title'])

            except toolkit.ObjectNotFound:
                try:
                    context['local_action'] = True
                    toolkit.get_action('organization_create')(context, data_dict)
                    context.pop('local_action', None)
                except toolkit.ValidationError, e:
                    log.warn('Error creating org: {0}'.format(str(e)))
        if len(duplicates):
            log.warn('Duplicate Organizations found: {0}'.format(', '.join(duplicates).encode('utf8')))
        return toolkit.get_action('organization_list')(context, {})

    def info(self):
        return {
            'name': 'ec_initial_harvester',
            'title': 'EC Initial Import Harvester',
            'description': 'Harvester for initial import of Glasgow Project',

        }

    def gather_stage(self, harvest_job):
        previous_job = model.Session.query(
            HarvestJob) \
            .filter(HarvestJob.source == harvest_job.source) \
            .filter(HarvestJob.gather_finished != None) \
            .filter(HarvestJob.id != harvest_job.id) \
            .order_by(HarvestJob.gather_finished.desc()) \
            .limit(1).first()
        try:
            orgs = self._create_orgs()
            api_url = config.get('ckanext.glasgow.metadata_api', '').rstrip('/')
            api_endpoint = api_url + '/Organisations/{0}/Datasets'

            harvest_object_ids = []
            for org_name in orgs:
                context = {
                    'model': model,
                    'session': model.Session,
                    'user': self._get_site_user()['name']
                }

                organization_show = toolkit.get_action('organization_show')
                org = organization_show(context, {'id': org_name})

                ec_api_org_id = org['id']

                endpoint = api_endpoint.format(ec_api_org_id)

                for dataset in ec_api(endpoint):

                    harvest_object = HarvestObject(
                        guid=dataset['Id'],
                        content=json.dumps(dataset),
                        job=harvest_job,
                        # Add reference to CKAN org to use on import stage
                        extras=[HarvestObjectExtra(
                            key='owner_org', value=org['id'])]
                    )

                    harvest_object.save()
                    harvest_object_ids.append(harvest_object.id)

        except EcApiException, e:
            self._save_gather_error(e.message, harvest_job)
            return False

        return harvest_object_ids

    def fetch_stage(self, harvest_object):
        api_url = config.get('ckanext.glasgow.metadata_api', '').rstrip('/')
        # NB: this end point does not seem to support the $skip parameter
        api_endpoint = api_url + '/Metadata/Organisation/{0}/Dataset/{1}/File'

        try:
            content = json.loads(harvest_object.content)
            org = content['OrganisationId']
            dataset = content['Id']
            verify_ssl = toolkit.asbool(
                config.get('ckanext.glasgow.verify_ssl_certs', True)
            )
            request = requests.get(api_endpoint.format(org, dataset),
                                   verify=verify_ssl)
            if request.status_code == 404:
                result = False
                log.debug('No files for dataset {0}'.format(dataset))
            else:
                result = _fetch_from_ec(request)
        except requests.exceptions.RequestException, e:
            self._save_object_error(
                'Error fetching file metadata for package {0}: {1}'.format(
                    harvest_object.guid, str(e)),
                harvest_object, 'Fetch')
            return False
        except ValueError:
            self._save_object_error(
                ('Could not load json when fetching file metadata for'
                 'package {0}: {1}').format(harvest_object.guid, e.error_dict),
                harvest_object, 'Fetch')
            return False
        except EcApiException, e:
            self._save_object_error(e.message, harvest_object, 'Fetch')
            return False

        if not result:
            return True

        for file_metadata in result['MetadataResultSet']:
            # create harvest object extra for each file
            ckan_dict = glasgow_schema.convert_ec_file_to_ckan_resource(
                file_metadata['FileMetadata'])
            ckan_dict['id'] = file_metadata['FileId']

            ckan_dict['ec_api_version_id'] = file_metadata['Version']

            #TODO: This needs to be removed once MS api is using the proper ExternalURL field
            if not ckan_dict.get('url') and file_metadata['FileMetadata'].get('FileExternalUrl'):
                ckan_dict['url'] = file_metadata['FileMetadata'].get('FileExternalUrl')
            harvest_object.extras.append(
                HarvestObjectExtra(key='file', value=json.dumps(ckan_dict))
            )
        harvest_object.save()
        return True

    def import_stage(self, harvest_object):
        site_user = toolkit.get_action('get_site_user')(
            {
                'model': model,
                'session': model.Session,
                'ignore_auth': True,
                'defer_commit': True
            }, {})

        context = {
            'model': model,
            'session': model.Session,
            'user': site_user['name'],
        }

        ec_data_dict = json.loads(harvest_object.content)
        ckan_data_dict = glasgow_schema.convert_ec_dataset_to_ckan_dataset(
            ec_data_dict.get('Metadata', {}))

        ckan_data_dict['id'] = unicode(ec_data_dict['Id'])

        ckan_data_dict['needs_approval'] = ec_data_dict.get('NeedsApproval', False)

        ckan_data_dict['__local_action'] = True

        # double check name
        if 'name' not in ckan_data_dict:
            ckan_data_dict['name'] = get_initial_dataset_name(ckan_data_dict)

        try:
            owner_org = self._get_object_extra(harvest_object, 'owner_org')

            ckan_data_dict['owner_org'] = owner_org


            try:
                pkg = toolkit.get_action('package_show')(context, {'id': ckan_data_dict['name']})

                try:
                    resources = []
                    for extra in harvest_object.extras:
                        if extra.key == 'file':
                            res_dict = json.loads(extra.value)
                            res_dict['package_id'] = pkg['id']
                            resources.append(res_dict)

                    ckan_data_dict['resources'] = resources

                    log.debug('Dataset {0} ({1}) exists and needs to be updated,'.format(
                                ckan_data_dict['title'].encode('utf8'), ckan_data_dict['name']))
                    toolkit.get_action('package_update')(context, ckan_data_dict)
                except toolkit.ValidationError, e:
                    self._save_object_error(
                        'Error saving resources for package {0}: {1}'.format(
                            harvest_object.guid, e.error_dict),
                        harvest_object,
                        'Import'
                    )
                    return False

            except toolkit.ObjectNotFound:
                log.debug('Dataset {0} ({1}) does not exist, creating it...'.format(ckan_data_dict['title'].encode('utf8'), ckan_data_dict['name']))
                resources = []
                for extra in harvest_object.extras:
                    if extra.key == 'file':
                        res_dict = json.loads(extra.value)
                        res_dict['package_id'] = ckan_data_dict['name']
                        resources.append(res_dict)

                ckan_data_dict['resources'] = resources

                # See ckan/ckanext-harvest#84
                context.pop('__auth_audit', None)
                try:

                    pkg = toolkit.get_action('package_create')(context,
                                                               ckan_data_dict)
                except toolkit.ValidationError, e:
                    self._save_object_error('Error saving package {0}: {1}'.format(
                        harvest_object.guid, e.error_dict),
                        harvest_object, 'Import')
                    return False

            from ckanext.harvest.model import harvest_object_table
            conn = model.Session.connection()
            u = update(
                harvest_object_table) \
                .where(harvest_object_table.c.package_id == bindparam('b_package_id')) \
                .values(current=False)
            conn.execute(u, b_package_id=pkg['id'])

            harvest_object.package_id = pkg['id']
            harvest_object.current = True
            harvest_object.save()
        except toolkit.ValidationError, e:
            self._save_object_error(
                'Invalid package with GUID {0}: {1}'.format(
                    harvest_object.guid, e.error_dict),
                harvest_object,
                'Import'
            )
            return False

        return True
