# Copyright (c) 2014, MapR Technologies
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import sahara.plugins.mapr.util.maprfs_helper as mfs
import sahara.plugins.mapr.versions.version_handler_factory as vhf
import sahara.service.edp.binary_retrievers.dispatch as d
import sahara.service.edp.oozie.engine as e


class MapROozieJobEngine(e.OozieJobEngine):

    def get_hdfs_user(self):
        return 'mapr'

    def create_hdfs_dir(self, remote, dir_name):
        mfs.create_maprfs_dir(remote, dir_name, self.get_hdfs_user())

    def _upload_workflow_file(self, where, job_dir, wf_xml, hdfs_user):
        f_name = 'workflow.xml'
        with where.remote() as r:
            mfs.put_file_to_maprfs(r, wf_xml, f_name, job_dir, hdfs_user)
        return job_dir + '/' + f_name

    def _upload_job_files_to_hdfs(self, where, job_dir, job):
        mains = job.mains or []
        libs = job.libs or []
        uploaded_paths = []
        hdfs_user = self.get_hdfs_user()
        with where.remote() as r:
            for m in mains:
                raw_data = d.get_raw_binary(m)
                mfs.put_file_to_maprfs(r, raw_data, m.name, job_dir, hdfs_user)
                uploaded_paths.append(job_dir + '/' + m.name)
            for l in libs:
                raw_data = d.get_raw_binary(l)
                lib_dir = job_dir + '/lib/'
                self.create_hdfs_dir(r, lib_dir)
                mfs.put_file_to_maprfs(r, raw_data, l.name, lib_dir,
                                       hdfs_user)
                uploaded_paths.append(lib_dir + l.name)
        return uploaded_paths

    def get_name_node_uri(self, cluster):
        h_version = cluster.hadoop_version
        v_handler = vhf.VersionHandlerFactory.get().get_handler(h_version)
        uri = v_handler.get_name_node_uri(cluster)
        return uri

    def get_oozie_server_uri(self, cluster):
        h_version = cluster.hadoop_version
        v_handler = vhf.VersionHandlerFactory.get().get_handler(h_version)
        uri = v_handler.get_oozie_server_uri(cluster)
        return uri

    def get_oozie_server(self, cluster):
        h_version = cluster.hadoop_version
        v_handler = vhf.VersionHandlerFactory.get().get_handler(h_version)
        server = v_handler.get_oozie_server(cluster)
        return server

    def get_resource_manager_uri(self, cluster):
        h_version = cluster.hadoop_version
        v_handler = vhf.VersionHandlerFactory.get().get_handler(h_version)
        uri = v_handler.get_resource_manager_uri(cluster)
        return uri
