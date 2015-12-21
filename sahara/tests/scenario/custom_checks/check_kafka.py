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

from sahara.tests.scenario import base as base_scenario
from sahara.tests.scenario import utils


class CustomCheckKafka(object):
    def __init__(self, base_class):
        self.base = base_class

    def _run_command_on_node(self, *args, **kwargs):
        return self.base._run_command_on_node(*args, **kwargs)

    def _get_nodes_with_process(self, *args, **kwargs):
        return self.base._get_nodes_with_process(*args, **kwargs)

    def fail(self, *args, **kwargs):
        return self.base.fail(*args, **kwargs)

    def _prepare_job_running(self, *args, **kwargs):
        return self.base._prepare_job_running(*args, **kwargs)

    def _job_batching(self, *args, **kwargs):
        return self.base._job_batching(*args, **kwargs)

    @property
    def _results(self):
        return self.base._results

    @_results.setter
    def _results(self, value):
        self.base._results = value

    @staticmethod
    def _get_nodes_desc_list(nodes, node_domain, port):
        data = []
        for node in nodes:
            fqdn = "{0}.{1}".format(
                node["instance_name"], node_domain)
            data.append("{0}:{1}".format(fqdn, port))
        return ",".join(data)

    def _get_node_ip(self, process):
        node = self._get_nodes_with_process(process)[0]
        return node["management_ip"]

    def _search_file_on_node(self, ip, file):
        file_path = self._run_command_on_node(
            ip, 'find / -name "{file}" 2>/dev/null -print | head -n 1'
                .format(file=file))
        if not file_path:
            self.fail("Cannot find file: {file}".format(file))
        return file_path.rstrip()

    def _create_test_topic(self, broker, topic, zookeepers):
        ip = self._get_node_ip(broker)
        scr = self._search_file_on_node(ip, "kafka-topics.sh")
        # TODO(vgridnev): Avoid hardcoded values in future
        self._run_command_on_node(
            ip, "{script} --create --zookeeper {zoo} --replication-factor "
                "1 --partitions 1 --topic {topic}".format(
                    script=scr, zoo=zookeepers, topic=topic))

    def _send_messages(self, broker, topic, broker_list):
        ip = self._get_node_ip(broker)

        scr = self._search_file_on_node(ip, "kafka-console-producer.sh")
        messages = ["<<EOF", "banana", "in", "sahara", "sahara", "data",
                    "processing", "service", "stack", "open", "stack", "EOF"]
        cmd = "{script} --broker-list {brokers} --topic {topic} {msg}"
        self._run_command_on_node(
            ip, cmd.format(
                script=scr, topic=topic, brokers=broker_list,
                msg=" ".join(messages)))

    def _prepare_spark_kafka_job_running(self, shs):
        ip = self._get_node_ip(shs)
        utils_url = (
            "http://central.maven.org/maven2/org/apache/spark"
            "/spark-streaming-kafka-assembly_2.10/1.4.1"
            "/spark-streaming-kafka-assembly_2.10-1.4.1.jar")
        # try to search spark-kafka assembly utils
        result = self._search_file_on_node(ip, "spark-streaming-kafka")
        if not result:
            self._run_command_on_node(
                ip, "wget -P /tmp/spark-utils {url}".format(
                    url=utils_url))
        return self._search_file_on_node(ip, "spark-streaming-kafka")

    @base_scenario.track_result("Check Kafka", False)
    def check(self):
        # This check will check correct work of Kafka
        # Required things to run this check:
        # Cluster running with at least one ZooKeeper server and
        # Kafka Brokers and Spark can be included too
        # Initially designed for Ambari plugin.
        ckd = self.base.testcase.get(
            'custom_checks', {}).get('check_kafka', {})
        topic = ckd.get('topic', 'test-topic')
        topic = utils.rand_name(topic)
        zk = ckd.get('zookeeper_process', "ZooKeeper")
        kb = ckd.get('kafka_process', "Kafka Broker")
        shs = ckd.get('spark_process', "Spark History Server")
        # Disable spark job running by default
        spark_flow = ckd.get('spark_flow_test', None)
        kb_port = ckd.get('kafka_port', 6667)
        zk_port = ckd.get('zookeeper_port', 2181)
        node_domain = ckd.get('node_domain', "novalocal")
        broker_list = self._get_nodes_desc_list(
            self._get_nodes_with_process(kb), node_domain, kb_port)
        zookeeper_list = self._get_nodes_desc_list(
            self._get_nodes_with_process(zk), node_domain, zk_port)
        self._create_test_topic(kb, topic, zookeeper_list)
        self._send_messages(kb, topic, broker_list)
        if spark_flow:
            dest = self._prepare_spark_kafka_job_running(shs)
            if 'configs' not in spark_flow:
                spark_flow['configs'] = {}
            # override driver classpath
            spark_flow['configs']['edp.spark.driver.classpath'] = dest
            timeout = spark_flow.get('timeout', 30)
            if 'args' not in spark_flow:
                spark_flow['args'] = []
            new_args = []
            for arg in spark_flow['args']:
                arg = arg.format(zookeeper_list=zookeeper_list,
                                 timeout=timeout, topic=topic)
                new_args.append(arg)
            spark_flow['args'] = new_args
            to_execute = [self._prepare_job_running(spark_flow)]
            self._job_batching(to_execute)


def check(self):
    CustomCheckKafka(self).check()
