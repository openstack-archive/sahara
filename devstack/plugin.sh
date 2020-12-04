#!/bin/bash
#
# lib/sahara

# Dependencies:
# ``functions`` file
# ``DEST``, ``DATA_DIR``, ``STACK_USER`` must be defined

# ``stack.sh`` calls the entry points in this order:
#
# install_sahara
# install_python_saharaclient
# configure_sahara
# start_sahara
# stop_sahara
# cleanup_sahara

# Save trace setting
XTRACE=$(set +o | grep xtrace)
set -o xtrace


# Functions
# ---------

# create_sahara_accounts() - Set up common required sahara accounts
#
# Tenant      User       Roles
# ------------------------------
# service     sahara    admin
function create_sahara_accounts {

    create_service_user "sahara"

    get_or_create_service "sahara" "data-processing" "Sahara Data Processing"
    get_or_create_endpoint "data-processing" \
        "$REGION_NAME" \
        "$SAHARA_SERVICE_PROTOCOL://$SAHARA_SERVICE_HOST:$SAHARA_SERVICE_PORT" \
        "$SAHARA_SERVICE_PROTOCOL://$SAHARA_SERVICE_HOST:$SAHARA_SERVICE_PORT" \
        "$SAHARA_SERVICE_PROTOCOL://$SAHARA_SERVICE_HOST:$SAHARA_SERVICE_PORT"
}

# cleanup_sahara() - Remove residual data files, anything left over from
# previous runs that would need to clean up.
function cleanup_sahara {

    # Cleanup auth cache dir
    if [ "$SAHARA_USE_MOD_WSGI" == "True" ]; then
        sudo rm -f $(apache_site_config_for sahara-api)
    fi
}

function configure_sahara_apache_wsgi {

    local sahara_apache_conf=$(apache_site_config_for sahara-api)
    local sahara_ssl=""
    local sahara_certfile=""
    local sahara_keyfile=""
    local venv_path=""

    if is_ssl_enabled_service sahara; then
        sahara_ssl="SSLEngine On"
        sahara_certfile="SSLCertificateFile $SAHARA_SSL_CERT"
        sahara_keyfile="SSLCertificateKeyFile $SAHARA_SSL_KEY"
    fi

    sudo cp $SAHARA_DIR/devstack/files/apache-sahara-api.template $sahara_apache_conf
    sudo sed -e "
        s|%PUBLICPORT%|$SAHARA_SERVICE_PORT|g;
        s|%APACHE_NAME%|$APACHE_NAME|g;
        s|%SAHARA_BIN_DIR%|$SAHARA_BIN_DIR|g;
        s|%SSLENGINE%|$sahara_ssl|g;
        s|%SSLCERTFILE%|$sahara_certfile|g;
        s|%SSLKEYFILE%|$sahara_keyfile|g;
        s|%USER%|$STACK_USER|g;
        s|%VIRTUALENV%|$venv_path|g
    " -i $sahara_apache_conf

}

