Image Generation
================

As of Newton, Sahara supports the creation of image generation and image
validation tooling as part of the plugin. If implemented properly, this
feature will enable your plugin to:

* Validate that images passed to it for use in cluster provisioning meet its
  specifications.
* Provision images from "clean" (OS-only) images.
* Pack pre-populated images for registration in Glance and use by Sahara.

All of these features can use the same image declaration, meaning that logic
for these three use cases can be maintained in one place.

This guide will explain how to enable this feature for your plugin, as well as
how to write or modify the image generation manifests that this feature uses.


Image Generation CLI
--------------------

The key user-facing interface to this feature is the CLI script
``sahara-image-pack``. This script will be installed with all other Sahara
binaries.

The usage of the CLI script ``sahara-image-pack`` is documented in
the :ref:`sahara-image-pack-label` section of the user guide.


The Image Manifest
------------------

As you'll read in the next section, Sahara's image packing tools allow plugin
authors to use any toolchain they choose. However, Sahara does provide a
built-in image packing framework which is uniquely suited to OpenStack use
cases, as it is designed to run the same logic while pre-packing an image or
while preparing an instance to launch a cluster after it is spawned in
OpenStack.

By convention, the image specification, and all the scripts that it calls,
should be located in the plugin's resources directory under a subdirectory
named "images".

A sample specification is below; the example is reasonably silly in practice,
and is only designed to highlight the use of the currently available
validator types. We'll go through each piece of this specification, but the
full sample is presented for context.

::

    arguments:
      java-distro:
        description: The java distribution.
        default: openjdk
        required: false
        choices:
          - oracle-java
          - openjdk

    validators:
      - os_case:
          - redhat:
              - package: nfs-utils
          - debian:
              - package: nfs-common
      - argument_case:
          argument_name: java-distro
          cases:
            openjdk:
              - any:
                - all:
                  - package: java-1.8.0-openjdk-devel
                  - argument_set:
                      argument_name: java-version
                      value: 1.8.0
                - all:
                  - package: java-1.7.0-openjdk-devel
                  - argument_set:
                      argument_name: java-version
                      value: 1.7.0
            oracle-java:
              - script: install_oracle_java.sh
      - script: setup_java.sh
      - package:
        - hadoop
        - hadoop-libhdfs
        - hadoop-native
        - hadoop-pipes
        - hadoop-sbin
        - hadoop-lzo
        - lzo
        - lzo-devel
        - hadoop-lzo-native


The Arguments Section
---------------------

First, the image specification should describe any arguments that may be used
to adjust properties of the image:

::

    arguments:                                 # The section header
      - java-distro:                           # The friendly name of the argument, and the name of the variable passed to scripts
          description: The java distribution.  # A friendly description to be used in help text
          default: openjdk                     # A default value for the argument
          required: false                      # Whether or not the argument is required
          choices:                             # The argument value must match an element of this list
            - oracle-java
            - openjdk

Specifications may contain any number of arguments, as declared above, by
adding more members to the list under the ``arguments`` key.

The Validators Section
----------------------

This is where the logical flow of the image packing and validation process
is declared. A tiny example validator list is specified below.

::

    validators:
      - package: nfs-utils
      - script: setup_java.sh

