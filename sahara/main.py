# Copyright (c) 2013 Mirantis Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import eventlet
import flask
from keystoneclient.middleware import auth_token
from oslo.config import cfg
import six
import stevedore
from werkzeug import exceptions as werkzeug_exceptions

from sahara.api import v10 as api_v10
from sahara.api import v11 as api_v11
from sahara import context
from sahara.middleware import auth_valid
from sahara.middleware import log_exchange
from sahara.openstack.common import log
from sahara.plugins import base as plugins_base
from sahara.service import api as service_api
from sahara.service import periodic
from sahara.utils import api as api_utils
from sahara.utils import patches
from sahara.utils import remote


LOG = log.getLogger(__name__)

eventlet.monkey_patch(
    os=True, select=True, socket=True, thread=True, time=True)

# Patches minidom's writexml to avoid excess whitespaces in generated xml
# configuration files that brakes Hadoop.
patches.patch_minidom_writexml()

opts = [
    cfg.StrOpt('os_auth_protocol',
               default='http',
               help='Protocol used to access OpenStack Identity service.'),
    cfg.StrOpt('os_auth_host',
               default='127.0.0.1',
               help='IP or hostname of machine on which OpenStack Identity '
                    'service is located.'),
    cfg.StrOpt('os_auth_port',
               default='5000',
               help='Port of OpenStack Identity service.'),
    cfg.StrOpt('os_admin_username',
               default='admin',
               help='This OpenStack user is used to verify provided tokens. '
                    'The user must have admin role in <os_admin_tenant_name> '
                    'tenant.'),
    cfg.StrOpt('os_admin_password',
               default='nova',
               help='Password of the admin user.'),
    cfg.StrOpt('os_admin_tenant_name',
               default='admin',
               help='Name of tenant where the user is admin.'),
    cfg.StrOpt('infrastructure_engine',
               default='direct',
               help='An engine which will be used to provision '
                    'infrastructure for Hadoop cluster.'),
    cfg.StrOpt('remote',
               default='ssh',
               help='A method for Sahara to execute commands '
                    'on VMs.')
]

CONF = cfg.CONF
CONF.register_opts(opts)


def make_app():
    """App builder (wsgi)

    Entry point for Sahara REST API server
    """
    app = flask.Flask('sahara.api')

    @app.route('/', methods=['GET'])
    def version_list():
        context.set_ctx(None)
        return api_utils.render({
            "versions": [
                {"id": "v1.0", "status": "CURRENT"}
            ]
        })

    @app.teardown_request
    def teardown_request(_ex=None):
        context.set_ctx(None)

    app.register_blueprint(api_v10.rest, url_prefix='/v1.0')
    app.register_blueprint(api_v10.rest, url_prefix='/v1.1')
    app.register_blueprint(api_v11.rest, url_prefix='/v1.1')

    plugins_base.setup_plugins()
    periodic.setup(app)

    engine = _get_infrastructure_engine()
    service_api.setup_service_api(engine)

    remote_driver = _get_remote_driver()
    remote.setup_remote(remote_driver, engine)

    def make_json_error(ex):
        status_code = (ex.code
                       if isinstance(ex, werkzeug_exceptions.HTTPException)
                       else 500)
        description = (ex.description
                       if isinstance(ex, werkzeug_exceptions.HTTPException)
                       else str(ex))
        return api_utils.render({'error': status_code,
                                 'error_message': description},
                                status=status_code)

    for code in six.iterkeys(werkzeug_exceptions.default_exceptions):
        app.error_handler_spec[None][code] = make_json_error

    if CONF.debug and not CONF.log_exchange:
        LOG.debug('Logging of request/response exchange could be enabled using'
                  ' flag --log-exchange')

    if CONF.log_exchange:
        cfg = app.config
        app.wsgi_app = log_exchange.LogExchange.factory(cfg)(app.wsgi_app)

    app.wsgi_app = auth_valid.filter_factory(app.config)(app.wsgi_app)

    app.wsgi_app = auth_token.filter_factory(
        app.config,
        auth_host=CONF.os_auth_host,
        auth_port=CONF.os_auth_port,
        auth_protocol=CONF.os_auth_protocol,
        admin_user=CONF.os_admin_username,
        admin_password=CONF.os_admin_password,
        admin_tenant_name=CONF.os_admin_tenant_name
    )(app.wsgi_app)

    return app


def _get_infrastructure_engine():
    """That should import and return one of
    sahara.service.instances*.py modules
    """

    LOG.info("Loading '%s' infrastructure engine" %
             CONF.infrastructure_engine)

    extension_manager = stevedore.DriverManager(
        namespace='sahara.infrastructure.engine',
        name=CONF.infrastructure_engine,
        invoke_on_load=True
    )

    return extension_manager.driver


def _get_remote_driver():
    LOG.info("Loading '%s' remote" % CONF.remote)

    extension_manager = stevedore.DriverManager(
        namespace='sahara.remote',
        name=CONF.remote,
        invoke_on_load=True
    )

    return extension_manager.driver
