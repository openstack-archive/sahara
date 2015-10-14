clusters:
  - plugin_name: spark
    plugin_version: 1.0.0
    image: ${spark_image}
    node_group_templates:
      - name: master
        flavor: ${ci_flavor_id}
        node_processes:
          - master
          - namenode
        auto_security_group: true
      - name: worker
        flavor: ${ci_flavor_id}
        node_processes:
          - datanode
          - slave
        auto_security_group: true
    cluster_template:
      name: spark100
      node_group_templates:
        master: 1
        worker: 1
      cluster_configs:
        HDFS:
          dfs.replication: 1
    cluster:
      name: ${cluster_name}
    scaling:
      - operation: add
        node_group: worker
        size: 1
    edp_jobs_flow:
      - spark_pi
      - spark_wordcount
