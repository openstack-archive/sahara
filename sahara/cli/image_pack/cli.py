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

from sahara.cli.image_pack import api
from sahara.i18n import _LI

LOG = log.getLogger(__name__)

CONF = cfg.CONF


CONF.register_cli_opts([
    cfg.StrOpt(
        'plugin',
        required=True,
        help="The name of the Sahara plugin for which you would like to "
             "generate an image. Use sahara-image-create -p PLUGIN -h to "
             "see a set of versions for a specific plugin."),
    cfg.StrOpt(
        'plugin-version',
        dest='plugin_version',
        required=True,
        help="The version of the Sahara plugin for which you would like to "
             "generate an image. Use sahara-image-create -p PLUGIN -v "
             "VERSION -h to see a full set of arguments for a specific plugin "
             "and version."),
    cfg.StrOpt(
        'image',
        required=True,
        help="The path to an image to modify. This image will be modified "
             "in-place: be sure to target a copy if you wish to maintain a "
             "clean master image."),
    cfg.StrOpt(
        'root-filesystem',
        dest='root_fs',
        required=False,
        help="The filesystem to mount as the root volume on the image. No"
             "value is required if only one filesystem is detected."),
    cfg.BoolOpt(
        'test-only',
        dest='test_only',
        default=False,
        help="If this flag is set, no changes will be made to the image; "
             "instead, the script will fail if discrepancies are found "
             "between the image and the intended state."),
])


def unregister_extra_cli_opt(name):
    try:
        for cli in CONF._cli_opts:
            if cli['opt'].name == name:
                CONF.unregister_opt(cli['opt'])
    except Exception:
        pass


for extra_opt in ["log-exchange", "host", "port"]:
    unregister_extra_cli_opt(extra_opt)


def main():
    CONF(project='sahara')

    CONF.reload_config_files()
    log.setup(CONF, "sahara")

    LOG.info(_LI("Command: {command}").format(command=' '.join(sys.argv)))

    api.set_logger(LOG)
    api.set_conf(CONF)

    api.pack_image(CONF.plugin, CONF.plugin_version, CONF.image,
                   CONF.root_fs, CONF.test_only)

    LOG.info(_LI("Finished packing image for {plugin} at version {version}"
                 ).format(plugin=CONF.plugin, version=CONF.plugin_version))
