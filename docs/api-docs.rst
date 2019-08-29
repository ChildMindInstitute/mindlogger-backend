API Documentation
=================

.. _restapi:

RESTful API
-----------

Clients access Girder servers uniformly via its RESTful web API. By providing
a single, stable, consistent web API, it is possible to write multiple
interchangeable clients using different technologies.

When a Girder instance is deployed, it typically also serves a page
that uses `Swagger <https://swagger.io>`_ to document
all available RESTful endpoints in the web API and also provide an easy way
for users to execute those endpoints with parameters of their choosing. In
this way, the Swagger page is just the simplest and lightest client application
for girderformindlogger. This page is served out of the path ``/api`` under the root path of
your Girder instance.


Internal Python API
-------------------

.. _models:

Models
^^^^^^

In Girder, the model layer is responsible for actually interacting with the
underlying database. Model classes are where the documents representing
resources are actually saved, retrieved, and deleted from the DBMS. Validation
of the resource documents is also done in the model layer, and is invoked
each time a document is about to be saved.

Typically, there is a model class for each resource type in the system. These
models are loaded as singletons for efficiency, but you should use them like
normal objects. For example, to use the ``list`` method of the Group model:

.. code-block:: python

    from girderformindlogger.models.group import Group
    groups = Group().list(user=self.getCurrentUser())

All models that require the standard access control semantics should extend the
`AccessControlledModel` class. Otherwise, they should extend the `Model` class.

All model classes must have an ``initialize`` method in which they declare
the name of their corresponding Mongo collection, as well as any collection
indexes they require. For example, to make a model whose documents live in a
collection called ``cat_collection`` and ensure that the ``name`` key is indexed
on that collection, you would use the following ``initialize`` method:

.. code-block:: python

    from girderformindlogger.models.model_base import Model

    class Cat(Model):
        def initialize(self):
            self.name = 'cat_collection'
            self.ensureIndex('name')


Model Helper Functions
~~~~~~~~~~~~~~~~~~~~~~
.. automodule:: girderformindlogger.models
   :members:

Model Base
~~~~~~~~~~
.. automodule:: girderformindlogger.models.model_base
   :members:

API Key
~~~~~~~
.. automodule:: girderformindlogger.models.api_key
   :members:

User
~~~~
.. automodule:: girderformindlogger.models.user
   :members:

Token
~~~~~
.. automodule:: girderformindlogger.models.token
   :members:

Group
~~~~~
.. automodule:: girderformindlogger.models.group
   :members:

Collection
~~~~~~~~~~

.. automodule:: girderformindlogger.models.collection
   :members:

Folder
~~~~~~
.. automodule:: girderformindlogger.models.folder
   :members:

Item
~~~~
.. automodule:: girderformindlogger.models.item
   :members:

Setting
~~~~~~~

.. automodule:: girderformindlogger.models.setting
   :members:

Assetstore
~~~~~~~~~~

.. automodule:: girderformindlogger.models.assetstore
   :members:

File
~~~~

.. automodule:: girderformindlogger.models.file
   :members:

Upload
~~~~~~

.. automodule:: girderformindlogger.models.upload
   :members:

Notification
~~~~~~~~~~~~

.. automodule:: girderformindlogger.models.notification
    :members:

Web API Endpoints
^^^^^^^^^^^^^^^^^

Base Classes and Helpers
~~~~~~~~~~~~~~~~~~~~~~~~
.. automodule:: girderformindlogger.api.access
   :members:

.. automodule:: girderformindlogger.api.api_main
   :members:

.. automodule:: girderformindlogger.api.describe
   :members:

.. automodule:: girderformindlogger.api.docs
   :members:

.. automodule:: girderformindlogger.api.filter_logging
   :members:

.. automodule:: girderformindlogger.api.rest
   :members:

.. _api-docs-utility:

Utility
^^^^^^^
.. automodule:: girderformindlogger.utility
   :members:

.. automodule:: girderformindlogger.utility.abstract_assetstore_adapter
   :members:

.. automodule:: girderformindlogger.utility.acl_mixin
   :members:

.. automodule:: girderformindlogger.utility.assetstore_utilities
   :members:

.. automodule:: girderformindlogger.utility.config
   :members:

.. automodule:: girderformindlogger.utility.filesystem_assetstore_adapter
   :members:

.. automodule:: girderformindlogger.utility.gridfs_assetstore_adapter
   :members:

.. automodule:: girderformindlogger.utility.mail_utils
   :members:

.. automodule:: girderformindlogger.utility.model_importer
   :members:

.. automodule:: girderformindlogger.utility.path
   :members:

.. automodule:: girderformindlogger.utility.progress
   :members:

.. automodule:: girderformindlogger.utility.resource
   :members:

.. automodule:: girderformindlogger.utility.s3_assetstore_adapter
   :members:

.. automodule:: girderformindlogger.utility.search
   :members:

.. automodule:: girderformindlogger.utility.server
   :members:

.. automodule:: girderformindlogger.utility.setting_utilities
   :members:

.. automodule:: girderformindlogger.utility.system
   :members:

.. automodule:: girderformindlogger.utility.webroot
   :members:

.. automodule:: girderformindlogger.utility.ziputil
   :members:

Constants
~~~~~~~~~
.. automodule:: girderformindlogger.constants
   :members:

.. _events:

Events
~~~~~~
.. automodule:: girderformindlogger.events
    :members:

Exceptions
~~~~~~~~~~
.. automodule:: girderformindlogger.exceptions
   :members:

Logging
~~~~~~~
.. automodule:: girderformindlogger
   :members:

Plugins
~~~~~~~
.. automodule:: girderformindlogger.plugin
   :members:

Python Client
-------------

See :ref:`python-client`

Web client
----------

Documentation for Girder's web client library is built and hosted by esdoc and can be found
`here <https://doc.esdoc.org/github.com/girderformindlogger/girderformindlogger>`_.
