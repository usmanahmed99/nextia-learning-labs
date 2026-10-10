"""A simulated AI provider for the scaling course: an OpenAI-compatible API on your computer.

It is NOT a model. It answers in the same shape as a real provider, with times, token
counts and quota answers (HTTP 429) taken from real recorded calls to a hosted model
(see calibration.json). Its answers are simple: keywords choose the team, a reply comes
from the recordings or a template, and a vector comes from the words of the text.
"""
