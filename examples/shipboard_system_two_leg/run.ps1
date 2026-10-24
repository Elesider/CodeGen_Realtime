param(
    [string]$Python = 'D:\ProgramData\anaconda3\python.exe',
    [string]$Codegen,
    [string]$Compiler,
    [string]$Output,
    [switch]$AnalyzeOnly
)
$ErrorActionPreference = 'Stop'
$nativeArgs = @((Join-Path $PSScriptRoot 'run.py'))
if ($Codegen) { $nativeArgs += @('--codegen', $Codegen) }
if ($Compiler) { $nativeArgs += @('--compiler', $Compiler) }
if ($Output) { $nativeArgs += @('--output', $Output) }
if ($AnalyzeOnly) { $nativeArgs += '--analyze-only' }
& $Python @nativeArgs
if ($LASTEXITCODE -ne 0) { throw "Two-leg run failed: exit $LASTEXITCODE" }
