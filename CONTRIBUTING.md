# Contributing to Geepers Kernel

Thank you for your interest in contributing to `geepers-kernel`! This guide will help you get started with the contribution process.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Guidelines](#coding-guidelines)

## Code of Conduct
In the interest of fostering an open and welcoming environment, we expect all contributors to be respectful and considerate of others. By participating in this project, you agree to:
- Be respectful of different viewpoints and experiences.
- Gracefully accept constructive criticism.
- Focus on what is best for the community.
- Show empathy towards other community members.

## How Can I Contribute?
- **Reporting Bugs**: Ensure the bug was not already reported by searching on GitHub under [Issues](https://github.com/your-repo/geepers-kernel/issues). If you're unable to find an open issue addressing the problem, [open a new one](https://github.com/your-repo/geepers-kernel/issues/new).
- **Suggesting Enhancements**: Open an issue with the tag "enhancement" to suggest new features or improvements.
- **Code Contributions**: Follow the [Pull Request Process](#pull-request-process) to submit code changes.

## Development Setup
1. **Clone the Repository**: `git clone https://github.com/your-repo/geepers-kernel.git`
2. **Install Dependencies**: Use `poetry` or `pip` to install dependencies. Run `poetry install` if using Poetry.
3. **Set Up Environment**: Configure environment variables or a `.env` file for API keys and other settings.
4. **Run Tests**: Use `pytest` to run the test suite with `poetry run pytest`.

## Pull Request Process
1. **Create a Branch**: Create a branch with a descriptive name related to the issue or feature (e.g., `feature/add-cli-tool` or `bugfix/fix-rate-limiting`).
2. **Make Your Changes**: Implement your changes and commit them with meaningful commit messages.
3. **Update Documentation**: Update any relevant documentation or add comments to your code as necessary.
4. **Run Tests**: Ensure all tests pass before submitting your PR.
5. **Submit Your PR**: Open a pull request against the `develop` branch. Fill in the PR template with details about your changes.
6. **Code Review**: Address any feedback from maintainers and make necessary revisions.

## Coding Guidelines
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python code.
- Write clear, concise commit messages.
- Include docstrings for all public modules, functions, classes, and methods.
- Add unit tests for new functionality and ensure existing tests pass.

Thank you for contributing to `geepers-kernel` and helping make it better!
