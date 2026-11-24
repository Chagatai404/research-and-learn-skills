# Research and learning plugin

Implementation plan following the design interview. Deliver one portable skill collection with native Codex and Claude Code packaging, a local learner profile and a migrated human-readable study collection. The proposed database and initial scoring scale are engineering choices to validate in the pilot.

## Existing material

The source checkout at d895e13 contains learn, prepare, research, audit, defend, notes-to-latex, manimgx and computer. It also contains seven specialist roles and discipline-specific research and audit lenses. Inventory these together with their referenced protocols, examples and behavioral tests. Trace each dependency on the app to its instructional purpose before porting. Historical tutor worktrees and vault templates may contain earlier contracts absent from main.

The CENG487 Lecture 4 note already links its course, neighboring lectures and source pages, flags an ambiguous diagram, defines notation and develops derivations. Preserve those strengths. The lecture template layers gist, recall, full lecture and derivation. The installed Obsidian skill still prescribes dated tutor sessions. Replace that behavior for this plugin and reconcile the conflicting installed guidance during rollout.

## Two entry points

1. **Learn.** Resolve the course week or independent goal. Read its note, relevant prerequisite ancestry and recent evidence. Resume an unanswered exercise or probe the most informative gap. Ask one question, wait for the learner and adapt the next step to the answer. Bracket difficulty using independent successes and misses. Teach one connected idea at a time, invite questions and let the learner request a different depth or medium. Close with unaided recall and a fresh transfer task. Revisit later with a different problem. Opening another chat resumes from the same note and evidence.
2. **Research.** Frame a question and competing explanations. Scout and verify primary sources, teach missing background, and agree on a revision-specific plan with criteria for failure. Run the smallest informative experiment before scaling. Bind each result to inputs, code revision, parameters and outputs. Audit each consequential claim against its evidence and alternatives. Preserve uncertainty when independent review is unavailable. The researcher decides claims and approves revised plans.
3. **Learn back.** From the actual agent diff, experiment or derivation, trace one result from inputs through method to output. Have the researcher explain a consequential choice, reconstruct a step and predict what changes under a perturbed assumption. Record demonstrated capabilities and remaining gaps separately from claim verdict and authorship. Resume a gap through Learn. A research decision can stand even when the researcher still wants practice.

## Contract selection

Build a catalog from the actual historical protocols, with each contract's learning objective, signs to use it, teaching moves, check and recovery path. For example, use a worked example with fading hints for procedural errors, term comparison and counterexamples for confused definitions, a derivation with stated assumptions for a formal claim, and code/data walkthrough for a result the agent produced. For an analogy, make the mapping and its limits explicit. Grade an unaided attempt before exposing its solution. Keep assisted practice available. Select text, a local figure, animation or executable example according to what the concept needs and the host can produce. Preserve faithful handwriting transcription as a separate operation.

## State and routing proposal

Keep a single learner profile across projects. Use a small local SQLite file outside the vault, a versioned schema and a Python standard-library helper callable from each host. Provide operations to resolve aliases, inspect a goal's prerequisites, record an attempt, resume a pending prompt, correct a grade and export or restore state. Keep pending work and evidence in ordinary records. Reserve graph nodes for reusable assessable capabilities. A goal points to the capabilities it requires. Store directed prerequisite relationships with reasons. Reject cycles and merge aliases without losing attempts. Create a capability only when it changes teaching, assessment or routing for a real goal. Check for existing capabilities before adding one.

Derive a readable confidence band and score from evidence. Prototype an ordinal 0–4 scale for assessed work (miss, assisted, independent routine, independent transfer, delayed reconstruction). Display unknown separately, with last independent evidence and review status. A stale demonstration prompts retrieval. Never infer a promotion from reading notes, chat length, self-report or agent work. Validate the aggregation rule on mixed histories before adopting it. Route toward the target using indispensable prerequisites and the nearest uncertain step. Echelon forms can support solving linear systems. For a quantum goal involving measurement in another basis, check basis changes and inner products first. Keep distinct branches of linear algebra distinct.

Use stable attempt identifiers, atomic transactions and optimistic revisions. Replaying a chat action cannot double-count evidence. A conflicting grade or simultaneous note edit must preserve both inputs for reconciliation. Render human feedback only after recording the corresponding attempt; make interrupted updates recoverable by ID.

## Vault proposal

Use one course index plus one note per documented syllabus week, one evolving independent-study note per coherent topic and one research overview with a note per sustained investigation when needed. Reuse existing source, attachment and durable concept notes. Link to a section when a topic already has a home. Preserve learner-authored answers verbatim. Each week opens with navigation, goals and a recall prompt, then has sections for its topics, detailed teaching, worked examples and source pointers. Put the current probe and a learner-editable answer directly under the relevant topic. Give concise feedback after submission and retain useful corrected reasoning. Keep answer keys out of open assessment prompts. Resuming reads only the active section and relevant evidence. Permit answers either in the note or in chat, binding feedback to the submitted version.

For research, keep the question, linked evidence, competing explanations, decisions and teach-back practice readable together. Code and raw results live in the project. Separate source-supported claims, agent interpretations and the learner's own reasoning in prose.

## Delivery and verification

