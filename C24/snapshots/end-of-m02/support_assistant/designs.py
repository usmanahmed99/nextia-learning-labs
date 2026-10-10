"""The defence designs we compare. At this point in the course the assistant has now these:

- `start`   : the weak start. A weak prompt, broad tools, no checks in code, a log that keeps the
              message body. Writes run at once, with no approval.
- `prompt`  : prompt-only. A strong system prompt and clear delimiters.
- `filter`  : prompt + a model-based input filter.
- `controls`: the first code controls -- least privilege by role, approval before a write, and an
              output check for a leaked secret or an outside link -- with a weak prompt.
- `secure`  : those controls and the strong prompt together.

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
    "filter": Controls(strong_prompt=True, delimiters=True, input_filter=True),
    "controls": Controls(require_approval=True, least_privilege=True, output_checks=True),
    "secure": Controls(strong_prompt=True, delimiters=True, require_approval=True, least_privilege=True,
                       output_checks=True),
}


def controls_for(design: str) -> Controls:
    if design not in DESIGNS:
        raise ValueError(f"Unknown design {design!r}: use one of {', '.join(DESIGNS)}.")
    return DESIGNS[design]
