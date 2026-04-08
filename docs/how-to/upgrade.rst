.. meta::
    :description: Learn how to upgrade the DNS charms to the latest revision.

How to upgrade
==============

Upgrade the DNS charms to the latest revision with the ``juju refresh`` command. 

.. tab-set::

   .. tab-item:: ``bind``

      .. code-block::

        juju refresh bind

   .. tab-item:: ``dns-policy``

      .. code-block::
        
        juju refresh dns-policy

   .. tab-item:: ``dns-integrator``

      .. code-block::
        
        juju refresh dns-integrator

   .. tab-item:: ``dns-resolver``

      .. code-block::
        
        juju refresh dns-resolver

   .. tab-item:: ``dns-secondary``

      .. code-block::
        
        juju refresh dns-secondary

Backups are not required before upgrading any of the charms;
any set configurations or relations should remain intact.

