"""The defence designs we compare, each a set of switches.

A design says how much the assistant is defended. The course compares four, plus the deliberately
weak `start` that the first module downloads:

- `start`   : the weak start. A weak prompt, broad tools, no checks in code, a log that keeps the
              message body, and full storage of every conversation. Writes run at once.
- `prompt`  : prompt-only. A strong system prompt and clear delimiters around untrusted content.
              Nothing is enforced in code.
- `filter`  : prompt + a model-based input filter that tries to catch an injection before it runs.
- `controls`: the system controls in code, with a weak prompt (to show the controls alone): approval
              before every write with role limits, a server-side tenant and customer scope, output
              checks, a file sandbox, a URL allow-list and least privilege by role.
- `secure`  : the controls and the strong prompt together (the course's end state).

The strict tool contracts, the refund rules and the audit event for a blocked operation are not
switches: they are plain correct code, the same in every design.
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
    sandbox_files: bool = False        # read_file stays inside the ticket's folder
    allowlist_urls: bool = False       # fetch_url only an allowed host; no SSRF, no bad redirect
    least_privilege: bool = False      # a read-only member gets no write tools
    redact_logs: bool = True           # the audit log keeps no secret and no message body
    minimize_data: bool = True         # a stored run keeps the outcome only, with an end date


CODE = dict(require_approval=True, enforce_tenant=True, output_checks=True, sandbox_files=True, allowlist_urls=True,
            least_privilege=True)

DESIGNS: dict[str, Controls] = {
    "start": Controls(redact_logs=False, minimize_data=False),
    "prompt": Controls(strong_prompt=True, delimiters=True),
    "filter": Controls(strong_prompt=True, delimiters=True, input_filter=True),
    "controls": Controls(**CODE),
    "secure": Controls(strong_prompt=True, delimiters=True, **CODE),
}


def controls_for(design: str) -> Controls:
    if design not in DESIGNS:
        raise ValueError(f"Unknown design {design!r}: use one of {', '.join(DESIGNS)}.")
    return DESIGNS[design]
