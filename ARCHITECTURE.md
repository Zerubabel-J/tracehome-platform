# Architecture

This document turns the agreed requirements into a design. We build it in two stages:

1. **Logical architecture:** the parts of the system and how they work together, without naming
   any technology. *(Done.)*
2. **AWS architecture:** each logical part mapped to AWS services, with a reason for every choice.
   *(In progress: the network is decided.)*

Separating the stages keeps the reasoning honest. If a part can't be justified without naming a
product, it probably isn't needed.

## Design principles

These nine principles guide every design choice. Each one protects specific business rules we
agreed in the requirements, listed here in full.

| Principle | What it means in practice | Business rules it protects |
|---|---|---|
| **1. One trusted source of truth for money and permissions** | Credits, unlocks, reviews, plan limits, and access rights are checked and changed together, in one place, as one all-or-nothing step | • A seeker can't spend more credits than they have<br>• A credit is never spent twice, even when a request is retried<br>• A seeker never pays twice to unlock the same listing<br>• A seeker's balance always equals the sum of their credit history<br>• An expired bonus credit can't be spent<br>• Contact details are visible only to seekers who unlocked them<br>• An advertiser never exceeds their plan's listing or agent limit<br>• A review exists only after an unlock and a reported viewing<br>• One seeker leaves at most one review per unlock<br>• An advertiser never sees another advertiser's private data |
| **2. Lists and copies may lag, but every action checks the source of truth** | Search results and cached pages may be slightly out of date. When someone acts, such as unlocking a contact, the system checks the current record. | • Only approved listings appear in search; a removed listing disappears within 1 minute<br>• A broker's listing is public only while the owner's approval is valid |
| **3. Background work is guaranteed, never lost** | Work that can wait, such as sending leads, is delayed safely and retried until it succeeds | • Every unlock produces a lead for the advertiser, even if their CRM is offline<br>• Every decision's record is archived for long-term keeping |
| **4. Automate clear cases, send doubtful ones to a person** | Automation decides when it's confident; otherwise a moderator decides | • Approving a fraudster is worse than rejecting an honest advertiser<br>• AI checks decide clear cases; people decide doubtful ones<br>• Refunds follow precise rules; doubtful ones go to a person<br>• Clear hidden contact details go back to the advertiser; unclear ones go to a moderator |
| **5. The public marketplace and the private workspace are designed differently** | Browsing is public, heavy, and fine slightly stale. The workspace is private, smaller, and must always be correct. | • TraceHome is two products: a public marketplace and a private advertiser workspace |
| **6. Personal data is kept separate, so it could move later** | Names, phone numbers, and documents are stored apart from everything else | • Everything runs on AWS for now, but personal data may need to move to Ethiopia if the law requires it |
| **7. Correctness beats availability when they conflict** | If the system can't be sure a credit is safe to spend, it refuses rather than risk a mistake | • Quality priority: correctness, then security, browsing availability, durability, speed, and cost |
| **8. Every decision leaves a record that can't be changed** | Credit changes, verifications, and moderation decisions are recorded when they happen, and never edited | • Every automated or human decision is recorded, and the record can't be changed<br>• Every purchase, spend, and refund is permanently recorded |
| **9. Pay for what's used; keep idle cost low** | Prefer parts that cost little when nobody is using them | • TraceHome runs within a small budget |

## The logical architecture

