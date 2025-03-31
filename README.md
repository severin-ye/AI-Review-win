# AI Review Assistant

A powerful AI-driven text review tool that helps users quickly and efficiently complete document review tasks.

## Features

- 🤖 Multiple Model Support: Integrated with various AI models (GPT-4o, GPT-4o-mini, Qwen, etc.)
- 📝 Smart Review: Automatic text error detection and correction with structured output
- 🔄 Batch Processing: Support for batch file processing
- 📊 Real-time Progress: Intuitive progress display interface
- 🎨 Theme Customization: Customizable interface themes
- 🔐 Security: Comprehensive key verification mechanism
- 🏥 Medical RAG System: Medical document retrieval and fact checking
- 🔍 Semantic Analysis: Intelligent text segmentation and analysis

## System Requirements

- Windows 10 or higher
- Python 3.8+
- Stable internet connection

## Installation

1. Clone the repository:
```bash
git clone https://github.com/severin-ye/AI-Review-win.git
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the program:
```bash
python main.py
```

## Project Structure

Main directory descriptions:

- `config/`: Configuration management directory
  - Core config modules and managers
  - Theme settings and application constants
  - Path management for consistent file organization
- `build/`: Build tools directory
  - Installation and packaging utilities
  - Build scripts and spec files in `specs/` subdirectory
  - Version information management
- `src/`: Source code directory
  - `core/`: Core text processing and AI review functionality
  - `ui/`: User interface components and pages
  - `utils/`: Utility functions for text, file and AI operations
  - `security/`: Key management and verification systems
- `tests/`: Test files directory
- `hide_file/`: Hidden runtime files
  - `config_files/`: Application configuration files
  - `temp_files/`: Temporary processing files
    - `original_files/`: Original files for review
    - `reviewed_files/`: Processed files after review
  - `medical_reference/`: Medical document storage
    - `documents/`: User uploaded medical documents
    - `chroma_db/`: Vector database for medical RAG

## Usage Guide

1. Enter a valid API key in the configuration interface on first use
2. Select files or folders to process
3. Choose review mode (automatic/manual)
4. Optionally upload medical reference documents for fact checking
5. Start processing and wait for results

## Medical RAG System

The system includes an integrated medical Retrieval-Augmented Generation (RAG) system:

- Support for uploading medical reference documents (PDF, TXT, CSV, Word)
- Automatic document vectorization and indexing
- Medical fact checking integration with AI review
- Contextual medical information retrieval during review process

## Configuration Guide

- Support for multiple AI model configurations:
  - GPT-4o: Advanced text review and analysis
  - GPT-4o-mini: Faster processing for simpler tasks
  - Qwen: Alternative model with comparable capabilities
- Customizable interface themes with color and font settings
- Flexible text processing parameter settings
- Medical RAG system configuration options

## Development Guide

For those interested in development, please ensure:

1. Follow the project's code standards
2. Conduct thorough testing before submission
3. Update relevant documentation
4. Use the project's modular architecture for extensions

## Additional Documentation

- [Project Structure Description](doc_Structure_Description.md): Detailed description of the project structure and architecture
- [Project Change Log](doc_log.md): Comprehensive record of all changes and updates to the project

