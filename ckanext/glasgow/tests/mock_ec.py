import logging
import uuid
import json

import flask
from werkzeug.exceptions import default_exceptions
from werkzeug.exceptions import HTTPException


def make_json_app(import_name, **kwargs):
    """
    Creates a JSON-oriented Flask app.

    All error responses that you don't specifically
    manage yourself will have application/json content
    type, and will contain JSON like this (just an example):

    { "message": "405: Method Not Allowed" }
    """
    def make_json_error(ex):
        response = flask.jsonify(Message=str(ex))
        response.status_code = (ex.code
                                if isinstance(ex, HTTPException)
                                else 500)
        return response

    app = flask.Flask(import_name, **kwargs)

    for code in default_exceptions.iterkeys():
        app.error_handler_spec[None][code] = make_json_error

    # Add logging
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)

    return app

app = make_json_app(__name__)

dataset_all_fields = [
    'Category',
    'Description',
    'License',
    'MaintainerContact',
    'MaintainerName',
    'OpennessRating',
    'PublishedOnBehalfOf',
    'Quality',
    'StandardName',
    'StandardRating',
    'StandardVersion',
    'Tags',
    'Theme',
    'Title',
    'UsageGuidance',
]

dataset_mandatory_fields = [

    'Title',
    'Description',
    'MaintainerName',
    'MaintainerContact',
    'License',
    'OpennessRating',
    'Quality',
]

dataset_fields_under_255_characters = [
    'Title',
    'MaintainerName',
    'MaintainerContact',
    'License',
    'Category',
    'PublishedOnBehalfOf',
    'StandardName',
    'StandardVersion',
    'Theme',
    'UsageGuidance',
]

file_all_fields = [
    'DatasetId',
    'Title',
    'Description',
    'Type',
    'License',
    'OpennessRating',
    'Quality',
    'StandardName',
    'StandardRating',
    'StandardVersion',
    'CreationDate',
]

file_mandatory_fields = [
    'DatasetId',
    'Title',
    'Description',
    'Type',
]

file_fields_under_255_characters = [
    'Title',
    'Type',
    'License',
    'StandardName',
    'StandardVersion',
]


@app.route('/Users', methods=['POST'])
def request_user_create():

    return flask.jsonify(**{
        "RequestId": unicode(uuid.uuid4()),
        }
    )

@app.route('/Organisations', methods=['POST'])
def request_organization_create():

    return flask.jsonify(**{
        "RequestId": unicode(uuid.uuid4()),
        }
    )

@app.route('/Organisations/Organisation/<organization_id>', methods=['PUT'])
def request_organization_update(organization_id):
    return flask.jsonify(**{
        "RequestId": unicode(uuid.uuid4()),
        }
    )


@app.route('/UserRoles/Organisation/<organization_id>/User/<user_id>', methods=['PUT'])
def request_user_role_update(organization_id, user_id):
    return flask.jsonify(**{
        "RequestId": unicode(uuid.uuid4()),
        }
    )


@app.route('/Files/Organisation/<organization_id>/Dataset/<user_id>/File/<file_id>', methods=['POST'])
def request_file_version_create(organization_id, user_id, file_id):
    return flask.jsonify(**{
        "RequestId": unicode(uuid.uuid4()),
        }
    )

@app.route('/Datasets/Organisation/<organization_id>', methods=['POST'])
def request_dataset_create(organization_id):

    return handle_dataset_request(organization_id)


@app.route('/Datasets/Organisation/<organization_id>/Dataset/<dataset_id>', methods=['PUT'])
def request_dataset_update(organization_id, dataset_id):

    return handle_dataset_request(organization_id, dataset_id)


@app.route('/Files/Organisation/<organization_id>/Dataset/<dataset_id>', methods=['POST'])
def request_file_create(organization_id, dataset_id):

    return handle_file_request(organization_id, dataset_id)


@app.route('/Files/Organisation/<organization_id>/Dataset/<dataset_id>', methods=['PUT'])
def request_file_update(organization_id, dataset_id):

    return handle_file_request(organization_id, dataset_id)

