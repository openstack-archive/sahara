=====================================================
Running WordCount example from the Oozie command line
=====================================================

1) Copy the *edp-java.jar* file from *sahara/edp-examples/edp-java* to *./wordcount/lib/edp-java.jar*

2) Modify the *job.properties* file to specify the correct **jobTracker** and **nameNode** addresses for your cluster.

3) Modify the *workflow.xml* file to contain the correct input and output paths. These paths may be Sahara swift urls or hdfs paths.

   * If swift urls are used, set the **fs.swift.service.sahara.username** and **fs.swift.service.sahara.password**
     properties in the **<configuration>** section.

4) Upload the *wordcount* directory to hdfs

  $ hadoop fs -put wordcount wordcount

5) Launch the job, specifying the correct oozie server and port

  $ oozie job -oozie http://oozie_server:port/oozie -config wordcount/job.properties -run

6) Don't forget to create your swift input path!  A Sahara swift url looks like *swift://container.sahara/object*
