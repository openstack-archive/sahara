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

import json


def url_for(headers, service_type, admin=False, endpoint_type=None):
    if not endpoint_type:
        endpoint_type = 'publicURL'
    if admin:
        endpoint_type = 'adminURL'

    catalog = headers['X-Service-Catalog']
    service = _get_service_from_catalog(catalog, service_type)

    if service:
        return service['endpoints'][0][endpoint_type]
    else:
        raise Exception('Service "%s" not found' % service_type)


def _get_service_from_catalog(catalog, service_type):
    if catalog:
        catalog = json.loads(catalog)
        for service in catalog:
            if service['type'] == service_type:
                return service

    return None
