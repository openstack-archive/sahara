Savanna Architecture (draft)
============================

.. image:: images/savanna-architecture.png
    :width: 800 px
    :scale: 99 %
    :align: left


The Savanna architecture consists of several components:

* Cluster Configuration Manager  - all the business logic resides here

* Auth component - responsible for client authentication & authorization

* DAL - Data Access Layer, persists internal models in DB

* VM Provisioning - component responsible for communication with Nova and Glance

* Deployment Engine - pluggable mechanism responsible for deploying Hadoop on provisioned VMs;
  existing management solutions like Apache Ambari and Cloudera Management Console could be utilized for that matter

* REST API - exposes Savanna functionality via REST

* Python Savanna Client - similar to other OpenStack components Savanna has its own python client

* Savanna pages - GUI for the Savanna is located on Horizon
