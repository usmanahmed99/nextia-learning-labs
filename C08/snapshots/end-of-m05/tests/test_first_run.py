from assistant.__main__ import main


def test_the_first_run_gives_the_known_good_answer(capsys):
    assert main(["analyse", "T-80008"]) == 0
    out = capsys.readouterr().out
    assert '"team": "delivery"' in out and out.strip().splitlines()[-1].startswith("valid | chat-small")


def test_an_unknown_ticket_is_reported(capsys):
    assert main(["analyse", "T-99999"]) == 2
    assert "No ticket T-99999" in capsys.readouterr().err
