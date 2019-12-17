.. |masterbranch| replace:: ``master`` branch

*********************
Girder for MindLogger
*********************

Changes
-------
Unreleased
==========
2019-12-17: v0.7.5
^^^^^^^^^^^^^^^^^^
* :racehorse: Check if user requesting user list is a coordinator just once

2019-12-17: v0.7.4
^^^^^^^^^^^^^^^^^^
* :ambulance: :chipmunk: Resolve caching issue for new users

2019-12-17: v0.7.3
^^^^^^^^^^^^^^^^^^
* :ambulance: :pencil: Save invitation acceptance

2019-12-16: v0.7.2
^^^^^^^^^^^^^^^^^^
* :ambulance: Restore `responseDates` to `applet` Objects
* :racehorse: Thread cache refreshing
* :ambulance: Update cache, *then* load when refreshing caches
* :pencil: Return real parsed URLs (resolve #247)

2019-12-05: v0.7.1
^^^^^^^^^^^^^^^^^^
* :racehorse: Resolve some query efficiency problems
* :fire: :books: Remove some deprecated text and illustrations from README

2019-11-25: v0.6.6
^^^^^^^^^^^^^^^^^^
* :ambulance: Fix `POST response/applet/activity` route

2019-11-25: v0.6.5
^^^^^^^^^^^^^^^^^^
* :pencil: Allow invitations for roles other than "user"

2019-11-21: v0.6.4
^^^^^^^^^^^^^^^^^^
* :sparkles: Informant-subject relationships

2019-11-20: v0.6.3
^^^^^^^^^^^^^^^^^^
* :hammer: Update invitation routes

2019-11-20: v0.6.2
^^^^^^^^^^^^^^^^^^
* :sparkles: ID codes

2019-11-19: v0.6.1
^^^^^^^^^^^^^^^^^^
* :sparkles: User profiles
* :tractor: :art: :hammer: Invitations

2019-11-19: v0.5.13
^^^^^^^^^^^^^^^^^^^
* :ambulance: restore `schedule` object to `GET /user/applets`
* :tractor: :art: Make URL values dereferenceable

2019-11-11: v0.5.12
^^^^^^^^^^^^^^^^^^^
* :hammer: :racehorse: Stability and performance fixes
* :lipstick: Clearer authentication error messages

2019-11-06: v0.5.11
^^^^^^^^^^^^^^^^^^^
* :ambulance: :speaker: Handle additional JSON-LD errors.

2019-11-04: v0.5.10
^^^^^^^^^^^^^^^^^^^
* :arrow_up: :tractor: :art: `|schema-standardization→reproschema| <https://github.com/ReproNim/reproschema/pull/278>`_
* :arrow_up: :tractor: :art: `|activitySet→protocol| <https://github.com/ReproNim/reproschema/pull/277>`_

2019-10-31 :jack_o_lantern:: v0.5.9
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
* :sparkles: :building_construction: New route: `GET schedule`

2019-10-30: v0.5.8
^^^^^^^^^^^^^^^^^^
* :hammer: Prefix all `reprolib <https://github.com/ReproNim/schema-standardization>`_ terms
* :ambulance: :tractor: Delanguage tag `http://schema.org/url`s

2019-10-25: v0.5.7
^^^^^^^^^^^^^^^^^^
* :racehorse: Improve `GET user/applets` speed

2019-10-25: v0.5.6
^^^^^^^^^^^^^^^^^^
* :tractor: Update user model
* :microscope: :snake: Test Python functions

2019-10-21: v0.5.5
^^^^^^^^^^^^^^^^^^
* :books: :microscope: Coverage reports

2019-10-11 ‒ 15: v0.5.3 ‒ v0.5.4
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
* :ambulance: :green_heart: Handle change in the way schema are defined per `|1c54072| <https://github.com/ReproNim/schema-standardization/commit/1c5407247817f2c8ec47f2f286683ad94065e2af>`_

2019-10-01: v0.5.2
^^^^^^^^^^^^^^^^^^
* :hammer: Fetch activity responses by URL rather than ID
* :green_heart: Restore continuous integration

2019-09-30: v0.5.1
^^^^^^^^^^^^^^^^^^
* :microscope: Add integration tests to run locally

2019-09-25: v0.4.8
^^^^^^^^^^^^^^^^^^
* :ambulance: Fix datetime bug

2019-09-24: v0.4.7
^^^^^^^^^^^^^^^^^^
* :sparkles: Reviewer can see data

2019-09-24: v0.4.4 ‒ v0.4.6
^^^^^^^^^^^^^^^^^^^^^^^^^^^
* :ambulance: Bug fixes regarding responses

2019-09-20: v0.4.3
^^^^^^^^^^^^^^^^^^
* :hammer: Allow arbitrary levels of activity nesting rather than forcing 3-level heirarchy

2019-09-19: v0.4.2
^^^^^^^^^^^^^^^^^^
* :racehorse: Optimized `GET responses`

2019-09-17: v0.4.1
^^^^^^^^^^^^^^^^^^
* :sparkles: `responseDates` added to `GET user/responses` for user role, returning a reverse chronological Array of ISO 8601 dates in which that applet has been responded to.
* :arrow_down: Reverted swagger-ui to v2
* :tractor: Response routes

2019-05-29: v0.3.1
^^^^^^^^^^^^^^^^^^
* :sparkles: New route: `GET /group/open`: List all groups with open registration.
* :sparkles: New route params:
  * `POST /group?openRegistration`: Whether users can join without being invited.
  * `PUT /group?openRegistration`: Whether users can join without being invited.
* :sparkles: New route functionality: `POST /group/{id}/member`: Now allows users to join without an invitation if a group's `openRegistration` is set to `true`.
* :sparkles: :tractor: Changed package name from `girder` to `girderformindlogger` and matched versioning to documentation.

2019-05-13
^^^^^^^^^^
* :hammer: :sparkles: Allow undefined keys in JSON-LD Expansion

2019-05-08
^^^^^^^^^^
* :hammer: :tractor: :arrow_up: Rebase from Girder 2.5 to Girder 3.0 (Unreleased)

-----

*Below is the changelog of the upstream Girder project's `|masterbranch| <https://github.com/girderformindlogger/girderformindlogger/tree/master>`_*

-----

=============
Release Notes
=============

This is the summary list of changes to Girder between each release. For full
details, see the commit logs at https://github.com/girderformindlogger/girderformindlogger

Unreleased
==========

Changes
-------

* Move minimum node version to 8.x due to upstream packages using newer ES features.
  (`#2707 <https://github.com/girderformindlogger/girderformindlogger/pull/2707>`_).
* Require MongoDB 3.4+ (`#2900 <https://github.com/girderformindlogger/girderformindlogger/pull/2900>`_)
* Removed the `@access.cookie` decorator; this is now an option on the other access decorators.

Bug Fixes
---------

Server
^^^^^^
* Fixed a bug where removing admin status from a user via the REST API did not work.
  (`#2720 <https://github.com/girderformindlogger/girderformindlogger/pull/2720>`_).

Web Client
^^^^^^^^^^
* Ensure that a text input doesn't appear after downloading checked items.
  (`#2736 <https://github.com/girderformindlogger/girderformindlogger/pull/2736>`_)

Python Client
^^^^^^^^^^^^^

* Added support for uploading empty files.
  (`#2714 <https://github.com/girderformindlogger/girderformindlogger/pull/2714>`_).

Added Features
--------------
* Google Storage is provisionally supported via S3 Assetstore
  (`#2876 <https://github.com/girderformindlogger/girderformindlogger/pull/2876>`_).

* Added an `NPM_EXE` environment variable and `--npm` flag to `girderformindlogger build` to configure the npm executable used.
  (`#2826 <https://github.com/girderformindlogger/girderformindlogger/pull/2826>`_).

* Added a privacy notice link to the footer which can be set on the Server Configuration view of the web client (
  `#2728 <https://github.com/girderformindlogger/girderformindlogger/pull/2728>`_).

* Added a setting to disable the notification stream. This may improve Girder's performance in runtime environments with
  fewer threads (`#2712 <https://github.com/girderformindlogger/girderformindlogger/pull/2712>`_).

* Added a task information panel that shows remote worker status.  This is accessible from the jobs
  list when the remote worker plugin is enabled and also from the worker plugin configuration page.
  (`#2678 <https://github.com/girderformindlogger/girderformindlogger/pull/2678>`_)

* Allow users to login with two-factor authentication via TOTP on a mobile authenticator app.
  (`#2655 <https://github.com/girderformindlogger/girderformindlogger/pull/2655>`_).

Python Client
^^^^^^^^^^^^^
* Added a ``--token`` option to the girder-client command line interface to allow users to specify
  a pre-created authentication token. (`#2689 <https://github.com/girderformindlogger/girderformindlogger/pull/2689>`_).
* Added a ``--retry`` option to the girder-client command line interface to retry connection and
  certain error responses (`#2697 <https://github.com/girderformindlogger/girderformindlogger/pull/2697>`_).
* Added a ``--verbose`` option to the girder-client command line interface to increase the verbosity
  of information dumped to stderr (`#2699 <https://github.com/girderformindlogger/girderformindlogger/pull/2699>`_).

Web Client
^^^^^^^^^^
* Filesystem and S3 assetstore imports show the selected destination resource path next to the ID when selected via the browser widget (`#2775 <https://github.com/girderformindlogger/girderformindlogger/pull/2775>`_).

Changes
-------

* The Server FUSE plugin has been refactored into the ``girderformindlogger mount`` command.
  Instead of setting a value in the configuration file and turning on a plugin,
  run ``girderformindlogger mount <mount path>`` before or after starting a Girder server.
  (`#2691 <https://github.com/girderformindlogger/girderformindlogger/pull/2691>`_)

Girder 2.5.0
============

Added Features
--------------

* Added a new system setting that will allow admins to disable logging in via a password. If disabled,
  the login dialog in the web client will no longer show the password login form. (`#2504 <https://github.com/girderformindlogger/girderformindlogger/pull/2504>`_)
* Added a new system setting that will allow admins to disable the API key authentication functionality.
  (`#2438 <https://github.com/girderformindlogger/girderformindlogger/pull/2438>`_)
* API endpoint in the hashsum_download plugin that returns a list of files matching a given hash sum.
  (`#2548 <https://github.com/girderformindlogger/girderformindlogger/pull/2458>`_)
* Integration with ``dogpile.cache`` for caching key value pairs via ``girderformindlogger.utility._cache.cache`` and
  ``girderformindlogger.utility._cache.requestCache``. (`#2274 <https://github.com/girderformindlogger/girderformindlogger/pull/2274>`_)
* Plugins can customize the header and description on the Swagger page.
  (`#2607 <https://github.com/girderformindlogger/girderformindlogger/pull/2607>`_)
* Common Girder operations can now be executed with a top level ``girderformindlogger`` command.
  (`#2596 <https://github.com/girderformindlogger/girderformindlogger/pull/2596>`_)
* Added the server FUSE plugin that mounts Girder files in a read-only
  user-space filesystem. (`#2521 <https://github.com/girderformindlogger/girderformindlogger/pull/2521>`_)
* Added support for the ``--host`` flag to ``girderformindlogger serve`` to allow dynamically
  setting the host. (`#2570 <https://github.com/girderformindlogger/girderformindlogger/pull/2570>`_)
* Added support for running the Python test suite via the ``tox`` command.
  (`#2528 <https://github.com/girderformindlogger/girderformindlogger/pull/2528>`_)
* Created a new "virtual folders" plugin. This plugin allows administrators to configure special
  read-only folders whose list of child items comes from a custom, user-defined database query.
  These folders act like database "views" into the item collection.
  (`#2620 <https://github.com/girderformindlogger/girderformindlogger/pull/2620>`_)
* Added a ``File().getLocalFilePath`` method.
  (`#2633 <https://github.com/girderformindlogger/girderformindlogger/pull/2633>`_)
* The stream logger handles more properties.
  (`#2522 <https://github.com/girderformindlogger/girderformindlogger/pull/2522>`_)
* Future-proof for CherryPy removal of response timeouts.
  (`#2487 <https://github.com/girderformindlogger/girderformindlogger/pull/2487>`_)
* Only use new style Python 2 classes.
  (`#2656 <https://github.com/girderformindlogger/girderformindlogger/pull/2656>`_)
* Allow cancellation of raw Celery tasks.
  (`#2602 <https://github.com/girderformindlogger/girderformindlogger/pull/2602>`_)
* Allow assetstore implementations from models besides the assetstore model itself. This enables
  assetstore adapters in plugins to be managed by users who are not necessarily site administrators.
  (`#2599 <https://github.com/girderformindlogger/girderformindlogger/pull/2599>`_)
* Add validation logic to rest endpoint paging parameters. (`#2462 <https://github.com/girderformindlogger/girderformindlogger/pull/2462>`_)
* Add rest endpoint to send user validation email. (`#2622 <https://github.com/girderformindlogger/girderformindlogger/pull/2622>`_)
* Add a search mode registry and a search mode for dicom metedata. (`#2450 <https://github.com/girderformindlogger/girderformindlogger/pull/2450>`_)
* Allow creation of item_tasks tasks from girder_worker describe decorators. (`#2270 <https://github.com/girderformindlogger/girderformindlogger/pull/2270>`_)
* New plugin to allow browsing of Girder data in a tree view. (`#2086 <https://github.com/girderformindlogger/girderformindlogger/pull/2086>`_)

Python Client
^^^^^^^^^^^^^
* Add a method to stream contents of a file download. (`#2476 <https://github.com/girderformindlogger/girderformindlogger/pull/2476>`_)

Web Client
^^^^^^^^^^
* Added a new, more fully-featured view for search results.
  (`#2347 <https://github.com/girderformindlogger/girderformindlogger/pull/2347>`_)
* For added safety, when deleting a collection a user will now be required to type the name of
  the collection into the confirmation dialog.
  (`#2473 <https://github.com/girderformindlogger/girderformindlogger/pull/2473>`_)
* New table_view plugin renders .csv and .tsv files as tables on the item page. (`#2480 <https://github.com/girderformindlogger/girderformindlogger/pull/2480>`_)
* Modal dialogs have a default maximum height and will have a scroll bar if needed.
  (`#2523 <https://github.com/girderformindlogger/girderformindlogger/pull/2523>`_)
* We now use the webpack DefinePlugin to add a build-time definition of the environment. This can
  be used to allow for different build output in production vs. development.
  (`#2631 <https://github.com/girderformindlogger/girderformindlogger/pull/2631>`_)
* Use ``href`` properties for navigation links in addition to JavaScript onclick events. (`#2489 <https://github.com/girderformindlogger/girderformindlogger/pull/2489>`_)
  (`#2578 <https://github.com/girderformindlogger/girderformindlogger/pull/2578>`_)
* Change instances of ``.g-server-config`` to ``.g-server-config a`` to enable adding of ``href`` properties to those links
* Add new methods: ``folder.removeContents``, ``item.getFiles``, ``user.fromTemporaryToken``.
  (`#2615 <https://github.com/girderformindlogger/girderformindlogger/pull/2615>`_)

Swagger Client
^^^^^^^^^^^^^^
* Swagger now expects zip files to be binary data, allowing them to be downloaded through the Web API.
  (`#2562 <https://github.com/girderformindlogger/girderformindlogger/pull/2562>`_)

Testing
^^^^^^^
* ``PYTHONPATH`` can be specified for client tests.
  (`#2535 <https://github.com/girderformindlogger/girderformindlogger/pull/2535>`_)
* Support for writing server-side tests using ``pytest``. (`#2412 <https://github.com/girderformindlogger/girderformindlogger/pull/2412>`_)
    * Added the `pytest-girderformindlogger <https://pypi.python.org/pypi/pytest-girderformindlogger>`_ package for downstream packages.
    * Added support for the ``mongomock`` package in the new ``pytest`` suite.
    * Plugins can be enabled for Pytest. (`#2634 <https://github.com/girderformindlogger/girderformindlogger/pull/2634>`_)
* Flake8 settings are now able to be automatically detected by many editors and IDEs. The ``flake8``
  tool may now be invoked directly from the command line, without necessarily using a CMake test.
  (`#2543 <https://github.com/girderformindlogger/girderformindlogger/pull/2543>`_)
* ESLint settings for plugin tests are now able to be automatically detected by many editors and
  IDEs. The ``eslint`` tool (including options such as ``--fix``) may now be invoked directly from
  the command line, without necessarily using a CMake test.
  (`#2550 <https://github.com/girderformindlogger/girderformindlogger/pull/2550>`_)


Bug fixes
---------
Server
^^^^^^
* Support range requests of S3 non-redirected data handling.  This fixes seeking on S3 assetstore files in the file context handler.  (`#2468 <https://github.com/girderformindlogger/girderformindlogger/pull/2468>`_)
* Pin to a specific version of CherryPy to work around upstream issues on OPTION endpoints.
  (`#2499 <https://github.com/girderformindlogger/girderformindlogger/pull/2499>`_)
* When a plugin supplying an assetstore fails to load, other assetstores could not be listed.
  (`#2498 <https://github.com/girderformindlogger/girderformindlogger/pull/2498>`_)
* Run pip installation of plugins using a subprocess rather than the pip module, for forward compatbility
  with pip. (`#2669 <https://github.com/girderformindlogger/girderformindlogger/pull/2669>`_)
* Correct complex plugin dependencies parsing. (`#2496 <https://github.com/girderformindlogger/girderformindlogger/pull/2496>`_)

Security Fixes
--------------
* The default Girder server now binds to localhost by default instead of 0.0.0.0.
  (`#2565 <https://github.com/girderformindlogger/girderformindlogger/pull/2565>`_)

Changes
-------
* Exceptions are now all accessible in the ``exceptions`` module and are descended from the ``GirderBaseException`` class.
  (`#2498 <https://github.com/girderformindlogger/girderformindlogger/pull/2498>`_)
* Require npm 5.2+ (with npm 5.6+ strongly recommended) to build the web client
* Require MongoDB 3.2+ (`#2540 <https://github.com/girderformindlogger/girderformindlogger/pull/2540>`_)
* Disable the background event thread in WSGI mode. (`#2642 <https://github.com/girderformindlogger/girderformindlogger/pull/2642>`_)
* Update imports of library from "dicom" to "pydicom". (`#2617 <https://github.com/girderformindlogger/girderformindlogger/pull/2617>`_)
* A log message is now emitted whenever a file is uploaded. (`#2571 <https://github.com/girderformindlogger/girderformindlogger/pull/2571>`_)

Deprecations
------------
* Server side tests should be written using the new ``pytest`` infrastructure.
* Move CLI commands to a "cli" module and deprecate "python -m" methods for starting Girder servers. (`#2616 <https://github.com/girderformindlogger/girderformindlogger/pull/2616>`)

Removals
--------
* The CMake options ``PYTHON_COVERAGE``, ``PYTHON_BRANCH_COVERAGE``, and ``PYTHON_COVERAGE_CONFIG`` are removed, and will have no effect if set.
  Python tests will always output coverage information, using a standardized configuration. If external test infrastructure needs to be run with
  different options, it should invoke ``pytest -cov-config ...`` or ``coverage run --rcfile=...`` directly.
  (`#2517 <https://github.com/girderformindlogger/girderformindlogger/pull/2517>`_)
* The CMake options ``COVERAGE_MINIMUM_PASS`` and ``JS_COVERAGE_MINIMUM_PASS`` are removed, and will have no effect if set.
  If external test infrastructure needs to set a coverage threshold, it should be done with a Codecov (or similar service) configuration.
  (`#2545 <https://github.com/girderformindlogger/girderformindlogger/pull/2545>`_)
* The CMake options ``ESLINT_CONFIG_FILE`` and ``ESLINT_IGNORE_FILE`` are removed, and will have no effect if set.
  If external test infrastructure needs to override ESLint configuration,
  `it should be done using ESLint's built-in configuration cascading mechanisms <plugin-development.html#customizing-static-analysis-of-client-side-code>`_.
  Most typical external plugins will continue to work with their current configuration.
* The deprecated ``DELETE /user/password`` endpoint is removed. The ``PUT /user/password/temporary``
  endpoint should always be used to reset passwords, as it uses a secure, token-based password
  mechanism. (`#2621 <https://github.com/girderformindlogger/girderformindlogger/pull/2621>`_)
* Dropped support for Python3 < 3.5. (`#2572 <https://github.com/girderformindlogger/girderformindlogger/pull/2572>`_)

Girder 2.4.0
============

Added Features
--------------
Server
^^^^^^
* Support for S3 buckets in regions other than us-east-1. (`#2153 <https://github.com/girderformindlogger/girderformindlogger/pull/2153>`_)
* Allow S3 credentials to be inferred by Boto. (`#2229 <https://github.com/girderformindlogger/girderformindlogger/pull/2229>`_)
* ``girder-shell`` console script which drops the user into a python repl with a configured webroot, giving the user the ability to import from any of the plugins specified. (`#2141 <https://github.com/girderformindlogger/girderformindlogger/pull/2141>`_)
* Support for configuration of pymongo client options as Girder config file options. (`#2380 <https://github.com/girderformindlogger/girderformindlogger/pull/2380>`_)
* Support for idiomatic use of Girder's model classes. Rather than using ``ModelImporter.model`` with strings for the model and plugin names, you can now use python imports of the model classes and instantiate and use them directly. (`#2376 <https://github.com/girderformindlogger/girderformindlogger/pull/2376>`_)
* Support for mounting REST endpoints under a prefix. Useful for grouping related endpoints, such as those exposed by a plugin. (`#2395 <https://github.com/girderformindlogger/girderformindlogger/pull/2395>`_)
* Option in worker task input specs to use local file paths in the worker when available, to avoid downloading files. (`#2356 <https://github.com/girderformindlogger/girderformindlogger/pull/2356>`_)
* Core setting allowing the instance brand name to be set. (`#2283 <https://github.com/girderformindlogger/girderformindlogger/pull/2283>`_)
* Core setting allowing the instance contact email address to be set. (`#2279 <https://github.com/girderformindlogger/girderformindlogger/pull/2279>`_)
* Core setting allowing the GUI header color to be set. (`#2334 <https://github.com/girderformindlogger/girderformindlogger/pull/2334>`_)
* “terms” plugin, which provides the option to require users to agree to a “Terms of Use” before accessing a collection. (`#2138 <https://github.com/girderformindlogger/girderformindlogger/pull/2138>`_)
* Improve the “homepage” plugin’s capabilities for making in-place changes to the home page. (`#2328 <https://github.com/girderformindlogger/girderformindlogger/pull/2328>`_)
* API endpoint, “/user/details”, allowing site admins to list the total number of users. (`#2262 <https://github.com/girderformindlogger/girderformindlogger/pull/2262>`_)
* Job cancellation support to Girder Worker jobs. (`#1983 <https://github.com/girderformindlogger/girderformindlogger/pull/1983>`_)
* Accept metadata on item and folder creation via the REST API. (`#2259 <https://github.com/girderformindlogger/girderformindlogger/pull/2259>`_)
* Allow ``girder-install plugin`` to get dependencies from a ``setup.py`` file. (`#2370 <https://github.com/girderformindlogger/girderformindlogger/pull/2370>`_)
* Create a registry for adding new search modes. (`#2363 <https://github.com/girderformindlogger/girderformindlogger/pull/2363>`_)

Web Client
^^^^^^^^^^
*  Published the Girder client side code as an npm package (https://www.npmjs.com/package/girderformindlogger). (`#2242 <https://github.com/girderformindlogger/girderformindlogger/pull/2242>`_)

Python Client
^^^^^^^^^^^^^
* Support for turning off certificate checking with ``--no-ssl-verify``. (`#2433 <https://github.com/girderformindlogger/girderformindlogger/pull/2433>`_)
* Support for specifying a custom certificate with ``--certificate``. (`#2267 <https://github.com/girderformindlogger/girderformindlogger/pull/2267>`_)
* Support for downloading individual files. (`#2429 <https://github.com/girderformindlogger/girderformindlogger/pull/2429>`_)

DevOps
^^^^^^
* Added a Terraform module for creating an S3 bucket compliant with Girder assetstore policies. (`#2267 <https://github.com/girderformindlogger/girderformindlogger/pull/2267>`_)
* Published a latest-py3 tag to Dockerhub for Girder images built with Python 3. (`#2321 <https://github.com/girderformindlogger/girderformindlogger/pull/2321>`_)

Deprecations
------------
Python Client
^^^^^^^^^^^^^
* ``requests.HTTPError`` should be caught in places where ``girder_client.HttpError`` used to. (`#2223 <https://github.com/girderformindlogger/girderformindlogger/pull/2223>`_)

Bug fixes
---------
Server
^^^^^^
* Fixed an error where certain filenames could cause broken Content-Disposition header values. (`#2330 <https://github.com/girderformindlogger/girderformindlogger/pull/2330>`_)
* AccessControlledModel.load ``fields`` argument now works more reliably. (`#2366 <https://github.com/girderformindlogger/girderformindlogger/pull/2366>`_, `#2352 <https://github.com/girderformindlogger/girderformindlogger/pull/2352>`_)
* Fixed an issue where the events daemon was failing to terminate correctly. (`#2379 <https://github.com/girderformindlogger/girderformindlogger/pull/2379>`_)

Web Client
^^^^^^^^^^
* Remove Bootstrap re-styling of tooltips. (`#2406 <https://github.com/girderformindlogger/girderformindlogger/pull/2406>`_)

DevOps
^^^^^^
* Fixed an issue which disallowed provisioning with the Girder Ansible module under Python 3. (`#2449 <https://github.com/girderformindlogger/girderformindlogger/pull/2449>`_)

Girder 2.3.0
============

Bug fixes
---------

* Fix uploading into HDFS assetstore using new upload mode

Security Fixes
--------------

* Ensure token scopes on API keys are valid
* Add secure cookie setting
* Upgrade swagger-ui version to fix XSS issues

Added Features
--------------

* Add REST endpoint for creating job models
* Add graphs for Jobs status history to Admin UI
* Improvements to item_tasks job execution, task import, task lists, and permission flag UIs
* Show plugin load failures on plugins page
* Add Candela plugin
* Compute missing hashes when files are uploaded, and allow for hashsum calculation for non-filesystem assetstore files
* Add support for running Girder in AWS Elastic Beanstalk
* Upgrade S3 assetstore to Boto3
* Add LDAP authentication plugin
* Send all http server errors to the error log
* Added an event when the web client connection to the server is stopped or started
* Support uploading small files in a single REST call
* Improved GridFS support, including better sharding support and faster writes
* Add a Description method to mark a route as deprecated
* Many improvements to the web client test infrastructure including

  * A new CMake macro, `add_standard_plugin_tests`, to enable basic tests for a typical plugin layout
  * A new `girderTest.importPlugin` function, to load plugin JS and CSS in web client tests
  * A static analysis test for Stylus files
  * New rules for Javascript and Pug static analysis tests

* A facility to initialize the database to a specific state for testing

Changes
-------

* Upgrade web client to use jQuery 3
* Upgrade web client to use Backbone 1.3
* Require Node.js 6.5+ and npm 3.10+ (with npm 5.3 strongly recommended) to build the web client

Deprecations
------------

* job Plugin: Python Job model `listAll` method
* hashsum_download plugin: Python `HashedFile.supportedAlgorithms` symbol
* item_tasks plugin: `item_task_json_description` and `item_task_json_specs` routes
* `module.loaders` in webpack helper files, and the use of Webpack 1.0 syntax in plugins' webpack helper files
* `restRequest.error` in rest.js
* `npm-install` in client side build
* `girderTest.addCoveredScript` and `girderTest.addCoveredScripts` in testUtilities.js
* access to file paths outside `/static/built/` in the web client test environment

Removals
--------

* Remove the unmaintained external web client
* Remove the unmaintained jQuery "girderBrowser" client, and associated "jquery_widgets" plugin

.. |schema-standardization→reproschema| replace:: ``schema-standardization`` → ``reproschema``
.. |activitySet→protocol| replace:: ``activity-sets`` → ``protocols``
.. |1c54072| replace:: ReproNim/schema-standardization@``1c54072``