This is fairly straightforward: this specification will install the nfs-utils
package (or check that it's present) and then run the ``setup_java.sh`` script.

All validators may be run in two modes: reconcile mode and test-only mode
(reconcile == false). If validators are run in reconcile mode, any image or
instance state which is not already true will be updated, if possible. If
validators are run in test-only mode, they will only test the image or
instance, and will raise an error if this fails.

We'll now go over the types of validators that are currently available in
Sahara. This framework is made to easily allow new validators to be created
and old ones to be extended: if there's something you need, please do file a
wishlist bug or write and propose your own!

Action validators
-----------------

These validators take specific, concrete actions to assess or modify your
image or instance.

The Package Validator
~~~~~~~~~~~~~~~~~~~~~

This validator type will install a package on the image, or validate that a
package is installed on the image. It can take several formats, as below:

::

    validators:
      - package: hadoop
      - package:
        - hadoop-libhdfs
        - nfs-utils:
            version: 1.3.3-8

As you can see, a package declaration can consist of:

* The package name as a string
* A list of packages, any of which may be:
  * The package name as a string
  * A dict with the package name as a key and a version property

The Script Validator
~~~~~~~~~~~~~~~~~~~~

This validator will run a script on the image. It can take several formats
as well:

::

    validators:
      - script: simple_script.sh        # Runs this file
      - script:
          set_java_home:                # The name of a script file
            arguments:                  # Only the named environment arguments are passed, for clarity
              - jdk-home
              - jre-home
            output: OUTPUT_VAR
      - script:
          store_nfs_version:            # Because inline is set, this is just a friendly name
            inline: rpm -q nfs-utils    # Runs this text directly, rather than reading a file
            output: nfs-version         # Places the stdout of this script into an argument
                                        # for future scripts to consume; if none exists, the
                                        # argument is created

Two variables are always available to scripts run under this framework:

* ``distro``: The distro of the image, in case you want to switch on distro
  within your script (rather than by using the os_case validator).
* ``test_only``: If this value equates to boolean false, then the script should
  attempt to change the image or instance if it does not already meet the
  specification. If this equates to boolean true, the script should exit with
  a failure code if the image or instance does not already meet the
  specification.


Flow Control Validators
-----------------------

These validators are used to build more complex logic into your
specifications explicitly in the yaml layer, rather than by deferring
too much logic to scripts.

The OS Case Validator
~~~~~~~~~~~~~~~~~~~~~

This validator runs different logic depending on which distribution of Linux
is being used in the guest.

::

    validators:
      - os_case:                      # The contents are expressed as a list, not a dict, to preserve order
          - fedora:                   # Only the first match runs, so put distros before families
              - package: nfs_utils    # The content of each case is a list of validators
          - redhat:                   # Red Hat distros include fedora, centos, and rhel
              - package: nfs-utils
          - debian:                   # The major supported Debian distro in Sahara is ubuntu
              - package: nfs-common


The Argument Case Validator
~~~~~~~~~~~~~~~~~~~~~~~~~~~

This validator runs different logic depending on the value of an argument.

::

    validators:
      - argument_case:
          argument_name: java-distro       # The name of the argument
          cases:                           # The cases are expressed as a dict, as only one can equal the argument's value
            openjdk:
              - script: setup-openjdk      # The content of each case is a list of validators
            oracle-java:
              - script: setup-oracle-java

The All Validator
~~~~~~~~~~~~~~~~~

This validator runs all the validators within it, as one logical block. If any
validators within it fail to validate or modify the image or instance, it will
fail.

::

    validators:
      - all:
          - package: nfs-utils
          - script: setup-nfs.sh

The Any Validator
~~~~~~~~~~~~~~~~~

This validator attempts to run each validator within it, until one succeeds,
and will report success if any do. If this is run in reconcile mode, it will
first try each validator in test-only mode, and will succeed without
making changes if any succeed (in the case below, if openjdk 1.7.0 were
already installed, the validator would succeed and would not install 1.8.0.)

::

    validators:
      - any:  # This validator will try to install openjdk-1.8.0, but it will settle for 1.7.0 if that fails
          - package: java-1.8.0-openjdk-devel
          - package: java-1.7.0-openjdk-devel

The Argument Set Validator
~~~~~~~~~~~~~~~~~~~~~~~~~~

You may find that you wish to store state in one place in the specification
for use in another. In this case, you can use this validator to set an
argument for future use.

::

    validators:
      - argument_set:
          argument_name: java-version
          value: 1.7.0

SPI Methods
-----------

In order to make this feature available for your plugin, you must
implement the following optional plugin SPI methods.

When implementing these, you may choose to use your own framework of choice
(Packer for image packing, etc.) By doing so, you can ignore the entire
framework and specification language described above. However, you may
wish to instead use the abstraction we've provided (its ability to keep
logic in one place for both image packing and cluster validation is useful
in the OpenStack context.) We will, of course, focus on that framework here.

::

    def get_image_arguments(self, hadoop_version):
        """Gets the argument set taken by the plugin's image generator"""

    def pack_image(self, hadoop_version, remote,
                   test_only=False, image_arguments=None):
        """Packs an image for registration in Glance and use by Sahara"""

    def validate_images(self, cluster, test_only=False, image_arguments=None):
        """Validates the image to be used by a cluster"""

The validate_images method is called after Heat provisioning of your cluster,
but before cluster configuration. If the test_only keyword of this method is
set to True, the method should only test the instances without modification.
If it is set to False, the method should make any necessary changes (this can
be used to allow clusters to be spun up from clean, OS-only images.) This
method is expected to use an ssh remote to communicate with instances, as
per normal in Sahara.

The pack_image method can be used to modify an image file (it is called by the
CLI above). This method expects an ImageRemote, which is essentially a
libguestfs handle to the disk image file, allowing commands to be run on the
image directly (though it could be any concretion that allows commands to be
run against the image.)

By this means, the validators described above can execute the same logic in
the image packing, instance validation, and instance preparation cases with
the same degree of interactivity and logical control.

In order to future-proof this document against possible changes, the doctext
of these methods will not be reproduced here, but they are documented very
fully in the sahara.plugins.provisioning abstraction.

These abstractions can be found in the module sahara.plugins.images.
You will find that the framework has been built with extensibility and
abstraction in mind: you can overwrite validator types, add your own
without modifying any core sahara modules, declare hierarchies of resource
locations for shared resources, and more. These features are documented in
the sahara.plugins.images module itself (which has copious doctext,) and we
encourage you to explore and ask questions of the community if you are
curious or wish to build your own image generation tooling.
