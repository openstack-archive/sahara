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
]

CONF = cfg.CONF
CONF.register_cli_opts(cli_opts)

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
