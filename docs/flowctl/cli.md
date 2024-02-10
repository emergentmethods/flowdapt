# `flowctl`

The CLI tool for managing Flowdapt.

**Usage**:

```bash
$ flowctl [OPTIONS] COMMAND [ARGS]...
```

**Options**:

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `--version, -v` | boolean | Show the flowctl version and exit. | **False** |
| `--app-dir` | path | The application directory to use.Defaults to the Flowdapt app directory. | **None** |
| `--config, -c` | text | The path to the configuration file relative to the application configs directory. | **flowctl.yaml** |
| `--env` | text | Load a .env file in the configuration. | **[]** |
| `--dev` | boolean | Run flowctl in development mode. | **False** |
| `--server, -s` | text | The Flowdapt server to connect to. Can be the server name or URL. | **** |
| `--install-completion` | choice (`bash` &#x7C; `zsh` &#x7C; `fish` &#x7C; `powershell` &#x7C; `pwsh`) | Install completion for the specified shell. | **None** |
| `--show-completion` | choice (`bash` &#x7C; `zsh` &#x7C; `fish` &#x7C; `powershell` &#x7C; `pwsh`) | Show completion for the specified shell, to copy it or customize the installation. | **None** |
| `--help` | boolean | Show this message and exit. | **False** |

**Commands**:

* `apply`: Apply one or more resource definition files.
* `config`: Commands for managing flowctl configuration.
* `delete`: Delete one or more resources of a specific kind.
* `get`: Get one or more resources of a specific kind.
* `inspect`: Describe a resource of a specific kind.
* `metrics`: Get information about the metrics of the server.
* `patch`: Patch a Resource given a kind, identifier, and set of options.
* `run`: Execute a Workflow by identifier with an optional input.
* `status`: Get the status of the Flowdapt server.

---

## `flowctl apply`

Apply one or more resource definition files.

**Usage**:

```bash
$ flowctl apply [OPTIONS]
```

**Options**:

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `--path, -p` | path | The path to a file or directory containing the resource(s) to apply. | **None** |
| `--help` | boolean | Show this message and exit. | **False** |

---

## `flowctl config`

**Usage**:

```bash
$ flowctl config [OPTIONS] COMMAND [ARGS]...
```

**Options**:

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `--help` | boolean | Show this message and exit. | **False** |

**Commands**:

* `add`: Add a server to the configuration.
* `current`: Get the current server.
* `get`: Get the specified key from the configuration file.
* `remove`: Remove a server from the configuration.
* `set`: Set the specified key to the specified value in the configuration file.
* `show`: Show the resolved Configuration.
* `use`: Set the current server.

---

### `flowctl config add`

Add a server to the configuration.

**Usage**:

```bash
$ flowctl config add [OPTIONS] SERVER_NAME URL
```

**Arguments**:

* `SERVER_NAME`: The server to add.  [required]
* `URL`: The url to add.  [required]

**Options**:

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `--help` | boolean | Show this message and exit. | **False** |

---

### `flowctl config current`

Get the current server.

**Usage**:

```bash
$ flowctl config current [OPTIONS]
```

**Options**:

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `--help` | boolean | Show this message and exit. | **False** |

---

### `flowctl config get`

Get the specified key from the configuration file.

**Usage**:

```bash
$ flowctl config get [OPTIONS] KEY
```

**Arguments**:

* `KEY`: The key to get.  [required]

**Options**:

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `--help` | boolean | Show this message and exit. | **False** |

---

### `flowctl config remove`

Remove a server from the configuration.

**Usage**:

```bash
$ flowctl config remove [OPTIONS] SERVER_NAME
```

**Arguments**:

* `SERVER_NAME`: The server to remove.  [required]

**Options**:

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `--help` | boolean | Show this message and exit. | **False** |

---

### `flowctl config set`

Set the specified key to the specified value in the configuration file.

**Usage**:

```bash
$ flowctl config set [OPTIONS] KEY VALUE
```

**Arguments**:

* `KEY`: The key to set.  [required]
* `VALUE`: The value to set.  [required]

**Options**:

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `--help` | boolean | Show this message and exit. | **False** |

---

### `flowctl config show`

Show the resolved Configuration.

Specify the format with the `--format` option. Defaults to `yaml`.
Renders the configuration as a syntax highlighted string if `--raw` is not specified.

**Usage**:

```bash
$ flowctl config show [OPTIONS]
```

**Options**:

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `--format, -f` | text | The format to render the configuration as. | **yaml** |
| `--raw` | boolean | None | **False** |
| `--help` | boolean | Show this message and exit. | **False** |

---

### `flowctl config use`

Set the current server.

**Usage**:

```bash
$ flowctl config use [OPTIONS] SERVER_NAME
```

**Arguments**:

* `SERVER_NAME`: The server to use.  [required]

**Options**:

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `--help` | boolean | Show this message and exit. | **False** |

---

## `flowctl delete`

Delete one or more resources of a specific kind.

**Usage**:

```bash
$ flowctl delete [OPTIONS] [RESOURCE_KIND] [RESOURCE_IDENTIFIER]
```

**Arguments**:

* `[RESOURCE_KIND]`: The kind of resource to get.
* `[RESOURCE_IDENTIFIER]`: The identifier of the resource to get.

**Options**:

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `--path, -p` | path | The path to a file or directory containing the resource(s) to delete. | **None** |
| `--help` | boolean | Show this message and exit. | **False** |

---

## `flowctl get`

Get one or more resources of a specific kind.

**Usage**:

```bash
$ flowctl get [OPTIONS] RESOURCE_KIND [RESOURCE_IDENTIFIER]
```

**Arguments**:

* `RESOURCE_KIND`: The kind of resource to get.  [required]
* `[RESOURCE_IDENTIFIER]`: The identifier of the resource to get.

**Options**:

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `--format, -f` | text | The format to output the resource in. Options are `table`, `json`, `yaml` and `raw`. | **table** |
| `--select` | text | The select query to filter the results. | **None** |
| `--help` | boolean | Show this message and exit. | **False** |

---

## `flowctl inspect`

Describe a resource of a specific kind.

**Usage**:

```bash
$ flowctl inspect [OPTIONS] RESOURCE_KIND RESOURCE_IDENTIFIER
```

**Arguments**:

* `RESOURCE_KIND`: The kind of resource to get.  [required]
* `RESOURCE_IDENTIFIER`: The identifier of the resource to get.  [required]

**Options**:

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `--help` | boolean | Show this message and exit. | **False** |

---

## `flowctl metrics`

Get information about the metrics of the server.

**Usage**:

```bash
$ flowctl metrics [OPTIONS] [NAME]
```

**Arguments**:

* `[NAME]`: The name of the metric to get.  [default: cpu]

**Options**:

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `--start-time, -s` | datetime (`%Y-%m-%d` &#x7C; `%Y-%m-%dT%H:%M:%S` &#x7C; `%Y-%m-%d %H:%M:%S`) | The start time of the metric to get. | **None** |
| `--end-time, -e` | datetime (`%Y-%m-%d` &#x7C; `%Y-%m-%dT%H:%M:%S` &#x7C; `%Y-%m-%d %H:%M:%S`) | The end time of the metric to get. | **None** |
| `--limit, -l` | integer | The maximum number of data points to get. | **30** |
| `--format, -f` | text | The format to render the metrics in. Options are: graph, raw, json, yaml. | **graph** |
| `--help` | boolean | Show this message and exit. | **False** |

---

## `flowctl patch`

Patch a Resource given a kind, identifier, and set of options.

**Usage**:

```bash
$ flowctl patch [OPTIONS] RESOURCE_KIND [RESOURCE_IDENTIFIER]
```

**Arguments**:

* `RESOURCE_KIND`: The kind of resource to get.  [required]
* `[RESOURCE_IDENTIFIER]`: The identifier of the resource to get.

**Options**:

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `--schema-version, -s` | text | The schema version to use when validating the resource. | **None** |
| `--help` | boolean | Show this message and exit. | **False** |

---

## `flowctl run`

Execute a Workflow by identifier with an optional input.

**Usage**:

```bash
$ flowctl run [OPTIONS] [RESOURCE_IDENTIFIER]
```

**Arguments**:

* `[RESOURCE_IDENTIFIER]`: The identifier of the Workflow to run.

**Options**:

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `--format, -f` | text | The output format to use. | **None** |
| `--result-only` | boolean | Only output the result of the run. | **False** |
| `--wait, --no-wait` | boolean | Wait for the run to complete. | **True** |
| `--namespace, -n` | text | The namespace to run the Workflow in. | **None** |
| `--show-progress, --disable-progress` | boolean | Show the progress spinner while waiting for the execution. | **True** |
| `--help` | boolean | Show this message and exit. | **False** |

---

## `flowctl status`

Get the status of the Flowdapt server.

**Usage**:

```bash
$ flowctl status [OPTIONS]
```

**Options**:

| Name | Type | Description | Default |
| ---- | ---- | ----------- | ------- |
| `--help` | boolean | Show this message and exit. | **False** |
