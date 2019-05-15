|logo| Girder for MindLogger |build-status| |license-badge| |gitter-badge| |codecov-badge|
==========================================================================================

**Data Management Platform**

Contents
--------
1. `Data Structure <#data-structure>`_
2. `Links <#links>`_
3. `Girder Source <#girder-source>`_

Data Structure
--------------
Girder for MindLogger has the following underlying data structure:

.. figure:: ./docs/images/Mindlogger-DB-ER.png
    :align: center
    :alt: MindLogger database entity-relationship diagram
    :figclass: align-center
    :target: ./docs/images/Mindlogger-DB-ER.dia
    The above `entity-relationship diagram <https://cacoo.com/blog/er-diagrams-vs-eer-diagrams-whats-the-difference/>`_ was created with `dia 0.97+git <https://live.gnome.org/Dia>`_.

Links
-----
- `ReproNim Schema specification <https://github.com/ReproNim/schema-standardization>`_
- `Development instance <https://mindlogger-dev.vasegurt.com>`_
- `Production instance <https://api.mindlogger.info>`_
- `Run a local instance <#requirements>`_

Girder Source
-------------

This source code is a customization of `:octocat: girder/girder@5ed7bdd <https://github.com/girder/girder/tree/5ed7bdd850e9dc8657cf25984627628374811048>`_

|girder-logo| Girder is a free and open source web-based data management platform developed by
|kitware-logo| as part of the |resonant-logo| data and analytics ecosystem.

Documentation of the Girder platform can be found at
`:book: Read the Docs <https://girder.readthedocs.io/en/latest>`_.

For questions, comments, or to get in touch with the maintainers, head to their `Discourse forum <https://discourse.girder.org>`_, or use their `Gitter Chatroom
<https://gitter.im/girder/girder>`_.

We'd love for you to `contribute to Girder <CONTRIBUTING.rst>`_.

.. |logo| image:: ./girder/web_client/src/assets/ML-logo.png
    :width: 25px
    :alt: Girder for MindLogger

.. |girder-logo| image:: ./girder/web_client/src/assets/Girder_Mark.png
    :width: 25px
    :alt: Girder for MindLogger

.. |kitware-logo| image:: https://www.kitware.com/img/small_logo_over.png
    :target: https://kitware.com
    :alt: Kitware
    :width: 100px

.. |resonant-logo| image:: https://resonant.kitware.com/img/Resonant_Mark_Text.png
    :target: https://resonant.kitware.com
    :alt: Resonant
    :width: 100px

.. |build-status| image:: https://circleci.com/gh/ChildMindInstitute/mindlogger-app-backend.svg?style=svg
    :target: https://circleci.com/gh/ChildMindInstitute/mindlogger-app-backend
    :alt: Build Status

.. |license-badge| image:: docs/license.png
    :target: LICENSE
    :alt: License

.. |codecov-badge| image:: https://img.shields.io/codecov/c/github/ChildMindInstitute/mindlogger-app-backend.svg
    :target: https://codecov.io/gh/ChildMindInstitute/mindlogger-app-backend
    :alt: Coverage Status
