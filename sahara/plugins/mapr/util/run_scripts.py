# Copyright (c) 2014, MapR Technologies
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

from oslo_log import log as logging

from sahara.i18n import _LI


LOG = logging.getLogger(__name__)


def run_configure_sh(remote, script_string):
    LOG.info(_LI("running configure.sh script"))
    remote.execute_command(script_string, run_as_root=True)


def start_zookeeper(remote):
    LOG.info(_LI("Starting mapr-zookeeper"))
    remote.execute_command('service mapr-zookeeper start', run_as_root=True)


def start_oozie(remote):
    LOG.info(_LI("Starting mapr-oozie"))
    remote.execute_command('service mapr-oozie start',
                           run_as_root=True,
                           raise_when_error=False)


def start_hive_metastore(remote):
    LOG.info(_LI("Starting mapr-hive-server2"))
    remote.execute_command('service mapr-hivemetastore start',
                           run_as_root=True)


def start_hive_server2(remote):
    LOG.info(_LI("Starting mapr-hive-server2"))
    remote.execute_command('service mapr-hiveserver2 start', run_as_root=True)


def start_warden(remote):
    LOG.info(_LI("Starting mapr-warden"))
    remote.execute_command('service mapr-warden start', run_as_root=True)


def start_cldb(remote):
    LOG.info(_LI("Starting mapr-cldb"))
    remote.execute_command('service mapr-cldb start', run_as_root=True)


def start_node_manager(remote):
    LOG.info(_LI("Starting nodemanager"))
    remote.execute_command(('/opt/mapr/hadoop/hadoop-2.3.0'
                            '/sbin/yarn-daemon.sh start nodemanager'),
                           run_as_root=True)


def start_resource_manager(remote):
    LOG.info(_LI("Starting resourcemanager"))
    remote.execute_command(('/opt/mapr/hadoop/hadoop-2.3.0'
                            '/sbin/yarn-daemon.sh start resourcemanager'),
                           run_as_root=True)
