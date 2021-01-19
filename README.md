# nbdep

This module automatically grabs and saves any imported modules into the metadata of the Notebook, everything is passed over the Jupyter kernel comm channel after the execution of each cell.

The actual module is implemented as an IPython extension that hooks onto sys.modules and performs a set difference on the modules that are imported and then passes it back to the Nbextension on the Javascript side which saves everything into metadata.

This package also includes a nbextension that writes out a pip requirements file based on the most up to date version of the dependencies.

## Installation
`pip install .`

`jupyter nbextension install --py nbdep --[user|sys-prefix]`

`jupyter nbextension enable nbdep --py --[user|sys-prefix]`

This package relies on IPython magics so either

`%load_ext nbdep` 

is required upon opening each notebook; the nbextension doesn't handle any events if the IPython extension is not enabled.

To ensure that the extension is loaded each time you open a new notebook then you should edit your configuration file to include the following line:

`c.InteractiveShellApp.extensions = [
    'nbdep'
]`

## Add bundler extension for requirements.txt deployment

`jupyter bundlerextension enable --sys-prefix --py nbdep`

