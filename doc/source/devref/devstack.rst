Setup VM for DevStack on OSX
============================

In order to run Devstsack in a local VM, you need to start by installing a guest with Ubuntu 12.04 server.
Download an image file from `Ubuntu's web site <http://www.ubuntu.com/download/server>`_ and create a new guest from it.
Virtualization solution should support nested virtualization.


Install VMWare Fusion and create a new VM with Ubuntu Server 12.04.
Recommended settings:

- Processor - at least 2 cores
- Enable hypervisor applications in this virtual machine
- Memory - at least 4GB
- Hard Drive - at least 60GB

**How to set fixed IP address for your VM**

1. Open file ``/Library/Preferences/VMware Fusion/vmnet8/dhcpd.conf``
2. There is a block named "subnet". It might look like this:

.. sourcecode:: text

    subnet 192.168.55.0 netmask 255.255.255.0 {
            range 192.168.55.128 192.168.55.254;

3. You need to pick an IP address outside of that range. For example - ``192.168.55.20``
4. Copy VM MAC address from VM settings->Network->Advanced
5. Append the following block to file ``dhcpd.conf`` (don't forget to replace ``VM_HOSTNAME`` and ``VM_MAC_ADDRESS`` with actual values):

.. sourcecode:: text

    host VM_HOSTNAME {
            hardware ethernet VM_MAC_ADDRESS;
            fixed-address 192.168.55.20;
    }

6. Now quit all the VmWare Fusion applications and restart vmnet:

.. sourcecode:: console

    $ sudo /Applications/VMware\ Fusion.app/Contents/Library/vmnet-cli --stop
    $ sudo /Applications/VMware\ Fusion.app/Contents/Library/vmnet-cli --start

7. Now start your VM, it should have new fixed IP address


Install DevStack on VM
----------------------

Now we are going to install DevStack in VM we just created. So, connect to VM with secure shell and follow instructions.

1. Clone DevStack:

.. sourcecode:: console

    $ sudo apt-get install git-core
    $ git clone https://github.com/openstack-dev/devstack.git

2. Create file ``localrc`` in devstack directory with the following content:

.. sourcecode:: bash

    ADMIN_PASSWORD=nova
    MYSQL_PASSWORD=nova
    RABBIT_PASSWORD=nova
    SERVICE_PASSWORD=$ADMIN_PASSWORD
    SERVICE_TOKEN=nova

    # Enable Swift
    ENABLED_SERVICES+=,swift

    SWIFT_HASH=66a3d6b56c1f479c8b4e70ab5c2000f5
    SWIFT_REPLICAS=1
    SWIFT_DATA_DIR=$DEST/data


    # Force checkout prerequsites
    # FORCE_PREREQ=1

    # keystone is now configured by default to use PKI as the token format which produces huge tokens.
    # set UUID as keystone token format which is much shorter and easier to work with.
    KEYSTONE_TOKEN_FORMAT=UUID

    # Change the FLOATING_RANGE to whatever IPs VM is working in.
    # In NAT mode it is subnet VMWare Fusion provides, in bridged mode it is your local network.
    # But only use the top end of the network by using a /27 and starting at the 224 octet.
    FLOATING_RANGE=192.168.55.224/27

    # Enable auto assignment of floating IPs. By default Savanna expects this setting to be enabled
    EXTRA_OPTS=(auto_assign_floating_ip=True)

    # Enable logging
    SCREEN_LOGDIR=$DEST/logs/screen

    # Set ``OFFLINE`` to ``True`` to configure ``stack.sh`` to run cleanly without
    # Internet access. ``stack.sh`` must have been previously run with Internet
    # access to install prerequisites and fetch repositories.
    # OFFLINE=True

3. Start DevStack:

.. sourcecode:: console

    $ ./stack.sh

4. Once previous step is finished Devstack will print Horizon URL. Navigate to this URL and login with login "admin" and password from localrc.

5. Now we need to modify security rules. It will allow to connect to VMs directly from your host. Navigate to project's "Admin" security tab and edit default Security Group rules:

   +-------------+-----------+---------+--------------+-----------+
   | IP Protocol | From Port | To Port | Source Group | CIDR      |
   +=============+===========+=========+==============+===========+
   | TCP         | 1         | 65535   | CIDR         | 0.0.0.0/0 |
   +-------------+-----------+---------+--------------+-----------+
   | ICMP        | -1        | -1      | CIDR         | 0.0.0.0/0 |
   +-------------+-----------+---------+--------------+-----------+


6. Congratulations! You have OpenStack running in your VM and ready to launch VMs inside that VM :)
