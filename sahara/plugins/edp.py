# Copyright (c) 2018 Red Hat, Inc.
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

from sahara.service.edp import hdfs_helper
from sahara.service.edp import job_utils
from sahara.service.edp.oozie import engine as oozie_engine
from sahara.service.edp.oozie.workflow_creator import workflow_factory
from sahara.service.edp.spark import engine as spark_engine
from sahara.service.edp.storm import engine as storm_engine
from sahara.utils import edp

JOB_TYPE_HIVE = edp.JOB_TYPE_HIVE
JOB_TYPE_SPARK = edp.JOB_TYPE_SPARK
JOB_TYPE_JAVA = edp.JOB_TYPE_JAVA
JOB_TYPE_SHELL = edp.JOB_TYPE_SHELL
JOB_TYPE_PIG = edp.JOB_TYPE_PIG
JOB_TYPE_STORM = edp.JOB_TYPE_STORM
JOB_TYPE_PYLEUS = edp.JOB_TYPE_PYLEUS
JOB_TYPE_MAPREDUCE = edp.JOB_TYPE_MAPREDUCE
JOB_TYPE_MAPREDUCE_STREAMING = edp.JOB_TYPE_MAPREDUCE_STREAMING
JOB_TYPES_ALL = edp.JOB_TYPES_ALL
JOB_STATUS_SUCCEEDED = edp.JOB_STATUS_SUCCEEDED


class PluginsStormJobEngine(storm_engine.StormJobEngine):

    def __init__(self, cluster, **kwargs):
        super(PluginsStormJobEngine, self).__init__(cluster)


class PluginsStormPyleusJobEngine(storm_engine.StormPyleusJobEngine):

    def __init__(self, cluster, **kwargs):
        super(PluginsStormPyleusJobEngine, self).__init__(cluster)


class PluginsSparkJobEngine(spark_engine.SparkJobEngine):

    def __init__(self, cluster, **kwargs):
        super(PluginsSparkJobEngine, self).__init__(cluster)


class PluginsSparkShellJobEngine(spark_engine.SparkShellJobEngine):

    def __init__(self, cluster, **kwargs):
        super(PluginsSparkShellJobEngine, self).__init__(cluster)


class PluginsOozieJobEngine(oozie_engine.OozieJobEngine):

    def __init__(self, cluster, **kwargs):
        super(PluginsOozieJobEngine, self).__init__(cluster)


def get_hive_shared_conf_path(hdfs_user, **kwargs):
    return edp.get_hive_shared_conf_path(hdfs_user)


def compare_job_type(job_type, *args, **kwargs):
    return edp.compare_job_type(job_type, *args, **kwargs)


def get_builtin_binaries(job, configs, **kwargs):
    return edp.get_builtin_binaries(job, configs)


def create_dir_hadoop2(r, dir_name, hdfs_user, **kwargs):
    hdfs_helper.create_dir_hadoop2(r, dir_name, hdfs_user)


def create_hbase_common_lib(r, **kwargs):
    hdfs_helper.create_hbase_common_lib(r)


def get_plugin(cluster, **kwargs):
    return job_utils.get_plugin(cluster)


def get_possible_job_config(job_type, **kwargs):
    return workflow_factory.get_possible_job_config(job_type)


def get_possible_mapreduce_configs(**kwargs):
    return workflow_factory.get_possible_mapreduce_configs()
