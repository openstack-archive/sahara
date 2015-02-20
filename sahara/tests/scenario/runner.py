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


def main():
    # parse args
    parser = argparse.ArgumentParser(description="Scenario tests runner.")
    parser.add_argument('scenario_file', help="Path to scenario file.")
    args = parser.parse_args()
    scenario_file = args.scenario_file

    # parse config
    with open(scenario_file, 'r') as yaml_file:
        config = yaml.load(yaml_file)

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
    os.environ['DISCOVER_DIRECTORY'] = test_dir_path
    return_code = os.system('bash tools/pretty_tox.sh')
    sys.exit(return_code)


if __name__ == '__main__':
    main()
