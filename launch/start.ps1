$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
if (!(Test-Path '.venv/Scripts/python.exe')) { py -3 -m venv .venv; if ($LASTEXITCODE -ne 0) { throw 'Python 3.11+ is required.' } }
& .venv/Scripts/python.exe -m pip install '.[platform]'
if ($LASTEXITCODE -ne 0) { throw 'Installation failed. Check Python version and network.' }
Write-Host 'Open http://127.0.0.1:8765 after the server starts. Ctrl+C to stop.'
& .venv/Scripts/python.exe -m science_platform serve
