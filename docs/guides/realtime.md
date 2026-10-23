---
description: Produce events for the bundled real-time demos, watch scored results in the console, and connect the demos to a deployed model or agent.
---

# Process real-time events

The real-time processor consumes Kafka events, enriches each one with online
features, scores it with a model, an agent or a built-in rule, and publishes the
result. This guide shows you how to produce events, watch the results, and
connect the demos to your own model and agent.

The processor ships with three demos:

| Demo | Input topic | Output topic | What it does |
| --- | --- | --- | --- |
| `fraud` | `mlaiops.transactions` | `mlaiops.fraud.alerts` | Adds 5-minute transaction statistics, scores the transaction, and flags scores of `0.5` or more |
| `callcenter` | `mlaiops.callcenter.transcripts` | `mlaiops.callcenter.insights` | Summarizes sentiment and intent with an agent, or with keyword sentiment |
| `recommendations` | `mlaiops.user.activity` | `mlaiops.recs.results` | Looks up profile features and returns a catalog ranked for the user's plan |

## Before you begin

- **To watch results:** the `realtime` service for a normal user, or any of the
  `viewer`, `engineer`, `operator` or `admin` roles.
- **To produce events:** a terminal with `KAFKA_REST_URL` set, such as a Jupyter
  workbench terminal, or shell access to the Compose host.
- **To connect a model or agent:** a deployed model or agent, and access to
  `deploy/.env` on the Compose host.

## Produce demo events

Run these commands in a Jupyter or IDE terminal:

```bash
python -m realtime.produce --demo fraud --count 5
python -m realtime.produce --demo callcenter --count 2
python -m realtime.produce --demo recommendations --count 2
```

On the Compose host, run the same module in the workbench container:

```bash
docker compose -f deploy/compose.yaml exec jupyter \
  python -m realtime.produce --demo fraud --count 5
```

**Verify:** the command finishes without errors. The **Real-time** page lists
the same commands under **Produce demo events**.

## Watch the results

=== "Console"

    Open **Real-time**. Each demo card shows the events processed, the average
    latency and, for fraud, the number of flagged events. The cards update live.

=== "API"

    ```bash
    curl -s -H "Authorization: Bearer $MLAIOPS_TOKEN" \
      "$MLAIOPS_URL/api/v1/realtime" | python -m json.tool
    ```

    ```json
    {"demos": {"fraud": {"events": 12, "avg_latency_ms": 1.82, "flagged": 4,
                         "updated_at": "..."}}}
    ```

For each event, the processor:

1. Reads the input topic through the Kafka REST proxy.
2. Adds online features from the feature gateway.
3. Scores the event with the configured model or agent, or with a built-in rule
   when none is configured.
4. Publishes the result to the output topic and records the latency.
5. Reports its statistics to Kionga for the console.

**Verify:** the event count on the demo card grows by the number of events you
produced.

## Connect the demos to a model and an agent

The demos run out of the box with built-in rules. To score with your own
components:

1. Choose the components:
    - **Fraud:** a deployed model whose MLflow `/invocations` route accepts
      `{"inputs": [[amount, txn_count_5m, txn_amount_5m]]}` and returns the
      score in `predictions[0]`.
    - **Call center:** a deployed agent. The processor sends each transcript to
      the agent with an instruction to summarize sentiment and intent.
2. Add them to `deploy/.env`:

    ```bash
    FRAUD_MODEL_ENDPOINT=http://mlaiops-serve-fraud-scorer:5001   # the model's endpoint_url
    CALLCENTER_AGENT_ID=agt-...                                   # the agent's ID
    ```

3. Recreate the processor:

    ```bash
    docker compose -f deploy/compose.yaml up -d realtime-processor
    ```

**Verify:** produce events again. The results on the output topics now carry
`"source": "model"` for fraud and `"source": "agent"` for the call center,
instead of `"source": "rule"`.

## Troubleshooting

- **The cards stay empty:** check that the `realtime-processor` service is
  running, then produce events again. See
  [Troubleshooting](../operations/troubleshooting.md).
- **Short pauses during load:** while Kafka reassigns its consumer group, the
  processor can time out on a read. It recreates its consumer and continues on
  its own, and statistics resume automatically.

## Next steps

- [Deploy a model](models-serving.md) for fraud scoring.
- [Build and deploy an agent](agents.md) for transcript analysis.
- [Use the built-in feature store](features.md).
