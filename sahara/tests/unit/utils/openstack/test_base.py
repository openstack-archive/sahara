# Copyright (c) 2014 Mirantis Inc.
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

from sahara.tests.unit import base as ub
from sahara.utils.openstack import base as b


class TestBase(ub.SaharaTestCase):

    def test_url_for_regions(self):
        service_catalog = (
            '[{"endpoints": '
            '  [{"adminURL": "http://192.168.0.5:8774/v2", '
            '    "region": "RegionOne", '
            '    "id": "83d12c9ad2d647ecab7cbe91adb8666b", '
            '    "internalURL": "http://192.168.0.5:8774/v2", '
            '    "publicURL": "http://172.18.184.5:8774/v2"}, '
            '   {"adminURL": "http://192.168.0.6:8774/v2", '
            '    "region": "RegionTwo", '
            '    "id": "07c5a555176246c783d8f0497c98537b", '
            '    "internalURL": "http://192.168.0.6:8774/v2", '
            '    "publicURL": "http://172.18.184.6:8774/v2"}], '
            '  "endpoints_links": [], '
            '  "type": "compute", '
            '  "name": "nova"}]')

        self.override_config("os_region_name", "RegionOne")
        self.assertEqual("http://172.18.184.5:8774/v2",
                         b.url_for(service_catalog, "compute"))

        self.override_config("os_region_name", "RegionTwo")
        self.assertEqual("http://172.18.184.6:8774/v2",
                         b.url_for(service_catalog, "compute"))
