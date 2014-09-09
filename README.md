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


## Instance reset protocol

This will reset the CKAN database against the current state of the platform API. All commands are to be run as root.

    # Stop Apache
    service apache2 stop

    # Stop harvester processes
    supervisorctl stop all

    # Update source (repeat for ckanext-oauth2waad if necessary)
    cd /usr/lib/ckan/default/src/ckanext-glasgow
    git pull

    # Clean DB
    ckan db clean

    # Clean serch index
    ckan search-index clean

    # Init DB
    ckan db init

    # Start harvester processes
    supervisorctl start all

    # Create harvest sources
    /usr/lib/ckan/default/src/ckanext-glasgow/bin/create_ckan_harvest_sources

    # Manually add a job for the initial harvester
    ckan --plugin=ckanext-harvest harvester job {source-id}

    # Force a run of the harvesters to run the previous job
    ckan --plugin=ckanext-harvest harvester run

    # Once it's finished, create the initial users
    ckan --plugin=ckanext-glasgow get_initial_users

    # Update the changelog harvester to have a frequency of ALWAYS
    # TODO: can we script this?
    https://ckanfrontend.cloudapp.net/harvest/edit/ec-changelog-harvester

    # Update the current audit id for the changelog harvester to the latest one
    ckan --plugin=ckanext-glasgow changelog_audit set

    # Offline tests
    ckan dataset list
    ckan user list

    # Start Apache
    service apache2 start

    # Online user tests
