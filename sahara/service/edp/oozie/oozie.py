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

import re

from oslo_serialization import jsonutils as json
from six.moves.urllib import parse as urlparse

import sahara.exceptions as ex


class OozieClient(object):
    def __init__(self, url, oozie_server):
        self.job_url = url + "/v2/job/%s"
        self.jobs_url = url + "/v2/jobs"
        self.oozie_server = oozie_server
        self.port = urlparse.urlparse(url).port

    def _get_http_session(self, info=None):
        return self.oozie_server.remote().get_http_client(self.port, info=info)

    def add_job(self, job_config, job_execution):
        session = self._get_http_session(job_execution.extra.get('neutron'))
        resp = session.post(self.jobs_url, data=job_config, headers={
            "Content-Type": "application/xml;charset=UTF-8"
        })
        _check_status_code(resp, 201)
        return get_json(resp)['id']

    def run_job(self, job_execution, job_id):
        session = self._get_http_session(job_execution.extra.get('neutron'))
        resp = session.put(self.job_url % job_id + "?action=start")
        _check_status_code(resp, 200)

    def kill_job(self, job_execution):
        session = self._get_http_session(job_execution.extra.get('neutron'))
        resp = session.put(self.job_url % job_execution.engine_job_id +
                           "?action=kill")
        _check_status_code(resp, 200)

    def manage_job(self, job_execution, action):
        session = self._get_http_session(job_execution.extra.get('neutron'))
        resp = session.put(self.job_url % job_execution.oozie_job_id +
                           "?action=" + action)
        _check_status_code(resp, 200)

    def get_job_info(self, job_execution, job_id=None):
        if job_id is None:
            job_id = job_execution.engine_job_id
        session = self._get_http_session(job_execution.extra.get('neutron'))
        resp = session.get(self.job_url % job_id + "?show=info")
        _check_status_code(resp, 200)
        return get_json(resp)

    def get_job_logs(self, job_execution):
        session = self._get_http_session(job_execution.extra.get('neutron'))
        resp = session.get(self.job_url % job_execution.engine_job_id +
                           "?show=log")
        _check_status_code(resp, 200)
        return resp.text

    def get_jobs(self, offset, size, **filter):
        url = self.jobs_url + "?offset=%s&len=%s" % (offset, size)
        if len(filter) > 0:
            f = ";".join([k + "=" + v for k, v in filter.items()])
            url += "&filter=" + urlparse.quote(f)

        session = self._get_http_session()
        resp = session.get(url)
        _check_status_code(resp, 200)
        return get_json(resp)


def _check_status_code(resp, expected_code):
    if resp.status_code != expected_code:
        resp_text = resp.text
        # cleaning tomcat error message
        message = resp_text.split("<HR size=\"1\" noshade=\"noshade\">")[1]
        message = message.replace("</p><p>", "\n")
        message = re.sub('<[^<]+?>', ' ', message)
        raise ex.OozieException(message)


def get_json(response):
    """Provides backward compatibility for old versions of requests library."""

    json_field_or_function = getattr(response, 'json', None)
    if callable(json_field_or_function):
        return response.json()
    else:
        return json.loads(response.content)
