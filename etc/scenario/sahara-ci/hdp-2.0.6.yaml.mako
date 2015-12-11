<%page args="is_proxy_gateway='true'"/>

clusters:
  - plugin_name: hdp
    plugin_version: 2.0.6
    image: ${hdp_two_image}
    node_group_templates:
      - name: master
        flavor: ${ci_flavor_id}
        node_processes:
          - AMBARI_SERVER
          - GANGLIA_SERVER
          - HISTORYSERVER
          - NAGIOS_SERVER
          - NAMENODE
          - OOZIE_SERVER
          - RESOURCEMANAGER
          - SECONDARY_NAMENODE
          - ZOOKEEPER_SERVER
        auto_security_group: true
        is_proxy_gateway: ${is_proxy_gateway}
      - name: worker
        flavor: ${ci_flavor_id}
        node_processes:
          - DATANODE
          - HDFS_CLIENT
          - MAPREDUCE2_CLIENT
          - NODEMANAGER
          - OOZIE_CLIENT
          - PIG
          - YARN_CLIENT
          - ZOOKEEPER_CLIENT
        volumes_per_node: 2
        volumes_size: 2
        auto_security_group: true
    cluster_template:
      name: hdp206
      node_group_templates:
        master: 1
        worker: 3
      cluster_configs:
        YARN:
          yarn.log-aggregation-enable: false
    cluster:
      name: ${cluster_name}
    scaling:
      - operation: add
        node_group: worker
        size: 1
    edp_jobs_flow:
      - pig_job
      - mapreduce_job
      - mapreduce_streaming_job
      - java_job
