#!/bin/bash

set -o errexit

source $GRENADE_DIR/grenaderc
source $GRENADE_DIR/functions

source $TOP_DIR/openrc admin admin

set -o xtrace

SAHARA_USER=sahara_grenade
SAHARA_PROJECT=sahara_grenade
SAHARA_PASS=pass
SAHARA_SERVER=sahara_server1
SAHARA_KEY=sahara_key
SAHARA_KEY_FILE=$SAVE_DIR/sahara_key.pem

JSON_PATH=`dirname $BASH_SOURCE`
PUBLIC_NETWORK_NAME=${PUBLIC_NETWORK_NAME:-public}
PRIVATE_NETWORK_NAME=${PRIVATE_NETWORK_NAME:-private}
# cirros image is not appropriate for cluster creation
SAHARA_IMAGE_NAME=${SAHARA_IMAGE_NAME:-fedora-heat-test-image}
SAHARA_IMAGE_USER=${SAHARA_IMAGE_USER:-fedora}
# custom flavor parameters
SAHARA_FLAVOR_NAME=${SAHARA_FLAVOR_NAME:-sahara_flavor}
SAHARA_FLAVOR_RAM=${SAHARA_FLAVOR_RAM:-1024}
SAHARA_FLAVOR_DISK=${SAHARA_FLAVOR_DISK:-10}

function _sahara_set_user {
    OS_TENANT_NAME=$SAHARA_PROJECT
    OS_PROJECT_NAME=$SAHARA_PROJECT
    OS_USERNAME=$SAHARA_USER
    OS_PASSWORD=$SAHARA_PASS
}

function register_image {
    eval $(openstack --os-image-api-version 1 image show -f \
        shell -c id $SAHARA_IMAGE_NAME)
    resource_save sahara image_id $id
    sahara image-register --id $id --username $SAHARA_IMAGE_USER
    sahara image-add-tag --id $id --tag fake
    sahara image-add-tag --id $id --tag 0.1
    echo $id
}

# args: <template> <floating_ip_pool> <security_group> <flavor_id>
function create_node_group_template {
    local tmp_file
    tmp_file=$(mktemp)
    local floating_pool=$2
    if is_service_enabled neutron; then
        eval $(openstack network show $2 -f shell -c id)
        local floating_pool=$id
    fi

    sed -e "s/FLAVOR_ID/$4/g" \
        -e "s/FLOATING_IP_POOL/$floating_pool/g" \
        -e "s/SEC_GROUP/$3/g" $1 > $tmp_file
    local template_id
    template_id=$(sahara node-group-template-create --json "$tmp_file" \
                                            | awk '$2 ~ /^id/ { print $4 }')
    echo $template_id
}

# args: <template> <node_group_id>
function create_cluster_template {
    local tmp_file
    tmp_file=$(mktemp)
    sed -e "s/NG_ID/$2/g" $1 > $tmp_file
    local cluster_template_id
    cluster_template_id=$(sahara cluster-template-create --json $tmp_file \
                                            | awk '$2 ~ /^id/ { print $4 }')
    echo $cluster_template_id
}

# args: <template> <cluster_template_id> <keypair> <image_id>
function create_cluster {
    local tmp_file
    tmp_file=$(mktemp)
    sed -e "s/CLUSTER_TEMPLATE_ID/$2/g" \
        -e "s/KEYPAIR/$3/g" \
        -e "s/IMAGE_ID/$4/g" $1 > $tmp_file

    # adding neutron management network id if neutron is enabled
    local net_id
    net_id=$(resource_get network net_id)
    if [[ -n "$net_id" ]]; then
        sed -i '8i ,"neutron_management_network": "NET_ID"' $tmp_file
        sed -i -e "s/NET_ID/$net_id/g" $tmp_file
    fi

    local cluster_id
    cluster_id=$(sahara cluster-create --json $tmp_file \
                                            | awk '$2 ~ /^id/ { print $4 }')
    echo $cluster_id
}

