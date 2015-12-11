<%page args="is_proxy_gateway='true'"/>

clusters:
  - plugin_name: fake
    plugin_version: "0.1"
    image: ${fake_plugin_image}
    node_group_templates:
      - name: worker
        flavor: ${ci_flavor_id}
        node_processes:
          - datanode
          - tasktracker
        volumes_per_node: 2
        volumes_size: 2
        auto_security_group: true
      - name: master
        flavor: ${ci_flavor_id}
        node_processes:
          - jobtracker
          - namenode
        auto_security_group: true
        is_proxy_gateway: ${is_proxy_gateway}
    cluster_template:
      name: fake01
      node_group_templates:
        master: 1
        worker: 1
    cluster:
      name: ${cluster_name}
    scaling:
      - operation: add
        node_group: worker
        size: 1
    edp_jobs_flow: pig_job
