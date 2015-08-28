Example Spark Job
=================

This example contains the compiled classes for SparkPi extracted from
the example jar distributed with Apache Spark version 1.3.1.

SparkPi example estimates Pi. It can take a single optional integer
argument specifying the number of slices (tasks) to use.

Example spark-wordcount Job
==========================

spark-wordcount is a modified version of the WordCount example from Apache Spark.
It can read input data from hdfs or swift container, then output the number of occurrences
of each word to standard output or hdfs.

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
    3. Fill the ``Main class`` input with the following class: ``sahara.edp.spark.SparkWordCount``
    4. Put the following values in the job's configs: ``edp.spark.adapt_for_swift`` with value ``True``,
       ``fs.swift.service.sahara.password`` with password for your username, and
       ``fs.swift.service.sahara.username`` with your username. These values are required for
       correct access to your input file, located in Swift.
    5. Execute the job. You will be able to view your output in hdfs.
