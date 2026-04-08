# Consumer Example

This directory shows the minimal setup required to use `github-as-yaml` as a
reusable Terraform module.

## Directory structure

```text
examples/consumer/
├── main.tf                 # Provider block + module call
├── outputs.tf              # Pass-through of module outputs
├── backend.tf.example      # Remote backend templates (copy to backend.tf)
├── Makefile                # Convenience shortcuts
└── config/
    ├── config.yml          # Organization name and subscription tier
    ├── group/
    │   └── base.yml        # Shared settings inherited by repositories
    ├── repository/
    │   └── example.yml     # Repository definitions
    └── ruleset/            # Ruleset definitions (empty by default)
```

## Quick start

### 1. Copy this directory

```bash
cp -r examples/consumer /path/to/your-org-configs
cd /path/to/your-org-configs
```

### 2. Edit `config/config.yml`

Replace `your-org-name` with your GitHub organization name and set the correct
`subscription` tier (`free`, `pro`, `team`, or `enterprise`).

### 3. Edit `main.tf`

Replace `your-org-name` in the `provider "github"` block and pin the module to the
desired release:

```hcl
provider "github" {
  owner = "your-org-name"
}

module "github_org" {
  source  = "gjed/config-as-yaml/github"
  version = "~> 1.0"

  config_path = "${path.root}/config"
}
```

### 4. Define your repositories

Edit `config/repository/` YAML files. Each top-level key is a repository name:

```yaml
my-service:
  description: "My service repository"
  groups:
    - base
```

### 5. Initialize and apply

```bash
export GITHUB_TOKEN="ghp_..."
make init && make plan && make apply
```

## Module variables

| Variable          | Type          | Default      | Description                                                    |
| ----------------- | ------------- | ------------ | -------------------------------------------------------------- |
| `config_path`     | `string`      | *(required)* | Path to the `config/` directory. Use `"${path.root}/config"`.  |
| `webhook_secrets` | `map(string)` | `{}`         | Webhook secrets keyed by the name used in `env:NAME` patterns. |

> **Important:** `config_path` must be a static string. Computed values (data sources,
> locals with unknown values) are not supported because `file()` and `fileset()` are
> evaluated at plan time.

## Module outputs

| Output                   | Description                                                    |
| ------------------------ | -------------------------------------------------------------- |
| `organization`           | GitHub organization name read from `config.yml`                |
| `repository_count`       | Number of managed repositories                                 |
| `repositories`           | Map of repository names → `{ name, url, ssh_url, visibility }` |
| `subscription_tier`      | Subscription tier from `config.yml`                            |
| `subscription_warnings`  | Warning when rulesets are skipped on free tier                 |
| `duplicate_key_warnings` | Warning when the same key appears in multiple config files     |

## Remote state (optional)

Copy `backend.tf.example` to `backend.tf` and uncomment the block matching your
preferred state backend (S3, GCS, Azure, or Terraform Cloud). Do not commit
`backend.tf` to version control.

## Migrating an existing fork

If you previously forked this repository and used it as a root module, follow these
steps to migrate to the module pattern:

1. Create a new consumer directory (this example) pointing at the versioned module.

1. Run the migration helper to generate `terraform state mv` commands:

   ```bash
   # From your existing Terraform directory:
   ../../scripts/migrate-state.sh --dry-run
   ```

1. Review the generated commands, then run without `--dry-run` to execute them.

1. Add a `provider "github"` block to your new `main.tf` with `owner = "your-org"`.

1. Remove the old Terraform root directory.
