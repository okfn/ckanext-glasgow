ckanext-glasgow
===============

[![Build Status](https://travis-ci.org/okfn/ckanext-glasgow.svg?branch=master)](https://travis-ci.org/okfn/ckanext-glasgow)

CKAN Extensions specific to Open Glasgow


## Configuration options

    ## Authorization Settings

    ckan.auth.anon_create_dataset = false
    ckan.auth.create_unowned_dataset = false
    ckan.auth.create_dataset_if_not_in_organization = false
    ckan.auth.user_create_groups = true
    ckan.auth.user_create_organizations = true
    ckan.auth.user_delete_groups = true
    ckan.auth.user_delete_organizations = true
    ckan.auth.create_user_via_api = false
    ckan.auth.create_user_via_web = true
    ckan.auth.roles_that_cascade_to_sub_groups = admin


    ## Search Settings

    ckan.site_id = glasgow


    ## Plugins Settings

    ckan.plugins = stats text_preview recline_preview glasgow_schema glasgow_harvest ec_changelog_harvester ec_initial_harvester oauth2waad

    # Local mock API
    #ckanext.glasgow.data_collection_api=http://localhost:7070
    #ckanext.glasgow.metadata_api=http://localhost:7070

    ckanext.glasgow.data_collection_api=https://gccctpecdatacollectionservicesint.cloudapp.net/
    ckanext.glasgow.metadata_api=https://gccctpecmetadataservicesint.cloudapp.net/
    ckanext.glasgow.identity_api=https://gccctpecidentityservicesINT.cloudapp.net/


    # OAuth 2.0 WAAD settings
    ckanext.oauth2waad.client_id = ...
    ckanext.oauth2waad.redirect_uri = https://localhost:5000/_waad_redirect_uri
    ckanext.oauth2waad.auth_endpoint = https://login.windows.net/common/oauth2/authorize
    ckanext.oauth2waad.auth_token_endpoint = https://login.windows.net/common/oauth2/token
    ckanext.oauth2waad.resource = http://GCCCTPECServicesINT.cloudapp.net:8080/
    ckanext.oauth2waad.csrf_secret = ...
    ckanext.oauth2waad.servicetoservice.auth_token_endpoint = https://login.windows.net/gccctpecadint.onmicrosoft.com/oauth2/token
    ckanext.oauth2waad.servicetoservice.client_id = ...
    ckanext.oauth2waad.servicetoservice.client_secret =
    ckanext.oauth2waad.servicetoservice.resource = http://GCCCTPECServicesINT.cloudapp.net:60855/ http://GCCCTPECServicesINT.cloudapp.net:8080/ http://GCCCTPECServicesINT.cloudapp.net:8083/
    ckanext.oauth2waad.servicetoservice.resource_names = metadata data_collection identity

    ## Storage Settings

    ckan.storage_path = ...
