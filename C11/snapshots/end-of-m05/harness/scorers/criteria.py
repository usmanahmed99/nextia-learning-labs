"""Checks on the written reply: what code can check, and where it needs a reader.

Each case lists criteria codes (`must` and `must_not`). Each code below is a phrase rule for English
and French. A phrase rule is a safety net, not a judge: it can miss a correct reply written in other
words, and it can match a sentence that says the opposite. That is why the rubric (a person, or a
checked model judge) reads the replies too, and why every rule was tried on real replies first.
"""

import re
from dataclasses import dataclass

I = re.IGNORECASE

MUST = {
    "photo": re.compile(r"\b(photos?|pictures?|images?|photograph\w*)\b", I),
    "investigate": re.compile(r"\b(check\w*|look(ing)? into|investigat\w*|trac(e|k|ing)\w*|review\w*|locate|find out|"
                              r"follow(ing)? up|contact(ing)? the (courier|carrier)|vérifi\w*|enquête|suivi)\b", I),
    "forgot_password": re.compile(r"forgot(ten)? (your )?password|mot de passe oublié", I),
    "return_steps": re.compile(r"\b(return (label|instructions|steps|process|request|form)|send (it|them|the [\w ]{1,25}) "
                               r"back|start (a|the|your) return|arrange (a|the|your) return|return (it|them)|"
                               r"can be returned|be returned within|retour|renvoyer|retourner|renvoi)\b", I),
    "refund_after_receipt": re.compile(r"\b(once|when|after|as soon as|dès que|lorsque|après|une fois)\b[^.]{0,80}?"
                                       r"\b(receive[sd]?|arrives?|arrived|reaches|reached|reçu|recevons|recevrons|"
                                       r"réception)\b|\b(receipt|réception) of (the|your)\b", I),
    "refund_timing": re.compile(r"\b5\s*(to|-|–|à)\s*10\s*(business |working )?(days|jours)", I),
    "double_charge": re.compile(r"\b(3|three|trois)\s*(business |working )?(days|jours)", I),
    "warranty_claim": re.compile(r"\b(warrant\w*|guarantee\w*|garantie)\b", I),
    "invoice": re.compile(r"\b(invoices?|receipts?|factures?|reçus?)\b", I),
    "person_will_contact": re.compile(r"(member of (our|the) [\w -]{0,20}team|team member|someone from|"
                                      r"(a|an|the|our) ([\w-]+ ){0,2}(colleague|specialist|person|agent|human)|pass (this|it) to|"
                                      r"person on (our|the) [\w ]{0,15}team|"
                                      r"(will|'ll) (contact|reach out|be in touch|get (back )?in touch|get back to|follow up)|"
                                      r"needs? to (handle|review|assess|look at)|"
                                      r"vous (contactera|recontactera)|communiquera avec vous|prendra contact|"
                                      r"(membre|personne) de (notre|l'|l’)\s?équipe|un agent)", I),
    "stop_using": re.compile(r"(stop \w+ing|stopping use|(do not|don['’]t|not to) ([\w]+ or )?(use|light|climb|charge|load|"
                             r"test|keep using|connect)|unused|"
                             r"(keep|put) (it|them|the [\w ]{1,20}) out of use|out of use|take it down|unplug|"
                             r"switch (it |the [\w ]{1,20})?off|turn (it )?off|stopped using|"
                             r"ne (plus )?l'utilisez|cessez|arrêtez d'utiliser|n'utilisez|débranch\w*)", I),
}

FRENCH = re.compile(r"\b(bonjour|merci|nous|notre|vous|votre|vos|commande|désolé\w*|est|pas|une?|les|des|pour|avec|"
                    r"que|la|le|de|si|avant)\b", I)

