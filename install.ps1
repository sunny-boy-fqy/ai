# AI Tool Installation & Update Script for Windows

$CONFIG_DIR = "$HOME\.config\ai"
$USER_AI_DIR = "$HOME\.ai"
$MCP_SERVERS_DIR = "$USER_AI_DIR\mcp_servers"
$VENV_PATH = "$CONFIG_DIR\python_venv"

Write-Host "=== 🤖 AI CLI Installation/Update (Windows) ===" -ForegroundColor Cyan

# 0. Helper Functions
function Check-Command($cmd) {
    Get-Command $cmd -ErrorAction SilentlyContinue
}

# 1. Check Dependencies
function Check-Python {
    if (-not (Check-Command "python")) {
        Write-Host "⚠️  未检测到 Python。" -ForegroundColor Yellow
        $useWinget = Read-Host "是否尝试通过 winget 自动安装 Python 3? (y/n)"
        if ($useWinget -eq "y") {
            if (Check-Command "winget") {
                Write-Host "正在通过 winget 安装 Python..."
                winget install Python.Python.3
                Write-Host "✅ Python 安装指令已发送，请在安装完成后重新启动此脚本。" -ForegroundColor Cyan
                exit
            } else {
                Write-Host "❌ 未找到 winget。请访问 https://www.python.org/ 下载并安装 Python 3 (记得勾选 'Add Python to PATH')。" -ForegroundColor Red
                exit 1
            }
        } else {
            exit 1
        }
    }
    
    # Check venv
    try {
        python -m venv --help | Out-Null
    } catch {
        Write-Host "❌ Python 环境不完整（缺少 venv 模块）。请重新安装 Python 并确保勾选了相关组件。" -ForegroundColor Red
        exit 1
    }
}

Check-Python

# 2. Directory Setup
$DEFAULT_DIR = "$HOME\ai"
$TARGET_DIR = Read-Host "请输入安装路径 [默认: $DEFAULT_DIR]"
if ([string]::IsNullOrWhiteSpace($TARGET_DIR)) { $TARGET_DIR = $DEFAULT_DIR }

if (-not (Test-Path $TARGET_DIR)) {
    Write-Host "Creating target directory $TARGET_DIR ..."
    mkdir $TARGET_DIR | Out-Null
}

# 3. Node.js Local Setup (Zero-Pollution)
if (-not (Test-Path $CONFIG_DIR)) { mkdir $CONFIG_DIR | Out-Null }
$NODE_LOCAL_DIR = "$CONFIG_DIR\node"
if (-not (Test-Path "$NODE_LOCAL_DIR\node.exe")) {
    Write-Host "正在安装私有 Node.js 运行环境 (零污染)..." -ForegroundColor Cyan
    $NODE_VERSION = "v20.11.1"
    $NODE_URL = "https://nodejs.org/dist/$NODE_VERSION/node-$NODE_VERSION-win-x64.zip"
    $TEMP_ZIP = "$env:TEMP\node.zip"
    
    Invoke-WebRequest -Uri $NODE_URL -OutFile $TEMP_ZIP
    Expand-Archive -Path $TEMP_ZIP -DestinationPath "$env:TEMP\node-temp" -Force
    
    if (-not (Test-Path $NODE_LOCAL_DIR)) { mkdir $NODE_LOCAL_DIR | Out-Null }
    $extracted = Get-ChildItem -Path "$env:TEMP\node-temp" -Directory | Select-Object -First 1
    Copy-Item -Path "$($extracted.FullName)\*" -Destination $NODE_LOCAL_DIR -Recurse -Force
    
    Remove-Item $TEMP_ZIP -Force
    Remove-Item "$env:TEMP\node-temp" -Recurse -Force
    Write-Host "✅ 本地 Node.js 安装完成。" -ForegroundColor Green
}
$LOCAL_NPX = "$NODE_LOCAL_DIR\npx.cmd"

# 4. Download / Update Source
if (-not (Test-Path "$TARGET_DIR\.git")) {
    if (Check-Command "git") {
        Write-Host "Cloning repository via git..."
        git clone https://github.com/sunny-boy-fqy/ai.git $TARGET_DIR
    } else {
        Write-Host "⚠️ git not found. Falling back to ZIP download..." -ForegroundColor Yellow
        $zipPath = "$env:TEMP\ai-main.zip"
        $zipUrl = "https://github.com/sunny-boy-fqy/ai/archive/refs/heads/main.zip"
        
        Write-Host "Downloading $zipUrl ..."
        Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath
        
        Write-Host "Extracting..."
        Expand-Archive -Path $zipPath -DestinationPath "$env:TEMP\ai-temp" -Force
        
        $extractedDir = Get-ChildItem -Path "$env:TEMP\ai-temp" -Directory | Select-Object -First 1
        Copy-Item -Path "$($extractedDir.FullName)\*" -Destination $TARGET_DIR -Recurse -Force
        
        Remove-Item -Path $zipPath -Force
        Remove-Item -Path "$env:TEMP\ai-temp" -Recurse -Force
        Write-Host "✅ Downloaded source via ZIP." -ForegroundColor Green
    }
} else {
    if (Check-Command "git") {
        Write-Host "Updating via git..."
        Set-Location $TARGET_DIR
        git pull
    } else {
        Write-Host "ℹ️ Repository exists but git is missing. Skipping update." -ForegroundColor Yellow
    }
}

# 5. Config Paths
if (-not (Test-Path $USER_AI_DIR)) { mkdir $USER_AI_DIR | Out-Null }
if (-not (Test-Path $MCP_SERVERS_DIR)) { mkdir $MCP_SERVERS_DIR | Out-Null }
$TARGET_DIR | Out-File -FilePath "$CONFIG_DIR\base_path.config" -Encoding UTF8 -NoNewline

# 6. Virtual Environment
if (-not (Test-Path $VENV_PATH)) {
    Write-Host "Creating Python virtual environment..."
    python -m venv $VENV_PATH
}

# 7. Install Dependencies
Write-Host "Installing/Updating Python dependencies..."
& "$VENV_PATH\Scripts\pip.exe" install --upgrade pip
& "$VENV_PATH\Scripts\pip.exe" install openai zhipuai groq beautifulsoup4 ebooklib httpx PyJWT tqdm pydantic lxml requests mcp ddgs duckduckgo_search

# 8. MCP Config
$MCP_CONFIG_PATH = "$CONFIG_DIR\mcp_config.json"
if (-not (Test-Path $MCP_CONFIG_PATH)) {
    if (Test-Path "$TARGET_DIR\mcp_servers\web_search_server.py") {
        Copy-Item "$TARGET_DIR\mcp_servers\web_search_server.py" "$MCP_SERVERS_DIR"
    }
    $mcp_content = @"
{
  "servers": {
    "filesystem": {
      "command": "$LOCAL_NPX",
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

# 9. PATH Setup
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
