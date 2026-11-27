"""Validate the documented Windows startup without accessing Google."""
import base64
from pathlib import Path
import shutil
import subprocess

import pytest


README = (Path(__file__).resolve().parents[1] / 'README.md').read_text(encoding='utf-8')


def powershell(source, cwd):
    command = shutil.which('pwsh') or shutil.which('powershell')
    if command is None:
        pytest.skip('Windows startup verification requires PowerShell')
    encoded = base64.b64encode(source.encode('utf-16-le')).decode('ascii')
    return subprocess.run([command, '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
                          cwd=cwd, capture_output=True, timeout=30)


def test_all_readme_powershell_examples_parse(tmp_path):
    import re
    blocks = re.findall(r'```powershell\s*\n(.*?)```', README, re.S)
    assert blocks
    for block in blocks:
        encoded = base64.b64encode(block.encode('utf-8')).decode('ascii')
        source = f"""
$source = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded}'))
$tokens = $null; $errors = $null
[void][System.Management.Automation.Language.Parser]::ParseInput($source, [ref]$tokens, [ref]$errors)
if ($errors.Count) {{ exit 1 }}
"""
        assert powershell(source, tmp_path).returncode == 0


def test_startup_rejects_wrong_directory_before_prompts_or_google(tmp_path):
    section = README.split('<!-- unified-startup -->', 1)[1].split('<!-- /unified-startup -->', 1)[0]
    block = section.split('```powershell\n', 1)[1].split('```', 1)[0]
    source = """
function Read-Host { throw 'Unexpected prompt before project validation' }
function Invoke-RestMethod { throw 'Unexpected network request' }
try {
""" + block + """
exit 2
} catch {
    if ($_.Exception.Message -like '*requirements-dev.txt*') { exit 0 }
    exit 3
}
"""
    assert powershell(source, tmp_path).returncode == 0


@pytest.mark.parametrize('blocked', [False, True])
def test_gcloud_config_uses_writable_user_directory_and_rejects_file(tmp_path, blocked):
    target = tmp_path / 'GuidedNotesBuzzer' / 'gcloud'
    if blocked:
        target.parent.mkdir()
        target.write_text('existing file', encoding='utf-8')
    section = README.split('# BEGIN GCLOUD USER CONFIG', 1)[1].split('# END GCLOUD USER CONFIG', 1)[0]
    encoded = base64.b64encode(str(tmp_path).encode('utf-8')).decode('ascii')
    setup = f"$env:LOCALAPPDATA = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded}'))\n"
    source = setup + '$ErrorActionPreference = "Stop"\ntry {\n' + section
    source += '\nif (-not (Test-Path -LiteralPath $env:CLOUDSDK_CONFIG -PathType Container)) { exit 2 }\nexit 0\n} catch { exit 3 }'
    assert powershell(source, tmp_path).returncode == (3 if blocked else 0)
    if blocked:
        assert target.read_text(encoding='utf-8') == 'existing file'
