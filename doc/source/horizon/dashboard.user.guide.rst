Sahara (Data Processing) UI User Guide
======================================

This guide assumes that you already have Sahara service and the Horizon dashboard up and running.
Don't forget to make sure that Sahara is registered in Keystone.
If you require assistance with that, please see the `installation guide <../installation.guide.html>`_.

Launching a cluster via the Sahara UI
-------------------------------------
Registering an Image
--------------------

1) Navigate to the "Project" dashboard, then the "Data Processing" tab, then click on the "Image Registry" panel.

2) From that page, click on the "Register Image" button at the top right.

3) Choose the image that you'd like to register as a Hadoop Image

4) Enter the username of the cloud-init user on the image.

5) Click on the tags that you want to add to the image. (A version ie: 1.2.1 and a type ie: vanilla are required for cluster functionality)

6) Click the "Done" button to finish the registration.

Create Node Group Templates
---------------------------

1) Navigate to the "Project" dashboard, then the "Data Processing" tab, then click on the "Node Group Templates" panel.

2) From that page, click on the "Create Template" button at the top right.

3) Choose your desired Plugin name and Version from the dropdowns and click "Create".

4) Give your Node Group Template a name (description is optional)

5) Choose a flavor for this template (based on your CPU/memory/disk needs)

6) Choose the storage location for your instance, this can be either "Ephemeral Drive" or "Cinder Volume".  If you choose "Cinder Volume", you will need to add additional configuration.

7) Choose which processes should be run for any instances that are spawned from this Node Group Template.

8) Click on the "Create" button to finish creating your Node Group Template.

Create a Cluster Template
-------------------------

1) Navigate to the "Project" dashboard, then the "Data Processing" tab, then click on the "Cluster Templates" panel.

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

1) Navigate to the "Project" dashboard, then the "Data Processing" tab, then click on the "Clusters" panel.

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
1) From the Data Processing/Clusters page, click on the "Scale Cluster" button of the row that contains the cluster that you want to scale.

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

1) From the Data Processing/Data Sources page, click on the "Create Data Source" button at the top right.

2) Give your Data Source a name.

3) Enter the URL to the Data Source.

  - For a Swift object, the url will look like <container>.sahara/<path> (ie: mycontainer.sahara/inputfile).  The "swift://" is automatically added for you.
  - For an HDFS object, the url will look like <host>/<path> (ie: myhost/user/hadoop/inputfile).  The "hdfs://" is automatically added for you.

4) Enter the username and password for the Data Source.

5) Enter an optional description.

6) Click on "Create".

7) Repeat for additional Data Sources.

Job Binaries
------------
Job Binaries are where you define/upload the source code (mains and libraries) for your job.

1) From the Data Processing/Job Binaries page, click on the "Create Job Binary" button at the top right.

2) Give your Job Binary a name (this can be different than the actual filename).

3) Choose the type of storage for your Job Binary.

  - For "Swift", you will need to enter the URL of your binary (<container>.sahara/<path>) as well as the username and password.
  - For "Internal database", you can choose from "Create a script" or "Upload a new file".

4) Enter an optional description.

5) Click on "Create".

6) Repeat for additional Job Binaries

Jobs
----
Jobs are where you define the type of job you'd like to run as well as which "Job Binaries" are required.

1) From the Data Processing/Jobs page, click on the "Create Job" button at the top right.

2) Give your Job a name.

3) Choose the type of job you'd like to run (Pig, Hive, MapReduce, Streaming MapReduce, Java Action)

4) Choose the main binary from the dropdown (not applicable for MapReduce or Java Action).

5) Enter an optional description for your Job.

6) Optionally, click on the "Libs" tab and add one or more libraries that are required for your job.  Each library must be defined as a Job Binary.

7) Click on "Create".

Job Executions
--------------
Job Executions are what you get by "Launching" a job.  You can monitor the status of your job to see when it has completed its run.

1) From the Data Processing/Jobs page, find the row that contains the job you want to launch and click on the "Launch Job" button at the right side of that row.

2) Choose the cluster (already running--see `Launching a Cluster`_ above) on which you would like the job to run.

3) Choose the Input and Output Data Sources (Data Sources defined above).

4) If additional configuration is required, click on the "Configure" tab.

  - Additional configuration properties can be defined by clicking on the "Add" button.
  - An example configuration entry might be mapred.mapper.class for the Name and org.apache.oozie.example.SampleMapper for the Value.

5) Click on "Launch".  To monitor the status of your job, you can navigate to the Sahara/Job Executions panel.

6) You can relaunch a Job Execution from the Job Executions page by using the "Relaunch on New Cluster" or "Relaunch on Existing Cluster" links.

  - Relaunch on New Cluster will take you through the forms to start a new cluster before letting you specify input/output Data Sources and job configuration.
  - Relaunch on Existing Cluster will prompt you for input/output Data Sources as well as allow you to change job configuration before launching the job.

