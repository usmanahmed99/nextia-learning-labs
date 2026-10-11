"""The official authorization flow with the SDK's own OAuth client, against the practice provider."""

from scripts import oauth_login


def test_the_sdk_client_signs_in_and_asks_only_for_the_advertised_scopes(capsys):
    assert oauth_login.main(["--user", "usr-sam"]) == 0
    out = capsys.readouterr().out
    assert "POST /mcp -> 401" in out
    assert "GET /.well-known/oauth-protected-resource/mcp -> 200" in out
    assert "POST /register -> 201" in out
    assert "scope 'knowledge:read tickets:read'" in out and "PKCE S256" in out
    assert "POST /token -> 200" in out
    assert "get_ticket T-30002 -> ok" in out
