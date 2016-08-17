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

import abc
import re

from oslo_serialization import jsonutils as json
from oslo_utils import uuidutils
import six
from six.moves.urllib import parse as urlparse

import sahara.exceptions as ex


@six.add_metaclass(abc.ABCMeta)
class BaseOozieClient(object):
    def __init__(self, url, oozie_server):
        self.job_url = url + "/v2/job/%s"
        self.jobs_url = url + "/v2/jobs"
        self.oozie_server = oozie_server
        self.port = urlparse.urlparse(url).port

    @abc.abstractmethod
    def add_job(self, job_config, job_execution):
        pass

    @abc.abstractmethod
    def manage_job(self, job_execution, action, job_id=None):
        pass

    @abc.abstractmethod
    def get_job_info(self, job_execution, job_id=None):
        pass

    def kill_job(self, job_execution):
        self.manage_job(job_execution, 'kill')

    def run_job(self, job_execution, job_id):
        self.manage_job(job_execution, 'start', job_id=job_id)


class OozieClient(BaseOozieClient):
    def add_job(self, job_config, job_execution):
        return self.post(
            job_execution, self.jobs_url, data=job_config, headers={
                "Content-Type": "application/xml;charset=UTF-8"})

    def manage_job(self, job_execution, action, job_id=None):
        job_id = job_id if job_id else job_execution.engine_job_id
        url = self.job_url % job_id + "?action=" + action
        self.put(job_execution, url)

    def get_job_info(self, job_execution, job_id=None):
        job_id = job_id if job_id else job_execution.engine_job_id
        url = self.job_url % job_id + "?show=info"
        return self.get(job_execution, url)

    def _get_http_session(self, info=None):
        return self.oozie_server.remote().get_http_client(self.port, info=info)

    def post(self, job_execution, url, data, headers):
        session = self._get_http_session(job_execution.extra.get('neutron'))
        resp = session.post(url, data=data, headers=headers)
        _check_status_code(resp, 201)
        return get_json(resp)['id']

    def put(self, job_execution, url):
        session = self._get_http_session(job_execution.extra.get('neutron'))
        resp = session.put(url)
        _check_status_code(resp, 200)

    def get(self, job_execution, url):
        session = self._get_http_session(job_execution.extra.get('neutron'))
        resp = session.get(url)
        _check_status_code(resp, 200)
        return get_json(resp)


class RemoteOozieClient(OozieClient):
    def __init__(self, url, oozie_server, hdfs_user):
        self.hdfs_user = hdfs_user
        self.oozie_url = url.replace(
            urlparse.urlparse(url).hostname, oozie_server.fqdn())
        super(RemoteOozieClient, self).__init__(url, oozie_server)

    def _oozie(self, cmd):
        return (
            "sudo su - -c 'oozie -Doozie.auth.token.cache=false "
            "{cmd} -oozie {oozie}' {user}".format(
                cmd=cmd, oozie=self.oozie_url, user=self.hdfs_user))

    def add_job(self, job_config, job_execution):
        with self.oozie_server.remote() as r:
            name = "/tmp/%s.xml" % uuidutils.generate_uuid()[:8]
            r.write_file_to(name, job_config)
            cmd = self._oozie("job -submit -config %s" % name)
            cmd += " | awk '{ print $2 }'"
            code, stdout = r.execute_command(cmd)
        stdout = stdout.strip()
        return stdout

    def manage_job(self, job_execution, action, job_id=None):
        job_id = job_id if job_id else job_execution.engine_job_id
        cmd = self._oozie("job -%s %s" % (action, job_id))
        with self.oozie_server.remote() as r:
            r.execute_command(cmd)

    def get_job_info(self, job_execution, job_id=None):
        job_id = job_id if job_id else job_execution.engine_job_id
        cmd = self._oozie("job -info %s" % job_id)
        cmd += " | grep Status | head -n 1 | awk '{ print $3 }'"
        with self.oozie_server.remote() as r:
            code, stdout = r.execute_command(cmd)
        return {'status': stdout.strip()}


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
