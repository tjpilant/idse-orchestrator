from click.testing import CliRunner

import idse_orchestrator
from idse_orchestrator.cli import main


def test_version_exposed():
    assert isinstance(idse_orchestrator.__version__, str)
    assert idse_orchestrator.__version__


def test_cli_version_flag():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0


def test_cli_help_flag():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
