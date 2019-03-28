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
An **applet** folder in the `Assignments <#collection>`_ collection contains 0
or more `User Settings <#user-settings>`_ items. The applet stores user roles,
scheduling, and other managerial settings for a single `Applet <#strong-entity>`_.
These folders are controlled by managers.

weak entity (under Users)
^^^^^^^^^^^^^^^^^^^^^^^^^
An **applet** folder in an `Assignments <#folder>`_ folder under a `User <#user>`_
in the `Users <#users>`_ collection contains 0 or 1 `Custom User Settings <#custom-user-settings>`_
item and stores a cipher key for `applet <#strong-entity>`_-specific user ids.
This folder is private, only accessible its parent user.

Applets
*******
The **applets** collection contains 0 or more `Applet <#strong-entity>`_
folders. This collection is controlled by editors.

Assignments
***********

collection
^^^^^^^^^^
The **assignments** collection contains 0 or more `Applet <#weak-entity-under-assignments>`_
folders. This collection is controlled by managers.

folder
^^^^^^
An **assignments** folder contains 0 or more `Applet <#weak-entity-under-users>`_ folders.
This folder is private, only accessible to its parent user.

Custom User Settings
********************
A **custom user settings** item contains user-defined overrides to default `User Settings <#user-settings>`_.
This item is private, only accessible to its parent user.

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

User Settings
*************
A **user settings** item contains user-specific information, such as display
name and custom scheduling. These items are controlled by managers.

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
