"""The defence designs we compare. Up to the end of the first module the assistant has only two designs:

- `start`   : the weak start. A weak prompt, broad tools, no checks in code, a log that keeps the
              message body. Writes run at once, with no approval.
- `prompt`  : prompt-only. A strong system prompt and clear delimiters around untrusted content.

The course adds the other designs -- a model-based input filter, and the system controls in code --
as you learn them. Every control the code can enforce is turned on by a flag here; at the start
every flag is off, so the assistant is weak on purpose.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Controls:
    strong_prompt: bool = False
    delimiters: bool = False
    input_filter: bool = False
    enforce_tenant: bool = False
    sandbox_files: bool = False
    allowlist_urls: bool = False
    output_checks: bool = False
    require_approval: bool = False
    least_privilege: bool = False
    redact_logs: bool = True


DESIGNS: dict[str, Controls] = {
    "start": Controls(redact_logs=False),
    "prompt": Controls(strong_prompt=True, delimiters=True),
}


def controls_for(design: str) -> Controls:
    if design not in DESIGNS:
        raise ValueError(f"Unknown design {design!r}: use one of {', '.join(DESIGNS)}.")
    return DESIGNS[design]
