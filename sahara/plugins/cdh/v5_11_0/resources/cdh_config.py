# Copyright (c) 2017 Massachusetts Open Cloud
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

from cm_api.api_client import ApiResource

cm_host = "localhost"
api = ApiResource(cm_host, username="admin", password="admin")  # nosec

c = api.get_all_clusters()[0]
services = c.get_all_services()


def process_service(service):
    service_name = service.name
    if service_name == "spark_on_yarn":
        service_name = "spark"
    for role_cfgs in service.get_all_role_config_groups():
        role_cm_cfg = role_cfgs.get_config(view='full')
        role_cfg = parse_config(role_cm_cfg)
        role_name = role_cfgs.roleType.lower()
        write_cfg(role_cfg, '%s-%s.json' % (service_name, role_name))

    service_cm_cfg = service.get_config(view='full')[0]
    service_cfg = parse_config(service_cm_cfg)
    write_cfg(service_cfg, '%s-service.json' % service_name)


def parse_config(config):
    cfg = []
    for name, value in config.items():
        p = {
            'name': value.name,
            'value': value.default,
            'display_name': value.displayName,
            'desc': value.description
        }
        cfg.append(p)

    return cfg


def write_cfg(cfg, file_name):
    to_write = __import__('json').dumps(cfg, sort_keys=True, indent=4,
                                        separators=(',', ': '))

    with open(file_name, 'w') as f:
        f.write(to_write)

if __name__ == '__main__':
    for service in services:
        process_service(service)