@app.route('/Organisations/<org_id>/Datasets', methods=['GET'])
def request_datasets(org_id):
    skip = int(flask.request.args.get('$skip', 0))
    metadata_result_set = {
        '4': [
            {
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
                },
            {
                "Id": 7,
                "Metadata": {
                    "Category": "quia",
                    "Description": "Eos porro labore vero. Ex voluptas dolore id repellat. Dolorum animi maiores debitis nesciunt maiores fuga.",
                    "License": "http://watsicaoconnell.info/rosenbaum/auer.html",
                    "MaintainerContact": "sandra@friesenborer.ca",
                    "MaintainerName": "Liana Pouros",
                    "OpennessRating": "4",
                    "PublishedOnBehalfOf": "Katlyn Friesen",
                    "Quality": "3",
                    "StandardName": "Et deleniti saepe libero quasi eos et nobis",
                    "StandardRating": "1",
                    "StandardVersion": "4.0.78",
                    "Tags": "deleniti rerum ratione in nemo",
                    "Title": "Dolorum qui illo aliquid",
                    "Theme": "illum",
                    "UsageGuidance": "Eveniet consequatur recusandae omnis distinctio aspernatur. Numquam sit nam dolorum rerum aliquid commodi. Excepturi sit enim dolorem ipsa possimus omnis. Perspiciatis qui delectus id modi sunt aut consectetur. Repellat suscipit ipsum est."
                    },
                "CreatedTime": "2014-06-09T21:46:48.51",
                "ModifiedTime": "2014-06-09T21:46:48.51",
                "OrganisationId": 4,
                "Title": "Dolorum qui illo aliquid"
                },
            {
                "Id": 8,
                "Metadata": {
                    "Category": "sit",
                    "Description": "Fuga voluptas ut et modi est maiores rerum. Sint qui aspernatur inventore quibusdam vel nulla temporibus necessitatibus. Vel voluptas similique quo illo. Repellendus totam ab repudiandae. Enim in corrupti illo ea reprehenderit dicta.",
                    "License": "http://schambergermills.us/schowalter/champlin.html",
                    "MaintainerContact": "granville.collins@hessel.co.uk",
                    "MaintainerName": "Rolando Kemmer",
                    "OpennessRating": "0",
                    "PublishedOnBehalfOf": "Wayne Greenfelder",
                    "Quality": "1",
                    "StandardName": "Est alias qui doloribus possimus iusto",
                    "StandardRating": "0",
                    "StandardVersion": "5.5.44",
                    "Tags": "possimus nemo id laboriosam expedita",
                    "Title": "Non ipsum dolore voluptatem",
                    "Theme": "sint",
                    "UsageGuidance": "Ut suscipit labore excepturi ex laudantium ex voluptates. Sed accusantium sed consequuntur sequi ipsa modi. Delectus perspiciatis mollitia sint ullam maxime et et omnis. Sint ipsa quia a nesciunt."
                    },
                "CreatedTime": "2014-06-09T21:46:52.52",
                "ModifiedTime": "2014-06-09T21:46:52.52",
                "OrganisationId": 4,
                "Title": "Non ipsum dolore voluptatem"
                }
            ],
        }
    res = metadata_result_set.get(org_id, [])
    return flask.jsonify(**{
        "MetadataResultSet": res[skip:],
        "ErrorMessage": None,
        "IsErrorResponse": False,
        "IsRetryRequested": False
        }
    )


@app.route('/Metadata/Organisation/<org_id>/Dataset/<dataset_id>/File',
           methods=['GET'])
