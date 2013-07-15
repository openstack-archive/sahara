Enabling Anti-Affinity Feature
==============================

The Anti-Affinity feature requires certain scheduler filters to be enabled on Nova.
Edit your ``/etc/nova/nova.conf`` in the following way:

.. sourcecode:: cfg

    [DEFAULT]

    ...

    scheduler_driver=nova.scheduler.filter_scheduler.FilterScheduler
    scheduler_default_filters=DifferentHostFilter,SameHostFilter
