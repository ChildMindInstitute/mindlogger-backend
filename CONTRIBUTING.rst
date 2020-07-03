Contributing to Girder for MindLogger
=====================================

1. Check the `open issues for this repository <https://github.com/ChildMindInstitute/mindlogger-app-backend/issues>`_, `open bug reports <https://github.com/ChildMindInstitute/MindLogger-bug-reports/issues>`_, and `the overall project 看板 <https://github.com/orgs/ChildMindInstitute/projects/9>`_ for known issues and discussions.
2. If your issue is not already listed, add your issue, optionally with :octocat: `gitmoji <https://gitmoji.carloscuesta.me/>`_.
3. Clone this repository.
4. If your issue already has a discussion, see if it has a branch. If so, checkout that branch before creating your own.
5. Create a new branch to work in.
6. When you’re ready to submit your changes, submit a pull request from your branch to the branch you branched  from (ie, the branch you checked out in step 4 above or ``master``).
7. One or more of the project developers will review your request and merge or request changes.

Versioning
----------

Use `Semantic Versioning 2.0.0 <https://semver.org/#semantic-versioning-200>`_. Always develop in a feature-specific branch.

Pull requests
-------------

Each pull request (PR) requires a review from at least one contributor other than the author of that PR.

Submitting a PR
~~~~~~~~~~~~~~~

1. Update `the CHANGELOG <./CHANGELOG.rst>`_ with a brief description of the changes in this new version.
2. From your branch, open a pull request to `master <https://github.com/ChildMindInstitute/mindlogger-app-backend/tree/master>`_.
3. Give your PR a descriptive title, optionally with :octocat: `gitmoji <https://gitmoji.carloscuesta.me/>`_.
4. Give a brief but thorough description of what your PR does.
5. Submit. `Circle CI <https://circleci.com/gh/ChildMindInstitute/mindlogger-app-backend>`_ will run :microscope: tests.
6. If no other pull requests are pending and you have adequate permissions to deploy to the development server, `deploy to the development server <#deploy-to-dev>`_ and add a note to your PR that you have done so.
7. Wait for a review.
8. Respond to the review if necessary.


Reviewing a PR
--------------

1. Review the description.
2. Test the branch and verify that the changes work as expected.
3. Verify that the `CHANGELOG <./CHANGELOG.rst>`_ has been adequately updated.
4. If any changes are necessary, request those changes.
5. Otherwise, or once the necessary changes are made, approve the PR.
6. Merge the PR (usually via a merge commit, but by a merge squash or a merge rebase by discretion).
7. Tag the master branch with an `updated version <#versioning>`_.


Deployment
----------
We are deploying through Amazon Web Services Elastic Beanstalk. To deploy, you'll need write access to the instance you're deploying to. For the process described in this document, you'll also need `the Elastic Beanstalk Command Line Interface (EB CLI) <https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/eb-cli3-install.html>`_.

You'll also need a Python virtual environment with setuptools. Instructions for setting up a virtual environment are `in this repository's README <./README.rst#installation>`_.

Elastic Beanstalk relies on Git and a local installation, so prior to deploying, you'll need to have a local installation with the latest tag and a named branch.

**Note:** *EB does not allow non-ASCII characters in the name of the branch or the latest commit message title from which it deploys.*

Deploy to dev
~~~~~~~~~~~~~

1. From the branch you want to deploy, create a temporary Git tag (typically the upcoming semver plus a hyphen and a suffix, eg, ``v0.7.4-contributing``).

   .. code-block:: sh

     git tag v0.7.4-contributing

2. Activate your **Girder for MindLogger** virtual environment.

   .. code-block:: sh

     ~/girder_env/bin/activate

3. Install **Girder for MindLogger** locally.

   .. code-block:: sh

     pip install -e .

4. Build **Girder for MindLogger** locally.

   .. code-block:: sh

     girderformindlogger build

5. Deactivate your virtual environment.

   .. code-block:: sh

     deactivate

6. Use EB CLI to deploy to the development server. Our development server instance is labeled `mindlogger-atlas-dev <https://console.aws.amazon.com/elasticbeanstalk/home?region=us-east-1#/environment/dashboard?applicationName=mindlogger_mongo_atlas&environmentId=e-cmi89zpeqn>`_.

   .. code-block:: sh

     eb deploy mindlogger-atlas-dev


Deploy to production
~~~~~~~~~~~~~~~~~~~~
1. Fetch tags from GitHub. (This example assumes your remote repository is named
   ``origin``).

   .. code-block:: sh

     git fetch origin --tags

2. Check out the latest tag, ie, the tag of the ``master`` branch's ``HEAD``,
   eg, ``v0.9.10`` in this example.

   .. code-block:: sh

     git checkout v0.9.10

3. Check out a local branch to deploy from. The name doesn't matter as long as
   the branch has a name with only ASCII characters.

   .. code-block:: sh

     git checkout -b deployment-example-v.0.9.10

4. Activate your **Girder for MindLogger** virtual environment.

   .. code-block:: sh

     ~/girder_env/bin/activate


5. Install **Girder for MindLogger** locally.

   .. code-block:: sh

     pip install -e .

