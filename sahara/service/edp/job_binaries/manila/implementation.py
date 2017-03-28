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

from sahara import conductor as c
from sahara import exceptions as ex
from sahara.i18n import _
from sahara.service.edp.job_binaries.base import JobBinaryType
from sahara.service.edp import job_utils
from sahara.service.edp.utils import shares as shares_service
from sahara.utils.openstack import manila as m

conductor = c.API


class ManilaType(JobBinaryType):
    def copy_binary_to_cluster(self, job_binary, **kwargs):
        remote = kwargs.pop('remote')
        path = self._get_share_path(job_binary, remote)
        # if path is None, then it was mounted in the default path
        # by the prepare_cluster method so just construct the
        # default path and return it
        if path is None:
            url = urlparse.urlparse(job_binary.url)
            share_id = url.netloc
            mount_point = shares_service.default_mount(share_id)
            path = shares_service.make_share_path(mount_point, url.path)
        return path

    def prepare_cluster(self, job_binary, **kwargs):
        remote = kwargs.pop('remote')
        path = self._get_share_path(job_binary, remote)
        if path is None:
            path = job_utils.mount_share_at_default_path(
                job_binary.url, remote.instance.node_group.cluster)

    def _get_share_path(self, job_binary, remote):
        shares = []
        if remote.instance.node_group.cluster.shares:
            shares.extend(remote.instance.node_group.cluster.shares)
        if remote.instance.node_group.shares:
            shares.extend(remote.instance.node_group.shares)

        path = shares_service.get_share_path(job_binary.url, shares)
        return path

    def validate_job_location_format(self, url):
        if url.startswith(m.MANILA_PREFIX):
            url = urlparse.urlparse(url)
            return (uuidutils.is_uuid_like(url.netloc) and url.path)
        else:
            return False

    def validate(self, data, **kwargs):
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

    def get_raw_data(self, job_binary, **kwargs):
        raise ex.NotImplementedException('Manila does not implement this '
                                         'method')
