## 1. Provider constraint

- [x] 1.1 Confirm `required_reviewers` exists in provider 6.12.0 for repository and organization
  rulesets (it does); no floor change needed

## 2. Repository rulesets

- [x] 2.1 Add `required_reviewers` (default `[]`) to the typed `rulesets` variable in
  `modules/repository/variables.tf`
- [x] 2.2 Add `team_ids` variable (`map(string)`, default `{}`) to `modules/repository`
- [x] 2.3 Add the dynamic `required_reviewers` block to `pull_request` in
  `modules/repository/main.tf`, resolving slug via `team_ids`

## 3. Slug resolution and organization rulesets

- [x] 3.1 Add `reviewer_team_slugs` local in `yaml-config.tf` (repository and organization rulesets)
- [x] 3.2 Add `team_ids` local in `main.tf`: managed teams from module outputs, remaining slugs from
  `data "github_team" "reviewers"`
- [x] 3.3 Pass `team_ids` to `module "repositories"`
- [x] 3.4 Add the dynamic `required_reviewers` block to `pull_request` in
  `github_organization_ruleset`, guarded against null

## 4. Validation

- [x] 4.1 Add `required_reviewers` validation to `validate_rulesets` in `scripts/validate-config.py`
- [x] 4.2 Add `tests/test_validate_required_reviewers.py`

## 5. Documentation

- [x] 5.1 `wiki/Configuration-Reference.md` (edited in the wiki repo; published after release, not part of this PR)
- [x] 5.2 `config/ruleset/default-rulesets.yml` commented example
- [x] 5.3 `AGENTS.md`
- [x] 5.4 `skills/ruleset-authoring/SKILL.md`

## 6. Verification

- [x] 6.1 `terraform fmt -check` and `terraform validate`
- [x] 6.2 `terraform plan` on a scratch config using a managed-team slug, an external slug, and a
  numeric id, for both a repository and an organization ruleset
- [x] 6.3 Full pytest suite and `pre-commit run --all-files`
