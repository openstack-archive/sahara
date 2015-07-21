clusters:
  - plugin_name: vanilla
    plugin_version: 1.2.1
    image: ${vanilla_image}
    node_group_templates:
      - name: worker-tt-dn
        flavor: ${ci_flavor_id}
        node_processes:
          - datanode
          - tasktracker
        volumes_per_node: 2
        volumes_size: 2
        auto_security_group: true
      - name: worker-tt
        flavor: ${ci_flavor_id}
        node_processes:
          - tasktracker
        auto_security_group: true
      - name: worker-dn
        flavor: ${ci_flavor_id}
        node_processes:
          - datanode
        volumes_per_node: 2
        volumes_size: 2
        auto_security_group: true
      - name: master-jt-nn
        flavor: ${ci_flavor_id}
        node_processes:
          - namenode
          - jobtracker
        auto_security_group: true
      - name: master-sec-nn-oz
        flavor: ${ci_flavor_id}
        node_processes:
          - oozie
          - secondarynamenode
        auto_security_group: true

    cluster_template:
      name: vanilla121
      node_group_templates:
        master-sec-nn-oz: 1
        master-jt-nn: 1
        worker-tt: 1
        worker-tt-dn: 2
        worker-dn: 1
      cluster_configs:
        HDFS:
          dfs.replication: 1
        MapReduce:
          mapred.map.tasks.speculative.execution: False
          mapred.child.java.opts: -Xmx512m
        general:
          'Enable Swift': True
    cluster:
      name: ${cluster_name}
    scaling:
      - operation: resize
        node_group: worker-tt-dn
        size: 1
      - operation: resize
        node_group: worker-dn
        size: 0
      - operation: resize
        node_group: worker-tt
        size: 0
      - operation: add
        node_group: worker-tt
        size: 1
      - operation: add
        node_group: worker-dn
        size: 1
    edp_jobs_flow: hadoop_1
