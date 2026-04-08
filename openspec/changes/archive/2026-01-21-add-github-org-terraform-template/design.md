# Design: GitHub Organization Terraform Template

## Context

Organizations managing GitHub repositories face challenges with manual configuration:

- Inconsistent repository settings across teams
- No audit trail for configuration changes
- Difficulty enforcing security policies
- Time-consuming onboarding of new repositories

This template provides a factory pattern implementation using Terraform and YAML configuration, enabling
GitOps workflows for GitHub organization management.

**Constraints:**

- Must work with GitHub Free tier (limited ruleset support for private repos)
- Must be easily forkable as a GitHub template
- Must support both personal accounts and organizations
- Configuration should be human-readable (YAML)

## Goals / Non-Goals

**Goals:**

- Provide a minimal, working template that users can fork and customize
- Support repository creation and configuration management
- Enable configuration groups for DRY configuration
- Support repository rulesets for branch protection
- Document all features and customization options

**Non-Goals:**

- Managing GitHub Actions workflows within repositories
- Managing GitHub organization settings (billing, security policies)
- Supporting GitHub Enterprise Server (focus on github.com)
- Providing a web UI or CLI wrapper

## Decisions

### Decision 1: YAML-native configuration

**What:** Use Terraform's native `yamldecode()` to read configuration directly from YAML files.

**Why:**

- No preprocessing or conversion scripts needed
- Human-readable configuration format
- Easy to validate and lint
- Familiar to users from other IaC tools (Kubernetes, Ansible)

**Alternatives considered:**

- Terraform variables (`.tfvars`) - less readable, harder to structure
- JSON configuration - less human-friendly
- HCL locals - mixes configuration with code

### Decision 2: Configuration groups pattern

**What:** Allow repositories to inherit from multiple named configuration groups that are merged
sequentially.

**Why:**

- Reduces duplication (DRY principle)
- Enables composable configurations (e.g., `["base", "oss"]`)
- Allows overrides at repository level

**Merge strategy:**

- Single values: later groups override earlier ones
- Lists (topics, rulesets): merged and deduplicated
- Maps (teams, collaborators): merged with later overriding

### Decision 3: Separate configuration files

**What:** Split configuration into four files:

- `config/config.yml` - Organization and global settings
- `config/groups.yml` - Configuration group definitions
- `config/repositories.yml` - Repository definitions
- `config/rulesets.yml` - Ruleset definitions

**Why:**

- Easier to navigate and edit
- Supports different change frequency (rulesets change less than repos)
- Clearer separation of concerns

### Decision 4: Repository module abstraction

**What:** Use a Terraform module to encapsulate repository resource management.

**Why:**

- Clean interface between configuration and resources
- Easier to extend with new features
- Supports testing in isolation

### Decision 5: Example-based documentation

**What:** Provide example configurations rather than exhaustive documentation.

**Why:**

- Templates are meant to be forked and modified
- Examples are easier to understand than abstract documentation
- Users can see working patterns immediately

## File Structure

```text
github-as-yaml/
├── config/                           # User-editable YAML configuration
│   ├── config.yml                    # Organization name, subscription tier
│   ├── groups.yml                    # Configuration groups (oss, internal)
│   ├── repositories.yml              # Repository definitions
│   └── rulesets.yml                  # Ruleset definitions
├── terraform/
│   ├── main.tf                       # Provider config, module instantiation
│   ├── yaml-config.tf                # YAML parsing and transformation
│   ├── outputs.tf                    # Output values
│   └── modules/
│       └── repository/               # Repository resource module
│           ├── main.tf               # Resources
│           ├── variables.tf          # Input variables
│           └── outputs.tf            # Module outputs
├── scripts/
│   ├── validate-config.py            # Configuration validation
│   └── onboard-repos.sh              # Import existing repositories
├── docs/
│   ├── QUICKSTART.md                 # Getting started guide
│   ├── CONFIGURATION.md              # Configuration reference
│   └── CUSTOMIZATION.md              # How to extend
├── .env.example                      # Environment variables template
├── .gitignore                        # Ignore patterns
├── Makefile                          # Common operations
└── README.md                         # Project overview
```

## Risks / Trade-offs

### Risk: GitHub API rate limiting

**Mitigation:** Terraform provider handles rate limiting. Document best practices for large organizations.

### Risk: State file contains sensitive information

**Mitigation:** Document remote backend setup (S3, GCS, Terraform Cloud). Include warnings about not
committing state files.

### Risk: Breaking changes in GitHub provider

**Mitigation:** Pin provider version (`~> 6.0`). Include upgrade notes in documentation.

### Trade-off: Simplicity vs. flexibility

**Decision:** Favor simplicity. Start with essential features (repository, teams, rulesets). Users can
extend as needed.

### Trade-off: Opinionated defaults vs. minimal configuration

**Decision:** Provide sensible defaults (e.g., squash merge, delete branch on merge) but make everything
overridable.

## Migration Plan

N/A - This is a new template project, not a migration.

## Open Questions

1. **Should we include team management?** Currently, teams are referenced by slug but not created. Users
   manage teams separately.

1. **Should we support importing existing repositories?** The module works with existing repos, but
   import workflow could be documented better.

## Deferred to Future Specs

- **CI/CD workflow**: Users can implement their own GitHub Actions workflow based on their requirements.
  Common patterns could be documented in a future spec.
