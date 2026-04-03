# Contributing to Tor Monitor Pro

Thank you for your interest in contributing to Tor Monitor Pro! We welcome contributions from the community. Whether it's bug reports, feature requests, code improvements, or documentation, your help makes this project better.

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue on GitHub. When reporting a bug, please include:

- **Description**: Clear description of the bug
- **Steps to Reproduce**: How to reproduce the issue
- **Expected vs Actual**: What you expected vs what actually happened
- **Environment**: Python version, OS, Tor version
- **Logs**: Relevant error messages or logs (without sensitive data)

### Suggesting Features

We're open to new feature ideas! Please open an issue with:

- **Feature Description**: Clear description of the proposed feature
- **Use Case**: Why this feature would be useful
- **Alternatives**: Any alternative approaches you've considered

### Code Contributions

#### Prerequisites

- Python 3.9 or higher
- Git
- Virtual environment (venv/virtualenv)

#### Setup Development Environment

1. **Fork the repository** on GitHub
2. **Clone your fork:**
   ```bash
   git clone https://github.com/your-username/tor-monitor-pro.git
   cd tor-monitor-pro
   ```
3. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   ```
4. **Install development dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

#### Making Changes

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Make your changes** and commit regularly with clear messages
3. **Write or update tests** for your changes
4. **Run quality checks:**
   ```bash
   # Format code
   black tor_monitor_pro/
   
   # Sort imports
   isort tor_monitor_pro/
   
   # Lint code
   ruff tor_monitor_pro/
   
   # Type checking
   mypy tor_monitor_pro/
   
   # Run tests
   pytest
   ```

#### Commit Messages

Please follow these commit message guidelines:

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters
- Reference issues and pull requests liberally after the first line
- Format: `type(scope): subject` (optional but recommended)

Examples:
- `feat(metrics): add percentile calculations`
- `fix(alerts): resolve threshold comparison bug`
- `docs(api): update endpoint examples`
- `refactor(database): simplify query logic`

#### Pull Request Process

1. **Update** the [README.md](README.md) or relevant documentation
2. **Add tests** for new functionality
3. **Update** [CHANGELOG.md](CHANGELOG.md) (if it exists)
4. **Push** to your fork and create a Pull Request
5. **Describe** your changes clearly in the PR description
6. **Link** any related issues

### Documentation

Documentation improvements are always welcome! You can contribute by:

- Fixing typos or unclear explanations
- Adding missing documentation
- Improving code examples
- Translating documentation

## Code Standards

### Python Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use type hints for function arguments and returns
- Docstrings should follow [Google style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)

Example:
```python
def collect_metrics(relay_name: str, timeout: int = 30) -> Dict[str, Any]:
    """Collect metrics from a Tor relay.
    
    Args:
        relay_name: The name of the relay to collect metrics from
        timeout: Timeout in seconds for the collection request (default: 30)
    
    Returns:
        A dictionary containing collected metrics
    
    Raises:
        RelayNotFoundError: If the relay cannot be reached
        TimeoutError: If the collection exceeds the timeout
    """
    # Implementation here
    pass
```

### Testing

- Write tests for all new functionality
- Aim for 80%+ code coverage for new code
- Use pytest as the test framework
- Test both success and failure cases

```bash
# Run tests with coverage
pytest --cov=tor_monitor_pro --cov-report=html
```

## Development Workflow

1. **Branch naming**: Use descriptive names like `feature/multi-relay-support` or `fix/connection-timeout`
2. **Frequent commits**: Commit logically related changes together
3. **Pull requests**: Keep PRs focused on a single feature or fix
4. **Code review**: Address review feedback promptly

## License

By contributing to Tor Monitor Pro, you agree that your contributions will be licensed under its MIT License.

## Questions?

- **GitHub Issues**: Use issues for bugs and features
- **Discussions**: Start a discussion for questions or ideas
- **Tor Forum**: Join [Tor's community forum](https://forum.torproject.org/) for relay-specific questions

## Recognition

Contributors will be recognized in:
- [README.md](README.md) acknowledgments section
- Release notes for major contributions
- Project history

Thank you for helping improve Tor Monitor Pro! 🙏
