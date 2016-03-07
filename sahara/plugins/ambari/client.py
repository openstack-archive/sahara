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


from oslo_log import log as logging
from oslo_serialization import jsonutils
from requests import auth

from sahara import context
from sahara.i18n import _
from sahara.plugins.ambari import decomission_helper as d_helper
from sahara.plugins import exceptions as p_exc


LOG = logging.getLogger(__name__)


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

    @staticmethod
    def req_id(response):
        if not response.text:
            raise p_exc.HadoopProvisionError("Cannot find request id. "
                                             "No response body")
        body = jsonutils.loads(response.text)
        if "Requests" not in body or "id" not in body["Requests"]:
            raise p_exc.HadoopProvisionError("Cannot find request id. "
                                             "Unexpected response format")
        return body["Requests"]["id"]

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
        return self.check_response(resp)

    def create_cluster(self, name, data):
        url = self._base_url + "/clusters/%s" % name
        resp = self.post(url, data=jsonutils.dumps(data))
        return self.check_response(resp).get("Requests")

    def add_host_to_cluster(self, instance):
        cluster_name = instance.cluster.name
        hostname = instance.fqdn()
        url = self._base_url + "/clusters/{cluster}/hosts/{hostname}".format(
            cluster=cluster_name, hostname=hostname)
        resp = self.post(url)
        self.check_response(resp)

    def create_config_group(self, cluster, data):
        url = self._base_url + "/clusters/%s/config_groups" % cluster.name
        resp = self.post(url, data=jsonutils.dumps(data))
        return self.check_response(resp)

    def add_service_to_host(self, inst, service):
        url = "{pref}/clusters/{cluster}/hosts/{host}/host_components/{proc}"
        url = url.format(pref=self._base_url, cluster=inst.cluster.name,
                         host=inst.fqdn(), proc=service)
        self.check_response(self.post(url))

    def start_service_on_host(self, inst, service, final_state):
        url = "{pref}/clusters/{cluster}/hosts/{host}/host_components/{proc}"
        url = url.format(
            pref=self._base_url, cluster=inst.cluster.name, host=inst.fqdn(),
            proc=service)
        data = {
            'HostRoles': {
                'state': final_state
            },
            'RequestInfo': {
                'context': "Starting service {service}, moving to state "
                           "{state}".format(service=service, state=final_state)
            }
        }
        resp = self.put(url, data=jsonutils.dumps(data))
        self.check_response(resp)
        # return req_id to check health of request
        return self.req_id(resp)

    def decommission_nodemanagers(self, cluster_name, instances):
        url = self._base_url + "/clusters/%s/requests" % cluster_name
        data = d_helper.build_nodemanager_decommission_request(cluster_name,
                                                               instances)
        resp = self.post(url, data=jsonutils.dumps(data))
        self.wait_ambari_request(self.req_id(resp), cluster_name)

    def decommission_datanodes(self, cluster_name, instances):
        url = self._base_url + "/clusters/%s/requests" % cluster_name
        data = d_helper.build_datanode_decommission_request(cluster_name,
                                                            instances)
        resp = self.post(url, data=jsonutils.dumps(data))
        self.wait_ambari_request(self.req_id(resp), cluster_name)

    def remove_process_from_host(self, cluster_name, instance, process):
        url = self._base_url + "/clusters/%s/hosts/%s/host_components/%s" % (
            cluster_name, instance.fqdn(), process)
        resp = self.delete(url)

        return self.check_response(resp)

    def stop_process_on_host(self, cluster_name, instance, process):
        url = self._base_url + "/clusters/%s/hosts/%s/host_components/%s" % (
            cluster_name, instance.fqdn(), process)
        check_installed_resp = self.check_response(self.get(url))

        if check_installed_resp["HostRoles"]["state"] != "INSTALLED":
            data = {"HostRoles": {"state": "INSTALLED"},
                    "RequestInfo": {"context": "Stopping %s" % process}}
            resp = self.put(url, data=jsonutils.dumps(data))

            self.wait_ambari_request(self.req_id(resp), cluster_name)

    def delete_host(self, cluster_name, instance):
        url = self._base_url + "/clusters/%s/hosts/%s" % (cluster_name,
                                                          instance.fqdn())
        resp = self.delete(url)
        return self.check_response(resp)

    def check_request_status(self, cluster_name, req_id):
        url = self._base_url + "/clusters/%s/requests/%d" % (cluster_name,
                                                             req_id)
        resp = self.get(url)
        return self.check_response(resp).get("Requests")

    def list_host_processes(self, cluster_name, instance):
        url = self._base_url + "/clusters/%s/hosts/%s" % (
            cluster_name, instance.fqdn())
        resp = self.get(url)
        body = jsonutils.loads(resp.text)

        procs = [p["HostRoles"]["component_name"]
                 for p in body["host_components"]]
        return procs

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

    def get_request_info(self, cluster_name, request_id):
        url = self._base_url + ("/clusters/%s/requests/%s" %
                                (cluster_name, request_id))
        resp = self.check_response(self.get(url))
        return resp.get('Requests')

    def wait_ambari_requests(self, requests, cluster_name):
        requests = set(requests)
        failed = []
        while len(requests) > 0:
            completed, not_completed = set(), set()
            for req_id in requests:
                request = self.get_request_info(cluster_name, req_id)
                status = request.get("request_status")
                if status == 'COMPLETED':
                    completed.add(req_id)
                elif status in ['IN_PROGRESS', 'PENDING']:
                    not_completed.add(req_id)
                else:
                    failed.append(request)
            if failed:
                msg = _("Some Ambari request(s) "
                        "not in COMPLETED state: %(description)s.")
                descrs = []
                for req in failed:
                    descr = _(
                        "request %(id)d: %(name)s - in status %(status)s")
                    descrs.append(descr %
                                  {'id': req.get("id"),
                                   'name': req.get("request_context"),
                                   'status': req.get("request_status")})
                raise p_exc.HadoopProvisionError(msg % {'description': descrs})
            requests = not_completed
            context.sleep(5)
            LOG.debug("Waiting for %d ambari request(s) to be completed",
                      len(not_completed))
        LOG.debug("All ambari requests have been completed")

    def wait_ambari_request(self, request_id, cluster_name):
        while True:
            status = self.check_request_status(cluster_name, request_id)
            LOG.debug("Task %s in %s state. Completed %.1f%%" % (
                status["request_context"], status["request_status"],
                status["progress_percent"]))
            if status["request_status"] == "COMPLETED":
                return
            if status["request_status"] in ["IN_PROGRESS", "PENDING"]:
                context.sleep(5)
            else:
                raise p_exc.HadoopProvisionError(
                    _("Ambari request in %s state") % status["request_status"])
