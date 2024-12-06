![](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fsgfost%2Fcodemeticulous%2Fmain%2Fpyproject.toml) ![](https://img.shields.io/github/license/sgfost/codemeticulous)

> [!NOTE]
> `codemeticulous` is in an early state of development and things are subject to change. Refer to the [table](#feature-roadmap) below to see currently supported formats and conversions.

`codemeticulous` is a python library and command line utility for validating and converting between different metadata standards for software. Validation is done by providing [pydantic](https://docs.pydantic.dev/latest/) models that mirror the standards' schema definitions.

Currently, CodeMeta is used as a central "hub" representation of software metadata as it is the most exhaustive, and provides [crosswalk definitions](https://codemeta.github.io/crosswalk/) between other formats. This is done in order to avoid the need for a bridge between every format, though custom conversion logic can be implemented where needed.

> [!NOTE]
> This is subject to change, however. There is an argument to be made for whether an even more robust internal data model would be beneficial. Namely, that going through CodeMeta/schema.org means some conversions will be lossy.

## Feature Roadmap

<table><thead>
  <tr>
    <th colspan="2">Schema</th>
    <th colspan="3">Status<br></th>
  </tr></thead>
<tbody>
  <tr>
    <td>Name<br></td>
    <td>Version(s)</td>
    <td>Pydantic Model</td>
    <td>from CodeMeta<br></td>
    <td>to CodeMeta<br></td>
  </tr>
  <tr>
    <td><a href="https://codemeta.github.io/">CodeMeta</a><br></td>
    <td><a href="https://w3id.org/codemeta/3.0"><code>v3</code></a></td>
    <td>✅ *</td>
    <td>-</td>
    <td>-</td>
  </tr>
  <tr>
    <td><a href="https://schema.datacite.org/">Datacite</a></td>
    <td><a href="https://datacite-metadata-schema.readthedocs.io/en/4.5/"><code>v4.5</code></a><br></td>
    <td>✅</td>
    <td>✅</td>
    <td></td>
  </tr>
  <tr>
    <td><a href="https://citation-file-format.github.io/">Citation File Format</a></td>
    <td><a href="https://github.com/citation-file-format/citation-file-format/blob/bd0b31df69dccf11b31584585b5fb8c39d3e0e09/schema.json"><code>1.2.0</a></code></td>
    <td>✅</td>
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

\* The `CodeMeta` model is currently implemented as a pydantic **v1** model, due to a heavy reliance on [pydantic_schemaorg](https://github.com/lexiq-legal/pydantic_schemaorg) which has not been fully updated.

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
from codemeticulous.codemeta.models import CodeMeta, Person
from codemeticulous.cff.convert import codemeta_to_cff

codemeta = CodeMeta(
  name="My Project",
  author=Person(givenName="Dale", familyName="Earnhardt"),
)

cff = codemeta_to_cff(codemeta)

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
```

<!-- ### As a Github Action -->

## Development

`codemeticulous` uses [`uv`](https://docs.astral.sh/uv/) for project management. The following assumes that you have [installed uv](https://docs.astral.sh/uv/getting-started/installation/).

Get started by cloning the repository and setting up a virtual environment

```
$ git clone https://github.com/sgfost/codemeticulous.git
$ cd codemeticulous
$ uv sync --dev
$ source .venv/bin/activate
```

Run tests

```
$ uv run pytest tests
```
