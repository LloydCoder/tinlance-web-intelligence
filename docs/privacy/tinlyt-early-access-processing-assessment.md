# Tinlyt early-access processing and transfer assessment

**Assessment date:** 3 November 2026  
**Controller:** Tinlance Limited  
**Scope:** Public website and early-access request workflow only  
**Status:** Technical controls and notice drafted; regulatory transfer review remains a launch gate.

## 1. Processing purpose and scope

The early-access form collects only the information needed to review and respond to a request:

- Name and email address.
- Optional company/project and role.
- Selected use case and optional workflow description.
- Mandatory request consent, notice version and timestamp.
- Separate optional product-update consent and timestamp.
- Anti-abuse challenge signals and keyed HMAC rate-limit identifiers.

The form must not invite passwords, API keys, private keys, confidential customer data or sensitive personal data. The authenticated Tinlyt workspace, investigations, evidence exports and browser execution are not included in this early-access processing scope.

The live feature flag remains disabled until the deployment and transfer gates in section 8 are met. No applicant records have been created.

## 2. Controller and contact

Tinlance Limited  
120 Okigwe Road, Owerri, Imo State, Nigeria  
Privacy contact: sales@tinlance.com (subject: Tinlyt privacy request)

No individual is described as a statutory Data Protection Officer in this assessment. Tinlance must determine whether it is a data controller of major importance under the NDPA/GAID classification criteria and appoint/notify a qualified DPO if required.

## 3. Data flow and provider inventory

| Provider | Function in this workflow | Verified processing/location facts |
|---|---|---|
| Vercel | Public website hosting and serverless intake endpoint | Vercel's DPA describes services running across AWS, Azure and Google Cloud infrastructure, multiple regions and globally replicated backups. Do not promise a single Vercel data region. |
| Supabase | Early-access request database and rate-limit store | Dedicated project `Tinlyt-Early-Access`, region `eu-west-1` (Ireland). Supabase states core project data is primarily hosted in the selected region; limited support/subprocessor processing may occur elsewhere. |
| Resend | Applicant confirmation and internal notification email | Sending domain uses `eu-west-1` for sending. Resend states customer data, message content and delivery logs are stored in the United States. |
| Cloudflare Turnstile | Bot and abuse prevention | Turnstile processes browser/device/interaction signals to provide the challenge service; Cloudflare also describes separate processing to improve detection capabilities. |

Sources reviewed:
- NDPC, Nigeria Data Protection Act 2023 — General Application and Implementation Directive 2025, Article 7, Article 34, Article 45 and Schedule 5: https://ndpc.gov.ng/wp-content/uploads/2025/07/NDP-ACT-GAID-2025-MARCH-20TH.pdf
- Vercel DPA: https://vercel.com/legal/dpa
- Supabase DPA: https://supabase.com/legal/customer-resources/data-processing-addendum
- Supabase data residency and transfers FAQ: https://supabase.com/legal/privacy-resources/data-residency-and-transfers-faq
- Resend security and GDPR information: https://resend.com/security and https://resend.com/security/gdpr/
- Cloudflare Turnstile privacy addendum: https://www.cloudflare.com/turnstile-privacy-policy/

## 4. Lawful purposes and bases

| Purpose | Proposed NDPA basis | Limitation |
|---|---|---|
| Review and respond to an early-access request | Processing at the data subject's request before a potential contract, where necessary; otherwise consent for the clearly described request handling | Do not use request data for unrelated marketing. |
| Optional product updates | Separate, affirmative consent | Must be optional, timestamped and withdrawable. |
| Abuse prevention and endpoint security | Legitimate interests in protecting the service and preventing automated abuse | Maintain a documented legitimate-interest assessment and minimize identifiers. |
| Legal claims or legal obligations | Applicable legal obligation or establishment/exercise/defence of legal claims | Retain only what is necessary for the relevant purpose. |

This table is an operational assessment, not a legal opinion. Tinlance must ensure each purpose has a documented lawful basis before enabling intake.

### Legitimate-interest assessment — endpoint security

- **Purpose:** prevent automated abuse, duplicate spam, credential-stuffing attempts and denial-of-service patterns against the public request endpoint.
- **Necessity:** Turnstile challenge verification and short-lived IP/email-derived HMAC counters provide proportionate abuse controls. The endpoint does not persist raw IP addresses in the rate-limit table.
- **Balancing:** the processing is limited to a request form, does not profile applicants for unrelated purposes, does not determine access eligibility automatically, and uses keyed hashes with short retention. The impact is limited compared with the security benefit.
- **Safeguards:** server-only database access, RLS, no browser-role table permissions, origin/hostname checks, HMAC-SHA256 identifiers, five requests per 15-minute window, and scheduled expiry of rate-limit rows.
- **Conclusion:** legitimate interests are the proposed basis for narrowly scoped endpoint-security processing. This conclusion must be revisited if the data collected, abuse controls, retention or service scope changes. Data subjects may raise an objection through the privacy contact; security processing necessary to protect the endpoint may continue where the applicable legal test permits it.

