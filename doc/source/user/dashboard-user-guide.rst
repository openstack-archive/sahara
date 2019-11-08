Sahara (Data Processing) UI User Guide
======================================

This guide assumes that you already have the sahara service and Horizon
dashboard up and running. Don't forget to make sure that sahara is
registered in Keystone. If you require assistance with that, please see the
`installation guide <../install/installation-guide.html>`_.

The sections below give a panel by panel overview of setting up clusters
and running jobs.  For a description of using the guided cluster and job tools,
look at `Launching a cluster via the Cluster Creation Guide`_ and
`Running a job via the Job Execution Guide`_.

Launching a cluster via the sahara UI
-------------------------------------
Registering an Image
--------------------

1) Navigate to the "Project" dashboard, then to the "Data Processing" tab, then
   click on the "Clusters" panel and finally the "Image Registry" tab.

2) From that page, click on the "Register Image" button at the top right

3) Choose the image that you'd like to register with sahara

4) Enter the username of the cloud-init user on the image

5) Choose plugin and version to make the image available only for the intended
   clusters

6) Click the "Done" button to finish the registration

Create Node Group Templates
---------------------------

1) Navigate to the "Project" dashboard, then to the "Data Processing" tab, then
   click on the "Clusters" panel and then the "Node Group Templates" tab.

2) From that page, click on the "Create Template" button at the top right

3) Choose your desired Plugin name and Version from the dropdowns and click
   "Next"

4) Give your Node Group Template a name (description is optional)

5) Choose a flavor for this template (based on your CPU/memory/disk needs)

6) Choose the storage location for your instance, this can be either "Ephemeral
   Drive" or "Cinder Volume".  If you choose "Cinder Volume", you will need to
   add additional configuration

7) Switch to the Node processes tab and choose which processes should be run
   for all instances that are spawned from this Node Group Template

8) Click on the "Create" button to finish creating your Node Group Template

Create a Cluster Template
-------------------------

1) Navigate to the "Project" dashboard, then to the "Data Processing" tab, then
   click on the "Clusters" panel and finally the "Cluster Templates" tab.

2) From that page, click on the "Create Template" button at the top right

3) Choose your desired Plugin name and Version from the dropdowns and click
   "Next"

4) Under the "Details" tab, you must give your template a name

5) Under the "Node Groups" tab, you should add one or more nodes that can be
   based on one or more templates

- To do this, start by choosing a Node Group Template from the dropdown and
  click the "+" button
- You can adjust the number of nodes to be spawned for this node group via
  the text box or the "-" and "+" buttons
- Repeat these steps if you need nodes from additional node group templates

6) Optionally, you can adjust your configuration further by using the "General
   Parameters", "HDFS Parameters" and "MapReduce Parameters" tabs

7) If you have Designate DNS service you can choose the domain name in "DNS"
   tab for internal and external hostname resolution

8) Click on the "Create" button to finish creating your Cluster Template

Launching a Cluster
-------------------

1) Navigate to the "Project" dashboard, then to the "Data Processing" tab, then
   click on the "Clusters" panel and lastly, click on the "Clusters" tab.

2) Click on the "Launch Cluster" button at the top right

3) Choose your desired Plugin name and Version from the dropdowns and click
   "Next"

4) Give your cluster a name (required)

5) Choose which cluster template should be used for your cluster

6) Choose the image that should be used for your cluster (if you do not see any
   options here, see `Registering an Image`_ above)

7) Optionally choose a keypair that can be used to authenticate to your cluster
   instances

8) Click on the "Create" button to start your cluster

- Your cluster's status will display on the Clusters table
- It will likely take several minutes to reach the "Active" state

Scaling a Cluster
-----------------
1) From the Data Processing/Clusters page (Clusters tab), click on the
   "Scale Cluster" button of the row that contains the cluster that you want to
   scale

2) You can adjust the numbers of instances for existing Node Group Templates

3) You can also add a new Node Group Template and choose a number of instances
   to launch

- This can be done by selecting your desired Node Group Template from the
  dropdown and clicking the "+" button
- Your new Node Group will appear below and you can adjust the number of
  instances via the text box or the "+" and "-" buttons

4) To confirm the scaling settings and trigger the spawning/deletion of
   instances, click on "Scale"

Elastic Data Processing (EDP)
-----------------------------
Data Sources
------------
Data Sources are where the input and output from your jobs are housed.

