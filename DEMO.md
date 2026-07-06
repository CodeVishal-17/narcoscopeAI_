# NarcoScope AI — Demo Script & Pitch (Gwalior Police Hackathon)

**One-liner:** *NarcoScope AI is a force-multiplier for narcotics investigators —
it continuously watches public Telegram, Instagram and WhatsApp activity, flags
drug-sale accounts (in Hindi and English), links them into operator networks, and
packages court-ready evidence for lawful action — with a human analyst in the loop
at every step.*

---

## The problem (what to open with)
- Drug trade has moved to encrypted/social platforms: Telegram channels, WhatsApp
  groups, Instagram handles — often coded, often in **Hindi/Hinglish**.
- A handful of investigators cannot manually monitor hundreds of channels.
- Even when they spot something, turning a screenshot into **court-admissible
  evidence** is slow and error-prone.

**NarcoScope AI does the watching and triage, so investigators spend their time on
the few accounts that matter — and hands them evidence that stands up in court.**

---

## Slide outline (8 slides, ~4 min)
1. **Title** — NarcoScope AI · "Cross-platform narcotics detection for Indian law
   enforcement." Team name + members.
2. **The problem** — trade on Telegram/WhatsApp/Instagram, coded Hindi slang,
   manual monitoring doesn't scale. One real (blurred) example.
3. **What it does** — 4-stage pipeline: **Ingest → Score → Link → Escalate**
   (one diagram; stress "human in the loop before escalation").
4. **Live demo** — switch to the app (see script below). *This is the slide you
   spend the most time on.*
5. **Detection engine** — hybrid: transparent rules + ML classifier + optional LLM.
   Show the measured accuracy: **Precision 0.97 / Recall 1.0 / F1 0.98** on a
   held-out, hand-labelled **Hindi + English** test set (52 messages).
6. **Operator networks** — the network graph: same UPI handle ⇒ one operator across
   Telegram + Instagram. "We surface the *person*, not just the post."
7. **Court-ready & lawful** — the SHA-256 evidence dossier + Section 63 BSA note.
   Explicit scope limits (no IP/phone extraction; lawful process for subscriber
   data). "Designed to be responsible, not just clever."
8. **Impact & roadmap** — 1 analyst watches 100 channels instead of 5; roadmap:
   bigger analyst-maintained slang dictionary, real-time alerts, more platforms.

---

## Live demo script (~3–4 min) — do this in order
> Have the backend + frontend running. Start on the **dashboard**, sample scan loaded.

1. **"This is a live system, not mockups."**
   - Point at the flagged-accounts table. "Nine accounts scanned, six flagged
     critical. Sorted by risk so an investigator triages the worst first."

2. **Show the Hindi detection (your killer differentiator).**
   - Click **@gwalior_night_plug**. In the evidence panel, read the flagged Hindi
     line: *"चिट्टा और गांजा उपलब्ध है, होम डिलीवरी Gwalior में, रेट पूछो DM पर."*
   - "It caught this in Hindi. Most tools only work in English — traffickers here
     don't write in English."

3. **Show the operator network (the investigative 'wow').**
   - Scroll to **Operator networks**. Point to the `nightplug@upi` cluster.
   - "The same UPI ID appears on a Telegram channel **and** an Instagram profile.
     That's not two leads — it's **one operator** running two storefronts. We link
     them automatically." Click a node → it opens that account.

4. **Generate the court-ready dossier.**
   - In the evidence panel, click **Generate legal-request dossier**.
   - "Every message gets a SHA-256 hash so we can prove it wasn't altered, plus a
     Section 63 Bharatiya Sakshya Adhiniyam note. The investigator prints this as
     a PDF and files it under lawful process." (Save-as-PDF in the print dialog.)

5. **Prove it's live, on real data.**
   - Open the **Telegram** panel, type a real public channel, hit **Scan channels**.
     Show it fetch and score live. "This is the official Telegram API — the one
     platform where scraping is lawful and first-party."

6. **Close on responsibility.**
   - Point to the **Model accuracy** panel (real numbers) and say: "We measured
     this honestly on labelled data. And nothing here auto-reports anyone — a human
     analyst signs off before anything escalates. For a police tool, that
     accountability matters as much as the accuracy."

---

## Anticipated judge questions (and answers)
- **"Can you read private WhatsApp chats?"** No — they're end-to-end encrypted and
  no tool can. We ingest a group's *own* exported chat once an investigator has
  lawfully joined it. Claiming otherwise would be illegal interception.
- **"Can you get the seller's phone/IP/address?"** No — platforms don't expose that
  publicly. Our job ends at a well-evidenced dossier; subscriber records need
  lawful process (Section 91 BNSS, or MLAT for foreign platforms).
- **"How accurate is it, really?"** 0.97 precision / 1.0 recall on a held-out
  Hindi+English hand-labelled set — and we *show* the one false positive. It's a
  first-pass filter for humans, not an autonomous decider.
- **"What about new slang you haven't seen?"** The rules catch known terms; the ML
  generalises; ambiguous cases can escalate to an LLM. A real deployment keeps the
  evasion slang dictionary in a restricted, analyst-maintained module — publishing
  it would be a how-to-evade guide.
- **"Is this legal for police to use?"** It reads only public content, keeps a human
  in the loop, and produces integrity-hashed evidence for lawful process. It is
  built to fit within CrPC/BNSS and the BSA 2023, not around them.

## Differentiators to hammer (why you beat other teams)
1. **It runs live on real Telegram data** — not slideware.
2. **It works in Hindi/Hinglish** — tuned to how MP traffickers actually write.
3. **It finds operators, not just posts** — cross-platform UPI linking.
4. **It produces court-ready, hashed evidence** — you understand the prosecution
   pipeline, not just the tech.
5. **It's honest and responsible** — measured accuracy, stated limits, human sign-off.
