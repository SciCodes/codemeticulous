import os
import click
import json

import yaml

from codemeticulous.codemeta.models import CodeMeta
from codemeticulous.datacite.models import DataciteV45
from codemeticulous.cff.models import CitationFileFormat
from codemeticulous.datacite.convert import codemeta_to_datacite, datacite_to_codemeta
from codemeticulous.cff.convert import codemeta_to_cff, cff_to_codemeta


models = {
    "codemeta": {"model": CodeMeta, "format": "json"},
    "datacite": {"model": DataciteV45, "format": "json"},
    "cff": {"model": CitationFileFormat, "format": "yaml"},
}

converters = {
    "codemeta": {
        "datacite": codemeta_to_datacite,
        "cff": codemeta_to_cff,
    },
    "datacite": {
        "codemeta": datacite_to_codemeta,
    },
    "cff": {
        "codemeta": cff_to_codemeta,
    },
}


@click.group()
def cli():
    pass


@cli.command()
@click.option(
    "-f",
    "--from",
    "from_format",
    type=click.Choice(models.keys()),
    required=True,
    help="Source format",
)
@click.option(
    "-t",
    "--to",
    "to_format",
    type=click.Choice(models.keys()),
    required=True,
    help="Target format",
)
@click.option(
    "-o",
    "--output",
    "output_file",
    type=click.File("w"),
    default=None,
    help="Output file name (by default prints to stdout)",
)
@click.argument("input_file", type=click.Path(exists=True))
def convert(from_format, to_format, input_file, output_file):
    if to_format not in converters.get(from_format, {}):
        click.echo(
            f"Conversion from {from_format} to {to_format} is not supported", err=True
        )
        return

    try:
        input_data = load_and_create_model(input_file, models[from_format]["model"])
    except ValueError as e:
        click.echo(str(e), err=True)
        return

    try:
        convert_func = converters[from_format][to_format]
        converted_data = convert_func(input_data)
    except Exception as e:
        click.echo(f"Error during conversion: {str(e)}", err=True)
        return

    output_format = models[to_format]["format"]

    try:
        output_data = dump_data(converted_data, output_format)
    except Exception as e:
        click.echo(f"Error during serialization: {str(e)}", err=True)
        return

    if output_file:
        output_file.write(output_data)
        click.echo(f"Data written to {output_file.name}")
    else:
        click.echo(output_data)


@cli.command()
@click.option(
    "-f",
    "--format",
    "format_name",
    type=click.Choice(models.keys()),
    required=True,
    help="Format to validate",
)
@click.argument("input_file", type=click.Path(exists=True))
def validate(format_name, input_file):
    try:
        load_and_create_model(input_file, models[format_name]["model"])
        click.echo(f"{input_file} is a valid {format_name} file.")
    except ValueError as e:
        click.echo(str(e), err=True)


def dump_data(data, format):
    if format == "json":
        return data.json()
    elif format == "yaml":
        return data.yaml()
    else:
        raise ValueError(f"Unsupported format: {format}. Expected json or yaml")


def load_and_create_model(file_path, model):
    try:
        data = load_file_autodetect(file_path)
    except Exception as e:
        raise ValueError(f"Failed to load file: {file_path}. {str(e)}")
    try:
        return model(**data)
    except Exception as e:
        raise ValueError(f"Failed to validate: {str(e)}")


def load_file_autodetect(file_path):
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    try:
        with open(file_path, "r") as file:
            if ext in [".json"]:
                return json.load(file)
            elif ext in [".yaml", ".yml"]:
                return yaml.safe_load(file)
            else:
                raise ValueError(
                    f"Unsupported file extension: {ext}. Expected .json or .yaml"
                )
    except Exception as e:
        raise ValueError(f"Failed to load file: {file_path}. {str(e)}")
