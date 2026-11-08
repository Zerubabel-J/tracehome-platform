# Requirements

This document describes **what** TraceHome must do and **how well**, not how it's built. It
deliberately avoids naming technologies, so we can think about the problem without being anchored
to a solution.

Each section ends with questions for the team. Answer them alone first, then discuss together.

## 1. The problem

### Problem statement, to validate

Home seekers in Addis Ababa search Telegram groups, brokers, and word of mouth. They often find
listings that are outdated, misleadingly described, already taken, or posted by people who aren't
authorized to advertise them. They lose time, travel, and money, and they don't know whom to trust.

Advertisers have a matching problem: honest owners, brokers, and agencies struggle to stand out
from unreliable ones.

### What we need to learn

Interview at least five seekers and five advertisers. Record what you hear, not what you hoped to hear.

**Seekers**
- How do you search for a home today?
- What makes you distrust a listing or a broker?
- Tell us about a viewing that went badly. What happened?
- How do you check that a home is still available?
- Would you pay to contact an advertiser? When, and how much?

**Advertisers**
- How do you advertise today, and what does it cost?
- How many inquiries are serious?
- What would make seekers trust you more?
- Would you pay for a better way to reach serious seekers?
- What would you need from us to prove you're genuine?

### Questions for the team

- Is the main pain finding homes, trusting listings, or something we haven't seen yet?
- What will people use instead of TraceHome, and why would they switch?

## 2. Users and stakeholders

| User | Who they are | What they want |
|---|---|---|
| Seeker | Someone renting or buying a home | Genuine listings, honest advertisers, less wasted time |
| Individual owner | Rents or sells their own property | Serious seekers, simple listing, little effort |
| Independent broker | Advertises others' properties | More clients, a good reputation |
| Agency | A registered business with several agents | Manage team and listings, grow the brand |
| Agent | Works for an agency | Manage assigned listings and leads |
| Moderator | Works for TraceHome | Verify advertisers and listings, handle reports and disputes |
| External tools | An advertiser's CRM or automation tool | Receive new leads automatically |

### Questions for the team

- Which user matters most at launch, and why?
- Can one person be both a seeker and an advertiser?
- Can one person belong to several agencies?
- Should brokers need written permission from owners?

## 3. Value for each side

| User | Gets | Gives |
|---|---|---|
| Seeker | Free browsing, trust signals, refunds for bad listings | Credits for contacts, honest reviews |
| Owner | Reach serious seekers | Accurate listings, availability updates |
| Broker and agency | Leads, reputation, team tools | Subscription, verification, accurate listings |
| TraceHome | Revenue and a trusted marketplace | Verification, moderation, fair rules |

**The tension to resolve:** we charge both sides, so each side must clearly get more value than it
pays. If seekers can easily find the same contacts elsewhere, they won't pay.

## 4. Business model

### Decided

- Free for both sides at launch, with bonus credits for seekers.
- Contact unlocks use credits from day one, even while free.
- Advertisers will later pay a monthly plan, limited by listings and agents.
- Purchased credits never expire.
- Bonus credits expire after 3 months, and are spent before purchased credits.
- Downgrading pauses listings above the new limit. Nothing is deleted.
- Individual owners get a permanent free plan, with up to 4 active listings.
- Clear hidden contact details send the listing back to the advertiser with the text highlighted.
  Unclear cases go to a moderator, and repeat offenders get an account review.
- Refunds follow precise rules, and doubtful cases go to a person.
- Contact details hidden in listings are detected and handled.

### Initial ideas, to discuss

- Browsing is free.
- Seekers buy credit packages, and one credit unlocks one listing's advertiser contact.
- Reopening a contact you already unlocked costs nothing.
- Credits are refunded for listings that are unavailable, fraudulent, duplicated, or unreachable.
- Purchases are simulated until we've checked payment rules, refunds, and disputes.

### Open

| Question | Options to consider |
|---|---|
| Package sizes and prices | To be learned from interviews |
| Which listings are paused on a downgrade? | The advertiser chooses; otherwise the oldest are paused first |
| What happens when a plan payment fails? | Grace period, then features limited |

