clusters:
  - plugin_name: mapr
    plugin_version: 5.0.0.mrv2
    image: ${mapr_500mrv2_image}
    node_group_templates:
      - name: master
        flavor:
          vcpus: 4
          ram: 8192
          root_disk: 80
          ephemeral_disk: 40
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
      - name: worker
        flavor:
          vcpus: 2
          ram: 4096
          root_disk: 40
          ephemeral_disk: 40
        node_processes:
          - NodeManager
          - FileServer
        auto_security_group: true
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
    scenario:
      - scale
