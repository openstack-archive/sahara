# Copyright 2015 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import sys

from oslo_config import cfg
from oslo_log import log
import pkg_resources as pkg

from sahara.db.templates import api
from sahara import version

LOG = log.getLogger(__name__)

CONF = cfg.CONF


def extra_option_checks():

    if not CONF.database.connection:
        print("No database connection string was specified in configuration",
              file=sys.stderr)
        sys.exit(1)

    if CONF.command.name in ['update', 'delete']:
        if CONF.command.plugin_version and not CONF.command.plugin_name:
            print("The --plugin-version option is not valid "
                  "without --plugin-name", file=sys.stderr)
            sys.exit(-1)

    if CONF.command.name == "update":
        # Options handling probably needs some refactoring in the future.
        # For now, though, we touch the conductor which ultimately touches
        # the plugins.base. Use the "plugins" option there as a default
        # list of plugins to process, since those are the plugins that
        # will be loaded by Sahara
        if not CONF.command.plugin_name:
            if "plugins" in CONF and CONF.plugins:
                LOG.info("Using plugin list {plugins} from "
                         "config".format(plugins=CONF.plugins))
            else:
                print("No plugins specified with --plugin-name "
                      "or config", file=sys.stderr)
                sys.exit(-1)


def add_command_parsers(subparsers):
    # Note, there is no 'list' command here because the client
    # or REST can be used for list operations. Default templates
    # will display, and templates will show the 'is_default' field.

    def add_id(parser):
        parser.add_argument('--id', required=True,
                            help='The id of the default '
                                 'template to delete')

    def add_tenant_id(parser):
        parser.add_argument('-t', '--tenant_id', required=True,
                            help='Tenant ID for database operations.')

    def add_name_and_tenant_id(parser):
        parser.add_argument('--name', dest='template_name', required=True,
                            help='Name of the default template')
        add_tenant_id(parser)

    def add_plugin_name_and_version(parser, require_plugin_name=False):

        plugin_name_help = ('Only process templates containing '
                            'a "plugin_name" field matching '
                            'one of these values.')

        if not require_plugin_name:
            extra = (' The default list of plugin names '
                     'is taken from the "plugins" parameter in '
                     'the [DEFAULT] config section.')
            plugin_name_help += extra

        parser.add_argument('-p', '--plugin-name', nargs="*",
                            required=require_plugin_name,
                            help=plugin_name_help)

        parser.add_argument('-pv', '--plugin-version', nargs="*",
                            help='Only process templates containing a '
                                 '"hadoop_version" field matching one of '
                                 'these values. This option is '
                                 'only valid if --plugin-name is specified '
                                 'as well. A version specified '
                                 'here may optionally be prefixed with a '
                                 'plugin name and a dot, for example '
                                 '"vanilla.1.2.1". Dotted versions only '
                                 'apply to the plugin named in the '
                                 'prefix. Versions without a prefix apply to '
                                 'all plugins.')

    fname = pkg.resource_filename(version.version_info.package,
                                  "plugins/default_templates")
    # update command
    parser = subparsers.add_parser('update',
                                   help='Update the default template set')
    parser.add_argument('-d', '--directory',
                        default=fname,
                        help='Template directory. Default is %s' % fname)
    parser.add_argument('-n', '--norecurse', action='store_true',
                        help='Do not descend into subdirectories')

    add_plugin_name_and_version(parser)
    add_tenant_id(parser)
    parser.set_defaults(func=api.do_update)

    # delete command
    parser = subparsers.add_parser('delete',
                                   help='Delete default templates '
                                        'by plugin and version')
    add_plugin_name_and_version(parser, require_plugin_name=True)
    add_tenant_id(parser)
    parser.set_defaults(func=api.do_delete)

    # node-group-template-delete command
    parser = subparsers.add_parser('node-group-template-delete',
                                   help='Delete a default '
                                        'node group template by name')
    add_name_and_tenant_id(parser)
    parser.set_defaults(func=api.do_node_group_template_delete)

    # cluster-template-delete command
    parser = subparsers.add_parser('cluster-template-delete',
                                   help='Delete a default '
                                        'cluster template by name')
    add_name_and_tenant_id(parser)
    parser.set_defaults(func=api.do_cluster_template_delete)

    # node-group-template-delete-id command
    parser = subparsers.add_parser('node-group-template-delete-id',
                                   help='Delete a default '
                                        'node group template by id')
    add_id(parser)
    parser.set_defaults(func=api.do_node_group_template_delete_by_id)

    # cluster-template-delete-id command
    parser = subparsers.add_parser('cluster-template-delete-id',
                                   help='Delete a default '
                                        'cluster template by id')
    add_id(parser)
    parser.set_defaults(func=api.do_cluster_template_delete_by_id)


command_opt = cfg.SubCommandOpt('command',
                                title='Command',
                                help='Available commands',
                                handler=add_command_parsers)
CONF.register_cli_opt(command_opt)


def unregister_extra_cli_opt(name):
    try:
        for cli in CONF._cli_opts:
            if cli['opt'].name == name:
                CONF.unregister_opt(cli['opt'])
    except Exception:
        pass


# Remove a few extra CLI opts that we picked up via imports
# Do this early so that they do not appear in the help
for extra_opt in ["log-exchange", "host", "port"]:
    unregister_extra_cli_opt(extra_opt)


def main():
    # TODO(tmckay): Work on restricting the options
    # pulled in by imports which show up in the help.
    # If we find a nice way to do this the calls to
    # unregister_extra_cli_opt() can be removed
    CONF(project='sahara')

    # For some reason, this is necessary to clear cached values
    # and re-read configs.  For instance, if this is not done
    # here the 'plugins' value will not reflect the value from
    # the config file on the command line
    CONF.reload_config_files()
    log.setup(CONF, "sahara")

    # If we have to enforce extra option checks, like one option
    # requires another, do it here
    extra_option_checks()

    # Since this may be scripted, record the command in the log
    # so a user can know exactly what was done
    LOG.info("Command: {command}".format(command=' '.join(sys.argv)))

    api.set_logger(LOG)
    api.set_conf(CONF)

    CONF.command.func()

    LOG.info("Finished {command}".format(command=CONF.command.name))
