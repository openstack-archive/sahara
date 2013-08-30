# Copyright (c) 2013 Mirantis Inc.
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

from savanna.service import api
from savanna.service.validations.edp import job_executor as j_exec
from savanna.tests.unit.service.validation import utils as u


class TestJobValidation(u.ValidationTestCase):
    def setUp(self):
        self._create_object_fun = j_exec.check_job_executor
        self.scheme = j_exec.JOB_EXEC_SCHEMA
        api.plugin_base.setup_plugins()

    def test_job_execution_validation(self):
        data = {
            "input_id": "9830d572-e242-4f2a-962f-5a850c787e09",
            "output_id": "9830d572-e242-4f2a-962f-5a850c787e09",
            "cluster_id": "9830d572-e242-4f2a-962f-5a850c787e09",

            "job_configs": {
                "a": "True",
                "b": 2,
                "c": True
            }
        }
        self._assert_types(data)
