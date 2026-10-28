# Security Policy

## Reporting a vulnerability

Report vulnerabilities privately through GitHub:
[Report a vulnerability](https://github.com/gjed/terraform-github-config-as-yaml/security/advisories/new)
(Security tab, then "Report a vulnerability"). Do not open public issues, pull requests, or discussions for
security problems.

Include, where possible:

- what the issue is and what an attacker can do with it
- the module version and the Terraform and `integrations/github` provider versions
- the YAML configuration or steps needed to reproduce it, with secrets removed

You will get an acknowledgement within 7 days. Confirmed issues are tracked in a private GitHub security
advisory, fixed in a new release, and disclosed in that advisory once the release is out. Reporters are
credited in the advisory unless they ask to stay anonymous.

## Scope

In scope:

- the module code (`*.tf`, `modules/`) producing a configuration weaker than the YAML asks for, for example a
  ruleset, visibility, permission or webhook setting that is silently dropped or widened
- secret values leaking outside Terraform state, for example into plan output, error messages or outputs
- the helper scripts in `scripts/` and the GitHub Actions workflows of this repository

Out of scope:

- secret values stored in Terraform state: this is how Terraform works; use an encrypted remote backend
- misconfiguration in your own YAML
- vulnerabilities in Terraform or the `integrations/github` provider itself; report those upstream

## Supported versions

Security fixes are released for the latest major version only.
