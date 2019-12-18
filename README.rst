|logo| Girder for MindLogger |github-version| |license-badge| |codecov-badge| |build-status|
============================================================================================

**Data Management Platform**

Contents
--------
1. `Requirements <#requirements>`_
2. `Installation <#installation>`_
3. `Deployment <#deployment>`_
4. `Data Structure <#data-structure>`_
    1. `Diagram <#diagram>`_
    2. `Glossary <#glossary>`_
5. `Links <#links>`_
6. `Contributing <./CONTRIBUTING.rst>`_
7. `Girder Source <#girder-source>`_

Reqirements
-----------

- MongoDB >= 3.6
- Python >= 3.5
  - CherryPy <=11.0.0
- Node >= 8.0

Installation
------------

1. Create and activate a virtual environment (replace ``~/girder_env`` if you want your virtual environment somewhere else). On launches after the first, only the line beginning with ``source`` is necessary.

   .. code-block:: shell

      python3 -m venv ~/girder_env
      source ~/girder_env/bin/activate
      pip install -U pip setuptools

2. Start MongoDB.

   .. code-block:: shell

      mongod &

3. From the root of this repository, install and build Girder for MindLogger.

   .. code-block:: shell

      pip install -e .
      girderformindlogger build

   Note: if ``pip install -e .`` fails with ``assert tag is not None, 'cant parse version %s' % tag`` from `setuptools_scm <https://github.com/pypa/setuptools_scm/>`_, check for git tags with ``-``s and delete those tags or replace them with ``+``s.

4. Start Girder for MindLogger.

   .. code-block:: shell

      girderformindlogger serve

5. When you're finished

   1. kill Girder for MindLogger,

      ``<Ctrl>`` + ``c``

   2. kill MongoDB, and

      .. code-block:: shell

         fg

      ``<Ctrl>`` + ``c``

   3. deactivate your virtual environment.

   .. code-block:: shell

      deactivate

Deployment
----------

Elastic Beanstalk
#################

If you're updating an existing Girder 2.x instance of Elastic Beanstalk, be sure to change your static files path from ``clients/web/static`` to ``girderformindlogger/web_client/static/``.

Data Structure
--------------
**Girder for MindLogger** uses `reprolib <https://github.com/ReproNim/schema-standardization>`_ and has the following underlying data structure:
*Note: This project is still in version 0 and these descriptions and diagrams may sometimes diverge from the actual data structure as we develop.*

Links
-----
- `reprolib specification <https://github.com/ReproNim/schema-standardization>`_
- `Development instance <https://dev.mindlogger.org>`_
- `Production instance <https://api.mindlogger.org>`_
- `Run a local instance <#requirements>`_

Contributing
------------
See `CONTRIBUTING <./CONTRIBUTING.rst>`_.

Girder Source
-------------

This source code is a customization of `:octocat: girder/girder@e97b1f7 <https://github.com/ChildMindInstitute/mindlogger-app-backend/pull/172/commits/e97b1f7ef7da894479e160cd4b64fb9be40128ce>`_

Girder is a free and open source web-based data management platform developed by
`Kitware <https://kitware.com>`_ as part of the `Resonant <https://resonant.kitware.com>`_ data and analytics ecosystem.

Documentation of the Girder platform can be found at
`:closed_book: Read the Docs <https://girderformindlogger.readthedocs.io/en/latest>`_.

For questions, comments, or to get in touch with the maintainers, head to their `Discourse forum <https://discourse.girderformindlogger.org>`_, or use their `Gitter Chatroom
<https://gitter.im/girderformindlogger/girderformindlogger>`_.

We'd love for you to `contribute to Girder <CONTRIBUTING.rst>`_.

.. |logo| image:: ./girderformindlogger/web_client/src/assets/ML-logo_25px.png
    :alt: Girder for MindLogger
    :target: https://api.mindlogger.org

.. |kitware-logo| image:: https://www.kitware.com/img/small_logo_over.png
    :target: https://kitware.com
    :alt: Kitware Logo

.. |build-status| image:: https://circleci.com/gh/ChildMindInstitute/mindlogger-app-backend.svg?style=svg
    :target: https://circleci.com/gh/ChildMindInstitute/mindlogger-app-backend
    :alt: Build Status

.. |license-badge| image:: docs/license.png
    :target: LICENSE
    :alt: License

.. |codecov-badge| image:: https://img.shields.io/codecov/c/github/ChildMindInstitute/mindlogger-app-backend.svg
    :target: https://codecov.io/gh/ChildMindInstitute/mindlogger-app-backend
    :alt: Coverage Status

.. |github-version| image:: https://img.shields.io/github/tag/ChildMindInstitute/mindlogger-app-backend.svg
    :target: https://github.com/ChildMindInstitute/mindlogger-app-backend/releases
    :alt: GitHub version
