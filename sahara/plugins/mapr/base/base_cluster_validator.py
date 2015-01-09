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


import sahara.plugins.mapr.abstract.cluster_validator as v
import sahara.plugins.mapr.util.validation_utils as vu
import sahara.plugins.mapr.versions.version_handler_factory as vhf


class BaseValidator(v.AbstractValidator):
    def validate(self, cluster_context):
        for service in cluster_context.required_services:
            vu.assert_present(service, cluster_context)
        for service in cluster_context.cluster_services:
            for rule in service.validation_rules:
                rule(cluster_context)

    def validate_scaling(self, cluster_context, existing, additional):
        cluster = cluster_context.cluster
        version = cluster.hadoop_version
        handler = vhf.VersionHandlerFactory.get().get_handler(version)
        cluster = vu.create_fake_cluster(cluster, existing, additional)
        cluster_context = handler.get_context(cluster)
        self.validate(cluster_context)
