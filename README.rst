Girder for MindLogger |build-status| |license-badge| |codecov-badge|
===========================================================================

**Data Management Platform**

|logo|

Contents
--------
1. `Data Structure <#data-structure>`_
    1. `Diagram <#diagram>`_
    2. `Glossary <#glossary>`_
2. `Links <#links>`_
3. `Girder Source <#girder-source>`_

Data Structure
--------------
Girder for MindLogger has the following underlying data structure:

Diagram
#######
.. figure:: ./docs/images/Mindlogger-DB-ER.png
    :align: center
    :alt: MindLogger database entity-relationship diagram
    :figclass: align-center
    :target: ./docs/images/Mindlogger-DB-ER.dia
    The above `entity-relationship diagram <https://cacoo.com/blog/er-diagrams-vs-eer-diagrams-whats-the-difference/>`_ was created with `dia 0.97+git <https://live.gnome.org/Dia>`_.

Glossary
########

Activity
^^^^^^^^
An "individual assessment", as defined in `ReproNim schema <https://github.com/ReproNim/schema-standardization/tree/0fb4abd67d209e76325e6f42d428d7c275252ec6#20-need-for-standardizing-assessments>`_: `Activity <https://raw.githubusercontent.com/ReproNim/schema-standardization/master/schemas/Activity.jsonld>`_.

Activity Set
^^^^^^^^^^^^
A "collection[…] of `activities <#activity>`_ as defined in `ReproNim schema <https://github.com/ReproNim/schema-standardization/tree/0fb4abd67d209e76325e6f42d428d7c275252ec6#20-need-for-standardizing-assessments>`_: `ActivitySet <https://raw.githubusercontent.com/ReproNim/schema-standardization/master/schemas/ActivitySet.jsonld>`_.

Applet
^^^^^^
A document assigning one or more `activity sets <#activity-set>`_ to one or more `users <#user>`_ with or without scheduling and other constraints.

Applet-specific User ID
^^^^^^^^^^^^^^^^^^^^^^^
An identifier for a given `user <#user>`_ (or `reviewer <#reviewer>`_ or `subject <#subject>`_) for an `applet <#applet>`_ that does not expose that user's other data to anyone authorized to view information related to that applet.

Context
^^^^^^^
    A set of rules for interpreting a JSON-LD document [from this database] as specified in The Context of the JSON-LD Syntax specification."

This definition comes from `JSON-LD 1.1 <https://json-ld.org/spec/latest/json-ld/>`_ `context <https://json-ld.org/spec/latest/json-ld/#dfn-contexts>`_.

Icon
^^^^

Illustration
^^^^^^^^^^^^

Manager
^^^^^^^
An individual responsible for setting schedules, `subjects <#subject>`_ and other constraints as well as inviting other managers, `users <#user>`_ and `reviewers <#reviewer>`_ to an `applet <#applet>`_.

Protected health information
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    Any information about health status, provision of health care, or payment for health care that […] can be linked to a specific `individual <#user>`_.

This definition comes from the Wikipedia article `Protected health information <https://en.wikipedia.org/wiki/Protected_health_information>`_.

Response
^^^^^^^^
Data collected when a `user <#user>`_ responds to an `activity <#activity>`_.

Reviewer
^^^^^^^^
An individual authorized to review `user <#user>`_ `responses <#response>`_ to `activitis <#activity>`_ in an `applet <#applet>`_.

Screen
^^^^^^
One or more "elements of individual assessments" displayed in a single screen or page view, as defined in `ReproNim schema <https://github.com/ReproNim/schema-standardization/tree/0fb4abd67d209e76325e6f42d428d7c275252ec6#20-need-for-standardizing-assessments>`_: `Item <https://raw.githubusercontent.com/ReproNim/schema-standardization/master/schemas/Field.jsonld>`_ and `Issue #85 <https://github.com/ReproNim/schema-standardization/issues/85>`_.

Skin
^^^^
Color scheme and other branding and appearance-related metadata.

Subject
^^^^^^^
The person being informed about by the `user <#user>`_ `responding <#response>`_ to an `activity <#activity>`_. For self-report, the same user as the informant.

Text
^^^^
Copy included in the mobile and web app, including "About MindLogger" and helper text.

User
^^^^
An individual using a MindLogger mobile application or MindLogger web application to `respond <#response>`_ to `activities <#activity>`_.

Links
-----
- `ReproNim Schema specification <https://github.com/ReproNim/schema-standardization>`_
- `Development instance <https://mindlogger-dev.vasegurt.com>`_
- `Production instance <https://api.mindlogger.info>`_
- `Run a local instance <#requirements>`_

Girder Source
-------------

This source code is a customization of `:octocat: girder/girder@5ed7bdd <https://github.com/girder/girder/tree/5ed7bdd850e9dc8657cf25984627628374811048>`_

Girder is a free and open source web-based data management platform developed by
`Kitware <https://kitware.com>`_ as part of the `Resonant <https://resonant.kitware.com>`_ data and analytics ecosystem.

Documentation of the Girder platform can be found at
`:closed_book: Read the Docs <https://girder.readthedocs.io/en/latest>`_.

For questions, comments, or to get in touch with the maintainers, head to their `Discourse forum <https://discourse.girder.org>`_, or use their `Gitter Chatroom
<https://gitter.im/girder/girder>`_.

We'd love for you to `contribute to Girder <CONTRIBUTING.rst>`_.

.. |logo| image:: ./girder/web_client/src/assets/ML-logo.png
    :width: 25px
    :alt: Girder for MindLogger

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