### Plans and limits

Free launch access is modelled as a plan, a "launch plan" with generous limits. When charging
starts, only the plans change, not the system.

| Plan concept | Meaning |
|---|---|
| Plan | A named package, such as Free, Starter, or Agency |
| Limits | Maximum active listings and agents |
| Subscription | Which plan an advertiser has, and its status |
| Entitlement check | Before publishing a listing or adding an agent, confirm the plan allows it |

### Credit lots

Because bonus credits expire and purchased ones don't, a balance is not just a single number. Each
grant or purchase is a **lot** with its own amount, type, and expiry date.

| Example lot | Amount | Expires |
|---|---|---|
| Welcome bonus, 5 Nov | 5 | 5 Feb |
| Purchase, 20 Nov | 10 | Never |

- Spending uses the bonus lot that expires soonest, then purchased lots.
- Seekers are reminded before bonus credits expire.
- Expiry is recorded in the ledger like any other change, so the history always adds up.

### Downgrades

| Rule | Detail |
|---|---|
| Who chooses | The advertiser picks which listings stay active; if they don't, the oldest are paused first |
| What seekers see | Paused listings disappear from search |
| Earlier unlocks | Seekers who already unlocked a paused listing keep access to its contact |
| Grace period | Proposed: 7 days' notice before pausing starts |
| Upgrading again | Paused listings can be reactivated, but must be reconfirmed as available |

### Free owner plan

Brokers might register as owners to avoid paying. The limit of 4 active listings, plus
ownership checks, makes that harder.

### Proposed refund rules

| Situation | Proposed handling |
|---|---|
| Advertiser marks the listing unavailable within 24 hours of an unlock | Automatic refund |
| Moderator removes the listing as fraudulent or duplicated | Automatic refund for everyone who unlocked it |
| Seeker reports no response, and the advertiser doesn't answer TraceHome within 48 hours | Automatic refund |
| Seeker reports wrong contact details | A person reviews it |
| A seeker requests unusually many refunds | A person reviews it |

The time limits are proposals to discuss.

## 5. Key journeys

These show the flow of the business, not of any technology.

### Advertiser joins and gets verified

```mermaid
flowchart TD
    a["Advertiser signs up"]
    b{"Owner, broker,<br/>or agency?"}
    o["Owner: simple checks"]
    br["Broker: extra checks"]
    ag["Agency: registration checks"]
    v{"Moderator<br/>approves?"}
    ok["Verified level shown<br/>on profile"]
    no["Asked for more<br/>information"]
    a --> b
    b --> o --> v
    b --> br --> v
    b --> ag --> v
    v -- Yes --> ok
    v -- No --> no --> v
```

### A listing's life

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> PendingReview: Advertiser submits
    PendingReview --> Published: Moderator approves
    PendingReview --> Draft: Changes requested
    Published --> Expired: Not reconfirmed in time
    Expired --> Published: Advertiser reconfirms
    Published --> Unavailable: Rented or sold
    Published --> Removed: Moderator removes it
    Unavailable --> [*]
    Removed --> [*]
```

### A seeker finds a home

```mermaid
sequenceDiagram
    autonumber
    actor Seeker
    participant TH as TraceHome
    actor Advertiser

    Seeker->>TH: Browse and search for free
    Seeker->>TH: Buy credits
    Seeker->>TH: Spend a credit to unlock a contact
    TH-->>Seeker: Show advertiser's contact details
    TH-->>Advertiser: Notify about a new lead
    Seeker->>Advertiser: Arrange a viewing
    TH->>Seeker: Ask how it went
    Seeker->>TH: Report the viewing
    Seeker->>TH: Review listing and advertiser
    TH-->>Advertiser: Share review, allow a response
```

### Something goes wrong

```mermaid
flowchart TD
    a["Seeker reports a problem"]
    b{"What kind?"}
    c["Listing unavailable<br/>or unreachable"]
    d["Listing misleading<br/>or fraudulent"]
    e["Advertiser behaved badly"]
    r["Refund the credit"]
    m["Moderator investigates"]
    act["Warn, lower verification,<br/>or remove"]
    rev["Becomes part of a review"]
    a --> b
    b --> c --> r
    b --> d --> m --> act
    d --> r
    b --> e --> rev
