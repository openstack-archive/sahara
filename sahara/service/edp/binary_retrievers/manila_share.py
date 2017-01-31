# Copyright (c) 2015 Red Hat Inc.
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

from sahara.service.edp import job_utils
from sahara.service.edp.utils import shares as shares_service


def get_file_info(job_binary, remote):
    shares = []
    if remote.instance.node_group.cluster.shares:
        shares.extend(remote.instance.node_group.cluster.shares)
    if remote.instance.node_group.shares:
        shares.extend(remote.instance.node_group.shares)
    path = shares_service.get_share_path(job_binary.url, shares)
    if path is None:
        path = job_utils.mount_share_at_default_path(
            job_binary.url,
            remote.instance.node_group.cluster)
    return {'type': 'path',
            'path': path}
