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
import subprocess
import sys
import tempfile

from mako import template as mako_template
from oslo_utils import fileutils
import six
import yaml

from sahara.tests.scenario import validation


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
    creds.setdefault('sahara_service_type', 'data-processing')
    creds['sahara_url'] = creds.get('sahara_url', None)
    creds['ssl_verify'] = creds.get('ssl_verify', True)
    creds['ssl_cert'] = creds.get('ssl_cert', None)

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
        if isinstance(testcase.get('edp_jobs_flow'), six.string_types):
            testcase['edp_jobs_flow'] = [testcase['edp_jobs_flow']]
        edp_jobs_flow = []
        for edp_flow in testcase.get('edp_jobs_flow', []):
            edp_jobs_flow.extend(config.get('edp_jobs_flow',
                                            {}).get(edp_flow))
        testcase['edp_jobs_flow'] = edp_jobs_flow


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


def read_template_variables(variable_file, verbose=False):
    variables = {}
    try:
        cp = six.moves.configparser.ConfigParser()
        # key-sensitive keys
        cp.optionxform = lambda option: option
        cp.readfp(open(variable_file))
        variables = cp.defaults()
    except IOError as ioe:
        print("WARNING: the input contains at least one template, but "
              "the variable configuration file '%s' is not valid: %s" %
              (variable_file, ioe))
    except six.moves.configparser.Error as cpe:
        print("WARNING: the input contains at least one template, but "
              "the variable configuration file '%s' can not be parsed: "
              "%s" % (variable_file, cpe))
    finally:
        if verbose:
            print("Template variables:\n%s" % (variables))
    # continue anyway, as the templates could require no variables
    return variables


def is_template_file(config_file):
    return config_file.endswith(('.yaml.mako', '.yml.mako'))


def read_scenario_config(scenario_config, template_vars=None,
                         verbose=False):
    """Parse the YAML or the YAML template file.

    If the file is a YAML template file, expand it first.
    """

    yaml_file = ''
    if is_template_file(scenario_config):
        scenario_template = mako_template.Template(filename=scenario_config,
                                                   strict_undefined=True)
        template = scenario_template.render_unicode(**template_vars)
        yaml_file = yaml.load(template)
    else:
        with open(scenario_config, 'r') as yaml_file:
            yaml_file = yaml.load(yaml_file)
    if verbose:
        print("YAML from %s:\n%s" % (scenario_config,
                                     yaml.safe_dump(yaml_file,
                                                    allow_unicode=True,
                                                    default_flow_style=False)))
    return yaml_file


def main():
    # parse args
    parser = argparse.ArgumentParser(description="Scenario tests runner.")
    parser.add_argument('scenario_arguments', help="Path to scenario files",
                        nargs='+')
    parser.add_argument('--variable_file', '-V', default='', nargs='?',
                        help='Path to the file with template variables')
    parser.add_argument('--verbose', default=False, action='store_true',
                        help='Increase output verbosity')
    parser.add_argument('--validate', default=False, action='store_true',
                        help='Validate yaml-files, tests will not be runned')

    args = parser.parse_args()
    scenario_arguments = args.scenario_arguments
    variable_file = args.variable_file
    verbose_run = args.verbose

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

    template_variables = {}
    if any(is_template_file(config_file) for config_file in files):
        template_variables = read_template_variables(variable_file,
                                                     verbose_run)

    for scenario_argument in files:
        test_scenario = read_scenario_config(scenario_argument,
                                             template_variables, verbose_run)
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

    # validate config
    validation.validate(config)

    if args.validate:
        return

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
    return_code = subprocess.call(command, shell=True)
    sys.exit(return_code)


if __name__ == '__main__':
    main()
