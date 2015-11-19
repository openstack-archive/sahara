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

from sahara.tests.unit import testutils as tu


def get_fake_cluster(**kwargs):
    mng = tu.make_inst_dict('id1', 'manager_inst', management_ip='1.2.3.4')
    mng_ng = tu.make_ng_dict('manager_ng', 1, ['CLOUDERA_MANAGER'], 1, [mng])

    mst = tu.make_inst_dict('id2', 'master_inst', management_ip='1.2.3.5')
    mst_ng = tu.make_ng_dict('master_ng', 1, ['HDFS_NAMENODE',
                                              'HDFS_SECONDARYNAMENODE',
                                              'YARN_RESOURCEMANAGER',
                                              'YARN_JOBHISTORY',
                                              'HIVE_SERVER2',
                                              'HIVE_METASTORE',
                                              'OOZIE_SERVER'], 1, [mst])

    wkrs = _get_workers()
    wkrs_ng = tu.make_ng_dict('worker_ng', 1, ['HDFS_DATANODE',
                                               'YARN_NODEMANAGER'],
                              len(wkrs), wkrs)
    return tu.create_cluster('test_cluster', 1, 'cdh', '5',
                             [mng_ng, mst_ng, wkrs_ng],
                             **kwargs)


def _get_workers():
    workers = []
    for i in range(3):
        w = tu.make_inst_dict('id0%d' % i, 'worker-0%d' % i,
                              management_ip='1.2.3.1%d' % i)
        workers.append(w)

    return workers
