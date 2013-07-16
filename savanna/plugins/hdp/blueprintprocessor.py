# Copyright (c) 2013 Hortonworks, Inc.
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

from savanna.plugins.hdp import baseprocessor as b


class BlueprintProcessor(b.BaseProcessor):

    def __init__(self, blueprint):
        self.blueprint = blueprint

    def process_user_inputs(self, user_inputs):
        for ui in user_inputs:
            configurations = self.blueprint['configurations']
            properties_dict = self._find_blueprint_section(configurations,
                                                           'name',
                                                           ui.config.file)

            if properties_dict is None:
                properties_dict = {'name': ui.config.file, 'properties': []}
                configurations.append(properties_dict)

            # need to look for property with
            # the same name
            properties = properties_dict['properties']
            prop = self._find_blueprint_section(properties, 'name',
                                                ui.config.name)
            if prop is not None:
                # time to change the value
                prop['value'] = ui.value
            else:
                prop = {'name': ui.config.name, 'value': ui.value}
                properties.append(prop)

    def process_node_groups(self, node_groups):
        # we're overwriting existing settings
        if node_groups:
            for node_group in node_groups:
                # we're either replacing existing settings for the group or
                # creating a new one.  either way
                if node_group.node_processes:
                    host_role_mapping = {u'name': unicode(node_group.name),
                                         u'components': [], u'hosts': []}
                    for process in node_group.node_processes:
                        host_role_mapping[u'components'].append(
                            {u'name': unicode(process.upper())})
                    if node_group.count > 1:
                        host_role_mapping[u'hosts'].append(
                            {u'cardinality': u'1+'})
                    else:
                        host_role_mapping[u'hosts'].append(
                            {u'cardinality': u'1'})

                    existing_mapping = next(
                        (item for item in self.blueprint['host_role_mappings']
                         if item['name'] == host_role_mapping['name']), None)

                    if (existing_mapping is not None):
                        mappings__index = self.blueprint[
                            'host_role_mappings'].index(existing_mapping)
                        self.blueprint['host_role_mappings'][
                            mappings__index] = host_role_mapping
                    else:
                        self.blueprint['host_role_mappings'].append(
                            host_role_mapping)
