concurrency: 1

credentials:
    os_username: ${OS_USERNAME}
    os_password: ${OS_PASSWORD}
    os_tenant: ${OS_TENANT_NAME}
    os_auth_url: ${OS_AUTH_URL}

network:
    type: ${network_type}
    private_network: ${network_private_name}
    public_network: ${network_public_name}

clusters:
    - plugin_name: vanilla
      plugin_version: 2.6.0
      image: ${vanilla_two_six_image}
      node_group_templates:
        - name: master
          node_processes:
            - namenode
            - resourcemanager
            - hiveserver
            - oozie
            - historyserver
            - secondarynamenode
          flavor: ${ci_flavor_id}
        - name: worker
          node_processes:
            - datanode
            - nodemanager
          flavor: ${ci_flavor_id}
      cluster_template:
          name: vanilla
          node_group_templates:
              master: 1
              worker: 3
      scenario:
          - run_jobs
          - scale
          - run_jobs
      edp_jobs_flow: test_flow
      retain_resources: true

edp_jobs_flow:
    test_flow:
        - type: Pig
          input_datasource:
              type: swift
              source: etc/edp-examples/edp-pig/top-todoers/data/input
          output_datasource:
              type: hdfs
              destination: /user/hadoop/edp-output
          main_lib:
              type: swift
              source: etc/edp-examples/edp-pig/top-todoers/example.pig
        - type: Java
          additional_libs:
              - type: database
                source: etc/edp-examples/hadoop2/edp-java/hadoop-mapreduce-examples-2.4.1.jar
          configs:
              edp.java.main_class: org.apache.hadoop.examples.QuasiMonteCarlo
          args:
              - 10
              - 10
        - type: MapReduce
          configs:
              mapred.mapper.class: org.apache.oozie.example.SampleMapper
              mapred.reducer.class: org.apache.oozie.example.SampleReducer
          additional_libs:
              - type: database
                source: etc/edp-examples/edp-java/edp-java.jar
          input_datasource:
              type: swift
              source: etc/edp-examples/edp-pig/top-todoers/data/input
          output_datasource:
              type: hdfs
              destination: /user/hadoop/edp-output
        - type: MapReduce.Streaming
          configs:
                edp.streaming.mapper: /bin/cat
                edp.streaming.reducer: /usr/bin/wc
          input_datasource:
              type: swift
              source: etc/edp-examples/edp-pig/top-todoers/data/input
          output_datasource:
              type: hdfs
              destination: /user/hadoop/edp-output
        - type: Hive
          input_datasource:
              type: swift
              source: etc/edp-examples/edp-hive/input.csv
          output_datasource:
              type: hdfs
              destination: /user/hadoop/edp-hive/
          main_lib:
              type: swift
              source: etc/edp-examples/edp-hive/script.q
