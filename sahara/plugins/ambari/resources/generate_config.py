#!/usr/bin/env python
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


from __future__ import print_function
import argparse
import sys

from oslo_serialization import jsonutils
import requests


def get_blueprint(ambari_address, username, password, cluster_name):
    url = "http://%s:8080/api/v1/clusters/%s?format=blueprint" % (
        ambari_address, cluster_name)
    resp = requests.get(url, auth=(username, password))
    resp.raise_for_status()
    if resp.text:
        return jsonutils.loads(resp.text)


def generate_config(blueprint):
    configs = {}
    for entity in blueprint["configurations"]:
        for cfg in entity:
            p = entity[cfg]["properties"]
            if not p:
                continue
            if "content" in p:
                del p["content"]
            for k, v in p.items():
                p[k] = " ".join(v.split())
            if p:
                configs[cfg] = p
    return configs


def write_config(cfg, version):
    with open("sahara/plugins/ambari/resources/configs-%s.json" % version,
              "w") as fp:
        jsonutils.dump(cfg, fp, indent=4, sort_keys=True,
                       separators=(",", ": "))


def main():
    parser = argparse.ArgumentParser(
        description="Ambari sample config generator")
    parser.add_argument("--address", help="Ambari address",
                        default="localhost")
    parser.add_argument("--username", help="Ambari username",
                        default="admin")
    parser.add_argument("--password", help="Ambari password",
                        default="admin")
    parser.add_argument("--cluster-name", help="Name of cluster",
                        default="cluster")
    ns = parser.parse_args(sys.argv[1:])

    bp = get_blueprint(ns.address,
                       ns.username,
                       ns.password,
                       ns.cluster_name)
    cfg = generate_config(bp)
    write_config(cfg, bp["Blueprints"]["stack_version"])


if __name__ == "__main__":
    main()
