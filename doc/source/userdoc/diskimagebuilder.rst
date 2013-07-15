Disk Image Builder
==================

As of now vanilla plugin works with images with pre-installed Apache Hadoop. To
simplify task of building such images we use
`Disk Image Builder <https://github.com/stackforge/diskimage-builder>`_.

`Disk Image Builder` is built of elements. An element is a particular set of
code that alters how the image is built, or runs within the chroot to prepare
the image.

Elements for building vanilla images are stored in `Savanna extra repository <https://github.com/stackforge/savanna-extra>`_


.. note::

   Savanna requires images with cloud-init package installed:

   * `For Fedora <http://pkgs.fedoraproject.org/cgit/cloud-init.git/>`_
   * `For Ubuntu <http://packages.ubuntu.com/precise/cloud-init>`_

In this document you will find instruction on how to build Ubuntu and Fedora
images with Apache Hadoop 1.1.2.

1. Clone repositories

    1.1 Clone the repository "https://github.com/stackforge/diskimage-builder" locally.

    .. sourcecode:: console

        git clone https://github.com/stackforge/diskimage-builder

    We've tested it with commit: ``7e0fe78cf227b0cca8e40d20c884c385bbb2b3c5``.

    1.2 Clone the repository "https://github.com/stackforge/savanna-extra" locally.

    .. sourcecode:: console

        git clone https://github.com/stackforge/savanna-extra
        git checkout 0.2

    1.3 You will need Oracle JDK 7 downloaded.

    The latest version is available at `Oracle Java page <http://www.oracle.com/technetwork/java/javase/downloads/index.html>`_

    Move the downloaded JDK to ``elements/hadoop/install.d/`` for an Ubuntu image
    or to ``elements/hadoop_fedora/post-install.d/`` for a Fedora
    and use its filename as ``JAVA_FILE`` parameter.

2. Install prerequisites

    Disk Image Builder requires some libs to be installed.
        * curl
        * kpartx
        * qemu

You may install them using your favorite package manager (ex. apt-get or yum)

    .. sourcecode:: console

        sudo apt-get install curl kpartx qemu

3. Add ``~/diskimage-builder/bin/`` directory to your path. For example:

   .. sourcecode:: bash

       PATH=$PATH:/home/$USER/diskimage-builder/bin/.

4. Export the following variable
    ``ELEMENTS_PATH=/home/$USER/diskimage-builder/elements/``
    to your ``.bashrc``. Then source it.

5. Copy file ``img-build-sudoers`` from ``~/disk-image-builder/sudoers.d/``
   to your ``/etc/sudoers.d/``:

   .. sourcecode:: bash

       sudo cp ~/disk-image-builder/sudoers.d/img-build-sudoers /etc/sudoers.d/
       sudo chown root:root /etc/sudoers.d/img-build-sudoers
       sudo chmod 440 /etc/sudoers.d/img-build-sudoers

6. Move ``elements`` directory to ``disk-image-builder/elements/``

   .. sourcecode:: console

    mv <path_to_savanna_extra>/savanna-extra/elements/*  <path_to_disk_image_builder>/diskimage-builder/elements/

7. Call the following command to create cloud image with Apache Hadoop:

   **Ubuntu cloud image**

   .. sourcecode:: console

       DIB_HADOOP_VERSION=1.1.2 JAVA_FILE=jdk-7u25-linux-x64.tar.gz \
           disk-image-create base vm hadoop ubuntu swift_hadoop -o hadoop_1_1_2

   **Fedora cloud image**

   .. sourcecode:: console

        DIB_HADOOP_VERSION=1.1.2 JAVA_FILE=jdk-7u25-linux-x64.tar.gz \
         DIB_IMAGE_SIZE=10 disk-image-create base vm fedora hadoop_fedora \
         swift_hadoop -o fedora_hadoop_1_1_2

   In this command:

   * ``DIB_HADOOP_VERSION`` - version of Hadoop to install (currently supports
     only Apache Hadoop 1.1.2)
   * ``JAVA_DOWNLOAD_URL`` - you also can use this parameter instead of
     ``JAVA_FILE`` to specify download link for JDK (tarball or bin)
   * ``DIB_IMAGE_SIZE`` - is parameter that specifies a volume of hard disk of
     instance. You need to specify it because Fedora doesn't use all available
     volume.
