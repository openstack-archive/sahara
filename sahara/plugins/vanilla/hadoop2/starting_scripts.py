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

from sahara.plugins import utils
from sahara.plugins.vanilla.hadoop2 import run_scripts as run
from sahara.plugins.vanilla import utils as vu
from sahara.utils import cluster_progress_ops as cpo


def start_namenode(cluster):
    nn = vu.get_namenode(cluster)
    _start_namenode(nn)


@cpo.event_wrapper(
    True, step=utils.start_process_event_message('NameNode'))
def _start_namenode(nn):
    run.format_namenode(nn)
    run.start_hadoop_process(nn, 'namenode')


def start_secondarynamenode(cluster):
    snn = vu.get_secondarynamenode(cluster)
    if snn:
        _start_secondarynamenode(snn)


@cpo.event_wrapper(
    True, step=utils.start_process_event_message("SecondaryNameNodes"))
def _start_secondarynamenode(snn):
    run.start_hadoop_process(snn, 'secondarynamenode')


def start_resourcemanager(cluster):
    rm = vu.get_resourcemanager(cluster)
    if rm:
        _start_resourcemanager(rm)


@cpo.event_wrapper(
    True, step=utils.start_process_event_message('ResourceManager'))
def _start_resourcemanager(snn):
    run.start_yarn_process(snn, 'resourcemanager')


def start_historyserver(cluster):
    hs = vu.get_historyserver(cluster)
    if hs:
        run.start_historyserver(hs)


def start_oozie(pctx, cluster):
    oo = vu.get_oozie(cluster)
    if oo:
        run.start_oozie_process(pctx, oo)


def start_hiveserver(pctx, cluster):
    hiveserver = vu.get_hiveserver(cluster)
    if hiveserver:
        run.start_hiveserver_process(pctx, hiveserver)


def start_spark(cluster):
    spark = vu.get_spark_history_server(cluster)
    if spark:
        run.start_spark_history_server(spark)
