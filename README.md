![](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fsgfost%2Fcodemeticulous%2Fmain%2Fpyproject.toml) ![](https://img.shields.io/github/license/sgfost/codemeticulous)

> [!WARNING]
> `codemeticulous` is in an early state of development and things are subject to change. Refer to the [table](#feature-roadmap) below to see currently supported formats and conversions.

`codemeticulous` is a python library and command line utility for working with different metadata standards for software. Several [Pydantic](https://docs.pydantic.dev/latest/) models that mirror metadata schemas are provided which allows for simple validation, (de)serialization and type-safety for developers.

For converting between different standards, an extension of [CodeMeta](https://codemeta.github.io/), called `CanonicalCodeMeta`, is used as a canonical data model or central "hub" representation, along with conversion logic back and forth between it and supported standards. This design allows for conversion between any two formats without needing to implement each bridge. CodeMeta was chosen as it is the most exhaustive and provides [crosswalk definitions](https://codemeta.github.io/crosswalk/) between other formats. Still, some data loss can occur, so some extension is needed to fill schema gaps and resolve abiguity. Note that `CanonicalCodeMeta` is not a proposed standard, but an internal data model used by this library.

## Feature Roadmap

<table><thead>
  <tr>
    <th>Schema</th>
    <th>Pydantic model</th>
    <th>Backward-compatible with<a href="#1"><sup>[1]</sup></a></th>
    <th>Convert <i>to</i></th>
    <th>Convert <i>from</i></th>
  </tr></thead>
<tbody>
  <tr>
    <td><a href="https://w3id.org/codemeta/3.0">CodeMeta v3</a></td>
    <td>✅<a href="#2"><sup>[2]</sup></a></td>
    <td>v2</td>
    <td>✅</td>
    <td>✅</td>
  </tr>
  <tr>
    <td><a href="https://datacite-metadata-schema.readthedocs.io/en/4.6">Datacite 4.6</a></td>
    <td>✅</td>
    <td>4.0, 4.1, 4.2, 4.3, 4.4, 4.5</td>
    <td>✅</td>
    <td></td>
  </tr>
  <tr>
    <td><a href="https://citation-file-format.github.io/">Citation File Format 1.2.0</a></td>
    <td>✅</td>
    <td></td>
    <td>✅</td>
    <td></td>
  </tr>
  <tr>
    <td>GitHub Repository</td>
    <td><a href="https://docs.github.com/en/rest/repos?apiVersion=2022-11-28"><code>2022-11-28</code></a></td>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td>Zenodo?</td>
    <td></td>
    <td></td>
    <td></td>
    <td></td>
  </tr>
  <tr>
    <td>...</td>
    <td></td>
    <td></td>
    <td></td>
    <td></td>
  </tr>
</tbody>
</table>

##### [1]
Lists the versions that can be safely used as input. Output will always use the specified version. For example, the `CodeMetaV3` model will accept v2 property names and automatically change them to v3 equivalents.

##### [2]
The `CodeMeta` model is currently implemented as a pydantic **v1** model, due to a heavy reliance on [pydantic_schemaorg](https://github.com/lexiq-legal/pydantic_schemaorg) which has not been fully updated.

## Installation

<!-- ```
pip install codemeticulous
```

or install the latest development version -->

```
$ pip install git+https://github.com/sgfost/codemeticulous.git
```

## Usage

### As a command line tool

```
$ codemeticulous convert --from codemeta --to cff codemeta.json > CITATION.cff
$ codemeticulous validate --format cff CITATION.cff
```

### As a python library

```python
from codemeticulous.codemeta import CodeMeta, Person
from codemeticulous import convert

codemeta = CodeMeta(
  name="My Project",
  author=Person(givenName="Dale", familyName="Earnhardt"),
)

# commit kwarg is an override that can be used to insert
# a custom field into the resulting metadata after conversion
cff = convert("codemeta", "cff", codemeta, commit="abcdef123456789")

print(codemeta.json(indent=True))
# {
#   "@context": "https://w3id.org/codemeta/3.0",
#   "@type": "SoftwareSourceCode",
#   "name": "My Project",
#   "author": {"@type": "Person", "givenName": "Dale", "familyName": "Earnhardt"}
# }

print(cff.yaml())
# authors:
# - family-names: Earnhardt
#   given-names: Dale
# cff-version: 1.2.0
# message: If you use this software, please cite it using the metadata from this file.
# title: My Project
# type: software
# commit: abcdef123456789
```

<!-- ### As a Github Action -->

## Development

`codemeticulous` uses [`uv`](https://docs.astral.sh/uv/) for project management. The following assumes that you have [installed uv](https://docs.astral.sh/uv/getting-started/installation/).

Get started by cloning the repository and setting up a virtual environment

```
$ git clone https://github.com/SciCodes/codemeticulous.git
$ cd codemeticulous
$ uv sync --dev
$ source .venv/bin/activate
```

Run tests

```
$ uv run pytest tests
```

