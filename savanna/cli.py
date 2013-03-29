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

from flask import Flask
import os

from oslo.config import cfg
from savanna.openstack.common import log
from savanna.storage.db import DB
from savanna.storage.db import setup_storage
from savanna.storage.defaults import setup_defaults

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class BaseCmd(object):
    name = None

    @classmethod
    def add_argument_parser(cls, subparsers):
        parser = subparsers.add_parser(cls.name, help=cls.__doc__)
        parser.set_defaults(cmd_class=cls)
        return parser


class ResetDbCmd(BaseCmd):
    """Reset the database."""

    name = 'reset-db'

    @classmethod
    def add_argument_parser(cls, subparsers):
        parser = super(ResetDbCmd, cls).add_argument_parser(subparsers)
        parser.add_argument('--with-gen-templates', action='store_true')
        return parser

    @staticmethod
    def main():
        gen = CONF.command.with_gen_templates

        app = Flask('savanna.manage')
        setup_storage(app)

        DB.drop_all()
        DB.create_all()

        setup_defaults(True, gen)

        LOG.info("DB has been removed and created from scratch, "
                 "gen templates: %s", gen)


class SampleConfCmd(BaseCmd):
    """Generates sample conf"""

    name = 'sample-conf'

    @classmethod
    def add_argument_parser(cls, subparsers):
        parser = super(SampleConfCmd, cls).add_argument_parser(subparsers)
        parser.add_argument('--full', action='store_true')
        return parser

    @staticmethod
    def main():
        possible_topdir = os.path.normpath(
            os.path.join(os.path.abspath(__file__), os.pardir, os.pardir))

        sample_path = possible_topdir + "/etc/savanna/savanna.conf.sample"
        if CONF.command.full:
            sample_path += "-full"
        try:
            f = open(sample_path, 'r')
            print f.read(),
            f.close()
        except IOError:
            print "File '" + sample_path + "' does not exist."


CLI_COMMANDS = [
    ResetDbCmd,
    SampleConfCmd
]


def add_command_parsers(subparsers):
    for cmd in CLI_COMMANDS:
        cmd.add_argument_parser(subparsers)


command_opt = cfg.SubCommandOpt('command',
                                title='Commands',
                                help='Available commands',
                                handler=add_command_parsers)


def main(argv=None, config_files=None):
    CONF.register_cli_opt(command_opt)
    CONF(args=argv[1:],
         project='savanna',
         usage='%(prog)s [' + '|'.join(
             [cmd.name for cmd in CLI_COMMANDS]) + ']',
         default_config_files=config_files)
    log.setup("savanna")
    CONF.command.cmd_class.main()