def request_files(org_id, dataset_id):
    skip = int(flask.request.args.get('$skip', 0))
    metadata_result_set =  {
        ('1', '3'): [
            {
                "CreatedTime": "2014-06-13T16:36:39.72",
                "DatasetId": 3,
                "FileId": "e2ef198d-26c8-41f1-9355-ac89f409de50",
                "FileMetadata": {
                    "CreationDate": "",
                    "DataSetId": "3",
                    "Description": "jg",
                    "FileExternalUrl": "http://test.com/Download/Organisation/1/Dataset/4/File/e2ef198d-26c8-41f1-9355-ac89f409de50/Version/584732b0-7d46-4b52-929f-9b1e7533239b",
                    "FileName": "test 964.txt",
                    "FileUrl": "bc60abf7-d42b-412e-bacf-9c8523e2eee6/test 964.txt",
                    "License": "",
                    "OpennessRating": "",
                    "Quality": "",
                    "StandardName": "",
                    "StandardRating": "",
                    "StandardVersion": "",
                    "Title": "NEw",
                    "Type": "uyf"
                },
                "ModifiedTime": "0001-01-01T00:00:00",
                "Status": 0,
                "Title": "NEw",
                "Version": "584732b0-7d46-4b52-929f-9b1e7533239b"
            },
            {
                "CreatedTime": "2014-06-13T11:26:24.6",
                "DataSetId": 3,
                "FileId": "f82379eb-aa2f-497b-aa51-b4f931a5e06d",
                "FileMetadata": {
                    "CreationDate": "1965-04-06T06:28:22",
                    "DataSetId": "3",
                    "Description": "Et nam qui quam. Ullam nam ducimus eaque similique laborum et nihil qui. Perspiciatis eum id earum. Eveniet fugiat ut aut quod mollitia. Sint magni architecto similique quibusdam suscipit et eaque.",
                    "FileExternalUrl": "http://test.com/Download/Organisation/1/Dataset/4/File/f82379eb-aa2f-497b-aa51-b4f931a5e06d/Version/727b1018-0d4b-405e-b96b-2417850d59e7",
                    "FileName": "beatae.magni",
                    "FileUrl": "7f18dfcd-9802-4656-95fe-20e09df3c16c/beatae.magni",
                    "License": "http://beattyharber.info/rohanreynolds/jenkinskutch.html",
                    "OpennessRating": "1",
                    "Quality": "0",
                    "StandardName": "Molestiae est possimus rem amet reprehenderit",
                    "StandardRating": "0",
                    "StandardVersion": "7.7.62",
                    "Title": "Aliquam dolorum voluptatem ipsam delectus repellat vel sunt",
                    "Type": "pfefferjohnson/kunzeshields"
                },
                "ModifiedTime": "0001-01-01T00:00:00",
                "Status": 0,
                "Title": "Aliquam dolorum voluptatem ipsam delectus repellat vel sunt",
                "Version": "727b1018-0d4b-405e-b96b-2417850d59e7"
            }
        ],
    }

    files = metadata_result_set.get((org_id, dataset_id), [])
    return flask.jsonify(**{
        "MetadataResultSet": files[skip:],
        "ErrorMessage": None,
        "IsErrorResponse": False,
        "IsRetryRequested": False
        }
    )


@app.route('/Metadata/Organisation', methods=['GET'])
def request_orgs():
    skip = int(flask.request.args.get('$skip', 0))
    metadata_result_set = [
        {
            "Id": 1,
            "Title": "Glasgow City Council",
            "CreatedTime": "2014-05-21T06:06:18.353",
            "ModifiedTime": "2014-05-21T06:06:18.353",
            "NeedsApproval": False
            },
        {
            "Id": 2,
            "Title": "Microsoft",
            "CreatedTime": "2014-05-21T00:00:00",
            "ModifiedTime": "2014-05-21T00:00:00",
            "NeedsApproval": False,
            },
        {
            "Id": 4,
            "Title": "Test Org",
            "CreatedTime": "2014-05-22T00:06:18",
            "ModifiedTime": "2014-05-22T06:06:18",
            "NeedsApproval": False,
            }
        ]

    return flask.jsonify(**{
        "MetadataResultSet": metadata_result_set[skip:],
        "ErrorMessage": None,
        "IsErrorResponse": False,
        "IsRetryRequested": False
        }
    )

@app.route('/Metadata/Organisation/<org_id>/Dataset/<dataset_id>/File/<file_id>/Versions',
           methods=['GET'])
