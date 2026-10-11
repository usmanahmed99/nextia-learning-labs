From: Grace (support lead)
To: Amira
Subject: login appears three times in the report

Hi Amira,

I ran the report on this week's export from the new web form:

    python -m ticket_cleaner data/web-form-export.csv

The report has three login lines and two billing lines:

    "by_category": {
      "Billing": 1,
      "LOGIN": 1,
      "Login": 1,
      "account": 1,
      "billing": 2,
      "login": 2,
      "shipping": 2
    }

They are the same teams. Before the web form, the report had one line per
team. I expected login 4, billing 3, shipping 2 and account 1. The export is
attached (data/web-form-export.csv).

Grace
