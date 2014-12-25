# Copyright (c) 2013 Mirantis Inc.
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

import random
import string
import time
import uuid

import fixtures
import six

from sahara.service.edp import job_utils
from sahara.tests.integration.tests import base
from sahara.utils import edp


class EDPJobInfo(object):
    PIG_PATH = 'etc/edp-examples/edp-pig/trim-spaces/'
    JAVA_PATH = 'etc/edp-examples/edp-java/'
    MAPREDUCE_PATH = 'etc/edp-examples/edp-mapreduce/'
    SPARK_PATH = 'etc/edp-examples/edp-spark/'
    HIVE_PATH = 'etc/edp-examples/edp-hive/'

    HADOOP2_JAVA_PATH = 'etc/edp-examples/hadoop2/edp-java/'

    def read_hive_example_script(self):
        return open(self.HIVE_PATH + 'script.q').read()

    def read_hive_example_input(self):
        return open(self.HIVE_PATH + 'input.csv').read()

    def read_pig_example_script(self):
        return open(self.PIG_PATH + 'example.pig').read()

    def read_pig_example_jar(self):
        return open(self.PIG_PATH + 'udf.jar').read()

    def read_java_example_lib(self, hadoop_vers=1):
        if hadoop_vers == 1:
            return open(self.JAVA_PATH + 'edp-java.jar').read()
        return open(self.HADOOP2_JAVA_PATH + (
            'hadoop-mapreduce-examples-2.4.1.jar')).read()

    def java_example_configs(self, hadoop_vers=1):
        if hadoop_vers == 1:
            return {
                'configs': {
                    'edp.java.main_class':
                    'org.openstack.sahara.examples.WordCount'
                }
            }

        return {
            'configs': {
                'edp.java.main_class':
                'org.apache.hadoop.examples.QuasiMonteCarlo'
            },
            'args': ['10', '10']
        }

    def read_mapreduce_example_jar(self):
        return open(self.MAPREDUCE_PATH + 'edp-mapreduce.jar').read()

    def mapreduce_example_configs(self):
        return {
            'configs': {
                'dfs.replication': '1',  # for Hadoop 1 only
                'mapred.mapper.class': 'org.apache.oozie.example.SampleMapper',
                'mapred.reducer.class':
                'org.apache.oozie.example.SampleReducer'
            }
        }

    def pig_example_configs(self):
        return {
            'configs': {
                'dfs.replication': '1'  # for Hadoop 1 only
            }
        }

    def mapreduce_streaming_configs(self):
        return {
            "configs": {
                "edp.streaming.mapper": "/bin/cat",
                "edp.streaming.reducer": "/usr/bin/wc"
            }
        }

    def read_spark_example_jar(self):
        return open(self.SPARK_PATH + 'spark-example.jar').read()

    def spark_example_configs(self):
        return {
            'configs': {
                'edp.java.main_class':
                'org.apache.spark.examples.SparkPi'
            },
            'args': ['4']
        }


