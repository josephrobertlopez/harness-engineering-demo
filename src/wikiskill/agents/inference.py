"""The Inference Agent: runs tasks with the current skills and nothing else.

**This class has no wiki handle, and that is the design.** The paper's central
ablation is that the wiki must be visible to the Skill Proposer but *not* to
the agent doing the rollouts -- letting inference read the wiki drops average
benchmark performance from 63.7% to 60.9%, because the agent leans on raw
notes instead of the distilled skill.

Enforcing that with a prompt instruction would be a convention one refactor
away from being violated. Enforcing it in the constructor signature means the
wiki is not reachable from here at all.
"""

from __future__ import annotations

from typing import Any, Protocol

from ..backends.base import Backend, LLMRequest
from ..bench import starter
from ..layers.raw import RawStore, trace_id
from ..protocol import ProtocolError, parse_action, parse_answer, parse_thought
from ..types import SkillSet, Task, Trace, TraceStep

SYSTEM = """\
You are an agent working against a simulated records service.

Available tools:
{tools}

Reply with exactly one of these two forms and nothing else:

THOUGHT: <one line of reasoning>
ACTION: <tool_name> {{"arg": "value"}}

THOUGHT: <one line of reasoning>
ANSWER: {{"key": "value"}}

Call tools until you can answer. The ANSWER payload must be a JSON object with
exactly the keys the task asks for.

## Learned skills

These are rules distilled from previous runs. Apply them.

{skills}
"""


class Environment(Protocol):
    def tool_spec(self) -> str: ...
    def call(self, name: str, args: dict[str, Any]) -> str: ...


class InferenceAgent:
    def __init__(self, backend: Backend, model: str, max_steps: int = 10) -> None:
        self.backend = backend
        self.model = model
        self.max_steps = max_steps

    def system_prompt(self, env: Environment, skillset: SkillSet) -> str:
        return SYSTEM.format(tools=env.tool_spec(), skills=skillset.render_for_prompt())

    def run(
        self,
        task: Task,
        env: Environment,
        skillset: SkillSet,
        *,
        iteration: int,
        raw: RawStore,
    ) -> Trace:
        system = self.system_prompt(env, skillset)
        sha = skillset.sha
        tid = trace_id(iteration, task.split, task.task_id, sha)

        raw.begin(iteration, task.split, task.task_id, sha)
        steps: list[TraceStep] = []
        transcript: list[str] = [f"TASK: {task.prompt}"]
        answer: dict[str, Any] | None = None
        truncated = False

        def push(step: TraceStep) -> None:
            steps.append(step)
            raw.record_step(iteration, task.split, task.task_id, sha, step)

        for turn in range(self.max_steps):
            req = LLMRequest(
                role="inference",
                model=self.model,
                system=system,
                prompt="\n".join(transcript) + "\n\nYour move:",
                max_tokens=2000,
                context={"family": task.family, "instance": task.env_spec.get("instance"), "turn": turn},
            )
            text = self.backend.complete(req).text
            transcript.append(text.strip())

            thought = parse_thought(text)
            if thought:
                push(TraceStep(index=len(steps), kind="reasoning", text=thought))

            try:
                answer = parse_answer(text)
                action = None if answer is not None else parse_action(text)
            except ProtocolError as exc:
                # A malformed turn is data, not an exception: the maintainer
                # should get to see that the agent lost the plot.
                push(TraceStep(index=len(steps), kind="error", text=str(exc)))
                transcript.append(f"SYSTEM: {exc}. Reply using the required format.")
                continue

            if answer is not None:
                push(TraceStep(index=len(steps), kind="answer", text=str(answer)))
                break

            if action is None:
                push(TraceStep(index=len(steps), kind="error", text="no ACTION and no ANSWER"))
                transcript.append("SYSTEM: reply with an ACTION or an ANSWER.")
                continue

            name, args = action
            push(TraceStep(index=len(steps), kind="tool_call", tool_name=name, tool_input=args))
            output = env.call(name, args)
            push(TraceStep(index=len(steps), kind="tool_result", tool_name=name, tool_output=output))
            transcript.append(f"OBSERVATION: {output}")
        else:
            truncated = True

        score, failure = starter.score(task, answer)
        if truncated and failure is None:
            failure = f"ran out of steps after {self.max_steps} turns"

        trace = Trace(
            trace_id=tid,
            task_id=task.task_id,
            split=task.split,
            family=task.family,
            iteration=iteration,
            skillset_sha=sha,
            steps=tuple(steps),
            final_answer=None if answer is None else str(answer),
            score=score,
            passed=score >= 1.0,
            failure_summary=failure,
            truncated=truncated,
        )
        raw.commit(trace)
        return trace