1) From the Data Processing/Jobs page (Data Sources tab), click on the
   "Create Data Source" button at the top right

2) Give your Data Source a name

3) Enter the URL of the Data Source

- For a swift object, enter <container>/<path> (ie: *mycontainer/inputfile*).
  sahara will prepend *swift://* for you
- For an HDFS object, enter an absolute path, a relative path or a full URL:

  + */my/absolute/path* indicates an absolute path in the cluster HDFS
  + *my/path* indicates the path */user/hadoop/my/path* in the cluster HDFS
    assuming the defined HDFS user is *hadoop*
  + *hdfs://host:port/path* can be used to indicate any HDFS location

4) Enter the username and password for the Data Source (also see
   `Additional Notes`_)

5) Enter an optional description

6) Click on "Create"

7) Repeat for additional Data Sources

Job Binaries
------------
Job Binaries are where you define/upload the source code (mains and libraries)
for your job.

1) From the Data Processing/Jobs (Job Binaries tab), click on the
   "Create Job Binary" button at the top right

2) Give your Job Binary a name (this can be different than the actual filename)

3) Choose the type of storage for your Job Binary

- For "swift", enter the URL of your binary (<container>/<path>) as well as
  the username and password (also see `Additional Notes`_)
- For "manila", choose the share and enter the path for the binary in this
  share. This assumes that you have already stored that file in the
  appropriate path on the share. The share will be automatically mounted to
  any cluster nodes which require access to the file, if it is not mounted
  already.
- For "Internal database", you can choose from "Create a script" or "Upload
  a new file" (**only API v1.1**)

4) Enter an optional description

5) Click on "Create"

6) Repeat for additional Job Binaries

Job Templates (Known as "Jobs" in the API)
------------------------------------------
Job templates are where you define the type of job you'd like to run as well
as which "Job Binaries" are required.

1) From the Data Processing/Jobs page (Job Templates tab),
   click on the "Create Job Template" button at the top right

2) Give your Job Template a name

3) Choose the type of job you'd like to run

4) Choose the main binary from the dropdown

   - This is required for Hive, Pig, and Spark jobs
   - Other job types do not use a main binary

5) Enter an optional description for your Job Template

6) Click on the "Libs" tab and choose any libraries needed by your job template

   - MapReduce and Java jobs require at least one library
   - Other job types may optionally use libraries

7) Click on "Create"

Jobs (Known as "Job Executions" in the API)
-------------------------------------------
Jobs are what you get by "Launching" a job template.  You can monitor the
status of your job to see when it has completed its run

1) From the Data Processing/Jobs page (Job Templates tab), find the row
   that contains the job template you  want to launch and click either
   "Launch on New Cluster" or "Launch on Existing Cluster" the right side
   of that row

2) Choose the cluster (already running--see `Launching a Cluster`_ above) on
   which you would like the job to run

3) Choose the Input and Output Data Sources (Data Sources defined above)

4) If additional configuration is required, click on the "Configure" tab

- Additional configuration properties can be defined by clicking on the "Add"
  button
- An example configuration entry might be mapred.mapper.class for the Name
  and org.apache.oozie.example.SampleMapper for the Value

5) Click on "Launch".  To monitor the status of your job, you can navigate to
   the Data Processing/Jobs panel and click on the Jobs tab.

6) You can relaunch a Job from the Jobs page by using the
   "Relaunch on New Cluster" or "Relaunch on Existing Cluster" links

- Relaunch on New Cluster will take you through the forms to start a new
  cluster before letting you specify input/output Data Sources and job
  configuration
- Relaunch on Existing Cluster will prompt you for input/output Data Sources
  as well as allow you to change job configuration before launching the job

Example Jobs
------------
There are sample jobs located in the sahara repository. In this section, we
will give a walkthrough on how to run those jobs via the Horizon UI. These
steps assume that you already have a cluster up and running (in the "Active"
state).  You may want to clone into https://opendev.org/openstack/sahara-tests/
so that you will have all of the source code and inputs stored locally.

1) Sample Pig job -
   https://opendev.org/openstack/sahara-tests/src/branch/master/sahara_tests/scenario/defaults/edp-examples/edp-pig/cleanup-string/example.pig

