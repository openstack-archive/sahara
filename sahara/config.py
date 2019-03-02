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

import itertools

# loading keystonemiddleware opts because sahara uses these options in code
from keystonemiddleware import opts  # noqa
from oslo_config import cfg
from oslo_log import log

from sahara import exceptions as ex
from sahara.i18n import _
from sahara.plugins import opts as plugins_base
from sahara.service.castellan import config as castellan
from sahara.service.edp.data_sources import opts as data_source
from sahara.service.edp.job_binaries import opts as job_binary
from sahara.topology import topology_helper
from sahara.utils.notification import sender
from sahara.utils.openstack import cinder
from sahara.utils.openstack import keystone
from sahara.utils import remote
from sahara import version


cli_opts = [
    cfg.HostAddressOpt('host', default='0.0.0.0',
                       help='Hostname or IP address that will be used '
                            'to listen on.'),
    cfg.PortOpt('port', default=8386,
                help='Port that will be used to listen on.'),
    cfg.BoolOpt('log-exchange', default=False,
                help='Log request/response exchange details: environ, '
                     'headers and bodies.')
]

edp_opts = [
    cfg.IntOpt('job_binary_max_KB',
               default=5120,
               help='Maximum length of job binary data in kilobytes that '
                    'may be stored or retrieved in a single operation.'),
    cfg.IntOpt('job_canceling_timeout',
               default=300,
               help='Timeout for canceling job execution (in seconds). '
                    'Sahara will try to cancel job execution during '
                    'this time.'),
    cfg.BoolOpt('edp_internal_db_enabled',
                default=True,
                help='Use Sahara internal db to store job binaries.')
]

db_opts = [
    cfg.StrOpt('db_driver',
               default='sahara.db',
               help='Driver to use for database access.')
]

networking_opts = [
    cfg.BoolOpt('use_floating_ips',
                default=True,
                help='If set to True, Sahara will use floating IPs to '
                     'communicate with instances. To make sure that all '
                     'instances have floating IPs assigned, make sure '
                     'that all Node Groups have "floating_ip_pool" '
                     'parameter defined.'),
    cfg.StrOpt('node_domain',
               default='novalocal',
               help="The suffix of the node's FQDN."),
    cfg.BoolOpt('use_namespaces',
                default=False,
                help="Use network namespaces for communication."),
    cfg.BoolOpt('use_rootwrap',
                default=False,
                help="Use rootwrap facility to allow non-root users to run "
                     "the sahara services and access private network IPs "
                     "(only valid to use in conjunction with "
                     "use_namespaces=True)"),
    cfg.StrOpt('rootwrap_command',
               default='sudo sahara-rootwrap /etc/sahara/rootwrap.conf',
               help="Rootwrap command to leverage.  Use in conjunction with "
                    "use_rootwrap=True")
]

dns_opts = [
    cfg.BoolOpt('use_designate',
                default=False,
                help='Use Designate for internal and external hostnames '
                     'resolution'),
    cfg.ListOpt('nameservers',
                default=[],
                help="IP addresses of Designate nameservers. "
                     "This is required if 'use_designate' is True")
]

accessible_ip_opts = [
    cfg.IPOpt('identity_ip_accessible',
              default=None,
              help='IP address of Keystone endpoint, accessible by tenant'
                   ' machines. If not set, the results of the DNS lookup'
                   ' performed where Sahara services are running will be'
                   ' used.'),
    cfg.IPOpt('object_store_ip_accessible',
              default=None,
              help='IP address of Swift endpoint, accessible by tenant'
                   ' machines. If not set, the results of the DNS lookup'
                   ' performed where Sahara services are running will be'
                   ' used.'),
]

CONF = cfg.CONF
CONF.register_cli_opts(cli_opts)
CONF.register_opts(networking_opts)
CONF.register_opts(edp_opts)
CONF.register_opts(db_opts)
CONF.register_opts(dns_opts)
CONF.register_opts(accessible_ip_opts)

log.register_options(CONF)

sahara_default_log_levels = [
    'stevedore=INFO',
    'eventlet.wsgi.server=WARN',
    'paramiko=WARN',
    'requests=WARN',
    'neutronclient=INFO',
]

log.set_defaults(
    default_log_levels=log.get_default_log_levels()+sahara_default_log_levels)


def list_opts():
    # NOTE (vgridnev): we make these import here to avoid problems
    #                  with importing unregistered options in sahara code.
    #                  As example, importing 'node_domain' in
    #                  sahara/conductor/objects.py

    from sahara.conductor import api
    from sahara import main as sahara_main
    from sahara.service import coordinator
    from sahara.service.edp import job_utils
    from sahara.service.heat import heat_engine
    from sahara.service.heat import templates
    from sahara.service import ntp_service
    from sahara.service import periodic
    from sahara.swift import swift_helper
    from sahara.utils import cluster_progress_ops as cpo
    from sahara.utils.openstack import base
    from sahara.utils.openstack import glance
    from sahara.utils.openstack import heat
    from sahara.utils.openstack import manila
    from sahara.utils.openstack import neutron
    from sahara.utils.openstack import nova
    from sahara.utils.openstack import swift
    from sahara.utils import poll_utils
    from sahara.utils import proxy
    from sahara.utils import ssh_remote

    return [
        (None,
         itertools.chain(cli_opts,
                         edp_opts,
                         networking_opts,
                         dns_opts,
                         db_opts,
                         accessible_ip_opts,
                         plugins_base.opts,
                         topology_helper.opts,
                         keystone.opts,
                         remote.ssh_opts,
                         sahara_main.opts,
                         job_utils.opts,
                         periodic.periodic_opts,
                         coordinator.coordinator_opts,
                         ntp_service.ntp_opts,
                         proxy.opts,
                         cpo.event_log_opts,
                         base.opts,
                         heat_engine.heat_engine_opts,
                         templates.heat_engine_opts,
                         ssh_remote.ssh_config_options,
                         castellan.opts,
                         data_source.opts,
                         job_binary.opts)),
        (poll_utils.timeouts.name,
         itertools.chain(poll_utils.timeouts_opts)),
        (api.conductor_group.name,
         itertools.chain(api.conductor_opts)),
        (cinder.cinder_group.name,
         itertools.chain(cinder.opts)),
        (glance.glance_group.name,
         itertools.chain(glance.opts)),
        (heat.heat_group.name,
         itertools.chain(heat.opts)),
        (manila.manila_group.name,
         itertools.chain(manila.opts)),
        (neutron.neutron_group.name,
         itertools.chain(neutron.opts)),
        (nova.nova_group.name,
         itertools.chain(nova.opts)),
        (swift.swift_group.name,
         itertools.chain(swift.opts)),
        (keystone.keystone_group.name,
         itertools.chain(keystone.ssl_opts)),
        (keystone.trustee_group.name,
         itertools.chain(keystone.trustee_opts)),
        (base.retries.name,
         itertools.chain(base.opts)),
        (swift_helper.public_endpoint_cert_group.name,
         itertools.chain(swift_helper.opts)),
        (castellan.castellan_group.name,
         itertools.chain(castellan.castellan_opts)),
        (sender.notifier_opts_group, sender.notifier_opts)
    ]


def parse_configs(conf_files=None):
    try:
        version_string = version.version_info.version_string()
        CONF(project='sahara', version=version_string,
             default_config_files=conf_files)
    except cfg.RequiredOptError as roe:
        raise ex.ConfigurationError(
            _("Option '%(option)s' is required for config group '%(group)s'") %
            {'option': roe.opt_name, 'group': roe.group.name})
