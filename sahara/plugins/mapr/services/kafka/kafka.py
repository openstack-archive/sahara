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

KAFKA = np.NodeProcess(
    name='kafka',
    ui_name='Kafka',
    package='mapr-kafka',
    open_ports=[9092]
)

KAFKA_REST = np.NodeProcess(
    name='kafka',
    ui_name='Kafka Rest',
    package='mapr-kafka-rest',
    open_ports=[8082]
)

KAFKA_CONNECT_HDFS = np.NodeProcess(
    name='kafka',
    ui_name='Kafka Connect HDFS',
    package='mapr-kafka-connect-hdfs'
)

KAFKA_CONNECT_JDBC = np.NodeProcess(
    name='kafka',
    ui_name='Kafka Connect JDBC',
    package='mapr-kafka-connect-jdbc'
)


class Kafka(s.Service):
    def __init__(self):
        super(Kafka, self).__init__()
        self._version = '0.9.0'
        self._name = 'kafka'
        self._ui_name = 'Kafka'
        self._node_processes = [KAFKA]


class KafkaRest(s.Service):
    def __init__(self):
        super(KafkaRest, self).__init__()
        self._version = '2.0.1'
        self._name = 'kafka-eco'
        self._ui_name = 'Kafka Rest'
        self._node_processes = [KAFKA_REST]
        self._validation_rules = [vu.at_least(1, KAFKA)]


class KafkaConnect(s.Service):
    def __init__(self):
        super(KafkaConnect, self).__init__()
        self._version = '2.0.1'
        self._name = 'kafka-connect'
        self._ui_name = 'Kafka Connect'
        self._node_processes = [KAFKA_CONNECT_HDFS, KAFKA_CONNECT_JDBC]
        self._validation_rules = [vu.at_least(1, KAFKA)]