class EDPTest(base.ITestCase):
    def setUp(self):
        super(EDPTest, self).setUp()
        self.edp_info = EDPJobInfo()

    def _create_data_source(self, name, data_type, url, description=''):
        source_id = self.sahara.data_sources.create(
            name, description, data_type, url, self.common_config.OS_USERNAME,
            self.common_config.OS_PASSWORD).id
        if not self.common_config.RETAIN_EDP_AFTER_TEST:
            self.addCleanup(self.sahara.data_sources.delete, source_id)
        return source_id

    def _create_job_binary_internals(self, name, data):
        job_binary_id = self.sahara.job_binary_internals.create(name, data).id
        if not self.common_config.RETAIN_EDP_AFTER_TEST:
            self.addCleanup(self.sahara.job_binary_internals.delete,
                            job_binary_id)
        return job_binary_id

    def _create_job_binary(self, name, url, extra=None, description=None):
        job_binary_id = self.sahara.job_binaries.create(
            name, url, description or '', extra or {}).id
        if not self.common_config.RETAIN_EDP_AFTER_TEST:
            self.addCleanup(self.sahara.job_binaries.delete, job_binary_id)
        return job_binary_id

    def _create_job(self, name, job_type, mains, libs):
        job_id = self.sahara.jobs.create(name, job_type, mains, libs,
                                         description='').id
        if not self.common_config.RETAIN_EDP_AFTER_TEST:
            self.addCleanup(self.sahara.jobs.delete, job_id)
        return job_id

    def _get_job_status(self, job_id):
        return self.sahara.job_executions.get(job_id).info['status']

    def poll_jobs_status(self, job_ids):
        timeout = self.common_config.JOB_LAUNCH_TIMEOUT * 60 * len(job_ids)
        try:
            with fixtures.Timeout(timeout, gentle=True):
                success = False
                while not success:
                    success = True
                    for job_id in job_ids:
                        status = self._get_job_status(job_id)
                        if status in [edp.JOB_STATUS_FAILED,
                                      edp.JOB_STATUS_KILLED,
                                      edp.JOB_STATUS_DONEWITHERROR]:
                            self.fail(
                                'Job status "%s" \'%s\'.' % (job_id, status))
                        if status != edp.JOB_STATUS_SUCCEEDED:
                            success = False

                    time.sleep(5)
        except fixtures.TimeoutException:
            self.fail(
                "Jobs did not return to '{0}' status within {1:d} minute(s)."
                .format(edp.JOB_STATUS_SUCCEEDED, timeout / 60))

    def _create_job_binaries(self, job_data_list, job_binary_internal_list,
                             job_binary_list, swift_connection=None,
                             container_name=None):
        for job_data in job_data_list:
            name = 'binary-job-%s' % str(uuid.uuid4())[:8]
            if isinstance(job_data, dict):
                for key, value in job_data.items():
                        name = 'binary-job-%s.%s' % (
                            str(uuid.uuid4())[:8], key)
                        data = value
            else:
                data = job_data

            if swift_connection:
                swift_connection.put_object(container_name, name, data)
                job_binary = self._create_job_binary(
                    name, 'swift://%s.sahara/%s' % (container_name, name),
                    extra={
                        'user': self.common_config.OS_USERNAME,
                        'password': self.common_config.OS_PASSWORD
                    }
                )
                job_binary_list.append(job_binary)
            else:
                job_binary_internal_list.append(
                    self._create_job_binary_internals(name, data)
                )
                job_binary_list.append(
                    self._create_job_binary(
                        name, 'internal-db://%s' % job_binary_internal_list[-1]
                    )
                )

    def _enable_substitution(self, configs):

        if "configs" not in configs:
            configs["configs"] = {}

        configs['configs'][job_utils.DATA_SOURCE_SUBST_NAME] = True
        configs['configs'][job_utils.DATA_SOURCE_SUBST_UUID] = True

    @base.skip_test('SKIP_EDP_TEST', 'Test for EDP was skipped.')
    def check_edp_hive(self):
        hdfs_input_path = '/user/hive/warehouse/input.csv'
        # put input data to HDFS
        self.put_file_to_hdfs(
            self.cluster_info['node_info']['namenode_ip'],
            hdfs_input_path, self.edp_info.read_hive_example_input())

        input_id = self._create_data_source(self.rand_name('hive-input'),
                                            'hdfs', hdfs_input_path)
        output_id = self._create_data_source(self.rand_name('hive-output'),
                                             'hdfs',
                                             '/user/hive/warehouse/output')
        script_id = self._create_job_binary_internals(
            self.rand_name('hive-script'),
            self.edp_info.read_hive_example_script())
        job_binary_id = self._create_job_binary(self.rand_name('hive-edp'),
                                                'internal-db://%s' % script_id)
        job_id = self._create_job(self.rand_name('edp-test-hive'),
                                  edp.JOB_TYPE_HIVE,
                                  [job_binary_id], [])
        job_execution_id = self.sahara.job_executions.create(
            job_id, self.cluster_id, input_id, output_id, {}).id
        if not self.common_config.RETAIN_EDP_AFTER_TEST:
            self.addCleanup(self.sahara.job_executions.delete,
                            job_execution_id)
        return job_execution_id

    @base.skip_test('SKIP_EDP_TEST', 'Test for EDP was skipped.')
    def edp_testing(self, job_type, job_data_list, lib_data_list=None,
                    configs=None, pass_input_output_args=False,
                    swift_binaries=False, hdfs_local_output=False):
        job_data_list = job_data_list or []
        lib_data_list = lib_data_list or []
        configs = configs or {}

        swift = self.connect_to_swift()
        container_name = 'Edp-test-%s' % str(uuid.uuid4())[:8]
        swift.put_container(container_name)
        if not self.common_config.RETAIN_EDP_AFTER_TEST:
            self.addCleanup(self.delete_swift_container, swift, container_name)
        swift.put_object(
            container_name, 'input', ''.join(
                random.choice(':' + ' ' + '\n' + string.ascii_lowercase)
                for x in six.moves.range(10000)
            )
        )

        input_id = None
        output_id = None
        job_id = None
        job_execution = None
        job_binary_list = []
        lib_binary_list = []
        job_binary_internal_list = []

        swift_input_url = 'swift://%s.sahara/input' % container_name
        if hdfs_local_output:
            # This will create a file in hdfs under the user
            # executing the job (i.e. /usr/hadoop/Edp-test-xxxx-out)
            output_type = "hdfs"
            output_url = container_name + "-out"
        else:
            output_type = "swift"
            output_url = 'swift://%s.sahara/output' % container_name

        input_name = 'input-%s' % str(uuid.uuid4())[:8]
        input_id = self._create_data_source(input_name,
                                            'swift', swift_input_url)

        output_name = 'output-%s' % str(uuid.uuid4())[:8]
        output_id = self._create_data_source(output_name,
                                             output_type,
                                             output_url)

        if job_data_list:
            if swift_binaries:
                self._create_job_binaries(job_data_list,
                                          job_binary_internal_list,
                                          job_binary_list,
                                          swift_connection=swift,
                                          container_name=container_name)
            else:
                self._create_job_binaries(job_data_list,
                                          job_binary_internal_list,
                                          job_binary_list)

        if lib_data_list:
            if swift_binaries:
                self._create_job_binaries(lib_data_list,
                                          job_binary_internal_list,
                                          lib_binary_list,
                                          swift_connection=swift,
                                          container_name=container_name)
            else:
                self._create_job_binaries(lib_data_list,
                                          job_binary_internal_list,
                                          lib_binary_list)

        job_id = self._create_job(
            'Edp-test-job-%s' % str(uuid.uuid4())[:8], job_type,
            job_binary_list, lib_binary_list)
        if not configs:
            configs = {}

        # TODO(tmckay): for spark we don't have support for swift
        # yet.  When we do, we'll need something to here to set up
        # swift paths and we can use a spark wordcount job

        # Append the input/output paths with the swift configs
        # if the caller has requested it...
        if edp.compare_job_type(
                job_type, edp.JOB_TYPE_JAVA) and pass_input_output_args:
            self._enable_substitution(configs)
            input_arg = job_utils.DATA_SOURCE_PREFIX + input_name
            output_arg = output_id
            if "args" in configs:
                configs["args"].extend([input_arg, output_arg])
            else:
                configs["args"] = [input_arg, output_arg]

        job_execution = self.sahara.job_executions.create(
            job_id, self.cluster_id, input_id, output_id,
            configs=configs)
        if not self.common_config.RETAIN_EDP_AFTER_TEST:
            self.addCleanup(self.sahara.job_executions.delete,
                            job_execution.id)

        return job_execution.id
