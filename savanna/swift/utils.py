# Copyright (c) 2013 Red Hat, Inc.
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

from oslo.config import cfg


CONF = cfg.CONF

SWIFT_INTERNAL_PREFIX = "swift-internal://"

#TODO(tmckay): support swift-external in a future version
# SWIFT_EXTERNAL_PREFIX = "swift-external://"


def retrieve_auth_url(append_tokens=True):
    url = "{0}://{1}:{2}/v2.0/{3}".format(
        CONF.os_auth_protocol,
        CONF.os_auth_host,
        CONF.os_auth_port,
        "tokens/" if append_tokens else "")
    return url
