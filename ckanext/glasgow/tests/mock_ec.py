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


@app.route('/Datasets/Organisation/<int:organization_id>', methods=['POST'])
def request_dataset_create(organization_id):

    return handle_dataset_request(organization_id)


@app.route('/Datasets/Organisation/<int:organization_id>', methods=['PUT'])
def request_dataset_update(organization_id):

    return handle_dataset_request(organization_id)


@app.route('/Files/Organisation/<int:organization_id>/Dataset/<int:dataset_id>', methods=['POST'])
def request_file_create(organization_id, dataset_id):

    return handle_file_request(organization_id, dataset_id)


@app.route('/Files/Organisation/<int:organization_id>/Dataset/<int:dataset_id>', methods=['PUT'])
def request_file_update(organization_id, dataset_id):

    return handle_file_request(organization_id, dataset_id)


def handle_dataset_request(organization_id):
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
        if not data.get(field):
            response = flask.jsonify(
                Message='Missing fields',
                ModelState={
                    'model.' + field:
                    ["The {0} field is required.".format(field)]
                })
            response.status_code = 400
            return response

    for field in dataset_fields_under_255_characters:
        if data.get(field) and len(data.get(field, '')) > 255:
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

    # Check for files
    if not len(flask.request.files):
        response = flask.jsonify(
            # TODO: use actual message
            Message='File Missing'
        )
        response.status_code = 400
        return response

    uploaded_file = flask.request.files.values()[0]
    if app.debug:
        app.logger.debug('File headers received:\n{0}'
                         .format(uploaded_file.headers))

    file_name = uploaded_file.filename

    if not len(flask.request.form):
        response = flask.jsonify(
            # TODO: use actual message
            Message='Metadata Missing'
        )
        response.status_code = 400
        return response

    metadata_fields = flask.request.form.values()[0]

    try:
        metadata = json.loads(metadata_fields)
    except ValueError:
        response = flask.jsonify(
            # TODO: use actual message
            Message='Wrong File Metadata'
        )
        response.status_code = 400
        return response
    if app.debug:
        app.logger.debug('File metadata received:\n{0}'
                         .format(metadata))

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
