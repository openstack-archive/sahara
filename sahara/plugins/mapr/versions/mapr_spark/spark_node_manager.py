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


from sahara.plugins.mapr.base import base_node_manager
from sahara.plugins.mapr.services.spark import spark


class SparkNodeManager(base_node_manager.BaseNodeManager):
    def start(self, cluster_context, instances=None):
        super(SparkNodeManager, self).start(cluster_context, instances)

        instances = instances or cluster_context.added_instances()
        slaves = cluster_context.filter_instances(instances, spark.SPARK_SLAVE)
        if slaves:
            spark.SPARK_SLAVE.start(cluster_context, slaves)
