## ADDED Requirements

### Requirement: Unknown Group and Repository Key Detection

The configuration validator SHALL report keys in group and repository entries that the module does not
consume. Unknown keys SHALL be reported as warnings, not errors, and SHALL NOT cause validation to fail.

The set of valid group keys SHALL be `visibility`, `homepage_url`, `has_wiki`, `has_issues`, `has_projects`,
`has_discussions`, `allow_merge_commit`, `allow_squash_merge`, `allow_rebase_merge`, `allow_auto_merge`,
`allow_update_branch`, `delete_branch_on_merge`, `web_commit_signoff_required`, `vulnerability_alerts`,
`license_template`, `topics`, `teams`, `collaborators`, `rulesets`, `branch_protections`, `webhooks`, and
`actions`. The set of valid repository keys SHALL be the valid group keys plus `description` and `groups`.

#### Scenario: Unknown key in a group

- **WHEN** a group entry contains a key not in the valid group keys
- **THEN** the validator emits a warning naming the group and the unknown key
- **AND** validation still succeeds

#### Scenario: Unknown key in a repository

- **WHEN** a repository entry contains a key not in the valid repository keys
- **THEN** the validator emits a warning naming the repository and the unknown key
- **AND** validation still succeeds

#### Scenario: Dead linear-history key

- **WHEN** a group or repository entry contains `require_linear_history`
- **THEN** the warning states that it is not a repository setting
- **AND** directs the user to a `required_linear_history` rule in a ruleset or branch protection

#### Scenario: All keys valid

- **WHEN** every key in group and repository entries is in the valid key set
- **THEN** the validator emits no unknown-key warnings
