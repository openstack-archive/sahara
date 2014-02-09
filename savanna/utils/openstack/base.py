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

from oslo.config import cfg


CONF = cfg.CONF


def url_for(service_catalog, service_type, admin=False, endpoint_type=None):
    if not endpoint_type:
        endpoint_type = 'publicURL'
    if admin:
        endpoint_type = 'adminURL'

    service = _get_service_from_catalog(service_catalog, service_type)

    if service:
        endpoints = service['endpoints']
        try:
            return _get_endpoint_url(endpoints, endpoint_type)
        except Exception:
            raise RuntimeError("For service %s not found "
                               "endpoint with type %s"
                               % (service_type, endpoint_type))

    else:
        raise Exception('Service "%s" not found' % service_type)


def _get_service_from_catalog(catalog, service_type):
    if catalog:
        catalog = json.loads(catalog)
        for service in catalog:
            if service['type'] == service_type:
                return service

    return None


def _get_endpoint_url(endpoints, endpoint_type):
    if 'interface' in endpoints[0]:
        endpoint_type = endpoint_type[0:-3]
        for endpoint in endpoints:
            if endpoint['interface'] == endpoint_type:
                return endpoint['url']
    return _get_case_insensitive(endpoints[0], endpoint_type)


def _get_case_insensitive(dictionary, key):
    for k, v in dictionary.items():
        if str(k).lower() == str(key).lower():
            return v

    #this will raise an exception as usual if key was not found
    return dictionary[key]


def retrieve_auth_url():
    protocol = CONF.os_auth_protocol
    host = CONF.os_auth_host
    port = CONF.os_auth_port

    return "%s://%s:%s/%s/" % (protocol, host, port,
                               'v3' if CONF.use_identity_api_v3 else 'v2.0')
