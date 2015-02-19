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
import sahara.plugins.mapr.util.validation_utils as vu


FLUME = np.NodeProcess(
    name='flume',
    ui_name='Flume',
    package='mapr-flume',
    open_ports=[]
)


@six.add_metaclass(s.Single)
class Flume(s.Service):
    def __init__(self):
        super(Flume, self).__init__()
        self._name = 'flume'
        self._ui_name = 'Flume'
        self._version = '1.5.0'
        self._node_processes = [FLUME]
        self._validation_rules = [vu.at_least(1, FLUME)]