function create {
    # create a tenant for the server
    eval $(openstack project create -f shell -c id $SAHARA_PROJECT)
    if [[ -z "$id" ]]; then
        die $LINENO "Didn't create $SAHARA_PROJECT project"
    fi
    resource_save sahara project_id $id

    # create the user, and set $id locally
    eval $(openstack user create $SAHARA_USER \
        --project $id \
        --password $SAHARA_PASS \
        -f shell -c id)
    if [[ -z "$id" ]]; then
        die $LINENO "Didn't create $SAHARA_USER user"
    fi
    resource_save sahara user_id $id

    # create flavor

    eval $(openstack flavor create -f shell -c id --ram $SAHARA_FLAVOR_RAM \
                            --disk $SAHARA_FLAVOR_DISK $SAHARA_FLAVOR_NAME)
    flavor_id=$id

    # register image
    image_id=$(register_image)

    # set ourselves to the created sahara user
    _sahara_set_user

    # create security group
    nova secgroup-create $SAHARA_USER "Sahara security group"
    nova secgroup-add-rule $SAHARA_USER tcp 22 22 0.0.0.0/0

    # create key pair for access
    openstack keypair create $SAHARA_KEY > $SAHARA_KEY_FILE
    chmod 600 $SAHARA_KEY_FILE

    # create node group template
    ng_id=$(create_node_group_template $JSON_PATH/ng-template.json \
                                $PUBLIC_NETWORK_NAME $SAHARA_USER $flavor_id)

    resource_save sahara ng_id $ng_id

    # create cluster template
    cluster_template_id=$(create_cluster_template \
                $JSON_PATH/cluster-template.json $ng_id)
    resource_save sahara cluster_template_id $cluster_template_id

    # create cluster
    cluster_id=$(create_cluster $JSON_PATH/cluster-create.json \
                                    $cluster_template_id $SAHARA_KEY $image_id)
    resource_save sahara cluster_id $cluster_id

    # wait until cluster moves to active state
    local timeleft=1000
    while [[ $timeleft -gt 0 ]]; do
        local cluster_state
        cluster_state=$(sahara cluster-show --id $cluster_id \
                                    | awk '$2 ~ /^status/ { print $4;exit }')
        if [[ "$cluster_state" != "Active" ]]; then
            if [[ "$cluster_state" == "Error" ]]; then
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

function verify {
    _sahara_set_user
    # check that cluster is in Active state
    local cluster_id
    cluster_id=$(resource_get sahara cluster_id)
    local cluster_state
    cluster_state=$(sahara cluster-show --id $cluster_id \
                                    | awk '$2 ~ /^status/ { print $4;exit }')
    echo -n $cluster_state
    if [[ "$cluster_state" != "Active" ]]; then
        die $LINENO "Cluster is not in Active state anymore"
    fi
    echo "Sahara verification: SUCCESS"
}

function verify_noapi {
    :
}

function destroy {
    _sahara_set_user
    set +o errexit

    # delete cluster
    local cluster_id
    cluster_id=$(resource_get sahara cluster_id)
    sahara cluster-delete --id $cluster_id > /dev/null
    # wait for cluster deletion
    local timeleft=500
    while [[ $timeleft -gt 0 ]]; do
        sahara cluster-show --id $cluster_id > /dev/null
        local rc=$?

        if [[ "$rc" != 1 ]]; then
            echo "Cluster still exists"
            sleep 5
            timeleft=$((timeleft - 5))
            if [[ $timeleft == 0 ]]; then
                die $LINENO "Cluster hasn't been deleted during 500 seconds"
            fi
        else
            break
        fi
    done

    set -o errexit

    # delete cluster template
    local cluster_template_id
    cluster_template_id=$(resource_get sahara cluster_template_id)
    sahara cluster-template-delete --id $cluster_template_id

    # delete node group template
    local ng_id
    ng_id=$(resource_get sahara ng_id)

    sahara node-group-template-delete --id $ng_id

    # delete security group
    nova secgroup-delete $SAHARA_USER

    source_quiet $TOP_DIR/openrc admin admin

    # unregister image
    local image_id
    image_id=$(resource_get sahara image_id)
    sahara image-unregister --id $image_id

    # delete flavor
    openstack flavor delete $SAHARA_FLAVOR_NAME

    # delete user and project
    local user_id
    user_id=$(resource_get sahara user_id)
    local project_id
    project_id=$(resource_get sahara project_id)
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
