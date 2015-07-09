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


from sahara.tests.scenario import base


@base.track_result("Check sentry")
def check(self):
    nodes = self._get_nodes_with_process('HBASE_MASTER')
    for node in nodes:
        node_ip = node['management_ip']
        conffile_dir = self._run_command_on_node(
            node_ip,
            'sudo find / -name "*-sentry-SENTRY_SERVER" | head -1'
        )
        self._run_command_on_node(
            node_ip, 'sudo cp %s/sentry-site.xml /tmp/sentry-site.xml'
                     % conffile_dir)
        self._run_command_on_node(node_ip,
                                  'sudo chmod 664 /tmp/sentry-site.xml')
        psql_jar = self._run_command_on_node(
            node_ip, 'ls /usr/share/cmf/lib/postgresql* | head -1')
        self._run_command_on_node(node_ip,
                                  'export HADOOP_CLASSPATH=:%s' % psql_jar)
        self._run_command_on_node(
            node_ip,
            'sentry --command schema-tool -conffile /tmp/sentry-site.xml '
            '-dbType postgres -info')
