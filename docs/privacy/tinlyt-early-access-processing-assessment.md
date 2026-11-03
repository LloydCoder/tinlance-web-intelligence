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
| Vercel | Public website hosting and serverless intake endpoint | Vercel's DPA (last updated 17 March 2026; effective 31 March 2026) expressly applies to customers on Pro and Enterprise plans. The connected Tinlyt project is on Hobby. DPA coverage for this controller/processor relationship is therefore **not established** by the published DPA; confirm separately with Vercel or move the personal-data intake endpoint to a processor with an applicable DPA. Vercel infrastructure and subprocessors are global; do not promise a single processing region. |
| Supabase | Early-access request database and rate-limit store | Dedicated project `Tinlyt-Early-Access`, region `eu-west-1` (Ireland). Supabase's current published DPA is Version 1 dated 1 August 2026 and is effective as of the service agreement. Data is primarily stored/processed in the selected region, while authorized subprocessors may process elsewhere. |
| Resend | Applicant confirmation and internal notification email | The sending domain uses `eu-west-1` for sending, but this does not provide EU data residency: Resend states primary processing/storage is in the United States. Its published DPA is dated 31 December 2025 and becomes binding through acceptance of the Terms of Service or execution. Confirm actual account-plan retention and current subprocessor list before intake. |
| Cloudflare Turnstile | Bot and abuse prevention | The Turnstile Privacy Addendum (last updated 18 June 2025) identifies Signals including client IP, TLS fingerprint, User-Agent, sitekey and associated origin. Cloudflare acts as processor for challenge security and as a separate controller when using Signals to improve detection capabilities. |

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

The NDPA sections 41–42 and GAID 2025 Article 45/Schedule 5 govern transfers from Nigeria. Article 45(2) says Schedule 5 is to be used pending a further NDPC cross-border instrument. Schedule 5 identifies an NDPC adequacy decision, an NDPC-approved cross-border data transfer instrument, or another lawful basis as potential grounds, including transfers necessary for a contract or steps taken at the data subject's request before entering a contract. Article 34 expects a controller/processor DPA with specified parties, purposes, processing locations, lawful bases, responsibilities, technical/organisational measures, DPIA/risk details and other contractual terms. The applicable transfer basis and DPA adequacy must be confirmed by qualified Nigerian privacy counsel; this engineering assessment does not decide the legal test.

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

The database migration `20261103061953_early_access_retention.sql` is applied to the live Supabase project. It creates a private SECURITY DEFINER cleanup function with an empty search path, revokes execution from browser and application roles, and schedules it hourly through Supabase Cron. The live cron job is active; the corresponding pgTAP tests insert synthetic expired/current rows inside a rollback transaction and verify the boundaries.

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
4. Complete the NDPA cross-border transfer assessment with qualified Nigerian privacy counsel and verify provider DPAs/subprocessor disclosures.
5. Resolve Vercel DPA coverage: the published DPA applies to Pro and Enterprise, while Tinlyt is on Hobby. Obtain written confirmation of applicable processor terms or move the personal-data intake endpoint to a suitable processor; keep the static frontend on Vercel if desired.
6. The latest frontend code is now deployed to the production aliases and the privacy notice is live. This gate is complete for the public frontend only; it does not prove the API/backend is deployed.
7. Add the missing Supabase server secret and dedicated Resend sending-only key directly to Vercel sensitive environment variables. Do not paste secrets into chat.
8. Run controlled end-to-end tests on a non-production preview or isolated test environment: Turnstile pass/fail, rate limits, duplicate submission, database persistence, both email flows, delivery-status update and deletion.
9. Verify the first scheduled hourly retention execution appears as successful in live Supabase Cron history. The job is active; the 06:33 UTC check preceded the next 07:00 UTC GMT schedule boundary.
10. Keep public workspace, account, investigation and evidence processing disabled until their separate privacy notice, terms and live data flows are documented.

## 9. Current state

The dedicated Supabase project is healthy and has no applicant rows. Live migration history is aligned with the repository through `20261103061953_early_access_retention`; the hourly Cron job is active, the cleanup function has passed manual execution, and the first scheduled run is pending confirmation in `cron.job_run_details`. Supabase advisors currently report only informational findings: RLS enabled with no policies on the two tables (intentional deny-by-default) and one unused index (no applicant workload exists yet). No applicant emails have been sent. No AWS application infrastructure has been provisioned. The frontend production deployment `dpl_BMSDcwrQn7EMNUbX8BRZtPfFEPBQ` is READY from commit `24f9a99f90b8d217b3b3d24ed72f105b8c9b64df`, with aliases `https://tinlyt.tinlance.com` and `https://tinlyt-web.vercel.app`; the subsequent main commit `4397d3f57b2eecae221be4a36bcf5010db311eea` changed only readiness documentation. The public `/privacy` page serves version `2026-11-03-v1`; `/api/twi/health` remains HTTP 404, so the TWI backend is not deployed. `EARLY_ACCESS_ENABLED=false` remains in all Vercel environments. The AWS identity remains root, the OIDC deployment role has no resource policies, no AWS Budget exists, and current credit balance is not exposed by the connected API.


## 10. Provider contract review update — 3 November 2026

The current public provider documents sharpen the outstanding contractual gate:

- **Vercel:** its DPA says it applies to customers on Pro and Enterprise plans. Tinlyt's connected project is on Hobby. Do not assume Vercel is contractually engaged as a processor under that DPA for early-access personal data. Obtain written confirmation of a suitable DPA/processor agreement or move the personal-data endpoint to another provider with applicable contractual terms. This does not require moving the static marketing frontend away from Vercel.
- **Supabase:** the current DPA is Version 1 dated 1 August 2026. It is effective with the service agreement, authorizes the published subprocessor list, and says customer-directed region data is stored and primarily processed in that region, subject to the DPA's stated exceptions and subprocessor processing. Confirm the account's agreement and subscribe to subprocessor changes.
- **Resend:** its DPA is dated 31 December 2025 and is effective through acceptance of the Terms of Service or execution. Its security documentation states data is stored in the United States; an EU sending region affects where email is sent from, not where data is stored. Confirm the account plan's retention and current subprocessors.
- **Cloudflare Turnstile:** its privacy addendum identifies client IP, TLS fingerprint, User-Agent, sitekey and origin as Signals; Cloudflare processes Signals as a processor to secure the site and as a controller for improving Turnstile detection. The public notice should continue to describe both purposes accurately.

Official provider references:
- Vercel DPA (last updated 17 March 2026): https://vercel.com/legal/dpa
- Supabase DPA (Version 1, 1 August 2026): https://supabase.com/legal/customer-resources/data-processing-addendum
- Resend DPA (last updated 31 December 2025): https://resend.com/legal/dpa
- Resend security/data-location details: https://resend.com/security
- Resend subprocessors (last updated 15 July 2026): https://resend.com/legal/subprocessors
- Cloudflare Turnstile Privacy Addendum: https://www.cloudflare.com/turnstile-privacy-policy/
- NDPC GAID 2025, especially Article 34 and Article 45/Schedule 5: https://ndpc.gov.ng/wp-content/uploads/2025/07/NDP-ACT-GAID-2025-MARCH-20TH.pdf

**Release decision:** these sources do not by themselves establish that Tinlance's actual contracts satisfy the NDPA. A qualified Nigerian privacy review must inspect the executed account agreements, processing purposes, destinations, subprocessor chains, transfer grounds and safeguards. The early-access form remains disabled until that review is signed off.
