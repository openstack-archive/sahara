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


def get_hive_mysql_configs(metastore_host, passwd):
    return {
        'javax.jdo.option.ConnectionURL': 'jdbc:mysql://%s/metastore' %
        metastore_host,
        'javax.jdo.option.ConnectionDriverName': 'com.mysql.jdbc.Driver',
        'javax.jdo.option.ConnectionUserName': 'hive',
        'javax.jdo.option.ConnectionPassword': passwd,
        'datanucleus.autoCreateSchema': 'false',
        'datanucleus.fixedDatastore': 'true',
        'hive.metastore.uris': 'thrift://%s:9083' % metastore_host,
    }


def get_oozie_mysql_configs():
    return {
        'oozie.service.JPAService.jdbc.driver':
        'com.mysql.jdbc.Driver',
        'oozie.service.JPAService.jdbc.url':
        'jdbc:mysql://localhost:3306/oozie',
        'oozie.service.JPAService.jdbc.username': 'oozie',
        'oozie.service.JPAService.jdbc.password': 'oozie'
    }


def get_required_mysql_configs(hive_hostname, passwd_mysql):
    configs = get_oozie_mysql_configs()
    if hive_hostname:
        configs.update(get_hive_mysql_configs(hive_hostname, passwd_mysql))
    return configs
