## 0.1.20 (2025-02-06)

### Fix

- Bump some dependencies for CVE fixes and pin anyio

## 0.1.19 (2025-01-25)

### Fix

- Update crontab dependency

## 0.1.18 (2024-11-20)

### Fix

- Remove result size check
- Ensure metrics data points sorted by timestamp

## 0.1.17 (2024-10-03)

### Fix

- Support passing runtime env config for ray executor

## 0.1.16 (2024-08-29)

### Fix

- if user is skipping DB, then user also doesnt care about the response cap

## 0.1.15 (2024-08-27)

### Fix

- Bump mkdocstrings and ensure runtime image uses bookworm

## 0.1.14 (2024-08-27)

### Fix

- Update to bookworm base docker image

## 0.1.13 (2024-08-26)

### Fix

- add libz-dev to apt-get install

## 0.1.12 (2024-08-26)

### Fix

- bump pyarrow

## 0.1.11 (2024-08-26)

### Fix

- pin numpy
- bump Ray and llvmlite

## 0.1.10 (2024-04-17)

### Fix

- bump semver to version 3

## 0.1.9 (2024-04-10)

### Fix

- Add new dask expr as valid types in dask collection methods
- Ensure new dask dataframes are registered in collections logic
- bump dask

## 0.1.8 (2024-04-04)

### Fix

- update poetry.lock

## 0.1.7 (2024-04-04)

### Fix

- Remove excess dtos in configs api

## 0.1.6 (2024-04-01)

### Fix

- Ensure mappers resource is included in local executor if not specified

## 0.1.5 (2024-03-31)

### Fix

- Fix bug with default configuration and run_retention_duration

## 0.1.4 (2024-03-22)

### Fix

- ensure we document how to configure the Cluster Memory Actor, bump Ray to 2.10.0, push poetry.lock
- Fix unit tests for ray cluster memory
- Add support for controlling ray cluster memory actor placement
- Fix bug in local executor cluster memory and add object store strategy

## 0.1.3 (2024-02-13)

### Fix

- improve the paperboy example, add comments for how scaling up could be considered

## 0.1.2 (2024-02-10)

### Fix

- **ci**: Ensure latest tags are built on tag pipelines

## 0.1.1 (2024-02-10)

### Fix

- Reinstante flowml bundled docker images and include README

## 0.1.0 (2024-02-10)

### Feat

- Initial project setup :tada:
