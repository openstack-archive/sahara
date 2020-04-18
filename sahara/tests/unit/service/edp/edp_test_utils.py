# Copyright (c) 2014 Mirantis Inc.
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


from unittest import mock

from oslo_utils import uuidutils

from sahara import conductor as cond
from sahara.utils import edp


conductor = cond.API

_java_main_class = "org.apache.hadoop.examples.WordCount"
_java_opts = "-Dparam1=val1 -Dparam2=val2"


def create_job_exec(type, configs=None, proxy=False, info=None):
    b = create_job_binary('1', type)
    j = _create_job('2', b, type)
    _cje_func = _create_job_exec_with_proxy if proxy else _create_job_exec
    e = _cje_func(j.id, type, configs, info)
    return j, e


def _create_job(id, job_binary, type):
    job = mock.Mock()
    job.id = id
    job.type = type
    job.name = 'special_name'
    job.interface = []
    if edp.compare_job_type(type, edp.JOB_TYPE_PIG, edp.JOB_TYPE_HIVE):
        job.mains = [job_binary]
        job.libs = None
    else:
        job.libs = [job_binary]
        job.mains = None
    return job


def create_job_binary(id, type):
    binary = mock.Mock()
    binary.id = id
    binary.url = "internal-db://42"
    if edp.compare_job_type(type, edp.JOB_TYPE_PIG):
        binary.name = "script.pig"
    elif edp.compare_job_type(type, edp.JOB_TYPE_MAPREDUCE, edp.JOB_TYPE_JAVA):
        binary.name = "main.jar"
    else:
        binary.name = "script.q"
    return binary


def create_cluster(plugin_name='fake', hadoop_version='0.1'):
    cluster = mock.Mock()
    cluster.plugin_name = plugin_name
    cluster.hadoop_version = hadoop_version
    return cluster


def create_data_source(url, name=None, id=None):
    data_source = mock.Mock()
    data_source.url = url
    if url.startswith("swift"):
        data_source.type = "swift"
        data_source.credentials = {'user': 'admin',
                                   'password': 'admin1'}
    elif url.startswith("hdfs"):
        data_source.type = "hdfs"
    if name is not None:
        data_source.name = name
    if id is not None:
        data_source.id = id
    return data_source


def _create_job_exec(job_id, type, configs=None, info=None):
    j_exec = mock.Mock()
    j_exec.id = uuidutils.generate_uuid()
    j_exec.job_id = job_id
    j_exec.job_configs = configs
    j_exec.info = info
    j_exec.input_id = 4
    j_exec.output_id = 5
    j_exec.engine_job_id = None
    j_exec.data_source_urls = {}
    if not j_exec.job_configs:
        j_exec.job_configs = {}
    if edp.compare_job_type(type, edp.JOB_TYPE_JAVA):
        j_exec.job_configs['configs']['edp.java.main_class'] = _java_main_class
        j_exec.job_configs['configs']['edp.java.java_opts'] = _java_opts
    return j_exec


def _create_job_exec_with_proxy(job_id, type, configs=None, info=None):
    j_exec = _create_job_exec(job_id, type, configs)
    j_exec.id = '00000000-1111-2222-3333-4444444444444444'
    j_exec.info = info
    j_exec.job_configs['proxy_configs'] = {
        'proxy_username': 'job_' + j_exec.id,
        'proxy_password': '55555555-6666-7777-8888-999999999999',
        'proxy_trust_id': '0123456789abcdef0123456789abcdef'
        }
    return j_exec
