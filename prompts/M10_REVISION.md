# M10 Revision Instruction

Follow [M10_REVISION_GOVERNANCE.md](M10_REVISION_GOVERNANCE.md). This file is subordinate to that governance contract.

Use an immutable `m10_revision_request` as the sole repair authority.

1. Repair only the cited defect and preserve the request's allowed scope.
2. Do not edit the predecessor artifact or any prior audit/review evidence.
3. Create a new successor with exact predecessor and finding bindings.
4. Do not claim approval, human review, release approval, provider authentication, live runtime behavior, learner outcomes, or an Internet-wide originality search.
5. Keep generated successor content `UNREVIEWED`.
6. Address every verbatim finding and every stated acceptance check. If a repair cannot meet a constraint, retain an escalated unresolved issue instead of weakening the requirement.
7. Never reuse a prior M9 review for changed bytes. A successor requires a fresh M9 review after M10 verification.

For a response that supplies authored content, return only the requested narrow generated payload. Do not emit trusted IDs, hashes, approval flags, lifecycle transitions, provenance assertions, or reviewer decisions; host orchestration supplies and validates those fields.
