# Copyright (c) 2015, MapR Technologies
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import os
import uuid

from oslo_utils import uuidutils
import six

import sahara.plugins.mapr.util.general as g

MV_TO_MAPRFS_CMD = ('sudo -u %(user)s'
                    ' hadoop fs -copyFromLocal %(source)s %(target)s'
                    ' && sudo rm -f %(source)s')
CP_TO_MAPRFS_CMD = ('sudo -u %(user)s'
                    ' hadoop fs -copyFromLocal %(source)s %(target)s')

CP_FROM_MAPRFS_CMD = ('sudo hadoop fs -copyToLocal %(source)s %(target)s')

RM_CMD = ('sudo -u %(user)s hadoop fs -rm %(path)s')
MKDIR_CMD_MAPR4 = 'sudo -u %(user)s hadoop fs -mkdir -p %(path)s'
MKDIR_CMD_MAPR3 = 'sudo -u %(user)s hadoop fs -mkdir %(path)s'


def put_file_to_maprfs(r, content, file_name, path, hdfs_user):
    tmp_file_name = '/tmp/%s.%s' % (file_name, six.text_type(uuid.uuid4()))
    r.write_file_to(tmp_file_name, content)
    target = os.path.join(path, file_name)
    move_from_local(r, tmp_file_name, target, hdfs_user)


def move_from_local(r, source, target, hdfs_user):
    args = {'user': hdfs_user, 'source': source, 'target': target}
    r.execute_command(MV_TO_MAPRFS_CMD % args)


def copy_from_local(r, source, target, hdfs_user):
    args = {'user': hdfs_user, 'source': source, 'target': target}
    r.execute_command(CP_TO_MAPRFS_CMD % args)


def copy_to_local(r, hdfs_source, target, hdfs_user, overwrite=True):
    args = {'source': hdfs_source, 'target': target}
    if overwrite:
        _rm_from_local(r, target)
    r.execute_command(CP_FROM_MAPRFS_CMD % args)


def exchange(source, target, src_path, trg_path, hdfs_user, alias_dir="/"):
    # check if target path contains file name, if not set file same as source
    if trg_path[-1] == '/':
        trg_path = trg_path + src_path.rsplit('/', 1)[1]
    alias = alias_dir + _generate_file_name()
    copy_from_local(source, src_path, alias, hdfs_user)
    copy_to_local(target, alias, trg_path, hdfs_user)
    remove(source, alias, hdfs_user)


def remove(r, path, hdfs_user):
    args = {'user': hdfs_user, 'path': path}
    r.execute_command(RM_CMD % args)


def create_maprfs4_dir(remote, dir_name, hdfs_user):
    remote.execute_command(MKDIR_CMD_MAPR4 % {'user': hdfs_user,
                                              'path': dir_name})


def create_maprfs3_dir(remote, dir_name, hdfs_user):
    remote.execute_command(MKDIR_CMD_MAPR3 % {'user': hdfs_user,
                                              'path': dir_name})


def mkdir(remote, path, recursive=True, run_as=None):
    command = 'hadoop fs -mkdir %(recursive)s %(path)s'
    args = {'recursive': '-p' if recursive else '', 'path': path}
    remote.execute_command(g._run_as(run_as, command % args))


def chmod(remote, path, mode, recursive=True, run_as=None):
    command = 'hadoop fs -chmod %(recursive)s %(mode)s %(path)s'
    args = {'recursive': '-R' if recursive else '', 'path': path, 'mode': mode}
    remote.execute_command(g._run_as(run_as, command % args))


def _generate_file_name(length=10):
    return uuidutils.generate_uuid()[:length]


def _rm_from_local(remote, file_name, exist=False):
    if exist:
        remote.execute_command("rm %s" % file_name, run_as_root=True)
    else:
        out, result = remote.execute_command("ls %s" % file_name,
                                             run_as_root=True,
                                             raise_when_error=False)
        if out == 0:
            remote.execute_command("rm %s" % file_name, run_as_root=True)
