"""The defence designs we compare, each a set of switches.

A design says how much the assistant is defended:

- `start`   : the weak start. A weak prompt, broad tools, no checks in code. Writes run at once.
- `prompt`  : prompt-only. A strong system prompt and clear delimiters around untrusted content.
              Nothing is enforced in code.
- `filter`  : prompt + a model-based input filter that tries to catch an injection before it runs.
- `controls`: the first controls in code, with a weak prompt (to show the controls alone): approval
              before every write with role limits, a server-side tenant and customer scope, e-mail
              only to the address on file, and an output check.
- `secure`  : the controls and the strong prompt together.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Controls:
    strong_prompt: bool = False        # the system prompt says what is data and what is an instruction
    delimiters: bool = False           # the ticket text goes inside [ticket] markers
    input_filter: bool = False         # a model call screens the input first
    require_approval: bool = False     # a write waits for a person; role and refund limits apply
    enforce_tenant: bool = False       # reads and writes stay inside the session's tenant and customer
    output_checks: bool = False        # refuse an answer that leaks the secret or an outside link


CODE = dict(require_approval=True, enforce_tenant=True, output_checks=True)

DESIGNS: dict[str, Controls] = {
    "start": Controls(),
    "prompt": Controls(strong_prompt=True, delimiters=True),
    "filter": Controls(strong_prompt=True, delimiters=True, input_filter=True),
    "controls": Controls(**CODE),
    "secure": Controls(strong_prompt=True, delimiters=True, **CODE),
}


def controls_for(design: str) -> Controls:
    if design not in DESIGNS:
        raise ValueError(f"Unknown design {design!r}: use one of {', '.join(DESIGNS)}.")
    return DESIGNS[design]