def file_versions(org_id, dataset_id, file_id):
    skip = int(flask.request.args.get('$skip', 0))
    metadata_result_set = {
        ('1', '1', '1'): [
            {
                "CreatedTime": "2014-06-13T09:23:27.763",
                "DataSetId": 1,
                "FileId": "1",
                "FileMetadata": {
                    "CreationDate": "1966-05-29T17:51:20",
                    "DataSetId": "1",
                    "Description": 'test_description',
                    "FileExternalUrl": "http://test.com/Download/Organisation/1/Dataset/1/File/1/Version/3afb06b1-4331-4abd-b88e-055492e21bab",
                    "FileName": "culpa.maxime",
                    "FileUrl": "http://test.com",
                    "License": "license",
                    "OpennessRating": "1",
                    "Quality": "2",
                    "StandardName": "Accusamus aspernatur ut minima rem natus hic expedita voluptatibus",
                    "StandardRating": "4",
                    "StandardVersion": "7.4.30",
                    "Title": "Voluptates ex non quo itaque est quidem praesentium",
                    "Type": "leannonvonrueden/bechtelarfritsch"
                },
                "ModifiedTime": "0001-01-01T00:00:00",
                "Status": 0,
                "Title": "Voluptates ex non quo itaque est quidem praesentium",
                "Version": "3afb06b1-4331-4abd-b88e-055492e21bab"
            },
            {
                "CreatedTime": "2014-06-13T09:23:27.763",
                "DataSetId": 1,
                "FileId": "1",
                "FileMetadata": {
                    "CreationDate": "1966-05-29T17:51:20",
                    "DataSetId": "1",
                    "Description": 'test_description 2',
                    "FileExternalUrl": "http://test.com/2",
                    "FileName": "file 2",
                    "FileUrl": "http://test.com.2",
                    "License": "license",
                    "OpennessRating": "2",
                    "Quality": "2",
                    "StandardName": "test 2",
                    "StandardRating": "2",
                    "StandardVersion": "7.4.30",
                    "Title": "title 2",
                    "Type": "type 2"
                },
                "ModifiedTime": "0001-01-01T00:00:00",
                "Status": 0,
                "Title": "Voluptates ex non quo itaque est quidem praesentium",
                "Version": "44444444444-4444444-44"
            }
        ]
    }

    try:
        #result = metadata_result_set[(org_id, dataset_id, file_id)]
        result = metadata_result_set[('1', '1', '1')]
    except KeyError:
        flask.abort(400)

    return flask.jsonify(**{
        "MetadataResultSet": result[skip:],
        "ErrorMessage": None,
        "IsErrorResponse": False,
        "IsRetryRequested": False
        }
    )


@app.route('/ChangeLog/RequestStatus/<request_id>', methods=['GET'])
def request_change_status(request_id):
    response_string = json.dumps([{
            'AuditId': 1,
            'RequestId': 'REQUEST-ID',
            'Timestamp': '3000-05-21T00:00:10',
            'AuditType': 'FileCreated',
            'Command': 'CreateFile',
            'ObjectType': 'File',
            'OperationState': 'Succeeded',
            'Component': 'DataPublication',
            'Owner': 'Admin',
            'Message': 'File Create Operation completed',
            'CustomProperties': [
                {
                    'OrganisationId': '1',
                    'DatasetId': '1',
                    'FileId': '1',
                    'Versionid': 'VERSION-ID',
                    }
                ]
            },
            ])
    return flask.Response(response_string, mimetype='application/json')


