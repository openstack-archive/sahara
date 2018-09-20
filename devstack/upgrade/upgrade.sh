#!/usr/bin/env bash

# ``upgrade-sahara``

echo "*********************************************************************"
echo "Begin $0"
echo "*********************************************************************"

# Clean up any resources that may be in use
cleanup() {
    set +o errexit

    echo "********************************************************************"
    echo "ERROR: Abort $0"
    echo "********************************************************************"

    # Kill ourselves to signal any calling process
    trap 2; kill -2 $$
}

trap cleanup SIGHUP SIGINT SIGTERM

# Keep track of the grenade directory
RUN_DIR=$(cd $(dirname "$0") && pwd)

# Source params
. $GRENADE_DIR/grenaderc

# Import common functions
. $GRENADE_DIR/functions

# This script exits on an error so that errors don't compound and you see
# only the first error that occurred.
set -o errexit

# Upgrade Sahara
# ============

# Get functions from current DevStack
. $TARGET_DEVSTACK_DIR/stackrc
. $TARGET_DEVSTACK_DIR/lib/apache
. $TARGET_DEVSTACK_DIR/lib/tls
. $(dirname $(dirname $BASH_SOURCE))/plugin.sh
. $(dirname $(dirname $BASH_SOURCE))/settings

# Print the commands being run so that we can see the command that triggers
# an error.  It is also useful for following allowing as the install occurs.
set -o xtrace

# Save current config files for posterity
[[ -d $SAVE_DIR/etc.sahara ]] || cp -pr $SAHARA_CONF_DIR $SAVE_DIR/etc.sahara

# install_sahara()
stack_install_service sahara
install_python_saharaclient

# calls upgrade-sahara for specific release
upgrade_project sahara $RUN_DIR $BASE_DEVSTACK_BRANCH $TARGET_DEVSTACK_BRANCH

# Migrate the database
$SAHARA_BIN_DIR/sahara-db-manage --config-file $SAHARA_CONF_FILE \
                                    upgrade head || die $LINENO "DB sync error"

# Start Sahara
start_sahara

# Don't succeed unless the service come up
ensure_services_started sahara-eng

set +o xtrace
echo "*********************************************************************"
echo "SUCCESS: End $0"
echo "*********************************************************************"
