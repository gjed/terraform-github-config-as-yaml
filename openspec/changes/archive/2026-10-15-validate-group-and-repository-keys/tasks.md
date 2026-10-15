## 1. Remove dead key

- [x] 1.1 Delete `require_linear_history: true` from the `oss` group in `config/group/default-groups.yml`

## 2. Validator

- [x] 2.1 Add `VALID_GROUP_KEYS` and `VALID_REPOSITORY_KEYS` to `scripts/validate-config.py`
- [x] 2.2 Emit a warning for each unknown key in group and repository entries, with a dedicated message for
      `require_linear_history`
- [x] 2.3 Add unit tests covering unknown key, `require_linear_history`, and all-valid-keys cases
- [x] 2.4 Confirm `config/`, `examples/`, and `tests/e2e/config/` produce no new warnings

## 3. Documentation

- [x] 3.1 Note in `docs/CONFIGURATION.md` that linear history is branch-level only (ruleset rule or branch
      protection)

## 4. Spec Updates

- [x] 4.1 Archive the change into `openspec/specs/` after implementation is complete

## 5. Verification

- [x] 5.1 Run `python scripts/validate-config.py` and the test suite
- [x] 5.2 Run `pre-commit run --all-files`
