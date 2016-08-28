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


from oslo_log import log as logging

import sahara.plugins.mapr.domain.service as s
import sahara.plugins.mapr.services.maprfs.maprfs as maprfs
import sahara.plugins.mapr.util.event_log as el
import sahara.utils.files as f

LOG = logging.getLogger(__name__)


class Swift(s.Service):
    HADOOP_SWIFT_JAR = ('plugins/mapr/services/swift/'
                        'resources/hadoop-swift-latest.jar')

    def __init__(self):
        super(Swift, self).__init__()
        self._name = 'swift'
        self._ui_name = 'Swift'
        self._cluster_defaults = ['swift-default.json']

    def install(self, cluster_context, instances):
        # swift does not require any package
        pass

    def configure(self, context, instances=None):
        instances = instances or context.get_instances()
        file_servers = context.filter_instances(instances, maprfs.FILE_SERVER)
        self._install_swift_jar(context, file_servers)

    @el.provision_step("Install Swift service")
    def _install_swift_jar(self, context, instances):
        LOG.debug('Installing Swift jar')
        jar = f.get_file_text(Swift.HADOOP_SWIFT_JAR)
        path = '%s/swift.jar' % context.hadoop_lib

        @el.provision_event()
        def install_on_instance(inst):
            with inst.remote() as r:
                r.write_file_to(path, jar, run_as_root=True)

        for instance in instances:
            install_on_instance(instance)
