Architecture
============

.. image:: images/sahara-architecture.png
    :width: 800 px
    :scale: 99 %
    :align: left


The Sahara architecture consists of several components:

* Cluster Configuration Manager  - all the business logic resides here

* Auth component - responsible for client authentication & authorization

* DAL - Data Access Layer, persists internal models in DB

* VM Provisioning - component responsible for communication with Nova and Glance

* Deployment Engine - pluggable mechanism responsible for deploying Hadoop on provisioned VMs;
  existing management solutions like Apache Ambari and Cloudera Management Console could be utilized for that matter

* REST API - exposes Sahara functionality via REST

* Python Sahara Client - similar to other OpenStack components Sahara has its own python client

* Sahara pages - GUI for the Sahara is located on Horizon