```mermaid
flowchart TB
    subgraph users["Users"]
        seeker["Seeker app"]
        workspace["Advertiser workspace"]
        console["Moderator console"]
        external["External tools<br/>CRM, automation"]
    end

    subgraph edge["Edge layer"]
        delivery["Content delivery<br/>Caches public pages and photos"]
        shield["Protection<br/>Filters attacks, limits request rates"]
    end

    subgraph entry["Entry layer"]
        gateway["Request entry<br/>Routes requests, checks sign-in"]
        identity["Identity<br/>Accounts, roles, sessions"]
    end

    subgraph core["Core application"]
        listings["Listings and plans"]
        credits["Credits and unlocks"]
        trust["Trust and verification"]
        reputation["Reviews and reputation"]
        cases["Review cases"]
        leads["Leads and integrations"]
    end

    subgraph truth["Source of truth"]
        db[("Transactional database<br/>Money, permissions, listings")]
        audit[("Audit records<br/>Can't be changed")]
    end

    subgraph copies["Copies for reading"]
        search[("Search index<br/>Up to 1 minute behind")]
    end

    subgraph files["File storage"]
        publicfiles[("Public files<br/>Approved photos")]
        privatefiles[("Private files<br/>Verification documents")]
        archive[("Archive<br/>Old documents and records")]
    end

    subgraph background["Background processing"]
        events["Event backbone<br/>Guaranteed delivery"]
        checks["AI checks<br/>Identity, documents, photos, hidden contacts"]
        delivery2["Lead delivery<br/>To external tools"]
        notify["Notifications<br/>SMS and email"]
        scheduler["Scheduled jobs<br/>Expiry, grace periods, reconciliation"]
        indexer["Search updates"]
    end

    subgraph ops["Operations"]
        monitor["Monitoring and alerts"]
        backup["Backups<br/>Copied to a second Region"]
    end

    seeker --> delivery
    workspace --> delivery
    console --> delivery
    delivery --> shield --> gateway
    gateway --> identity
    gateway --> core
    core --> db
    core --> audit
    core --> privatefiles
    core --> events
    seeker -. "reads" .-> search
    events --> checks
    events --> delivery2
    events --> notify
    events --> indexer
    indexer --> search
    checks --> cases
    delivery2 --> external
    scheduler --> core
    privatefiles --> archive
    delivery --> publicfiles
    monitor -. "watches" .-> core
    backup -. "protects" .-> db
```

### What each part does, and why it exists

| Part | Responsibility | Why it exists |
|---|---|---|
| Content delivery | Serves public pages and photos from copies close to users | Browsing must stay available, and fast on slow mobile networks |
| Protection | Blocks attacks and limits request rates | Scraping and abuse resistance |
| Request entry | One front door for every request | One place to check sign-in and route requests |
| Identity | Accounts, roles, and sessions that expire within 5 minutes | Advertisers never see each other's data, and removed agents lose access within 5 minutes |
| Core application | All business rules | Modules of one application, not separate services, so the team can understand and change it |
| Transactional database | The source of truth for money, permissions, and listings | Money and permission rules need one all-or-nothing place (principle 1) |
| Audit records | Every credit change and decision | P8 |
| Search index | A copy of approved listings, built for searching | Fast browsing; it may lag behind the database (principle 2) |
| Public files | Approved listing photos | Served to anyone, through content delivery |
| Private files | Verification documents | Never public; encrypted, with strict access (principle 6) |
| Archive | Documents and records kept for years | Rarely read, so cheaper storage is appropriate |
| Event backbone | Carries "something happened" messages, and keeps them until handled | Guaranteed background work (principle 3) |
| AI checks | Identity, documents, photos, and hidden contact details | Automated decisions with confidence levels (principle 4) |
| Review cases | One queue for every doubtful decision | One shared queue for all seven kinds of review case (principle 4) |
| Lead delivery | Sends leads to CRMs and automation tools, retrying when they're down | Every unlock must produce a lead for the advertiser |
| Notifications | SMS and email | Reminders, alerts, and confirmations |
| Scheduled jobs | Bonus expiry, listing expiry, grace periods, balance checks | Time-based rules |
| Monitoring | Notices problems before users report them | Observability |
| Backups | Restorable copies, also kept in a second Region | Restore lost data within 1 hour; survive a Region failure using copied backups |

## Core application modules

The core is one application with clear internal boundaries. Each module owns its data, and other
modules use it only through its defined actions.

| Module | Owns | Must keep instantly true |
|---|---|---|
| Accounts and advertisers | Users, advertisers, members, roles | Removed agents lose access within 5 minutes |
| Listings and plans | Listings, photos, plans, subscriptions | Plan limits when publishing |
| Trust and verification | Verification levels, owner approvals | Only valid approvals allow public listings |
| Credits and unlocks | Credit lots, ledger, unlocks | Credits are never overspent, spent twice, or spent after expiry; no listing is unlocked twice; contacts go only to seekers who unlocked them |
| Reviews and reputation | Viewing reports, reviews, responses | Reviews only after an unlock and a reported viewing; one review per unlock |
| Review cases | Cases, assignments, decisions | Every decision is recorded |
| Leads and integrations | Leads, connections to external tools | Every unlock creates a lead |

