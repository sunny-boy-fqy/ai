# AI CLI Tool

A simple command-line interface for interacting with various AI providers (OpenAI, ZhipuAI, Groq, etc.).

## Features
- Support for multiple AI providers and models.
- Interactive chat mode with memory.
- Easy provider and model management.
- Dynamic base path configuration.

## Installation
1. Clone this repository.
2. Clone your configuration repository into the `config` directory (or run `configure.sh` to initialize).
3. Run `./configure.sh` to set up the `ai` alias in your `.bashrc`.
4. Run `source ~/.bashrc`.

## Usage
- `ai [prompt]` - Quick query.
- `ai chat` - Enter interactive chat mode.
- `ai new` - Add a new provider or API key.
- `ai model` - Switch or manage models.
- `ai switch` - Switch between providers.
- `ai status` - Show current status and asset statistics.

## Project Structure
- `ai_caller.py`: Main logic for AI interaction.
- `ai_run.sh`: Entry point script.
- `configure.sh`: Setup script.
- `mcp_tools.py`: MCP tool integration module.
- `config/`: Directory for private configurations (stored in a separate repository).

## MCP 工具支持

本项目现已支持 Model Context Protocol (MCP)，允许 AI 调用外部工具。

### 配置 MCP Tools

在 `~/.config/ai/mcp_config.json` 中配置你的 MCP 服务器。例如：

```json
{
  "servers": {
    "filesystem": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-filesystem", "/path/to/search"],
      "type": "stdio"
    }
  }
}
```
