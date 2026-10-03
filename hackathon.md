# hackathon.md — rules and submission checklist

**AI Swarm Dynamics Hackathon** — AI Village (AI Digest, part of Sage, a 501c3) × Grove Research.
Page: https://swarmchasing.com · Discord: server "Sage" → `#hackathon-chat`, `#find-teammates` (Rohit joined 1 Oct).
Questions: `#hackathon` on the AI Village Discord, or [email].
Checked 1–2 Oct 2026. **If this file and the live page disagree, the live page wins — re-check at kickoff.**

## Clock

| | PT | IST |
|---|---|---|
**⚠️ CHANGED (logistics page, read 3 Oct from the official repo Georgeingebretsen/swarmchasing): submissions are due
Sun 5:00 PM PT — 4 hours earlier than we had. Chat + the form link moved to the Swarmchasing SLACK.**

| | PT | IST |
|---|---|---|
| Doors / check-in (SF) | Sat Oct 3, 10:00 AM | Sat Oct 3, 10:30 PM |
| Kickoff talk (livestream, link in Slack #announcements) | Sat Oct 3, 11:00 AM | Sat Oct 3, 11:30 PM |
| **Submissions due (form link in Slack #announcements)** | **Sun Oct 4, 5:00 PM** | **Mon Oct 5, 5:30 AM** |
| IRL demos (SF, ~2 min each, livestreamed) | Sun Oct 4, 6:00–7:00 PM | Mon Oct 5, 6:30–7:30 AM |
| Our submit target | | **Mon Oct 5, 2:00 AM** — 3.5 h buffer |

Slack invite: https://join.slack.com/t/swarmchasing/shared_invite/zt-4bkawym4l-CEe685XK94zEP9aB1gwfsw
Form asks: short write-up or video · GitHub repo link · optional results write-up · names + emails of the team.
One submission per team. Judged by a panel of Grove Research + AI Village staff, online = in-person; results ~1 week
after. (Compute reimbursement is for in-person attendees only.)

"Feel free to get started early!" (page + FAQ: "Can I start building before the weekend? Feel free to get started
ahead of time!").

## Hard rules (page + FAQ)
- Online registration auto-approved (done, 22 Sep, email from George Ingebretsen). Solo is fine; no team size limit.
- The AI Village dataset is optional ("Not at all!… you might not even involve direct transcript analysis") — we use it.
- **Dataset terms** (Hugging Face access form, accepted 30 Sep): use for research and analysis, **not to train or
  fine-tune AI systems** without written permission; **don't try to re-identify individuals**; **cite AI Digest /
  AI Village**; tell them about publications. Credentials found in data: report, never use.

## What to submit (FAQ, verbatim)
"(a) a short write-up / video explaining your project, (b) a link to github repo with your code, and (c) optionally a
write-up of real results you identified by using your tool."
- [~] Short write-up (`docs/WRITEUP.md` — drafted 3 Oct, numbers checked by `heirloom verify`) **and** a short video (script in WRITEUP.md)
- [ ] Public GitHub repo (no data files, no keys)
- [x] **Real results write-up** — `docs/WRITEUP.md` → "What we found" (marked as the results write-up; site: /findings)
- [ ] Where/how to submit: **not announced yet** — watch Discord `#hackathon-chat` and email; note it here

## How it's judged
"We're assembling a team of ~3-5 judges (members of the AI Village staff and experts in the field)." No written
criteria. Read the hosts' own words as the rubric:
- Greenblatt (quoted on the page): "We don't have good approaches for understanding/overseeing the activity and aims
  of AI 'swarms'."
- Shoshannah Tekofsky (AI Village, X, 9 Sep): "we currently have no good way to monitor all AI data"; (27 Aug) "We
  need more ways to speed up monitoring. If you have an idea, try it out on our data".
- George Ingebretsen (Discord, 23 Sep) on the daily summaries: "they don't really track the interesting stuff".
- Hitch (Discord): "Verification is a huge problem and mega time intensive."

## Likely judges (profile before the video)
AI Digest team: **Adam Binksmith** (Director), **George Ingebretsen** (runs the hackathon), **Shoshannah Tekofsky**,
**Zak Miller** (a 13 Jun 2025 memory says the 93-list "NEVER EXISTED (confirmed by [person]/help@)" — probably him, not
verified; if so, he lived that case). Advisor: Daniel
Kokotajlo. Grove Research: Larissa Schiavo, Deepfates. Possibly Transluce (sharing tooling at the event).

## Ship checklist (Mon Oct 5, by 6:00 AM IST)
- [x] The 93-list trail rebuilds from raw data with one command (`heirloom trail --case 93-list`)
- [ ] The "still alive" list on 2026 data, each item with evidence quotes and live-village links
- [x] Every number in the write-up comes from a saved run (`runs/<timestamp>.json`) with the export date
- [x] Human names / emails masked everywhere; AI Digest / AI Village cited
- [x] README: one-line pitch → what it does → how to run (download + `uv run`) → data terms → results
- [ ] Repo public, no data, no keys in history
- [ ] Video recorded (aim ≤ 3 min), write-up + results submitted the way the hosts ask, confirmation saved
- [ ] HACKATHONS sheet updated (append only)
