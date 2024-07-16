# Development

This plugin uses [poetry] and [typer] for aiding in development.

The general instructions for development are:

- Have QGIS installed locally
-  Fork the code repository
-  Clone your fork locally
-  Install poetry
-  Install the plugin dependencies into a new virtual env with

   ```
   cd qgis_geonode
   poetry install
   ```

- Place the QGIS Python-related libraries into the virtualenv created by poetry by using our custom CLI command 

   ```
   cd qgis_geonode
   poetry run pluginadmin install-qgis-into-venv
   ```

-  Work on a feature/bug on a new branch

-  Test things out locally by installing the plugin with our custom CLI command

   ```
   poetry run pluginadmin install
   ```

-  When ready, submit a PR for your code to be reviewed and merged


## pluginadmin

This plugin comes with a `pluginadmin` CLI command which provides commands useful for development.
It is used to perform all operations related to the plugin:

- Install the plugin to your local QGIS user profile
- Ensure your virtual env has access to the QGIS Python bindings
- Build a zip of the plugin
- etc.

It is run inside the virtual environment created by poetry. As such it must be invoked like this:

```
# get an overview of existing commands
poetry run python pluginadmin --help
```


## Install plugin into your local QGIS python plugins directory

When developing, in order to try out the plugin locally you need to
call `poetry run python pluginadmin.py install` command. This command will copy all files into your
local QGIS python plugins directory. Upon making changes to the code you
will need to call this installation command again and potentially also restart QGIS.

```
poetry run python pluginadmin.py install
```

!!! info
Perhaps a more robust set of instructions would be to:

- Create a custom QGIS user profile for development (here named `conefor-dev`)
- Create a sample QGIS project to aid in development (here named `qgisconefor-sample-project.qgz`)
- execute the following:

```shell
poetry run pluginadmin --qgis-profile conefor-dev install \
    && qgis --profiles-path ${HOME}/.local/share/QGIS/QGIS3 --profile conefor-dev --project qgisconefor-sample-project.qgz
```
