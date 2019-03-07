# Copyright (c) 2018 Massachusetts Open Cloud
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

import re

from oslo_middleware import base
from oslo_serialization import jsonutils
import webob
import webob.dec

from sahara.api import microversion as mv


class VersionResponseMiddlewareV1(base.Middleware):

    @webob.dec.wsgify
    def __call__(self, req):
        """Respond to a request for all Sahara API versions."""
        path = req.environ['PATH_INFO']
        if re.match(r"^/*$", path):
            response = webob.Response(request=req, status=300,
                                      content_type="application/json")
            response.body = jsonutils.dump_as_bytes(self._get_versions(req))
            return response
        else:
            return self.application

    def _get_versions(self, req):
        """Populate the version response with APIv1 stuff."""
        version_response = {
            "versions": [
                {"id": "v1.0",
                 "status": "SUPPORTED",
                 "links": self._get_links("1.0", req)
                 },
                {"id": "v1.1",
                 "status": "CURRENT",
                 "links": self._get_links("1.1", req)
                 }
            ]
        }
        return version_response

    @staticmethod
    def _get_links(version, req):
        href = "%s/v%s/" % (req.host_url, version)
        return [{"rel": "self", "href": href}]


class VersionResponseMiddlewareV2(VersionResponseMiddlewareV1):

    def _get_versions(self, req):
        """Populate the version response with APIv1 and APIv2 stuff."""
        version_response = (
            super(VersionResponseMiddlewareV2, self)._get_versions(req)
        )
        version_response["versions"][1]["status"] = "SUPPORTED"  # v1.1
        version_response["versions"].append(
            {"id": "v2",
             "status": "CURRENT",
             "links": self._get_links("2", req),
             "min_version": mv.MIN_API_VERSION,
             "max_version": mv.MAX_API_VERSION
             }
        )
        return version_response
