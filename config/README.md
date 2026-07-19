# Configuration

Config files for dynamic modification of the benchmark in
a central place. These files are mapped into relevant containers
or read by postprocessing systems to aggregate results.

## What can you configure?

For details on what these options mean and what you can do with them
consult the service documentation or have a look at the code.

### testcases.jsonc

This file is directly mapped into the logger container and used to define
what tests are run, in what order and how often.

### postprocess.jsonc

This configuration is used to change the beahviour of the postprocessing
pipeline found in `/analysis`.

#### A note on .jsonc

The files in this folder are `JSONC` files. that means that it is possible to use javascript
comments inside the objects without breaking them. This is useful for annotations and explanations
without cluttering the objects.
