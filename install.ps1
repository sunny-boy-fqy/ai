# AI Tool Installation & Update Script for Windows

$TARGET_DIR = "$HOME\ai"
$CONFIG_DIR = "$HOME\.config\ai"
$USER_AI_DIR = "$HOME\.ai"
$MCP_SERVERS_DIR = "$USER_AI_DIR\mcp_servers"
$VENV_PATH = "$CONFIG_DIR\python_venv"

Write-Host "=== 🤖 AI CLI Installation/Update (Windows) ===" -ForegroundColor Cyan

# 1. Check Dependencies
function Check-Command($cmd) {
    Get-Command $cmd -ErrorAction SilentlyContinue
}

if (-not (Check-Command "git")) {
    Write-Host "❌ git not found. Please install git." -ForegroundColor Red
    exit 1
}

if (-not (Check-Command "python")) {
    Write-Host "❌ python not found. Please install Python 3." -ForegroundColor Red
    exit 1
}

# 2. Directory Setup
if (-not (Test-Path $TARGET_DIR)) {
    Write-Host "Creating target directory $TARGET_DIR ..."
    mkdir $TARGET_DIR | Out-Null
}

if (-not (Test-Path "$TARGET_DIR\.git")) {
    Write-Host "Cloning repository..."
    git clone https://github.com/sunny-boy-fqy/ai.git $TARGET_DIR
}

# 3. Config Paths
if (-not (Test-Path $CONFIG_DIR)) { mkdir $CONFIG_DIR | Out-Null }
if (-not (Test-Path $MCP_SERVERS_DIR)) { mkdir $MCP_SERVERS_DIR | Out-Null }

$TARGET_DIR | Out-File -FilePath "$CONFIG_DIR\base_path.config" -Encoding ascii -NoNewline

# 4. Virtual Environment
if (-not (Test-Path $VENV_PATH)) {
    Write-Host "Creating Python virtual environment..."
    python -m venv $VENV_PATH
}

# 5. Install Dependencies
Write-Host "Installing/Updating Python dependencies..."
& "$VENV_PATH\Scripts\pip.exe" install --upgrade pip
& "$VENV_PATH\Scripts\pip.exe" install openai zhipuai groq beautifulsoup4 ebooklib httpx PyJWT tqdm pydantic lxml requests mcp ddgs duckduckgo_search

# 6. MCP Config
$MCP_CONFIG_PATH = "$CONFIG_DIR\mcp_config.json"
if (-not (Test-Path $MCP_CONFIG_PATH)) {
    if (Test-Path "$TARGET_DIR\mcp_servers\web_search_server.py") {
        Copy-Item "$TARGET_DIR\mcp_servers\web_search_server.py" "$MCP_SERVERS_DIR"
    }
    $mcp_content = @"
{
  "servers": {
    "filesystem": {
      "command": "npx.cmd",
      "args": ["-y", "@modelcontextprotocol/server-filesystem"],
      "type": "stdio"
    },
    "web-search": {
      "command": "$VENV_PATH\Scripts\python.exe",
      "args": ["$MCP_SERVERS_DIR\web_search_server.py"],
      "type": "stdio"
    }
  }
}
"@
    $mcp_content | Out-File -FilePath $MCP_CONFIG_PATH -Encoding utf8
}

# 7. PATH Setup
Write-Host "Setting up PATH..." -ForegroundColor Cyan
$CurrentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($CurrentPath -notlike "*$TARGET_DIR*") {
    [Environment]::SetEnvironmentVariable("Path", "$CurrentPath;$TARGET_DIR", "User")
    $env:Path += ";$TARGET_DIR"
    Write-Host "✅ Added $TARGET_DIR to User PATH." -ForegroundColor Green
} else {
    Write-Host "ℹ️ $TARGET_DIR is already in PATH." -ForegroundColor Yellow
}

$versionPath = Join-Path $TARGET_DIR "version.txt"
$version = if (Test-Path $versionPath) { Get-Content $versionPath -Raw } else { "v0.1" }

Write-Host "`n✅ Installation/Update complete!" -ForegroundColor Green
Write-Host "Please restart your terminal to apply PATH changes."
Write-Host "Current version: $version"
