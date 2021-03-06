# -*- coding: utf-8 -*-
import json
import mock

import nose.tools as nt

from ckan.lib import search
from ckan import model

import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories

import ckanext.harvest.model as harvest_model
from ckanext.harvest.tests.factories import HarvestJobFactory
from ckan.plugins import toolkit

from ckanext.glasgow.harvesters.ec_harvester import (
    EcInitialHarvester, EcApiException)
from ckanext.glasgow.harvesters.changelog import (
    handle_user_create,
    handle_user_update,
    handle_role_change,
    handle_organization_update,
)
from ckanext.glasgow.tests import run_mock_ec


class TestDatasetCreate(object):

    @classmethod
    def setup_class(cls):



        # Start mock EC API
        harvest_model.setup()
        run_mock_ec()

    def setup(self):
        helpers.reset_db()
        # Create test user
        self.normal_user = helpers.call_action('user_create',
                                              name='normal_user',
                                              email='test@test.com',
                                              password='test')

    @classmethod
    def teardown_class(cls):

        helpers.reset_db()
        search.clear()

    def test_create_orgs(self):
        harvester = EcInitialHarvester()
        orgs = harvester._create_orgs()
        nt.assert_equals(len(orgs), 3)

    def test_create_orgs_same_id_as_platform(self):
        harvester = EcInitialHarvester()
        orgs = harvester._create_orgs()

        org = helpers.call_action('organization_show', id=orgs[0])

        assert org['id'] in ('1', '2', '3')  # Ids returned by the mock api


    @mock.patch('requests.get')
    def test_create_orgs_bad_response(self, m):
        # setup a mock for requests.get that returns an object
        # with a status_code of 500
        req = mock.MagicMock()
        req.status_code = 500
        m.return_value = req
        harvester = EcInitialHarvester()
        nt.assert_raises(
            EcApiException,
            harvester._create_orgs)

    @mock.patch('requests.get')
    def test_create_orgs_non_json_response(self, m):
        req = mock.MagicMock()
        req.status_code = 200
        req.content = '<html>not json</html>'
        m.return_value = req
        harvester = EcInitialHarvester()
        nt.assert_raises(
            EcApiException,
            harvester._create_orgs)

    @mock.patch('requests.get')
    def test_create_orgs_api_error(self, m):
        req = mock.MagicMock()
        req.status_code = 200
        req.content = '''{
            "IsRetryRequested": false,
            "ErrorMessage": "an error occured",
            "IsErrorResponse": true,
            "MetadataResultSet": []}
        '''
        m.return_value = req
        harvester = EcInitialHarvester()
        nt.assert_raises(
            EcApiException,
            harvester._create_orgs)

    @mock.patch('requests.get')
    def test_create_orgs_no_metadataresultset(self, m):
        # setup a mock for requests.get that returns an object
        # with a status_code of 500
        req = mock.MagicMock()
        req.status_code = 200
        req.content = '''{
            "IsRetryRequested": false,
            "ErrorMessage": "an error occured",
            "IsErrorResponse": true}
        '''
        m.return_value = req
        harvester = EcInitialHarvester()
        nt.assert_raises(
            EcApiException,
            harvester._create_orgs)

    def test_gather(self):
        harvester = EcInitialHarvester()
        job = HarvestJobFactory()
        harvest_result = harvester.gather_stage(job)
        nt.assert_true(harvest_result)

        nt.assert_equals(len(job.objects), 3)

    @mock.patch('requests.get')
    def test_gather_with_ec_500_response(self, m):
        # setup a mock for requests.get that returns an object
        # with a status_code of 500
        req = mock.MagicMock()
        req.status_code = 500
        m.return_value = req

        harvester = EcInitialHarvester()
        job = HarvestJobFactory()

        nt.assert_equals(False, harvester.gather_stage(job))

    @mock.patch('requests.get')
    def test_gather_with_ec_failed_response(self, m):
        # simulate a api error response with error message
        req = mock.MagicMock()
        req.status_code = 200
        req.content = '''{
            "IsRetryRequested": false,
            "ErrorMessage": "an error occured",
            "IsErrorResponse": true,
            "MetadataResultSet": []}
        '''
        m.return_value = req

        harvester = EcInitialHarvester()
        job = HarvestJobFactory()

        nt.assert_equals(False, harvester.gather_stage(job))

    def test_fetch(self):
        harvester = EcInitialHarvester()
        job = HarvestJobFactory()
        org = factories.Organization(name='test-org-1', needs_approval=False,
                                     __local_action=True)

        harvest_object = harvest_model.HarvestObject(
            guid='3',
            job=job,
            extras=[harvest_model.HarvestObjectExtra(
                key='owner_org', value=org['id'])],
            content=json.dumps({
                "Id": 3,
                "Metadata": {
                    "Category": "debitis",
                    "Description": "Sint perspiciatis et dolorem. Consectetur impedit porro omnis nisi adipisci eum rerum tenetur. Voluptate accusamus praesentium autem molestiae possimus a quibusdam harum.",
                    "License": "http://mayert.us/gibsondickinson/dicki.html",
                    "MaintainerContact": "nova_windler@swift.uk",
                    "MaintainerName": "Marge Conn",
                    "OpennessRating": "0",
                    "PublishedOnBehalfOf": "Ms. Gloria Bode",
                    "Quality": "3",
                    "StandardName": "Iste maxime ad non ea",
                    "StandardRating": "4",
                    "StandardVersion": "4.4.0",
                    "Tags": "beatae consequatur sunt ducimus mollitia",
                    "Title": "Raj Data Set 001 with spéciàl çhãrs",
                    "Theme": "assumenda",
                    "UsageGuidance": "Sed magnam labore voluptatem accusamus aut dicta eos et. Et omnis aliquam fugit sed iusto. Consectetur esse et tempora."
                    },
                "CreatedTime": "2014-06-09T14:08:08.78",
                "ModifiedTime": "2014-06-09T14:08:08.78",
                "OrganisationId": 1,
                "Title": "Raj Data Set 001"
                }))
        harvest_object.save()
        harvest_result = harvester.fetch_stage(harvest_object)
        nt.assert_true(harvest_result)

        file_extras = [e for e in harvest_object.extras if e.key == 'file']
        nt.assert_equals(len(file_extras), 2)

        # TODO: split into seperate test
        harvester.import_stage(harvest_object)
        pkg = helpers.call_action('package_show', name_or_id=harvest_object.package_id)

        nt.assert_equals(len(pkg['resources']), 2)

    def test_import(self):
        harvester = EcInitialHarvester()
        job = HarvestJobFactory()
        org = factories.Organization(id='4', name='test-org-2',
                                     needs_approval=False,
                                     __local_action=True)
        harvest_object = harvest_model.HarvestObject(
            guid='3',
            job=job,
            extras=[harvest_model.HarvestObjectExtra(
                key='owner_org', value=org['id'])],
            content=json.dumps({
                "Id": 3,
                "Metadata": {
                    "Category": "debitis",
                    "Description": "Sint perspiciatis et dolorem. Consectetur impedit porro omnis nisi adipisci eum rerum tenetur. Voluptate accusamus praesentium autem molestiae possimus a quibusdam harum.",
                    "License": "http://mayert.us/gibsondickinson/dicki.html",
                    "MaintainerContact": "nova_windler@swift.uk",
                    "MaintainerName": "Marge Conn",
                    "OpennessRating": "0",
                    "PublishedOnBehalfOf": "Ms. Gloria Bode",
                    "Quality": "3",
                    "StandardName": "Iste maxime ad non ea",
                    "StandardRating": "4",
                    "StandardVersion": "4.4.0",
                    "Tags": "beatae consequatur sunt ducimus mollitia",
                    "Title": "Raj Data Set 001",
                    "Theme": "assumenda",
                    "UsageGuidance": "Sed magnam labore voluptatem accusamus aut dicta eos et. Et omnis aliquam fugit sed iusto. Consectetur esse et tempora."
                    },
                "CreatedTime": "2014-06-09T14:08:08.78",
                "ModifiedTime": "2014-06-09T14:08:08.78",
                "OrganisationId": 4,
                "Title": "Raj Data Set 001"
                }))
        harvest_object.save()
        harvest_result = harvester.import_stage(harvest_object)
        nt.assert_true(harvest_result)
        pkg = helpers.call_action('package_show', name_or_id=u'raj-data-set-001')
        nt.assert_equals(pkg['title'], u'Raj Data Set 001')

        nt.assert_equals(pkg['id'], u'3')

        org = helpers.call_action('organization_show', id=u'test-org-2')

        nt.assert_equals(org['id'], '4')
        nt.assert_equals(len(org['packages']), 1)
        nt.assert_equals(org['packages'][0]['name'], u'raj-data-set-001')