## Where work happens

The most important design boundary: what happens **while the user waits**, and what happens
**in the background**.

| While the user waits | In the background |
|---|---|
| Browsing and searching | Updating the search index |
| Unlocking a contact and spending a credit | Delivering the lead to the advertiser's CRM |
| Creating or editing a listing | AI checks on photos, text, and documents |
| Writing a review | Notifications |
| Moderator decisions | Expiry and grace period jobs |
| Signing in | Archiving old documents and records |
| | Copying backups to the second Region |

**The rule:** a user waits only for work that must be instantly true. Everything else goes to the
background, where it's guaranteed but can be delayed.

## Key flows

### Unlocking a contact

Everything inside the box happens as one all-or-nothing step. If any part fails, nothing changes.

```mermaid
sequenceDiagram
    autonumber
    actor Seeker
    participant App as Core application
    participant DB as Source of truth
    participant Events as Event backbone
    participant Leads as Lead delivery
    actor CRM as Advertiser's CRM

    Seeker->>App: Unlock this listing, with a request ID
    App->>DB: Was this request ID already handled?
    alt Already handled
        DB-->>App: Return the earlier result
    else New request
        rect rgba(120, 120, 120, 0.15)
            App->>DB: Lock the seeker's credit lots
            App->>DB: Check the listing is still approved and available
            App->>DB: Spend the soonest-expiring credit
            App->>DB: Record the unlock and the ledger entry
            App->>DB: Record a "lead created" event to send
        end
    end
    App-->>Seeker: Show the contact details
    DB->>Events: Send the recorded event
    Events->>Leads: Deliver the lead
    Leads->>CRM: Send, retrying if the CRM is down
```

**Why the event is recorded in the same step:** if the system crashed after spending the credit
but before recording the event, the advertiser would never get the lead, breaking the rule that
every unlock produces a lead. Saving the event with the unlock means a crash can't separate them. A background process
then sends it.

### Publishing a listing

```mermaid
sequenceDiagram
    autonumber
    actor Advertiser
    participant App as Core application
    participant Events as Event backbone
    participant AI as AI checks
    participant Cases as Review cases
    actor Mod as Moderator

    Advertiser->>App: Submit listing with photos
    App->>App: Check plan limit and owner approval
    App-->>Advertiser: Submitted, checks in progress
    App->>Events: Listing submitted
    Events->>AI: Check photos and text
    alt Clear contact details found
        AI->>App: Send back to advertiser, with the text highlighted
    else All clear
        AI->>App: Approve
        App->>Events: Listing published, so update search
    else Unsure
        AI->>Cases: Open a case
        Cases->>Mod: Assign by priority
        Mod->>App: Approve or reject, with a reason
    end
```

### Search staying up to date

```mermaid
flowchart LR
    a["Listing approved,<br/>changed, or removed"]
    b["Event recorded<br/>with the change"]
    c["Search updater"]
    d[("Search index")]
    e["Seeker browses"]
    f["Seeker unlocks"]
    g[("Source of truth")]
    a --> b --> c --> d --> e
    e --> f
    f -- "always checks" --> g
```

Search may be up to 1 minute behind. Unlocking always checks the source of truth, so a seeker can
never pay for a listing that was just removed.

## Data classes

Each kind of data needs different protection. This table drives encryption, access, and storage
choices in the next stage.

| Class | Examples | Who can see it | Kept for |
|---|---|---|---|
| Public | Approved listings, photos, review summaries | Anyone | While the listing is live |
| Internal | Plans, case queues, metrics | TraceHome staff | As needed |
| Personal | Names, phone numbers, email addresses | The person, and seekers who unlocked them | While the account exists, then by policy |
| Sensitive | ID checks, ownership documents | Moderators with a reason; every access recorded | By law, pending legal advice |
| Financial | Credit lots, ledger | The seeker, finance, and auditors | Years; never changed |
| Audit | Decisions and access records | Auditors | Years; never changed |

## Questions to answer before mapping to AWS

