# CI authentication

Terraform's GitHub provider reads its credential from the `GITHUB_TOKEN` environment variable. This page
explains which credential to put there, what it needs to be allowed to do, and how to keep it out of logs.

## GitHub App or personal access token

Use a **GitHub App installation token**. A personal access token (PAT) works, but it is the weaker choice:

| Concern         | GitHub App installation token               | Personal access token                         |
| --------------- | ------------------------------------------- | --------------------------------------------- |
| Owner           | The organization                            | One person; breaks when they leave            |
| Lifetime        | Minted per run, expires in one hour         | Long-lived (or a rotation chore)              |
| Permissions     | Explicit and auditable, one set per feature | Broad scopes (`repo`, `admin:org`)            |
| Rate limit      | Scales with the installation                | 5,000 requests per hour, shared with the user |
| Separate duties | Easy: one App to plan, another to apply     | Needs two accounts                            |
| Audit log       | Actions are attributed to the App           | Attributed to a person                        |

A PAT is acceptable for a personal account (an App cannot manage user-level settings such as account
membership) or for a first trial. For anything shared, create an App.

## Two identities: plan and apply

Whoever can push a branch to the configuration repository controls the Terraform code that runs in the pull
request plan. That job must therefore not hold a credential that can change the organization. The examples
use two Apps:

| App       | Permissions                  | Where the private key lives                                            | Used by                        |
| --------- | ---------------------------- | ---------------------------------------------------------------------- | ------------------------------ |
| Plan App  | Read-only (see table below)  | Repository secret `TF_PLAN_APP_PRIVATE_KEY`                            | Pull request plan, drift check |
| Apply App | Read and write (table below) | Environment secret `TF_APPLY_APP_PRIVATE_KEY` of the apply environment | Apply on the default branch    |

An environment secret is only released after the environment's required reviewers approve, and only to
workflows on the branches the environment allows. The App IDs are not secret and are stored as repository
variables `TF_PLAN_APP_CLIENT_ID` and `TF_APPLY_APP_CLIENT_ID` (the `client-id` input of the token action).

If you accept the trade-off, one App with write permissions can serve every workflow: set both variables
to the same value and store the same key in both places.

## Minimum App permissions

Grant only the rows for the features you use. The plan App takes the same rows at **read** level. The
names follow the permission picker on the App's settings page.

| Feature in `config/`                        | Permission                       | Level          |
| ------------------------------------------- | -------------------------------- | -------------- |
| Any repository management                   | Repository: Metadata             | Read           |
| Repositories, branch protection, rulesets   | Repository: Administration       | Read and write |
| Collaborators, team access to repositories  | Repository: Administration       | Read and write |
| New repositories created with `auto_init`   | Repository: Contents             | Read and write |
| Repository webhooks                         | Repository: Webhooks             | Read and write |
| Repository Actions secrets and variables    | Repository: Secrets, Variables   | Read and write |
| Repository Dependabot secrets               | Repository: Dependabot secrets   | Read and write |
| Environments (and their secrets, variables) | Repository: Environments         | Read and write |
| Teams, team and organization membership     | Organization: Members            | Read and write |
| Organization rulesets, settings, Actions    | Organization: Administration     | Read and write |
| Organization webhooks                       | Organization: Webhooks           | Read and write |
| Organization Actions secrets and variables  | Organization: Secrets, Variables | Read and write |
| Organization Dependabot secrets             | Organization: Dependabot secrets | Read and write |
| Security manager teams                      | Organization: Administration     | Read and write |

Environment secrets and variables also need the repository Secrets and Variables permissions. Assigning a
security manager role may additionally need Organization: Custom organization roles.

Install the App on **all repositories** of the organization, or on every repository the configuration
manages. A repository outside the installation fails with `404 Not Found`.

The table follows the provider's resources when it was written. When you enable a new module feature, run a
plan with the plan identity first: a missing permission shows up as a `403` naming the endpoint.

## Passing the token to Terraform

The provider needs no `token` argument; `GITHUB_TOKEN` in the environment is enough, and the `owner` stays
in the `provider "github"` block.

GitHub Actions: mint the installation token in the job and expose it to the one step that needs it.

```yaml
- name: Create GitHub App token
  id: app-token
  uses: actions/create-github-app-token@f418cff399f7aef4c2f0ad47e25ca7a6abbdd6fc # v3.4.0
  with:
    client-id: ${{ vars.TF_PLAN_APP_CLIENT_ID }}
    private-key: ${{ secrets.TF_PLAN_APP_PRIVATE_KEY }}
    owner: ${{ github.repository_owner }}

- name: Terraform plan
  run: terraform plan -input=false
  env:
    GITHUB_TOKEN: ${{ steps.app-token.outputs.token }}
```

Using a PAT instead: drop the first step and set `GITHUB_TOKEN: ${{ secrets.TF_GITHUB_TOKEN }}`.

Jenkins: bind a "GitHub App" credential (from the GitHub Branch Source plugin) with `withCredentials`
and a `usernamePassword` binding whose `passwordVariable` is `GITHUB_TOKEN`; the plugin exchanges the key
for a short-lived installation token. Create one credential for the plan App (Validate and Plan stages) and
one for the apply App (Apply stage), as in GitHub Actions. The `tfcmt` plan comment also needs the plan
App to have Repository: Pull requests at read and write level. Jenkins needs the private key in PKCS#8
format:

```bash
openssl pkcs8 -topk8 -inform PEM -outform PEM -in downloaded-key.pem -out converted-key.pem -nocrypt
```

Backend credentials (state bucket, Terraform Cloud token) are separate; see the examples in `ci/backends/`.

## Keeping the token out of logs

- Pass the token only through `env:` on the steps that run Terraform. Never write it into a file, a
  command line, an `echo`, or a job output other than the step output of the token action (which GitHub
  masks automatically).
- Do not run Terraform with `TF_LOG=DEBUG` or `TRACE` in shared runs: provider debug logs can include
  request headers.
- A saved plan file (`-out`) holds sensitive values in clear text. Do not upload it as an artifact and do
  not keep it with `scripts/detect-drift.sh --plan-file` on a shared runner.
- Terraform prints sensitive values as `(sensitive value)` in plan output and the drift report prints
  `(sensitive)`. A plain `terraform show -json` does not hide them, so do not post it anywhere.
- The state holds secret values for managed secrets and webhooks: use an encrypted private backend.

## Creating the Apps

1. In the organization settings, go to **Developer settings → GitHub Apps → New GitHub App**.

1. Give it a name, any homepage URL, untick **Webhook → Active**, and set the permissions from the table
   (read-only for the plan App).

1. Under **Where can this GitHub App be installed?** choose **Only on this account**.

1. After creating it, copy the **Client ID**, then **Generate a private key** and store it as the secret.

1. **Install App** on the organization, with access to all repositories.

1. Create the apply environment (for example `github-org-apply`) under **Settings → Environments** of the
   configuration repository, add required reviewers, restrict it to the default branch, and add the Apply
   App's private key as an environment secret.

Keep each App scoped to Terraform. General CI pipelines should use a different credential: the Apply App can
change repository settings and organization membership.
