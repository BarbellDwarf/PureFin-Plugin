# Contributing to PureFin Content Filter

Thank you for your interest in contributing to PureFin Content Filter! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## How to Contribute

### Reporting Bugs

Before creating a bug report:
1. Check the [FAQ](docs/faq.md) and [Troubleshooting Guide](docs/troubleshooting.md)
2. Search existing [GitHub Issues](https://github.com/BarbellDwarf/PureFin-Plugin/issues)
3. Verify the issue with the latest version

When reporting a bug, include:
- Jellyfin version
- Plugin version
- Operating system and version
- Docker/container details if applicable
- Steps to reproduce
- Expected vs actual behavior
- Relevant log excerpts
- Screenshots if applicable

### Suggesting Features

Feature requests are welcome! Please:
1. Check if the feature is already planned (see roadmap)
2. Search existing feature requests
3. Provide clear use cases and benefits
4. Describe the proposed solution
5. Consider implementation challenges

### Contributing Code

#### Development Setup

1. Fork the repository
2. Clone your fork:
```bash
git clone https://github.com/YOUR-USERNAME/PureFin-Plugin.git
cd PureFin-Plugin
```

3. Set up development environment:
```bash
# Build plugin
cd Jellyfin.Plugin.ContentFilter
dotnet build

# Start AI services
cd ../ai-services
docker compose up -d
```

4. Create a feature branch:
```bash
git checkout -b feature/my-feature
```

#### Coding Guidelines

**C# Plugin Code:**
- Follow .NET coding conventions
- Use meaningful variable and method names
- Add XML documentation comments
- Keep methods focused and testable
- Use nullable reference types appropriately
- Handle exceptions gracefully

**Python AI Services:**
- Follow PEP 8 style guide
- Use type hints
- Document functions and classes
- Handle errors appropriately
- Log important operations

**General:**
- Write self-documenting code
- Add comments for complex logic only
- Keep files under 500 lines when possible
- Test your changes thoroughly

#### Commit Messages

Follow conventional commit format:
```
type(scope): subject

body (optional)

footer (optional)
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(plugin): add per-user sensitivity settings

fix(monitor): resolve session tracking memory leak

docs(api): update scene analyzer endpoint documentation
```

#### Pull Request Process

1. Update documentation for any changed functionality
2. Add entries to CHANGELOG.md under [Unreleased]
3. Ensure all tests pass:
```bash
dotnet test
python -m pytest
```

4. Update the README if needed
5. Create pull request with clear description:
   - What problem does it solve?
   - How does it solve it?
   - Any breaking changes?
   - Testing performed

6. Link related issues
7. Wait for review and address feedback

#### Testing

- Add unit tests for new functionality
- Update existing tests if behavior changes
- Run all tests before submitting PR
- Manual testing steps in PR description

### Contributing Documentation

Documentation improvements are always welcome:
- Fix typos and grammar
- Clarify unclear sections
- Add examples and tutorials
- Improve organization
- Translate to other languages

### Contributing AI Models

If contributing AI models or improvements:
1. Document model architecture and training
2. Provide accuracy metrics
3. Include model license and attribution
4. Document inference requirements
5. Provide test cases

## Development Resources

- [Developer Guide](docs/developer-guide.md)
- [API Documentation](docs/api/)
- [Jellyfin Plugin Docs](https://jellyfin.org/docs/general/server/plugins/)
- [Project Planning Docs](copilot-prompts/)

## Review Process

1. **Automated Checks**: CI/CD runs tests and linting
2. **Code Review**: Maintainer reviews code quality and design
3. **Testing**: Manual testing if needed
4. **Approval**: Two approvals required for major changes
5. **Merge**: Squash and merge to main branch

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Acknowledged in release notes
- Credited in documentation

## Questions?

- Check [FAQ](docs/faq.md)
- Review [Documentation](docs/)
- Open a [Discussion](https://github.com/BarbellDwarf/PureFin-Plugin/discussions)
- Ask in pull request comments

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

Thank you for contributing to PureFin Content Filter!
