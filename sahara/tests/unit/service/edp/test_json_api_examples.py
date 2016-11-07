# Copyright (c) 2014 Red Hat Inc.
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

import itertools
import os

from oslo_serialization import jsonutils as json
from oslo_utils import uuidutils
import testtools

from sahara.service.validations.edp import data_source_schema
from sahara.service.validations.edp import job_binary_schema
from sahara.service.validations.edp import job_execution_schema
from sahara.service.validations.edp import job_schema
from sahara.utils import api_validator


class TestJSONApiExamplesV11(testtools.TestCase):

    EXAMPLES_PATH = 'etc/edp-examples/json-api-examples/v1.1/%s'

    def test_data_sources(self):
        schema = data_source_schema.DATA_SOURCE_SCHEMA
        path = self.EXAMPLES_PATH % 'data-sources'
        formatter = self._formatter()
        self._test(schema, path, formatter)

    def test_job_binaries(self):
        schema = job_binary_schema.JOB_BINARY_SCHEMA
        path = self.EXAMPLES_PATH % 'job-binaries'
        formatter = self._formatter("job_binary_internal_id",
                                    "script_binary_internal_id",
                                    "text_binary_internal_id")
        self._test(schema, path, formatter)

    def test_jobs(self):
        schema = job_schema.JOB_SCHEMA
        path = self.EXAMPLES_PATH % 'jobs'
        formatter = self._formatter("job_binary_id",
                                    "udf_binary_id",
                                    "script_binary_id",
                                    "text_binary_id")
        self._test(schema, path, formatter)

    def test_job_executions(self):
        schema = job_execution_schema.JOB_EXEC_SCHEMA
        path = self.EXAMPLES_PATH % 'job-executions'
        formatter = self._formatter("cluster_id",
                                    "input_source_id",
                                    "output_source_id")
        self._test(schema, path, formatter)

    def _test(self, schema, path, formatter):
        validator = api_validator.ApiValidator(schema)
        for filename in self._files_in_path(path):
            file_path = '/'.join((path, filename))
            with open(file_path, 'r') as payload:
                payload = payload.read() % formatter
                payload = json.loads(payload)
                validator.validate(payload)

    def _files_in_path(self, path):
        all_files = (files for (path, directories, files) in os.walk(path))
        return itertools.chain(*all_files)

    def _formatter(self, *variables):
        return {variable: uuidutils.generate_uuid() for variable in variables}
