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

from oslo_config import cfg
from oslo_utils import uuidutils

from sahara import conductor as c
from sahara import context
from sahara import exceptions as e
from sahara.i18n import _
from sahara.plugins import utils as plugin_utils
from sahara.service.edp import base_engine
from sahara.service.edp.job_binaries import manager as jb_manager
from sahara.service.edp import job_utils
from sahara.service.validations.edp import job_execution as j
from sahara.utils import cluster as cluster_utils
from sahara.utils import edp
from sahara.utils import files
from sahara.utils import remote

conductor = c.API
CONF = cfg.CONF


class StormJobEngine(base_engine.JobEngine):
    def __init__(self, cluster):
        self.cluster = cluster

    def _get_topology_and_inst_id(self, job_id):
        try:
            topology_name, inst_id = job_id.split("@", 1)
            if topology_name and inst_id:
                return (topology_name, inst_id)
        except Exception:
            pass
        return "", ""

    def _get_instance_if_running(self, job_execution):
        topology_name, inst_id = self._get_topology_and_inst_id(
            job_execution.engine_job_id)
        if not topology_name or not inst_id or (
           job_execution.info['status'] in edp.JOB_STATUSES_TERMINATED):
            return None, None
        # TODO(tmckay): well, if there is a list index out of range
        # error here it probably means that the instance is gone. If we
        # have a job execution that is not terminated, and the instance
        # is gone, we should probably change the status somehow.
        # For now, do nothing.
        try:
            instance = cluster_utils.get_instances(self.cluster, [inst_id])[0]
        except Exception:
            instance = None
        return topology_name, instance

    def _get_topology_name(self, job_execution):
        topology_name, inst_id = self._get_topology_and_inst_id(
            job_execution.engine_job_id)

        return topology_name

    def _set_topology_name(self, job_execution, name):
        return self._generate_topology_name(name)

    def _generate_topology_name(self, name):
        return name + "_" + uuidutils.generate_uuid()

    def _get_job_status_from_remote(self, job_execution, retries=3):

        topology_name, inst_id = self._get_instance_if_running(
            job_execution)
        if topology_name is None or inst_id is None:
            return edp.JOB_STATUSES_TERMINATED

        topology_name = self._get_topology_name(job_execution)
        master = plugin_utils.get_instance(self.cluster, "nimbus")

        cmd = (
            "%(storm)s -c nimbus.host=%(host)s "
            "list | grep %(topology_name)s | awk '{print $2}'") % (
            {
                "storm": "/usr/local/storm/bin/storm",
                "host": master.hostname(),
                "topology_name": topology_name
            })
        for i in range(retries):
            with remote.get_remote(master) as r:
                ret, stdout = r.execute_command("%s " % (cmd))
            # If the status is ACTIVE is there, it's still running
            if stdout.strip() == "ACTIVE":
                return {"status": edp.JOB_STATUS_RUNNING}
            else:
                if i == retries - 1:
                    return {"status": edp.JOB_STATUS_KILLED}
                context.sleep(10)

    def _job_script(self, python_version):
        path = "service/edp/resources/launch_command.py"
        return files.get_file_text(path).replace(
            '{{PYTHON_VERSION}}', python_version)

    def _prepare_job_binaries(self, job_binaries, r):
        for jb in job_binaries:
            jb_manager.JOB_BINARIES.get_job_binary_by_url(jb.url). \
                prepare_cluster(jb, remote=r)

    def _upload_job_files(self, where, job_dir, job, job_configs):

        def upload(r, dir, job_file, proxy_configs):
            path = jb_manager.JOB_BINARIES. \
                get_job_binary_by_url(job_file.url). \
                copy_binary_to_cluster(job_file,
                                       proxy_configs=proxy_configs,
                                       remote=r, context=context.ctx())
            return path
        uploaded_paths = []
        with remote.get_remote(where) as r:
            mains = list(job.mains) if job.mains else []
            libs = list(job.libs) if job.libs else []

            job_binaries = mains + libs
            self._prepare_job_binaries(job_binaries, r)

            for job_file in job_binaries:
                uploaded_paths.append(
                    upload(r, job_dir, job_file,
                           job_configs.get('proxy_configs')))

            return uploaded_paths

    def _exec_cmd_on_remote_instance(self, master, cmd):
        if master is not None:
            with remote.get_remote(master) as r:
                ret, stdout = r.execute_command("%s > /dev/null 2>&1 & echo $!"
                                                % cmd)

                return ret, stdout

    def cancel_job(self, job_execution):
        topology_name, instance = self._get_instance_if_running(job_execution)
        if topology_name is None or instance is None:
            return None

        topology_name = self._get_topology_name(job_execution)
        master = plugin_utils.get_instance(self.cluster, "nimbus")

        cmd = (
            '%(storm_kill)s -c nimbus.host=%(host)s %(topology_name)s') % (
            {
                "storm_kill": "/usr/local/storm/bin/storm kill",
                "host": master.hostname(),
                "topology_name": topology_name
            })

        ret, stdout = self._exec_cmd_on_remote_instance(instance, cmd)

        if ret == 0:
            # We had some effect, check the status
            return self._get_job_status_from_remote(job_execution)

    def get_job_status(self, job_execution):
        topology_name, instance = self._get_instance_if_running(job_execution)
        if instance is not None:
            return self._get_job_status_from_remote(job_execution, retries=3)

    def _execute_remote_job(self, master, wf_dir, cmd):
        # If an exception is raised here, the job_manager will mark
        # the job failed and log the exception
        # The redirects of stdout and stderr will preserve output in the wf_dir
        with remote.get_remote(master) as r:
            # Upload the command launch script
            launch = os.path.join(wf_dir, "launch_command")
            python_version = r.get_python_version()
            r.write_file_to(launch, self._job_script(python_version))
            r.execute_command("chmod +x %s" % launch)
            ret, stdout = r.execute_command(
                "cd %s; ./launch_command %s > /dev/null 2>&1 & echo $!"
                % (wf_dir, cmd))

        return ret, stdout

    def _build_command(self, paths, updated_job_configs, host, topology_name):

        app_jar = paths.pop(0)
        job_class = updated_job_configs["configs"]["edp.java.main_class"]

        args = updated_job_configs.get('args', [])
        args = " ".join([arg for arg in args])

        if args:
            args = " " + args

        cmd = (
            '%(storm_jar)s -c nimbus.host=%(host)s %(job_jar)s '
            '%(main_class)s %(topology_name)s%(args)s' % (
                {
                    "storm_jar": "/usr/local/storm/bin/storm jar",
                    "main_class": job_class,
                    "job_jar": app_jar,
                    "host": host,
                    "topology_name": topology_name,
                    "args": args
                }))

        return cmd

    def run_job(self, job_execution):
        ctx = context.ctx()
        job = conductor.job_get(ctx, job_execution.job_id)

        # This will be a dictionary of tuples, (native_url, runtime_url)
        # keyed by data_source id
        data_source_urls = {}

        additional_sources, updated_job_configs = (
            job_utils.resolve_data_source_references(job_execution.job_configs,
                                                     job_execution.id,
                                                     data_source_urls,
                                                     self.cluster)
        )

        job_execution = conductor.job_execution_update(
            ctx, job_execution,
            {"data_source_urls": job_utils.to_url_dict(data_source_urls)})

        # Now that we've recorded the native urls, we can switch to the
        # runtime urls
        data_source_urls = job_utils.to_url_dict(data_source_urls,
                                                 runtime=True)

        job_utils.prepare_cluster_for_ds(additional_sources,
                                         self.cluster, updated_job_configs,
                                         data_source_urls)

        # We'll always run the driver program on the master
        master = plugin_utils.get_instance(self.cluster, "nimbus")

        # TODO(tmckay): wf_dir should probably be configurable.
        # The only requirement is that the dir is writable by the image user
        wf_dir = job_utils.create_workflow_dir(master, '/tmp/storm-edp', job,
                                               job_execution.id, "700")

        paths = self._upload_job_files(master, wf_dir, job,
                                       updated_job_configs)

        topology_name = self._set_topology_name(job_execution, job.name)

        # Launch the storm job using storm jar
        host = master.hostname()
        cmd = self._build_command(paths, updated_job_configs, host,
                                  topology_name)

        job_execution = conductor.job_execution_get(ctx, job_execution.id)
        if job_execution.info['status'] == edp.JOB_STATUS_TOBEKILLED:
            return (None, edp.JOB_STATUS_KILLED, None)

        ret, stdout = self._execute_remote_job(master, wf_dir, cmd)
        if ret == 0:
            # Success, we'll add the wf_dir in job_execution.extra and store
            # topology_name@instance_id as the job id
            # We know the job is running so return "RUNNING"
            return (topology_name + "@" + master.id,
                    edp.JOB_STATUS_RUNNING,
                    {'storm-path': wf_dir})

        # Hmm, no execption but something failed.
        # Since we're using backgrounding with redirect, this is unlikely.
        raise e.EDPError(_("Storm job execution failed. Exit status = "
                           "%(status)s, stdout = %(stdout)s") %
                         {'status': ret, 'stdout': stdout})

    def run_scheduled_job(self, job_execution):
        raise e.NotImplementedException(_("Currently Storm engine does not"
                                          " support scheduled EDP jobs"))

    def validate_job_execution(self, cluster, job, data):
        j.check_main_class_present(data, job)

    @staticmethod
    def get_possible_job_config(job_type):
        return {'job_config': {'configs': [], 'args': []}}

    @staticmethod
    def get_supported_job_types():
        return [edp.JOB_TYPE_STORM]


class StormPyleusJobEngine(StormJobEngine):
    def _build_command(self, paths, updated_job_configs, host, topology_name):

        jar_file = paths.pop(0)
        cmd = ("{pyleus} -n {nimbus_host} {jar_file}").format(
            pyleus='pyleus submit', nimbus_host=host, jar_file=jar_file)

        return cmd

    def validate_job_execution(self, cluster, job, data):
        j.check_topology_name_present(data, job)

    def _set_topology_name(self, job_execution, name):
        topology_name = job_execution["configs"]["topology_name"]
        return topology_name

    def _execute_remote_job(self, master, wf_dir, cmd):
        with remote.get_remote(master) as r:
            ret, stdout = r.execute_command(
                "cd %s; %s > /dev/null 2>&1 & echo $!"
                % (wf_dir, cmd))

        return ret, stdout

    @staticmethod
    def get_possible_job_config(job_type):
        return {'job_config': {'configs': [], 'args': []}}

    @staticmethod
    def get_supported_job_types():
        return [edp.JOB_TYPE_PYLEUS]
