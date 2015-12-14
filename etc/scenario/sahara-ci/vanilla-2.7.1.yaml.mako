<%page args="is_proxy_gateway='true'"/>

clusters:
  - plugin_name: vanilla
    plugin_version: 2.7.1
    image: ${vanilla_two_seven_one_image}
    node_group_templates:
      - name: worker-dn-nm
        flavor: ${ci_flavor_id}
        node_processes:
          - datanode
          - nodemanager
        volumes_per_node: 2
        volumes_size: 2
        auto_security_group: true
      - name: worker-nm
        flavor: ${ci_flavor_id}
        node_processes:
          - nodemanager
        auto_security_group: true
      - name: worker-dn
        flavor: ${ci_flavor_id}
        node_processes:
          - datanode
        volumes_per_node: 2
        volumes_size: 2
        auto_security_group: true
      - name: master-rm-nn-hvs
        flavor: ${ci_flavor_id}
        node_processes:
          - namenode
          - resourcemanager
          - hiveserver
          - nodemanager
        auto_security_group: true
      - name: master-oo-hs-sn
        flavor: ${ci_flavor_id}
        node_processes:
          - oozie
          - historyserver
          - secondarynamenode
          - nodemanager
        auto_security_group: true
        is_proxy_gateway: ${is_proxy_gateway}
    cluster_template:
      name: vanilla271
      node_group_templates:
        master-rm-nn-hvs: 1
        master-oo-hs-sn: 1
        worker-dn-nm: 2
        worker-dn: 1
        worker-nm: 1
      cluster_configs:
        HDFS:
          dfs.replication: 1
    cluster:
      name: ${cluster_name}
    scaling:
      - operation: resize
        node_group: worker-dn-nm
        size: 1
      - operation: resize
        node_group: worker-dn
        size: 0
      - operation: resize
        node_group: worker-nm
        size: 0
      - operation: add
        node_group: worker-dn
        size: 1
      - operation: add
        node_group: worker-nm
        size: 2
    edp_jobs_flow:
      - pig_job
      - mapreduce_job
      - mapreduce_streaming_job
      - java_job
      - hive_job