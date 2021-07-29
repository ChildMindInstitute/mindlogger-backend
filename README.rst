|logo| Girder for MindLogger |github-version| |license-badge| |codecov-badge| |build-status|
============================================================================================

**Data Management Platform**

Contents
--------
1. `Requirements <#requirements>`_
2. `Installation <#installation>`_
3. `Deployment <#deployment>`_
4. `Data Structure <#data-structure>`_
5. `Links <#links>`_
6. `Contributing <./CONTRIBUTING.rst>`_
7. `Girder Source <#girder-source>`_

Requirements
------------

- MongoDB >= 3.6
- Python >= 3.5
  - CherryPy <=11.0.0
- Node >= 8.0
- Redis

Installation
------------

Linux/Mac
#########

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

Windows
#######

1. In Windows Powershell, create and activate a virtual environment (replace ``$HOME\girder_env`` if you want your virtual environment somewhere else). On launches after the first, only the line ending with ``Activate.ps1`` is necessary.

   .. code-block:: shell

      python3 -m venv $HOME\girder_env
      $HOME\girder_env\Scripts\Activate.ps1
      pip install -U pip setuptools

2. Start MongoDB.

   .. code-block:: shell

      mongod

3. Open a new PowerShell terminal and navigate to the root of this repository. Reactivate the virtual environment and then install and build Girder for MindLogger.

   .. code-block:: shell

      $HOME\girder_env\Scripts\Activate.ps1
      pip install -e .
      girderformindlogger build

4. Start Girder for MindLogger.

   .. code-block:: shell

      girderformindlogger serve

5. When you're finished

   1. kill Girder for MindLogger

      ``<Ctrl>`` + ``c``

   2. kill MongoDB

      ``<Ctrl>`` + ``c``

   3. deactivate your virtual environment.

   .. code-block:: shell

      deactivate

Docker
######

The database and api can be run using docker-compose for local development purposes.

1. make sure docker is running. For example:

   .. code-block:: shell

      docker -v
         Docker version 20.10.7, build f0df350


2. run the db and api.

   .. code-block:: shell

      docker-compose -f docker-compose.local.yml up


The first time this command is run will take a few minutes as the images are downloaded and built.

3. make some changes to your local code and restart the girderformindlogger container to see the changes.

   .. code-block:: shell

      docker-compose -f docker-compose.local.yml restart girderformindlogger

or  

   .. code-block:: shell

      docker restart mindlogger-backend_girderformindlogger_1

Deployment
----------

See `CONTRIBUTING.rst#deployment <./CONTRIBUTING.rst#deployment>`_.

Elastic Beanstalk
#################

If you're updating an existing Girder 2.x instance of Elastic Beanstalk, be sure to change your static files path from ``clients/web/static`` to ``girderformindlogger/web_client/static/``.

Data Structure
--------------
**Girder for MindLogger** uses `reprolib <https://github.com/ReproNim/schema-standardization>`_ and has the following underlying data structure.
*Note: This project is still in version 0 and these descriptions and diagrams may sometimes diverge from the actual data structure as we develop.*

The diagram below shows how the reproschema classes (`protocol <#protocol>`_, `activity <#activity>`_ and `screen <#screen>`_) fit between the user handling (access and customization, in `applet <#applet>`_ in the Girder for Mindlogger backend) and the display implementation (the UI components handled in the front-end applications).

.. image:: https://matter.childmind.org/assets/img/blog/MindLogger%20ecological%20momentary%20assessments%20in%20the%20Healthy%20Brain%20Network/slide6.png
    :alt: applet → protocol → activity → screen → UI components

https://api.mindlogger.org/api/v1 displays a comprehensive list of currently available API calls including parameters, notes about what the operations do, and notes about deprecation.

In transit between the (access-controlled) API and the (BSON storage) database, all data in MindLogger are shaped into one or more of the data models defined in the submodules of `girderformindlogger.models <https://github.com/ChildMindInstitute/mindlogger-app-backend/tree/master/girderformindlogger/models>`_. Here is a brief overview of those data models. Rather than duplicate documentation provided elsewhere (and risk sliding out of sync), links are provided to further documentation where appropriate.

Because all of these data are stored in BSON, arbitrary additional keys and values can be included in an instance of any of the data models. For models unique to MindLogger (ie, involved in implementation beyond the protocol level), a data dictionary is provided here.

activity
########

An `Activity as defined in reproschema <https://raw.githubusercontent.com/ReproNim/reproschema/master/schemas/Activity>`_, stored as a `Girder folder <#folder>`_.

``cached`` is autogenerated once the activity is parsed on the server.

api_key
#######

A model `inherited from Girder <https://girder.readthedocs.io/en/stable/api-docs.html#module-girder.models.api_key>`_.

applet
######

