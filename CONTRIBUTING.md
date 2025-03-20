# Contributing to State of Mika SDK

Thank you for your interest in contributing to the State of Mika SDK! This document provides guidelines and instructions for contributing to this project.

## Code of Conduct

Please help us keep this project open and inclusive. By participating, you are expected to uphold this code of conduct.

## How Can I Contribute?

### Reporting Bugs

This section guides you through submitting a bug report. Following these guidelines helps maintainers understand your report, reproduce the issue, and fix it.

- **Use the GitHub issue tracker** - Submit bugs using the [GitHub issue tracker](https://github.com/state-of-mika/sdk/issues).
- **Use a clear and descriptive title** for the issue.
- **Describe the exact steps to reproduce the problem** in as much detail as possible.
- **Provide specific examples** to demonstrate the steps.
- **Describe the behavior you observed** after following the steps and why you consider it a problem.
- **Explain which behavior you expected to see** instead and why.
- **Include screenshots or animated GIFs** if they help illustrate the issue.
- **Include details about your environment** like Python version, OS, etc.

### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion, including completely new features and minor improvements to existing functionality.

- **Use the GitHub issue tracker** with the enhancement label.
- **Use a clear and descriptive title** for the issue.
- **Provide a detailed description of the suggested enhancement** in as much detail as possible.
- **Explain why this enhancement would be useful** to most users.

### Pull Requests

- **Fill in the required template** provided when creating a pull request.
- **Include screenshots or animated GIFs** in your pull request whenever possible.
- **Follow the Python style guide**.
- **Document new code** based on the documentation style used in the project.
- **End all files with a newline**.
- **Make sure your code passes all tests**.

## Development Environment Setup

1. Fork the repository.
2. Clone your fork:
   ```
   git clone https://github.com/your-username/sdk.git
   cd sdk
   ```
3. Set up a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
4. Install development dependencies:
   ```
   pip install -e ".[dev]"
   ```
5. Set up pre-commit hooks:
   ```
   pre-commit install
   ```

## Running Tests

Run tests using pytest:

```
pytest
```

To run a specific test file:

```
pytest tests/test_specific_file.py
```

## Code Style

This project follows the [Black](https://black.readthedocs.io/en/stable/) code style. You can format your code automatically with:

```
black .
```

## Documentation

- All public modules, functions, classes, and methods should have docstrings.
- Use [Google style docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings).

## Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line

## Creating a Release

1. Update the version number in `setup.py`, `pyproject.toml`, and `__init__.py`.
2. Update the CHANGELOG.md file.
3. Create a new GitHub release with a detailed description of changes.

## License

By contributing, you agree that your contributions will be licensed under the project's MIT License. 