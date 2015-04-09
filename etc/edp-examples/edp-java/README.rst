=====================
EDP WordCount Example
=====================

Overview
--------

``WordCount.java`` is a modified version of the WordCount example bundled with
version 1.2.1 of Apache Hadoop. It has been extended for use from a java action
in an Oozie workflow. The modification below allows any configuration values
from the ``<configuration>`` tag in an Oozie workflow to be set in the
Configuration object::

    // This will add properties from the <configuration> tag specified
    // in the Oozie workflow.  For java actions, Oozie writes the
    // configuration values to a file pointed to by ooze.action.conf.xml
    conf.addResource(new Path("file:///",
                              System.getProperty("oozie.action.conf.xml")));

In the example workflow, we use the ``<configuration>`` tag to specify user and
password configuration values for accessing swift objects.

Compiling
---------

To build the jar, add ``hadoop-core`` and ``commons-cli`` to the classpath.

On a node running Ubuntu 13.04 with hadoop 1.2.1 the following commands
will compile ``WordCount.java`` from within the ``src`` directory::

    $ mkdir wordcount_classes
    $ javac -classpath /usr/share/hadoop/hadoop-core-1.2.1.jar:/usr/share/hadoop/lib/commons-cli-1.2.jar -d wordcount_classes WordCount.java
    $ jar -cvf edp-java.jar -C wordcount_classes/ .

Note, on a node with hadoop 2.3.0 the ``javac`` command above can be replaced with:

    $ javac -classpath /opt/hadoop-2.3.0/share/hadoop/common/hadoop-common-2.3.0.jar:/opt/hadoop-2.3.0/share/hadoop/mapreduce/hadoop-mapreduce-client-core-2.3.0.jar:/opt/hadoop-2.3.0/share/hadoop/common/lib/commons-cli-1.2.jar:/opt/hadoop-2.3.0/share/hadoop/mapreduce/lib/hadoop-annotations-2.3.0.jar -d wordcount_classes WordCount.java

Running from the Sahara UI
--------------------------

Running the WordCount example from the sahara UI is very similar to running a
Pig, Hive, or MapReduce job.

1. Create a job binary that points to the ``edp-java.jar`` file
2. Create a ``Java`` job type and add the job binary to the ``libs`` value
3. Launch the job:

    1. Add the input and output paths to ``args``
    2. If swift input or output paths are used, set the
       ``fs.swift.service.sahara.username`` and
       ``fs.swift.service.sahara.password`` configuration values
    3. The Sahara UI will prompt for the required ``main_class`` value and
       the optional ``java_opts`` value


