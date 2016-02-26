# Copyright (c) 2014 Hoang Do, Phuc Vo, P. Michiardi, D. Venzano
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

from oslo_log import log as logging

from sahara.i18n import _
from sahara.plugins.spark import config_helper as c_helper
from sahara.plugins import utils
from sahara.utils import cluster_progress_ops
from sahara.utils import poll_utils


LOG = logging.getLogger(__name__)


def start_processes(remote, *processes):
    for proc in processes:
        if proc == "namenode":
            remote.execute_command("sudo service hadoop-hdfs-namenode start")
        elif proc == "datanode":
            remote.execute_command("sudo service hadoop-hdfs-datanode start")
        else:
            remote.execute_command("screen -d -m sudo hadoop %s" % proc)


def refresh_nodes(remote, service):
    remote.execute_command("sudo -u hdfs hadoop %s -refreshNodes"
                           % service)


def format_namenode(nn_remote):
    nn_remote.execute_command("sudo -u hdfs hadoop namenode -format")


def clean_port_hadoop(nn_remote):
    nn_remote.execute_command(("sudo netstat -tlnp"
                               "| awk '/:8020 */"
                               "{split($NF,a,\"/\"); print a[1]}'"
                               "| xargs sudo kill -9"))


def start_spark_master(nn_remote, sp_home):
    nn_remote.execute_command("bash " + os.path.join(sp_home,
                                                     "sbin/start-all.sh"))


def stop_spark(nn_remote, sp_home):
    nn_remote.execute_command("bash " + os.path.join(sp_home,
                                                     "sbin/stop-all.sh"))


@cluster_progress_ops.event_wrapper(
    True, step=_("Await DataNodes start up"), param=("cluster", 0))
def await_datanodes(cluster):
    datanodes_count = len(utils.get_instances(cluster, "datanode"))
    if datanodes_count < 1:
        return

    log_msg = _("Waiting on %d DataNodes to start up") % datanodes_count
    with utils.get_instance(cluster, "namenode").remote() as r:
        poll_utils.plugin_option_poll(
            cluster, _check_datanodes_count,
            c_helper.DATANODES_STARTUP_TIMEOUT,
            log_msg, 1, {"remote": r, "count": datanodes_count})


def _check_datanodes_count(remote, count):
    if count < 1:
        return True

    LOG.debug("Checking DataNodes count")
    ex_code, stdout = remote.execute_command(
        'sudo su -lc "hdfs dfsadmin -report" hdfs | '
        'grep \'Live datanodes\|Datanodes available:\' | '
        'grep -o \'[0-9]\+\' | head -n 1')
    LOG.debug("DataNodes count='{count}'".format(count=stdout.strip()))

    return stdout and int(stdout) == count
