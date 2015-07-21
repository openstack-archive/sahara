clusters:
  - plugin_name: hdp
    plugin_version: 1.3.2
    image: ${hdp_image}
    node_group_templates:
      - name: master
        flavor: ${ci_flavor_id}
        node_processes:
          - JOBTRACKER
          - NAMENODE
          - SECONDARY_NAMENODE
          - GANGLIA_SERVER
          - NAGIOS_SERVER
          - AMBARI_SERVER
          - OOZIE_SERVER
        auto_security_group: false
      - name: worker
        flavor: ${ci_flavor_id}
        node_processes:
          - TASKTRACKER
          - DATANODE
          - HDFS_CLIENT
          - MAPREDUCE_CLIENT
          - OOZIE_CLIENT
          - PIG
        volumes_per_node: 2
        volumes_size: 2
        auto_security_group: false
    cluster_template:
      name: hdp132
      node_group_templates:
        master: 1
        worker: 3
    cluster:
      name: ${cluster_name}
    scaling:
      - operation: add
        node_group: worker
        size: 1
    edp_jobs_flow: hadoop_1
