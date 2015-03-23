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

from sahara.service.edp.oozie.workflow_creator import workflow_factory
from sahara.utils import xmlutils


def get_possible_hive_config_from(file_name):
    '''Return the possible configs, args, params for a Hive job.'''
    config = {
        'configs': xmlutils.load_hadoop_xml_defaults(file_name),
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
        'configs': xmlutils.load_hadoop_xml_defaults(file_name),
        'args': [],
        'params': {}
        }
    return config
