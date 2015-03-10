#!/usr/bin/env python

# Copyright (c) 2015 Mirantis Inc.
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

from __future__ import print_function
import argparse
import os
import sys
import tempfile

from mako import template as mako_template
import yaml

from sahara.openstack.common import fileutils


TEST_TEMPLATE_PATH = 'sahara/tests/scenario/testcase.py.mako'


def set_defaults(config):
    # set up credentials
    config['credentials'] = config.get('credentials', {})
    creds = config['credentials']
    creds['os_username'] = creds.get('os_username', 'admin')
    creds['os_password'] = creds.get('os_password', 'nova')
    creds['os_tenant'] = creds.get('os_tenant', 'admin')
    creds['os_auth_url'] = creds.get('os_auth_url',
                                     'http://localhost:5000/v2.0')
    creds['sahara_url'] = creds.get('sahara_url', None)

    # set up network
    config['network'] = config.get('network', {})
    net = config['network']
    net['type'] = net.get('type', 'neutron')
    net['private_network'] = net.get('private_network', 'private')
    net['auto_assignment_floating_ip'] = net.get('auto_assignment_floating_ip',
                                                 False)
    net['public_network'] = net.get('public_network', 'public')

    default_scenario = ['run_jobs', 'scale', 'run_jobs']

    # set up tests parameters
    for testcase in config['clusters']:
        testcase['class_name'] = "".join([
            testcase['plugin_name'],
            testcase['plugin_version'].replace('.', '_')])
        testcase['retain_resources'] = testcase.get('retain_resources', False)
        testcase['scenario'] = testcase.get('scenario', default_scenario)
        testcase['edp_jobs_flow'] = (
            config.get('edp_jobs_flow', {}).get(
                testcase.get('edp_jobs_flow', None), None))


def _merge_dicts_sections(dict_with_section, dict_for_merge, section):
    if dict_with_section.get(section) is not None:
        for key in dict_with_section[section]:
            if dict_for_merge[section].get(key) is not None:
                if dict_for_merge[section][key] != (
                        dict_with_section[section][key]):
                    raise ValueError('Sections %s is different' % section)
            else:
                dict_for_merge[section][key] = dict_with_section[section][key]
    return dict_for_merge


def recursive_walk(directory):
    list_of_files = []
    for file in os.listdir(directory):
        path = os.path.join(directory, file)
        if os.path.isfile(path):
            list_of_files.append(path)
        else:
            list_of_files += recursive_walk(path)
    return list_of_files


def main():
    # parse args
    parser = argparse.ArgumentParser(description="Scenario tests runner.")
    parser.add_argument('scenario_arguments', help="Path to scenario files",
                        nargs='+')
    args = parser.parse_args()
    scenario_arguments = args.scenario_arguments

    # parse config
    config = {'credentials': {},
              'network': {},
              'clusters': [],
              'edp_jobs_flow': {}}
    files = []
    for scenario_argument in scenario_arguments:
        if os.path.isdir(scenario_argument):
            files += recursive_walk(scenario_argument)
        if os.path.isfile(scenario_argument):
            files.append(scenario_argument)
    for scenario_argument in files:
        with open(scenario_argument, 'r') as yaml_file:
            test_scenario = yaml.load(yaml_file)
        config = _merge_dicts_sections(test_scenario, config, 'credentials')
        config = _merge_dicts_sections(test_scenario, config, 'network')

        if test_scenario.get('clusters') is not None:
            config['clusters'] += test_scenario['clusters']

        if test_scenario.get('edp_jobs_flow') is not None:
            for key in test_scenario['edp_jobs_flow']:
                if key not in config['edp_jobs_flow']:
                    config['edp_jobs_flow'][key] = (
                        test_scenario['edp_jobs_flow'][key])
                else:
                    raise ValueError('Job flow exist')

    set_defaults(config)
    credentials = config['credentials']
    network = config['network']
    testcases = config['clusters']

    # create testcase file
    test_template = mako_template.Template(filename=TEST_TEMPLATE_PATH)
    testcase_data = test_template.render(testcases=testcases,
                                         credentials=credentials,
                                         network=network)

    test_dir_path = tempfile.mkdtemp()
    print("The generated test file located at: %s" % test_dir_path)
    fileutils.write_to_tempfile(testcase_data, prefix='test_', suffix='.py',
                                path=test_dir_path)

    # run tests
    concurrency = config.get('concurrency')
    os.environ['DISCOVER_DIRECTORY'] = test_dir_path
    command = 'bash tools/pretty_tox.sh'
    if concurrency:
        command = command + ' -- --concurrency %d' % concurrency
    return_code = os.system(command)
    sys.exit(return_code)


if __name__ == '__main__':
    main()
