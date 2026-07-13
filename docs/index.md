# Tox Ansible Documentation

> Need help or want to discuss the project? See our [Contributor guide](https://ansible.readthedocs.io/projects/tox-ansible/contributor_guide/#talk-to-us) to join the conversation!

## About Tox Ansible

`tox-ansible` is a utility designed to simplify the testing of ansible content collections.

Implemented as `tox` plugin, `tox-ansible` provides a simple way to test ansible content collections across multiple python interpreter and ansible versions.

`tox-ansible` uses `tox` to create and manage testing environments, `ansible-test sanity` to run sanity tests, `pytest` to run unit tests, and Molecule to run integration scenarios.

When used on a local development system, each of the environments are left intact after a test run. This allows for easy debugging of failed tests for a given test type, python interpreter and ansible version.

By using `tox` to create and manage the testing environments, Test outcomes should always be the same on a local development system as they are in a CI/CD pipeline.

`tox` virtual environments are created in the `.tox` directory. These are easily deleted and recreated if needed.
