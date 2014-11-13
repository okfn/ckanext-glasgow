ckanext-glasgow
===============

[![Build Status](https://travis-ci.org/okfn/ckanext-glasgow.svg?branch=master)](https://travis-ci.org/okfn/ckanext-glasgow)

CKAN Extensions specific to Open Glasgow

## Install

There are Ansible scripts in the *deployment* folder to aid in the install. Once you
have the relevant access permissions set up against the relevant server, you can 
install all components by running eg:

    ansible-playbook deployment/dbserver.yml -i deployment/inventories/staging -u azureuser -s -vvvv

    ansible-playbook deployment/webserver.yml -i deployment/inventories/staging -u azureuser -s -vvvv

All configurations settings (including changing the default DB password) must be set
manually on the `/etc/ckan/default/production.ini` file following the next section guidance.

Afterwards run the commands on the "Instance setup / reset protocol", skiping the reset ones.

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


    ## Site Settings

    ckan.site_url = {host}


    ## Search Settings

    ckan.site_id = glasgow


    ## Plugins Settings

    ckan.plugins = stats text_preview recline_preview glasgow_schema glasgow_organizations glasgow_harvest ec_changelog_harvester ec_initial_harvester oauth2waad

    ckan.harvest.mq.type=redis

    # Local mock API
    #ckanext.glasgow.data_collection_api=http://localhost:7070
    #ckanext.glasgow.metadata_api=http://localhost:7070
    #ckanext.glasgow.identity_api=http://localhost:7070

    ckanext.glasgow.data_collection_api=https://datacollection.open.glasgow.gov.uk
    ckanext.glasgow.metadata_api=https://dataservices.open.glasgow.gov.uk
    ckanext.glasgow.identity_api=https://identity.open.glasgow.gov.uk


    # OAuth 2.0 WAAD settings
    ckanext.oauth2waad.client_id = ...
    ckanext.oauth2waad.redirect_uri = https://{host}/_waad_redirect_uri
    ckanext.oauth2waad.auth_endpoint = https://login.windows.net/open.glasgow.gov.uk/oauth2/authorize
    ckanext.oauth2waad.auth_token_endpoint = https://login.windows.net/open.glasgow.gov.uk/oauth2/token
    ckanext.oauth2waad.resource = http://GCCCTPECServicesPrep.cloudapp.net:8080/
    ckanext.oauth2waad.csrf_secret = ...

    ckanext.oauth2waad.servicetoservice.auth_token_endpoint = https://login.windows.net/open.glasgow.gov.uk/oauth2/token
    ckanext.oauth2waad.servicetoservice.client_id = ...
    ckanext.oauth2waad.servicetoservice.client_secret = ...
    ckanext.oauth2waad.servicetoservice.resource = http://GCCCTPECServicesPrep.cloudapp.net:60855/ http://GCCCTPECServicesPrep.cloudapp.net:8080/ http://GCCCTPECServicesPrep.cloudapp.net:8083/
    ckanext.oauth2waad.servicetoservice.resource_names = metadata data_collection identity

    ## Storage Settings

    ckan.storage_path = ...


## Instance setup / reset protocol

This will reset the CKAN database against the current state of the platform API. All commands are to be run as root.

This first section is only to be run when reseting an existing instance. If you are doing a first install, skip to the next one:

    # Stop Apache
    service apache2 stop

    # Stop harvester processes
    supervisorctl stop all

    # Update source (repeat for ckanext-oauth2waad if necessary)
    cd /usr/lib/ckan/default/src/ckanext-glasgow
    git pull

    # Clean DB
    ckan db clean

    # Clear serch index
    ckan search-index clear

    # Init DB
    ckan db init

    # Create OKFN sysadmin user
    /usr/lib/ckan/default/bin/paster --plugin=ckan sysadmin add okfn -c /etc/ckan/default/production.ini

    # Start harvester processes
    supervisorctl start all

Common steps for reseting and first install:


    # Create initial harvest source
    ckan --plugin=ckanext-harvest harvester source ec-initial-harvester url_initial ec_initial_harvester "EC Initial harvester" -c /etc/ckan/default/production.ini

    # Manually add a job for the initial harvester
    ckan --plugin=ckanext-harvest harvester job {source-id}

    # Force a run of the harvesters to run the previous job
    ckan --plugin=ckanext-harvest harvester run

    # Once it's finished, create the initial users
    ckan --plugin=ckanext-glasgow get_initial_users

    # Update the current audit id for the changelog harvester to the latest one
    ckan --plugin=ckanext-glasgow changelog_audit set

    # Create changelog harvest source
    ckan --plugin=ckanext-harvest harvester source ec-changelog-harvester url_changelog ec_changelog_harvester "EC Changelog harvester" True "" ALWAYS -c /etc/ckan/default/production.ini

    # Offline tests
    ckan dataset list
    ckan user list

    # Start Apache
    service apache2 start

    # Online user tests
