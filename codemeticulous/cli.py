import os
import traceback
import click
import json
import yaml

from codemeticulous.convert import STANDARDS, convert as _convert
from codemeticulous.ai_convert import convert_ai as _convert_ai

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
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Print verbose output",
)
@click.argument("input_file", type=click.Path(exists=True))
def convert(source_format: str, target_format: str, input_file, output_file, verbose):
    try:
        input_data = load_file_autodetect(input_file)
    except Exception as e:
        click.echo(f"Failed to load file: {input_file}. {str(e)}", err=True)
        if verbose:
            traceback.print_exc()
    try:
        converted_data = _convert(source_format, target_format, input_data)
    except Exception as e:
        click.echo(f"Error during conversion: {str(e)}", err=True)
        if verbose:
            traceback.print_exc()
        return

    output_format = STANDARDS[target_format]["format"]

    try:
        output_data = dump_data(converted_data, output_format)
    except Exception as e:
        click.echo(f"Error during serialization: {str(e)}", err=True)
        if verbose:
            traceback.print_exc()
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
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Print verbose output",
)
@click.argument("input_file", type=click.Path(exists=True))
def validate(format_name, input_file, verbose):
    try:
        load_and_create_model(input_file, STANDARDS[format_name]["model"])
        click.echo(f"{input_file} is a valid {format_name} file.")
    except ValueError as e:
        click.echo(str(e), err=True)
        if verbose:
            traceback.print_exc()


@cli.command()
@click.option(
    "-k",
    "--key",
    "api_key",
    type=str,
    required=True,
    help="API key for LLM authorization",
)
@click.option(
    "-m",
    "--model",
    "llm_model",
    type=str,
    required=True,
    help="LLM model to use for conversion (e.g., 'openrouter/openai/gpt-4o')",
)
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
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Print verbose output",
)
@click.argument("input_file", type=click.Path(exists=True))
def ai_convert(api_key: str, llm_model: str, source_format: str, target_format: str, input_file, output_file, verbose):
    try:
        input_data = load_file_autodetect(input_file)
    except Exception as e:
        click.echo(f"Failed to load file: {input_file}. {str(e)}", err=True)
        if verbose:
            traceback.print_exc()
    try:
        converted_data = _convert_ai(api_key, llm_model, source_format, target_format, input_data)
        click.echo("AI-assisted conversion successful.")
    except Exception as e:
        click.echo(f"Error during AI-assisted conversion: {str(e)}", err=True)
        if verbose:
            traceback.print_exc()
        return

    output_format = STANDARDS[target_format]["format"]

    try:
        output_data = dump_data(converted_data, output_format)
    except Exception as e:
        click.echo(f"Error during serialization: {str(e)}", err=True)
        if verbose:
            traceback.print_exc()
        return

    if output_file:
        output_file.write(output_data)
        click.echo(f"Data written to {output_file.name}")
    else:
        click.echo(output_data)


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