## 5. Cross-border transfer analysis

Personal data may be processed in Ireland/EU, the United States and other locations used by Vercel or Cloudflare subprocessors. The Resend sending region does not change the fact that Resend stores customer data in the United States.

The NDPA sections 41–42 and GAID 2025 Article 45/Schedule 5 govern transfers from Nigeria. Schedule 5 identifies an NDPC adequacy decision, an NDPC-approved cross-border data transfer instrument, or another lawful basis as potential grounds. It also describes transfers necessary for a contract or steps taken at the data subject's request before entering a contract.

The narrow proposed basis for this workflow is that the data subject requests evaluation and a response, and the selected cloud/database/email services are used to perform those requested steps. That basis must be assessed provider-by-provider and destination-by-destination. Resend's EU Standard Contractual Clauses are relevant contractual safeguards but are not represented here as an NDPC adequacy decision or an NDPC-approved Nigerian transfer instrument.

Before enabling the form, Tinlance must retain evidence of:
1. The applicable NDPA section 42 ground for each provider and destination.
2. The provider DPA and current subprocessor list for each service.
3. The technical and contractual safeguards relied upon.
4. The assessment of risks to data subjects and the complaint/redress route.
5. Any additional consent or transfer instrument required after qualified Nigerian privacy review.

If a required transfer basis or safeguard is not established, the form remains disabled. The privacy notice must not state that every transfer is covered by an adequacy decision.

## 6. Retention and deletion

- Early-access request rows are deleted when `created_at` is older than 12 months, except where a documented legal obligation or legal claim requires a limited extension.
- Rate-limit HMAC rows are deleted when `updated_at` is older than 24 hours. A scheduled hourly job means cleanup occurs within approximately 25 hours.
- Marketing opt-in is stored on the request row and is removed with that row; withdrawal must be honoured earlier.
- Provider email, log and backup retention follows the provider's current plan and published deletion/backup policy. Tinlance must not promise provider-side deletion sooner than the provider contract permits.

The database migration `20261103070000_early_access_retention.sql` creates a private SECURITY DEFINER cleanup function with an empty search path, revokes execution from browser and application roles, and schedules it hourly through Supabase Cron. The corresponding pgTAP tests insert synthetic expired/current rows inside a rollback transaction and verify the boundaries.

## 7. Technical and organisational safeguards

- RLS enabled on request and rate-limit tables; no browser-role table policies.
- Anonymous and authenticated roles have no access to intake records or the private rate-limit schema.
- The endpoint uses a server-only Supabase credential; application service-role grants are limited to insert, generated identifier/timestamp readback and delivery-status updates.
- The rate-limit RPC is SECURITY INVOKER with an empty search path and bounded arguments.
- Rate-limit identifiers are HMAC-SHA256 hashes; raw IP addresses are not written to the rate-limit table.
- Turnstile hostname and request origin are checked; the form rejects non-JSON and oversized requests.
- Optional marketing consent is separate from mandatory request consent.
- The form and endpoint remain disabled until all required configuration and acceptance tests pass.
- Public landing pages do not intentionally load advertising or analytics trackers. The homepage discloses the current cookie/tracking position.

## 8. Launch gates

The following remain outstanding and must be evidenced before enabling early access:

1. Add a dedicated Supabase server secret to Vercel. The publishable/anon key is not sufficient and must never be substituted.
2. Create a dedicated Resend sending-only key restricted to `tinlance.com`, then add it as a sensitive Vercel environment variable without exposing the token in chat.
3. Add the approved notice version to Vercel; keep `EARLY_ACCESS_ENABLED=false` until the deployment includes the notice and runtime configuration.
4. Complete the NDPA cross-border transfer assessment and verify processor DPAs/subprocessor disclosures.
5. Verify the latest frontend deployment on Vercel; the current production alias is behind main while the Hobby deployment/build-rate limit is active.
6. Run controlled end-to-end tests on a non-production preview or isolated test environment: Turnstile pass/fail, rate limits, duplicate submission, database persistence, both email flows, delivery status update and deletion.
7. Verify the hourly retention job runs successfully in the live Supabase Cron history.
8. Keep public workspace, account, investigation and evidence processing disabled until their separate privacy notice, terms and live data flows are documented.

## 9. Current state

The dedicated Supabase project is healthy, has no applicant rows, and its migration history is aligned with the repository through the least-privilege migration. The retention migration is prepared in source control and must pass the isolated database workflow before being applied to the live project. No applicant emails have been sent. No AWS application infrastructure has been provisioned. The frontend is hosted on Vercel, but the latest main revision has not been promoted to the custom production domain.
