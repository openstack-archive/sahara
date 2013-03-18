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

import logging

from eventlet import monkey_patch
from flask import Flask
from keystoneclient.middleware.auth_token import filter_factory as auth_token
from oslo.config import cfg
from werkzeug.exceptions import default_exceptions
from werkzeug.exceptions import HTTPException
from eho.api import v02 as api_v02

from eho.middleware.auth_valid import filter_factory as auth_valid
from eho.utils.scheduler import setup_scheduler
from eho.storage.defaults import setup_defaults
from eho.utils.api import render
from eho.storage.storage import setup_storage


monkey_patch(os=True, select=True, socket=True, thread=True, time=True)

opts = [
    cfg.StrOpt('os_auth_protocol',
               default='http',
               help='Protocol used to access OpenStack Identity service'),
    cfg.StrOpt('os_auth_host',
               default='openstack',
               help='IP or hostname of machine on which OpenStack Identity '
                    'service is located'),
    cfg.StrOpt('os_auth_port',
               default='35357',
               help='Port of OpenStack Identity service'),
    cfg.StrOpt('os_admin_username',
               default='admin',
               help='This OpenStack user is used to verify provided tokens. '
                    'The user must have admin role in <os_admin_tenant_name> '
                    'tenant'),
    cfg.StrOpt('os_admin_password',
               default='nova',
               help='Password of the admin user'),
    cfg.StrOpt('os_admin_tenant_name',
               default='admin',
               help='Name of tenant where the user is admin'),
    cfg.StrOpt('nova_internal_net_name',
               default='novanetwork',
               help='Name of network which IPs are given to the VMs')
]

sqlalchemy_opts = [
    cfg.StrOpt('database_uri',
               default='sqlite:////tmp/eho-server.db',
               help='URL for sqlalchemy database'),
    cfg.BoolOpt('echo',
                default=False,
                help='Sqlalchemy echo')
]

CONF = cfg.CONF
CONF.register_opts(opts)
CONF.register_opts(sqlalchemy_opts, group='sqlalchemy')
CONF.import_opt('log_level', 'eho.config')


def make_app():
    """
    Entry point for Elastic Hadoop on OpenStack REST API server
    """
    app = Flask('eho.api')

    app.config['SQLALCHEMY_DATABASE_URI'] = CONF.sqlalchemy.database_uri
    app.config['SQLALCHEMY_ECHO'] = CONF.sqlalchemy.echo

    root_logger = logging.getLogger()
    root_logger.setLevel(CONF.log_level)

    app.register_blueprint(api_v02.rest, url_prefix='/v0.2')

    setup_storage(app)
    setup_defaults(app)
    setup_scheduler(app)

    def make_json_error(ex):
        status_code = (ex.code
                       if isinstance(ex, HTTPException)
                       else 500)
        description = (ex.description
                       if isinstance(ex, HTTPException)
                       else str(ex))
        return render({'error': status_code, 'error_message': description},
                      status=status_code)

    for code in default_exceptions.iterkeys():
        app.error_handler_spec[None][code] = make_json_error

    app.wsgi_app = auth_valid(app.config)(app.wsgi_app)

    app.wsgi_app = auth_token(
        app.config,
        auth_host=CONF.os_auth_host,
        auth_port=CONF.os_auth_port,
        auth_protocol=CONF.os_auth_protocol,
        admin_user=CONF.os_admin_username,
        admin_password=CONF.os_admin_password,
        admin_tenant=CONF.os_admin_tenant_name
    )(app.wsgi_app)

    return app