```

### Questions for the team

- What exactly counts as a "reported viewing"? Can we trust it?
- How long can a listing stay published before it must be reconfirmed?
- What happens to unlocked contacts when a listing is removed?
- Should advertisers see who unlocked their contact?

## 5a. Review cases

The same pattern appears again and again: **automate clear cases, and send doubtful ones to a
person.**

| Case type | Created when |
|---|---|
| Identity check | Automated identity check isn't confident |
| Licence check | An agency submits a licence |
| Ownership check | Ownership documents are submitted |
| Refund | A refund doesn't match a clear rule |
| Hidden contact details | Detection isn't sure, or the advertiser appeals |
| Review dispute | An advertiser disputes a review |
| Report | Someone reports a listing or advertiser |

**Proposed:** one shared review system for all case types, not a separate one for each. Every case
has a type, priority, status, assigned moderator, waiting time, and decision record.

```mermaid
stateDiagram-v2
    [*] --> Open: Automation isn't sure
    Open --> InReview: Moderator picks it up
    InReview --> Decided: Moderator decides
    InReview --> WaitingForInfo: More information needed
    WaitingForInfo --> InReview: Information received
    Decided --> Appealed: Affected person appeals
    Appealed --> InReview: Reopened
    Decided --> [*]
```

### What the AI checks must provide

| Requirement | Reason |
|---|---|
| A confidence level with every result | Decides between approving automatically and sending to a person |
| A reason a person can understand | Moderators and advertisers must know why |
| A record of every automated decision | Audits, appeals, and measuring accuracy |
| A person can overrule any automated decision | Automation will make mistakes |
| Accuracy measured against people's decisions | Shows whether the thresholds are right |
| Checks run in the background | People shouldn't wait on a screen while checks run |

## 6. Business rules

None of these rules is agreed yet. Change a status to **Agreed** only after the team decides.

| Area | Rule | Status |
|---|---|---|
| Verification | Every advertiser has a visible verification level | To discuss |
| Verification | Brokers need more checks than owners and agencies | To discuss; checks not defined |
| Listings | A listing must be approved before it's public | To discuss |
| Listings | Listings expire unless reconfirmed | To discuss; period open |
| Listings | Contact details mustn't appear in the listing itself | To discuss |
| Credits | One credit per listing contact, no repeat charge | To discuss |
| Credits | A credit can never be spent twice, or lost | To discuss |
| Credits | Every purchase, spend, and refund is permanently recorded | To discuss |
| Credits | Purchased credits never expire | Agreed |
| Plans | Publishing listings and adding agents is limited by the advertiser's plan | Agreed |
| Refunds | Clear cases are automatic; doubtful cases go to a person | Agreed |
| Listings | Hidden contact details in text or photos are detected | Agreed |
| Reviews | Only after an unlock and a reported viewing | To discuss |
| Reviews | Listing accuracy and advertiser behavior rated separately | To discuss |
| Reviews | Advertisers can respond and dispute | To discuss |
| Reviews | Overall rating shown only after enough reviews | To discuss; number open |
| Reviews | Abusive or defamatory reviews are moderated | To discuss |
| Privacy | Contact details are shown only to seekers who unlocked them | To discuss |
| Leads | Advertisers can receive leads in their own tools | To discuss |

## 6a. Trust and verification

Status: the four trust levels, automation with human review, and broker approval are decided.
Everything else in this section is a proposal to discuss.

### Two kinds of trust

The trust ladder mixes two different things. **Who** the advertiser is belongs to the account.
**Whether they may advertise this home** belongs to each listing. An agency can be fully licensed
and still post a listing it has no right to advertise.

| Applies to | Level | What's checked | Who checks it |
|---|---|---|---|
| Advertiser | Phone confirmed | The advertiser controls the phone number | Automated |
| Advertiser | Identity checked | The person is who they claim to be | Automated where possible, a person when unsure |
| Advertiser | Licensed agency | A valid business or brokerage licence | A person, unless an official online check exists |
| Listing | Advertising approved | The owner allowed this broker to advertise this home | The owner confirms through TraceHome |
| Listing | Ownership proven | The advertiser, or the owner they act for, owns the home | A person reviews ownership documents |

**Proposed:** show seekers both badges, the advertiser's level and the listing's level, with the
date each check was done.

### Automation with human review

```mermaid
flowchart TD
    a["Advertiser submits evidence"]
    b["Automated check"]
    c{"How confident?"}
    ok["Approve automatically"]
    hum["Person reviews"]
    no["Reject, with the reason"]
    a --> b --> c
    c -- "High" --> ok
    c -- "Uncertain" --> hum
    c -- "Clearly invalid" --> no
    hum --> ok
    hum --> no
