# Copyright (c) 2017 OpenStack Foundation
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

import six.moves.urllib.parse as urlparse

from sahara import exceptions as ex
from sahara.i18n import _
from sahara.service.edp.data_sources.base import DataSourceType


class MapRFSType(DataSourceType):
    def validate(self, data):
        self._validate_url(data['url'])

    def _validate_url(self, url):
        if len(url) == 0:
            raise ex.InvalidDataException(_("MapR FS url must not be empty"))
        url = urlparse.urlparse(url)
        if url.scheme:
            if url.scheme != "maprfs":
                raise ex.InvalidDataException(_("URL scheme must be 'maprfs'"))
