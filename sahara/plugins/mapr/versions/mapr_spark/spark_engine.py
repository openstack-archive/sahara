# Copyright (c) 2015, MapR Technologies
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import os

from sahara import conductor as c
from sahara import context
from sahara import exceptions as e
from sahara.i18n import _
import sahara.plugins.mapr.services.spark.spark as spark
import sahara.plugins.mapr.util.general as g
import sahara.plugins.mapr.versions.version_handler_factory as vhf
import sahara.plugins.utils as plugin_utils
from sahara.service.edp import job_utils
from sahara.service.edp.spark import engine as base_engine
from sahara.swift import utils as su
from sahara.utils import edp

conductor = c.API


class MapRSparkEngine(base_engine.SparkJobEngine):
    def run_job(self, job_execution):
        ctx = context.ctx()
        job = conductor.job_get(ctx, job_execution.job_id)

        additional_sources, updated_job_configs = (
            job_utils.resolve_data_source_references(job_execution.job_configs)
        )

        # We'll always run the driver program on the master
        master = plugin_utils.get_instance(
            self.cluster, spark.SPARK_MASTER.ui_name)

        # TODO(tmckay): wf_dir should probably be configurable.
        # The only requirement is that the dir is writable by the image user
        wf_dir = job_utils.create_workflow_dir(
            master, '/tmp/spark-edp', job, job_execution.id, "700")
        paths, builtin_paths = self._upload_job_files(
            master, wf_dir, job, updated_job_configs)

        # We can shorten the paths in this case since we'll run out of wf_dir
        paths = [os.path.basename(p) for p in paths]
        builtin_paths = [os.path.basename(p) for p in builtin_paths]

        # TODO(tmckay): for now, paths[0] is always assumed to be the app
        # jar and we generate paths in order (mains, then libs).
        # When we have a Spark job type, we can require a "main" and set
        # the app jar explicitly to be "main"
        app_jar = paths.pop(0)
        job_class = updated_job_configs["configs"]["edp.java.main_class"]

        # If we uploaded builtins then we are using a wrapper jar. It will
        # be the first one on the builtin list and the original app_jar needs
        # to be added to the  'additional' jars
        if builtin_paths:
            wrapper_jar = builtin_paths.pop(0)
            wrapper_class = 'org.openstack.sahara.edp.SparkWrapper'
            wrapper_xml = self._upload_wrapper_xml(
                master, wf_dir, updated_job_configs)
            wrapper_args = "%s %s" % (wrapper_xml, job_class)
            additional_jars = ",".join([app_jar] + paths + builtin_paths)
        else:
            wrapper_jar = wrapper_class = wrapper_args = ""
            additional_jars = ",".join(paths)

        # All additional jars are passed with the --jars option
        if additional_jars:
            additional_jars = " --jars " + additional_jars

        # Launch the spark job using spark-submit and deploy_mode = client
        cluster_context = self._get_cluster_context(self.cluster)
        spark_home_dir = spark.Spark().home_dir(cluster_context)

        # TODO(tmckay): we need to clean up wf_dirs on long running clusters
        # TODO(tmckay): probably allow for general options to spark-submit
        args = updated_job_configs.get('args', [])
        args = " ".join([su.inject_swift_url_suffix(arg) for arg in args])

        submit_args = {
            "spark_submit": "%s/bin/spark-submit" % spark_home_dir,
            "addnl_jars": additional_jars,
            "master_url": spark.SPARK_MASTER.submit_url(cluster_context),
            "args": args
        }
        if wrapper_jar and wrapper_class:
            # Substrings which may be empty have spaces
            # embedded if they are non-empty
            submit_args.update({
                "driver_cp": self.get_driver_classpath(),
                "wrapper_class": wrapper_class,
                "wrapper_jar": wrapper_jar,
                "wrapper_args": wrapper_args,
            })
            submit_cmd = ('%(spark_submit)s%(driver_cp)s'
                          ' --class %(wrapper_class)s%(addnl_jars)s'
                          ' --master %(master_url)s'
                          ' %(wrapper_jar)s %(wrapper_args)s %(args)s')
        else:
            submit_args.update({
                "job_class": job_class,
                "app_jar": app_jar,
            })
            submit_cmd = ('%(spark_submit)s --class %(job_class)s'
                          '%(addnl_jars)s --master %(master_url)s'
                          ' %(app_jar)s %(args)s')
        submit_cmd = g._run_as('mapr', submit_cmd % submit_args)

        job_execution = conductor.job_execution_get(ctx, job_execution.id)
        if job_execution.info['status'] == edp.JOB_STATUS_TOBEKILLED:
            return (None, edp.JOB_STATUS_KILLED, None)

        # If an exception is raised here, the job_manager will mark
        # the job failed and log the exception
        # The redirects of stdout and stderr will preserve output in the wf_dir
        with master.remote() as r:
            # Upload the command launch script
            launch = os.path.join(wf_dir, "launch_command")
            r.write_file_to(launch, self._job_script())
            r.execute_command("chmod +x %s" % launch)
            ret, stdout = r.execute_command(
                "cd %s && ./launch_command %s > /dev/null 2>&1 & echo $!"
                % (wf_dir, submit_cmd), raise_when_error=False)

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

    def _get_cluster_context(self, cluster):
        version = cluster.hadoop_version
        handler = vhf.VersionHandlerFactory.get().get_handler(version)
        return handler.get_context(cluster)