An access-controlled, potentially customized, implementation of a `protocol <#protocol>`_ within MindLogger, stored as a `Girder folder <#folder>`_.

+------------------------+----------+-----------+---------------+
| Attribute Name         | Required | Type      | Autogenerated |
+========================+==========+===========+===============+
| {keys required for     | true     | {various} | {mostly}      |
|  Girder Folders}       |          |           |               |
+------------------------+----------+-----------+---------------+
| ``meta.applet``        | true     | dict      | false         |
+------------------------+----------+-----------+---------------+
| ``meta.protocol``      | true     | dict      | false         |
+------------------------+----------+-----------+---------------+
| ``roles``              | true     | dict      | true          |
+------------------------+----------+-----------+---------------+
| ``cached``             | true     | dict      | true          |
+------------------------+----------+-----------+---------------+

``meta.protocol`` defines the protocol for the the applet.

``meta.applet`` defines applet-level customization, including scheduling.

``roles`` is an Object with the following structure, where the innermost array is populated with ObjectIds:

.. code-block:: JSON

    {
      "coordinator": {
        "groups": []
      },
      "editor": {
        "groups": []
      },
      "manager": {
        "groups": []
      },
      "reviewer": {
        "groups": []
      },
      "user": {
        "groups": []
      }
    }

``cached`` is autogenerated once the applet is parsed on the server.

assetstore
##########

A model `inherited from Girder <https://girder.readthedocs.io/en/stable/user-guide.html#assetstores>`_.

assignment
##########

Deprecated. Do not use.

collection
##########

A model `inherited from Girder <https://girder.readthedocs.io/en/stable/user-guide.html#collections>`_.

file
####

A model `inherited from Girder <https://girder.readthedocs.io/en/stable/user-guide.html#files>`_.

folder
######

A model `inherited from Girder <https://girder.readthedocs.io/en/stable/user-guide.html#folders>`_.

group
#####

A model `inherited from Girder <https://girder.readthedocs.io/en/stable/user-guide.html#groups>`_.

ID_code
#######

In order to protect user privacy, reviewers cannot see any information from a `profile <#profile>`_ or its underlying `user <#user>`_. Rather, users are identified through ID codes which are tied to profiles. ID codes need not be unique, and a profile can have more than one ID code. ID codes are autogenerated if not supplied through the API.

+----------------+----------+----------+---------------+
| Attribute Name | Required | Type     | Autogenerated |
+================+==========+==========+===============+
| ``_id``        | true     | ObjectId | true          |
+----------------+----------+----------+---------------+
| ``code``       | true     | string   | optional      |
+----------------+----------+----------+---------------+
| ``profileId``  | true     | ObjectId | false         |
+----------------+----------+----------+---------------+
| ``created``    | true     | datetime | true          |
+----------------+----------+----------+---------------+
| ``updated``    | true     | datetime | true          |
+----------------+----------+----------+---------------+

invitation
##########

An invitation is a single-use document, tied to a particular applet and user role, that persists until someone accepts or declines. If an invitation is accepted, a profile is created for the user who accepted the invitation if one does not already exist, and the user is inducted into a group authorizing the role in the applet as defined in the invitation. Invitations also include information about who created the invitation and when.

+------------------------+----------+----------+---------------+
| Attribute Name         | Required | Type     | Autogenerated |
+========================+==========+==========+===============+
| ``_id``                | true     | ObjectId | true          |
+------------------------+----------+----------+---------------+
| ``appletId``           | true     | ObjectId | false         |
+------------------------+----------+----------+---------------+
| ``role``               | true     | string   | false         |
+------------------------+----------+----------+---------------+
| ``invitedBy``          | true     | dict     | true          |
+------------------------+----------+----------+---------------+
| ``coordinatorDefined`` | false    | dict     | false         |
+------------------------+----------+----------+---------------+
| ``created``            | true     | datetime | true          |
+------------------------+----------+----------+---------------+
| ``updated``            | true     | datetime | true          |
+------------------------+----------+----------+---------------+

item
####

A model `inherited from Girder <https://girder.readthedocs.io/en/stable/user-guide.html#items>`_.

model_base
##########

A model `inherited from Girder <https://girder.readthedocs.io/en/stable/api-docs.html#models>`_.

notification
############

A model `inherited from Girder <https://girder.readthedocs.io/en/stable/api-docs.html#module-girder.models.notification>`_.

profile
#######

A **profile** stores information specific to the intersection of a `user <#user>`_ and an `applet <#applet>`_. The API should handle selecting the appropriate value for customizable fields in this order of preference (profile.userDefined is most preferred, component default is least preferred):

profile.userDefined > profile.coordinatorDefined > applet > protocol > activity > screen > component default

