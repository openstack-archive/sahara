# Copyright (c) 2015 Intel Corporation
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

from oslo_serialization import jsonutils as json
import six

from sahara.plugins.cdh.client import api_client

# -- cm config --

cm_address = 'localhost'
cm_port = 7180
cm_username = 'admin'
cm_password = 'admin'

hdfs_service_name = 'hdfs01'
yarn_service_name = 'yarn01'
oozie_service_name = 'oozie01'
hive_service_name = 'hive01'
hue_service_name = 'hue01'
spark_service_name = 'spark_on_yarn01'
zookeeper_service_name = 'zookeeper01'
hbase_service_name = 'hbase01'
flume_service_name = 'flume01'
sqoop_service_name = 'sqoop01'
solr_service_name = 'solr01'
ks_indexer_service_name = 'ks_indexer01'
impala_service_name = 'impala01'
sentry_service_name = 'sentry01'


def get_cm_api():
    return api_client.ApiResource(cm_address, server_port=cm_port,
                                  username=cm_username, password=cm_password)


def get_cluster(api):
    return api.get_all_clusters()[0]


def process_service(service, service_name):
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
    for name, value in six.iteritems(config):
        p = {
            'name': value.name,
            'value': value.default,
            'display_name': value.displayName,
            'desc': value.description
        }
        cfg.append(p)

    return cfg


def write_cfg(cfg, file_name):
    to_write = json.dumps(cfg, sort_keys=True, indent=4,
                          separators=(',', ': '))

    with open(file_name, 'w') as f:
        f.write(to_write)


def main():
    client = get_cm_api()
    cluster = get_cluster(client)

    hdfs = cluster.get_service(hdfs_service_name)
    process_service(hdfs, 'hdfs')

    yarn = cluster.get_service(yarn_service_name)
    process_service(yarn, 'yarn')

    oozie = cluster.get_service(oozie_service_name)
    process_service(oozie, 'oozie')

    hive = cluster.get_service(hive_service_name)
    process_service(hive, 'hive')

    hue = cluster.get_service(hue_service_name)
    process_service(hue, 'hue')

    spark = cluster.get_service(spark_service_name)
    process_service(spark, 'spark')

    zookeeper = cluster.get_service(zookeeper_service_name)
    process_service(zookeeper, 'zookeeper')

    hbase = cluster.get_service(hbase_service_name)
    process_service(hbase, 'hbase')

    flume = cluster.get_service(flume_service_name)
    process_service(flume, 'flume')

    sqoop = cluster.get_service(sqoop_service_name)
    process_service(sqoop, 'sqoop')

    solr = cluster.get_service(solr_service_name)
    process_service(solr, 'solr')

    ks_indexer = cluster.get_service(ks_indexer_service_name)
    process_service(ks_indexer, 'ks_indexer')

    impala = cluster.get_service(impala_service_name)
    process_service(impala, 'impala')

    sentry = cluster.get_service(sentry_service_name)
    process_service(sentry, 'sentry')


if __name__ == '__main__':
    main()