- Load the input data file from
  https://opendev.org/openstack/sahara-tests/src/branch/master/sahara_tests/scenario/defaults/edp-examples/edp-pig/cleanup-string/data/input
  into swift

  - Click on Project/Object Store/Containers and create a container with any
    name ("samplecontainer" for our purposes here)

  - Click on Upload Object and give the object a name
    ("piginput" in this case)

- Navigate to Data Processing/Jobs/Data Sources, Click on Create Data Source

  - Name your Data Source ("pig-input-ds" in this sample)

  - Type = Swift, URL samplecontainer/piginput, fill-in the Source
    username/password fields with your username/password and click "Create"

- Create another Data Source to use as output for the job

  - Name = pig-output-ds, Type = Swift, URL = samplecontainer/pigoutput,
    Source username/password, "Create"

- Store your Job Binaries in Swift (you can choose another type of storage
  if you want)

  - Navigate to Project/Object Store/Containers, choose "samplecontainer"

  - Click on Upload Object and find example.pig at
    <sahara-tests root>/sahara-tests/scenario/defaults/edp-examples/
    edp-pig/cleanup-string/, name it "example.pig" (or other name).
    The Swift path will be swift://samplecontainer/example.pig

  - Click on Upload Object and find edp-pig-udf-stringcleaner.jar at
    <sahara-tests root>/sahara-tests/scenario/defaults/edp-examples/
    edp-pig/cleanup-string/, name it "edp-pig-udf-stringcleaner.jar"
    (or other name). The Swift path will be
    swift://samplecontainer/edp-pig-udf-stringcleaner.jar

  - Navigate to Data Processing/Jobs/Job Binaries, Click on Create Job Binary

  - Name = example.pig, Storage type = Swift,
    URL = samplecontainer/example.pig, Username = <your username>,
    Password = <your password>

  - Create another Job Binary:  Name = edp-pig-udf-stringcleaner.jar,
    Storage type = Swift,
    URL = samplecontainer/edp-pig-udf-stringcleaner.jar,
    Username = <your username>, Password = <your password>

- Create a Job Template

  - Navigate to Data Processing/Jobs/Job Templates, Click on
    Create Job Template

  - Name = pigsample, Job Type = Pig, Choose "example.pig" as the main binary

  - Click on the "Libs" tab and choose "edp-pig-udf-stringcleaner.jar",
    then hit the "Choose" button beneath the dropdown, then click
    on "Create"

- Launch your job

  - To launch your job from the Job Templates page, click on the down
    arrow at the far right of the screen and choose
    "Launch on Existing Cluster"

  - For the input, choose "pig-input-ds", for output choose "pig-output-ds".
    Also choose whichever cluster you'd like to run the job on

  - For this job, no additional configuration is necessary, so you can just
    click on "Launch"

  - You will be taken to the "Jobs" page where you can see your job
    progress through "PENDING, RUNNING, SUCCEEDED" phases

  - When your job finishes with "SUCCEEDED", you can navigate back to Object
    Store/Containers and browse to the samplecontainer to see your output.
    It should be in the "pigoutput" folder

2) Sample Spark job -
   https://opendev.org/openstack/sahara-tests/src/branch/master/sahara_tests/scenario/defaults/edp-examples/edp-spark
   You can clone into https://opendev.org/openstack/sahara-tests/ for quicker
   access to the files for this sample job.

- Store the Job Binary in Swift (you can choose another type of storage if
  you want)

  - Click on Project/Object Store/Containers and create a container with any
    name ("samplecontainer" for our purposes here)

  - Click on Upload Object and find spark-wordcount.jar at
    <sahara-tests root>/sahara-tests/scenario/defaults/edp-examples/
    edp-spark/, name it "spark-wordcount.jar" (or other name).
    The Swift path will be swift://samplecontainer/spark-wordcount.jar

  - Navigate to Data Processing/Jobs/Job Binaries, Click on Create Job Binary

  - Name = sparkexample.jar, Storage type = Swift,
    URL = samplecontainer/spark-wordcount.jar, Username = <your username>,
    Password = <your password>

- Create a Job Template

  - Name = sparkexamplejob, Job Type = Spark,
    Main binary = Choose sparkexample.jar, Click "Create"