# configure_sahara() - Set config files, create data dirs, etc
function configure_sahara {
    sudo install -d -o $STACK_USER $SAHARA_CONF_DIR

    cp -p $SAHARA_DIR/etc/sahara/api-paste.ini $SAHARA_CONF_DIR

    configure_keystone_authtoken_middleware $SAHARA_CONF_FILE sahara

    # Set admin user parameters needed for trusts creation
    iniset $SAHARA_CONF_FILE \
        trustee project_name $SERVICE_TENANT_NAME
    iniset $SAHARA_CONF_FILE trustee username sahara
    iniset $SAHARA_CONF_FILE \
        trustee password $SERVICE_PASSWORD
    iniset $SAHARA_CONF_FILE \
        trustee user_domain_name "$SERVICE_DOMAIN_NAME"
    iniset $SAHARA_CONF_FILE \
        trustee project_domain_name "$SERVICE_DOMAIN_NAME"
    iniset $SAHARA_CONF_FILE \
        trustee auth_url "$KEYSTONE_SERVICE_URI/v3"

    iniset_rpc_backend sahara $SAHARA_CONF_FILE DEFAULT

    # Set configuration to send notifications

    if is_service_enabled ceilometer; then
        iniset $SAHARA_CONF_FILE oslo_messaging_notifications driver "messaging"
    fi

    iniset $SAHARA_CONF_FILE DEFAULT debug $ENABLE_DEBUG_LOG_LEVEL

    iniset $SAHARA_CONF_FILE DEFAULT plugins $SAHARA_ENABLED_PLUGINS

    iniset $SAHARA_CONF_FILE \
        database connection `database_connection_url sahara`

    if is_service_enabled neutron; then
        iniset $SAHARA_CONF_FILE neutron endpoint_type $SAHARA_ENDPOINT_TYPE
        if is_ssl_enabled_service "neutron" \
            || is_service_enabled tls-proxy; then
            iniset $SAHARA_CONF_FILE neutron ca_file $SSL_BUNDLE_FILE
        fi
    fi

    if is_ssl_enabled_service "heat" || is_service_enabled tls-proxy; then
        iniset $SAHARA_CONF_FILE heat ca_file $SSL_BUNDLE_FILE
    fi
    iniset $SAHARA_CONF_FILE heat endpoint_type $SAHARA_ENDPOINT_TYPE

    if is_ssl_enabled_service "cinder" || is_service_enabled tls-proxy; then
        iniset $SAHARA_CONF_FILE cinder ca_file $SSL_BUNDLE_FILE
    fi
    iniset $SAHARA_CONF_FILE cinder endpoint_type $SAHARA_ENDPOINT_TYPE

    if is_ssl_enabled_service "nova" || is_service_enabled tls-proxy; then
        iniset $SAHARA_CONF_FILE nova ca_file $SSL_BUNDLE_FILE
    fi
    iniset $SAHARA_CONF_FILE nova endpoint_type $SAHARA_ENDPOINT_TYPE

    if is_ssl_enabled_service "swift" || is_service_enabled tls-proxy; then
        iniset $SAHARA_CONF_FILE swift ca_file $SSL_BUNDLE_FILE
    fi
    iniset $SAHARA_CONF_FILE swift endpoint_type $SAHARA_ENDPOINT_TYPE

    if is_ssl_enabled_service "key" || is_service_enabled tls-proxy; then
        iniset $SAHARA_CONF_FILE keystone ca_file $SSL_BUNDLE_FILE
    fi
    iniset $SAHARA_CONF_FILE keystone endpoint_type $SAHARA_ENDPOINT_TYPE

    if is_ssl_enabled_service "glance" || is_service_enabled tls-proxy; then
        iniset $SAHARA_CONF_FILE glance ca_file $SSL_BUNDLE_FILE
    fi
    iniset $SAHARA_CONF_FILE glance endpoint_type $SAHARA_ENDPOINT_TYPE

    # Register SSL certificates if provided
    if is_ssl_enabled_service sahara; then
        ensure_certificates SAHARA

        iniset $SAHARA_CONF_FILE ssl cert_file "$SAHARA_SSL_CERT"
        iniset $SAHARA_CONF_FILE ssl key_file "$SAHARA_SSL_KEY"
    fi

    iniset $SAHARA_CONF_FILE DEFAULT use_syslog $SYSLOG

    # Format logging
    if [ "$LOG_COLOR" == "True" ] && [ "$SYSLOG" == "False" ]; then
        if [ "$SAHARA_USE_MOD_WSGI" == "False" ]; then
            setup_colorized_logging $SAHARA_CONF_FILE DEFAULT
        fi
    fi

    if is_service_enabled tls-proxy; then
        # Set the service port for a proxy to take the original
        iniset $SAHARA_CONF_FILE DEFAULT port $SAHARA_SERVICE_PORT_INT
    fi

    if [ "$SAHARA_ENABLE_DISTRIBUTED_PERIODICS" == "True" ]; then
        # Enable distributed periodic tasks
        iniset $SAHARA_CONF_FILE DEFAULT periodic_coordinator_backend_url\
            $SAHARA_PERIODIC_COORDINATOR_URL
        pip_install tooz[memcached]

        restart_service memcached
    fi

    recreate_database sahara
    $SAHARA_BIN_DIR/sahara-db-manage \
        --config-file $SAHARA_CONF_FILE upgrade head

    if [ "$SAHARA_USE_MOD_WSGI" == "True" ]; then
        configure_sahara_apache_wsgi
    fi
}

# install_sahara() - Collect source and prepare
function install_sahara {
    setup_develop $SAHARA_DIR
    if [ "$SAHARA_USE_MOD_WSGI" == "True" ]; then
        install_apache_wsgi
    fi
}

# install_ambari() - Collect source and prepare
function install_ambari {
    git_clone $AMBARI_PLUGIN_REPO $AMBARI_PLUGIN_DIR $AMBARI_PLUGIN_BRANCH
    setup_develop $AMBARI_PLUGIN_DIR
}

# install_cdh() - Collect source and prepare
function install_cdh {
    git_clone $CDH_PLUGIN_REPO $CDH_PLUGIN_DIR $CDH_PLUGIN_BRANCH
    setup_develop $CDH_PLUGIN_DIR
}

# install_mapr() - Collect source and prepare
function install_mapr {
    git_clone $MAPR_PLUGIN_REPO $MAPR_PLUGIN_DIR $MAPR_PLUGIN_BRANCH
    setup_develop $MAPR_PLUGIN_DIR
}

