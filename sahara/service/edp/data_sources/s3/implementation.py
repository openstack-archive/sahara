# Copyright (c) 2018 OpenStack Contributors
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
from sahara.service.edp import s3_common
from sahara.utils import types


class S3Type(DataSourceType):
    configs_map = {"accesskey": s3_common.S3_ACCESS_KEY_CONFIG,
                   "secretkey": s3_common.S3_SECRET_KEY_CONFIG,
                   "endpoint": s3_common.S3_ENDPOINT_CONFIG,
                   "bucket_in_path": s3_common.S3_BUCKET_IN_PATH_CONFIG,
                   "ssl": s3_common.S3_SSL_CONFIG}

    bool_keys = ["bucket_in_path",
                 "ssl"]

    def validate(self, data):
        self._validate_url(data['url'])

        # Do validation loosely, and don't require much... the user might have
        # (by their own preference) set some or all configs manually

        if "credentials" not in data:
            return

        for key in data["credentials"].keys():
            if key not in self.configs_map.keys():
                raise ex.InvalidDataException(
                    _("Unknown config '%s' for S3 data source") % key)
            if key in self.bool_keys:
                if not isinstance(data["credentials"][key], bool):
                    raise ex.InvalidDataException(
                        _("Config '%s' must be boolean") % key)

    def _validate_url(self, url):
        if len(url) == 0:
            raise ex.InvalidDataException(_("S3 url must not be empty"))

        url = urlparse.urlparse(url)
        if url.scheme not in ["s3", "s3a"]:
            raise ex.InvalidDataException(
                _("URL scheme must be 's3' or 's3a'"))

        if not url.hostname:
            raise ex.InvalidDataException(_("Bucket name must be present"))

        if not url.path:
            raise ex.InvalidDataException(_("Object name must be present"))

    def prepare_cluster(self, data_source, cluster, **kwargs):
        if hasattr(data_source, "credentials"):
            job_configs = kwargs.pop('job_configs')

            if isinstance(job_configs, types.FrozenDict):
                return
            if job_configs.get('configs', None) is None:
                return

            creds = data_source.credentials
            job_conf = job_configs['configs']

            for config_name, s3a_cfg_name in self.configs_map.items():
                if job_conf.get(s3a_cfg_name, None) is None:  # no overwrite
                    if creds.get(config_name, None) is not None:
                        job_conf[s3a_cfg_name] = creds[config_name]

    def get_runtime_url(self, url, cluster):
        return url.replace("s3://", "s3a://", 1)
