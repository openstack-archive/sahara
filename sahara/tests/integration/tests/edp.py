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
from oslo.utils import excutils
import six

from sahara.swift import swift_helper as sw
from sahara.tests.integration.tests import base
from sahara.utils import edp


class EDPJobInfo(object):
    PIG_PATH = 'etc/edp-examples/pig-job/'
    JAVA_PATH = 'etc/edp-examples/edp-java/'
    MAPREDUCE_PATH = 'etc/edp-examples/edp-mapreduce/'
    SPARK_PATH = 'etc/edp-examples/edp-spark/'

    HADOOP2_JAVA_PATH = 'etc/edp-examples/hadoop2/edp-java/'

    def read_pig_example_script(self):
        return open(self.PIG_PATH + 'example.pig').read()

    def read_pig_example_jar(self):
        return open(self.PIG_PATH + 'udf.jar').read()

    def read_java_example_lib(self, hadoop_vers=1):
        if hadoop_vers == 1:
            return open(self.JAVA_PATH + 'edp-java.jar').read()
        return open(self.HADOOP2_JAVA_PATH + (
            'hadoop-mapreduce-examples-2.3.0.jar')).read()

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
                'mapred.mapper.class': 'org.apache.oozie.example.SampleMapper',
                'mapred.reducer.class':
                'org.apache.oozie.example.SampleReducer'
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
        return self.sahara.data_sources.create(
            name, description, data_type, url, self.common_config.OS_USERNAME,
            self.common_config.OS_PASSWORD).id

    def _create_job_binary_internals(self, name, data):
        return self.sahara.job_binary_internals.create(name, data).id

    def _create_job_binary(self, name, url, extra=None, description=None):
        return self.sahara.job_binaries.create(
            name, url, description or '', extra or {}).id

    def _create_job(self, name, job_type, mains, libs):
        return self.sahara.jobs.create(name, job_type, mains, libs,
                                       description='').id

    def _await_job_execution(self, job):
        timeout = self.common_config.JOB_LAUNCH_TIMEOUT * 60
        status = self.sahara.job_executions.get(job.id).info['status']
        try:
            with fixtures.Timeout(timeout, gentle=True):
                while status != edp.JOB_STATUS_SUCCEEDED:
                    if status == edp.JOB_STATUS_KILLED:
                        self.fail("Job status == '{0}'.".format(
                            edp.JOB_STATUS_KILLED))

                    time.sleep(10)
                    status = self.sahara.job_executions.get(
                        job.id).info['status']

        except fixtures.TimeoutException:
            self.fail(
                "Job did not return to '{0}' status within {1:d} minute(s)."
                .format(edp.JOB_STATUS_SUCCEEDED,
                        self.common_config.JOB_LAUNCH_TIMEOUT)
            )

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

    def _delete_job(self, execution_job, job_id, job_binary_list,
                    job_binary_internal_list, input_id, output_id):
        if execution_job:
            self.sahara.job_executions.delete(execution_job.id)
        if job_id:
            self.sahara.jobs.delete(job_id)
        if job_binary_list:
            for job_binary_id in job_binary_list:
                self.sahara.job_binaries.delete(job_binary_id)
        if job_binary_internal_list:
            for internal_id in job_binary_internal_list:
                self.sahara.job_binary_internals.delete(internal_id)
        if input_id:
            self.sahara.data_sources.delete(input_id)
        if output_id:
            self.sahara.data_sources.delete(output_id)

    def _add_swift_configs(self, configs):

        if "configs" not in configs:
            configs["configs"] = {}

        if sw.HADOOP_SWIFT_USERNAME not in configs["configs"]:
            configs["configs"][
                sw.HADOOP_SWIFT_USERNAME] = self.common_config.OS_USERNAME
        if sw.HADOOP_SWIFT_PASSWORD not in configs["configs"]:
            configs["configs"][
                sw.HADOOP_SWIFT_PASSWORD] = self.common_config.OS_PASSWORD

    @base.skip_test('SKIP_EDP_TEST',
                    'Test for EDP was skipped.')
    def edp_testing(self, job_type, job_data_list, lib_data_list=None,
                    configs=None, pass_input_output_args=False,
                    swift_binaries=False, hdfs_local_output=False):
        job_data_list = job_data_list or []
        lib_data_list = lib_data_list or []
        configs = configs or {}

        try:
            swift = self.connect_to_swift()
            container_name = 'Edp-test-%s' % str(uuid.uuid4())[:8]
            swift.put_container(container_name)
            swift.put_object(
                container_name, 'input', ''.join(
                    random.choice(':' + ' ' + '\n' + string.ascii_lowercase)
                    for x in six.moves.range(10000)
                )
            )

        except Exception as e:
            with excutils.save_and_reraise_exception():
                self.delete_swift_container(swift, container_name)
                print(str(e))
        input_id = None
        output_id = None
        job_id = None
        job_execution = None
        try:
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

            # Java jobs don't use data sources.  Input/output paths must
            # be passed as args with corresponding username/password configs
            if not edp.compare_job_type(job_type,
                                        edp.JOB_TYPE_JAVA,
                                        edp.JOB_TYPE_SPARK):
                input_id = self._create_data_source(
                    'input-%s' % str(uuid.uuid4())[:8], 'swift',
                    swift_input_url)
                output_id = self._create_data_source(
                    'output-%s' % str(uuid.uuid4())[:8], output_type,
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
                self._add_swift_configs(configs)
                if "args" in configs:
                    configs["args"].extend([swift_input_url,
                                            output_url])
                else:
                    configs["args"] = [swift_input_url,
                                       output_url]

            job_execution = self.sahara.job_executions.create(
                job_id, self.cluster_id, input_id, output_id,
                configs=configs)

            if job_execution:
                self._await_job_execution(job_execution)

        except Exception as e:
            with excutils.save_and_reraise_exception():
                print(str(e))

        finally:
            self.delete_swift_container(swift, container_name)
            self._delete_job(
                job_execution, job_id, job_binary_list + lib_binary_list,
                job_binary_internal_list, input_id, output_id
            )
