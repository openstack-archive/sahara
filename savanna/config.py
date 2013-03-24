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
               help='set host'),
    cfg.IntOpt('port', default=8080,
               help='set port'),
    cfg.BoolOpt('allow-cluster-ops', default=False,
                help='without that option'
                     ' the application operates in dry run mode and does not '
                     ' send any requests to the OpenStack cluster')
]

CONF = cfg.CONF
CONF.register_cli_opts(cli_opts)


def parse_args(argv, conf_files):
    CONF(argv, project='savanna', default_config_files=conf_files)
