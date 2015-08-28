edp_jobs_flow:
  hadoop_2:
    - type: Pig
      input_datasource:
        type: swift
        source: etc/edp-examples/edp-pig/trim-spaces/data/input
      output_datasource:
        type: hdfs
        destination: /user/hadoop/edp-output
      main_lib:
        type: swift
        source: etc/edp-examples/edp-pig/trim-spaces/example.pig
      additional_libs:
        - type: swift
          source: etc/edp-examples/edp-pig/trim-spaces/udf.jar
    - type: MapReduce
      input_datasource:
        type: swift
        source: etc/edp-examples/edp-pig/trim-spaces/data/input
      output_datasource:
        type: hdfs
        destination: /user/hadoop/edp-output
      additional_libs:
        - type: database
          source:  etc/edp-examples/edp-mapreduce/edp-mapreduce.jar
      configs:
        mapred.mapper.class: org.apache.oozie.example.SampleMapper
        mapred.reducer.class: org.apache.oozie.example.SampleReducer
    - type: MapReduce.Streaming
      input_datasource:
        type: swift
        source: etc/edp-examples/edp-pig/trim-spaces/data/input
      output_datasource:
        type: hdfs
        destination: /user/hadoop/edp-output
      configs:
        edp.streaming.mapper: /bin/cat
        edp.streaming.reducer: /usr/bin/wc
    - type: Java
      additional_libs:
        - type: database
          source: etc/edp-examples/hadoop2/edp-java/hadoop-mapreduce-examples-2.6.0.jar
      configs:
       edp.java.main_class: org.apache.hadoop.examples.QuasiMonteCarlo
      args:
        - 10
        - 10
  hadoop_1:
    - type: Pig
      input_datasource:
        type: swift
        source: etc/edp-examples/edp-pig/trim-spaces/data/input
      output_datasource:
        type: hdfs
        destination: /user/hadoop/edp-output
      main_lib:
        type: swift
        source: etc/edp-examples/edp-pig/trim-spaces/example.pig
      additional_libs:
        - type: swift
          source: etc/edp-examples/edp-pig/trim-spaces/udf.jar
      configs:
        dfs.replication: 1
    - type: MapReduce
      input_datasource:
        type: swift
        source: etc/edp-examples/edp-pig/trim-spaces/data/input
      output_datasource:
        type: hdfs
        destination: /user/hadoop/edp-output
      additional_libs:
        - type: database
          source:  etc/edp-examples/edp-mapreduce/edp-mapreduce.jar
      configs:
        dfs.replication: 1
        mapred.mapper.class: org.apache.oozie.example.SampleMapper
        mapred.reducer.class: org.apache.oozie.example.SampleReducer
    - type: MapReduce.Streaming
      input_datasource:
        type: swift
        source: etc/edp-examples/edp-pig/trim-spaces/data/input
      output_datasource:
        type: hdfs
        destination: /user/hadoop/edp-output
      configs:
        dfs.replication: 1
        edp.streaming.mapper: /bin/cat
        edp.streaming.reducer: /usr/bin/wc
  spark_edp:
    - type: Spark
      main_lib:
        type: database
        source: etc/edp-examples/edp-spark/spark-example.jar
      configs:
        edp.java.main_class: org.apache.spark.examples.SparkPi
      args:
        - 4
    - type: Spark
      input_datasource:
        type: swift
        source: etc/edp-examples/edp-spark/sample_input.txt
      main_lib:
        type: database
        source: etc/edp-examples/edp-spark/spark-wordcount.jar
      configs:
        edp.java.main_class: sahara.edp.spark.SparkWordCount
        edp.spark.adapt_for_swift: true
        fs.swift.service.sahara.username: ${OS_USERNAME}
        fs.swift.service.sahara.password: ${OS_PASSWORD}
      args:
        - '{input_datasource}'
  transient:
    - type: Pig
      input_datasource:
        type: swift
        source: etc/edp-examples/edp-pig/trim-spaces/data/input
      output_datasource:
        type: hdfs
        destination: /user/hadoop/edp-output
      main_lib:
        type: swift
        source: etc/edp-examples/edp-pig/trim-spaces/example.pig
      additional_libs:
        - type: swift
          source: etc/edp-examples/edp-pig/trim-spaces/udf.jar
  mapr:
    - type: Pig
      input_datasource:
        type: maprfs
        source: etc/edp-examples/edp-pig/trim-spaces/data/input
      output_datasource:
        type: maprfs
        destination: /user/hadoop/edp-output
      main_lib:
        type: swift
        source: etc/edp-examples/edp-pig/trim-spaces/example.pig
      additional_libs:
        - type: swift
          source: etc/edp-examples/edp-pig/trim-spaces/udf.jar
    - type: MapReduce
      input_datasource:
        type: maprfs
        source: etc/edp-examples/edp-pig/trim-spaces/data/input
      output_datasource:
        type: maprfs
        destination: /user/hadoop/edp-output
      additional_libs:
        - type: database
          source:  etc/edp-examples/edp-mapreduce/edp-mapreduce.jar
      configs:
        mapred.mapper.class: org.apache.oozie.example.SampleMapper
        mapred.reducer.class: org.apache.oozie.example.SampleReducer
    - type: MapReduce.Streaming
      input_datasource:
        type: maprfs
        source: etc/edp-examples/edp-pig/trim-spaces/data/input
      output_datasource:
        type: maprfs
        destination: /user/hadoop/edp-output
      configs:
        edp.streaming.mapper: /bin/cat
        edp.streaming.reducer: /usr/bin/wc
    - type: Java
      additional_libs:
        - type: database
          source: etc/edp-examples/hadoop2/edp-java/hadoop-mapreduce-examples-2.6.0.jar
      configs:
       edp.java.main_class: org.apache.hadoop.examples.QuasiMonteCarlo
      args:
        - 10
        - 10