Answer these yourself first. They test whether the design is clear to you.

1. Why does unlocking a contact happen while the user waits, but delivering the lead doesn't?
2. Why is the search index allowed to be wrong for a minute, but the credit balance never is?
3. Why is the core one application with modules, and not seven separate services?
4. What happens to a lead if the advertiser's CRM is offline when the seeker unlocks the contact?
5. Why are public photos and verification documents stored separately?

---

# Stage 2: AWS architecture

Each part of the logical architecture is mapped to AWS here, one layer at a time, following a
request from the seeker's phone down to the data.

```text
DNS → CDN at the edge → firewall → load balancer → compute → database and files
           all inside a network: VPC, subnets, gateways
```

**Target versus build.** For every layer we describe two things:

- **Target design:** what TraceHome needs to meet its requirements with real users.
- **Development build:** what we actually run now, within a budget of about $30. Every difference
  is a conscious choice with a reason, and we know how to switch it on later.

## Network

### The rule

Only the load balancer faces the internet. Everything else is private and accepts traffic only
from the part directly in front of it.

The diagram shows the **target design**: what we present and defend. The development build is a
smaller version of it, described at the end of this section.

![TraceHome network architecture: target design](docs/network-architecture.svg)

*Open the image on its own for full size. The source is [docs/network-architecture.svg](docs/network-architecture.svg).*

### How to read the diagram

**Colors**

| Color | Meaning |
|---|---|
| Green | **Public subnet.** Routes to the internet gateway. Only the load balancer and NAT gateways live here |
| Blue | **Private app subnet.** The application and workers. Calls out through its own zone's NAT gateway; only the load balancer can call in |
| Teal | **Private data subnet.** The database and search index. No internet route at all, in or out |
| Purple | **The VPC and its doors.** The internet gateway and the S3 gateway endpoint are the only ways in or out |
| Amber | **Amazon S3.** A regional service outside the VPC |
| Orange, dashed | **Edge.** DNS, CDN, and firewall. Decided in the next layer |
| Grey dashed outline | **Availability Zone.** A separate data center in the same Region |
| Dashed box | **Standby.** Used only when something fails |

**Lines:** solid dark lines are requests and data access, dashed red lines are outbound calls
(never inbound), the dashed teal line is database replication, and amber lines are file traffic.
**SG** means security group: the only traffic each part accepts.

**Following the numbers**

| # | What happens | Why it's designed this way |
|---|---|---|
| ① | The seeker's phone looks up TraceHome's address | Users never see AWS internals, only a domain name |
| ② | All traffic arrives at the CDN over HTTPS | The CDN is close to users and filters attacks before they reach AWS |
| ③ | Photos come straight from the CDN's cache | Most browsing traffic never reaches our servers, which is fast and cheap |
| ④ | Pages and API calls the CDN can't cache go through the internet gateway to the load balancer | The load balancer accepts traffic from the CDN only, so no one can bypass the firewall |
| ⑤ | The load balancer shares requests between two copies of the application in two zones | If one zone fails, the other copy keeps serving |
| ⑥ | The application and workers read and write the source of truth | Every money and permission action checks here |
| ⑦ | Searches go to the search index; workers keep it up to date | Heavy browsing never slows down the source of truth |
| ⑧ | The database copies every change to a standby in zone B | If zone A fails, the standby takes over in 1–2 minutes with no lost data |
| ⑨ | Files go to S3 through the free gateway endpoint | No NAT charges for the largest traffic, and files never cross the internet |
| ⑩ | Calls to AI checks, CRMs, and SMS go out through each zone's NAT gateway | Private parts can call out, but nothing outside can start a connection in |

**What's deliberately in one zone:** the background workers and the search index. Work waits
safely in the queue, and the index can be rebuilt from the source of truth, so a zone failure only
delays them.

### Where each part lives

| Part | Where it lives | Who can reach it |
|---|---|---|
| Load balancer | Public subnets, in two zones | The internet, on HTTPS only |
| NAT gateway | Public subnet | Nothing can start a connection to it from outside |
| Application | Private app subnets | Only the load balancer |
| Background workers | Private app subnets | No one. They pull work from a queue; nothing calls into them |
| Database | Private data subnets | Only the application and the workers |
| Search index | Private data subnets | Only the application and the indexer |
| Files | Outside the VPC. S3 is a regional service, not part of a subnet | See below |