class TestUserCreate(object):
    @classmethod
    def setup_class(cls):
        # Start mock EC API
        harvest_model.setup()
        run_mock_ec()

    def setup(self):
        helpers.reset_db()
        self.normal_user = helpers.call_action('user_create',
                                              name='normal_user',
                                              email='test@test.com',
                                              password='test')

        # Create test org
        self.test_org = helpers.call_action('organization_create',
                                       context={
                                           'user': 'normal_user',
                                           'local_action': True,
                                       },
                                       name='test_org',
                                       needs_approval=False,
                                       id='organisation123')

    @classmethod
    def teardown_class(cls):
        helpers.reset_db()
        search.clear()

    @mock.patch('requests.request')
    def test_user_create(self, mock_request):
        content = {"UserName": 'testuser',
            "About": "about",
            "DisplayName": "display name",
            "Roles": ['OrganisationEditor'],
            "FirstName": "firstname",
            "LastName": "lastname",
            "UserId": "userid123",
            "IsRegistered": False,
            "OrganisationId": 'organisation123',
            "Email": "em@il.com"
        }
        mock_request.return_value = mock.Mock(
            status_code=200,
            content=json.dumps(content),
            **{
                'raise_for_status.return_value': None,
                'json.return_value': content,
            }
        )
        site_user = helpers.call_action('get_site_user')
        handle_user_create(
            context={
                'model': model,
                'ignore_auth': True,
                'local_action': True,
                'user': site_user['name']
            },
            audit={'CustomProperties':{'UserName':'testuser'}},
            harvest_object=None,
        )

        user = helpers.call_action('user_show', id='testuser')
        membership = helpers.call_action('member_list', id='organisation123')
        nt.assert_dict_contains_subset(
            {'about': u'about',
             'display_name': u'display name',
             'email_hash': '6dc2fde946483a1d8a84b89345a1b638',
             'fullname': u'display name',
             'id': u'userid123',
             'name': u'testuser',
             'state': u'active',
             'sysadmin': False
            },
            user
        )
        nt.assert_equals(membership[1], (u'userid123', u'user', u'Editor'))


    @mock.patch('requests.request')
    def test_registered_users_does_not_create_user(self, mock_request):
        content = {"UserName": 'testuser',
            "About": "about",
            "DisplayName": "display name",
            "Roles": ['OrganisationEditor'],
            "FirstName": "firstname",
            "LastName": "lastname",
            "UserId": "userid123",
            "IsRegistered": True,
            "OrganisationId": 'organisation123',
            "Email": "em@il.com"
        }
        mock_request.return_value = mock.Mock(
            status_code=200,
            content=json.dumps(content),
            **{
                'raise_for_status.return_value': None,
                'json.return_value': content,
            }
        )
        site_user = helpers.call_action('get_site_user')
        handle_user_create(
            context={
                'model': model,
                'ignore_auth': True,
                'local_action': True,
                'user': site_user['name']
            },
            audit={'CustomProperties':{'UserName':'testuser'}},
            harvest_object=None,
        )

        nt.assert_raises(
            toolkit.ObjectNotFound,
            helpers.call_action,
            'user_show',
            id='testuser'
        )


