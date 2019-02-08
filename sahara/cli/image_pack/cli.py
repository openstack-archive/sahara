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
import six

from sahara.cli.image_pack import api
from sahara.i18n import _

LOG = log.getLogger(__name__)

CONF = cfg.CONF

CONF.register_cli_opts([
    cfg.StrOpt(
        'image',
        required=True,
        help=_("The path to an image to modify. This image will be modified "
               "in-place: be sure to target a copy if you wish to maintain a "
               "clean master image.")),
    cfg.StrOpt(
        'root-filesystem',
        dest='root_fs',
        required=False,
        help=_("The filesystem to mount as the root volume on the image. No "
               "value is required if only one filesystem is detected.")),
    cfg.BoolOpt(
        'test-only',
        dest='test_only',
        default=False,
        help=_("If this flag is set, no changes will be made to the image; "
               "instead, the script will fail if discrepancies are found "
               "between the image and the intended state."))])


def unregister_extra_cli_opt(name):
    try:
        for cli in CONF._cli_opts:
            if cli['opt'].name == name:
                CONF.unregister_opt(cli['opt'])
    except Exception:
        pass


for extra_opt in ["log-exchange", "host", "port"]:
    unregister_extra_cli_opt(extra_opt)


def add_plugin_parsers(subparsers):
    api.setup_plugins()
    for plugin in api.get_loaded_plugins():
        args_by_version = api.get_plugin_arguments(plugin)
        if all(args is NotImplemented for version, args
               in six.iteritems(args_by_version)):
            continue
        plugin_parser = subparsers.add_parser(
            plugin, help=_('Image generation for the {plugin} plugin').format(
                plugin=plugin))
        version_parsers = plugin_parser.add_subparsers(
            title=_("Plugin version"),
            dest="version",
            help=_("Available versions"))
        for version, args in six.iteritems(args_by_version):
            if args is NotImplemented:
                continue
            version_parser = version_parsers.add_parser(
                version, help=_('{plugin} version {version}').format(
                    plugin=plugin, version=version))
            for arg in args:
                arg_token = ("--%s" % arg.name if len(arg.name) > 1 else
                             "-%s" % arg.name)
                version_parser.add_argument(arg_token,
                                            dest=arg.name,
                                            help=arg.description,
                                            default=arg.default,
                                            required=arg.required,
                                            choices=arg.choices)
            version_parser.set_defaults(args={arg.name
                                              for arg in args})


command_opt = cfg.SubCommandOpt('plugin',
                                title=_('Plugin'),
                                help=_('Available plugins'),
                                handler=add_plugin_parsers)

CONF.register_cli_opt(command_opt)


def main():
    CONF(project='sahara')

    CONF.reload_config_files()
    log.setup(CONF, "sahara")

    LOG.info("Command: {command}".format(command=' '.join(sys.argv)))

    api.set_logger(LOG)
    api.set_conf(CONF)

    plugin = CONF.plugin.name
    version = CONF.plugin.version
    args = CONF.plugin.args
    image_arguments = {arg: getattr(CONF.plugin, arg) for arg in args}

    api.pack_image(CONF.image, plugin, version, image_arguments,
                   CONF.root_fs, CONF.test_only)

    LOG.info("Finished packing image for {plugin} at version "
             "{version}".format(plugin=plugin, version=version))
