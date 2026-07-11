# Production installer for livekit-agent-simulator (lk-sim + MCP) on Windows.
#
#   irm "https://raw.githubusercontent.com/quangdang46/livekit-agent-simulator/main/install.ps1" | iex
#
# Or with args:
#   irm .../install.ps1 | iex
#   # Or download then: .\install.ps1 -Version v0.1.0 -Verify -NoMcp
#
#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$Version = $env:LK_SIM_VERSION,
    [string]$GitRef = $(if ($env:LK_SIM_REF) { $env:LK_SIM_REF } else { "main" }),
    [switch]$FromGit,
    [switch]$NoMcp,
    [switch]$Verify,
    [switch]$Uninstall,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"
$BinaryName = "lk-sim"
$McpBin = "livekit-agent-simulator-mcp"
$McpServerName = "livekit-agent-simulator"
$PkgName = "livekit-agent-simulator"
$Owner = "quangdang46"
$Repo = "livekit-agent-simulator"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    if ($Quiet -and $Level -eq "INFO") { return }
    $prefix = "[$BinaryName]"
    if ($Level -eq "WARN") { Write-Host "$prefix WARN: $Message" -ForegroundColor Yellow }
    elseif ($Level -eq "ERROR") { Write-Host "$prefix ERROR: $Message" -ForegroundColor Red }
    else { Write-Host "$prefix $Message" }
}

function Get-PypiVersion([string]$v) {
    if ([string]::IsNullOrWhiteSpace($v)) { return $null }
    return $v.TrimStart("v")
}

function Merge-JsonIntoFile {
    param(
        [string]$FilePath,
        [string]$Key,
        [hashtable]$Value
    )
    $dir = Split-Path -Parent $FilePath
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

    $data = [ordered]@{}
    if (Test-Path $FilePath) {
        try {
            $raw = Get-Content -Path $FilePath -Raw -ErrorAction Stop
            if ($raw.Trim()) {
                $obj = $raw | ConvertFrom-Json
                $data = [ordered]@{}
                foreach ($p in $obj.PSObject.Properties) {
                    $data[$p.Name] = $p.Value
                }
            }
        } catch {
            $data = [ordered]@{}
        }
    }

    if (-not $data.Contains($Key)) {
        $data[$Key] = [ordered]@{}
    }

    $bucket = $data[$Key]
    if ($null -eq $bucket) { $bucket = [ordered]@{} }

    # Convert nested PSCustomObject bucket to hashtable-ish
    $bucketMap = [ordered]@{}
    if ($bucket -is [System.Collections.IDictionary]) {
        foreach ($k in $bucket.Keys) { $bucketMap[$k] = $bucket[$k] }
    } elseif ($bucket.PSObject) {
        foreach ($p in $bucket.PSObject.Properties) { $bucketMap[$p.Name] = $p.Value }
    }

    foreach ($k in $Value.Keys) {
        $bucketMap[$k] = $Value[$k]
    }
    $data[$Key] = $bucketMap

    ($data | ConvertTo-Json -Depth 12) + "`n" | Set-Content -Path $FilePath -Encoding UTF8
}

function Remove-McpFromFile {
    param([string]$FilePath, [string]$ParentKey = "mcpServers", [string]$ServerName)
    if (-not (Test-Path $FilePath)) { return }
    try {
        $obj = Get-Content -Path $FilePath -Raw | ConvertFrom-Json
        if ($null -eq $obj.$ParentKey) { return }
        $map = [ordered]@{}
        foreach ($p in $obj.PSObject.Properties) {
            if ($p.Name -eq $ParentKey) {
                $inner = [ordered]@{}
                foreach ($ip in $p.Value.PSObject.Properties) {
                    if ($ip.Name -ne $ServerName) { $inner[$ip.Name] = $ip.Value }
                }
                $map[$p.Name] = $inner
            } else {
                $map[$p.Name] = $p.Value
            }
        }
        ($map | ConvertTo-Json -Depth 12) + "`n" | Set-Content -Path $FilePath -Encoding UTF8
    } catch {
        Write-Log "Could not edit $FilePath : $_" "WARN"
    }
}

