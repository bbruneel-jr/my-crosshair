# Run the crosshair overlay (uses system Python)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m src.overlay
