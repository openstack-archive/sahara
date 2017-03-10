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


def start_zookeeper(remote):
    remote.execute_command("sudo %s %s" % (
        "/opt/zookeeper/zookeeper/bin/zkServer.sh",
        "start"))


def start_storm_supervisor(node):
    _create_supervisor_log_file(node)
    _stop_supervisor_deamon(node)
    _start_supervisor_deamon(node)


def start_storm_nimbus_and_ui(node):
    _create_supervisor_log_file(node)
    _stop_supervisor_deamon(node)
    _start_supervisor_deamon(node)


def stop_storm_nimbus_and_ui(node):
    _stop_supervisor_deamon(node)


def stop_storm_supervisor(node):
    _stop_supervisor_deamon(node)


def _start_supervisor_deamon(node):
    node.execute_command("sudo service supervisor start")


def _stop_supervisor_deamon(node):
    node.execute_command("sudo service supervisor stop")


def _create_supervisor_log_file(node):
    node.execute_command("sudo mkdir -p /var/log/storm")
    node.execute_command("sudo chmod -R 777 /var/log/storm")
    node.execute_command("sudo chown -R storm:storm /var/log/storm")