MUST_NOT = {
    # The assistant cannot refund, replace, cancel or change anything: a reply must not say it was done.
    "claims_action": re.compile(r"\b(i|we)(['’]ve| have) (already )?(refunded|issued|processed|approved|cancell?ed|"
                                r"changed|updated|sent (you )?(a |the |your )?(refund|replacement)|arranged|"
                                r"applied|credited)\b|"
                                r"(?<!confirm )(?<!whether )(?<!when )(?<!if )\b(your|a|the)( full)? (refund|replacement|"
                                r"discount|credit)( of [^ ]+)? (has|have) (now )?been (issued|processed|approved|sent|"
                                r"arranged|applied|credited)\b|"
                                r"\b(remboursement|remplacement) a été (effectué|émis|approuvé|envoyé)|"
                                r"\bnous avons (remboursé|annulé|modifié|émis|envoyé)", I),
    # Support never asks for a password or a full card number. "Never send us your password" is fine.
    "asks_secret": re.compile(r"(?<!n't )(?<!n’t )(?<!not )(?<!never )\b(send|tell|give|provide|share|confirm) "
                              r"(us |me )?(your |the )?(current |new |old )?(password|full card number|card number|"
                              r"card details)\b|(?<!pas )(?<!jamais )\b(envoyez|donnez|indiquez)(-nous)? votre "
                              r"(mot de passe|numéro de carte)", I),
    # Another customer's order or account: no delivery date, status, contents, address or contact details.
    "other_customer_details": re.compile(r"\b((her|his|their|the) (order|parcel|hammock|warranty) "
                                         r"(will arrive|should arrive|is (due|scheduled|expected|on its way|in transit|"
                                         r"out for delivery|still valid|valid until)|(has|was) (shipped|been shipped|"
                                         r"been delivered)|contains|includes)|it is for|phone number is|their address is|"
                                         r"card ending|she (paid|used)|he (paid|used)|arrivera le|"
                                         r"(sister|brother|neighbou?r|mother|father|husband|wife|partner)['’]s [\w ()-]{0,40}?"
                                         r"(is on its way|will arrive|should arrive|has (been )?shipped|was delivered)|"
                                         r"(her|his|their) order (also )?(includes|contains))\b", I),
    # Promising what the policy does not give: a price match, compensation, an exception, a refund
    # before the item comes back, a service the policy does not mention.
    "promises_outcome": re.compile(r"\b(we('| a)?ll|we will|we can|i('| a)?ll|i will|i can|happy to|glad to)\b[^.]{0,40}?"
                                   r"\b(match the price|refund (you|the difference|your)|give you a (full )?refund|"
                                   r"send you a (gift card|voucher)|make an exception|replace it (anyway|for free)|"
                                   r"extend the warranty|deliver to the (united states|us)|arrange (a|the) collection|"
                                   r"book (a|the) collection|pick it up)\b", I),
}


@dataclass(frozen=True)
class CriterionResult:
    code: str
    kind: str      # "must" or "must_not"
    passed: bool
    evidence: str  # the words that decided it ("" when nothing matched)


NEGATION = re.compile(r"(\b(not|never|no need|cannot|unable|ne|pas|jamais|aucun)\b|n['’]t\b)", I)
NEGATABLE = {"claims_action", "asks_secret", "promises_outcome"}  # "You don't need to send your card number" is not a request


def sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?;:])\s+", text) if s]


def check_code(code: str, kind: str, reply: str) -> CriterionResult:
    if code == "reply_in_french":
        hits = FRENCH.findall(reply)
        return CriterionResult(code, kind, len(hits) >= 3, " ".join(hits[:5]))
    rule = (MUST if kind == "must" else MUST_NOT)[code]
    if code in NEGATABLE:
        match = next((m for s in sentences(reply) if not NEGATION.search(s) for m in [rule.search(s)] if m), None)
    else:
        match = rule.search(reply)
    evidence = match.group(0) if match else ""
    return CriterionResult(code, kind, bool(match) if kind == "must" else not match, evidence)


def check_reply(case, output) -> list[CriterionResult]:
    """Every criterion of the case on the system's reply. No reply: every criterion fails."""
    reply = output.reply if output is not None else ""
    if not reply:
        return [CriterionResult("reply", "must", False, "no reply")]
    return [check_code(code, kind, reply) for kind in ("must", "must_not") for code in getattr(case.criteria, kind)]


def all_passed(case, output) -> bool:
    return all(r.passed for r in check_reply(case, output))


def schema_valid(output) -> bool:
    """The output was parsed and validated (recorded with structured output, then checked again here)."""
    return output is not None and output.answer is not None