**Visible to the public is not the same as open to the public.** Both buckets stay private, with
Block Public Access turned on:

- Photos reach users through the CDN, and only the CDN has permission to read the public files
  bucket.
- Verification documents never go through the CDN. A reviewer gets a link that expires after a few
  minutes, and every access is recorded.

Keeping the two buckets apart limits the blast radius: one wrong permission setting can expose
only listing photos, which are public anyway, never identity documents.

### Three layers of subnets

| Layer | Contains | Route to the internet |
|---|---|---|
| Public | Load balancer, NAT gateway | Directly, through the internet gateway |
| Private app | Application, background workers | Outbound only, through the NAT gateway |
| Private data | Database, search index | None. Data can't leave by any internet path |

The data layer has no route to the internet at all. Even if an attacker got into the database
server, it couldn't send data out directly.

### Address plan (proposed)

| Range | Use |
|---|---|
| `10.20.0.0/16` | The whole VPC: about 65,000 addresses, room to grow, and unlikely to clash if we connect another network later |
| `10.20.0.0/24`, `10.20.1.0/24` | Public subnets, zones A and B |
| `10.20.10.0/24`, `10.20.11.0/24` | Private app subnets, zones A and B |
| `10.20.20.0/24`, `10.20.21.0/24` | Private data subnets, zones A and B |

### Security groups: "only from X" rules

Each part allows traffic only from the security group in front of it, not from an IP range, so
the rules keep working when containers change addresses.

| Security group | Allows in | From |
|---|---|---|
| Load balancer | HTTPS (443) | The internet |
| Application | The application port | The load balancer's security group only |
| Workers | Nothing | No one |
| Database | The database port | The application and workers security groups only |
| Search index | The search port | The application and workers security groups only |

### Calls going out

The application and workers must call services outside the VPC, without being reachable from
outside.

| Destination | Path | Why |
|---|---|---|
| S3 (photos, documents) | S3 gateway endpoint | Free, and photo traffic is the largest. Traffic stays inside AWS |
| AI checks, CRM webhooks, SMS | NAT gateway | The only way out to the internet for private subnets. Replies come back; new connections from outside can't come in |
| Other AWS services (queues, secrets, logs) | NAT gateway for now | An interface endpoint costs about $7 a month per zone. We add one when traffic or security justifies it |

**Not used here, and why.** VPC peering and Transit Gateway connect one network to another (VPC to
VPC, or VPC to an office datacenter). They don't give a private subnet a way out to the internet
or to AWS services, so they don't solve this problem.

### One zone or two

High availability matters most for the parts the user waits on. Parts behind a queue, or parts
that can be rebuilt, can live in one zone.

| Part | Target design | Why |
|---|---|---|
| Load balancer | Two zones | AWS requires at least two zones for an Application Load Balancer |
| Application | Two zones | Browsing must keep working if one zone fails |
| Database | Multi-AZ: a standby in the second zone | Correctness comes first. Failover takes about 1–2 minutes with no lost data |
| Background workers | One zone | Work waits safely in the queue. If the zone fails, workers restart elsewhere and catch up. Leads may arrive late, but are never lost |
| Search index | One node | It's a copy. If it's lost, we rebuild it from the source of truth |
| NAT gateway | One per zone | So losing a zone doesn't stop outbound calls in the other |
| Files | Automatic | S3 already stores every file across at least three zones |

### Target versus development build

| | Target design | Development build | What we accept |
|---|---|---|---|
| Database | Multi-AZ | Single zone, with automated backups | A zone failure means restoring from backup |
| NAT | One NAT gateway per zone (about $32 a month each) | One small NAT instance (about $3 a month) | Outbound calls stop if it fails, which only delays background work |
| Application | Two or more copies across two zones | One copy | Short downtime during deployments or failures |
| Load balancer | Two zones | Two zones | Required by AWS, so no difference |

**For the presentation:** "This is the architecture TraceHome needs. For the demo we run a cheaper
version, and we switch on Multi-AZ when there are real users."
