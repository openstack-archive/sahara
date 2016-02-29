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
import sahara.plugins.mapr.util.validation_utils as vu

PIG = np.NodeProcess(
    name='pig',
    ui_name='Pig',
    package='mapr-pig'
)


class Pig(s.Service):
    def __init__(self):
        super(Pig, self).__init__()
        self._name = 'pig'
        self._ui_name = 'Pig'
        self._node_processes = [PIG]
        self._validation_rules = [vu.at_least(1, PIG)]


class PigV013(Pig):
    def __init__(self):
        super(PigV013, self).__init__()
        self._version = '0.13'


class PigV014(Pig):
    def __init__(self):
        super(PigV014, self).__init__()
        self._version = '0.14'


class PigV015(Pig):
    def __init__(self):
        super(PigV015, self).__init__()
        self._version = '0.15'
