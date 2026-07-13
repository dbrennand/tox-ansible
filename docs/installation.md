# Installation

> Need help or want to discuss the project? See our [Contributor guide](https://ansible.readthedocs.io/projects/tox-ansible/contributor_guide/#talk-to-us) to join the conversation!

Getting started with tox-ansible is as simple as:

```bash
pip install tox-ansible
```

## Dependencies

`tox-ansible` will install additional dependencies where they are needed:

- `tox` version 4.0 or greater.
- `pytest-ansible`, `pytest`, and `pytest-xdist` for unit environments
- `pytest-cov` when unit test coverage is enabled
- `molecule` for integration environments
- `pyyaml`

Each generated test environment will also install:

- `ansible-dev-environment` (ade) -- handles collection installation, ansible-core versioning, and Python dependency resolution.

Molecule drivers are optional and are not inferred from scenario configuration. Declare drivers and other integration Python packages in `tests/integration/requirements.txt`, for example `molecule-plugins[docker]`.
