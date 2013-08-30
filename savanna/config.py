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

from oslo.config import cfg

cli_opts = [
    cfg.StrOpt('host', default='',
               help='Hostname of IP address that will be used to listen on'),
    cfg.IntOpt('port', default=8386,
               help='Port that will be used to listen on'),
    cfg.BoolOpt('log-exchange', default=False,
                help='Log request/response exchange details: environ, '
                     'headers and bodies')
]

cluster_node_opts = [
    cfg.BoolOpt('use_floating_ips',
                default=True,
                help='When set to false, Savanna uses only internal IP of VMs.'
                     ' When set to true, Savanna expects OpenStack to auto-'
                     'assign floating IPs to cluster nodes. Internal IPs will '
                     'be used for inter-cluster communication, while floating '
                     'ones will be used by Savanna to configure nodes. Also '
                     'floating IPs will be exposed in service URLs. This '
                     'option is ignored when "use_neutron" is set to True'),
    cfg.StrOpt('node_domain',
               default='novalocal',
               help="The suffix of the node's FQDN. In nova-network that is "
                    "dhcp_domain config parameter"),
    cfg.BoolOpt('use_neutron',
                default=False,
                help="Use Neutron or Nova Network")
]


CONF = cfg.CONF
CONF.register_cli_opts(cli_opts)
CONF.register_opts(cluster_node_opts)

ARGV = []


def parse_configs(argv=None, conf_files=None):
    if argv is not None:
        global ARGV
        ARGV = argv
    try:
        CONF(ARGV, project='savanna', default_config_files=conf_files)
    except cfg.RequiredOptError as roe:
        # TODO(slukjanov): replace RuntimeError with Savanna-specific exception
        raise RuntimeError("Option '%s' is required for config group "
                           "'%s'" % (roe.opt_name, roe.group.name))
