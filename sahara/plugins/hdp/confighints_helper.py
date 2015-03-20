# Copyright (c) 2015 Red Hat, Inc.
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

from oslo_serialization import jsonutils as json

from sahara.service.edp.oozie.workflow_creator import workflow_factory
from sahara.utils import files as pkg


def get_possible_hive_config_from(file_name):
    '''Return the possible configs, args, params for a Hive job.'''
    config = {
        'configs': load_hadoop_json_for_tag(file_name, 'hive-site.xml'),
        'params': {}
        }
    return config


def get_possible_mapreduce_config_from(file_name):
    '''Return the possible configs, args, params for a MapReduce job.'''
    config = {
        'configs': get_possible_pig_config_from(file_name).get('configs')
        }
    config['configs'] += workflow_factory.get_possible_mapreduce_configs()
    return config


def get_possible_pig_config_from(file_name):
    '''Return the possible configs, args, params for a Pig job.'''
    config = {
        'configs': load_hadoop_json_for_tag(file_name, 'mapred-site.xml'),
        'args': [],
        'params': {}
        }
    return config


def get_properties_for_tag(configurations, tag_name):
    '''Get the properties for a tag

    Given a list of configurations, return the properties for the named tag.
    If the named tag cannot be found returns an empty list.

    '''
    for obj in configurations:
        if obj.get('tag') == tag_name:
            return obj.get('properties')
    return []


def load_hadoop_json_for_tag(file_name, tag_name):
    '''Given a file name and a tag, return the configs from that tag.'''
    full_json = load_json_file(file_name)
    properties = get_properties_for_tag(full_json['configurations'], tag_name)
    configs = []
    for prop in properties:
        configs.append({
            'name': prop.get('name'),
            'value': prop.get('default_value'),
            'description': prop.get('description')
        })
    return configs


def load_json_file(file_name):
    '''Given a package relative json file name, return the json.'''
    ftext = pkg.get_file_text(file_name)
    loaded_json = json.loads(ftext)
    return loaded_json
