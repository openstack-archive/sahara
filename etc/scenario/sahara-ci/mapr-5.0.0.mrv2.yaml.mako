clusters:
  - plugin_name: mapr
    plugin_version: 5.0.0.mrv2
    image: ${mapr_500mrv2_image}
    node_group_templates:
      - name: master
        flavor: ${ci_flavor_id}
        node_processes:
          - Metrics
          - Webserver
          - ZooKeeper
          - HTTPFS
          - Oozie
          - FileServer
          - CLDB
          - Flume
          - Hue
          - NodeManager
          - HistoryServer
          - ResourceManager
          - HiveServer2
          - HiveMetastore
          - Sqoop2-Client
          - Sqoop2-Server
        auto_security_group: true
        volumes_per_node: 2
        volumes_size: 20
      - name: worker
        flavor: ${ci_flavor_id}
        node_processes:
          - NodeManager
          - FileServer
        auto_security_group: true
        volumes_per_node: 2
        volumes_size: 20
    cluster_template:
      name: mapr500mrv2
      node_group_templates:
        master: 1
        worker: 3
    cluster:
      name: ${cluster_name}
    scaling:
      - operation: add
        node_group: worker
        size: 1
    edp_jobs_flow: mapr
