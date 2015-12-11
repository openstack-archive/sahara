<%page args="is_proxy_gateway='true'"/>

clusters:
  - plugin_name: mapr
    plugin_version: 4.0.2.mrv2
    image: ${mapr_402mrv2_image}
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
        is_proxy_gateway: ${is_proxy_gateway}
      - name: worker
        flavor: ${ci_flavor_id}
        node_processes:
          - NodeManager
          - FileServer
        auto_security_group: true
        volumes_per_node: 2
        volumes_size: 20
    cluster_template:
      name: mapr402mrv2
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
