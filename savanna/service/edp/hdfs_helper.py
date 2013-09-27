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


def put_file_to_hdfs(r, file, file_name, path, hdfs_user):
    r.write_file_to('/tmp/%s' % file_name, file)
    move_from_local(r, '/tmp/%s' % file_name, path + '/' + file_name,
                    hdfs_user)


def copy_from_local(r, source, target, hdfs_user):
    r.execute_command('sudo su - -c "hadoop dfs -copyFromLocal '
                      '%s %s" %s' % (source, target, hdfs_user))


def move_from_local(r, source, target, hdfs_user):
    r.execute_command('sudo su - -c "hadoop dfs -moveFromLocal '
                      '%s %s" %s' % (source, target, hdfs_user))


def create_dir(r, dir_name, hdfs_user):
    r.execute_command(
        'sudo su - -c "hadoop dfs -mkdir %s" %s' % (dir_name, hdfs_user))