1. Map all eight former skills, seven roles, references and historical contracts. Port the seven learning and research skills. Extract scoped-path checks, change previews, backups and read-back verification from the computer workflow for migration and note maintenance. Omit the standalone computer executor. Verify current Codex and Claude packaging and identify an existing tool-capable host for the Ollama pilot.
2. Build one shared skill tree with thin host manifests and an offline install path. Keep specialized roles usable as instructions on single-agent hosts. Identify any review requiring a genuinely separate reviewer. Remove dependencies on ROS tools, the portal, background services and model API calls.
3. Implement state and routing. Verify unknown, assisted success, independent transfer, delayed lapse, alias merge, cycles, grade correction, simultaneous writers, backup and interrupted resume.
4. Build the learning vertical slice with one genuine syllabus week and one independent topic. Verify appropriate contract selection, detailed explanations, hints, withheld keys, note editing and a cross-host resume. Ten chats on the same material must yield one week note and zero session nodes.
5. Build research and learn-back around one reproducible result. Check that changed plans invalidate approvals, claims point to exact artifacts, unsupported conclusions remain unresolved and a successful agent run grants the learner no mastery.
6. Inventory both legacy vault layouts by path and content. Produce an old-to-new map, including heading links, embeds, attachments, source locators, learner answers, conflicting versions and missing syllabus dates. Stage copies outside the live vault, preview one complete course week, verify backlinks, then migrate in reversible batches. Preserve uncertain mappings for review. Keep a manifest with original hashes, backups and tested restore steps. Preserve old assessment provenance; import ambiguous history as unassessed.
7. Exercise identical requests on Codex, Claude Code and the named local host. Test first use, offline use, interrupted grading, late review, research explanation and restoration. Cut over installed skills and relevant agent guidance only after these checks. Any retirement or deletion of the old project is a separate action.

## Decision record

| Choice | Status | Reason |
|---|---|---|
| Separate learning and research entry points, shared learner context, direct tutoring, week/topic notes | Confirmed | Explicit request |
| One shared skill source, local transactional profile outside Obsidian | Proposed | Reliable cross-host resume and clean notes |
| Model compatibility | Confirmed | Support locally hosted Ollama models now and future open-weight models through the same skill content. Test the host's ability to read skills, update notes, run the helper and access research tools separately from model quality. |
| Source discovery when online | Confirmed | Use host browsing for public papers and official sources. Literature search, source verification and adversarial review are required research capabilities. |
| Visible practice history | Confirmed | Keep the active probe, diagnostically useful original reasoning and corrected explanation in the topic or week. Store repetitive attempts in the learner profile. |
| Long-term coverage and navigation | Confirmed | Course index maps every syllabus week and objective to an exact note section, marking uncovered objectives explicitly. Research index maps questions to methods, sources, findings, limitations and decisions. Preserve links across weeks and related investigations. |
| Local interaction | Confirmed | Ollama through a tool-capable host is sufficient. Plain Ollama chat is outside the compatibility target. |
| Migration scope | Confirmed | Account for every existing course and research note. Import mastery only from attributable graded learner work. |
| File operations | Confirmed | Retain safeguards in note maintenance and migration. Ship seven domain skills. |
| First migration pilot | Engineering choice: CENG487 | Existing lectures, links, caveats and overlapping layouts make it a meaningful test. Roll out to the remaining courses and projects after validation. |
| Exact historical contract inventory and score aggregation | Implementation verification | Check against legacy materials and mixed evidence histories during the pilot. |

## Migration reconciliation

Inventory every course and research collection in the vault, including relevant topic, source, review and archived material outside the two project trees. Identify linked evidence in legacy records. For each original note, record its digest, destination note and section, migration outcome, and any ambiguity. Many originals may map to one week. Preserve ambiguous material in a navigable location pending reconciliation. Verify heading and block links, embeds, mathematical content, original answers and source locators in the staged collection. Count every input exactly once in the manifest and report unresolved items.

For each imported assessment, retain a pointer to the original graded attempt, the learner response, grade, assessed capability and any recorded assistance. Preserve unknown assistance as unknown. An old score without traceable graded work supplies no mastery. Re-importing the same source must yield identical evidence counts. Verify these conditions on the pilot and again after the full import.

Before applying a batch, verify canonical paths against the intended roots and compare current contents with their previewed digests. Preserve concurrent edits for reconciliation. Back up every affected original, verify the written contents and link targets, and exercise restoration on a staged copy. The completion report gives note coverage, graded evidence imported, unresolved mappings and backup locations.

## Acceptance checks from the interview

- From a course index, locate a syllabus objective, its detailed explanation and an example in two navigation steps. Check coverage against the actual syllabus. Mark unstudied material separately from missing notes and from demonstrated understanding.
- From a research index, follow a claim to its source passage or reproducible result, strongest alternative explanation, discriminating test and current decision. Capture unsuccessful searches or unresolved verification in the investigation when they affect the conclusion.
- Reopen a week after repeated practice. Its topic sections still read as a coherent lecture. Routine attempts are retrievable separately and a learner's substantive original answer survives correction.
- Run the same lesson and a source-verification task through a tool-capable local host. A missing browser or independent reviewer leaves the corresponding research step pending and resumable on another host. Changing model family must not require duplicating teaching contracts.
