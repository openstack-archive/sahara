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

import collections
import itertools
from unittest import mock


from sahara.service.validations.edp import job as j
from sahara.service.validations.edp import job_execution_schema as j_e_schema
from sahara.service.validations.edp import job_interface as j_i
from sahara.service.validations.edp import job_schema as j_schema
from sahara.tests.unit.service.validation import utils as u
from sahara.utils import edp


def _configs(**kwargs):
    arg = {
        "name": "Reducer Count",
        "mapping_type": "configs",
        "location": "mapred.reduce.tasks",
        "value_type": "number",
        "required": True,
        "default": "1"
    }
    arg.update(kwargs)
    return arg


def _params(**kwargs):
    arg = {
        "name": "Input Path",
        "mapping_type": "params",
        "location": "INPUT",
        "value_type": "data_source",
        "required": False,
        "default": "hdfs://path"
    }
    arg.update(kwargs)
    return arg


def _args(**kwargs):
    arg = {
        "name": "Positional Argument",
        "mapping_type": "args",
        "location": "0",
        "value_type": "string",
        "required": False,
        "default": "arg_value"
    }
    arg.update(kwargs)
    return arg


_mapping_types = {"configs", "args", "params"}


def _job(job_type, interface):
    return {"name": "job", "type": job_type, "interface": interface}


_job_types = [
    _job(edp.JOB_TYPE_HIVE, [_configs(), _params()]),
    _job(edp.JOB_TYPE_PIG, [_configs(), _params(), _args()]),
    _job(edp.JOB_TYPE_MAPREDUCE, [_configs()]),
    _job(edp.JOB_TYPE_MAPREDUCE_STREAMING, [_configs()]),
    _job(edp.JOB_TYPE_JAVA, [_configs(), _args()]),
    _job(edp.JOB_TYPE_SHELL, [_configs(), _params(), _args()]),
    _job(edp.JOB_TYPE_SPARK, [_configs(), _args()]),
    _job(edp.JOB_TYPE_STORM, [_args()]),
    _job(edp.JOB_TYPE_PYLEUS, [])
]


class TestJobInterfaceValidation(u.ValidationTestCase):

    def setUp(self):
        super(TestJobInterfaceValidation, self).setUp()
        self._create_object_fun = j.check_interface
        self.scheme = j_schema.JOB_SCHEMA

    def test_interface(self):
        for job in _job_types:
            self._assert_create_object_validation(data=job)

    def test_no_interface(self):
        job = _job(edp.JOB_TYPE_PIG, None)
        self._assert_create_object_validation(data=job)

    def test_overlapping_names(self):
        job = _job(edp.JOB_TYPE_PIG,
                   [_configs(), _configs(location="mapred.map.tasks")])
        self._assert_create_object_validation(
            data=job, bad_req_i=(
                1, "INVALID_DATA",
                "Name must be unique within the interface for any job."))

    def test_unacceptable_types(self):
        for job in _job_types:
            acceptable_types = [arg['mapping_type']
                                for arg in job['interface']]
            unacceptable_types = _mapping_types - set(acceptable_types)
            unacceptable_args = (globals()["_" + m_type]()
                                 for m_type in unacceptable_types)
            bad_job = job.copy()
            for arg in unacceptable_args:
                bad_job['interface'] = [arg]
                permutations = itertools.permutations(acceptable_types)
                msgs = ["Only mapping types %s are allowed for job type %s." %
                        (list(permutation), bad_job['type'])
                        for permutation in permutations]
                self._assert_create_object_validation(
                    data=bad_job, bad_req_i=(1, "INVALID_DATA", msgs))

    def test_bad_positional_arg_locations(self):
        job = _job(edp.JOB_TYPE_PIG, [_args(location="1")])
        self._assert_create_object_validation(
            data=job, bad_req_i=(
                1, "INVALID_DATA",
                "Locations of positional arguments must be an unbroken "
                "integer sequence ascending from 0."))

        job = _job(edp.JOB_TYPE_PIG, [_args(location="fish")])
        self._assert_create_object_validation(
            data=job, bad_req_i=(
                1, "INVALID_DATA",
                "Locations of positional arguments must be an unbroken "
                "integer sequence ascending from 0."))

        job = _job(edp.JOB_TYPE_PIG,
                   [_args(), _args(location="2", name="Argument 2")])
        self._assert_create_object_validation(
            data=job, bad_req_i=(
                1, "INVALID_DATA",
                "Locations of positional arguments must be an unbroken "
                "integer sequence ascending from 0."))

    def test_required_positional_arg_without_default(self):
        arg = _args(required=False)
        del arg['default']
        job = _job(edp.JOB_TYPE_PIG, [arg])
        self._assert_create_object_validation(
            data=job, bad_req_i=(
                1, "INVALID_DATA",
                "Positional arguments must be given default values if they "
                "are not required."))

    def test_overlapping_locations(self):
        job = _job(edp.JOB_TYPE_PIG,
                   [_configs(), _configs(name="Mapper Count")])
        self._assert_create_object_validation(
            data=job, bad_req_i=(
                1, "INVALID_DATA",
                "The combination of mapping type and location must be unique "
                "within the interface for any job."))

    def test_number_values(self):
        job = _job(edp.JOB_TYPE_PIG, [_configs(default="fish")])
        self._assert_create_object_validation(
            data=job, bad_req_i=(
                1, "INVALID_DATA",
                "Value 'fish' is not a valid number."))

    @mock.patch('sahara.conductor.API.data_source_get')
    def test_data_source_values(self, data_source):
        data_source.return_value = True
        job = _job(edp.JOB_TYPE_PIG,
                   [_params(default="DEADBEEF-DEAD-BEEF-DEAD-BEEFDEADBEEF")])
        self._assert_create_object_validation(data=job)

        data_source.return_value = False
        self._assert_create_object_validation(
            data=job, bad_req_i=(
                1, "INVALID_REFERENCE",
                "DataSource with id 'DEADBEEF-DEAD-BEEF-DEAD-BEEFDEADBEEF' "
                "doesn't exist"))

        job = _job(edp.JOB_TYPE_PIG, [_params(default="Filial Piety")])
        self._assert_create_object_validation(
            data=job, bad_req_i=(
                1, "INVALID_DATA",
                "Data source value 'Filial Piety' is neither a valid data "
                "source ID nor a valid URL."))

    def test_default_data_type(self):
        param = _params()
        del param['value_type']
        job = _job(edp.JOB_TYPE_PIG, [param])
        self._assert_create_object_validation(data=job)
        assert param['value_type'] == j_i.DEFAULT_DATA_TYPE


