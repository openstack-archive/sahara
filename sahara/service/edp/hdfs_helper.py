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


from oslo_utils import uuidutils
import six
from six.moves.urllib import parse as urlparse

from sahara import conductor as c
from sahara import context
from sahara.plugins import exceptions as ex
from sahara.plugins import utils as u
from sahara.utils import cluster as cluster_utils

conductor = c.API

HBASE_COMMON_LIB_PATH = "/user/sahara-hbase-lib"


def create_hbase_common_lib(r):
    r.execute_command(
        'sudo su - -c "hdfs dfs -mkdir -p %s" hdfs' % (
            HBASE_COMMON_LIB_PATH))
    ret_code, stdout = r.execute_command(
        'hbase classpath')
    if ret_code == 0:
        paths = stdout.split(':')
        for p in paths:
            if p.endswith(".jar"):
                r.execute_command('sudo su - -c "hdfs dfs -put -p %s %s" hdfs'
                                  % (p, HBASE_COMMON_LIB_PATH))
    else:
        raise ex.RequiredServiceMissingException('hbase')


def put_file_to_hdfs(r, file, file_name, path, hdfs_user):
    tmp_file_name = '%s.%s' % (file_name, six.text_type(
        uuidutils.generate_uuid()))
    r.write_file_to('/tmp/%s' % tmp_file_name, file)
    move_from_local(r, '/tmp/%s' % tmp_file_name, path + '/' + file_name,
                    hdfs_user)


def copy_from_local(r, source, target, hdfs_user):
    r.execute_command('sudo su - -c "hdfs dfs -copyFromLocal '
                      '%s %s" %s' % (source, target, hdfs_user))


def move_from_local(r, source, target, hdfs_user):
    # using copyFromLocal followed by rm to address permission issues that
    # arise when image user is not the same as hdfs user (permissions-wise).
    r.execute_command('sudo su - -c "hdfs dfs -copyFromLocal %(source)s '
                      '%(target)s" %(user)s && sudo rm -f %(source)s' %
                      {"source": source, "target": target, "user": hdfs_user})


def create_dir_hadoop1(r, dir_name, hdfs_user):
    r.execute_command(
        'sudo su - -c "hdfs dfs -mkdir %s" %s' % (dir_name, hdfs_user))


def create_dir_hadoop2(r, dir_name, hdfs_user):
    r.execute_command(
        'sudo su - -c "hdfs dfs -mkdir -p %s" %s' % (dir_name, hdfs_user))


def _get_cluster_hosts_information(host, cluster):
    for clust in conductor.cluster_get_all(context.ctx()):
        if clust.id == cluster.id:
            continue

        for i in u.get_instances(clust):
            if i.instance_name == host:
                return cluster_utils.generate_etc_hosts(clust)

    return None


def _is_cluster_configured(cluster, host_info):
    inst = u.get_instances(cluster)[0]
    cat_etc_hosts = 'cat /etc/hosts'
    with inst.remote() as r:
        exit_code, etc_hosts = r.execute_command(cat_etc_hosts)
        return all(host in etc_hosts for host in host_info)


def configure_cluster_for_hdfs(cluster, data_source_url):
    host = urlparse.urlparse(data_source_url).hostname

    etc_hosts_information = _get_cluster_hosts_information(host, cluster)
    if etc_hosts_information is None:
        # Ip address hasn't been resolved, the last chance is for VM itself
        return

    # If the cluster was already configured for this data source
    # there's no need to configure it again
    if _is_cluster_configured(cluster, etc_hosts_information.splitlines()):
        return

    etc_hosts_update = ('/tmp/etc-hosts-update'
                        '.%s' % six.text_type(uuidutils.generate_uuid()))
    tmp_etc_hosts = ('/tmp/etc-hosts'
                     '.%s' % six.text_type(uuidutils.generate_uuid()))
    update_etc_hosts_cmd = (
        'cat %(etc_hosts_update)s /etc/hosts | '
        'sort | uniq > %(tmp_etc_hosts)s && '
        'cat %(tmp_etc_hosts)s > /etc/hosts && '
        'rm -f %(tmp_etc_hosts)s %(etc_hosts_update)s' %
        {'etc_hosts_update': etc_hosts_update, 'tmp_etc_hosts': tmp_etc_hosts})

    for inst in u.get_instances(cluster):
        with inst.remote() as r:
            r.write_file_to(etc_hosts_update, etc_hosts_information)
            r.execute_command(update_etc_hosts_cmd, run_as_root=True)