```

Automation can't check everything:

| Check | Can it be automated? |
|---|---|
| Phone ownership | Yes, with a one-time code |
| Identity | Possibly. Ethiopia's Fayda national ID offers consent-based checks to approved organizations, which requires an agreement. Until then, simulate it. |
| Business licence | We found no official online check, so a person reviews it for now |
| Ownership documents | A person reviews them |

**Two kinds of error:** wrongly approving a fraudster damages seekers' trust, while wrongly
rejecting an honest advertiser loses supply. **Decided:** approving a fraudster is worse. So
automation approves only clear cases, and doubtful ones go to a person.

To keep honest advertisers from leaving while they wait, tell them exactly what's missing, show
how long review usually takes, and let them prepare listings that publish once they're verified.

### Broker approval from the owner

Proposed approach: the owner confirms through TraceHome.

```mermaid
sequenceDiagram
    autonumber
    actor Broker
    participant TH as TraceHome
    actor Owner

    Broker->>TH: Create listing and enter the owner's phone number
    TH->>Owner: Send a confirmation request
    Owner->>TH: Approve this broker, for this home, until a chosen date
    TH-->>Broker: Listing can be published
    Owner->>TH: Can withdraw approval at any time
    TH-->>Broker: Listing is unpublished if approval is withdrawn
```

| Rule | Reason |
|---|---|
| Approval is per broker, per home, and expires | Limits the damage if something goes wrong |
| The owner can withdraw approval at any time | The owner stays in control |
| The owner's name must match the ownership document, if one is provided | Stops a broker using a friend's phone |
| Moderators audit a random sample | Catches fraud that the automated steps miss |
| Several approved brokers for one home are shown as one listing | Avoids duplicate listings |

**Weakness to accept:** a broker could still give a fake owner number. Matching names, random audits,
and reputation reduce this risk, but they can't remove it completely.

### Losing a level

| Event | Effect |
|---|---|
| A document or licence expires | Level expires; the advertiser is reminded beforehand and can renew |
| Important details change, such as name or licence | Level returns to pending until rechecked |
| Fraud is suspected | Temporary suspension while a moderator investigates |
| Fraud is confirmed | Level removed, and listings unpublished |
| Owner withdraws approval | That listing's approval is removed; the advertiser keeps their level |
| Repeated complaints | Triggers a review; never an automatic penalty |

Every change records who made it, when, and why. The advertiser is notified, given the reason,
and can appeal.

```mermaid
stateDiagram-v2
    [*] --> Pending
    Pending --> Verified: Checks pass
    Pending --> Rejected: Checks fail
    Verified --> Expired: Document or licence expires
    Expired --> Pending: Advertiser renews
    Verified --> Pending: Important details change
    Verified --> Suspended: Fraud suspected
    Suspended --> Verified: Cleared on investigation
    Suspended --> Revoked: Fraud confirmed
    Rejected --> Pending: Advertiser resubmits
