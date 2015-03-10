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


from sahara.plugins.mapr.base import base_version_handler as bvh
from sahara.plugins.mapr.services.management import management
from sahara.plugins.mapr.services.maprfs import maprfs
from sahara.plugins.mapr.services.spark import spark
from sahara.plugins.mapr.versions.mapr_spark import context as c
from sahara.plugins.mapr.versions.mapr_spark import spark_engine as edp_engine
from sahara.plugins.mapr.versions.mapr_spark import spark_node_manager


version = 'spark'


class VersionHandler(bvh.BaseVersionHandler):
    def __init__(self):
        super(VersionHandler, self).__init__()
        self._node_manager = spark_node_manager.SparkNodeManager()
        self._version = version
        self._required_services = [
            management.Management(),
            maprfs.MapRFS(),
            spark.Spark(),
        ]
        self._services = [
            management.Management(),
            maprfs.MapRFS(),
            spark.Spark(),
        ]

    def get_context(self, cluster, added=None, removed=None):
        return c.Context(cluster, self, added, removed)

    def get_edp_engine(self, cluster, job_type):
        if job_type in edp_engine.MapRSparkEngine.get_supported_job_types():
            return edp_engine.MapRSparkEngine(cluster)
        return None
