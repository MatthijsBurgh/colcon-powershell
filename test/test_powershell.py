# Copyright 2026 Matthijs van der Burgh
# Licensed under the Apache License, Version 2.0

import subprocess
import sys
from unittest.mock import mock_open
from unittest.mock import patch

from colcon_powershell.shell import powershell
from colcon_powershell.shell.powershell import get_parent_process_name
from colcon_powershell.shell.powershell import parent_process_is_powershell
from colcon_powershell.shell.powershell import PowerShellExtension
import pytest


@pytest.mark.skipif(
    sys.platform == 'win32', reason='Not supported on Windows')
def test_get_parent_process_name():
    name = get_parent_process_name()
    assert isinstance(name, str)
    assert name


@pytest.mark.parametrize('content, expected', [
    ('pwsh\n', 'pwsh'),
    ('bash\n', 'bash'),
    ('\n', None),
])
def test_get_parent_process_name_linux(content, expected):
    with patch.object(sys, 'platform', 'linux'), \
            patch('builtins.open', mock_open(read_data=content)):
        assert get_parent_process_name() == expected


def test_get_parent_process_name_linux_error():
    with patch.object(sys, 'platform', 'linux'), \
            patch('builtins.open', side_effect=FileNotFoundError):
        assert get_parent_process_name() is None


@pytest.mark.parametrize('output, expected', [
    ('pwsh\n', 'pwsh'),
    ('-pwsh\n', 'pwsh'),
    ('/usr/local/bin/pwsh\n', 'pwsh'),
    ('-/usr/local/bin/pwsh\n', 'pwsh'),
    ('/bin/zsh\n', 'zsh'),
    ('', None),
])
def test_get_parent_process_name_ps(output, expected):
    with patch.object(sys, 'platform', 'darwin'), \
            patch.object(subprocess, 'check_output', return_value=output):
        assert get_parent_process_name() == expected


@pytest.mark.parametrize('error', [
    FileNotFoundError,
    subprocess.CalledProcessError(1, 'ps'),
    UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid'),
])
def test_get_parent_process_name_ps_error(error):
    with patch.object(sys, 'platform', 'darwin'), \
            patch.object(subprocess, 'check_output', side_effect=error):
        assert get_parent_process_name() is None


@pytest.mark.parametrize('parent_name, executable, expected', [
    ('pwsh', '/usr/bin/pwsh', True),
    ('bash', '/usr/bin/pwsh', False),
    ('pwsh-preview', '/usr/bin/pwsh', False),
    ('pwsh-preview', '/usr/bin/pwsh-preview', True),
    ('pwsh', None, True),
])
def test_parent_process_is_powershell(parent_name, executable, expected):
    with patch.object(powershell, 'powershell_executable_name', 'pwsh'), \
            patch.object(powershell, 'POWERSHELL_EXECUTABLE', executable), \
            patch.object(
                powershell, 'get_parent_process_name',
                return_value=parent_name), \
            patch.dict('os.environ', {'PSModulePath': '/foo'}):
        assert parent_process_is_powershell() is expected


@pytest.mark.parametrize('environ, expected', [
    ({'PSModulePath': '/foo'}, True),
    ({'PSModulePath': ''}, False),
    ({}, False),
])
def test_parent_process_is_powershell_fallback(environ, expected):
    with patch.object(
        powershell, 'get_parent_process_name', return_value=None
    ), patch.dict('os.environ', environ, clear=True):
        assert parent_process_is_powershell() is expected


def test_extension_is_primary():
    with patch.object(powershell, 'POWERSHELL_EXECUTABLE', None), \
            patch.object(
                powershell, 'parent_process_is_powershell'
            ) as is_powershell:
        assert not PowerShellExtension()._is_primary
        is_powershell.assert_not_called()

    if sys.platform == 'win32':
        return

    for expected in (True, False):
        with patch.object(
            powershell, 'POWERSHELL_EXECUTABLE', '/usr/bin/pwsh'
        ), patch.object(
            powershell, 'parent_process_is_powershell', return_value=expected
        ):
            assert PowerShellExtension()._is_primary is expected