```

### Retention and the law

Ethiopia's Personal Data Protection Proclamation (No. 1321/2024) is in force. Summaries say it
requires keeping personal data no longer than its purpose needs, gives people rights such as access
and erasure, and **may require personal data collected in Ethiopia to be stored in Ethiopia**. We
haven't read the official text, so every point here needs legal confirmation.

**Proposed principle:** store as little as possible. If an identity check can return a yes or no
answer, keep the answer, not a copy of the ID.

| Record | Proposed retention, pending legal advice |
|---|---|
| ID images, if we must keep them | Delete soon after verification, once any appeal period ends |
| Verification decisions, without the documents | Keep for several years, for disputes and audits |
| Ownership documents | Keep while listings are active, plus a dispute period |
| Audit records | Keep for years, and protect them from being changed |

**Decided for now:** everything runs on AWS, using made-up data. Personal data is kept clearly
separate from other data, so it could move to local storage later if the law requires it.

**Why this matters for architecture:** minimizing data may remove the need to archive ID images at
all. Long-term archive storage would then be for decision records, audit records, and ownership
documents. A legal requirement can add a service, and it can also remove one.

## 6b. Rules that must always hold

An **invariant** is a rule that must be true at every moment, no matter how many people act at
once, and even if something crashes halfway. Invariants decide which actions must happen as one
all-or-nothing step, and that later shapes the architecture.

Agreed on 6 November. **Instantly** means the rule is checked and changed in one
all-or-nothing step. **Eventually** means it may take seconds or minutes, but must never be lost.

| # | Invariant | Proposed | Reason |
|---|---|---|---|
| 1 | A seeker can't spend more credits than they have | Instantly | Even a short gap lets two requests both succeed |
| 2 | A credit is never spent twice, even when a request is retried | Instantly | A retry must return the first result, not charge again |
| 3 | A seeker never pays twice to unlock the same listing | Instantly | Same reason as rule 2 |
| 4 | A seeker's balance always equals the sum of their ledger entries | Instantly | The balance and its ledger entry change together |
| 5 | An expired bonus credit can't be spent | Instantly, when spending | Checked at the moment of use; the cleanup job can run later |
| 6 | Contact details are visible only to seekers who unlocked them | Instantly | A leaked number can't be taken back |
| 7 | An advertiser never has more active listings or agents than their plan allows | Instantly, when publishing | After a downgrade, a 7-day grace period applies on purpose |
| 8 | Only approved listings appear in search | Eventually for appearing; removal within 1 minute | A late appearance harms nobody; a fraudulent listing must vanish fast |
| 9 | A broker's listing is public only while the owner's approval is valid | Quickly in search; instantly when unlocking | Same pattern as rule 8 |
| 10 | A review exists only after an unlock and a reported viewing | Instantly | Checked when the review is created |
| 11 | One seeker leaves at most one review per unlock | Instantly | Stops duplicate reviews |
| 12 | An advertiser never sees another advertiser's private data | Instantly | Any leak is a serious breach |
| 13 | Every unlock produces a lead for the advertiser | Eventually, but guaranteed | A short delay is fine; losing a lead is not |
| 14 | Every automated or human decision is recorded, and the record can't be changed | Instantly for the record; eventually for archiving | A decision without a record can't be audited |
| 15 | A removed agent loses access immediately | Within 5 minutes | Agreed limit for signed-in sessions |

### Three principles from this list

1. **Money and permissions need instant rules.** Credits, unlocks, reviews, and access must be
   checked and changed together in one place.
2. **Lists and copies can lag, but actions can't.** Search results and cached pages may be slightly
   out of date. But when a seeker acts, such as unlocking a contact, the system checks the
   up-to-date record.
3. **Eventually still means guaranteed.** Leads, notifications, and archiving can wait, but they
   must never be lost.

## 7. Domain model

These are the main business concepts and how they relate. They aren't database tables.

```mermaid
erDiagram
    ADVERTISER ||--o{ MEMBER : has
    ADVERTISER ||--o{ LISTING : publishes
    ADVERTISER ||--o{ VERIFICATION : receives
    LISTING ||--o{ PHOTO : shows
    SEEKER ||--o{ CREDIT_ENTRY : owns
    SEEKER ||--o{ CONTACT_UNLOCK : makes
    LISTING ||--o{ CONTACT_UNLOCK : receives
    CONTACT_UNLOCK ||--o| VIEWING_REPORT : leads_to
    VIEWING_REPORT ||--o| REVIEW : allows
    REVIEW ||--o| RESPONSE : gets
    SEEKER ||--o{ REPORT : files
    LISTING ||--o{ REPORT : about
    LISTING ||--o{ OWNER_APPROVAL : needs
    ADVERTISER ||--o| SUBSCRIPTION : has
    SUBSCRIPTION }o--|| PLAN : follows
    REVIEW_CASE }o--|| MODERATOR : assigned_to
```

| Concept | Meaning |
|---|---|
| Advertiser | An owner, broker, or agency that publishes listings |
| Member | A person acting for an advertiser, such as an agency's agent |
| Verification | A check TraceHome performed, and its result |
| Owner approval | An owner's time-limited permission for a broker to advertise one home |
| Plan | A package with limits on listings and agents |
| Subscription | Which plan an advertiser has, and its status |
| Review case | Any decision automation sends to a person |
| Listing | A property offered for rent or sale |
| Credit entry | A permanent record of a purchase, spend, or refund |
| Contact unlock | A seeker paying to see one listing's advertiser contact; also a lead |
| Viewing report | A seeker's statement that a viewing happened, and its outcome |
| Review | Ratings of listing accuracy and advertiser behavior, with comments |
| Report | A complaint about a listing or advertiser |

### Questions for the team

- What other concepts are missing?
- Which concepts belong to an advertiser, and must stay private from other advertisers?
- Which records must never be changed or deleted?

## 8. Functional requirements

| Area | Requirement | Suggested version |
|---|---|---|
| Accounts | Seekers and advertisers can register and sign in | First |
| Advertisers | Advertisers choose a type and submit verification details | First |
| Advertisers | Agencies invite members and assign roles | First |
| Listings | Advertisers create, edit, submit, reconfirm, and close listings | First |
| Listings | Listings include photos, price, type, sub-city, and neighborhood | First |
| Moderation | Moderators approve or reject advertisers, listings, and reviews | First |
| Search | Anyone can browse and filter by area, price, type, and size | First |
| Credits | Seekers buy credits through a simulated payment | First |
| Credits | Seekers spend credits to unlock contacts and see their balance | First |
| Credits | Refunds are issued for eligible problems | First |
| Leads | Advertisers see who unlocked their listings | First |
| Leads | Advertisers can send new leads to an external tool automatically | First |
| Reviews | Eligible seekers report viewings and leave reviews | First |
| Reviews | Advertisers respond to reviews or dispute them | First |
| Reports | Anyone can report a problem with a listing or advertiser | First |
| Search | Map and radius search | Later |
| Feedback | Voice feedback | Later |
| Payments | Real payments | Later |
| Languages | Amharic interface | Later |

## 9. Quality requirements

Agreed on 7 November. Different parts of TraceHome need different levels of quality. Treating
everything as equally critical is expensive and hides what really matters.

### Priorities

| Rank | Quality | Why it ranks here |
|---|---|---|
| 1 | Correctness of money and permissions | A wrong charge or a leaked contact destroys trust and can't be undone |
| 2 | Security and privacy | Personal data and verification documents are sensitive |
| 3 | Availability of browsing | Seekers leave if they can't browse |
| 4 | Durability of leads and records | Paid leads and decisions must never be lost |
| 5 | Speed on mobile networks | Most seekers use phones, often on slow connections |
| 6 | Cost | Small budget; pay for what's used |

When two qualities conflict, the higher rank wins. For example, when the system can't confirm a
credit balance, it refuses the unlock rather than risk spending a credit twice.

### Targets by part of the system

| Part | Availability target | Speed target | Data loss allowed |
|---|---|---|---|
| Browsing and search | 99.9%, about 43 minutes of downtime a month | Search results in under 300 ms for 95% of requests; first page under 3 seconds on a slow mobile network | Not applicable; it shows copies |
| Unlocking and credits | 99.5% | Under 1 second for 95% of requests | None for confirmed transactions |
| Advertiser workspace | 99.5% | Under 1 second for 95% of requests | Up to 5 minutes, recovered from backup |
| Leads to external tools | Delivered within 1 minute normally; delayed during outages | Not applicable | None |
| AI checks and review cases | Delays are acceptable; cases wait in the queue | Clear cases decided within 5 minutes | None |
| Verification documents and records | Rarely read | Retrieval within hours is acceptable for old documents | None |

### Load

| Assumption | Value |
|---|---|
| Daily active users at a successful launch | 5,000 |
| Normal load | About 1 to 2 requests a second |
| Peak load | About 12 requests a second |
| Sudden spike, such as a viral Telegram post | 10 times peak for an hour |
| Active listings | 20,000 |
| Photos | About 10 per listing |

These numbers are estimates. Test them against interviews and real usage.

### Recovery

| Event | Expected behavior | Recovery target |
|---|---|---|
| One server or process fails | Others take over; users barely notice | Automatic, within a minute |
| One data center in the Region fails | System keeps running in another | Automatic, within minutes |
| Data deleted by mistake | Restore from backup | Within 1 hour, losing at most 5 minutes of data |
| A whole Region fails | Accept downtime, and rebuild from backups copied to a second Region | Hours to a day |

### Other qualities

| Quality | Requirement |
|---|---|
| Auditability | Every credit change, verification, and moderation decision can be explained |
| Security | Each role sees and does only what it needs |
| Abuse resistance | Scraping, fake accounts, and review attacks are limited and detected |
| Observability | We notice problems, such as lost leads or growing review queues, before users report them |
| Cost | Runs within a small budget, using the minimum resources when idle |

## 10. Constraints and assumptions

| Constraint | Effect |
|---|---|
| Team of three, all learning | Prefer designs we can fully understand and explain |
| Small budget | Run only what we need, when we need it |
| One development environment | No separate production environment for now |
| Built on AWS | Required by the course, but services are chosen later |
| Ethiopian data protection law | May restrict where personal data is stored and for how long; needs legal review |
| Learning is a goal | We'll choose designs that teach us core cloud concepts |

**Assumptions to check:** most seekers use mobile phones; seekers will pay for contacts; owners will
accept verification; addresses use sub-city and neighborhood more than street names.

## 11. What could go wrong

Agreed on 7 November. The goal is graceful degradation: when one part fails, the rest
keeps working, and the most important rules still hold.

| Failure | What users experience | What must stay true |
|---|---|---|
| Main database unavailable | Browsing still works from copies; unlocks and changes are refused with a clear message | No credit is lost or spent twice |
| Search unavailable | Simple browsing by area still works, or a clear message appears | Unlocks still check the up-to-date record |
| AI check service unavailable | Checks wait in a queue; nothing is approved automatically | No fraudster is approved during the outage |
| Advertiser's CRM offline for a day | Leads appear in TraceHome, and are delivered once the CRM returns | No lead is lost |
| Notifications fail | Delayed reminders and alerts | They're retried, and failures are visible |
| Viral traffic spike | Browsing slows slightly but works | Unlocks stay correct |
| Scraping attempt | Requests are limited, and credits block mass contact access | Advertisers' numbers stay protected |
| Data deleted by mistake | Short outage for the affected data | Restored with at most 5 minutes lost |
| Two requests spend the last credit | One succeeds, one is refused | Balance is never negative |
| Harmful or stolen photos uploaded | Not visible until checked | Nothing harmful is shown publicly |
| Competitor posts fake reviews | Reviews need an unlock and a reported viewing; patterns are flagged | Advertisers can dispute |
| A removed agent is still signed in | Loses access within 5 minutes | No private data is accessed after that |

For each failure: How likely is it? How bad is it? How would we notice? Who responds?

## 12. From requirements to architecture

Only after this document is agreed should we start choosing technology. When we do, every choice
should answer:

1. Which requirement does it serve?
2. What alternatives did we consider?
3. What tradeoff are we accepting?
4. How will we prove it works, including when it fails?

## Glossary

| Term | Meaning |
|---|---|
| Seeker | Someone looking to rent or buy a home |
| Advertiser | An owner, broker, or agency that publishes listings |
| Credit | A unit seekers spend to unlock one listing's advertiser contact |
| Unlock | Spending a credit to see a listing's contact details |
| Lead | A record that a seeker is interested in a listing |
| Verification level | What TraceHome has checked about an advertiser |
| Reconfirmation | An advertiser confirming a listing is still available |
