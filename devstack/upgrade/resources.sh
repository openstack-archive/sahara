#!/bin/bash

set -o errexit

. $GRENADE_DIR/grenaderc
. $GRENADE_DIR/functions

. $TOP_DIR/openrc admin admin

set -o xtrace

SAHARA_USER=sahara_grenade
SAHARA_PROJECT=sahara_grenade
SAHARA_PASS=pass
SAHARA_KEY=sahara_key
SAHARA_KEY_FILE=$SAVE_DIR/sahara_key.pem

PUBLIC_NETWORK_NAME=${PUBLIC_NETWORK_NAME:-public}

# cirros image is not appropriate for cluster creation
SAHARA_IMAGE_NAME=${SAHARA_IMAGE_NAME:-fedora-heat-test-image}
SAHARA_IMAGE_USER=${SAHARA_IMAGE_USER:-fedora}

# custom flavor parameters
SAHARA_FLAVOR_NAME=${SAHARA_FLAVOR_NAME:-sahara_flavor}
SAHARA_FLAVOR_RAM=${SAHARA_FLAVOR_RAM:-1024}
SAHARA_FLAVOR_DISK=${SAHARA_FLAVOR_DISK:-10}

NG_TEMPLATE_NAME=ng-template-grenade
CLUSTER_TEMPLATE_NAME=cluster-template-grenade
CLUSTER_NAME=cluster-grenade

function sahara_set_user {
    # set ourselves to the created sahara user
    OS_TENANT_NAME=$SAHARA_PROJECT
    OS_PROJECT_NAME=$SAHARA_PROJECT
    OS_USERNAME=$SAHARA_USER
    OS_PASSWORD=$SAHARA_PASS
}

function create_tenant {
    # create a tenant for the server
    eval $(openstack project create -f shell -c id $SAHARA_PROJECT)
    if [[ -z "$id" ]]; then
        die $LINENO "Didn't create $SAHARA_PROJECT project"
    fi
    resource_save sahara project_id $id
}

function create_user {
    local project_id=$id
    eval $(openstack user create $SAHARA_USER \
        --project $project_id \
        --password $SAHARA_PASS \
        -f shell -c id)
    if [[ -z "$id" ]]; then
        die $LINENO "Didn't create $SAHARA_USER user"
    fi
    resource_save sahara user_id $id

    # Workaround for bug: https://bugs.launchpad.net/keystone/+bug/1662911
    openstack role add member --user $id --project $project_id
}

function create_keypair {
    # create key pair for access
    openstack keypair create $SAHARA_KEY > $SAHARA_KEY_FILE
    chmod 600 $SAHARA_KEY_FILE
}

function create_flavor {
    eval $(openstack flavor create -f shell -c id \
            --ram $SAHARA_FLAVOR_RAM \
            --disk $SAHARA_FLAVOR_DISK \
            $SAHARA_FLAVOR_NAME)
    resource_save sahara flavor_id $id
}

function register_image {
    eval $(openstack image show \
            -f shell -c id $SAHARA_IMAGE_NAME)
    resource_save sahara image_id $id
    openstack dataprocessing image register $id --username $SAHARA_IMAGE_USER
    openstack dataprocessing image tags set $id --tags fake 0.1
}

function create_node_group_template {
    eval $(openstack network show -f shell -c id $PUBLIC_NETWORK_NAME)
    local public_net_id=$id
    local flavor_id=$(resource_get sahara flavor_id)
    openstack dataprocessing node group template create \
        --name $NG_TEMPLATE_NAME \
        --flavor $flavor_id \
        --plugin fake \
        --plugin-version 0.1 \
        --processes jobtracker namenode tasktracker datanode \
        --floating-ip-pool $public_net_id \
        --auto-security-group
}

function create_cluster_template {
    openstack dataprocessing cluster template create \
        --name $CLUSTER_TEMPLATE_NAME \
        --node-groups $NG_TEMPLATE_NAME:1
}

function create_cluster {
    local net_id=$(resource_get network net_id)
    local image_id=$(resource_get sahara image_id)
    if [[ -n "$net_id" ]]; then
        eval $(openstack dataprocessing cluster create \
                --name $CLUSTER_NAME \
                --cluster-template $CLUSTER_TEMPLATE_NAME \
                --image $image_id \
                --user-keypair $SAHARA_KEY \
                --neutron-network $net_id \
                -f shell -c id)
    else
        eval $(openstack dataprocessing cluster create \
                --name $CLUSTER_NAME \
                --cluster-template $CLUSTER_TEMPLATE_NAME \
                --image $image_id \
                --user-keypair $SAHARA_KEY \
                -f shell -c id)
    fi
    resource_save sahara cluster_id $id
}

function wait_active_state {
    # wait until cluster moves to active state
    local timeleft=1000
    while [[ $timeleft -gt 0 ]]; do
        eval $(openstack dataprocessing cluster show -f shell \
                -c Status $CLUSTER_NAME)
        if [[ "$status" != "Active" ]]; then
            if [[ "$status" == "Error" ]]; then
                die $LINENO "Cluster is in Error state"
            fi
            echo "Cluster is still not in Active state"
            sleep 10
            timeleft=$((timeleft - 10))
            if [[ $timeleft == 0 ]]; then
                die $LINENO "Cluster hasn't moved to Active state \
                                                        during 1000 seconds"
            fi
        else
            break
        fi
    done
}

function check_active {
    # check that cluster is in Active state
    eval $(openstack dataprocessing cluster show -f shell \
            -c Status $CLUSTER_NAME)
    if [[ "$status" != "Active" ]]; then
        die $LINENO "Cluster is not in Active state anymore"
    fi
    echo "Sahara verification: SUCCESS"
}

function create {
    create_tenant

    create_user

    create_flavor

    register_image

    sahara_set_user

    create_keypair

    create_node_group_template

    create_cluster_template

    create_cluster

    wait_active_state
}

function verify {
    :
}

function verify_noapi {
    :
}

function destroy {
    sahara_set_user
    set +o errexit

    # delete cluster
    check_active

    openstack dataprocessing cluster delete $CLUSTER_NAME --wait

    set -o errexit

    # delete cluster template
    openstack dataprocessing cluster template delete $CLUSTER_TEMPLATE_NAME

    # delete node group template
    openstack dataprocessing node group template delete $NG_TEMPLATE_NAME

    source_quiet $TOP_DIR/openrc admin admin

    # unregister image
    local image_id=$(resource_get sahara image_id)
    openstack dataprocessing image unregister $image_id

    # delete flavor
    openstack flavor delete $SAHARA_FLAVOR_NAME

    # delete user and project
    local user_id=$(resource_get sahara user_id)
    local project_id=$(resource_get sahara project_id)
    openstack user delete $user_id
    openstack project delete $project_id
}

# Dispatcher
case $1 in
    "create")
        create
        ;;
    "verify_noapi")
        verify_noapi
        ;;
    "verify")
        verify
        ;;
    "destroy")
        destroy
        ;;
    "force_destroy")
        set +o errexit
        destroy
        ;;
esac
