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

import copy


_COMMON_DECOMMISSION_TEMPLATE = {
    "RequestInfo": {
        "context": "",
        "command": "DECOMMISSION",
        "parameters": {
            "slave_type": "",
            "excluded_hosts": ""
        },
        "operation_level": {
            "level": "HOST_COMPONENT",
            "cluster_name": ""
        }
    },
    "Requests/resource_filters": [
        {
            "service_name": "",
            "component_name": ""
        }
    ]
}

_COMMON_RESTART_TEMPLATE = {
    "RequestInfo": {
        "context": "",
        "command": "RESTART",
        "operation_level": {
            "level": "HOST",
            "cluster_name": ""
        }
    },
    "Requests/resource_filters": [
        {
            "service_name": "",
            "component_name": "",
            "hosts": ""
        }
    ]
}

_COMMON_RESTART_SERVICE_TEMPLATE = {
    "RequestInfo": {
        "context": "",
    },
    "Body": {
        "ServiceInfo": {
            "state": ""
        }
    }
}


def build_datanode_decommission_request(cluster_name, instances):
    tmpl = copy.deepcopy(_COMMON_DECOMMISSION_TEMPLATE)

    tmpl["RequestInfo"]["context"] = "Decommission DataNodes"

    tmpl["RequestInfo"]["parameters"]["slave_type"] = "DATANODE"
    tmpl["RequestInfo"]["parameters"]["excluded_hosts"] = ",".join(
        [i.fqdn() for i in instances])

    tmpl["RequestInfo"]["operation_level"]["cluster_name"] = cluster_name

    tmpl["Requests/resource_filters"][0]["service_name"] = "HDFS"
    tmpl["Requests/resource_filters"][0]["component_name"] = "NAMENODE"

    return tmpl


def build_nodemanager_decommission_request(cluster_name, instances):
    tmpl = copy.deepcopy(_COMMON_DECOMMISSION_TEMPLATE)

    tmpl["RequestInfo"]["context"] = "Decommission NodeManagers"

    tmpl["RequestInfo"]["parameters"]["slave_type"] = "NODEMANAGER"
    tmpl["RequestInfo"]["parameters"]["excluded_hosts"] = ",".join(
        [i.fqdn() for i in instances])

    tmpl["RequestInfo"]["operation_level"]["cluster_name"] = cluster_name

    tmpl["Requests/resource_filters"][0]["service_name"] = "YARN"
    tmpl["Requests/resource_filters"][0]["component_name"] = "RESOURCEMANAGER"

    return tmpl


def build_namenode_restart_request(cluster_name, nn_instance):
    tmpl = copy.deepcopy(_COMMON_RESTART_TEMPLATE)

    tmpl["RequestInfo"]["context"] = "Restart NameNode"

    tmpl["RequestInfo"]["operation_level"]["cluster_name"] = cluster_name

    tmpl["Requests/resource_filters"][0]["service_name"] = "HDFS"
    tmpl["Requests/resource_filters"][0]["component_name"] = "NAMENODE"
    tmpl["Requests/resource_filters"][0]["hosts"] = nn_instance.fqdn()

    return tmpl


def build_resourcemanager_restart_request(cluster_name, rm_instance):
    tmpl = copy.deepcopy(_COMMON_RESTART_TEMPLATE)

    tmpl["RequestInfo"]["context"] = "Restart ResourceManager"

    tmpl["RequestInfo"]["operation_level"]["cluster_name"] = cluster_name

    tmpl["Requests/resource_filters"][0]["service_name"] = "YARN"
    tmpl["Requests/resource_filters"][0]["component_name"] = "RESOURCEMANAGER"
    tmpl["Requests/resource_filters"][0]["hosts"] = rm_instance.fqdn()

    return tmpl


def build_stop_service_request(service_name):
    tmpl = copy.deepcopy(_COMMON_RESTART_SERVICE_TEMPLATE)
    tmpl["RequestInfo"]["context"] = (
        "Restart %s service (stopping)" % service_name)
    tmpl["Body"]["ServiceInfo"]["state"] = "INSTALLED"
    return tmpl


def build_start_service_request(service_name):
    tmpl = copy.deepcopy(_COMMON_RESTART_SERVICE_TEMPLATE)
    tmpl["RequestInfo"]["context"] = (
        "Restart %s service (starting)" % service_name)
    tmpl["Body"]["ServiceInfo"]["state"] = "STARTED"
    return tmpl
