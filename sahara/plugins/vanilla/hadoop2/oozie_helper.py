# Copyright (c) 2014 Mirantis Inc.
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
from sahara.plugins.vanilla.hadoop2 import utils as u


def get_oozie_required_xml_configs(hadoop_conf_dir):
    """Following configs differ from default configs in oozie-default.xml."""
    return {
        'oozie.service.ActionService.executor.ext.classes':
        'org.apache.oozie.action.email.EmailActionExecutor,'
        'org.apache.oozie.action.hadoop.HiveActionExecutor,'
        'org.apache.oozie.action.hadoop.ShellActionExecutor,'
        'org.apache.oozie.action.hadoop.SqoopActionExecutor,'
        'org.apache.oozie.action.hadoop.DistcpActionExecutor',

        'oozie.service.SchemaService.wf.ext.schemas':
        'shell-action-0.1.xsd,shell-action-0.2.xsd,shell-action-0.3.xsd,'
        'email-action-0.1.xsd,hive-action-0.2.xsd,hive-action-0.3.xsd,'
        'hive-action-0.4.xsd,hive-action-0.5.xsd,sqoop-action-0.2.xsd,'
        'sqoop-action-0.3.xsd,sqoop-action-0.4.xsd,ssh-action-0.1.xsd,'
        'ssh-action-0.2.xsd,distcp-action-0.1.xsd,distcp-action-0.2.xsd,'
        'oozie-sla-0.1.xsd,oozie-sla-0.2.xsd',

        'oozie.service.JPAService.create.db.schema': 'false',
        'oozie.service.HadoopAccessorService.hadoop.configurations': '*=%s' % (
            hadoop_conf_dir)
    }


def get_oozie_mysql_configs(cluster):
    return {
        'oozie.service.JPAService.jdbc.driver':
        'com.mysql.jdbc.Driver',
        'oozie.service.JPAService.jdbc.url':
        'jdbc:mysql://localhost:3306/oozie',
        'oozie.service.JPAService.jdbc.username': 'oozie',
        'oozie.service.JPAService.jdbc.password': u.get_oozie_password(
            cluster)
    }
