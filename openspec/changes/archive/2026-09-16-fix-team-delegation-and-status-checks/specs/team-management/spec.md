## MODIFIED Requirements

### Requirement: PR Review Request Delegation

The system SHALL manage PR review request delegation settings using the `github_team_settings`
resource when `review_request_delegation` is defined.

The system SHALL accept `algorithm` in any casing and SHALL normalise it to the uppercase form the
GitHub provider requires (`ROUND_ROBIN` or `LOAD_BALANCE`). The provider rejects any other casing
with `expected algorithm to be one of ["ROUND_ROBIN" "LOAD_BALANCE"]`.

#### Scenario: Enable review request delegation

- **GIVEN** a team defines:
  ```yaml
  platform-team:
    description: "Platform engineering"
    review_request_delegation:
      enabled: true
      algorithm: ROUND_ROBIN
      member_count: 2
      notify: true
  ```
- **WHEN** `terraform apply` is executed
- **THEN** a `github_team_settings` resource is created for `platform-team`
- **AND** review request delegation is enabled with round robin algorithm
- **AND** 2 members are assigned per review request
- **AND** the whole team is notified

#### Scenario: Load balance algorithm

- **GIVEN** a team defines `review_request_delegation.algorithm: LOAD_BALANCE`
- **WHEN** `terraform apply` is executed
- **THEN** the delegation uses the load balance algorithm

#### Scenario: Lowercase algorithm is normalised

- **GIVEN** a team defines `review_request_delegation.algorithm: round_robin`
- **WHEN** `terraform apply` is executed
- **THEN** validation passes
- **AND** the value sent to the provider is `ROUND_ROBIN`

#### Scenario: Unsupported algorithm rejected

- **GIVEN** a team defines `review_request_delegation.algorithm: random`
- **WHEN** validation runs
- **THEN** an error reports the algorithm is invalid
- **AND** the error lists `ROUND_ROBIN` and `LOAD_BALANCE` as the valid values

#### Scenario: Default delegation values

- **GIVEN** a team defines `review_request_delegation: { enabled: true }`
- **WHEN** `terraform apply` is executed
- **THEN** the algorithm defaults to `ROUND_ROBIN`
- **AND** the member count defaults to `1`
- **AND** notify defaults to `true`

#### Scenario: No delegation configured

- **GIVEN** a team does not define `review_request_delegation`
- **WHEN** `terraform apply` is executed
- **THEN** no `github_team_settings` resource is created for the team
- **AND** the team uses GitHub's default review request behavior

#### Scenario: Disable delegation

- **GIVEN** a team defines `review_request_delegation: { enabled: false }`
- **WHEN** `terraform apply` is executed
- **THEN** a `github_team_settings` resource is created with delegation disabled
