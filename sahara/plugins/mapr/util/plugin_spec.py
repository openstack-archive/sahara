# Copyright (c) 2014, MapR Technologies
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import json
import os.path

from oslo_log import log as logging
import six

import sahara.plugins.mapr.util.config_file_utils as cfu
import sahara.plugins.mapr.util.dict_utils as du
import sahara.plugins.mapr.util.func_utils as fu
import sahara.plugins.provisioning as p
import sahara.utils.files as fm


LOG = logging.getLogger(__name__)


class PluginSpec(object):

    def __init__(self, path):
        self.base_dir = os.path.dirname(path)
        self.plugin_spec_dict = self._load_plugin_spec_dict(path)
        self.service_file_name_map = self._load_service_file_name_map()
        self.default_configs = self._load_default_configs()
        self.service_node_process_map = self._load_service_node_process_map()
        self.plugin_config_objects = self._load_plugin_config_objects()
        self.file_name_config_map = self._load_file_name_config_map()
        self.plugin_config_items = self._load_plugin_config_items()
        self.plugin_configs = self._load_plugin_configs()
        self.default_plugin_configs = self._load_default_plugin_configs()
        self.file_type_map = self._load_file_type_map()

    def _load_plugin_spec_dict(self, path):
        LOG.debug('Loading plugin spec from %s', path)
        plugin_spec_dict = json.loads(fm.get_file_text(path))
        return plugin_spec_dict

    def _load_service_file_name_map(self):
        LOG.debug('Loading service -> filename mapping')
        return dict((s['name'], [fn for fn in s['files']])
                    for s in self.plugin_spec_dict['services']
                    if 'files' in s and s['files'])

    def _load_default_configs(self):
        LOG.debug('Loading defaults from local files')
        file_name_data_map = {}
        for f in self.plugin_spec_dict['files']:
            if 'local' not in f:
                LOG.debug('%s skipped. No "local" section', f['remote'])
                continue
            local_path = os.path.join(self.base_dir, f['local'])
            LOG.debug('Loading %(local_path)s as default for %(remote)s',
                      {'local_path': local_path, 'remote': f['remote']})
            data = cfu.load_file(local_path, f['type'])
            file_name_data_map[f['remote']] = data
        return du.append_to_key(self.service_file_name_map, file_name_data_map)

    def _load_plugin_config_items(self):
        LOG.debug('Loading full configs map for plugin')
        items = map(lambda i: i.to_dict(), self.plugin_config_objects)

        def mapper(item):
            file_name = du.get_keys_by_value_2(
                self.file_name_config_map, item['name'])[0]
            append_f = fu.append_field_function('file', file_name)
            return append_f(item)
        return map(mapper, items)

    def _load_plugin_configs(self):
        LOG.debug('Loading plugin configs {service:{file:{name:value}}}')
        m_fields = ['applicable_target', 'file']
        vp_fields = ('name', 'default_value')
        reducer = du.iterable_to_values_pair_dict_reducer(*vp_fields)
        return du.map_by_fields_values(self.plugin_config_items,
                                       m_fields, dict, reducer)

    def _load_default_plugin_configs(self):
        return du.deep_update(self.default_configs, self.plugin_configs)

    def _load_service_node_process_map(self):
        LOG.debug('Loading {service:[node process]} mapping')
        return dict((s['name'], [np for np in s['node_processes']])
                    for s in self.plugin_spec_dict['services']
                    if 'node_processes' in s and s['node_processes'])

    def _load_file_name_config_map(self):
        LOG.debug('Loading {filename:[config_name]} names mapping')
        r = {}
        for fd in self.plugin_spec_dict['files']:
            if 'configs' in fd:
                r[fd['remote']] = [i['name']
                                   for ir, sd in six.iteritems(fd['configs'])
                                   for s, items in six.iteritems(sd)
                                   for i in items]
        return r

    def _load_plugin_config_objects(self):
        LOG.debug('Loading config objects for sahara-dashboard')

        def mapper(item):
            req = ['name', 'applicable_target', 'scope']
            opt = ['description', 'config_type', 'config_values',
                   'default_value', 'is_optional', 'priority']
            kargs = dict((k, item[k]) for k in req + opt if k in item)
            return p.Config(**kargs)
        result = []
        for file_dict in self.plugin_spec_dict['files']:
            if 'configs' not in file_dict:
                LOG.debug('%s skipped. No "configs" section',
                          file_dict['remote'])
                continue
            remote_path = file_dict['remote']
            applicable_target = du.get_keys_by_value_2(
                self.service_file_name_map, remote_path)[0]
            for is_required, scope_dict in six.iteritems(file_dict['configs']):
                is_optional = is_required != 'required'
                for scope, items in six.iteritems(scope_dict):
                    fields = {'file': remote_path, 'is_optional': is_optional,
                              'scope': scope,
                              'applicable_target': applicable_target}
                    append_f = fu.append_fields_function(fields)
                    result.extend([append_f(i) for i in items])
        return map(mapper, result)

    def _load_file_type_map(self):
        LOG.debug('Loading {filename:type} mapping')
        return dict((f['remote'], f['type'])
                    for f in self.plugin_spec_dict['files'])

    def get_node_process_service(self, node_process):
        return du.get_keys_by_value_2(self.service_node_process_map,
                                      node_process)[0]

    def get_default_plugin_configs(self, services):
        return dict((k, self.default_plugin_configs[k])
                    for k in services if k in self.default_plugin_configs)

    def get_config_file(self, scope, service, name):
        p_template = {
            'applicable_target': service, 'scope': scope, 'name': name}
        q_fields = ['file']
        q_predicate = fu.like_predicate(p_template)
        q_source = self.plugin_config_items
        q_result = du.select(q_fields, q_source, q_predicate)
        if q_result and 'file' in q_result[0]:
            return q_result[0]['file']
        else:
            return None

    def get_file_type(self, file_name):
        if file_name in self.file_type_map:
            return self.file_type_map[file_name]
        else:
            return None

    def get_service_for_file_name(self, file_name):
        return du.get_keys_by_value_2(self.service_file_name_map, file_name)[0]

    def get_version_config_objects(self):
        common_fields = {'scope': 'cluster',
                         'config_type': 'dropdown',
                         'is_optional': False,
                         'priority': 1}

        def has_version_field(service):
            return 'versions' in service

        def get_versions(service):
            return {'name': '%s Version' % service['name'],
                    'applicable_target': service['name'],
                    'config_values': [(v, v) for v in service['versions']]}

        def add_common_fields(item):
            item.update(common_fields)
            return item

        def to_config(item):
            return p.Config(**item)

        mapper = fu.chain_function(get_versions, add_common_fields, to_config)
        source = self.plugin_spec_dict['services']
        return map(mapper, filter(has_version_field, source))

    def get_configs(self):
        return self.plugin_config_objects + self.get_version_config_objects()