6. Build **Girder for MindLogger** locally.

   .. code-block:: sh

     girderformindlogger build

7. Deactivate your virtual environment.

   .. code-block:: sh

     deactivate

8. Use EB CLI to deploy to the production server. Our production server
   instance is labeled `mindlogger-girder-atlas <https://console.aws.amazon.com/elasticbeanstalk/home?region=us-east-1#/environment/dashboard?applicationName=mindlogger_mongo_atlas&environmentId=e-vhc2nxivk7>`_.

   .. code-block:: sh

     eb deploy mindlogger-girder-atlas


Contributing to Girder (upstream project)
=========================================

There are many ways to contribute to Girder, with varying levels of effort.  Do try to
look through the documentation first if something is unclear, and let us know how we can
do better.

- Ask a question on the `Girder Discourse <https://discourse.girderformindlogger.org/>`_
- Ask a question in the `Gitter Forum <https://gitter.im/girderformindlogger/girderformindlogger>`_
- Submit a feature request or bug, or add to the discussion on the `Girder issue tracker <https://github.com/girderformindlogger/girderformindlogger/issues>`_
- Submit a `Pull Request <https://github.com/girderformindlogger/girderformindlogger/pulls>`_ to improve Girder or its documentation

We encourage a range of contributions, from patches that include passing tests and
documentation, all the way down to half-baked ideas that launch discussions.

The PR Process, CircleCI, and Related Gotchas
---------------------------------------------

How to submit a PR
~~~~~~~~~~~~~~~~~~

If you are new to Girder development and you don't have push access to the Girder
repository, here are the steps:

1. `Fork and clone <https://help.github.com/articles/fork-a-repo/>`_ the repository.
2. Create a branch.
3. `Push <https://help.github.com/articles/pushing-to-a-remote/>`_ the branch to your GitHub fork.
4. Create a `Pull Request <https://github.com/girderformindlogger/girderformindlogger/pulls>`_.

This corresponds to the ``Fork & Pull Model`` mentioned in the
`GitHub flow <https://guides.github.com/introduction/flow/index.html>`_ guides.

If you have push access to Girder repository, you could simply push your branch
into the main repository and create a `Pull Request <https://github.com/girderformindlogger/girderformindlogger/pulls>`_. This
corresponds to the ``Shared Repository Model`` and will facilitate other developers to checkout your
topic without having to `configure a remote <https://help.github.com/articles/configuring-a-remote-for-a-fork/>`_.
It will also simplify the workflow when you are *co-developing* a branch.

When submitting a PR, make sure to add a ``Cc: @girder/developers`` comment to notify Girder
developers of your awesome contributions. Based on the
comments posted by the reviewers, you may have to revisit your patches.

Automatic testing of pull requests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When you submit a PR to the Girder repo, CircleCI will run the build and test suite on the
head of the branch. If you add new commits onto the branch, those will also automatically
be run through the CI process. The status of the CI process (passing, failing, or in progress) will
be displayed directly in the PR page in GitHub.

The CircleCI build will run according to the `circle.yml file <https://github.com/girderformindlogger/girderformindlogger/blob/master/circle.yml>`_,
which is useful as an example for how to set up your own environment for testing.

Your test results will be posted on `Girder's CircleCI dashboard <https://circleci.com/gh/girderformindlogger>`_.
These results will list any failed tests. Coverage reports and any screenshots
from failed web client tests will be attached to the build as artifact files. You can reach your
build by clicking the build status link on your GitHub PR.

Tracking Public Symbols
^^^^^^^^^^^^^^^^^^^^^^^

Adding new public symbols to Girder's python library should only be done intentionally, as doing so
increases the surface of the API and introduces a maintenance burden. Public symbols are packages,
modules, and symbols within those modules that do not start with an underscore character. To help
with this goal, public symbol addition and removal is tracked automatically as part of our CI
process, with the full list of symbols residing in ``scripts/publicNames.txt``

Any PR that adds new public symbols must regenerate the ``scripts/publicNames.txt`` file. This is
done by running the following script::

    python scripts/publicNames.py > scripts/publicNames.txt

Changes to the file should be committed as a part of the PR or not all CI tests will pass.


How to integrate a PR
^^^^^^^^^^^^^^^^^^^^^

Getting your contributions integrated is relatively straightforward, here is the checklist:

- All tests pass
- Public symbols list is updated in ``scripts/publicNames.txt``
- Any significant changes are added to the ``CHANGELOG.rst`` with human-readable and understandable
  text (i.e. not a commit message). Text should be placed in the "Unreleased" section, and grouped
  into the appropriate sub-section of:

  - Bug fixes
  - Security fixes
  - Added features
  - Changes
  - Deprecations
  - Removals

- Consensus is reached. This requires that a reviewer adds an "approved" review via GitHub with no
  changes requested, and a reasonable amount of time passed without anyone objecting.

Next, there are two scenarios:

- You do NOT have push access: A Girder core developer will integrate your PR.
- You have push access: Simply click on the "Merge pull request" button.

Then, click on the "Delete branch" button that appears afterward.
