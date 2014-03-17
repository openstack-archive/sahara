Sahara UI User Guide
====================

This guide assumes that you already have sahara-api and the Sahara Dashboard configured and running.
If you require assistance with that, please see the installation guides.

Launching a cluster via the Sahara Dashboard
--------------------------------------------
Registering an Image
--------------------

1) Navigate to the "Sahara" tab in the dashboard, then click on the "Image Registry" panel.

2) From that page, click on the "Register Image" button at the top right.

3) Choose the image that you'd like to register as a Hadoop Image

4) Enter the username of the cloud-init user on the image.

5) Click on the tags that you want to add to the image. (A version ie: 1.2.1 and a type ie: vanilla are required for cluster functionality)

6) Click the "Done" button to finish the registration.

Create Node Group Templates
---------------------------

1) Navigate to the "Sahara" tab in the dashboard, then click on the "Node Group Templates" panel.

2) From that page, click on the "Create Template" button at the top right.

3) Choose your desired Plugin name and Version from the dropdowns and click "Create".

4) Give your Node Group Template a name (description is optional)

5) Choose a flavor for this template (based on your CPU/memory/disk needs)

6) Choose the storage location for your instance, this can be either "Ephemeral Drive" or "Cinder Volume".  If you choose "Cinder Volume", you will need to add additional configuration.

7) Choose which processes should be run for any instances that are spawned from this Node Group Template.

8) Click on the "Create" button to finish creating your Node Group Template.

Create a Cluster Template
-------------------------

1) Navigate to the "Sahara" tab in the dashboard, then click on the "Cluster Templates" panel.

2) From that page, click on the "Create Template" button at the top right.

3) Choose your desired Plugin name and Version from the dropdowns and click "Create".

4) Under the "Details" tab, you must give your template a name.

5) Under the "Node Groups" tab, you should add one or more nodes that can be based on one or more templates.

  - To do this, start by choosing a Node Group Template from the dropdown and click the "+" button.
  - You can adjust the number of nodes to be spawned for this node group via the text box or the "-" and "+" buttons.
  - Repeat these steps if you need nodes from additional node group templates.

6) Optionally, you can adjust your configuration further by using the "General Parameters", "HDFS Parameters" and "MapReduce Parameters" tabs.

7) Click on the "Create" button to finish creating your Cluster Template.

Launching a Cluster
-------------------

1) Navigate to the "Sahara" tab in the dashboard, then click on the "Clusters" panel.

2) Click on the "Launch Cluster" button at the top right.

3) Choose your desired Plugin name and Version from the dropdowns and click "Create".

4) Give your cluster a name. (required)

5) Choose which cluster template should be used for your cluster.

6) Choose the image that should be used for your cluster (if you do not see any options here, see `Registering an Image`_ above).

7) Optionally choose a keypair that can be used to authenticate to your cluster instances.

8) Click on the "Create" button to start your cluster.

  - Your cluster's status will display on the Clusters table.
  - It will likely take several minutes to reach the "Active" state.

Scaling a Cluster
-----------------
1) From the Sahara/Clusters page, click on the "Scale Cluster" button of the row that contains the cluster that you want to scale.

2) You can adjust the numbers of instances for existing Node Group Templates.

3) You can also add a new Node Group Template and choose a number of instances to launch.

  - This can be done by selecting your desired Node Group Template from the dropdown and clicking the "+" button.
  - Your new Node Group will appear below and you can adjust the number of instances via the text box or the +/- buttons.

4) To confirm the scaling settings and trigger the spawning/deletion of instances, click on "Scale".

Elastic Data Processing (EDP)
-----------------------------
Data Sources
------------
Data Sources are where the input and output from your jobs are housed.

1) From the Sahara/Data Sources page, click on the "Create Data Source" button at the top right.

2) Give your Data Source a name.

3) Enter the URL to the Data Source.  For a Swift object, the url will look like <container>.sahara/<path>.  The "swift://" is automatically added for you.

4) Enter the username and password for the Data Source.

5) Enter an optional description.

6) Click on "Create".

7) Repeat for additional Data Sources.

Job Binaries
------------
Job Binaries are where you define/upload the source code (mains and libraries) for your job.

1) From the Sahara/Job Binaries page, click on the "Create Job Binary" button at the top right.

2) Give your Job Binary a name (this can be different than the actual filename).

3) Choose the type of storage for your Job Binary.

  - For "Swift Internal", you will need to enter the URL of your binary (<container>.sahara/<path>) as well as the username and password.
  - For "Sahara internal database", you can choose from a pre-existing "job binary internal", "Create a script" or "Upload a new file".

4) Enter an optional description.

5) Click on "Create".

6) Repeat for additional Job Binaries

Jobs
----
Jobs are where you define the type of job you'd like to run as well as which "Job Binaries" are required.

1) From the Sahara/Jobs page, click on the "Create Job" button at the top right.

2) Give your Job a name.

3) Choose the type of job you'd like to run (Pig, Hive, Jar)

4) Choose the main binary from the dropdown.

5) Enter an optional description for your Job.

6) Optionally, click on the "Libs" tab and add one or more libraries that are required for your job.  Each library must be defined as a Job Binary.

7) Click on "Create".

Job Executions
--------------
Job Executions are what you get by "Launching" a job.  You can monitor the status of your job to see when it has completed its run.

1) From the Sahara/Jobs page, find the row that contains the job you want to launch and click on the "Launch Job" button at the right side of that row.

2) Choose the cluster (already running--see `Launching a Cluster`_ above) on which you would like the job to run.

3) Choose the Input and Output Data Sources (Data Sources defined above).

4) If additional configuration is required, click on the "Configure" tab.

  - Additional configuration properties can be defined by clicking on the "Add" button.
  - An example configuration entry might be mapred.mapper.class for the Name and org.apache.oozie.example.SampleMapper for the Value.

5) Click on "Launch".  To monitor the status of your job, you can navigate to the Sahara/Job Executions panel.

Additional Notes
----------------
1) Throughout the Sahara UI, you will find that if you try to delete an object that you will not be able to delete it if another object depends on it.
An example of this would be trying to delete a Job that has an existing Job Execution.  In order to be able to delete that job, you would first need to delete any Job Executions that relate to that job.
