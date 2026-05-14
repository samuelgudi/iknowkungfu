---
name: adversarial-test-design
description: Use this skill when writing tests and you want them to actually catch regressions rather than just turn green. Covers designing tests that try to break the code, choosing real inputs over trivial ones, when to avoid mocks, and how to recognize a false-green test.
---

# adversarial-test-design

A test's job is to **fail when the code is wrong**. A test that passes whether or not the code is correct has done nothing — it is theatre that produces a green checkmark. This skill is about writing tests that genuinely try to break the code, so that a passing suite actually means something.

The mindset shift: do not write a test to confirm the code works. Write a test to *catch the code being broken*. Those produce different tests.

## Use this skill when

- You are writing tests for new code or a bug fix.
- An existing suite is green but bugs still ship — a sign the tests are not biting.
- You are reviewing tests and want to judge whether they would actually catch a regression.

## Real-red before green

Before a test is worth anything, you must have seen it **fail for the right reason**.

1. Write the test.
2. Run it against code that is wrong — either the not-yet-written implementation, or the pre-fix buggy code for a bug-fix test. Watch it fail. Confirm it failed *because of the behaviour you are testing*, not because of a typo or a missing import.
3. Now make it pass.

A test that has only ever been seen green is unverified. You do not know if it can fail at all. The single most common defect in a test suite is tests that cannot fail.

## Adversarial inputs

The happy path is the input the author already had in mind — and the author already made that case work. Bugs live in the inputs the author *did not* think of. Deliberately reach for those:

- **Empty and absent** — empty string, empty list, empty file, zero, null, missing optional field.
- **Boundaries** — first, last, one past the end, exactly the limit, exactly one over.
- **Malformed** — wrong type, wrong shape, truncated, trailing garbage, wrong encoding.
- **Large** — input big enough to expose an O(n²), a buffer assumption, a recursion limit.
- **Hostile text** — unicode, emoji, right-to-left, embedded quotes and separators, the characters that break naive parsing and naive escaping.
- **Concurrent / repeated** — the same operation twice, two operations interleaved, retry after partial failure.
- **The input that violates an unstated assumption** — for every "this will always be X" the code assumes, write the test where it is not X.

You do not need all of these for every function. You need to *ask* all of them and write the ones that could plausibly break this code.

## Mocks: every mock is an assumption

A mock replaces a real dependency with a stand-in that behaves how *you think* the real one behaves. That is an assumption, and assumptions drift from reality silently. When they drift, the test still passes — against the mock — while production breaks.

- **Prefer the real dependency.** A real in-memory database, a real temp filesystem, a real local instance — these catch the integration bugs that mocks define out of existence.
- **Mock only what you genuinely cannot use real**: the network, the clock, randomness, a paid third-party API, a destructive side effect. These are true externals.
- **When you must mock, assert the contract.** Verify the code *called the dependency correctly* — right method, right arguments, right order. A mock that just returns a canned value and is never asserted against tests nothing.
- **Be suspicious of a test that mocks the thing under test's own collaborators heavily.** If most of the test is mock setup, the test is mostly describing your assumptions, not the system's behaviour.

## Recognizing a false-green test

A test is false-green if it passes when it should not. Checks:

- **The mutation check.** Break the code on purpose — flip a comparison, return a constant, delete a line. Does a test go red? If not, that code path is untested regardless of what the coverage number says.
- **It asserts on the mock.** The assertion checks a value the test itself injected through a mock. It is testing the test.
- **It asserts implementation, not behaviour.** It checks that a specific private method was called, or matches an exact internal structure. It will break on a harmless refactor and pass on a real behavioural regression — exactly backwards.
- **Happy-path only.** Every input is valid and well-formed. The bugs are not there.
- **Snapshot-everything.** A giant snapshot assertion that gets blindly re-blessed whenever it changes asserts nothing — it just records whatever the code currently does, bug included.

The one question to ask of any test: **"if the behaviour I care about broke, would this test catch it?"** If the honest answer is "not necessarily", the test needs rework.

## Anti-patterns

- **Writing the test to match the code.** Tests derived from reading the implementation inherit its blind spots. Derive them from the *specification* — what the code is supposed to do.
- **Testing the mock.** If the assertions only touch mock-injected values, the real code was never exercised.
- **Asserting implementation details.** Brittle against refactors, blind to behavioural regressions.
- **Happy-path-only suites.** Green, and meaningless. The adversarial inputs are the point.
- **Tests that have never failed.** Unverified. See one fail for the right reason before trusting it.
- **Chasing a coverage number.** 100% coverage with non-biting tests is 0% protection. Coverage measures what executed, not what was checked.

## What this skill does not do

- It does not prescribe a test framework, a runner, or a directory layout — it is about test *content*, whatever the tooling.
- It does not cover the test-driven-development *process* (the red-green-refactor loop as a workflow) — it covers what makes an individual test adversarial, which applies whether or not you practise TDD.
- It does not set a coverage target — it argues that the target is the wrong instrument. The instrument is "would this catch the bug".
