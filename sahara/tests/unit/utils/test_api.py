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

import mock
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

    @mock.patch('flask.request')
    @mock.patch('flask.Response')
    def test_render_pagination(self, flask, request):
        serializer = wsgi.JSONDictSerializer()
        request.status_code = 200

        api.render(self.page, 'application/json', 200, name='clusters')
        body = serializer.serialize(self.response)
        flask.assert_called_with(
            response=body, status=200, mimetype='application/json')

        self.page.prev, self.page.next = 35, 49
        api.render(self.page, 'application/json', 200, name='clusters')
        paginate_response = copy.copy(self.response)
        paginate_response["markers"] = \
            {"prev": 35, "next": 49}

        body = serializer.serialize(paginate_response)
        flask.assert_called_with(
            response=body, status=200, mimetype='application/json')

        self.page.prev, self.page.next = 7, None
        api.render(self.page, 'application/json', 200, name='clusters')
        paginate_response = copy.copy(self.response)
        paginate_response["markers"] = {"prev": 7, "next": None}

        body = serializer.serialize(paginate_response)
        flask.assert_called_with(
            response=body, status=200, mimetype='application/json')

        self.page.prev, self.page.next = None, 14
        api.render(self.page, 'application/json', 200, name='clusters')

        paginate_response = copy.copy(self.response)
        paginate_response["markers"] = {"prev": None, "next": 14}

        body = serializer.serialize(paginate_response)
        flask.assert_called_with(
            response=body, status=200, mimetype='application/json')

        self.page.prev, self.page.next = None, 11
        api.render(self.page, 'application/json', 200, name='clusters')

        paginate_response = copy.copy(self.response)
        paginate_response["markers"] = \
            {"prev": None, "next": 11}

        body = serializer.serialize(paginate_response)
        flask.assert_called_with(
            response=body, status=200, mimetype='application/json')

        self.page.prev, self.page.next = None, 11
        api.render(self.page, 'application/json', 200, name='clusters')
