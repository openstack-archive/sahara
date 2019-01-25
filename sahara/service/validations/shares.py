# Copyright (c) 2015 Red Hat, Inc.
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

from sahara import exceptions as ex
from sahara.i18n import _
from sahara.service.edp.utils import shares
from sahara.utils.openstack import manila


SHARE_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "id": {
                "type": "string",
                "format": "uuid"
            },
            "path": {
                "type": ["string", "null"]
            },
            "access_level": {
                "type": ["string", "null"],
                "enum": ["rw", "ro"],
                "default": "rw"
            }
        },
        "additionalProperties": False,
        "required": [
            "id"
        ]
    }
}


def check_shares(data):
    if not data:
        return

    paths = (share.get('path') for share in data)
    paths = [path for path in paths if path is not None]
    if len(paths) != len(set(paths)):
        raise ex.InvalidDataException(
            _('Multiple shares cannot be mounted to the same path.'))

    for path in paths:
        if not path.startswith('/') or '\x00' in path:
            raise ex.InvalidDataException(
                _('Paths must be absolute Linux paths starting with "/" '
                  'and may not contain nulls.'))

    client = manila.client()
    for share in data:
        manila_share = manila.get_share(client, share['id'])
        if not manila_share:
            raise ex.InvalidReferenceException(
                _("Requested share id %s does not exist.") % share['id'])

        share_type = manila_share.share_proto
        if share_type not in shares.SUPPORTED_SHARE_TYPES:
            raise ex.InvalidReferenceException(
                _("Requested share id %(id)s is of type %(type)s, which is "
                  "not supported by Sahara.")
                % {"id": share['id'], "type": share_type})
