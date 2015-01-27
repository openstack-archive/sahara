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

import copy

from sahara import context
import sahara.tests.unit.conductor.base as test_base
from sahara.tests.unit.conductor.manager import test_edp


def _merge_dict(original, update):
    new = copy.deepcopy(original)
    new.update(update)
    return new


SAMPLE_JOB = _merge_dict(test_edp.SAMPLE_JOB, {
    "interface": [
        {
            "name": "Reducer Count",
            "mapping_type": "configs",
            "location": "mapred.reduce.tasks",
            "value_type": "number",
            "required": True,
            "default": "1"
        },
        {
            "name": "Input Path",
            "mapping_type": "params",
            "location": "INPUT",
            "value_type": "data_source",
            "required": False,
            "default": "hdfs://path"
        },
        {
            "name": "Positional Argument 2",
            "mapping_type": "args",
            "location": "1",
            "value_type": "string",
            "required": False,
            "default": "default"
        },
        {
            "name": "Positional Argument 1",
            "mapping_type": "args",
            "location": "0",
            "value_type": "string",
            "required": False,
            "default": "arg_1"
        },

    ]
})

SAMPLE_JOB_EXECUTION = _merge_dict(test_edp.SAMPLE_JOB, {
    "interface": {
        "Reducer Count": "2",
        "Positional Argument 2": "arg_2"
    },
    "job_configs": {"args": ["arg_3"], "configs": {"mapred.map.tasks": "3"}}
})


class JobExecutionTest(test_base.ConductorManagerTestCase):
    def test_interface_flows(self):
        ctx = context.ctx()
        job = self.api.job_create(ctx, SAMPLE_JOB)
        arg_names = [arg['name'] for arg in job['interface']]
        self.assertEqual(arg_names, ["Reducer Count", "Input Path",
                                     "Positional Argument 2",
                                     "Positional Argument 1"])

        job_ex_input = copy.deepcopy(SAMPLE_JOB_EXECUTION)
        job_ex_input['job_id'] = job['id']

        self.api.job_execution_create(ctx, job_ex_input)

        lst = self.api.job_execution_get_all(ctx)
        self.assertEqual(1, len(lst))

        job_ex_result = lst[0]
        configs = {
            'configs': {'mapred.reduce.tasks': '2',
                        'mapred.map.tasks': '3'},
            'args': ['arg_1', 'arg_2', 'arg_3'],
            'params': {'INPUT': 'hdfs://path'}
        }
        self.assertEqual(configs, job_ex_result['job_configs'])
        self.api.job_execution_destroy(ctx, job_ex_result['id'])

        del job_ex_input['job_configs']
        self.api.job_execution_create(ctx, job_ex_input)

        lst = self.api.job_execution_get_all(ctx)
        self.assertEqual(1, len(lst))

        job_ex_result = lst[0]
        configs = {
            'configs': {'mapred.reduce.tasks': '2'},
            'args': ['arg_1', 'arg_2'],
            'params': {'INPUT': 'hdfs://path'}
        }
        self.assertEqual(configs, job_ex_result['job_configs'])
