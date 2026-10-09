from assistant.history import Conversation, ConversationStore, estimate_tokens


def test_the_oldest_turns_are_cut_first_and_the_newest_is_kept():
    conv = Conversation("system", budget_tokens=60)
    for i in range(6):
        conv.add("user", f"question {i} " + "x" * 80)   # about 22 tokens each
    sent = conv.messages()
    assert sent[0]["role"] == "system" and sent[-1]["content"].startswith("question 5")
    assert sum(estimate_tokens(m["content"]) for m in sent) <= 60 and conv.dropped() == 4


def test_each_agent_has_their_own_conversation():
    store = ConversationStore("system")
    store.get("camille", "T-80005").add("user", "Make it shorter.")
    assert store.get("grace", "T-80005").turns == []
    assert store.get("camille", "T-80005") is store.get("camille", "T-80005")


def test_a_recorded_follow_up_conversation_replays(mock):
    from assistant.context import MAX_TOKENS, build_request
    from assistant.data import load_tickets

    first = build_request(load_tickets()["T-80005"], "chat-small", "v2")
    conv = Conversation(first["messages"][0]["content"], budget_tokens=3000)
    conv.add("user", first["messages"][1]["content"])
    conv.add("assistant", mock.complete(first).text)
    conv.add("user", "Make the reply shorter: two sentences.")
    answer = mock.complete({"model": "chat-small", "messages": conv.messages(), "max_completion_tokens": MAX_TOKENS})
    assert answer.finish_reason == "stop" and "commande" in answer.text
