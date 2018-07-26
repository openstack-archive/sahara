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

import contextlib
import os

from oslo_config import cfg
from oslo_log import log
from oslo_service import service as oslo_service
from oslo_service import sslutils
from oslo_service import wsgi as oslo_wsgi
import stevedore

from sahara.api import acl
from sahara.common import config as common_config
from sahara import config
from sahara import context
from sahara.plugins import base as plugins_base
from sahara.service import api
from sahara.service.castellan import config as castellan
from sahara.service.edp.data_sources import manager as ds_manager
from sahara.service.edp.job_binaries import manager as jb_manager
from sahara.service import ops as service_ops
from sahara.service import periodic
from sahara.utils.openstack import cinder
from sahara.utils.openstack import keystone
from sahara.utils import remote
from sahara.utils import rpc as messaging

LOG = log.getLogger(__name__)


opts = [
    cfg.StrOpt('os_region_name',
               help='Region name used to get services endpoints.'),
    cfg.StrOpt('remote',
               default='ssh',
               help='A method for Sahara to execute commands '
                    'on VMs.'),
    cfg.IntOpt('api_workers', default=1,
               help="Number of workers for Sahara API service (0 means "
                    "all-in-one-thread configuration)."),
]

INFRASTRUCTURE_ENGINE = 'heat'
CONF = cfg.CONF
CONF.register_opts(opts)


class SaharaWSGIService(oslo_wsgi.Server):
    def __init__(self, service_name, app):
        super(SaharaWSGIService, self).__init__(
            CONF, service_name, app, host=CONF.host, port=CONF.port,
            use_ssl=sslutils.is_enabled(CONF))


def setup_common(possible_topdir, service_name):
    dev_conf = os.path.join(possible_topdir,
                            'etc',
                            'sahara',
                            'sahara.conf')
    config_files = None
    if os.path.exists(dev_conf):
        config_files = [dev_conf]

    config.parse_configs(config_files)
    common_config.set_config_defaults()
    log.setup(CONF, "sahara")

    # Validate other configurations (that may produce logs) here
    cinder.validate_config()
    keystone.validate_config()
    validate_castellan_config()

    messaging.setup(service_name)

    plugins_base.setup_plugins()

    ds_manager.setup_data_sources()
    jb_manager.setup_job_binaries()

    LOG.info('Sahara {service} started'.format(service=service_name))


def validate_castellan_config():
    with admin_context():
        castellan.validate_config()


def setup_sahara_api(mode):
    ops = _get_ops_driver(mode)

    api.setup_api(ops)


def setup_sahara_engine():
    periodic.setup()

    engine = _get_infrastructure_engine()
    service_ops.setup_ops(engine)

    remote_driver = _get_remote_driver()
    remote.setup_remote(remote_driver, engine)


def setup_auth_policy():
    acl.setup_policy()


def make_app():
    app_loader = oslo_wsgi.Loader(CONF)
    return app_loader.load_app("sahara")


def _load_driver(namespace, name):
    extension_manager = stevedore.DriverManager(
        namespace=namespace,
        name=name,
        invoke_on_load=True
    )
    LOG.info("Driver {name} successfully loaded".format(name=name))

    return extension_manager.driver


def _get_infrastructure_engine():
    """Import and return one of sahara.service.*_engine.py modules."""
    LOG.debug("Infrastructure engine {engine} is loading".format(
        engine=INFRASTRUCTURE_ENGINE))
    return _load_driver('sahara.infrastructure.engine', INFRASTRUCTURE_ENGINE)


def _get_remote_driver():
    LOG.debug("Remote {remote} is loading".format(remote=CONF.remote))

    return _load_driver('sahara.remote', CONF.remote)


def _get_ops_driver(driver_name):
    LOG.debug("Ops {driver} is loading".format(driver=driver_name))

    return _load_driver('sahara.run.mode', driver_name)


def get_process_launcher():
    return oslo_service.ProcessLauncher(CONF, restart_method='mutate')


def launch_api_service(launcher, service):
    launcher.launch_service(service, workers=CONF.api_workers)
    service.start()
    launcher.wait()


@contextlib.contextmanager
def admin_context():
    ctx = context.get_admin_context()
    context.set_ctx(ctx)
    try:
        yield
    finally:
        context.set_ctx(None)
