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

from oslo_config import cfg
from oslo_utils import uuidutils
import six.moves.urllib.parse as urlparse

from sahara import conductor as c
from sahara import exceptions as ex
from sahara.i18n import _
from sahara.service.edp.job_binaries.base import JobBinaryType
import sahara.service.validations.edp.base as b

CONF = cfg.CONF
conductor = c.API


class InternalDBType(JobBinaryType):
    def copy_binary_to_cluster(self, job_binary, **kwargs):
        # url example: 'internal-db://JobBinaryInternal-UUID'
        r = kwargs.pop('remote')

        dst = self._generate_valid_path(job_binary)
        raw = self.get_raw_data(job_binary, **kwargs)

        r.write_file_to(dst, raw)
        return dst

    def get_raw_data(self, job_binary, **kwargs):
        context = kwargs.pop('context')
        # url example: 'internal-db://JobBinaryInternal-UUID'
        binary_internal_id = job_binary.url[len("internal-db://"):]
        return conductor.job_binary_internal_get_raw_data(context,
                                                          binary_internal_id)

    def validate_job_location_format(self, url):
        try:
            self._validate_url(url)
        except ex.InvalidDataException:
            return False
        return True

    def validate(self, data, **kwargs):
        self._validate_url(data['url'])
        internal_uid = data['url'].replace("internal-db://", '')
        b.check_job_binary_internal_exists(internal_uid)

    def _validate_url(self, url):
        if len(url) == 0:
            raise ex.InvalidDataException(
                _("Internal data base url must not be empty"))
        url = urlparse.urlparse(url)
        if url.scheme != "internal-db":
            raise ex.InvalidDataException(
                _("URL scheme must be 'internal-db'"))
        if not uuidutils.is_uuid_like(url.netloc):
            raise ex.InvalidDataException(
                _("Internal data base url netloc must be a uuid"))
