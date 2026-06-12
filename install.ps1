$ErrorActionPreference = "Stop"

$InstallDir = $env:AME_INSTALL_DIR
if (-not $InstallDir) {
  $InstallDir = Join-Path $HOME ".ame"
}

$Package = $env:AME_PACKAGE
if (-not $Package) {
  $Package = "adaptive-memory-engine"
}

$Version = $env:AME_VERSION

$PythonCommand = $null
$PythonArgs = @()
$Candidates = @(
  @{ Command = Get-Command python -ErrorAction SilentlyContinue; Args = @() },
  @{ Command = Get-Command python3 -ErrorAction SilentlyContinue; Args = @() },
  @{ Command = Get-Command py -ErrorAction SilentlyContinue; Args = @("-3") }
)

foreach ($Candidate in $Candidates) {
  if (-not $Candidate.Command) {
    continue
  }
  & $Candidate.Command.Source @($Candidate.Args) -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" 2>$null
  if ($LASTEXITCODE -eq 0) {
    $PythonCommand = $Candidate.Command.Source
    $PythonArgs = $Candidate.Args
    break
  }
}

if (-not $PythonCommand) {
  throw "Python 3.11 or newer is required."
}

& $PythonCommand @PythonArgs -m venv $InstallDir

$VenvPython = Join-Path $InstallDir "Scripts\python.exe"
$AmeExe = Join-Path $InstallDir "Scripts\ame.exe"
$AmeBin = Join-Path $InstallDir "Scripts"

& $VenvPython -m pip install --upgrade pip

if ($Version) {
  & $VenvPython -m pip install --upgrade "$Package==$Version"
} else {
  & $VenvPython -m pip install --upgrade $Package
}

$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not $UserPath) {
  $UserPath = ""
}

$PathParts = $UserPath -split ";" | Where-Object { $_ }
if ($PathParts -notcontains $AmeBin) {
  $NewUserPath = if ($UserPath) { "$AmeBin;$UserPath" } else { $AmeBin }
  [Environment]::SetEnvironmentVariable("Path", $NewUserPath, "User")
}

$env:Path = "$AmeBin;$env:Path"
& $AmeExe --help | Out-Null

Write-Host "Adaptive Memory Engine installed."
Write-Host ""
Write-Host "Restart your terminal, then create your MCP config:"
Write-Host "  ame connect --client codex"
Write-Host ""
Write-Host "For Claude Code:"
Write-Host "  ame connect --client claude"
