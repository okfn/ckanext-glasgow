import re
import nose

import ckan.new_tests.helpers as helpers

from ckanext.glasgow.tests import run_mock_ec
from ckanext.glasgow.tests.functional import get_test_app

eq_ = nose.tools.eq_


class TestCreateDataset(object):

    @classmethod
    def setup_class(cls):
        cls.app = get_test_app()

        # Create test user
        cls.sysadmin_user = helpers.call_action('user_create',
                                                name='sysadmin_user',
                                                email='test@test.com',
                                                password='test',
                                                sysadmin=True)

        cls.normal_user = helpers.call_action('user_create',
                                              name='normal_user',
                                              email='test@test.com',
                                              password='test')
        test_org = helpers.call_action('organization_create',
                                       context={'user': 'sysadmin_user'},
                                       name='test_org')

        member = {'username': 'normal_user',
                  'role': 'admin',
                  'id': 'test_org'}
        helpers.call_action('organization_member_create',
                            context={'user': 'sysadmin_user'},
                            **member)

        # Start mock EC API
        run_mock_ec()

    @classmethod
    def teardown_class(cls):
        helpers.reset_db()

    def test_create_dataset_anon(self):

        response = self.app.get('/dataset/new')

        # CKAN redirects to the login page
        eq_(response.status_int, 302)

    def test_create_dataset_normal_user(self):

        data_dict = {
            'name': 'test-dataset',
            'title': 'Test Dataset',
            'notes': 'Some longer description',
            'maintainer': 'Test maintainer',
            'maintainer_email': 'Test maintainer email',
            'license_id': 'uk-ogl',
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

        extra_environ = {'REMOTE_USER': str(self.normal_user['name'])}
        response = self.app.get('/dataset/new', extra_environ=extra_environ)

        eq_(response.status_int, 200)

        form = response.forms[1]

        # Make sure we are using the custom form
        assert 'openness_rating' in form.fields.keys()

        for field, value in data_dict.iteritems():
            if field != 'tags':
                form[field] = value

        form['tag_string'] = ','.join(
            [tag['name'] for tag in data_dict['tags']])

        response = form.submit('save', extra_environ=extra_environ)

        eq_(response.status_int, 302)
        assert '/dataset/test-dataset' in response.headers['Location']

        response = response.follow()

        eq_(response.status_int, 200)

        assert ('[Pending] {0}'.format(data_dict['title'])
                in response.html.head.title.text)

        # Make sure a task has been created for this request

        pending_task = helpers.call_action('pending_task_for_dataset',
                                           name=data_dict['name'],
                                           )
        assert pending_task

    def test_create_dataset_missing_fields(self):

        data_dict = {

        }

        extra_environ = {'REMOTE_USER': str(self.normal_user['name'])}
        response = self.app.get('/dataset/new', extra_environ=extra_environ)

        eq_(response.status_int, 200)

        form = response.forms[1]

        # Make sure we are using the custom form
        assert 'openness_rating' in form.fields.keys()

        response = form.submit('save', extra_environ=extra_environ)

        eq_(response.status_int, 200)

        error_div = response.html.find(
            attrs={'class': re.compile(r".*\berror-explanation\b.*")})

        assert error_div
        assert 'Missing value' in error_div.text

    def test_create_dataset_missing_fields(self):

        data_dict = {

        }

        extra_environ = {'REMOTE_USER': str(self.normal_user['name'])}
        response = self.app.get('/dataset/new', extra_environ=extra_environ)

        eq_(response.status_int, 200)

        form = response.forms[1]

        # Make sure we are using the custom form
        assert 'openness_rating' in form.fields.keys()

        response = form.submit('save', extra_environ=extra_environ)

        eq_(response.status_int, 200)

        error_div = response.html.find(
            attrs={'class': re.compile(r".*\berror-explanation\b.*")})

        assert error_div
        assert 'Missing value' in error_div.text