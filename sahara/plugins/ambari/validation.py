# Copyright (c) 2015 Mirantis Inc.
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


from sahara import conductor
from sahara import context
from sahara.i18n import _
from sahara.plugins.ambari import common
from sahara.plugins import exceptions as ex
from sahara.plugins import utils


conductor = conductor.API


def validate_creation(cluster_id):
    ctx = context.ctx()
    cluster = conductor.cluster_get(ctx, cluster_id)
    _check_ambari(cluster)
    _check_hdfs(cluster)
    _check_yarn(cluster)


def _check_ambari(cluster):
    am_count = utils.get_instances_count(cluster, common.AMBARI_SERVER)
    zk_count = utils.get_instances_count(cluster, common.ZOOKEEPER_SERVER)
    if am_count != 1:
        raise ex.InvalidComponentCountException(common.AMBARI_SERVER, 1,
                                                am_count)
    if zk_count == 0:
        raise ex.InvalidComponentCountException(common.ZOOKEEPER_SERVER,
                                                _("1 or more"), zk_count)


def _check_hdfs(cluster):
    nn_count = utils.get_instances_count(cluster, common.NAMENODE)
    dn_count = utils.get_instances_count(cluster, common.DATANODE)
    if nn_count != 1:
        raise ex.InvalidComponentCountException(common.NAMENODE, 1, nn_count)
    if dn_count == 0:
        raise ex.InvalidComponentCountException(
            common.DATANODE, _("1 or more"), dn_count)


def _check_yarn(cluster):
    rm_count = utils.get_instances_count(cluster, common.RESOURCEMANAGER)
    nm_count = utils.get_instances_count(cluster, common.NODEMANAGER)
    hs_count = utils.get_instances_count(cluster, common.HISTORYSERVER)
    at_count = utils.get_instances_count(cluster, common.APP_TIMELINE_SERVER)
    if rm_count != 1:
        raise ex.InvalidComponentCountException(common.RESOURCEMANAGER, 1,
                                                rm_count)
    if hs_count != 1:
        raise ex.InvalidComponentCountException(common.HISTORYSERVER, 1,
                                                hs_count)
    if at_count != 1:
        raise ex.InvalidComponentCountException(common.APP_TIMELINE_SERVER, 1,
                                                at_count)
    if nm_count == 0:
        raise ex.InvalidComponentCountException(common.NODEMANAGER,
                                                _("1 or more"), nm_count)
