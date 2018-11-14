# nbdepv

This module automatically grabs and saves any imported modules into the metadata of the Notebook, everything is passed over the Jupyter kernel comm channel after the execution of each cell.

The actual module is implemented as an IPython extension that hooks onto sys.modules and performs a set difference on the modules that are imported and then passes it back to the Nbextension on the Javascript side which saves everything into metadata.


## Installation
`pip install .`

`jupyter nbextension install --py nbdepv --[user|sys-prefix]`

`jupyter nbextension enable nbdepv --py --[user|sys-prefix]`



