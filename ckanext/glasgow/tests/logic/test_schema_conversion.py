import nose

import ckan.new_tests.helpers as helpers

import ckanext.glasgow.logic.schema as custom_schema

eq_ = nose.tools.eq_


class TestSchemaConversion(object):

    def test_convert_ckan_dataset_to_ec_dataset(self):

        ckan_dict = {
            'name': 'test-dataset',
            'title': 'Test Dataset',
            'notes': 'Some longer description',
            'needs_approval': False,
            'maintainer': 'Test maintainer',
            'maintainer_email': 'Test maintainer email',
            'license_id': 'OGL-UK-2.0',
            'tags': [
                {'name': 'Test tag 1'},
                {'name': 'Test tag 2'},
            ],
            'id': 'dataset-id',
            'openness_rating': 3,
            'quality': 5,
            'published_on_behalf_of': 'Test published on behalf of',
            'usage_guidance': 'Test usage guidance',
            'category': 'Test category',
            'theme': 'Test theme',
            'standard_name': 'Test standard name',
            'standard_rating': 5,
            'standard_version': 'Test standard version',
        }

        ec_dict = custom_schema.convert_ckan_dataset_to_ec_dataset(ckan_dict)

        eq_(ec_dict['Id'], 'dataset-id')
        eq_(ec_dict['Title'], 'Test Dataset')
        eq_(ec_dict['Description'], 'Some longer description')
        eq_(ec_dict['MaintainerName'], 'Test maintainer')
        eq_(ec_dict['MaintainerContact'], 'Test maintainer email')
        eq_(ec_dict['License'], 'OGL-UK-2.0')
        eq_(ec_dict['Tags'], 'Test tag 1,Test tag 2')
        eq_(ec_dict['OpennessRating'], 3)
        eq_(ec_dict['Quality'], 5)
        eq_(ec_dict['PublishedOnBehalfOf'], 'Test published on behalf of')
        eq_(ec_dict['UsageGuidance'], 'Test usage guidance')
        eq_(ec_dict['Category'], 'Test category')
        eq_(ec_dict['Theme'], 'Test theme')
        eq_(ec_dict['StandardName'], 'Test standard name')
        eq_(ec_dict['StandardRating'], 5)
        eq_(ec_dict['StandardVersion'], 'Test standard version')

    def test_convert_ckan_dataset_to_ec_dataset_integer_values_are_0(self):
        '''Check that the converter does not interpret numerical

        values for OpennessRating/Quality/etc of 0 as False or notexistening
        in the dictionary'''
        ckan_dict = {
            'name': 'test-dataset',
            'title': 'Test Dataset',
            'notes': 'Some longer description',
            'needs_approval': False,
            'maintainer': 'Test maintainer',
            'maintainer_email': 'Test maintainer email',
            'license_id': 'OGL-UK-2.0',
            'tags': [
                {'name': 'Test tag 1'},
                {'name': 'Test tag 2'},
            ],
            'id': 'dataset-id',
            'openness_rating': 0,
            'quality': 0,
            'published_on_behalf_of': 'Test published on behalf of',
            'usage_guidance': 'Test usage guidance',
            'category': 'Test category',
            'theme': 'Test theme',
            'standard_name': 'Test standard name',
            'standard_rating': 1,
            'standard_version': 'Test standard version',
        }

        ec_dict = custom_schema.convert_ckan_dataset_to_ec_dataset(ckan_dict)

        eq_(ec_dict['Id'], 'dataset-id')
        eq_(ec_dict['Title'], 'Test Dataset')
        eq_(ec_dict['Description'], 'Some longer description')
        eq_(ec_dict['MaintainerName'], 'Test maintainer')
        eq_(ec_dict['MaintainerContact'], 'Test maintainer email')
        eq_(ec_dict['License'], 'OGL-UK-2.0')
        eq_(ec_dict['Tags'], 'Test tag 1,Test tag 2')
        eq_(ec_dict['OpennessRating'], 0)
        eq_(ec_dict['Quality'], 0)
        eq_(ec_dict['PublishedOnBehalfOf'], 'Test published on behalf of')
        eq_(ec_dict['UsageGuidance'], 'Test usage guidance')
        eq_(ec_dict['Category'], 'Test category')
        eq_(ec_dict['Theme'], 'Test theme')
        eq_(ec_dict['StandardName'], 'Test standard name')
        eq_(ec_dict['StandardRating'], 1)
        eq_(ec_dict['StandardVersion'], 'Test standard version')

    def test_convert_ec_dataset_to_ckan_dataset(self):

        ec_dict = {
            'Id': 1,
            'Title': 'Test Dataset',
            'Description': 'Some longer description',
            'MaintainerName': 'Test maintainer',
            'MaintainerContact': 'Test maintainer email',
            'License': 'OGL-UK-2.0',
            'Tags': 'Test tag 1,Test tag 2',
            'OpennessRating': 3,
            'Quality': 5,
            'PublishedOnBehalfOf': 'Test published on behalf of',
            'UsageGuidance': 'Test usage guidance',
            'Category': 'Test category',
            'Theme': 'Test theme',
            'StandardName': 'Test standard name',
            'StandardRating': 5,
            'StandardVersion': 'Test standard version',
        }

        ckan_dict = custom_schema.convert_ec_dataset_to_ckan_dataset(ec_dict)

        eq_(ckan_dict['id'], '1')
        eq_(ckan_dict['title'], 'Test Dataset')
        eq_(ckan_dict['notes'], 'Some longer description')
        eq_(ckan_dict['maintainer'], 'Test maintainer')
        eq_(ckan_dict['maintainer_email'], 'Test maintainer email')
        eq_(ckan_dict['license_id'], 'OGL-UK-2.0')
        eq_(ckan_dict['tags'], [
            {'name': 'Test tag 1'},
            {'name': 'Test tag 2'},
            ])
        eq_(ckan_dict['openness_rating'], 3)
        eq_(ckan_dict['quality'], 5)
        eq_(ckan_dict['published_on_behalf_of'], 'Test published on behalf of')
        eq_(ckan_dict['usage_guidance'], 'Test usage guidance')
        eq_(ckan_dict['category'], 'Test category')
        eq_(ckan_dict['theme'], 'Test theme')
        eq_(ckan_dict['standard_name'], 'Test standard name')
        eq_(ckan_dict['standard_rating'], 5)
        eq_(ckan_dict['standard_version'], 'Test standard version')

    def test_convert_ec_dataset_to_ckan_dataset_integer_values_are_0(self):
        '''Check that the converter does not interpret numerical

        values for OpennessRating/Quality/etc of 0 as False or notexistening
        in the dictionary'''

        ec_dict = {
            'Id': 1,
            'Title': 'Test Dataset',
            'Description': 'Some longer description',
            'MaintainerName': 'Test maintainer',
            'MaintainerContact': 'Test maintainer email',
            'License': 'OGL-UK-2.0',
            'Tags': 'Test tag 1,Test tag 2',
            'OpennessRating': 0,
            'Quality': 0,
            'PublishedOnBehalfOf': 'Test published on behalf of',
            'UsageGuidance': 'Test usage guidance',
            'Category': 'Test category',
            'Theme': 'Test theme',
            'StandardName': 'Test standard name',
            'StandardRating': 1,
            'StandardVersion': 'Test standard version',
        }

        ckan_dict = custom_schema.convert_ec_dataset_to_ckan_dataset(ec_dict)

        eq_(ckan_dict['id'], '1')
        eq_(ckan_dict['title'], 'Test Dataset')
        eq_(ckan_dict['notes'], 'Some longer description')
        eq_(ckan_dict['maintainer'], 'Test maintainer')
        eq_(ckan_dict['maintainer_email'], 'Test maintainer email')
        eq_(ckan_dict['license_id'], 'OGL-UK-2.0')
        eq_(ckan_dict['tags'], [
            {'name': 'Test tag 1'},
            {'name': 'Test tag 2'},
            ])
        eq_(ckan_dict['openness_rating'], 0)
        eq_(ckan_dict['quality'], 0)
        eq_(ckan_dict['published_on_behalf_of'], 'Test published on behalf of')
        eq_(ckan_dict['usage_guidance'], 'Test usage guidance')
        eq_(ckan_dict['category'], 'Test category')
        eq_(ckan_dict['theme'], 'Test theme')
        eq_(ckan_dict['standard_name'], 'Test standard name')
        eq_(ckan_dict['standard_rating'], 1)
        eq_(ckan_dict['standard_version'], 'Test standard version')

    def test_convert_ckan_dataset_to_ec_dataset_missing_fields(self):

        ckan_dict = {
        }

        ec_dict = custom_schema.convert_ckan_dataset_to_ec_dataset(ckan_dict)

        assert 'Title' not in ec_dict

    def test_convert_ec_dataset_to_ckan_dataset_missing_fields(self):

        ec_dict = {
        }

        ckan_dict = custom_schema.convert_ec_dataset_to_ckan_dataset(ec_dict)

        assert 'title' not in ec_dict

    def test_convert_ckan_resource_to_ec_file(self):

        ckan_dict = {
            'id': 'resource-id',
            'package_id': 'test-dataset-id',
            'name': 'Test File name',
            'url': 'http://some.file.com',
            'description': 'Some longer description',
            'format': 'application/csv',
            'license_id': 'uk-ogl',
            'openness_rating': 3,
            'quality': 5,
            'standard_name': 'Test standard name',
            'standard_rating': 1,
            'standard_version': 'Test standard version',
            'creation_date': '2014-03-22T05:42:00',
            'ec_api_dataset_id': 1,
        }

        ec_dict = custom_schema.convert_ckan_resource_to_ec_file(ckan_dict)

        eq_(ec_dict['FileId'], 'resource-id')
        eq_(ec_dict['DatasetId'], 1)
        eq_(ec_dict['Title'], 'Test File name')
        eq_(ec_dict['ExternalUrl'], 'http://some.file.com')
        eq_(ec_dict['Description'], 'Some longer description')
        eq_(ec_dict['Type'], 'application/csv')
        eq_(ec_dict['License'], 'uk-ogl')
        eq_(ec_dict['OpennessRating'], 3)
        eq_(ec_dict['Quality'], 5)
        eq_(ec_dict['StandardName'], 'Test standard name')
        eq_(ec_dict['StandardRating'], 1)
        eq_(ec_dict['StandardVersion'], 'Test standard version')
        eq_(ec_dict['CreationDate'], '2014-03-22T05:42:00')

    def test_convert_ckan_resource_to_ec_file_no_ec_api_dataset_id(self):

        # Create a dataset for the resource
        helpers.call_action('user_create',
                            name='sysadmin_user',
                            email='test@test.com',
                            password='test',
                            sysadmin=True)

        helpers.call_action('organization_create',
                            context={
                                'user': 'sysadmin_user',
                                'local_action': True,
                            },
                            name='test_org',
                            extras=[{'key': 'ec_api_id',
                                     'value': 1}])

        context = {'local_action': True, 'user': 'sysadmin_user'}
        data_dict = {
            'name': 'test_dataset',
            'owner_org': 'test_org',
            'title': 'Test Dataset',
            'notes': 'Some longer description',
            'needs_approval': False,
            'maintainer': 'Test maintainer',
            'maintainer_email': 'Test maintainer email',
            'license_id': 'OGL-UK-2.0',
            'openness_rating': 3,
            'quality': 5,
            'id': 4,
        }

        test_org = helpers.call_action('package_create',
                                       context=context,
                                       **data_dict)

        ckan_dict = {
            'package_id': 'test-dataset',
            'name': 'Test File name',
            'url': 'http://some.file.com',
            'description': 'Some longer description',
            'format': 'application/csv',
            'license_id': 'uk-ogl',
            'openness_rating': 3,
            'quality': 5,
            'standard_name': 'Test standard name',
            'standard_rating': 1,
            'standard_version': 'Test standard version',
            'creation_date': '2014-03-22T05:42:00',
            'id': 'resource-id',

        }

        ec_dict = custom_schema.convert_ckan_resource_to_ec_file(ckan_dict)

        eq_(ec_dict['FileId'], 'resource-id')
        eq_(ec_dict['DatasetId'], 'test-dataset')
        eq_(ec_dict['Title'], 'Test File name')
        eq_(ec_dict['ExternalUrl'], 'http://some.file.com')
        eq_(ec_dict['Description'], 'Some longer description')
        eq_(ec_dict['Type'], 'application/csv')
        eq_(ec_dict['License'], 'uk-ogl')
        eq_(ec_dict['OpennessRating'], 3)
        eq_(ec_dict['Quality'], 5)
        eq_(ec_dict['StandardName'], 'Test standard name')
        eq_(ec_dict['StandardRating'], 1)
        eq_(ec_dict['StandardVersion'], 'Test standard version')
        eq_(ec_dict['CreationDate'], '2014-03-22T05:42:00')

        helpers.reset_db()

    def test_convert_ec_file_to_ckan_resource(self):

        ec_dict = {
            'FileId': 2,
            'DatasetId': 1,
            'Title': 'Test File name',
            'Description': 'Some longer description',
            'ExternalUrl': 'http://some.file.com',
            'Type': 'application/csv',
            'License': 'uk-ogl',
            'OpennessRating': 3,
            'Quality': 5,
            'StandardName': 'Test standard name',
            'StandardRating': 1,
            'StandardVersion': 'Test standard version',
            'CreationDate': '2014-03-22T05:42:00',
        }

        ckan_dict = custom_schema.convert_ec_file_to_ckan_resource(ec_dict)

        eq_(ckan_dict['id'], 2)
        eq_(ckan_dict['name'], 'Test File name')
        eq_(ckan_dict['description'], 'Some longer description')
        eq_(ckan_dict['url'], 'http://some.file.com')
        eq_(ckan_dict['format'], 'application/csv')
        eq_(ckan_dict['license_id'], 'uk-ogl')
        eq_(ckan_dict['openness_rating'], 3)
        eq_(ckan_dict['quality'], 5)
        eq_(ckan_dict['standard_name'], 'Test standard name')
        eq_(ckan_dict['standard_rating'], 1)
        eq_(ckan_dict['standard_version'], 'Test standard version')
        eq_(ckan_dict['creation_date'], '2014-03-22T05:42:00')

    def test_convert_ckan_resource_to_ec_file_missing_fields(self):

        ckan_dict = {
        }

        ec_dict = custom_schema.convert_ckan_resource_to_ec_file(ckan_dict)

        assert 'Title' not in ec_dict

    def test_convert_ec_file_to_ckan_resource_missing_fields(self):

        ec_dict = {
        }

        ckan_dict = custom_schema.convert_ec_dataset_to_ckan_dataset(ec_dict)

        assert 'name' not in ec_dict

    def test_convert_ckan_organization_to_ec_organization(self):

        ckan_dict = {
            'id': 'org-id',
            'title': 'Test Org',
            'description': 'Some longer description',
        }

        ec_dict = custom_schema.convert_ckan_organization_to_ec_organization(ckan_dict)

        eq_(ec_dict['Id'], 'org-id')
        #eq_(ec_dict['Title'], 'Test Org')
        eq_(ec_dict['About'], 'Some longer description')

    def test_convert_ec_organization_to_ckan_organization(self):

        ec_dict = {
            'Id': 'org-id',
            'About': 'Test Org',
            'Description': 'Some longer description',
        }

        ckan_dict = custom_schema.convert_ec_organization_to_ckan_organization(ec_dict)

        eq_(ckan_dict['id'], 'org-id')
        eq_(ckan_dict['title'], 'Test Org')
        eq_(ckan_dict['description'], 'Some longer description')
