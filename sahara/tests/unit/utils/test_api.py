# Copyright (c) 2016 Mirantis Inc.
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

import copy

import testtools

from sahara.utils import api
from sahara.utils import types
from sahara.utils import wsgi


class APIUtilsTest(testtools.TestCase):

    class FakeCluster(object):

        def to_dict(self):
            return {"id": 42, "name": "myFirstCluster"}

    page = types.Page([FakeCluster()])
    response = {"clusters":
                [
                    {
                        "id": 42,
                        "name": "myFirstCluster"
                    }
                ]
                }

    def test_render_pagination(self):
        def _assert_response_equal(response_obj, response, status, mimetype):
            self.assertEqual(response_obj.response, [response.encode()])
            self.assertEqual(response_obj.status, status)
            self.assertEqual(response_obj.mimetype, mimetype)

        from sahara.api.middleware import sahara_middleware  # noqa
        app = sahara_middleware.build_app()

        with app.test_request_context():
            _200_OK = '200 OK'
            serializer = wsgi.JSONDictSerializer()

            resp = \
                api.render(self.page, 'application/json', 200, name='clusters')
            body = serializer.serialize(self.response)
            _assert_response_equal(resp, body, _200_OK, 'application/json')

            self.page.prev, self.page.next = 35, 49
            resp = \
                api.render(self.page, 'application/json', 200, name='clusters')
            paginate_response = copy.copy(self.response)
            paginate_response["markers"] = \
                {"prev": 35, "next": 49}

            body = serializer.serialize(paginate_response)
            _assert_response_equal(resp, body, _200_OK, 'application/json')

            self.page.prev, self.page.next = 7, None
            resp = \
                api.render(self.page, 'application/json', 200, name='clusters')
            paginate_response = copy.copy(self.response)
            paginate_response["markers"] = {"prev": 7, "next": None}

            body = serializer.serialize(paginate_response)
            _assert_response_equal(resp, body, _200_OK, 'application/json')

            self.page.prev, self.page.next = None, 14
            resp = \
                api.render(self.page, 'application/json', 200, name='clusters')

            paginate_response = copy.copy(self.response)
            paginate_response["markers"] = {"prev": None, "next": 14}

            body = serializer.serialize(paginate_response)
            _assert_response_equal(resp, body, _200_OK, 'application/json')

            self.page.prev, self.page.next = None, 11
            resp = \
                api.render(self.page, 'application/json', 200, name='clusters')

            paginate_response = copy.copy(self.response)
            paginate_response["markers"] = \
                {"prev": None, "next": 11}

            body = serializer.serialize(paginate_response)
            _assert_response_equal(resp, body, _200_OK, 'application/json')
