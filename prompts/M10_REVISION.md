# M10 Revision Instruction

## Active revision flow

When an artifact fails a relevant check:

1. Preserve the predecessor bytes unchanged.
2. Create a corrected revision at a new, previously unused path.
3. Retain a short note containing the predecessor hash, defect, and changed artifact path.
4. Run the schema/validator/tests relevant to the changed artifact.
5. Stop and report the result.

Do not require a full M9 import, closure inventory, supersession index, 120 reviews, a fresh whole-population review, or an approval tier. Keep generated revised content `UNREVIEWED` and do not claim human review, release approval, provider behavior, learner outcomes, or public-distribution authority.

## Historical governance

[M10_REVISION_GOVERNANCE.md](M10_REVISION_GOVERNANCE.md) describes retained immutable historical records. Use it only when explicitly verifying or extending that historical contract; do not apply it as the default revision workflow.
