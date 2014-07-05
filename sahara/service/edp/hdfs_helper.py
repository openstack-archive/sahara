# Copyright (c) 2013 Mirantis Inc.
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

import os

from six.moves.urllib import parse as urlparse

from sahara import conductor as c
from sahara import context
from sahara.plugins.general import utils as u
from sahara.utils import general as g


conductor = c.API


def put_file_to_hdfs(r, file, file_name, path, hdfs_user):
    r.write_file_to('/tmp/%s' % file_name, file)
    move_from_local(r, '/tmp/%s' % file_name, path + '/' + file_name,
                    hdfs_user)


def copy_from_local(r, source, target, hdfs_user):
    r.execute_command('sudo su - -c "hadoop dfs -copyFromLocal '
                      '%s %s" %s' % (source, target, hdfs_user))


def move_from_local(r, source, target, hdfs_user):
    # using copyFromLocal followed by rm to address permission issues that
    # arise when image user is not the same as hdfs user (permissions-wise).
    # The moveFromLocal implementation actually is a copy and delete
    # combination, so functionally the implementation is equivalent
    r.execute_command('sudo su - -c "hadoop dfs -copyFromLocal '
                      '%s %s" %s' % (source, target, hdfs_user))
    r.execute_command('sudo rm -f %s' % source)


def _dir_missing(path, hdfs_user, r):
    ret_code, stdout = r.execute_command(
        'sudo su - -c "hadoop dfs -test -e %s" %s' % (path, hdfs_user),
        raise_when_error=False)

    return ret_code == 1


def create_dir(r, dir_name, hdfs_user):
    # there were significant differences between the 'mkdir' and 'mkdir -p'
    # behaviors in Hadoop 1.2.0 vs. 2.2.0 forcing the creation of a
    # manual implementation of 'mkdir -p'
    comp_paths = dir_name.split(os.sep)
    path = os.sep
    for comp in comp_paths:
        if len(comp) > 0:
            path += comp + os.sep
        if _dir_missing(path, hdfs_user, r):
            r.execute_command(
                'sudo su - -c "hadoop dfs -mkdir %s" %s' %
                (path, hdfs_user))


def _get_cluster_hosts_information(host, cluster):
    for clust in conductor.cluster_get_all(context.ctx()):
        if clust.id == cluster.id:
            continue

        for i in u.get_instances(c):
            if i.instance_name == host:
                return g.generate_etc_hosts(c)

    return None


def configure_cluster_for_hdfs(cluster, data_source):
    host = urlparse.urlparse(data_source.url).hostname

    etc_hosts_information = _get_cluster_hosts_information(host, cluster)
    if etc_hosts_information is None:
        # Ip address hasn't been resolved, the last chance is for VM itself
        return

    update_etc_hosts_cmd = (
        'cat /tmp/etc-hosts-update /etc/hosts | '
        'sort | uniq > /tmp/etc-hosts && '
        'cat /tmp/etc-hosts > /etc/hosts && '
        'rm -f /tmp/etc-hosts /tmp/etc-hosts-update')

    for inst in u.get_instances(cluster):
        with inst.remote() as r:
            r.write_file_to('/tmp/etc-hosts-update', etc_hosts_information)
            r.execute_command(update_etc_hosts_cmd, run_as_root=True)
