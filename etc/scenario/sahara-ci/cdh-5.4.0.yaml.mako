<%page args="is_proxy_gateway='true'"/>

clusters:
  - plugin_name: cdh
    plugin_version: 5.4.0
    image: ${cdh_5_4_0_image}
    node_group_templates:
      - name: worker-dn
        flavor: ${ci_flavor_id}
        node_processes:
          - HDFS_DATANODE
        volumes_per_node: 2
        volumes_size: 2
        auto_security_group: true
        node_configs:
          &ng_configs
          DATANODE:
            dfs_datanode_du_reserved: 0
      - name: worker-nm
        flavor: ${ci_flavor_id}
        node_processes:
          - YARN_NODEMANAGER
        auto_security_group: true
      - name: worker-nm-dn
        flavor: ${ci_flavor_id}
        node_processes:
          - YARN_NODEMANAGER
          - HDFS_DATANODE
        volumes_per_node: 2
        volumes_size: 2
        auto_security_group: true
        node_configs:
          *ng_configs
      - name: manager
        flavor: ${large_flavor_id}
        node_processes:
          - CLOUDERA_MANAGER
          - KMS
        auto_security_group: true
      - name: master-core
        flavor: ${medium_flavor_id}
        node_processes:
          - HDFS_NAMENODE
          - YARN_RESOURCEMANAGER
          - SENTRY_SERVER
          - YARN_NODEMANAGER
          - ZOOKEEPER_SERVER
        auto_security_group: true
        is_proxy_gateway: ${is_proxy_gateway}
      - name: master-additional
        flavor: ${medium_flavor_id}
        node_processes:
          - OOZIE_SERVER
          - YARN_JOBHISTORY
          - YARN_NODEMANAGER
          - HDFS_SECONDARYNAMENODE
          - HIVE_METASTORE
          - HIVE_SERVER2
          - SPARK_YARN_HISTORY_SERVER
        auto_security_group: true
    cluster_template:
      name: cdh540
      node_group_templates:
        manager: 1
        master-core: 1
        master-additional: 1
        worker-nm-dn: 1
        worker-nm: 1
        worker-dn: 1
      cluster_configs:
        HDFS:
          dfs_replication: 1
    cluster:
      name: ${cluster_name}
    scenario:
      - run_jobs
      - sentry
    edp_jobs_flow:
      - pig_job
      - mapreduce_job
      - mapreduce_streaming_job
      - java_job
      - spark_wordcount