Example Jobs
------------
There are sample jobs located in the sahara repository.  The instructions there guide you through running the jobs via the command line.
In this section, we will give a walkthrough on how to run those jobs via the Horizon UI.
These steps assume that you already have a cluster up and running (in the "Active" state).

1) Sample Pig job - https://github.com/openstack/sahara/tree/master/etc/edp-examples/pig-job

  - Load the input data file from https://github.com/openstack/sahara/tree/master/etc/edp-examples/pig-job/data/input into swift

    - Click on Projet/Object Store/Containers and create a container with any name ("samplecontainer" for our purposes here).

    - Click on Upload Object and give the object a name ("piginput" in this case)

    - Navigate to Data Processing/Data Sources, Click on Create Data Source.

    - Name your Data Source ("pig-input-ds" in this sample)

    - Type = Swift, URL samplecontainer.sahara/piginput, fill-in the Source username/password fields with your username/password and click "Create"

  - Create another Data Source to use as output for the job

    - Create another Data Source to use as output for our job.  Name = pig-output-ds, Type = Swift, URL = samplecontainer.sahara/pigoutput, Source username/password, "Create"

  - Store your Job Binaries in the Sahara database

    - Navigate to Data Processing/Job Binaries, Click on Create Job Binary

    - Name = example.pig, Storage type = Internal database, click Browse and find example.pig wherever you checked out the sahara project <sahara root>/etc/edp-examples/pig-job

    - Create another Job Binary:  Name = udf.jar, Storage type = Internal database, click Browse and find udf.jar wherever you checked out the sahara project <sahara root>/etc/edp-examples/pig-job

  - Create a Job

    - Navigate to Data Processing/Jobs, Click on Create Job

    - Name = pigsample, Job Type = Pig, Choose "example.pig" as the main binary

    - Click on the "Libs" tab and choose "udf.jar", then hit the "Choose" button beneath the dropdown, then click on "Create"

  - Launch your job

    - To launch your job from the Jobs page, click on the down arrow at the far right of the screen and choose "Launch on Existing Cluster"

    - For the input, choose "pig-input-ds", for output choose "pig-output-ds".  Also choose whichever cluster you'd like to run the job on.

    - For this job, no additional configuration is necessary, so you can just click on "Launch"

    - You will be taken to the "Job Executions" page where you can see your job progress through "PENDING, RUNNING, SUCCEEDED" phases

    - When your job finishes with "SUCCEEDED", you can navigate back to Object Store/Containers and browse to the samplecontainer to see your output.  It should be in the "pigoutput" folder.

2) Sample Spark job - https://github.com/openstack/sahara/tree/master/etc/edp-examples/edp-spark

  - Store the Job Binary in the Sahara database

    - Navigate to Data Processing/Job Binaries, Click on Create Job Binary

    - Name = sparkexample.jar, Storage type = Internal database, Browse to the location <sahara root>/etc/edp-examples/edp-spark and choose spark-example.jar, Click "Create"

  - Create a Job

    - Name = sparkexamplejob, Job Type = Spark, Main binary = Choose sparkexample.jar, Click "Create"

  - Launch your job

    - To launch your job from the Jobs page, click on the down arrow at the far right of the screen and choose "Launch on Existing Cluster"

    - Choose whichever cluster you'd like to run the job on.

    - Click on the "Configure" tab

    - Set the main class to be:  org.apache.spark.examples.SparkPi

    - Under Arguments, click Add and fill in the number of "Slices" you want to use for the job.  For this example, let's use 100 as the value

    - Click on Launch

    - You will be taken to the "Job Executions" page where you can see your job progress through "PENDING, RUNNING, SUCCEEDED" phases

    - When your job finishes with "SUCCEEDED", you can see your results by sshing to the Spark "master" node.

    - The output is located at /tmp/spark-edp/<name of job>/<job execution id>.  You can do ``cat stdout`` which should display something like "Pi is roughly 3.14156132"

    - It should be noted that for more complex jobs, the input/output may be elsewhere.  This particular job just writes to stdout, which is logged in the folder under /tmp.

Additional Notes
----------------
1) Throughout the Sahara UI, you will find that if you try to delete an object that you will not be able to delete it if another object depends on it.
An example of this would be trying to delete a Job that has an existing Job Execution.  In order to be able to delete that job, you would first need to delete any Job Executions that relate to that job.

2) In the examples above, we mention adding your username/password for the Swift Data Sources.
It should be noted that it is possible to configure Sahara such that the username/password credentials are *not* required.
For more information on that, please refer to: :doc:`Sahara Advanced Configuration Guide <../userdoc/advanced.configuration.guide>`
