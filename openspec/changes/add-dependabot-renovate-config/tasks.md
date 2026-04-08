## Prerequisites

- [ ] 0.1 Complete `add-file-provisioning-workflow` implementation (dependency)

## 1. Configuration Schema

- [ ] 1.1 Design Dependabot config schema (mirror official Dependabot v2 schema)
- [ ] 1.2 Design Renovate config schema (common options, allow raw JSON passthrough)
- [ ] 1.3 Add `dependabot` block to repository YAML schema
- [ ] 1.4 Add `renovate` block to repository YAML schema
- [ ] 1.5 Add dependency config support to groups schema
- [ ] 1.6 Update validation scripts for new configuration options

## 2. Terraform Implementation

- [ ] 2.1 Implement Dependabot YAML generation from configuration
- [ ] 2.2 Implement Renovate JSON generation from configuration
- [ ] 2.3 Integrate with file provisioning workflow
- [ ] 2.4 Handle config merging from groups (updates lists, package rules)
- [ ] 2.5 Implement conflict detection for same ecosystem in multiple groups
- [ ] 2.6 Add dual-tool warning when both configured on same repo

## 3. Presets and Templates

- [ ] 3.1 Create common Dependabot presets (npm-weekly, docker-monthly, etc.)
- [ ] 3.2 Create common Renovate presets (recommended, automerge-minor, etc.)
- [ ] 3.3 Implement preset expansion logic
- [ ] 3.4 Document available presets

## 4. Validation

- [ ] 4.1 Add validation for Dependabot ecosystems
- [ ] 4.2 Add validation for schedule intervals
- [ ] 4.3 Add validation for required fields
- [ ] 4.4 Add warning for dual-tool configuration

## 5. Documentation

- [ ] 5.1 Document Dependabot configuration options
- [ ] 5.2 Document Renovate configuration options
- [ ] 5.3 Add examples for different project types (npm, docker, python, etc.)
- [ ] 5.4 Add migration guide (Dependabot \<-> Renovate)
- [ ] 5.5 Document configuration merging behavior

## 6. Testing

- [ ] 6.1 Test basic Dependabot configuration generation
- [ ] 6.2 Test basic Renovate configuration generation
- [ ] 6.3 Test configuration merging from groups
- [ ] 6.4 Test preset expansion
- [ ] 6.5 Test validation error cases
- [ ] 6.6 Test dual-tool scenarios
