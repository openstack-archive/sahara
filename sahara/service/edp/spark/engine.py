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

from sahara import conductor as c
from sahara import context
from sahara import exceptions as e
from sahara.i18n import _
from sahara.plugins.general import utils as plugin_utils
from sahara.plugins.spark import config_helper as c_helper
from sahara.service.edp import base_engine
from sahara.service.edp import job_utils
from sahara.service.validations.edp import job_execution as j
from sahara.utils import edp
from sahara.utils import files
from sahara.utils import general
from sahara.utils import remote

conductor = c.API


class SparkJobEngine(base_engine.JobEngine):
    def __init__(self, cluster):
        self.cluster = cluster

    def _get_pid_and_inst_id(self, job_id):
        try:
            pid, inst_id = job_id.split("@", 1)
            if pid and inst_id:
                return (pid, inst_id)
        except Exception:
            pass
        return "", ""

    def _get_instance_if_running(self, job_execution):
        pid, inst_id = self._get_pid_and_inst_id(job_execution.oozie_job_id)
        if not pid or not inst_id or (
           job_execution.info['status'] in edp.JOB_STATUSES_TERMINATED):
            return None, None
        # TODO(tmckay): well, if there is a list index out of range
        # error here it probably means that the instance is gone. If we
        # have a job execution that is not terminated, and the instance
        # is gone, we should probably change the status somehow.
        # For now, do nothing.
        try:
            instance = general.get_instances(self.cluster, [inst_id])[0]
        except Exception:
            instance = None
        return pid, instance

    def _get_result_file(self, r, job_execution):
        result = os.path.join(job_execution.extra['spark-path'], "result")
        return r.execute_command("cat %s" % result,
                                 raise_when_error=False)

    def _check_pid(self, r, pid):
        ret, stdout = r.execute_command("ps hp %s" % pid,
                                        raise_when_error=False)
        return ret

    def _get_job_status_from_remote(self, r, pid, job_execution):
        # If the pid is there, it's still running
        if self._check_pid(r, pid) == 0:
            return {"status": edp.JOB_STATUS_RUNNING}

        # The process ended. Look in the result file to get the exit status
        ret, stdout = self._get_result_file(r, job_execution)
        if ret == 0:
            exit_status = stdout.strip()
            if exit_status == "0":
                return {"status": edp.JOB_STATUS_SUCCEEDED}
            # SIGINT will yield either -2 or 130
            elif exit_status in ["-2", "130"]:
                return {"status": edp.JOB_STATUS_KILLED}

        # Well, process is done and result is missing or unexpected
        return {"status": edp.JOB_STATUS_DONEWITHERROR}

    def cancel_job(self, job_execution):
        pid, instance = self._get_instance_if_running(job_execution)
        if instance is not None:
            with remote.get_remote(instance) as r:
                ret, stdout = r.execute_command("kill -SIGINT %s" % pid,
                                                raise_when_error=False)
                if ret == 0:
                    # We had some effect, check the status
                    return self._get_job_status_from_remote(r,
                                                            pid, job_execution)

    def get_job_status(self, job_execution):
        pid, instance = self._get_instance_if_running(job_execution)
        if instance is not None:
            with remote.get_remote(instance) as r:
                return self._get_job_status_from_remote(r, pid, job_execution)

    def _job_script(self):
        path = "service/edp/resources/launch_command.py"
        return files.get_file_text(path)

    def run_job(self, job_execution):
        ctx = context.ctx()
        job = conductor.job_get(ctx, job_execution.job_id)

        proxy_configs = job_execution.job_configs.get('proxy_configs')

        # We'll always run the driver program on the master
        master = plugin_utils.get_instance(self.cluster, "master")

        # TODO(tmckay): wf_dir should probably be configurable.
        # The only requirement is that the dir is writable by the image user
        wf_dir = job_utils.create_workflow_dir(master, '/tmp/spark-edp', job,
                                               job_execution.id)
        paths = job_utils.upload_job_files(master, wf_dir, job,
                                           libs_subdir=False,
                                           proxy_configs=proxy_configs)

        # We can shorten the paths in this case since we'll run out of wf_dir
        paths = [os.path.basename(p) for p in paths]

        # TODO(tmckay): for now, paths[0] is always assumed to be the app
        # jar and we generate paths in order (mains, then libs).
        # When we have a Spark job type, we can require a "main" and set
        # the app jar explicitly to be "main"
        app_jar = paths.pop(0)

        # The rest of the paths will be passed with --jars
        additional_jars = ",".join(paths)
        if additional_jars:
            additional_jars = "--jars " + additional_jars

        # Launch the spark job using spark-submit and deploy_mode = client
        host = master.hostname()
        port = c_helper.get_config_value("Spark", "Master port", self.cluster)
        spark_submit = os.path.join(
            c_helper.get_config_value("Spark",
                                      "Spark home",
                                      self.cluster),
            "bin/spark-submit")

        job_class = job_execution.job_configs.configs["edp.java.main_class"]

        # TODO(tmckay): we need to clean up wf_dirs on long running clusters
        # TODO(tmckay): probably allow for general options to spark-submit
        args = " ".join(job_execution.job_configs.get('args', []))

        # The redirects of stdout and stderr will preserve output in the wf_dir
        cmd = "%s %s --class %s %s --master spark://%s:%s %s" % (
            spark_submit,
            app_jar,
            job_class,
            additional_jars,
            host,
            port,
            args)

        # If an exception is raised here, the job_manager will mark
        # the job failed and log the exception
        with remote.get_remote(master) as r:
            # Upload the command launch script
            launch = os.path.join(wf_dir, "launch_command")
            r.write_file_to(launch, self._job_script())
            r.execute_command("chmod +x %s" % launch)
            ret, stdout = r.execute_command(
                "cd %s; ./launch_command %s > /dev/null 2>&1 & echo $!"
                % (wf_dir, cmd))

        if ret == 0:
            # Success, we'll add the wf_dir in job_execution.extra and store
            # pid@instance_id as the job id
            # We know the job is running so return "RUNNING"
            return (stdout.strip() + "@" + master.id,
                    edp.JOB_STATUS_RUNNING,
                    {'spark-path': wf_dir})

        # Hmm, no execption but something failed.
        # Since we're using backgrounding with redirect, this is unlikely.
        raise e.EDPError(_("Spark job execution failed. Exit status = "
                           "%(status)s, stdout = %(stdout)s") %
                         {'status': ret, 'stdout': stdout})

    def validate_job_execution(self, cluster, job, data):
        j.check_main_class_present(data, job)

    @staticmethod
    def get_possible_job_config(job_type):
        return {'job_config': {'configs': [], 'args': []}}

    @staticmethod
    def get_supported_job_types():
        return [edp.JOB_TYPE_SPARK]
