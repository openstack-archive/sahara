# Copyright (c) 2017 Massachusetts Open Cloud
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

import six
import six.moves.urllib.parse as urlparse

import sahara.exceptions as ex
from sahara.i18n import _
from sahara.service.edp.job_binaries.base import JobBinaryType
from sahara.service.edp import s3_common


class S3Type(JobBinaryType):
    def copy_binary_to_cluster(self, job_binary, **kwargs):
        r = kwargs.pop('remote')

        dst = self._generate_valid_path(job_binary)
        raw = self.get_raw_data(job_binary)

        r.write_file_to(dst, raw)
        return dst

    def validate_job_location_format(self, url):
        url = urlparse.urlparse(url)
        return url.scheme == "s3" and url.hostname

    def validate(self, data, **kwargs):
        # We only check on create, not update
        if not kwargs.get('job_binary_id', None):
            s3_common._validate_job_binary_url(data['url'])
            extra = data.get("extra", {})
            if (six.viewkeys(extra) !=
                    {"accesskey", "secretkey", "endpoint"}):
                raise ex.InvalidDataException(
                    _("Configs 'accesskey', 'secretkey', and 'endpoint'"
                      " must be provided."))

    def get_raw_data(self, job_binary, **kwargs):
        return s3_common.get_raw_job_binary_data(job_binary)