# install_spark() - Collect source and prepare
function install_spark {
    git_clone $SPARK_PLUGIN_REPO $SPARK_PLUGIN_DIR $SPARK_PLUGIN_BRANCH
    setup_develop $SPARK_PLUGIN_DIR
}

# install_storm() - Collect source and prepare
function install_storm {
    git_clone $STORM_PLUGIN_REPO $STORM_PLUGIN_DIR $STORM_PLUGIN_BRANCH
    setup_develop $STORM_PLUGIN_DIR
}

# install_vanilla() - Collect source and prepare
function install_vanilla {
    git_clone $VANILLA_PLUGIN_REPO $VANILLA_PLUGIN_DIR $VANILLA_PLUGIN_BRANCH
    setup_develop $VANILLA_PLUGIN_DIR
}

# install_python_saharaclient() - Collect source and prepare
function install_python_saharaclient {
    if use_library_from_git "python-saharaclient"; then
        git_clone $SAHARACLIENT_REPO $SAHARACLIENT_DIR $SAHARACLIENT_BRANCH
        setup_develop $SAHARACLIENT_DIR
    fi
}

# start_sahara() - Start running processes, including screen
function start_sahara {
    local service_port=$SAHARA_SERVICE_PORT
    local service_protocol=$SAHARA_SERVICE_PROTOCOL
    if is_service_enabled tls-proxy; then
        service_port=$SAHARA_SERVICE_PORT_INT
        service_protocol="http"
    fi

    if [ "$SAHARA_USE_MOD_WSGI" == "True" ] ; then
        enable_apache_site sahara-api
        restart_apache_server
    else
        run_process sahara-api "$SAHARA_BIN_DIR/sahara-api \
            --config-file $SAHARA_CONF_FILE"
    fi

    run_process sahara-eng "$SAHARA_BIN_DIR/sahara-engine \
        --config-file $SAHARA_CONF_FILE"

    echo "Waiting for Sahara to start..."
    if ! wait_for_service $SERVICE_TIMEOUT \
                $service_protocol://$SAHARA_SERVICE_HOST:$service_port; then
        die $LINENO "Sahara did not start"
    fi

    # Start proxies if enabled
    if is_service_enabled tls-proxy; then
        start_tls_proxy '*' $SAHARA_SERVICE_PORT \
                            $SAHARA_SERVICE_HOST \
                            $SAHARA_SERVICE_PORT_INT &
    fi
}

# configure_tempest_for_sahara() - Tune Tempest configuration for Sahara
function configure_tempest_for_sahara {
    if is_service_enabled tempest; then
        iniset $TEMPEST_CONFIG service_available sahara True
        iniset $TEMPEST_CONFIG data-processing-feature-enabled plugins $SAHARA_INSTALLED_PLUGINS
    fi
}

# stop_sahara() - Stop running processes
function stop_sahara {
    # Kill the Sahara screen windows
    if [ "$SAHARA_USE_MOD_WSGI" == "True" ]; then
        disable_apache_site sahara-api
        restart_apache_server
    else
        stop_process sahara-all
        stop_process sahara-api
        stop_process sahara-eng
    fi
}

# is_sahara_enabled. This allows is_service_enabled sahara work
# correctly throughout devstack.
function is_sahara_enabled {
    if is_service_enabled sahara-api || \
        is_service_enabled sahara-eng; then
        return 0
    else
        return 1
    fi
}

function is_plugin_required {
    if [ "${SAHARA_INSTALLED_PLUGINS/$1}" = "$SAHARA_INSTALLED_PLUGINS" ] ; then
        return 1
    else
        return 0
    fi
}

# Dispatcher for Sahara plugin
if is_service_enabled sahara; then
    if [[ "$1" == "stack" && "$2" == "install" ]]; then
        echo_summary "Installing sahara"
        install_sahara
        if is_plugin_required ambari; then
            install_ambari
        fi
        if is_plugin_required cdh; then
            install_cdh
        fi
        if is_plugin_required mapr; then
            install_mapr
        fi
        if is_plugin_required spark; then
            install_spark
        fi
        if is_plugin_required storm; then
            install_storm
        fi
        if is_plugin_required vanilla; then
            install_vanilla
        fi
        install_python_saharaclient
        cleanup_sahara
    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        echo_summary "Configuring sahara"
        configure_sahara
        create_sahara_accounts
    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        echo_summary "Initializing sahara"
        start_sahara
    elif [[ "$1" == "stack" && "$2" == "test-config" ]]; then
        echo_summary "Configuring tempest"
        configure_tempest_for_sahara
    fi

    if [[ "$1" == "unstack" ]]; then
        stop_sahara
    fi

    if [[ "$1" == "clean" ]]; then
        cleanup_sahara
    fi
fi


# Restore xtrace
$XTRACE

# Local variables:
# mode: shell-script
# End:
