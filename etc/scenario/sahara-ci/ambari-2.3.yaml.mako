clusters:
  - plugin_name: ambari
    plugin_version: '2.3'
    image: ${ambari_2_1_image}
    node_group_templates:
      - name: master
        flavor: ${medium_flavor_id}
        node_processes:
          - Ambari
          - MapReduce History Server
          - Spark History Server
          - NameNode
          - ResourceManager
          - SecondaryNameNode
          - YARN Timeline Server
          - ZooKeeper
          - Kafka Broker
        auto_security_group: true
      - name: master-edp
        flavor: ${ci_flavor_id}
        node_processes:
          - Hive Metastore
          - HiveServer
          - Oozie
        auto_security_group: true
      - name: worker
        flavor: ${ci_flavor_id}
        node_processes:
          - DataNode
          - NodeManager
        volumes_per_node: 2
        volumes_size: 2
        auto_security_group: true
    cluster_template:
      name: ambari21
      node_group_templates:
        master: 1
        master-edp: 1
        worker: 3
      cluster_configs:
        HDFS:
          dfs.datanode.du.reserved: 0
    custom_checks:
      check_kafka:
        zookeeper_process: ZooKeeper
        kafka_process: Kafka Broker
        spark_flow:
          - type: Spark
            main_lib:
              type: database
              source: etc/edp-examples/edp-spark/spark-kafka-example.jar
            args:
              - '{zookeeper_list}'
              - '{topic}'
              - '{timeout}'
            timeout: 30
    cluster:
      name: ${cluster_name}
    scenario:
      - run_jobs
      - kafka

    edp_jobs_flow:
      - java_job
      - spark_pi
