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
import six.moves.urllib.parse as urlparse

from sahara import exceptions as ex
from sahara.i18n import _
from sahara.service.edp.data_sources.base import DataSourceType
from sahara.swift import swift_helper as sw
from sahara.swift import utils as su
from sahara.utils.types import FrozenDict

CONF = cfg.CONF


class SwiftType(DataSourceType):
    def validate(self, data):
        self._validate_url(data['url'])

        if not CONF.use_domain_for_proxy_users and "credentials" not in data:
            raise ex.InvalidCredentials(_("No credentials provided for Swift"))
        if not CONF.use_domain_for_proxy_users and (
                "user" not in data["credentials"]):
            raise ex.InvalidCredentials(
                _("User is not provided in credentials for Swift"))
        if not CONF.use_domain_for_proxy_users and (
                "password" not in data["credentials"]):
            raise ex.InvalidCredentials(
                _("Password is not provided in credentials for Swift"))

    def _validate_url(self, url):
        if len(url) == 0:
            raise ex.InvalidDataException(_("Swift url must not be empty"))

        url = urlparse.urlparse(url)
        if url.scheme != "swift":
            raise ex.InvalidDataException(_("URL scheme must be 'swift'"))

        # The swift url suffix does not have to be included in the netloc.
        # However, if the swift suffix indicator is part of the netloc then
        # we require the right suffix.
        # Additionally, the path must be more than '/'
        if (su.SWIFT_URL_SUFFIX_START in url.netloc and not
           url.netloc.endswith(su.SWIFT_URL_SUFFIX)) or len(url.path) <= 1:
            raise ex.InvalidDataException(
                _("URL must be of the form swift://container%s/object")
                % su.SWIFT_URL_SUFFIX)

    def prepare_cluster(self, data_source, cluster, **kwargs):
        if hasattr(data_source, "credentials"):
            job_configs = kwargs.pop('job_configs')

            # if no data source was passed as a reference for the job, the
            # job_configs will not be changed (so it will be a FronzenDict)
            # and we don't need to change it as well
            if isinstance(job_configs, FrozenDict) or \
               job_configs.get('configs', None) is None:
                return

            if not job_configs.get('proxy_configs'):
                username = data_source.credentials['user']
                password = data_source.credentials['password']

                # Don't overwrite if there is already a value here
                if job_configs['configs'].get(sw.HADOOP_SWIFT_USERNAME, None) \
                   is None and (username is not None):
                    job_configs['configs'][sw.HADOOP_SWIFT_USERNAME] = username
                if job_configs['configs'].get(sw.HADOOP_SWIFT_PASSWORD, None) \
                   is None and (password is not None):
                    job_configs['configs'][sw.HADOOP_SWIFT_PASSWORD] = password
