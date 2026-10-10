# Ten-minute walkthrough (for Omar, Grace and Ines)

1. **The problem in one sentence (1 min).** Several shops want the assistant; each must see only its own documents; Omar needs a price per shop.
2. **What people will do (1 min).** The journeys J1 to J5 and what is out of scope.
3. **The design on one page (2 min).** The container diagram: one application, one database, one model provider. Why not more services yet (ADR-0001).
4. **What it costs (2 min).** Base scenario: about US$52 a month for two shops, about US$26 per shop; low to high: US$41 to US$76. Most of it is fixed (the API replica and the database), so the cost per shop falls as shops join: about US$14 per shop with four shops in month 12. If usage doubles, the total rises about 13%, not 100%.
5. **What we tested (1 min).** The strong model costs 19 times more per question and was not better on our 67 questions (ADR-0003).
6. **Assumptions (1 min).** The numbers we did not verify: customers per day, questions per customer, growth, the cache hit share. The high scenario hits the provider quota in the busiest minute from the first month: the first thing to measure.
7. **Risks and failures (1 min).** The database is a single point of failure; the restore plan (ADR-0005). The provider quota (F1).
8. **The roadmap and what we ask for (1 min).** Release 1 with two shops, the validation work, the signals for each later step. One unresolved assumption to decide today: will customers see the assistant on the home page?

Speak plainly: say "measured", "price" or "assumption" for every number you show.
