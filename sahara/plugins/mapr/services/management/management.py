# Copyright (c) 2015, MapR Technologies
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import sahara.plugins.mapr.domain.node_process as np
import sahara.plugins.mapr.domain.service as s
import sahara.plugins.mapr.util.commands as cmd
import sahara.plugins.mapr.util.password_utils as pu
import sahara.plugins.mapr.util.validation_utils as vu


ZK_CLIENT_PORT = 5181

ZOOKEEPER = np.NodeProcess(
    name='mapr-zookeeper',
    ui_name='ZooKeeper',
    package='mapr-zookeeper',
    open_ports=[ZK_CLIENT_PORT]
)

WEB_SERVER = np.NodeProcess(
    name='webserver',
    ui_name='Webserver',
    package='mapr-webserver',
    open_ports=[8443]
)

METRICS = np.NodeProcess(
    name='metrics',
    ui_name='Metrics',
    package='mapr-metrics',
    open_ports=[1111]
)


class Management(s.Service):
    SSL_KEYSTORE = '/opt/mapr/conf/ssl_keystore'

    def __init__(self):
        super(Management, self).__init__()
        self._ui_name = 'Management'
        self._node_processes = [ZOOKEEPER, WEB_SERVER, METRICS]

        self._ui_info = None
        self._validation_rules = [
            vu.at_least(1, ZOOKEEPER),
            vu.at_least(1, WEB_SERVER),
            vu.odd_count_of(ZOOKEEPER),
        ]

    def post_install(self, cluster_context, instances):
        instance = cluster_context.get_instance(WEB_SERVER)
        cmd.chown(instance, 'mapr:mapr', self.SSL_KEYSTORE)

    def get_ui_info(self, cluster_context):
        # MCS uses credentials of the administrative user (PAM auth)
        return [('MapR Control System (MCS)', WEB_SERVER,
                 {s.SERVICE_UI: 'https://%s:8443',
                  'Username': pu.MAPR_USER_NAME,
                  'Password': pu.get_mapr_password(cluster_context.cluster)})]