Every UI component *should* have a default in case of a cascade of ``undefined``s all the way down the chain above. If no coordinator-defined or user-defined value is provided for ``displayName``, that field will be auto-populated from the profile's associated user.

+------------------------+----------+----------+---------------+
| Attribute Name         | Required | Type     | Autogenerated |
+========================+==========+==========+===============+
| ``_id``                | true     | ObjectId | true          |
+------------------------+----------+----------+---------------+
| ``appletId``           | true     | ObjectId | false         |
+------------------------+----------+----------+---------------+
| ``userId``             | true     | ObjectId | false         |
+------------------------+----------+----------+---------------+
| ``profile``            | true     | Boolean  | true          |
+------------------------+----------+----------+---------------+
| ``coordinatorDefined`` | false    | dict     | false         |
+------------------------+----------+----------+---------------+
| ``userDefined``        | false    | dict     | optional      |
+------------------------+----------+----------+---------------+
| ``created``            | true     | datetime | true          |
+------------------------+----------+----------+---------------+
| ``updated``            | true     | datetime | true          |
+------------------------+----------+----------+---------------+

protocol
########

An `ActivitySet as defined in reproschema <https://raw.githubusercontent.com/ReproNim/reproschema/master/schemas/ActivitySet>`_, stored as a `Girder folder <#folder>`_.

``cached`` is autogenerated once the protocol is parsed on the server.

protoUser
#########

Deprecated. Do not use.

response_folder
###############

The **response_folder** module contains 2 models: **ResponseItem** and **ResponseFolder**.

A **ResponseItem** is created (as a `Girder item <#item>`_) each time a user completes an activity. ResponseItems are stored in **ResponseFolders** (each a `Girder folder <#folder>`_) which are access controlled to allow authorized reviewers to see all data they are authorized to see and only data they are authorized to see.

roles
#####

**Roles** are applet-specific and handled through `groups <#group>`_. When a new applet is created, the creator of the applet is automatically inducted into all groups with roles for that applet.

* *editors* can modify the content of protocols, activities, and screens
* *managers* can modify the customization of applets and can manage all user roles
* *coordinators* can manage a limited set of user roles: coordinator and user
* *users* can perform the activities in an applet's protocol, can customize their own settings, and can see their own data
* *reviewers* can access all data collected from an applet

An individual, through group memberships, can have any combination of roles per applet and can have roles in any number of applets. Roles that manager users can see limited personal information (eg, ``displayName``). Reviewers see users identified only by ``ID code``. Take care to limit the number of reviewers with user-management permissions to minimize the risk of reidentification.

screen
######

An `Item as defined in reproschema <https://raw.githubusercontent.com/ReproNim/reproschema/master/schemas/Field>`_, stored as a a `Girder item <#item>`_.

``cached`` is autogenerated once the screen is parsed on the server.

theme
#####

allows admins to manage themes for styling applets.
themes are saved in a collection called themes, with a folder for each theme.

**adding a new theme**  

Viewing saved themes (get request) is possible without logging in, but only database administrators for the girderformindlogger instance can add, change or delete themes (i.e.: to use the post, put and delete endpoints). By default the first person to create an account in a girder instance is an admin.

1. To add a theme, log in to giderformindlogger's GUI with an admin account. https://api.mindlogger.org/#?dialog=login

As a site admin, you should see an Admin console link in the left-side navigation bar ( refer to [girder docs](https://girder.readthedocs.io/en/latest/deployment.html#create-a-site-admin-user) ). 

**Important:** The **1st theme** added to the database is selected as the default theme for all new applets.

2. Using the API GUI, you can add themes with different logos, colors etc. (see fields here https://api-staging.mindlogger.org/api/v1#/theme ). Make sure to manually check before posting a new theme that the image urls are publicly accessible and that the image's format is compatible with the appearance in the app.  

See an example of the logo, background image and colors applied in the app here: https://github.com/ChildMindInstitute/mindlogger-app/issues/1864  


Below is the mindlogger theme as an example:

name: mindlogger  

logo: https://mindlogger.org/assets/logos/mindlogger-logo-transparent.png   

backgroundImage: https://mindlogger.org/assets/img/bg0.jpg  

primaryColor: #0067A0  

secondaryColor: #FFFFFF   

tertiaryColor: #404040  

setting
#######

A model `inherited from Girder <https://girder.readthedocs.io/en/stable/api-docs.html#module-girder.models.setting>`_.

token
#####

A model `inherited from Girder <https://girder.readthedocs.io/en/stable/api-docs.html#module-girder.models.token>`_.

upload
######

A model `inherited from Girder <https://girder.readthedocs.io/en/stable/api-docs.html#module-girder.models.upload>`_.

user
####

A model `inherited from Girder <https://girder.readthedocs.io/en/stable/user-guide.html#users>`_.

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