@app.route('/ChangeLog/RequestChanges')
@app.route('/ChangeLog/RequestChanges/<audit_id>')
def request_changelog(audit_id=None):

    # Authorization

    if ('Authorization' not in flask.request.headers or
       flask.request.headers['Authorization'] == 'Bearer unknown_token'):
        response = flask.jsonify(
            Message='Not Auhtorized'
        )
        response.status_code = 401
        return response

    response = [
            {
                "AuditId": 1005,
                "AuditType": "FileCreated",
                "Command": "CreateFile",
                "Component": "DataPublication",
                "CustomProperties": [
                    {
                        "DatasetId": "691E26D0-BACA-4082-AB2D-59AA0027AAF3",
                        "FileId": "AB1E26D0-BACA-4082-AB2D-59AA0027AA90",
                        "OrganisationId": "73612F17-0A19-431F-A86C-F3FE59F86E4A",
                        "Versionid": "781E26D0-BACA-4082-AB2D-59AA0027AA67"
                    }
                ],
                "Message": "File Create Operation completed",
                "ObjectType": "File",
                "OperationState": "Succeeded",
                "Owner": "Widget Admin",
                "RequestId": "D3C86B10-90F8-4CA6-A943-1404FB6C06BF",
                "Timestamp": "2014-05-21T00:00:10"
            },
            {
                "AuditId": 1010,
                "AuditType": "DatasetCreated",
                "Command": "CreateDataset",
                "Component": "DataPublication",
                "CustomProperties": [
                    {
                        "DatasetId": "691E26D0-BACA-4082-AB2D-59AA0027AAF3",
                        "OrganisationId": "73612F17-0A19-431F-A86C-F3FE59F86E4A"
                    }
                ],
                "Message": "Dataset Create Operation completed",
                "ObjectType": "Dataset",
                "OperationState": "Succeeded",
                "Owner": "Joe",
                "RequestId": "90C86B10-90F8-4CA6-A943-1404FB6C0645",
                "Timestamp": "2014-05-21T00:00:10"
            },
            {
                "AuditId": 1012,
                "AuditType": "DatasetCreated",
                "Command": "CreateDataset",
                "Component": "DataPublication",
                "CustomProperties": [
                    {
                        "DatasetId": "691E26D0-BACA-4082-AB2D-XXXXXXXXXXXX",
                        "OrganisationId": "73612F17-0A19-431F-A86C-F3FE59F86E4A"
                    }
                ],
                "Message": "Dataset Create Operation completed",
                "ObjectType": "Dataset",
                "OperationState": "Succeeded",
                "Owner": "Joe",
                "RequestId": "90C86B10-90F8-4CA6-A943-YYYYYYYYYYY",
                "Timestamp": "2014-05-22T13:54:10"
            }

        ]

    top = int(flask.request.args.get('$top', 1000))
    object_type = flask.request.args.get('$ObjectType')

    if audit_id:
        for index, audit in enumerate(response):
            if audit['AuditId'] == audit_id:
                response = response[index:]

    if object_type:
        audits = [a for a in response
                  if a['ObjectType'] == object_type]
        response = audits

    if top:
        response = response[:top]

    return flask.Response(json.dumps(response),
                          headers={
                          'Content-type': 'application/json'
                          })


@app.route('/Identity/User')
def user_list():
    response = [
        {
            'UserId': 'dcfb1b12-fe52-4d71-9aad-c60fc4c6952c',
            'UserName': 'johndoe',
            'OrganisationId': 'de0f2f6e-58ca-4a7b-95b1-7fd6e8df1f69',
            'Email': 'john.doe@org.com',
            'FirstName': 'John',
            'LastName': 'Doe',
            'DisplayName': 'John Doe',
            'About': 'Description',
            'Roles': ['OrganisationEditor'],
            'IsRegistered': False,
            },
        ]
    skip = int(flask.request.args.get('$skip', 0))
    return flask.Response(json.dumps(response[skip:]),
                          headers={
                          'Content-type': 'application/json'
                          })


@app.route('/Identity/User/<user>')
def user_show(user):
    response = {
            'UserId': 'dcfb1b12-fe52-4d71-9aad-c60fc4c6952c',
            'UserName': 'johndoe',
            'OrganisationId': 'de0f2f6e-58ca-4a7b-95b1-7fd6e8df1f69',
            'Email': 'john.doe@org.com',
            'FirstName': 'John',
            'LastName': 'Doe',
            'DisplayName': 'John Doe',
            'About': 'Description',
            'Roles': ['OrganisationEditor'],
            'IsRegistered': False,
    }
        
    return flask.Response(json.dumps(response),
                          headers={
                          'Content-type': 'application/json'
                          })

