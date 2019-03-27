Girder for Mindlogger
====================

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
An **activity** folder contains 1 or more
`Activity Version <#activity-version>`_ folders. If an **activity** is selected
via the `/activity/{id} <https://mindlogger-dev.vasegurt.com/api/v1#!/activity/activity_getActivity>`_
endpoint, the latest activity version is returned. These folders are controlled
by editors.

Activity Version
****************
An **activity version** folder contains 1 or more `screen <#screen>`_ items and
is read-only once activated, other than being deactivatible. If an **activity
version** is selected via the `/activity/version/{id} <https://mindlogger-dev.vasegurt.com/api/v1#!/activity/activity_getActivityVersion>`_
endpoint, that version will be returned even if a newer version of that
`activity <#activity>`_ is available. These folders are controlled by editors.

Applet
******

strong entity
^^^^^^^^^^^^^
An **applet** folder in the `Applets <#applets>`_ collection contains 0 or
more `Activity <#activity>`_ folders. These folders are controlled by editors.

weak entity (under Assignments)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

weak entity (under Users)
^^^^^^^^^^^^^^^^^^^^^^^^^

Applets
*******
The **applets** collection contains 0 or more `Applet <#strong-entity>`_
folders. This collection is controlled by editors.

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
A **screen** item contains information about prompts, response options, and user
interface. A **screen** is read-only once activated, other than being
deactivatible. These items are controlled by editors.

Subject
*******

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

|logo| Girder for Mindlogger |build-status| |docs-status| |license-badge| |gitter-badge| |codecov-badge|
-----------------------------------------------------------------------------------------

**Data Management Platform**

Girder is a free and open source web-based data management platform developed by
`Kitware <https://kitware.com>`_ as part of the `Resonant <http://resonant.kitware.com>`_
data and analytics ecosystem.

|kitware-logo|

Documentation of the Girder platform can be found at
https://girder.readthedocs.io.
