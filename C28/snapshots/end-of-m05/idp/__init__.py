"""A mock identity provider (authorization server) for practice on your own computer.

It signs RS256 access tokens with a key made on your computer (`python -m idp init`), publishes
the public key (JWKS) and its metadata (RFC 8414), registers clients (RFC 7591) and runs the
authorization code flow with PKCE (S256). Sign-in has no password: you pick a made-up person.
It is a simplified copy of the authentication course's provider. Never use it for real accounts.
Signing and keys use PyJWT and cryptography; there is no hand-written cryptography.
"""
