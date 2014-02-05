How to build Oozie
==================

.. note::

    Apache does not make Oozie builds, so it has to be built manually.

Prerequisites
-------------

 * Maven
 * JDK 1.6 (1.7 is not allowed there)
 * Downloaded Oozie distribution from `Apache mirror <http://apache-mirror.rbc.ru/pub/apache/oozie/4.0.0>`_
 * Downloaded `ext-2.2.zip <http://extjs.com/deploy/ext-2.2.zip>`_ (it is needed for enable Oozie web console)
 * All Hadoop jar files (either on hadoop cluster or simply from any repository)

.. note::

    Name of extJS archive should be only ``ext-2.2.zip``, there is a check in oozie-setup.sh

To build oozie.tar.gz you should follow the steps below:

* Make package:

.. sourcecode:: console

    $ bin/mkdistro.sh -DskipTests

* Unpack file distro/target/oozie-x.x.x-distro.tar.gz
* Create ``libext`` directory in <oozie-path>
* Copy hadoop jars (including hadoop-core, hadoop-client, hadoop-auth) and ``ext-2.2.zip`` to ``libext`` directory
* Prepare war for Oozie web console:

.. sourcecode:: console

    $ bin/oozie-setup.sh prepare-war

Then your Oozie package is ready, pack it to tar.gz:

.. sourcecode:: console

    $ tar -czf oozie.tar.gz <oozie-dir>

Similar instruction to build oozie.tar.gz you may find there: http://oozie.apache.org/docs/4.0.0/DG_QuickStart.html#Building_Oozie