def handle_dataset_request(organization_id, dataset_id=None):
    data = flask.request.json

    if app.debug:
        app.logger.debug('Headers received:\n{0}'
                         .format(flask.request.headers))
        app.logger.debug('Data received:\n{0}'.format(data))

    if not data:
        response = flask.jsonify(
            Message='No data received'
        )
        response.status_code = 400
        return response

    # Authorization

    if ('Authorization' not in flask.request.headers or
       flask.request.headers['Authorization'] == 'Bearer unknown_token'):
        response = flask.jsonify(
            Message='Not Auhtorized'
        )
        response.status_code = 401
        return response

    # Basic Validation

    for field in dataset_mandatory_fields:
        if not field in data:
            response = flask.jsonify(
                Message='Missing fields',
                ModelState={
                    'model.' + field:
                    ["The {0} field is required.".format(field)]
                })
            response.status_code = 400
            return response

    for field in dataset_fields_under_255_characters:
        if field in data and len(data.get(field, '')) > 255:
            response = flask.jsonify(
                Message='Field too long',
                ModelState={
                    'model.' + field:
                    ["{0} field must be shorter than 255 characters."
                     .format(field)]
                })
            response.status_code = 400
            return response

    # All good, return a request id
    request_id = unicode(uuid.uuid4())
    if app.debug:
        app.logger.debug('Request id generated:\n{0}'.format(request_id))

    return flask.jsonify(
        RequestId=request_id
    )


def handle_file_request(organization_id, dataset_id):

    ec_api_error_msg = ('The request is invalid. Content of type ' +
                       'multipart/form-data is required. It must contain ' +
                       'file content and file metadata parts')

    if app.debug:
        app.logger.debug('Headers received:\n{0}'
                         .format(flask.request.headers))

    # Authorization

    if ('Authorization' not in flask.request.headers or
       flask.request.headers['Authorization'] == 'unknown_token'):
        response = flask.jsonify(
            Message='Not Auhtorized'
        )
        response.status_code = 401
        return response

    # Get metadata
    if len(flask.request.form):
        metadata_fields = flask.request.form.values()[0]
        try:
            metadata = json.loads(metadata_fields)
        except ValueError:
            response = flask.jsonify(
                Message=ec_api_error_msg
            )
            response.status_code = 400
            return response

    else:
        metadata = flask.request.json

    if app.debug:
        app.logger.debug('File metadata received:\n{0}'
                         .format(metadata))

    if not metadata.get('ExternalUrl'):
        # Check for files
        if not len(flask.request.files):
            response = flask.jsonify(
                Message=ec_api_error_msg
            )
            response.status_code = 400
            return response

        uploaded_file = flask.request.files.values()[0]
        if app.debug:
            app.logger.debug('File headers received:\n{0}'
                             .format(uploaded_file.headers))

        file_name = uploaded_file.filename

    for field in file_mandatory_fields:
        if not metadata.get(field):
            response = flask.jsonify(
                Message='Missing fields',
                ModelState={
                    'model.' + field:
                    ["The {0} field is required.".format(field)]
                })
            response.status_code = 400
            return response

    for field in file_fields_under_255_characters:
        if metadata.get(field) and len(metadata.get(field, '')) > 255:
            response = flask.jsonify(
                Message='Field too long',
                ModelState={
                    'model.' + field:
                    ["{0} field must be shorter than 255 characters."
                     .format(field)]
                })
            response.status_code = 400
            return response

    # All good, return a request id
    request_id = unicode(uuid.uuid4())
    if app.debug:
        app.logger.debug('Request id generated:\n{0}'.format(request_id))

    return flask.jsonify(
        RequestId=request_id
    )


@app.route('/')
def api_description():

    api_desc = {
        'Request dataset creation': 'POST /Datasets',
        'Request dataset update': 'PUT /Datasets',
        'Request file creation': 'POST /Files',
        'Request file update': 'PUT /Files',

    }

    return flask.jsonify(**api_desc)


def run(**kwargs):
    app.run(**kwargs)


if __name__ == '__main__':
    run(port=7070, debug=True)
