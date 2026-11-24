---
name: learn
description: Teach, probe, quiz or review a university course, independent subject, paper or research prerequisite. Resume from a week or topic note and adapt to demonstrated understanding.
---

# Learn

Read [teaching contracts](../../references/teaching-contracts.md) and [study notes](../../references/study-notes.md). Use the local learner profile through `python scripts/profile.py --help` from the installed plugin root. Read subcommand help before use. Resolve the same existing learner profile on every host. A tool-capable Ollama host uses these same files and helper.

1. Identify the target capability, active note section and relevant prerequisite ancestry. Consult existing scoped evidence and the next due review. Prefer one upstream gap that actually changes the route to this goal. A stale success merits a retrieval check. Add a capability only if tracking it separately changes teaching, assessment or routing. Reuse existing aliases and record why each prerequisite is necessary.
2. Resume a pending prompt first. Otherwise choose one question that separates a missing prerequisite from a new idea. Start near the learner's demonstrated level, adjust difficulty as evidence arrives, normally limit diagnostic questioning to 3–5 turns and move into teaching sooner when the gap is clear. Save the pending prompt and criteria in private state, put the active question in the note and wait. A draft remains a draft until the learner submits it.
3. Bind assessment to the exact prompt, submitted response and revision. Accept valid equivalent methods. Capture the response, assistance, grade, reason and evidence locator under a stable attempt ID through the helper. On retry inspect existing state first. Use the helper's actual supported fields; keep detailed rationale with the response or in the note when appropriate. A request for help, recognition alone, reading or watching a solution cannot establish independent performance. If the learner says “I don't know”, record the gap and teach.
4. Give specific feedback on the first consequential error. Select the matching contract: motivate the idea, build from known foundations, explain or derive it, show a worked case and invite a question. Respect requested order and depth. For substantial new lessons use [prepare](../prepare/SKILL.md). Use a fresh problem after help and credit the actual scope tested.
5. Close with free recall then one transfer item, one per turn. Arrange delayed retrieval using the profile's review information. Preserve the active or next question and useful correction in the same note. When returning after a lapse, check then repair the weak dimension. Report what the learner demonstrated and what remains open in ordinary language.

## Profile operations

Start with `python scripts/profile.py find TERM` to discover existing capability names, goals and open scopes before adding anything. Omit TERM to list the profile when the learner says “continue” without naming a topic. Reuse the returned scope for resume and use the goal name exactly as returned for routing.

Use one stable scope per week or topic, such as `ceng487/week-4`. From the plugin root, `python scripts/profile.py resume SCOPE` retrieves an open prompt; `route GOAL` lists its prerequisite route and `history CAPABILITY` gives earlier attempts. Use `capability ID TITLE`, `alias ID ALIAS`, `require TARGET PREREQUISITE REASON` and `goal GOAL CAPABILITY` only for real relationships. Register a fresh prompt with `ask SCOPE ATTEMPT_ID CAPABILITY QUESTION`. Set criteria privately before the question, and preserve the original prompt and difficulty across hosts. Grade with `grade ATTEMPT_ID RESPONSE VERDICT ASSISTANCE MODE RATIONALE`, passing text fields as individual arguments. Record recognition, routine application, independent transfer or delayed retrieval accurately. Re-read help for allowed values. A new exercise gets a new ID. Use revision-checked correction only for an error in the recorded assessment.

For example, after resolving a genuine capability and goal, a tutor can open a prompt as follows. Use a fresh ID per actual exercise. Keep the rubric private when displaying the pending question.

```console
python scripts/profile.py capability factor-pure-state "Recognize a factorizable pure state"
python scripts/profile.py ask ceng487/composite-states factor-001 factor-pure-state "The second row of a normalized two-qubit coefficient matrix is twice its first. What does that tell you about the state?" --rubric "Identifies a product state and justifies rank one or an equivalent factorization."
python scripts/profile.py resume ceng487/composite-states
```

If the learner requests help, save `python scripts/profile.py hint factor-001 hinted` before showing the hint, or use `revealed` before giving the solution. On another host use the saved assistance and rubric when grading. Preserve the exact submitted response even if it contains an error.
