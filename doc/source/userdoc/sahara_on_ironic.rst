How do run a Sahara cluster on bare metal servers
=================================================

Hadoop clusters are designed to store and analyze extremely large amounts
of unstructured data in distributed computing environments. Sahara enables
you to boot Hadoop clusters in both virtual and bare metal environments.
When Booting Hadoop clusters with Sahara on bare metal servers, you benefit
from the bare metal performance with self-service resource provisioning.


1. Create a new OpenStack environment using Devstack as described
   in the `Devstack Guide <http://docs.openstack.org/developer/devstack/>`_

2. Install Ironic as described in the `Ironic Installation Guide
   <http://docs.openstack.org/developer/ironic/deploy/install-guide.html>`_

3. Install Sahara as described in the `Sahara Installation Guide
   <http://docs.openstack.org/developer/sahara/userdoc/installation.guide.html>`_

4. Build the Sahara image and prepare it for uploading to Glance:

   - Build an image for Sahara plugin with the ``-b`` flag. Use sahara image elements
     when building the image. See `<https://github.com/openstack/sahara-image-elements>`_

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
     the servers power and network. For example:

.. code-block:: bash

   $ ironic node-create -d pxe_ipmitool \
   $ -i ipmi_address=$IP_ADDRESS \
   $ -i ipmi_username=$USERNAME \
   $ -i ipmi_password=$PASSWORD \
   $ -i pxe_deploy_kernel=$deploy.kernel.id \
   $ -i pxe_deploy_ramdisk=$deploy.ramfs.id

   $ ironic port-create -n $NODE_ID -a "$MAC_eth1"
..

   - Add the hardware information:

.. code-block:: bash

   $ ironic node-update $NODE_ID add properties/cpus=$CPU \
   $ properties/memory_mb=$RAM properties/local_gb=$ROOT_GB \
   $ properties/cpu_arch='x86_64'
..

7. Add a special flavor for the bare metal instances with an arch meta
   parameter to match the virtual architecture of the server’s CPU
   with the metal one. For example:

.. code-block:: bash

   $ nova flavor-create baremetal auto $RAM $DISK_GB $CPU
   $ nova flavor-key baremetal set cpu_arch=x86_64
..

Note:
+++++
The vCPU ad vRAM parameters (x86_64 in the example) will not be applied because
the operating system has access to the real CPU cores and RAM. Only the root
disk parameter is applied, and Ironic will resize the root disk partition.
Ironic supports only a flat network topology for the bare metal provisioning,
you must use Neutron to configure it.

8. Launch your Sahara cluster on Ironic from the cluster template:

   * Log in to Horizon.

   * Go to Data Processing > Node Group Templates.
       * Find the templates that belong to the plugin you would like to use
       * Update those templates to use ‘bare metal’ flavor instead of the
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
==================

* Security groups are not applied.
* When booting a nova instance with a bare metal flavor, the user can not
  provide a pre-created neutron port to ``nova boot`` command. `LP1544195
  <https://bugs.launchpad.net/nova/+bug/1544195>`_
* Nodes are not isolated by tenants.
* VM to Bare Metal network routing is not allowed.
* The user has to specify the count of ironic nodes before Devstack deploys
  an Openstack.
* The user cannot use the same image for several ironic node types.
  For example, if there are 3 ironic node types, the user has to create
  3 images and 3 flavors.
* Multiple interfaces on a single node are not supported. Devstack configures
  only one interface.

