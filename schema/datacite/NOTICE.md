# Vendored DataCite schemas

The DataCite Metadata Schema 4.5 and 4.6 XSD files in this directory were
copied from the official [DataCite schema repository](https://github.com/datacite/schema)
at commit `591a9cc86eb7989782dde1b49bbc6f5531b71f34`.

Only `metadata.xsd` and its required `include/*.xsd` files are vendored so
that `codemeticulous` can validate generated XML reproducibly without network
access.
