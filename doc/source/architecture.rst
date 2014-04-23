Architecture
============

.. image:: images/sahara-architecture.png
    :width: 800 px
    :scale: 99 %
    :align: left


The Sahara architecture consists of several components:

* Auth component - responsible for client authentication & authorization, communicates with Keystone

* DAL - Data Access Layer, persists internal models in DB

* Provisioning Engine - component responsible for communication with Nova, Heat, Cinder and Glance

* Vendor Plugins - pluggable mechanism responsible for configuring and launching Hadoop on provisioned VMs;
  existing management solutions like Apache Ambari and Cloudera Management Console could be utilized for that matter

* EDP - :doc:`../userdoc/edp` responsible for scheduling and managing Hadoop jobs on clusters provisioned by Sahara

* REST API - exposes Sahara functionality via REST

* Python Sahara Client - similar to other OpenStack components Sahara has its own python client

* Sahara pages - GUI for the Sahara is located on Horizon
