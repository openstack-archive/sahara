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
import re
import requests
import urllib

import savanna.exceptions as ex


class OozieClient(object):
    def __init__(self, url):
        self.job_url = url + "/v1/job/%s"
        self.jobs_url = url + "/v1/jobs"

    def add_job(self, job_config):
        resp = requests.post(self.jobs_url, job_config, headers={
            "Content-Type": "application/xml;charset=UTF-8"
        })
        _check_status_code(resp, 201)
        return get_json(resp)['id']

    def run_job(self, job_id):
        resp = requests.put(self.job_url % job_id + "?action=start")
        _check_status_code(resp, 200)

    def kill_job(self, job_id):
        resp = requests.put(self.job_url % job_id + "?action=kill")
        _check_status_code(resp, 200)

    def get_job_status(self, job_id):
        resp = requests.get(self.job_url % job_id + "?show=info")
        _check_status_code(resp, 200)
        return get_json(resp)

    def get_job_logs(self, job_id):
        resp = requests.get(self.job_url % job_id + "?show=log")
        _check_status_code(resp, 200)
        return resp.text

    def get_jobs(self, offset, size, **filter):
        url = self.jobs_url + "?offset=%s&len=%s" % (offset, size)
        if len(filter) > 0:
            f = ";".join([k + "=" + v for k, v in filter.items()])
            url += "&filter=" + urllib.quote(f)

        resp = requests.get(url)
        _check_status_code(resp, 200)
        return get_json(resp)


def _check_status_code(resp, expected_code):
    if resp.status_code != expected_code:
        resp_text = resp.text
        #cleaning tomcat error message
        message = resp_text.split("<HR size=\"1\" noshade=\"noshade\">")[1]
        message = message.replace("</p><p>", "\n")
        message = re.sub('<[^<]+?>', ' ', message)
        raise OozieException(message)


def get_json(response):
    """This method provided backward compatibility with old versions
    of requests library

    """
    json_field_or_function = getattr(response, 'json', None)
    if callable(json_field_or_function):
        return response.json()
    else:
        return json.loads(response.content)


class OozieException(ex.SavannaException):
    pass
