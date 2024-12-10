import os
import click
import json
import yaml

from codemeticulous.convert import STANDARDS, convert as _convert


@click.group()
def cli():
    pass


@cli.command()
@click.option(
    "-f",
    "--from",
    "source_format",
    type=click.Choice(STANDARDS.keys()),
    required=True,
    help="Source format",
)
@click.option(
    "-t",
    "--to",
    "target_format",
    type=click.Choice(STANDARDS.keys()),
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
def convert(source_format: str, target_format: str, input_file, output_file):
    try:
        input_data = load_file_autodetect(input_file)
    except Exception as e:
        click.echo(f"Failed to load file: {input_file}. {str(e)}", err=True)

    try:
        converted_data = _convert(source_format, target_format, input_data)
    except Exception as e:
        click.echo(f"Error during conversion: {str(e)}", err=True)
        return

    output_format = STANDARDS[target_format]["format"]

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
    type=click.Choice(STANDARDS.keys()),
    required=True,
    help="Format to validate",
)
@click.argument("input_file", type=click.Path(exists=True))
def validate(format_name, input_file):
    try:
        load_and_create_model(input_file, STANDARDS[format_name]["model"])
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
            elif ext in [".yaml", ".yml", ".cff"]:
                return yaml.safe_load(file)
            else:
                raise ValueError(f"Unsupported file extension: {ext}.")
    except Exception as e:
        raise ValueError(f"Failed to load file: {file_path}. {str(e)}")