function Resolve-McpBinary {
    $cmd = Get-Command $McpBin -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = @(
        (Join-Path $env:USERPROFILE ".local\bin\$McpBin.exe"),
        (Join-Path $env:USERPROFILE ".local\bin\$McpBin"),
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Scripts\$McpBin.exe")
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { return $c }
    }
    return $null
}

function Configure-AllMcpProviders {
    $binary = Resolve-McpBinary
    if (-not $binary) {
        Write-Log "MCP binary not found on PATH — skip provider config" "WARN"
        return
    }
    Write-Log "Configuring MCP providers → $binary"
    $entry = @{
        $McpServerName = @{
            command = $binary
            args    = @()
            env     = @{}
        }
    }

    Merge-JsonIntoFile -FilePath (Join-Path $env:USERPROFILE ".claude.json") -Key "mcpServers" -Value $entry
    Merge-JsonIntoFile -FilePath (Join-Path $env:USERPROFILE ".cursor\mcp.json") -Key "mcpServers" -Value $entry

    $cline = Join-Path $env:APPDATA "Code\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json"
    if (Test-Path (Split-Path $cline)) {
        Merge-JsonIntoFile -FilePath $cline -Key "mcpServers" -Value $entry
    }

    Merge-JsonIntoFile -FilePath (Join-Path $env:USERPROFILE ".codeium\windsurf\mcp_config.json") -Key "mcpServers" -Value $entry
    Merge-JsonIntoFile -FilePath (Join-Path $env:USERPROFILE ".vscode\mcp.json") -Key "servers" -Value $entry
    Merge-JsonIntoFile -FilePath (Join-Path $env:USERPROFILE ".gemini\settings.json") -Key "mcpServers" -Value $entry
    Merge-JsonIntoFile -FilePath (Join-Path $env:USERPROFILE ".aws\amazonq\mcp.json") -Key "mcpServers" -Value $entry
    Merge-JsonIntoFile -FilePath (Join-Path $env:USERPROFILE ".aws\amazonq\default.json") -Key "mcpServers" -Value $entry

    $opencode = Join-Path $env:USERPROFILE ".opencode.json"
    if ((Test-Path $opencode) -or (Test-Path (Join-Path $env:USERPROFILE ".config\opencode"))) {
        $ocEntry = @{
            $McpServerName = @{
                type    = "stdio"
                command = $binary
                args    = @()
                env     = @()
            }
        }
        Merge-JsonIntoFile -FilePath $opencode -Key "mcpServers" -Value $ocEntry
    }

    # Codex TOML
    $codexDir = Join-Path $env:USERPROFILE ".codex"
    $codex = Join-Path $codexDir "config.toml"
    if (Test-Path $codexDir) {
        if (-not (Test-Path $codex)) { New-Item -ItemType File -Path $codex -Force | Out-Null }
        $content = Get-Content -Path $codex -Raw -ErrorAction SilentlyContinue
        if ($content -notmatch "\[mcp_servers\.$([regex]::Escape($McpServerName))\]") {
            Add-Content -Path $codex -Value @"

[mcp_servers.$McpServerName]
type = "stdio"
command = "$binary"
args = []
"@
        }
    }
}

