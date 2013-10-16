Welcome to Savanna!
===================

Savanna project aims to provide users with simple means to provision a Hadoop
cluster at OpenStack by specifying several parameters like Hadoop version,
cluster topology, nodes hardware details and a few more.

Overview
--------

* :doc:`overview`
* :doc:`architecture`
* `Roadmap <https://wiki.openstack.org/wiki/Savanna/Roadmap>`_


User guide
----------

**Installation**

.. toctree::
   :maxdepth: 1

   userdoc/installation.guide
   horizon/installation.guide

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
   userdoc/hdp_plugin

**Elastic Data Processing**

.. toctree::
   :maxdepth: 1

   userdoc/edp

**APIs**

.. toctree::
   :maxdepth: 1

   userdoc/python_client
   userdoc/rest_api_v1.0
   userdoc/rest_api_v1.1_EDP

**Miscellaneous**

.. toctree::
   :maxdepth: 1

   userdoc/hadoop-swift
   userdoc/diskimagebuilder


Developer Guide
---------------
**Programming HowTos and Tutorials**

.. toctree::
    :maxdepth: 1

    devref/development.guidelines
    devref/development.environment
    horizon/dev.environment.guide
    devref/quickstart
    devref/how_to_participate


**Background Concepts for Savanna**

.. toctree::
    :maxdepth: 1

    devref/plugins
    devref/plugin.spi
    devref/edp.spi
    userdoc/statuses


**Other Resources**

.. toctree::
   :maxdepth: 1

   devref/launchpad
   devref/gerrit
   devref/jenkins
