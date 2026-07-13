# Usage of tox-ansible

> Need help or want to discuss the project? See our [Contributor guide](https://ansible.readthedocs.io/projects/tox-ansible/contributor_guide/#talk-to-us) to learn how to join the conversation!

## Getting started

From the root of your collection, add a `[tool.tox-ansible]` section to your `pyproject.toml` (the section can be empty if no skip filters are needed):

```toml
# pyproject.toml
[tool.tox]
requires = ["tox>=4.2"]

[tool.tox-ansible]
```

Then list the available environments:

```bash
tox list --ansible
```

A list of dynamically generated Ansible environments will be displayed:

```

default environments:
...
integration-py3.11-2.14      -> Integration tests for ansible.scm using ansible-core 2.14 and python 3.11
integration-py3.12-devel     -> Integration tests for ansible.scm using ansible-core devel and python 3.11
...
sanity-py3.11-2.14           -> Sanity tests for ansible.scm using ansible-core 2.14 and python 3.11
sanity-py3.12-devel          -> Sanity tests for ansible.scm using ansible-core devel and python 3.11
...
unit-py3.11-2.14             -> Unit tests for ansible.scm using ansible-core 2.14 and python 3.11
unit-py3.12-devel            -> Unit tests for ansible.scm using ansible-core devel and python 3.11
```

These represent the available testing environments. Each denotes the type of tests that will be run, the Python interpreter used to run the tests, and the Ansible version used to run the tests.

To run tests with a single environment, simply run the following command:

```bash
tox -e sanity-py3.11-2.14 --ansible
```

To run tests with multiple environments, simply add the environment names to the command:

```bash
tox -e sanity-py3.11-2.14,unit-py3.11-2.14 --ansible
```

To run all tests of a specific type in all available environments, use the factor `-f` flag:

```bash
tox -f unit --ansible -p auto
```

To run all tests across all available environments:

```bash
tox --ansible -p auto
```

Note: The `-p auto` flag will run multiple tests in parallel.
Note: The specific Python interpreter will need to be pre-installed on your system, e.g.:

```bash
sudo dnf install python3.9
```

To review the specific commands and configuration for each of the integration, sanity, and unit factors:

```bash
tox config --ansible
```

Generate specific GitHub action matrix as per scope mentioned with `--matrix-scope`:

```bash
tox --ansible --gh-matrix --matrix-scope unit
```

A list of dynamically generated Ansible environments will be displayed specifically for unit tests:

```
[
  {
    "description": "Unit tests using ansible 2.9 and python 3.8",
    "factors": [
      "unit",
      "py3.8",
      "2.9"
    ],
    "name": "unit-py3.8-2.9",
    "python": "3.8"
  },
  ...
  {
    "description": "Unit tests using ansible-core milestone and python 3.12",
    "factors": [
      "unit",
      "py3.12",
      "milestone"
    ],
    "name": "unit-py3.12-milestone",
    "python": "3.12"
  }
]
```

!!! note "Using tox-ansible.ini"
    If your project uses `tox-ansible.ini` instead of `pyproject.toml`, add `--conf tox-ansible.ini` to every tox command:

    ```bash
    tox list --ansible --conf tox-ansible.ini
    tox -e unit-py3.13-2.19 --ansible --conf tox-ansible.ini
    ```

    See the [Configuration](configuration.md) page for details on both approaches.

<!-- cspell:ignore prerun -->

## Passing command line arguments to test runners

Arguments after `--` are forwarded to the environment's runner: `ansible-test` for `sanity-*`, pytest for `unit-*`, and Molecule for `integration-*`.

```bash
tox -f sanity --ansible -- --test validate-modules -vvv
```

The arguments after the `--` will be passed to the `ansible-test` command. Thus in this example, only the `validate-modules` sanity test will run, but with an increased verbosity.

The same applies to pytest unit environments:

```bash
tox -e unit-py3.13-2.19 --ansible -- --junit-xml=tests/output/junit/unit.xml
```

Molecule options retain their original order. All scenarios run by default, including when options such as `--workers` are supplied:

```bash
tox -e integration-py3.13-2.19 --ansible -- --workers 4
```

Select scenarios with `-s` or `--scenario-name`; an explicit selection replaces the default `--all`:

```bash
tox -e integration-py3.13-2.19 --ansible -- -s default
```

## Unit test coverage

Use `--coverage` to generate a coverage report for Python files in the collection's `plugins/` directory while running unit tests:

```bash
tox -e unit-py3.13-2.19 --ansible --coverage
```

tox-ansible installs `pytest-cov` and generates the required path mappings automatically, including the collection-specific installation path created by Ansible Dev Environment. Eligible Python files below `plugins/` that the unit tests do not import appear with 0% coverage. The collection does not need a `.coveragerc` or a custom unit test command.

Each unit environment stores its raw coverage data in its own tox environment directory. Parallel environments therefore produce independent reports; tox-ansible does not automatically combine results across the Python and ansible-core matrix.

Coverage can also be enabled persistently with `coverage = true` in `[tool.tox-ansible]` in `pyproject.toml` or `[ansible]` in `tox-ansible.ini`. See the [Configuration](configuration.md#unit-test-coverage) page for examples and precedence rules.

Additional pytest-cov options can be passed after `--`, for example:

```bash
tox -e unit-py3.13-2.19 --ansible --coverage -- --cov-report=xml
```

## Usage in a CI/CD pipeline

A GitHub Actions matrix is dynamically created by `tox-ansible` using the `--gh-matrix` and `--ansible` flags. The list of environments is converted to a list of entries in json format which is stored under the `envlist` key in the file specified by the `GITHUB_OUTPUT` environment variable.

Below shows relevant snippets from a GitHub Action workflow which:

1. Uses the `--gh-matrix` flag to generate a list of environments.
2. Creates individual jobs for each environment using a [matrix strategy](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/run-job-variations).

!!! note

    This is not a production ready GitHub Action workflow. It is missing key steps for readability purposes. You will need to set up Python and install `tox-ansible` in your GitHub Action workflow.

```yaml
# .github/workflows/tox-ansible.yml
name: Tox Ansible
# ...
jobs:
  generate-matrix:
    # ...
    outputs:
      envlist: ${{ steps.matrix.outputs.envlist }}
    steps:
      # ...
      - name: Generate matrix
        id: matrix
        run: |
          tox --ansible --conf tox-ansible.ini --gh-matrix

  tox-ansible:
    needs: generate-matrix
    # ...
    strategy:
      fail-fast: false
      matrix:
        env: ${{ fromJSON(needs.generate-matrix.outputs.envlist) }}
    steps:
      # ...
      - name: Run tox environment ${{ matrix.env.name }}
        run: |
          tox --ansible --conf tox-ansible.ini -e ${{ matrix.env.name }}
```

## Skip functionality

Circumstances may require certain tests to be skipped. `tox-ansible` supports skipping tests via `skip` in `[tool.tox-ansible]` (pyproject.toml) or `[ansible]` (tox-ansible.ini).

Example for `pyproject.toml`:

```toml
# pyproject.toml
[tool.tox-ansible]
skip = sanity-py3.13
```

Example for `tox-ansible.ini`:

```ini
# tox-ansible.ini
[ansible]
skip =
    sanity-py3.13
```

## Testing Molecule scenarios

Every `integration-*` environment invokes Molecule directly. One tox environment covers every scenario that Molecule discovers through its collection-aware `extensions/molecule/` layout; Molecule remains authoritative for discovery, ordering, shared state, concurrency, and failures. If no scenarios are found, the environment fails with Molecule's diagnostic.

Before Molecule runs, ADE installs the collection and Ansible collection dependencies. Tox-ansible therefore generates an environment-specific base configuration under `.tox/.tox-ansible/molecule/` containing:

```yaml
---
prerun: false
```

This avoids duplicating ADE's installation work. A scenario can explicitly set `prerun: true`; scenario configuration has higher precedence and may intentionally repeat that work. Existing Molecule base configuration is preserved using Molecule's normal priority: repository `.config/molecule/config.yml`, collection `extensions/molecule/config.yml`, then user `~/.config/molecule/config.yml`.

Use the following dependency files for integration tests:

- `tests/integration/requirements.yml` for Ansible collections.
- `tests/integration/requirements.txt` for Python packages, including Molecule drivers and verifier packages.

Tox-ansible installs Molecule automatically but does not inspect `molecule.yml` to infer optional driver packages. For example, a Docker scenario should declare `molecule-plugins[docker]` in `tests/integration/requirements.txt`.

### Migrating from the pytest adapter

The `pytest_ansible.molecule.MoleculeScenario` adapter test previously recommended by tox-ansible is no longer needed for integration environments. Remove that adapter test and keep the scenarios under `extensions/molecule/`; Molecule will discover and execute them directly.

Tox-ansible keeps its complete ansible-core matrix. Molecule's upstream support policy may cover fewer combinations, and unsupported combinations are not silently filtered.
