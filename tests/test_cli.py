import json
import subprocess
from pathlib import Path

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
                "--version",
                "1",
                "input.json",
            ],
        )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["title"] == "Tool"
    assert "author[0]:" in result.stderr
    assert "author[0]:" not in result.stdout


def test_cli_requires_explicit_opt_out_for_unprovenanced_input() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("input.json", "w", encoding="utf-8") as file:
            json.dump({"title": "Tool"}, file)

        result = runner.invoke(
            cli,
            [
                "convert",
                "--from",
                "software-metadata",
                "--to",
                "software-metadata",
                "--version",
                "1",
                "input.json",
            ],
        )

    assert result.exit_code != 0
    assert "requires --allow-unprovenanced" in result.stderr


def test_cli_accepts_canonical_software_metadata_input() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("input.json", "w", encoding="utf-8") as file:
            json.dump({"title": "Tool"}, file)

        result = runner.invoke(
            cli,
            [
                "convert",
                "--from",
                "software-metadata",
                "--to",
                "software-metadata",
                "--version",
                "1",
                "--allow-unprovenanced",
                "input.json",
            ],
        )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["title"] == "Tool"


def test_cli_accepts_bom_encoded_structured_collection_input() -> None:
    runner = CliRunner()
    collection = {
        "metadata": {"title": "Tool"},
        "sources": [
            {
                "id": "page",
                "uri": "https://example.org/tool",
                "kind": "project-page",
                "retrieved_at": "2026-10-19T00:00:00Z",
            }
        ],
        "fields": [
            {
                "path": "title",
                "status": "retrieved",
                "evidence": [
                    {
                        "source_id": "page",
                        "value": "Tool",
                        "acquisition": "retrieved",
                    }
                ],
                "selected_evidence": 0,
            }
        ],
    }
    with runner.isolated_filesystem():
        with open("collection.json", "w", encoding="utf-8-sig") as file:
            json.dump(collection, file)

        result = runner.invoke(
            cli,
            [
                "convert",
                "--from",
                "collected-software-metadata",
                "--to",
                "software-metadata",
                "--version",
                "1",
                "collection.json",
            ],
        )

    assert result.exit_code == 0
    assert json.loads(result.stdout)["title"] == "Tool"


def test_cli_validate_is_independent_of_conversion_targets() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("input.json", "w", encoding="utf-8") as file:
            json.dump({"@type": "SoftwareSourceCode", "name": "Tool"}, file)

        result = runner.invoke(
            cli,
            [
                "validate",
                "--format",
                "codemeta",
                "--version",
                "3.0",
                "input.json",
            ],
        )

    assert result.exit_code == 0
    assert "is valid codemeta 3.0 metadata" in result.stdout


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
                "--version",
                "1",
                "input.json",
            ],
        )

    assert result.exit_code != 0
    assert "Error during conversion" in result.stderr


def test_cli_reports_conversion_issues_before_serialization_failure() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("input.json", "w", encoding="utf-8") as file:
            json.dump(
                {
                    "@type": "SoftwareSourceCode",
                    "name": "Tool",
                    "author": {"@type": "Person", "name": "Ada Lovelace"},
                    "publisher": {"@type": "Organization", "name": "Archive"},
                    "datePublished": "2024-01-01",
                    "downloadUrl": "https://example.org/download",
                },
                file,
            )

        result = runner.invoke(
            cli,
            [
                "convert",
                "--from",
                "codemeta",
                "--to",
                "datacite.xml",
                "--version",
                "4.6",
                "input.json",
            ],
        )

    assert result.exit_code != 0
    assert "download_url: download URL is unsupported by DataCite" in result.stderr
    assert "DataCite XML requires a DOI identifier" in result.stderr


def test_cli_validation_failure_is_nonzero() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("input.json", "w", encoding="utf-8") as file:
            json.dump({"@type": "SoftwareSourceCode"}, file)

        result = runner.invoke(
            cli,
            [
                "validate",
                "--format",
                "codemeta",
                "--version",
                "3.0",
                "input.json",
            ],
        )

    assert result.exit_code != 0
    assert "Invalid codemeta 3.0 document" in result.stderr


def _git_repository(path: Path) -> Path:
    path.mkdir()
    subprocess.run(
        ["git", "init", "--quiet"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    return path


def test_skill_install_uses_git_repository_root(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    repository = _git_repository(tmp_path / "repository")
    nested_directory = repository / "src" / "package"
    nested_directory.mkdir(parents=True)
    monkeypatch.chdir(nested_directory)

    result = runner.invoke(
        cli,
        [
            "skill",
            "install",
            "research-software-metadata",
        ],
    )

    destination = repository / ".agents" / "skills" / "research-software-metadata"
    assert result.exit_code == 0
    assert (destination / "SKILL.md").is_file()
    assert (destination / "references" / "collection-contract.md").is_file()


def test_skill_install_refuses_overwrite(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    repository = _git_repository(tmp_path / "repository")
    monkeypatch.chdir(repository)
    arguments = [
        "skill",
        "install",
        "research-software-metadata",
    ]

    assert runner.invoke(cli, arguments).exit_code == 0

    second = runner.invoke(cli, arguments)

    assert second.exit_code != 0
    assert "already exists" in second.output


def test_skill_install_all_agents(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    repository = _git_repository(tmp_path / "repository")
    monkeypatch.chdir(repository)

    result = runner.invoke(
        cli,
        [
            "skill",
            "install",
            "research-software-metadata",
            "--agent",
            "all",
        ],
    )

    assert result.exit_code == 0
    assert (repository / ".agents/skills/research-software-metadata/SKILL.md").is_file()
    assert (repository / ".claude/skills/research-software-metadata/SKILL.md").is_file()


def test_skill_install_requires_git_repository(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    outside_repository = tmp_path / "not-a-repository"
    outside_repository.mkdir()
    monkeypatch.chdir(outside_repository)

    result = runner.invoke(
        cli,
        ["skill", "install", "research-software-metadata"],
    )

    assert result.exit_code != 0
    assert "must be run from inside a Git repository" in result.output