class TestChangeLogUserUpdate(object):
    @classmethod
    def setup_class(cls):
        # Start mock EC API
        harvest_model.setup()
        run_mock_ec()

    def setup(self):
        helpers.reset_db()
        self.normal_user = helpers.call_action('user_create',
                                              name='normal_user',
                                              email='test@test.com',
                                              password='test')


        self.test_user = helpers.call_action('user_create',
                                             id='userid123',
                                             name='testuser',
                                             email='test1@test.com',
                                             password='test')

        # Create test org that the user is currently in
        self.test_org = helpers.call_action('organization_create',
                                       context={
                                           'user': 'normal_user',
                                           'local_action': True,
                                       },
                                       name='an_org')
        helpers.call_action('organization_member_create',
                            context={
                                'user': 'normal_user',
                                'local_action': True,
                            },
                            id=self.test_org['id'],
                            username=self.test_user['name'],
                            role='editor')


        # the org we want to add the user to
        self.test_org = helpers.call_action('organization_create',
                                       context={
                                           'user': 'normal_user',
                                           'local_action': True,
                                       },
                                       name='test_org',
                                       id='organisation123')
    @classmethod
    def teardown_class(cls):
        helpers.reset_db()
        search.clear()

    @mock.patch('requests.request')
    def test_user_update(self, mock_request):
        content = {"UserName": 'testuser',
            "About": "about",
            "DisplayName": "display name",
            "Roles": ['OrganisationEditor'],
            "FirstName": "firstname",
            "LastName": "lastname",
            "UserId": "userid123",
            "IsRegistered": False,
            "OrganisationId": 'organisation123',
            "Email": "em@il.com"
        }
        mock_request.return_value = mock.Mock(
            status_code=200,
            content=json.dumps(content),
            **{
                'raise_for_status.return_value': None,
                'json.return_value': content,
            }
        )
        site_user = helpers.call_action('get_site_user')
        handle_user_update(
            context={
                'model': model,
                'ignore_auth': True,
                'local_action': True,
                'user': site_user['name']
            },
            audit={'CustomProperties':{'UserName':'testuser'}},
            harvest_object=None,
        )

        user = helpers.call_action('user_show', id='testuser')
        nt.assert_dict_contains_subset(
            {'about': u'about',
             'display_name': u'display name',
             'email_hash': '6dc2fde946483a1d8a84b89345a1b638',
             'fullname': u'display name',
             'id': u'userid123',
             'name': u'testuser',
             'state': u'active',
             'sysadmin': False
            },
            user
        )

        membership = helpers.call_action('member_list', id='an_org')

    @mock.patch('requests.request')
    def test_make_editor_admin(self, mock_request):
        content = {"UserName": 'testuser',
            "About": "about",
            "DisplayName": "display name",
            "Roles": ['OrganisationAdmin'],
            "FirstName": "firstname",
            "LastName": "lastname",
            "UserId": "userid123",
            "IsRegistered": False,
            "OrganisationId": 'organisation123',
            "Email": "em@il.com"
        }
        mock_request.return_value = mock.Mock(
            status_code=200,
            content=json.dumps(content),
            **{
                'raise_for_status.return_value': None,
                'json.return_value': content,
            }
        )
        site_user = helpers.call_action('get_site_user')
        handle_role_change(
            context={
                'model': model,
                'ignore_auth': True,
                'local_action': True,
                'user': site_user['name']
            },
            audit={'CustomProperties':{'UserId': self.test_user['id']}},
            harvest_object=None,
        )

        membership = helpers.call_action('member_list', id='organisation123')
        nt.assert_equals(membership[1], (u'userid123', u'user', u'Admin'))

        membership = helpers.call_action('member_list', id='an_org')
        nt.assert_false(u'userid123' in set(i[0] for i in membership))

