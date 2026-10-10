import json

from support_assistant.designs import controls_for
from support_assistant.identity import Session
from support_assistant.runner import fresh_world
from support_assistant.tools import run_tool

WEAK = controls_for("start")
SECURE = controls_for("secure")


def session(tenant="larkfield", role="staff", sub="usr-sam"):
    return Session(sub=sub, tenant=tenant, role=role)


def run(name, args, controls, sess, ticket, world):
    return run_tool(name, json.dumps(args), 1, controls, sess, ticket, world)
