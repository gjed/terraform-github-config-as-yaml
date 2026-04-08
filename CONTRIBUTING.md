# Contributing to GitHub As YAML

Thank you for your interest in contributing! This document provides guidelines and instructions
for contributing to this project.

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By
participating, you are expected to uphold this code. Please report unacceptable behavior to the
project maintainers.

## How to Contribute

### Reporting Issues

Before creating an issue, please:

1. **Search existing issues** to avoid duplicates
1. **Use the issue templates** if available
1. **Include relevant details**:
   - Terraform version (`terraform version`)
   - GitHub Provider version
   - Operating system
   - Steps to reproduce
   - Expected vs actual behavior
   - Relevant configuration (sanitized of secrets)

### Suggesting Features

Feature requests are welcome! Please:

1. **Check existing issues** to see if it's already proposed
1. **Describe the use case** - what problem does it solve?
1. **Propose a solution** if you have one in mind
1. **Consider alternatives** you've thought about

### Submitting Pull Requests

1. **Fork the repository** and create your branch from `main`
1. **Follow the setup instructions** below
1. **Make your changes** following the code style guidelines
1. **Test your changes** thoroughly
1. **Update documentation** if needed
1. **Submit a pull request** with a clear description

## Development Setup

### Prerequisites

- [Terraform](https://www.terraform.io/downloads) >= 1.0
- [pre-commit](https://pre-commit.com/) for git hooks
- [tflint](https://github.com/terraform-linters/tflint) for Terraform linting
- [Python](https://www.python.org/) 3.x for validation scripts

### Installation

1. Clone your fork:

   ```bash
   git clone https://github.com/YOUR_USERNAME/terraform-github-config-as-yaml.git
   cd terraform-github-config-as-yaml
   ```

1. Install pre-commit hooks:

   ```bash
   pip install pre-commit
   pre-commit install
   ```

1. Install tflint:

   ```bash
   curl -s https://raw.githubusercontent.com/terraform-linters/tflint/master/install_linux.sh | bash
   ```

1. Verify your setup:

   ```bash
   terraform version
   tflint --version
   pre-commit run --all-files
   ```

### Running Tests

```bash
# Validate Terraform configuration
terraform init
terraform validate

# Run all pre-commit hooks
pre-commit run --all-files

# Run specific hook
pre-commit run terraform-fmt --all-files
```

## Code Style

### Terraform

- **Formatting**: Use `terraform fmt` (enforced by pre-commit)
- **Naming**: Use snake_case for resources, variables, and outputs
- **Variables**: Always include `description` and `type`
- **Locals**: Use for computed values and reducing repetition
- **Modules**: Keep focused and single-purpose

Example:

```hcl
variable "repository_name" {
  description = "Name of the GitHub repository"
  type        = string
}

locals {
  full_name = "${var.owner}/${var.repository_name}"
}

resource "github_repository" "this" {
  name        = var.repository_name
  description = var.description
  visibility  = var.visibility
}
```

### YAML

- **Indentation**: 2 spaces
- **Quotes**: Use quotes for strings with special characters
- **Comments**: Add comments for complex configurations
- **Keys**: Use snake_case for consistency with Terraform

Example:

```yaml
# Repository configuration
repositories:
  my-app:
    description: "My application repository"
    visibility: private
    has_issues: true
```

### Markdown

- **Headings**: Use ATX-style (`#`) headings
- **Lists**: Use `-` for unordered lists
- **Code blocks**: Always specify the language
- **Line length**: Keep lines under 120 characters when practical
- **Links**: Use reference-style links for repeated URLs

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```text
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Formatting, no code change
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance tasks

Examples:

```text
feat(rulesets): add support for tag protection rules

fix(teams): handle team permission inheritance correctly

docs(readme): add troubleshooting section for rate limits
```

## Pull Request Guidelines

### Before Submitting

- [ ] Code follows the style guidelines
- [ ] Pre-commit hooks pass (`pre-commit run --all-files`)
- [ ] Terraform validates (`terraform validate`)
- [ ] Documentation is updated if needed
- [ ] Commit messages follow conventions

### PR Description

Include:

1. **What** - Brief description of changes
1. **Why** - Motivation or issue reference
1. **How** - Implementation approach (if not obvious)
1. **Testing** - How you tested the changes

Example:

```markdown
## What
Add support for repository rulesets with tag protection.

## Why
Closes #42 - Users need to protect release tags from deletion.

## How
Extended the ruleset module to accept `target = "tag"` and added
corresponding validation for tag-specific rules.

## Testing
- Added example configuration in `examples/tag-protection`
- Tested against a personal GitHub organization
- Verified plan output shows correct resources
```

### Review Process

1. Maintainers will review your PR
1. Address any feedback or requested changes
1. Once approved, a maintainer will merge the PR
1. Your contribution will be included in the next release

## Project Structure

```text
.
├── config.yml              # Example configuration
├── main.tf                 # Root module entry point
├── variables.tf            # Input variables
├── outputs.tf              # Output values
├── versions.tf             # Provider requirements
├── modules/
│   └── repository/         # Repository sub-module
├── examples/               # Usage examples
└── docs/                   # Additional documentation
```

## Getting Help

- **Questions**: Open a [Discussion](../../discussions)
- **Bugs**: Open an [Issue](../../issues)

## Recognition

Contributors are recognized in:

- Release notes for significant contributions
- README acknowledgments for major features

Thank you for contributing!