class TestOrgUpdate(object):
    @classmethod
    def setup_class(cls):
        # Start mock EC API
        harvest_model.setup()
        run_mock_ec()

    def setup(self):
        helpers.reset_db()
        self.normal_user = helpers.call_action('user_create',
                                              name='normal_user',
                                              email='test@test.com',
                                              password='test')


        self.test_user = helpers.call_action('user_create',
                                             id='userid123',
                                             name='testuser',
                                             email='test1@test.com',
                                             password='test')

        # Create test org that the user is currently in
        self.test_org = helpers.call_action('organization_create',
                                       context={
                                           'user': 'normal_user',
                                           'local_action': True,
                                       },
                                       name='an_org')

    @mock.patch('requests.request')
    def test_update_does_not_remove_users(self, mock_request):
        old_members = helpers.call_action('member_list', id=self.test_org['id'])
        content = { 'MetadataResultSet': [{
            "Id": self.test_org['id'],
            "Title": "Glasgow City Council",
            "CreatedTime": "2014-05-21T06:06:18.353",
            "ModifiedTime": "2014-05-21T06:06:18.353"
            }]
        }
        mock_request.return_value = mock.Mock(
            status_code=200,
            content=json.dumps(content),
            **{
                'raise_for_status.return_value': None,
                'json.return_value': content,
            }
        )
        site_user = helpers.call_action('get_site_user')
        handle_organization_update(
            context={
                'model': model,
                'ignore_auth': True,
                'local_action': True,
                'user': site_user['name']
            },
            audit={'CustomProperties':{'OrganisationId': self.test_org['id']}},
            harvest_object=None,
        )

        members = helpers.call_action('member_list', id=self.test_org['id'])
        nt.assert_equals(old_members, members)

    @mock.patch('requests.request')
    def test_update_does_org_that_does_not_exist(self, mock_request):
        content = { 'MetadataResultSet': [{
            "Id": 1,
            "Title": "Glasgow City Council",
            "CreatedTime": "2014-05-21T06:06:18.353",
            "ModifiedTime": "2014-05-21T06:06:18.353"
            }]
        }
        mock_request.return_value = mock.Mock(
            status_code=200,
            content=json.dumps(content),
            **{
                'raise_for_status.return_value': None,
                'json.return_value': content,
            }
        )
        site_user = helpers.call_action('get_site_user')
        handle_organization_update(
            context={
                'model': model,
                'ignore_auth': True,
                'local_action': True,
                'user': site_user['name']
            },
            audit={'CustomProperties':{'OrganisationId': 'does not exist'}},
            harvest_object=None,
        )