- Launch your job

  - To launch your job from the Job Templates page, click on the
    down arrow at the far right of the screen and choose
    "Launch on Existing Cluster"

  - Choose whichever cluster you'd like to run the job on

  - Click on the "Configure" tab

  - Set the main class to be:  sahara.edp.spark.SparkWordCount

  - Under Arguments, click Add and fill url for the input file,
    once more click Add and fill url for the output file.

  - Click on Launch

  - You will be taken to the "Jobs" page where you can see your job
    progress through "PENDING, RUNNING, SUCCEEDED" phases

  - When your job finishes with "SUCCEEDED", you can see your results in
    your output file.

  - The stdout and stderr files of the command used for executing your job
    are located at  /tmp/spark-edp/<name of job template>/<job id>
    on Spark master node in case of Spark clusters, or on Spark JobHistory
    node in other cases like Vanilla, CDH and so on.


Additional Notes
----------------
1) Throughout the sahara UI, you will find that if you try to delete an object
   that you will not be able to delete it if another object depends on it.
   An example of this would be trying to delete a Job Template that has an
   existing Job.  In order to be able to delete that job, you would
   first need to delete any Job Templates that relate to that job.

2) In the examples above, we mention adding your username/password for the
   swift Data Sources. It should be noted that it is possible to configure
   sahara such that the username/password credentials are *not* required. For
   more information on that, please refer to: :doc:`Sahara Advanced
   Configuration Guide <../admin/advanced-configuration-guide>`

Launching a cluster via the Cluster Creation Guide
--------------------------------------------------
1) Under the Data Processing group, choose "Clusters" and then click on the
   "Clusters" tab.  The "Cluster Creation Guide" button is above that table.
   Click on it.

2) Click on the "Choose Plugin" button then select the cluster type from the
   Plugin Name dropdown and choose your target version. When done, click
   on "Select" to proceed.

3) Click on "Create a Master Node Group Template".  Give your template a name,
   choose a flavor and choose which processes should run on nodes launched
   for this node group.  The processes chosen here should be things that are
   more server-like in nature (namenode, oozieserver, spark master, etc).
   Optionally, you can set other options here such as availability zone,
   storage, security and process specific parameters.  Click on "Create"
   to proceed.

4) Click on "Create a Worker Node Group Template".  Give your template a name,
   choose a flavor and choose which processes should run on nodes launched
   for this node group.  Processes chosen here should be more worker-like in
   nature (datanode, spark slave, task tracker, etc).  Optionally, you can set
   other options here such as availability zone, storage, security and process
   specific parameters.  Click on "Create" to proceed.

5) Click on "Create a Cluster Template".  Give your template a name.  Next,
   click on the "Node Groups" tab and enter the count for each of the node
   groups (these are pre-populated from steps 3 and 4).  It would be common
   to have 1 for the "master" node group type and some larger number of
   "worker" instances depending on you desired cluster size.  Optionally,
   you can also set additional parameters for cluster-wide settings via
   the other tabs on this page.  Click on "Create" to proceed.

6) Click on "Launch a Cluster".  Give your cluster a name and choose the image
   that you want to use for all instances in your cluster.  The cluster
   template that you created in step 5 is already pre-populated.  If you want
   ssh access to the instances of your cluster, select a keypair from the
   dropdown.  Click on "Launch" to proceed.  You will be taken to the Clusters
   panel where you can see your cluster progress toward the Active state.

Running a job via the Job Execution Guide
-----------------------------------------
1) Under the Data Processing group, choose "Jobs" and then click on the
   "Jobs" tab.  The "Job Execution Guide" button is above that table. Click
   on it.

2) Click on "Select type" and choose the type of job that you want to run.

3) If your job requires input/output data sources, you will have the option
   to create them via the "Create a Data Source" button (Note: This button will
   not be shown for job types that do not require data sources).  Give your
   data source a name and choose the type.  If you have chosen swift, you
   may also enter the username and password.  Enter the URL for your data
   source.  For more details on what the URL should look like, see
   `Data Sources`_.

4) Click on "Create a job template".  Give your job template a name.
   Depending on the type of job that you've chosen, you may need to select
   your main binary and/or additional libraries (available from the "Libs"
   tab).  If you have not yet uploaded the files to run your program, you
   can add them via the "+" icon next to the "Choose a main binary" select box.

5) Click on "Launch job".  Choose the active cluster where you want to run you
   job.  Optionally, you can click on the "Configure" tab and provide any
   required configuration, arguments or parameters for your job.  Click on
   "Launch" to execute your job.  You will be taken to the Jobs tab where
   you can monitor the state of your job as it progresses.
