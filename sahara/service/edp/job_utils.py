# Copyright (c) 2014 OpenStack Foundation
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

import os
import uuid

from oslo.config import cfg
import six

from sahara import conductor as c
from sahara import context
from sahara.plugins import base as plugin_base
from sahara.service.edp.binary_retrievers import dispatch
from sahara.service.edp import hdfs_helper as h
from sahara.utils import edp
from sahara.utils import remote


opts = [
    cfg.StrOpt('job_workflow_postfix',
               default='',
               help='Postfix for storing jobs in hdfs. Will be '
                    'added to /user/hadoop/.')
]

CONF = cfg.CONF
CONF.register_opts(opts)

conductor = c.API


def get_plugin(cluster):
    return plugin_base.PLUGINS.get_plugin(cluster.plugin_name)


def upload_job_files_to_hdfs(where, job_dir, job, hdfs_user):
    mains = job.mains or []
    libs = job.libs or []
    uploaded_paths = []

    with remote.get_remote(where) as r:
        for main in mains:
            raw_data = dispatch.get_raw_binary(main)
            h.put_file_to_hdfs(r, raw_data, main.name, job_dir, hdfs_user)
            uploaded_paths.append(job_dir + '/' + main.name)
        for lib in libs:
            raw_data = dispatch.get_raw_binary(lib)
            # HDFS 2.2.0 fails to put file if the lib dir does not exist
            h.create_dir(r, job_dir + "/lib", hdfs_user)
            h.put_file_to_hdfs(r, raw_data, lib.name, job_dir + "/lib",
                               hdfs_user)
            uploaded_paths.append(job_dir + '/lib/' + lib.name)
    return uploaded_paths


def upload_job_files(where, job_dir, job, libs_subdir=True):
    mains = job.mains or []
    libs = job.libs or []
    uploaded_paths = []

    # Include libs files in the main dir if libs_subdir is False
    if not libs_subdir:
        mains += libs

    with remote.get_remote(where) as r:
        for job_file in mains:
            dst = os.path.join(job_dir, job_file.name)
            raw_data = dispatch.get_raw_binary(job_file)
            r.write_file_to(dst, raw_data)
            uploaded_paths.append(dst)

        if libs_subdir and libs:
            libs_dir = os.path.join(job_dir, "libs")
            r.execute_command("mkdir -p %s" % libs_dir)
            for job_file in libs:
                dst = os.path.join(libs_dir, job_file.name)
                raw_data = dispatch.get_raw_binary(job_file)
                r.write_file_to(dst, raw_data)
                uploaded_paths.append(dst)
    return uploaded_paths


def create_hdfs_workflow_dir(where, job, hdfs_user):

    constructed_dir = '/user/%s/' % hdfs_user
    constructed_dir = _add_postfix(constructed_dir)
    constructed_dir += '%s/%s' % (job.name, six.text_type(uuid.uuid4()))
    with remote.get_remote(where) as r:
        h.create_dir(r, constructed_dir, hdfs_user)

    return constructed_dir


def create_workflow_dir(where, path, job, uuid=None):

    if uuid is None:
        uuid = six.text_type(uuid.uuid4())

    constructed_dir = _add_postfix(path)
    constructed_dir += '%s/%s' % (job.name, uuid)
    with remote.get_remote(where) as r:
        ret, stdout = r.execute_command("mkdir -p %s" % constructed_dir)
    return constructed_dir


def get_data_sources(job_execution, job):
    if edp.compare_job_type(job.type, edp.JOB_TYPE_JAVA):
        return None, None

    ctx = context.ctx()
    input_source = conductor.data_source_get(ctx, job_execution.input_id)
    output_source = conductor.data_source_get(ctx, job_execution.output_id)
    return input_source, output_source


def _add_postfix(constructed_dir):

    def _append_slash_if_needed(path):
        if path[-1] != '/':
            path += '/'
        return path

    constructed_dir = _append_slash_if_needed(constructed_dir)
    if CONF.job_workflow_postfix:
        constructed_dir = ''.join([str(constructed_dir),
                                   str(CONF.job_workflow_postfix)])
    return _append_slash_if_needed(constructed_dir)
