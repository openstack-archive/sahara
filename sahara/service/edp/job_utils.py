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
from sahara.utils import edp
from sahara.utils import remote


opts = [
    cfg.StrOpt('job_workflow_postfix',
               default='',
               help="Postfix for storing jobs in hdfs. Will be "
                    "added to '/user/<hdfs user>/' path.")
]

CONF = cfg.CONF
CONF.register_opts(opts)

conductor = c.API


def get_plugin(cluster):
    return plugin_base.PLUGINS.get_plugin(cluster.plugin_name)


def upload_job_files(where, job_dir, job, libs_subdir=True,
                     proxy_configs=None):
    mains = job.mains or []
    libs = job.libs or []
    uploaded_paths = []

    def upload(r, dir, job_file):
        dst = os.path.join(dir, job_file.name)
        raw_data = dispatch.get_raw_binary(job_file, proxy_configs)
        r.write_file_to(dst, raw_data)
        uploaded_paths.append(dst)

    with remote.get_remote(where) as r:
        libs_dir = job_dir
        if libs_subdir and libs:
            libs_dir = os.path.join(libs_dir, "libs")
            r.execute_command("mkdir -p %s" % libs_dir)
        for job_file in mains:
            upload(r, job_dir, job_file)
        for job_file in libs:
            upload(r, libs_dir, job_file)
    return uploaded_paths


def create_workflow_dir(where, path, job, use_uuid=None):

    if use_uuid is None:
        use_uuid = six.text_type(uuid.uuid4())

    constructed_dir = _append_slash_if_needed(path)
    constructed_dir += '%s/%s' % (job.name, use_uuid)
    with remote.get_remote(where) as r:
        ret, stdout = r.execute_command("mkdir -p %s" % constructed_dir)
    return constructed_dir


def get_data_sources(job_execution, job):
    if edp.compare_job_type(job.type, edp.JOB_TYPE_JAVA, edp.JOB_TYPE_SPARK):
        return None, None

    ctx = context.ctx()
    input_source = conductor.data_source_get(ctx, job_execution.input_id)
    output_source = conductor.data_source_get(ctx, job_execution.output_id)
    return input_source, output_source


def _append_slash_if_needed(path):
    if path[-1] != '/':
        path += '/'
    return path
