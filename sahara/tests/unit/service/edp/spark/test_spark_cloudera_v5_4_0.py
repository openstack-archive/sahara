# Copyright (c) 2015 ISPRAS
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

from sahara.plugins.cdh.v5_4_0 import edp_engine
from sahara.tests.unit.service.edp.spark import base as tests


class TestClouderaPlugin(tests.TestSpark):
    def setUp(self):
        super(TestClouderaPlugin, self).setUp()
        self.master_host = "CLOUDERA_MANAGER"
        self.engine_class = edp_engine.EdpSparkEngine
        self.spark_user = "sudo -u spark "
        self.spark_submit = "spark-submit"
        self.master = "yarn-cluster"
        self.deploy_mode = "cluster"