int_arg = collections.namedtuple("int_arg",
                                 ["name", "mapping_type", "location",
                                  "value_type", "required", "default"])


def j_e_i_wrapper(data):
    job = mock.Mock(
        interface=[int_arg(**_configs()),
                   int_arg(**_args()),
                   int_arg(**_params())]
    )
    j_i.check_execution_interface(data, job)


class TestJobExecutionInterfaceValidation(u.ValidationTestCase):

    def setUp(self):
        super(TestJobExecutionInterfaceValidation, self).setUp()
        self._create_object_fun = j_e_i_wrapper
        self.scheme = j_e_schema.JOB_EXEC_SCHEMA

    def test_valid_execution(self):
        data = {"cluster_id": "DEADBEEF-DEAD-BEEF-DEAD-BEEFDEADBEEF",
                "interface": {"Reducer Count": "2",
                              "Input Path": "swift://path",
                              "Positional Argument": "value"}}
        self._assert_create_object_validation(data=data)

    def test_no_execution_interface(self):
        data = {"cluster_id": "DEADBEEF-DEAD-BEEF-DEAD-BEEFDEADBEEF"}
        self._assert_create_object_validation(data=data, bad_req_i=(
            1, "INVALID_DATA",
            "An interface was specified with the template for this job. "
            "Please pass an interface map with this job (even if empty)."))

    def test_bad_argument_name(self):
        data = {"cluster_id": "DEADBEEF-DEAD-BEEF-DEAD-BEEFDEADBEEF",
                "interface": {"Fish": "Rainbow Trout",
                              "Reducer Count": "2",
                              "Input Path": "swift://path"}}
        self._assert_create_object_validation(data=data, bad_req_i=(
            1, "INVALID_DATA", "Argument names: ['Fish'] were not found in "
                               "the interface for this job."))

    def test_required_argument_missing(self):
        data = {"cluster_id": "DEADBEEF-DEAD-BEEF-DEAD-BEEFDEADBEEF",
                "interface": {"Positional Argument": "Value"}}
        self._assert_create_object_validation(data=data, bad_req_i=(
            1, "INVALID_DATA", "Argument names: ['Reducer Count'] are "
                               "required for this job."))

    @mock.patch('sahara.conductor.API.data_source_get')
    def test_bad_values(self, data_source):
        data = {"cluster_id": "DEADBEEF-DEAD-BEEF-DEAD-BEEFDEADBEEF",
                "interface": {"Reducer Count": "Two"}}
        self._assert_create_object_validation(data=data, bad_req_i=(
            1, "INVALID_DATA", "Value 'Two' is not a valid number."))

        data = {"cluster_id": "DEADBEEF-DEAD-BEEF-DEAD-BEEFDEADBEEF",
                "interface": {"Reducer Count": "2",
                              "Input Path": "not_a_url"}}
        self._assert_create_object_validation(data=data, bad_req_i=(
            1, "INVALID_DATA", "Data source value 'not_a_url' is neither a "
                               "valid data source ID nor a valid URL."))

        data = {"cluster_id": "DEADBEEF-DEAD-BEEF-DEAD-BEEFDEADBEEF",
                "interface": {"Reducer Count": "2",
                              "Positional Argument": 2}}
        self._assert_create_object_validation(data=data, bad_req_i=(
            1, "INVALID_DATA", "Value '2' is not a valid string."))

        data_source.return_value = False
        data = {"cluster_id": "DEADBEEF-DEAD-BEEF-DEAD-BEEFDEADBEEF",
                "interface":
                    {"Reducer Count": "2",
                     "Input Path": "DEADBEEF-DEAD-BEEF-DEAD-BEEFDEADBEEF"}}
        self._assert_create_object_validation(
            data=data, bad_req_i=(
                1, "INVALID_REFERENCE",
                "DataSource with id 'DEADBEEF-DEAD-BEEF-DEAD-BEEFDEADBEEF' "
                "doesn't exist"))

    def test_overlapping_data(self):
        data = {"cluster_id": "DEADBEEF-DEAD-BEEF-DEAD-BEEFDEADBEEF",
                "interface": {"Reducer Count": "2"},
                "job_configs": {"configs": {"mapred.reduce.tasks": "2"}}}
        self._assert_create_object_validation(data=data)

        data = {"cluster_id": "DEADBEEF-DEAD-BEEF-DEAD-BEEFDEADBEEF",
                "interface": {"Reducer Count": "2"},
                "job_configs": {"configs": {"mapred.reduce.tasks": "3"}}}
        self._assert_create_object_validation(data=data, bad_req_i=(
            1, "INVALID_DATA",
            "Argument 'Reducer Count' was passed both through the interface "
            "and in location 'configs'.'mapred.reduce.tasks'. Please pass "
            "this through either the interface or the configuration maps, "
            "not both."))
