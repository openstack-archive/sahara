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


import six

import sahara.plugins.mapr.domain.node_process as np
import sahara.plugins.mapr.domain.service as s
import sahara.plugins.mapr.util.commands as cmd
import sahara.plugins.mapr.util.validation_utils as vu


HTTP_FS = np.NodeProcess(
    name='httpfs',
    ui_name='HTTPFS',
    package='mapr-httpfs',
    open_ports=[14000]
)


@six.add_metaclass(s.Single)
class HttpFS(s.Service):
    def __init__(self):
        super(HttpFS, self).__init__()
        self._name = 'httpfs'
        self._ui_name = 'HttpFS'
        self._version = '1.0'
        self._node_processes = [HTTP_FS]
        self._cluster_defaults = ['httpfs-default.json']
        self._validation_rules = [vu.at_least(1, HTTP_FS)]

    def post_install(self, cluster_context, instances):
        instance = cluster_context.get_instance(HTTP_FS)
        cmd.chown(instance, 'mapr:mapr', self.service_dir(cluster_context))
