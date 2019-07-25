# Copyright (c) 2014 OpenStack Foundation
# Copyright (c) 2015 ISPRAS
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
from sahara.service.castellan import utils as key_manager
from sahara.service.edp import base_engine
from sahara.service.edp.job_binaries import manager as jb_manager
from sahara.service.edp import job_utils
from sahara.service.edp import s3_common
from sahara.service.validations.edp import job_execution as j
from sahara.swift import swift_helper as sw
from sahara.swift import utils as su
from sahara.utils import cluster as c_u
from sahara.utils import edp
from sahara.utils import files
from sahara.utils import remote
from sahara.utils import xmlutils

conductor = c.API
CONF = cfg.CONF


class SparkJobEngine(base_engine.JobEngine):
    def __init__(self, cluster):
        self.cluster = cluster
        # We'll always run the driver program on the master
        self.master = None
        # These parameters depend on engine that is used
        self.plugin_params = {"master": "",
                              "spark-user": "",
                              "deploy-mode": "",
                              "spark-submit": "",
                              "driver-class-path": "",
                              }

    def _get_pid_and_inst_id(self, job_id):
        try:
            pid, inst_id = job_id.split("@", 1)
            if pid and inst_id:
                return (pid, inst_id)
        except Exception:
            pass
        return "", ""

    def _get_instance_if_running(self, job_execution):
        pid, inst_id = self._get_pid_and_inst_id(job_execution.engine_job_id)
        if not pid or not inst_id or (
           job_execution.info['status'] in edp.JOB_STATUSES_TERMINATED):
            return None, None
        # TODO(tmckay): well, if there is a list index out of range
        # error here it probably means that the instance is gone. If we
        # have a job execution that is not terminated, and the instance
        # is gone, we should probably change the status somehow.
        # For now, do nothing.
        try:
            instance = c_u.get_instances(self.cluster, [inst_id])[0]
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

    def _job_script(self, python_version):
        path = "service/edp/resources/launch_command.py"
        return files.get_file_text(path).replace(
            '{{PYTHON_VERSION}}', python_version)

    def _upload_wrapper_xml(self, where, job_dir, job_configs):
        xml_name = 'spark.xml'
        proxy_configs = job_configs.get('proxy_configs')
        configs = {}
        cfgs = job_configs.get('configs', {})
        if proxy_configs:
            configs[sw.HADOOP_SWIFT_USERNAME] = proxy_configs.get(
                'proxy_username')
            configs[sw.HADOOP_SWIFT_PASSWORD] = key_manager.get_secret(
                proxy_configs.get('proxy_password'))
            configs[sw.HADOOP_SWIFT_TRUST_ID] = proxy_configs.get(
                'proxy_trust_id')
            configs[sw.HADOOP_SWIFT_DOMAIN_NAME] = CONF.proxy_user_domain_name
        else:
            targets = [sw.HADOOP_SWIFT_USERNAME]
            configs = {k: cfgs[k] for k in targets if k in cfgs}
            if sw.HADOOP_SWIFT_PASSWORD in cfgs:
                configs[sw.HADOOP_SWIFT_PASSWORD] = (
                    key_manager.get_secret(cfgs[sw.HADOOP_SWIFT_PASSWORD])
                )

        for s3_cfg_key in s3_common.S3_DS_CONFIGS:
            if s3_cfg_key in cfgs:
                if s3_cfg_key == s3_common.S3_SECRET_KEY_CONFIG:
                    configs[s3_cfg_key] = (
                        key_manager.get_secret(cfgs[s3_cfg_key])
                    )
                else:
                    configs[s3_cfg_key] = cfgs[s3_cfg_key]

        content = xmlutils.create_hadoop_xml(configs)
        with remote.get_remote(where) as r:
            dst = os.path.join(job_dir, xml_name)
            r.write_file_to(dst, content)
        return xml_name

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

        def upload_builtin(r, dir, builtin):
            dst = os.path.join(dir, builtin['name'])
            r.write_file_to(dst, builtin['raw'])
            return dst

        builtin_libs = []
        if edp.is_adapt_spark_for_swift_enabled(
                job_configs.get('configs', {})):
            path = 'service/edp/resources/edp-spark-wrapper.jar'
            name = 'builtin-%s.jar' % uuidutils.generate_uuid()
            builtin_libs = [{'raw': files.try_get_file_text(path),
                             'name': name}]

        uploaded_paths = []
        builtin_paths = []
        with remote.get_remote(where) as r:
            mains = list(job.mains) if job.mains else []
            libs = list(job.libs) if job.libs else []

            job_binaries = mains + libs
            self._prepare_job_binaries(job_binaries, r)

            for job_file in job_binaries:
                uploaded_paths.append(
                    upload(r, job_dir, job_file,
                           job_configs.get('proxy_configs')))

            for builtin in builtin_libs:
                builtin_paths.append(
                    upload_builtin(r, job_dir, builtin))

        return uploaded_paths, builtin_paths

    def _check_driver_class_path(self, job_configs, param_dict, wf_dir):
        overridden = edp.spark_driver_classpath(
            job_configs.get('configs', {}))
        if overridden:
            param_dict['driver-class-path'] = (
                " --driver-class-path " + overridden)
            return
        if not param_dict.get('wrapper_jar'):
            # no need in driver classpath if swift as datasource is not used
            param_dict['driver-class-path'] = ""
            return
        cp = param_dict['driver-class-path'] or ""
        if param_dict['deploy-mode'] == 'client' and not (
                cp.startswith(":") or cp.endswith(":")):
            cp += ":" + wf_dir
        param_dict['driver-class-path'] = " --driver-class-path " + cp

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

    def _build_command(self, wf_dir, paths, builtin_paths,
                       updated_job_configs):

        indep_params = {}

        # TODO(tmckay): for now, paths[0] is always assumed to be the app
        # jar and we generate paths in order (mains, then libs).
        # When we have a Spark job type, we can require a "main" and set
        # the app jar explicitly to be "main"
        indep_params["app_jar"] = paths.pop(0)
        indep_params["job_class"] = (
            updated_job_configs["configs"]["edp.java.main_class"])
        if self.plugin_params.get('drivers-to-jars', None):
            paths.extend(self.plugin_params['drivers-to-jars'])
        # If we uploaded builtins then we are using a wrapper jar. It will
        # be the first one on the builtin list and the original app_jar needs
        # to be added to the  'additional' jars
        if builtin_paths:
            indep_params["wrapper_jar"] = builtin_paths.pop(0)
            indep_params["wrapper_class"] = (
                'org.openstack.sahara.edp.SparkWrapper')
            wrapper_xml = self._upload_wrapper_xml(self.master,
                                                   wf_dir,
                                                   updated_job_configs)
            indep_params["wrapper_args"] = "%s %s" % (
                wrapper_xml, indep_params["job_class"])

            indep_params["addnl_files"] = wrapper_xml

            indep_params["addnl_jars"] = ",".join(
                [indep_params["wrapper_jar"]] + paths + builtin_paths)

        else:
            indep_params["addnl_jars"] = ",".join(paths)

        # All additional jars are passed with the --jars option
        if indep_params["addnl_jars"]:
            indep_params["addnl_jars"] = (
                " --jars " + indep_params["addnl_jars"])

        # Launch the spark job using spark-submit and deploy_mode = client
        # TODO(tmckay): we need to clean up wf_dirs on long running clusters
        # TODO(tmckay): probably allow for general options to spark-submit
        indep_params["args"] = updated_job_configs.get('args', [])
        indep_params["args"] = " ".join([su.inject_swift_url_suffix(arg)
                                         for arg in indep_params["args"]])
        if indep_params.get("args"):
            indep_params["args"] = (" " + indep_params["args"])

        mutual_dict = self.plugin_params.copy()
        mutual_dict.update(indep_params)

        # Handle driver classpath. Because of the way the hadoop
        # configuration is handled in the wrapper class, using
        # wrapper_xml, the working directory must be on the classpath
        self._check_driver_class_path(updated_job_configs, mutual_dict, wf_dir)

        if mutual_dict.get("wrapper_jar"):
            # Substrings which may be empty have spaces
            # embedded if they are non-empty
            cmd = (
                '%(spark-user)s%(spark-submit)s%(driver-class-path)s'
                ' --files %(addnl_files)s'
                ' --class %(wrapper_class)s%(addnl_jars)s'
                ' --master %(master)s'
                ' --deploy-mode %(deploy-mode)s'
                ' %(app_jar)s %(wrapper_args)s%(args)s') % dict(
                mutual_dict)
        else:
            cmd = (
                '%(spark-user)s%(spark-submit)s%(driver-class-path)s'
                ' --class %(job_class)s%(addnl_jars)s'
                ' --master %(master)s'
                ' --deploy-mode %(deploy-mode)s'
                ' %(app_jar)s%(args)s') % dict(
                mutual_dict)

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

        # It is needed in case we are working with Spark plugin
        self.plugin_params['master'] = (
            self.plugin_params['master'] % {'host': self.master.hostname()})

        # TODO(tmckay): wf_dir should probably be configurable.
        # The only requirement is that the dir is writable by the image user
        wf_dir = job_utils.create_workflow_dir(self.master, '/tmp/spark-edp',
                                               job, job_execution.id, "700")
        paths, builtin_paths = self._upload_job_files(
            self.master, wf_dir, job, updated_job_configs)

        # We can shorten the paths in this case since we'll run out of wf_dir
        paths = [os.path.basename(p) if p.startswith(wf_dir) else p
                 for p in paths]
        builtin_paths = [os.path.basename(p) for p in builtin_paths]

        cmd = self._build_command(wf_dir, paths, builtin_paths,
                                  updated_job_configs)

        job_execution = conductor.job_execution_get(ctx, job_execution.id)
        if job_execution.info['status'] == edp.JOB_STATUS_TOBEKILLED:
            return (None, edp.JOB_STATUS_KILLED, None)

        # If an exception is raised here, the job_manager will mark
        # the job failed and log the exception
        # The redirects of stdout and stderr will preserve output in the wf_dir
        with remote.get_remote(self.master) as r:
            # Upload the command launch script
            launch = os.path.join(wf_dir, "launch_command")
            python_version = r.get_python_version()
            r.write_file_to(launch, self._job_script(python_version))
            r.execute_command("chmod u+rwx,g+rx,o+rx %s" % wf_dir)
            r.execute_command("chmod +x %s" % launch)
            ret, stdout = r.execute_command(
                "cd %s; ./launch_command %s > /dev/null 2>&1 & echo $!"
                % (wf_dir, cmd))

        if ret == 0:
            # Success, we'll add the wf_dir in job_execution.extra and store
            # pid@instance_id as the job id

            # We know the job is running so return "RUNNING"
            return (stdout.strip() + "@" + self.master.id,
                    edp.JOB_STATUS_RUNNING,
                    {'spark-path': wf_dir})

        # Hmm, no execption but something failed.
        # Since we're using backgrounding with redirect, this is unlikely.
        raise e.EDPError(_("Spark job execution failed. Exit status = "
                           "%(status)s, stdout = %(stdout)s") %
                         {'status': ret, 'stdout': stdout})

    def run_scheduled_job(self, job_execution):
        raise e.NotImplementedException(_("Currently Spark engine does not"
                                          " support scheduled EDP jobs"))

    def validate_job_execution(self, cluster, job, data):
        j.check_main_class_present(data, job)

    @staticmethod
    def get_possible_job_config(job_type):
        return {'job_config': {'configs': [], 'args': []}}

    @staticmethod
    def get_supported_job_types():
        return [edp.JOB_TYPE_SPARK]


class SparkShellJobEngine(SparkJobEngine):
    def _build_command(self, wf_dir, paths, builtin_paths,
                       updated_job_configs):
        main_script = paths.pop(0)
        args = " ".join(updated_job_configs.get('args', []))

        env_params = ""
        params = updated_job_configs.get('params', {})
        for key, value in params.items():
            env_params += "{key}={value} ".format(key=key, value=value)

        cmd = ("{env_params}{cmd} {main_script} {args}".format(
            cmd='/bin/sh', main_script=main_script, env_params=env_params,
            args=args))

        return cmd

    def validate_job_execution(self, cluster, job, data):
        # Shell job doesn't require any special validation
        pass

    @staticmethod
    def get_possible_job_config(job_type):
        return {'job_config': {'configs': {}, 'args': [], 'params': {}}}

    @staticmethod
    def get_supported_job_types():
        return [edp.JOB_TYPE_SHELL]
