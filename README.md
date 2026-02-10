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
- `config/`: Directory for private configurations (stored in a separate repository).
