How to run a Sahara cluster on bare metal servers
=================================================

Hadoop clusters are designed to store and analyze extremely large amounts
of unstructured data in distributed computing environments. Sahara enables
you to boot Hadoop clusters in both virtual and bare metal environments.
When Booting Hadoop clusters with Sahara on bare metal servers, you benefit
from the bare metal performance with self-service resource provisioning.


1. Create a new OpenStack environment using Devstack as described
   in the :devstack-doc:`Devstack Guide <>`

2. Install Ironic as described in the :ironic-doc:`Ironic Installation Guide
   <install/>`

3. Install Sahara as described in the `Sahara Installation Guide
   <../install/installation-guide.html>`_

4. Build the Sahara image and prepare it for uploading to Glance:

   - Build an image for Sahara plugin which supports baremetal deployment.
     Refer to the :ref:`building-baremetal-images-label` section.

   - Convert the qcow2 image format to the raw format. For example:

.. sourcecode:: console

   $ qemu-img convert -O raw image-converted.qcow image-converted-from-qcow2.raw
..

- Mount the raw image to the system.
- ``chroot`` to the mounted directory and remove the installed grub.
- Build grub2 from sources and install to ``/usr/sbin``.
- In ``/etc/sysconfig/selinux``, disable selinux ``SELINUX=disabled``
- In the configuration file, set ``onboot=yes`` and ``BOOTPROTO=dhcp``
  for every interface.
- Add the configuration files for all interfaces in the
  ``/etc/sysconfig/network-scripts`` directory.

5. Upload the Sahara disk image to Glance, and register it in the
   Sahara Image Registry. Referencing its separate kernel and initramfs images.

6. Configure the bare metal network for the Sahara cluster nodes:

- Add bare metal servers to your environment manually referencing their
  IPMI addresses (Ironic does not detect servers), for Ironic to manage
  the servers power and network. Also, configure the scheduling
  information and add the required flavors. Please check the
  :ironic-doc:`Enrollment section of the Ironic installation guide
  <install/enrollment.html>`.


7. Launch your Sahara cluster on Ironic from the cluster template:

   * Log in to Horizon.

   * Go to Data Processing > Node Group Templates.
       * Find the templates that belong to the plugin you would like to use
       * Update those templates to use 'bare metal' flavor instead of the
         default one

   * Go to Data Processing > Cluster Templates.

   * Click Launch Cluster.

   * On the Launch Cluster dialog:
       * Specify the bare metal network for cluster nodes

The cluster provisioning time is slower compared to the cluster provisioning
of the same size that runs on VMs. Ironic does real hardware reports which
is time consuming, and the whole root disk is filled from ``/dev/zero`` for
security reasons.

Known limitations:
------------------

* Security groups are not applied.
* Nodes are not isolated by projects.
* VM to Bare Metal network routing is not allowed.
* The user has to specify the count of ironic nodes before Devstack deploys
  an OpenStack.
* The user cannot use the same image for several ironic node types.
  For example, if there are 3 ironic node types, the user has to create
  3 images and 3 flavors.
* Multiple interfaces on a single node are not supported. Devstack configures
  only one interface.

