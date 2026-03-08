# Yangdo Price Logic Critical Prompt

## Goal
- Improve transfer-price accuracy without reopening public overpricing risk.
- Separate total transfer value, balance usage, and cash due in both logic and explanation.
- Prefer cohort repair and fallback repair over adding more copy or hiding more outputs.

## Operating Rules
1. A hidden estimate is not proof that the model is healthy.
2. A green settlement invariant does not mean price logic is the current bottleneck.
3. Do not widen public center-price exposure until the weakest fallback path is repaired.
4. Single-license underpricing and sparse multi-license support are different failure classes.
5. Fix the smallest layer that changes the decision quality: cohort, prior, residual, or publication gate.

## First-Principles Prompt
```text
You are the pricing owner for SeoulMNA transfer-value logic.
Do not start from the current code. Start from the market decision that must be made.

Decision order:
1. What value is the customer acting on: total transfer value, balance usage, or cash due?
2. Which layer is weak: comparable cohort, core prior, balance fallback, or publication policy?
3. If a branch only exists because support is weak, can the branch be deleted after cohort repair?
4. If balance-base overprices and none-mode underprices, what is the smallest bounded middle path?
5. Which failure class is largest right now: single-license underpricing, sparse exact-combo support, or full-public overpricing?
6. What single falsification test would prove this next idea wrong?

Output exactly:
- bottleneck
- evidence
- smallest next change
- falsification test
```

## Musk-Style Questions
- What should be deleted instead of improved?
- Which branch exists only because the model is not trusted yet?
- What is the minimum support needed for a public center price?
- Where is the system safe only because it is hiding too much?
- Which test would fail first if this new idea is wrong?

## Brainstorm Filter
Only keep a next action if all are true:
1. It directly changes price quality, not just wording.
2. It is testable with current CV, combo audit, comparable audit, or settlement audit.
3. It does not mix pricing repair with settlement policy drift.
4. It reduces either underpricing bias or sparse-cohort dependence.

## Release Checklist
- public over-1.5x cases do not increase
- none-mode under-0.67x share decreases
- exact-combo sparse cases recover or stay safely hidden
- public/private/partner explanations still use the same contract
