Example Spark Job
=================

This example contains the compiled classes for SparkPi extracted from
the example jar distributed with Apache Spark version 1.3.1.

SparkPi example estimates Pi. It can take a single optional integer
argument specifying the number of slices (tasks) to use.

Example spark-wordcount Job
===========================

spark-wordcount is a modified version of the WordCount example from Apache
Spark. It can read input data from hdfs or swift container, then output the
number of occurrences of each word to standard output or hdfs.

Launching wordcount job from Sahara UI
--------------------------------------

1. Create a job binary that points to ``spark-wordcount.jar``.
2. Create a job template and set ``spark-wordcount.jar`` as the main binary
   of the job template.
3. Create a Swift container with your input file. As example, you can upload
   ``sample_input.txt``.
3. Launch job:

    1. Put path to input file in ``args``
    2. Put path to output file in ``args``
    3. Fill the ``Main class`` input with the following class:
       ``sahara.edp.spark.SparkWordCount``
    4. Put the following values in the job's configs:
       ``edp.spark.adapt_for_swift`` with value ``True``,
       ``fs.swift.service.sahara.password`` with password for your username,
       and ``fs.swift.service.sahara.username`` with your username. These
       values are required for correct access to your input file, located in
       Swift.
    5. Execute the job. You will be able to view your output in hdfs.

Launching spark-kafka-example
-----------------------------

0. Create a cluster with ``Kafka Broker``, ``ZooKeeper`` and
   ``Spark History Server``. The Ambari plugin can be used for that purpose.
   Please, use your keypair during cluster creation to have the ability to
   ssh in instances with that processes. For simplicity, these services
   should located on same the node.
1. Ssh to the node with the ``Kafka Broker`` service. Create a sample topic
   using the following command:
   ``path/kafka-topics.sh --create --zookeeper localhost:2181 \
   --replication-factor 1 --partitions 1 --topic test-topic``.
   Also execute ``path/kafka-console-producer.sh --broker-list \
   localhost:6667 --topic test-topic`` and then put several messages in the
   topic. Please, note that you need to replace the values ``localhost``
   and ``path`` with your own values.
2. Download the Spark Streaming utils to the node with your
   ``Spark History Server`` from this URL:
   ``http://central.maven.org/maven2/org/apache/spark/spark-streaming-kafka-assembly_2.10/1.4.1/spark-streaming-kafka-assembly_2.10-1.4.1.jar``.
   Now you are ready to launch your job from sahara UI.
3. Create a job binary that points to ``spark-kafka-example.py``.
   Also you need to create a job that uses this job binary as a main binary.
4. Execute the job with the following job configs:
   ``edp.spark.driver.classpath`` with a value that points to the utils
   downloaded during step 2. Also the job should be run with the following
   arguments: ``localhost:2181`` as the first argument, ``test-topic`` as
   the second, and ``30`` as the third.
5. Congratulations, your job was successfully launched!
