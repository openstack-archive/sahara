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

import six

from sahara import conductor as c
from sahara import context
from sahara.service import shares as shares_service

conductor = c.API


def get_file_info(job_binary, remote):
    shares = []
    if remote.instance.node_group.cluster.shares:
        shares.extend(remote.instance.node_group.cluster.shares)
    if remote.instance.node_group.shares:
        shares.extend(remote.instance.node_group.shares)
    # url example: 'manila://ManilaShare-uuid/path_to_file'
    url = six.moves.urllib.parse.urlparse(job_binary.url)
    share_id = url.netloc
    if not any(s['id'] == share_id for s in shares):
        # Automount this share to the cluster
        cluster = remote.instance.node_group.cluster
        if cluster.shares:
            cluster_shares = [dict(s) for s in cluster.shares]
        else:
            cluster_shares = []
        needed_share = {
            'id': share_id,
            'path': '/mnt/{0}'.format(share_id),
            'access_level': 'rw'
        }

        cluster_shares.append(needed_share)
        cluster = conductor.cluster_update(
            context.ctx(), cluster, {'shares': cluster_shares})
        shares_service.mount_shares(cluster)
        shares = cluster.shares

    # using list() as a python2/3 workaround
    share = list(filter(lambda s: s['id'] == share_id, shares))[0]
    mount_point = share.get('path', "/mnt/%s" % share_id)

    res = {
        'type': 'path',
        'path': "{0}{1}".format(mount_point, url.path)
    }
    return res
