# 0013. Privacy allowlist for source metadata, and attribution by construction

- Status: Accepted
- Date: 2026-11-02

## Context and problem statement

Shoalscope's sources are public environmental data, but their metadata is not always free of
personal data. The NOAA cruise metadata JSON lists scientists' names, e-mail addresses, phone
numbers and street addresses. OOI data has no open-data licence and requires citation in a set
format. How does Shoalscope handle both?

## Decision drivers

- No personal data stored, logged or published anywhere.
- Every product must carry the citation its sources require.
- Rules must be automatic, not reliant on reviewers noticing.

## Considered options

1. **Allowlists**: connectors keep only named, non-personal fields; everything else is dropped
   and counted. Attribution is generated from the source registry.
2. Denylists of known personal fields.
3. Store everything and filter at publication.

## Decision outcome

Chosen: **option 1**.

- Each connector declares an allowlist of metadata fields (cruise ID, dates, platform,
  instrument, calibration state; transducer and pulse settings from raw `XML0`). Unknown
  fields are dropped and counted in an ops metric, never logged by value (M3.6, M10.6).
- A test feeds a synthetic metadata document full of personal-looking fields and asserts none
  of them reaches storage, logs or traces.
- The source registry (M10.1) holds each source's terms and citation template; every product,
  export and API response built from a source carries its citation (M16.7).
- Raw OOI files are never redistributed; only derived products are stored and published.

### Consequences

- Good: new metadata fields cannot leak by default.
- Bad: useful new fields need an explicit allowlist change, reviewed like a schema change.
