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

import logging

from oslo.config import cfg

from savanna import context
from savanna.utils import xmlutils as x


LOG = logging.getLogger(__name__)
CONF = cfg.CONF
HADOOP_SWIFT_AUTH_URL = 'fs.swift.service.savanna.auth.url'
HADOOP_SWIFT_TENANT = 'fs.swift.service.savanna.tenant'


def _retrieve_auth_url():
    url = "{0}://{1}:{2}/v2.0/tokens/".format(
        CONF.os_auth_protocol, CONF.os_auth_host, CONF.os_auth_port)
    return url


def _retrieve_tenant():
    try:
        return context.current().headers['X-Tenant-Name']
    except RuntimeError:
        LOG.error("Cannot retrieve tenant for swift integration. "
                  "Stop cluster creation")
        #todo(slukjanov?) raise special error here
        raise RuntimeError("Cannot retrieve tenant for swift integration")


def get_swift_configs():
    configs = x.load_hadoop_xml_defaults('swift/resources/conf-template.xml')
    for conf in configs:
        if conf['name'] == HADOOP_SWIFT_AUTH_URL:
            conf['value'] = _retrieve_auth_url()
        if conf['name'] == HADOOP_SWIFT_TENANT:
            conf['value'] = _retrieve_tenant()

    result = [cfg for cfg in configs if cfg['value']]
    LOG.info("Swift would be integrated with the following "
             "params: %s", result)
    return result
