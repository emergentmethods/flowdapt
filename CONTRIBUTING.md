# Contributor Guide

This guide is intended for developers of Flowdapt, people who want to contribute to the Flowdapt codebase or documentation, or people who want to understand the source code of the application they're running.

There are a few things you can do ensure your environment is ready for development on Flowdapt. First, ensure that you have `uv` installed on your system. For more details on how to install `uv`, see the [Poetry documentation](https://docs.astral.sh/uv/getting-started/installation/).

Next, clone the repo and create the virtual environment:

```bash
git clone https://github.com/emergentmethods/flowdapt.git
cd flowdapt
python3 -m venv .venv
source .venv/bin/activate
```

Then, install the dependencies:

```bash
uv sync
```

Finally, install the pre-commit hooks:

```bash
pre-commit install --install-hooks && pre-commit install --hook-type commit-msg
```

These are required to ensure that the code is formatted correctly and that the tests pass before committing. If you NEED to skip the pre-commit hooks, you can use the `--no-verify` flag when committing. However CI will still run the hooks and fail if they do not pass.

## Commit messages

Commit messages should follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification (specifically the Angular convention). This allows us to automatically generate changelogs and version numbers for releases. The commit message should be in the following format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

## Changes to dependencies

Any changes to dependencies, such as adding one, removing, or upgrading a version should always be followed by `poetry lock --no-update`. This ensures each installation of flowdapt always has the exact libraries and packages required for running. Changes to the `poetry.lock` should be in it's own commit with a message similar to `chore(dependencies): added attrs package`. This ensures we can always test changes to the dependencies and verify the application still works how it should.

## Changes to the Rest API

This guide outlines the procedure for introducing changes to the flowdapt/services REST API.

### Preliminary Notes

When making alterations to the REST API interface of any services, or to the Data Transfer Objects (DTOs) that the API uses in any of the schema modules, it's essential to regenerate the OpenAPI spec. Once the new specification has been generated, you need to create a merge request (MR) against the SDK repository containing the modified specification. Upon approval and merging of this MR, new SDKs will be generated and published.

To regenerate the specification, use the dev command:

```bash
flowdapt dev spec
```

### Part 1: Introducing Changes

1. **Create a new feature branch in the flowdapt repository**: After making changes to the REST API endpoints, generate the new specification using `flowdapt dev spec`. If a new service has been created, ensure its information is added to the code for dev spec so it is included when generating the new specification.

2. **Replicate changes to the SDK repository**: Create a new feature branch in the corresponding SDK repository (it is best if they are done in the Python SDk first to allow flowctl access to the changes). Implement the changes in the SDK to match the new specification. This may involve adding new endpoints, modifying existing ones, or altering the DTOs. Once the changes are made, push the feature branch to the SDK repository. This isn't required if the changes to flowdapt have not been merged yet, however we like to keep the SDK up to date with the flowdapt changes.

3. **Make necessary changes in the flowctl repository**: Create a new feature branch in the flowctl repository corresponding to the one in the flowdapt repository. Implement the changes in the flowctl repository to match the new specification. This may involve adding new commands, modifying existing ones, or altering the DTOs. Once the changes are made, push the feature branch to the flowctl repository. This step can not happen until flowdapt and the python SDK have been merged to main.

5. **Approval and merging**: Once the flowdapt merge request (MR) is approved and merged to main, the SDK MR can also be approved and merged. Subsequently, the flowctl MR can be reviewed and then merged. The first two steps are required to be merged before the third can be merged.

### Part 2: Utilizing a Feature Branch with SDK Changes

1. **Pull the feature branches**: Import each feature branch to your local clones. For instance, flowdapt, SDK, flowctl. Remember, sometimes API changes in flowdapt may not come with flowctl and SDK changes yet.

2. **Setup development environment**: Ensure that the flowdapt, SDK, and flowctl repositories are installed in development mode. This can be done by running `poetry install` in each repository. Sometimes it is necessary to change where poetry gets the package from, so you can update the `pyproject.toml` file to point to the local directory if necessary.

3. **Use the updated flowctl with the new flowdapt server**: Most of the time (about 95%), things should remain backwards compatible, so you can continue to use the new flowctl even with an older version of flowdapt. MR's should make note of any breaking changes otherwise.


## Coverage report

Coverage reports can be generated by ensuring the module `coverage` is installed and then executing:

```bash
coverage run --source=flowdapt/ -m pytest flowdapt/test/
coverage html -d coverage-report
```

which will run the unit tests and then create a folder with detailed summary information about the code coverage. Flowdapt includes a Taskfile with commands that make it easy to perform these tasks. For example, to run the tests and generate the coverage report, you can run:

```bash
task unit-tests
```