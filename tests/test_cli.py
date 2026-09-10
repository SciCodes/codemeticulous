import json

from click.testing import CliRunner

from codemeticulous.cli import cli


def test_cli_convert_prints_document_and_loss_diagnostics() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("input.json", "w", encoding="utf-8") as file:
            json.dump(
                {"@type": "SoftwareSourceCode", "name": "Tool", "author": "Unknown"},
                file,
            )

        result = runner.invoke(
            cli,
            [
                "convert",
                "--from",
                "codemeta",
                "--to",
                "software-metadata",
                "input.json",
            ],
        )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["title"] == "Tool"
    assert "author[0]:" in result.stderr
    assert "author[0]:" not in result.stdout


def test_cli_validate_is_independent_of_conversion_targets() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("input.json", "w", encoding="utf-8") as file:
            json.dump({"@type": "SoftwareSourceCode", "name": "Tool"}, file)

        result = runner.invoke(cli, ["validate", "--format", "codemeta", "input.json"])

    assert result.exit_code == 0
    assert "is a valid codemeta file" in result.stdout


def test_cli_convert_failure_is_nonzero() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("input.json", "w", encoding="utf-8") as file:
            json.dump({"@type": "SoftwareSourceCode"}, file)

        result = runner.invoke(
            cli,
            [
                "convert",
                "--from",
                "codemeta",
                "--to",
                "software-metadata",
                "input.json",
            ],
        )

    assert result.exit_code != 0
    assert "Error during conversion" in result.stderr


def test_cli_validation_failure_is_nonzero() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("input.json", "w", encoding="utf-8") as file:
            json.dump({"@type": "SoftwareSourceCode"}, file)

        result = runner.invoke(cli, ["validate", "--format", "codemeta", "input.json"])

    assert result.exit_code != 0
    assert "Failed to validate" in result.stderr
