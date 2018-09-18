#!/bin/bash

# ``shutdown-sahara``

set -o errexit

. $GRENADE_DIR/grenaderc
. $GRENADE_DIR/functions

# We need base DevStack functions for this
. $BASE_DEVSTACK_DIR/functions
. $BASE_DEVSTACK_DIR/stackrc # needed for status directory

. $BASE_DEVSTACK_DIR/lib/tls
. $BASE_DEVSTACK_DIR/lib/apache
. ${GITDIR[sahara]}/devstack/plugin.sh

set -o xtrace

export ENABLED_SERVICES+=,sahara-api,sahara-eng,
stop_sahara

# sanity check that service is actually down
ensure_services_stopped sahara-eng
