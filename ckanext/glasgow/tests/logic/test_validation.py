import nose

from ckan import model

# 2.3 will offer navl_validate in toolkit
from ckan.lib.navl.dictization_functions import validate

import ckanext.glasgow.logic.schema as custom_schema

eq_ = nose.tools.eq_

create_dataset_schema = custom_schema.create_package_schema()

resource_schema = custom_schema.resource_schema()


class TestDatasetValidation(object):

    def test_basic_valid(self):

        data_dict = {
            'name': 'test-dataset',
            'title': 'Test Dataset',
            'notes': 'Some longer description',
            'maintainer': 'Test maintainer',
            'maintainer_email': 'Test maintainer email',
            'license_id': 'OGL-UK-2.0',
            'tags': [
                {'name': 'Test tag 1'},
                {'name': 'Test tag 2'},
            ],
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
        context = {'model': model, 'session': model.Session}

        data, errors = validate(data_dict, create_dataset_schema, context)

        # No errors
        eq_(errors, {})

        converted_to_extras = [
            'openness_rating',
            'quality',
            'published_on_behalf_of',
            'usage_guidance',
            'category',
            'theme',
            'standard_name',
            'standard_rating',
            'standard_version',
        ]

        # No modifications
        for key in set(data_dict.keys()) - set(converted_to_extras):
            eq_(data_dict[key], data[key])

        for key in converted_to_extras:
            for extra in data['extras']:
                if extra['key'] == key:
                    eq_(data_dict[key], extra['value'])

    def test_create_missing_fields(self):

        data_dict = {

        }
        context = {'model': model, 'session': model.Session}

        data, errors = validate(data_dict, create_dataset_schema, context)

        eq_(sorted(errors.keys()), ['license_id', 'maintainer',
            'maintainer_email', 'name', 'notes', 'openness_rating', 'quality',
                                    'title'])

        for k, v in errors.iteritems():
            eq_(errors[k], ['Missing value'])

    def test_create_only_mandatory_fields(self):

        data_dict = {
            'name': 'test-dataset',
            'title': 'Test Dataset',
            'notes': 'Some longer description',
            'maintainer': 'Test maintainer',
            'maintainer_email': 'Test maintainer email',
            'license_id': 'OGL-UK-2.0',
            'openness_rating': 3,
            'quality': 5,
        }
        context = {'model': model, 'session': model.Session}

        data, errors = validate(data_dict, create_dataset_schema, context)

        # No errors
        eq_(errors, {})

    def test_create_fields_too_long(self):

        data_dict = {
            'name': 'test-dataset',
            'title': 'a' * 256,
            'notes': 'Some longer description',
            'maintainer': 'a' * 256,
            'maintainer_email': 'a' * 256,
            'license_id': 'OGL-UK-2.0',
            'openness_rating': 3,
            'quality': 5,
            'published_on_behalf_of': 'a' * 256,
            'usage_guidance': 'a' * 256,
            'category': 'a' * 256,
            'theme': 'a' * 256,
            'standard_name': 'a' * 256,
            'standard_rating': 5,
            'standard_version': 'a' * 256,
        }

        context = {'model': model, 'session': model.Session}

        data, errors = validate(data_dict, create_dataset_schema, context)

        eq_(sorted(errors.keys()), ['category', 'maintainer',
            'maintainer_email', 'published_on_behalf_of',
                                    'standard_name', 'standard_version',
                                    'theme', 'title', 'usage_guidance'])

        for k, v in errors.iteritems():
            eq_(errors[k], ['Length must be less than 255 characters'])

    def test_create_description_too_long(self):

        data_dict = {
            'name': 'test-dataset',
            'title': 'Test Dataset',
            'notes': 'a' * 4001,
            'maintainer': 'Test maintainer',
            'maintainer_email': 'Test maintainer email',
            'license_id': 'OGL-UK-2.0',
            'openness_rating': 3,
            'quality': 5,
        }

        context = {'model': model, 'session': model.Session}

        data, errors = validate(data_dict, create_dataset_schema, context)

        eq_(errors, {'notes': ['Length must be less than 4000 characters']})

    def test_create_name_too_long_is_trimmed(self):

        data_dict = {
            'name': 'a' * 200,
            'title': 'Test Dataset',
            'notes': 'Some longer description',
            'maintainer': 'Test maintainer',
            'maintainer_email': 'Test maintainer email',
            'license_id': 'OGL-UK-2.0',
            'openness_rating': 3,
            'quality': 5,
        }

        context = {'model': model, 'session': model.Session}

        data, errors = validate(data_dict, create_dataset_schema, context)

        eq_(errors, {})

        eq_(data['name'], 'a' * 100)

    def test_create_wrong_integers(self):

        data_dict = {
            'name': 'test-dataset',
            'title': 'Test Dataset',
            'notes': 'Some longer description',
            'maintainer': 'Test maintainer',
            'maintainer_email': 'Test maintainer email',
            'license_id': 'OGL-UK-2.0',
            'tags': [
                {'name': 'Test tag 1'},
                {'name': 'Test tag 2'},
            ],
            'openness_rating': 'a',
            'quality': '4%',
            'published_on_behalf_of': 'Test published on behalf of',
            'usage_guidance': 'Test usage guidance',
            'category': 'Test category',
            'theme': 'Test theme',
            'standard_name': 'Test standard name',
            'standard_rating': 53.45,
            'standard_version': 'Test standard version',
        }
        context = {'model': model, 'session': model.Session}

        data, errors = validate(data_dict, create_dataset_schema, context)

        eq_(sorted(errors.keys()), ['openness_rating', 'quality',
                                    'standard_rating'])

        for k, v in errors.iteritems():
            eq_(errors[k], ['Invalid integer',
                            'Value must be an integer between 0 and 5'])

    def test_create_integers_out_of_range(self):

        data_dict = {
            'name': 'test-dataset',
            'title': 'Test Dataset',
            'notes': 'Some longer description',
            'maintainer': 'Test maintainer',
            'maintainer_email': 'Test maintainer email',
            'license_id': 'OGL-UK-2.0',
            'tags': [
                {'name': 'Test tag 1'},
                {'name': 'Test tag 2'},
            ],
            'openness_rating': -1,
            'quality': 10,
            'published_on_behalf_of': 'Test published on behalf of',
            'usage_guidance': 'Test usage guidance',
            'category': 'Test category',
            'theme': 'Test theme',
            'standard_name': 'Test standard name',
            'standard_rating': '50',
            'standard_version': 'Test standard version',
        }
        context = {'model': model, 'session': model.Session}

        data, errors = validate(data_dict, create_dataset_schema, context)

        eq_(sorted(errors.keys()), ['openness_rating', 'quality',
                                    'standard_rating'])

        for k, v in errors.iteritems():
            eq_(errors[k], ['Value must be an integer between 0 and 5'])


class TestResourceValidation(object):

    def test_basic_valid(self):

        data_dict = {
            'package_id': 'test-dataset-id',
            'name': 'Test File name',
            'description': 'Some longer description',
            'format': 'application/csv',
            'license_id': 'uk-ogl',
            'openness_rating': 3,
            'quality': 5,
            'standard_name': 'Test standard name',
            'standard_rating': 1,
            'standard_version': 'Test standard version',
            'creation_date': '2014-03-22T05:42:00',
        }
        context = {'model': model, 'session': model.Session}

        data, errors = validate(data_dict, resource_schema, context)

        # No errors
        eq_(errors, {})

        # No modifications
        for key in data_dict.keys():
            eq_(data_dict[key], data[key])

    def test_create_missing_fields(self):

        data_dict = {

        }

        context = {'model': model, 'session': model.Session}

        data, errors = validate(data_dict, resource_schema, context)

        eq_(sorted(errors.keys()), ['description', 'format', 'name',
                                    'package_id'])

        for k, v in errors.iteritems():
            eq_(errors[k], ['Missing value'])

    def test_create_only_mandatory_fields(self):

        data_dict = {
            'package_id': 'test-dataset-id',
            'name': 'Test File name',
            'description': 'Some longer description',
            'format': 'application/csv',
        }

        context = {'model': model, 'session': model.Session}

        data, errors = validate(data_dict, resource_schema, context)

        # No errors
        eq_(errors, {})

    def test_create_fields_too_long(self):

        data_dict = {
            'package_id': 'test-dataset-id',
            'name': 'a' * 256,
            'description': 'Some longer descripiton',
            'format': 'a' * 256,
            'maintainer': 'a' * 256,
            'standard_name': 'a' * 256,
            'standard_version': 'a' * 256,
        }

        context = {'model': model, 'session': model.Session}

        data, errors = validate(data_dict, resource_schema, context)

        eq_(sorted(errors.keys()), ['format', 'name', 'standard_name',
                                    'standard_version'])

        for k, v in errors.iteritems():
            eq_(errors[k], ['Length must be less than 255 characters'])

    def test_create_description_too_long(self):

        data_dict = {
            'package_id': 'test-dataset-id',
            'name': 'Test File name',
            'description': 'a' * 4001,
            'format': 'application/csv',
            'license_id': 'uk-ogl',
            'openness_rating': 3,
            'quality': 5,
            'standard_name': 'Test standard name',
            'standard_rating': 1,
            'standard_version': 'Test standard version',
            'creation_date': '2014-03-22T05:42:00',
        }

        context = {'model': model, 'session': model.Session}

        data, errors = validate(data_dict, resource_schema, context)

        eq_(errors,
            {'description': ['Length must be less than 4000 characters']})

    def test_create_wrong_integers(self):

        data_dict = {
            'package_id': 'test-dataset-id',
            'name': 'Test File name',
            'description': 'Some longer description',
            'format': 'application/csv',
            'license_id': 'uk-ogl',
            'openness_rating': 'a',
            'quality': '4%',
            'standard_name': 'Test standard name',
            'standard_rating': 53.45,
            'standard_version': 'Test standard version',
            'creation_date': '2014-03-22T05:42:00',
        }

        context = {'model': model, 'session': model.Session}

        data, errors = validate(data_dict, resource_schema, context)

        eq_(sorted(errors.keys()), ['openness_rating', 'quality',
                                    'standard_rating'])

        for k, v in errors.iteritems():
            eq_(errors[k], ['Invalid integer',
                            'Value must be an integer between 0 and 5'])

    def test_create_integers_out_of_range(self):

        data_dict = {
            'package_id': 'test-dataset-id',
            'name': 'Test File name',
            'description': 'Some longer description',
            'format': 'application/csv',
            'license_id': 'uk-ogl',
            'openness_rating': -12,
            'quality': 6,
            'standard_name': 'Test standard name',
            'standard_rating': 55,
            'standard_version': 'Test standard version',
            'creation_date': '2014-03-22T05:42:00',
        }

        context = {'model': model, 'session': model.Session}

        data, errors = validate(data_dict, resource_schema, context)

        eq_(sorted(errors.keys()), ['openness_rating', 'quality',
                                    'standard_rating'])

        for k, v in errors.iteritems():
            eq_(errors[k], ['Value must be an integer between 0 and 5'])
