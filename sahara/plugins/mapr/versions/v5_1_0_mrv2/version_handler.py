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


import sahara.plugins.mapr.base.base_version_handler as bvh
from sahara.plugins.mapr.services.drill import drill
from sahara.plugins.mapr.services.flume import flume
from sahara.plugins.mapr.services.hbase import hbase
from sahara.plugins.mapr.services.hive import hive
from sahara.plugins.mapr.services.httpfs import httpfs
from sahara.plugins.mapr.services.hue import hue
from sahara.plugins.mapr.services.impala import impala
from sahara.plugins.mapr.services.mahout import mahout
from sahara.plugins.mapr.services.management import management as mng
from sahara.plugins.mapr.services.maprfs import maprfs
from sahara.plugins.mapr.services.oozie import oozie
from sahara.plugins.mapr.services.pig import pig
from sahara.plugins.mapr.services.spark import spark
from sahara.plugins.mapr.services.sqoop import sqoop2
from sahara.plugins.mapr.services.swift import swift
from sahara.plugins.mapr.services.yarn import yarn
import sahara.plugins.mapr.versions.v5_1_0_mrv2.context as c


version = "5.1.0.mrv2"


class VersionHandler(bvh.BaseVersionHandler):
    def __init__(self):
        super(VersionHandler, self).__init__()
        self._version = version
        self._required_services = [
            yarn.YARNv270(),
            maprfs.MapRFS(),
            mng.Management(),
            oozie.Oozie(),
        ]
        self._services = [
            hive.HiveV013(),
            hive.HiveV10(),
            hive.HiveV12(),
            impala.ImpalaV141(),
            pig.PigV014(),
            pig.PigV015(),
            flume.FlumeV16(),
            flume.FlumeV15(),
            sqoop2.Sqoop2(),
            mahout.MahoutV010(),
            oozie.OozieV410(),
            oozie.OozieV420(),
            hue.HueV370(),
            hue.HueV381(),
            hue.HueV390(),
            hbase.HBaseV0989(),
            hbase.HBaseV09812(),
            drill.DrillV11(),
            drill.DrillV12(),
            drill.DrillV14(),
            yarn.YARNv270(),
            maprfs.MapRFS(),
            mng.Management(),
            httpfs.HttpFS(),
            swift.Swift(),
            spark.SparkOnYarn()
        ]

    def get_context(self, cluster, added=None, removed=None):
        return c.Context(cluster, self, added, removed)
