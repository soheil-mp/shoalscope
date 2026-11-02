# 0008. Edge processing and NATS JetStream transport with a telemetry budget

- Status: Accepted
- Date: 2026-11-02

## Context and problem statement

Moored and autonomous echosounders often sit behind slow, intermittent or metered links
(cellular, satellite). Shipping raw pings is impossible there. Shoalscope's edge node
processes pings next to the instrument and sends compact products. Which transport, and how
is bandwidth controlled?

## Decision drivers

- Store-and-forward when the link is down, with bounded disk on a small arm64 device.
- At-least-once delivery with deduplication and replay for backfills.
- A hard byte budget per hour, with priorities when the budget is tight.
- Apache-2.0 or similar licences; a small footprint.

## Considered options

1. **NATS JetStream with a leaf-node server on the device** and a hub on the platform.
2. MQTT 5 (Mosquitto or EMQX) from the device, bridged into a log on the platform.
3. Apache Kafka 4 with devices as remote producers.
4. Eclipse Zenoh.

## Decision outcome

Chosen: **option 1**. The device's leaf node keeps a local JetStream stream, so publishes
succeed offline and flow to the hub when the link returns. Subjects are
`shoalscope.{deployment}.{kind}.v{n}`; payloads are Protobuf (ADR-0011); message IDs make
publishes idempotent within the deduplication window.

A **telemetry budget manager** (M12.5) sits in front of the publisher: a byte budget per hour,
priority classes (health and alarms, then NASC cells, tracks, single targets, echogram
thumbnails), adaptive decimation of low-priority classes, and a backlog policy for long
outages. The platform consumer acknowledges only after the Iceberg commit (M12.7).

### Consequences

- Good: store-and-forward and replay are built in; one small binary on the device.
- Good: the budget makes link costs explicit and testable.
- Bad: Kafka is more common in data-engineering job descriptions; ingestion is written against
  a small transport interface so an adapter could be added later.
- Neutral: MQTT is common on buoys, and NATS can accept MQTT clients if an instrument
  requires it.

## Confirmation

Toxiproxy-based tests cut, slow and cap the link and assert no loss or duplication after
recovery (M12.8).
