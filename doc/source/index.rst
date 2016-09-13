Welcome to Sahara!
==================

The sahara project aims to provide users with a simple means to provision data
processing frameworks (such as Hadoop, Spark and Storm) on OpenStack. This is
accomplished by specifying configuration parameters such as the framework
version, cluster topology, node hardware details and more.

Overview
--------

.. toctree::
    :maxdepth: 1

    overview
    architecture
    Roadmap <https://wiki.openstack.org/wiki/Sahara/Roadmap>


User guide
----------

**Installation**

.. toctree::
   :maxdepth: 1

   userdoc/installation.guide
   userdoc/configuration.guide
   userdoc/dashboard.guide
   userdoc/advanced.configuration.guide
   userdoc/upgrade.guide
   userdoc/sampleconfig

**How To**

.. toctree::
   :maxdepth: 1

   userdoc/overview
   horizon/dashboard.user.guide
   userdoc/features
   userdoc/registering_image

**Plugins**

.. toctree::
   :maxdepth: 1

   userdoc/plugins
   userdoc/vanilla_plugin
   userdoc/ambari_plugin
   userdoc/spark_plugin
   userdoc/cdh_plugin
   userdoc/mapr_plugin

**Elastic Data Processing**

.. toctree::
   :maxdepth: 1

   userdoc/edp

**API**

.. toctree::
   :maxdepth: 2

   restapi

**Miscellaneous**

.. toctree::
   :maxdepth: 1

   userdoc/guest-requirements
   userdoc/hadoop-swift
   userdoc/vanilla_imagebuilder
   userdoc/cdh_imagebuilder

Developer Guide
---------------
**Programming HowTos and Tutorials**

.. toctree::
    :maxdepth: 1

    devref/development.guidelines
    devref/development.environment
    devref/devstack
    horizon/dev.environment.guide
    devref/quickstart
    devref/how_to_participate
    devref/how_to_build_oozie
    devref/adding_database_migrations
    devref/testing
    devref/log.guidelines
    devref/apiv2

**Background Concepts for Sahara**

.. toctree::
    :maxdepth: 1

    devref/plugins
    devref/plugin.spi
    devref/edp.spi
    userdoc/statuses
    userdoc/sahara_on_ironic

**Other Resources**

.. toctree::
   :maxdepth: 1

   devref/launchpad
   devref/gerrit
   devref/jenkins
