---
title: 'Document skill custom configuration in skill-build.md'
type: 'chore'
created: '2026-05-05'
status: 'done'
route: 'one-shot'
---

## Intent

**Problem:** `skill-build.md` documented the skill authoring contract but had no coverage of the custom configuration feature delivered in Epic 8 stories 8.1–8.3: the `config_fields` manifest schema, the `configuration:` config.yaml block, `self.configuration` injection, and the `nimble add` interactive prompting flow.

**Approach:** Add `self.configuration` to Section 1, `config_fields` to Section 4, `configuration:` to Section 5, a new Section 6 "Skill Custom Configuration" with a four-step walkthrough, a configuration anti-pattern to Section 8, and two new maintenance rows to Section 9. Renumber old Sections 6–8 to 7–9.

## Suggested Review Order

- [`.ai/skill-build.md:41`](../../../.ai/skill-build.md) — Section 1: `self.configuration` auto-injected attribute
- [`.ai/skill-build.md:161`](../../../.ai/skill-build.md) — Section 4: `config_fields` optional field schema and error cases
- [`.ai/skill-build.md:198`](../../../.ai/skill-build.md) — Section 5: `configuration:` in config.yaml binding example
- [`.ai/skill-build.md:217`](../../../.ai/skill-build.md) — Section 6: full custom configuration walkthrough (Steps 1–4)
- [`.ai/skill-build.md:386`](../../../.ai/skill-build.md) — Section 8: new anti-pattern for `config.get("configuration")`
- [`.ai/skill-build.md:410`](../../../.ai/skill-build.md) — Section 9: new maintenance table rows for `ConfigFieldSpec` and `_collect_config_values`