function Uninstall-All {
    Write-Log "Uninstalling $PkgName..."
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        try { uv tool uninstall $PkgName 2>$null } catch {}
    }
    if (Get-Command pipx -ErrorAction SilentlyContinue) {
        try { pipx uninstall $PkgName 2>$null } catch {}
    }
    Remove-McpFromFile -FilePath (Join-Path $env:USERPROFILE ".claude.json") -ServerName $McpServerName
    Remove-McpFromFile -FilePath (Join-Path $env:USERPROFILE ".cursor\mcp.json") -ServerName $McpServerName
    Remove-McpFromFile -FilePath (Join-Path $env:USERPROFILE ".vscode\mcp.json") -ParentKey "servers" -ServerName $McpServerName
    Remove-McpFromFile -FilePath (Join-Path $env:USERPROFILE ".gemini\settings.json") -ServerName $McpServerName
    Remove-McpFromFile -FilePath (Join-Path $env:USERPROFILE ".aws\amazonq\mcp.json") -ServerName $McpServerName
    Remove-McpFromFile -FilePath (Join-Path $env:USERPROFILE ".aws\amazonq\default.json") -ServerName $McpServerName
    Write-Log "Uninstalled $PkgName" "INFO"
}

function Install-Package {
    $hasUv = [bool](Get-Command uv -ErrorAction SilentlyContinue)
    $hasPipx = [bool](Get-Command pipx -ErrorAction SilentlyContinue)
    if (-not $hasUv -and -not $hasPipx) {
        throw "Need uv or pipx. Install uv: https://docs.astral.sh/uv/getting-started/installation/"
    }

    $spec = $PkgName
    if ($FromGit) {
        $spec = "git+https://github.com/$Owner/$Repo.git@$GitRef"
        Write-Log "Source: git @$GitRef"
    } elseif ($Version) {
        $pv = Get-PypiVersion $Version
        $spec = "$PkgName==$pv"
        Write-Log "Source: PyPI $spec"
    } else {
        Write-Log "Source: PyPI latest $PkgName"
    }

    try {
        if ($hasUv) {
            Write-Log "uv tool install --force $spec"
            & uv tool install --force $spec
            if ($LASTEXITCODE -ne 0) { throw "uv tool install failed" }
        } else {
            Write-Log "pipx install --force $spec"
            & pipx install --force $spec
            if ($LASTEXITCODE -ne 0) { throw "pipx install failed" }
        }
    } catch {
        Write-Log "Primary install failed — falling back to git@$GitRef" "WARN"
        $gitspec = "git+https://github.com/$Owner/$Repo.git@$GitRef"
        if ($Version -and $Version.StartsWith("v")) {
            $gitspec = "git+https://github.com/$Owner/$Repo.git@$Version"
        }
        if ($hasUv) {
            & uv tool install --force $gitspec
            if ($LASTEXITCODE -ne 0) { throw "git fallback install failed" }
        } else {
            & pipx install --force $gitspec
            if ($LASTEXITCODE -ne 0) { throw "git fallback install failed" }
        }
    }
}

# === Main ===
if ($Uninstall) {
    Uninstall-All
    return
}

Write-Log "Installing $PkgName (CLI $BinaryName + MCP $McpBin)"
Install-Package

if (-not $NoMcp) {
    Configure-AllMcpProviders
} else {
    Write-Log "Skipped MCP auto-config (-NoMcp)"
}

if ($Verify) {
    $lk = Get-Command $BinaryName -ErrorAction SilentlyContinue
    if (-not $lk) { throw "$BinaryName not on PATH after install" }
    & $BinaryName --help | Out-Null
    Write-Log "Verified $BinaryName --help"
}

Write-Host ""
Write-Host "✓ $PkgName installed" -ForegroundColor Green
$lkCmd = Get-Command $BinaryName -ErrorAction SilentlyContinue
if ($lkCmd) { Write-Host "  CLI: $($lkCmd.Source)" }
$mcp = Resolve-McpBinary
if ($mcp) { Write-Host "  MCP: $mcp" }
Write-Host ""
Write-Host "  Quick start:"
Write-Host "    $BinaryName guide"
Write-Host "    $BinaryName init --root C:\path\to\target"
Write-Host "    $BinaryName web --root C:\path\to\target"
Write-Host ""
Write-Host "  Report player is prebuilt in the package (no Node/pnpm required)."
Write-Host ""
