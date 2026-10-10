"""The defence designs we compare, each a set of switches.

A design says how much the assistant is defended. The course compares four, plus the deliberately
weak `start` that the first module downloads:

- `start`   : the weak start. A weak prompt, broad tools, no checks in code, a log that keeps the
              message body. Writes run at once, with no approval.
- `prompt`  : prompt-only. A strong system prompt and clear delimiters around untrusted content.
              Nothing is enforced in code.
- `filter`  : prompt + a model-based input filter that tries to catch an injection before it runs.
- `controls`: the system controls in code, with a weak prompt (to show the controls alone): least
              privilege by role, a server-side tenant check, a file sandbox, a URL allow-list,
              output checks for the secret and outside links, and approval before every write.
- `secure`  : the controls and the strong prompt together (the course's end state).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Controls:
    strong_prompt: bool = False
    delimiters: bool = False
    input_filter: bool = False
    enforce_tenant: bool = False       # reads and writes stay inside the session's tenant and customer
    sandbox_files: bool = False        # read_file stays inside the ticket's folder
    allowlist_urls: bool = False       # fetch_url only an allowed host; no SSRF, no bad redirect
    output_checks: bool = False        # refuse an answer that leaks the secret or an outside link
    require_approval: bool = False     # a write waits for a person; role and refund limits apply
    least_privilege: bool = False      # a read-only member gets no write tools
    redact_logs: bool = True           # the audit log keeps no secret and no message body


DESIGNS: dict[str, Controls] = {
    "start": Controls(redact_logs=False),
    "prompt": Controls(strong_prompt=True, delimiters=True),
    "filter": Controls(strong_prompt=True, delimiters=True, input_filter=True),
    "controls": Controls(enforce_tenant=True, sandbox_files=True, allowlist_urls=True, output_checks=True,
                         require_approval=True, least_privilege=True),
    "secure": Controls(strong_prompt=True, delimiters=True, enforce_tenant=True, sandbox_files=True,
                       allowlist_urls=True, output_checks=True, require_approval=True, least_privilege=True),
}


def controls_for(design: str) -> Controls:
    if design not in DESIGNS:
        raise ValueError(f"Unknown design {design!r}: use one of {', '.join(DESIGNS)}.")
    return DESIGNS[design]
