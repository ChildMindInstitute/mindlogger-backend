Girder for Mindlogger
====================

Reqirements
-----------

- MongoDB >= 3.6
- Python >= 3.5
- Node >= 8.0

Installation
------------

1. Create and activate a virtual environment (replace ``~/girder_env`` if you want your virtual environment somewhere else). On launches after the first, only the line beginning with ``source`` is necessary. ::

   python3 -m venv ~/girder_env
   source ~/girder_env/bin/activate
   pip install -U pip setuptools

2. Start MongoDB. ::

   mongod &

3. From the root of this repository, install and build Girder for Mindlogger. ::

   pip install -e .
   girder build

4. Start Girder for Mindlogger. ::

   girder serve

5. When you're finished

   1. kill Girder for Mindlogger,

      ``<Ctrl>``+``c``

   2. kill MongoDB, and ::

      fg

      ``<Ctrl>``+``c``

   3. deactivate your virtual environment. ::

      deactivate


Data Structure
--------------

Mindlogger is moving towards the following data structure:

.. figure:: ./docs/images/Mindlogger-DB-ER.png
    :align: center
    :alt: Mindlogger database entity-relationship diagram
    :figclass: align-center
    :target: ./docs/images/Mindlogger-DB-ER.dia

    The above `entity-relationship diagram <https://cacoo.com/blog/er-diagrams-vs-eer-diagrams-whats-the-difference/>`_ was created with `dia 0.97+git <https://live.gnome.org/Dia>`_.

Entities
########

Each entity is separately access controlled.

Activity
********

Activity Version
****************

Applet
******

strong entity
^^^^^^^^^^^^^

weak entity (under Assignments)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

weak entity (under Users)
^^^^^^^^^^^^^^^^^^^^^^^^^

Applets
*******

A Girder Collection

Custom User Settings
********************

PHI
***

Response
********

Responses
*********

Screen
******

User
****

strong entity
^^^^^^^^^^^^^

weak entity
^^^^^^^^^^^

Users
*****

Links
-----

- Development instance: https://mindlogger-dev.vasegurt.com
- Production instance: https://api.mindlogger.info
- Run a local instance: If one clones our `girder <https://github.com/ChildMindInstitute/mindlogger-app-backend/tree/girder>`_ or `girder-dev <https://github.com/ChildMindInstitute/mindlogger-app-backend/tree/girder-dev>`_ branch of this repository, following `the official Girder documentation <https://girder.readthedocs.io/en/stable/admin-docs.html>`_ should get a local instance running.

|logo| Girder |build-status| |docs-status| |license-badge| |gitter-badge| |codecov-badge|
-----------------------------------------------------------------------------------------

**Data Management Platform**

This source code is a customization of `:octocat: girder/girder <https://github.com/girder/girder/tree/292690e7e4c269ed3b34757ba86ddfa2713f9f16>`_

Girder is a free and open source web-based data management platform developed by
`Kitware <https://kitware.com>`_ as part of the `Resonant <http://resonant.kitware.com>`_
data and analytics ecosystem.

|kitware-logo|

Documentation of the Girder platform can be found at
https://girder.readthedocs.io.

For questions, comments, or to get in touch with the maintainers, head to our `Discourse forum <https://discourse.girder.org>`_, or use our `Gitter Chatroom
<https://gitter.im/girder/girder>`_.

We'd love for you to `contribute to Girder <CONTRIBUTING.rst>`_.

.. |logo| image:: girder/web_client/static/img/Girder_Favicon.png

.. |kitware-logo| image:: https://www.kitware.com/img/small_logo_over.png
    :target: https://kitware.com
    :alt: Kitware Logo

.. |build-status| image:: https://circleci.com/gh/girder/girder.png?style=shield
    :target: https://circleci.com/gh/girder/girder
    :alt: Build Status

.. |docs-status| image:: https://readthedocs.org/projects/girder/badge?version=latest
    :target: https://girder.readthedocs.org
    :alt: Documentation Status

.. |license-badge| image:: docs/license.png
    :target: https://pypi.python.org/pypi/girder
    :alt: License

.. |gitter-badge| image:: https://badges.gitter.im/Join Chat.svg
    :target: https://gitter.im/girder/girder?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge
    :alt: Gitter Chat

.. |codecov-badge| image:: https://img.shields.io/codecov/c/github/girder/girder.svg
    :target: https://codecov.io/gh/girder/girder
    :alt: Coverage Status
