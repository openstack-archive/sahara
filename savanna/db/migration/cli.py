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

import gettext

from oslo.config import cfg

from savanna.db import api as db_api


gettext.install('savanna', unicode=1)

CONF = cfg.CONF


def map_status(status):
    return 'Success' if status else 'Fail'


def db_handler():
    drop_status = db_api.drop_db()
    print("Dropping database: %s" % map_status(drop_status))
    start_status = db_api.setup_db()
    print("Creating database: %s" % map_status(start_status))


def add_command_parsers(subparsers):
    parser = subparsers.add_parser('db-sync')
    parser.set_defaults(func=db_handler)


command_opt = cfg.SubCommandOpt('command',
                                title='Command',
                                help='Available commands',
                                handler=add_command_parsers)


CONF.register_cli_opt(command_opt)


def main():
    CONF()
    CONF.command.func()
