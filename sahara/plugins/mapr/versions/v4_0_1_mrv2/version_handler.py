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


from sahara.plugins.mapr.base import base_version_handler as bvh
from sahara.plugins.mapr.services.drill import drill
from sahara.plugins.mapr.services.flume import flume
from sahara.plugins.mapr.services.hbase import hbase
from sahara.plugins.mapr.services.hive import hive
from sahara.plugins.mapr.services.httpfs import httpfs
from sahara.plugins.mapr.services.hue import hue
from sahara.plugins.mapr.services.mahout import mahout
from sahara.plugins.mapr.services.management import management
from sahara.plugins.mapr.services.maprfs import maprfs
from sahara.plugins.mapr.services.oozie import oozie
from sahara.plugins.mapr.services.pig import pig
from sahara.plugins.mapr.services.sqoop import sqoop2
from sahara.plugins.mapr.services.swift import swift
from sahara.plugins.mapr.services.yarn import yarn
import sahara.plugins.mapr.versions.v4_0_1_mrv2.context as c


version = '4.0.1.mrv2'


class VersionHandler(bvh.BaseVersionHandler):
    def __init__(self):
        super(VersionHandler, self).__init__()
        self._version = version
        self._required_services = [
            yarn.YARNv241(),
            maprfs.MapRFS(),
            management.Management(),
            oozie.Oozie(),
        ]
        self._services = [
            maprfs.MapRFS(),
            management.Management(),
            oozie.Oozie(),
            hive.HiveV012(),
            hive.HiveV013(),
            hbase.HBaseV094(),
            hbase.HBaseV098(),
            httpfs.HttpFS(),
            mahout.Mahout(),
            pig.Pig(),
            swift.Swift(),
            yarn.YARNv241(),
            flume.Flume(),
            drill.Drill(),
            sqoop2.Sqoop2(),
            hue.Hue(),
        ]

    def get_context(self, cluster, added=None, removed=None):
        return c.Context(cluster, self, added, removed)
