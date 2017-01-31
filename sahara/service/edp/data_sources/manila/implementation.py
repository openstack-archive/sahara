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

from oslo_utils import uuidutils
import six.moves.urllib.parse as urlparse

from sahara import exceptions as ex
from sahara.i18n import _
from sahara.service.edp.data_sources.base import DataSourceType
from sahara.service.edp import job_utils
from sahara.service.edp.utils import shares as shares_service


class ManilaType(DataSourceType):
    def validate(self, data):
        self._validate_url(data['url'])

    def _validate_url(self, url):
        if len(url) == 0:
            raise ex.InvalidDataException(_("Manila url must not be empty"))
        url = urlparse.urlparse(url)
        if url.scheme != "manila":
            raise ex.InvalidDataException(_("Manila url scheme must be"
                                            " 'manila'"))
        if not uuidutils.is_uuid_like(url.netloc):
            raise ex.InvalidDataException(_("Manila url netloc must be a"
                                            " uuid"))
        if not url.path:
            raise ex.InvalidDataException(_("Manila url path must not be"
                                            " empty"))

    def _prepare_cluster(self, url, cluster):
        path = self._get_share_path(url, cluster.shares or [])
        if path is None:
            path = job_utils.mount_share_at_default_path(url,
                                                         cluster)
        return path

    def get_runtime_url(self, url, cluster):
        # TODO(mariannelm): currently the get_runtime_url method is responsible
        # for preparing the cluster for the manila job type which is not the
        # best approach. In order to make a prepare_cluster method for manila
        # the edp/job_utils.py resolve_data_source_reference function must be
        # refactored
        path = self._prepare_cluster(url, cluster)
        # This gets us the mount point, but we need a file:// scheme to
        # indicate a local filesystem path
        return "file://{path}".format(path=path)

    def _get_share_path(self, url, shares):
        return shares_service.get_share_path(url, shares)
