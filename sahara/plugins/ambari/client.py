# Copyright (c) 2015 Mirantis Inc.
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


from oslo_serialization import jsonutils
from requests import auth


class AmbariClient(object):
    def __init__(self, instance, port="8080", **kwargs):
        kwargs.setdefault("username", "admin")
        kwargs.setdefault("password", "admin")

        self._port = port
        self._base_url = "http://{host}:{port}/api/v1".format(
            host=instance.management_ip, port=port)
        self._instance = instance
        self._http_client = instance.remote().get_http_client(port)
        self._headers = {"X-Requested-By": "sahara"}
        self._auth = auth.HTTPBasicAuth(kwargs["username"], kwargs["password"])
        self._default_client_args = {"verify": False, "auth": self._auth,
                                     "headers": self._headers}

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        self._instance.remote().close_http_session(self._port)

    def get(self, *args, **kwargs):
        kwargs.update(self._default_client_args)
        return self._http_client.get(*args, **kwargs)

    def post(self, *args, **kwargs):
        kwargs.update(self._default_client_args)
        return self._http_client.post(*args, **kwargs)

    def put(self, *args, **kwargs):
        kwargs.update(self._default_client_args)
        return self._http_client.put(*args, **kwargs)

    def delete(self, *args, **kwargs):
        kwargs.update(self._default_client_args)
        return self._http_client.delete(*args, **kwargs)

    def get_alerts_data(self, cluster):
        url = self._base_url + "/clusters/%s/alerts?fields=*" % cluster.name
        resp = self.get(url)
        data = self.check_response(resp)
        return data.get('items', [])

    @staticmethod
    def check_response(resp):
        resp.raise_for_status()
        if resp.text:
            return jsonutils.loads(resp.text)

    def get_registered_hosts(self):
        url = self._base_url + "/hosts"
        resp = self.get(url)
        data = self.check_response(resp)
        return data.get("items", [])

    def get_host_info(self, host):
        url = self._base_url + "/hosts/%s" % host
        resp = self.get(url)
        data = self.check_response(resp)
        return data.get("Hosts", {})

    def update_user_password(self, user, old_password, new_password):
        url = self._base_url + "/users/%s" % user
        data = jsonutils.dumps({
            "Users": {
                "old_password": old_password,
                "password": new_password
            }
        })
        resp = self.put(url, data=data)
        self.check_response(resp)

    def create_blueprint(self, name, data):
        url = self._base_url + "/blueprints/%s" % name
        resp = self.post(url, data=jsonutils.dumps(data))
        self.check_response(resp)

    def create_cluster(self, name, data):
        url = self._base_url + "/clusters/%s" % name
        resp = self.post(url, data=jsonutils.dumps(data))
        return self.check_response(resp).get("Requests")

    def check_request_status(self, cluster_name, req_id):
        url = self._base_url + "/clusters/%s/requests/%d" % (cluster_name,
                                                             req_id)
        resp = self.get(url)
        return self.check_response(resp).get("Requests")

    def set_up_mirror(self, stack_version, os_type, repo_id, repo_url):
        url = self._base_url + (
            "/stacks/HDP/versions/%s/operating_systems/%s/repositories/%s") % (
                stack_version, os_type, repo_id)
        data = {
            "Repositories": {
                "base_url": repo_url,
                "verify_base_url": True
            }
        }
        resp = self.put(url, data=jsonutils.dumps(data))
        self.check_response(resp)
