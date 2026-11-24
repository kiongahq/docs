---
icon: material/lightning-bolt-outline
description: Produce events for the bundled real-time demos, watch scored results in the console, and connect the demos to a deployed model or agent.
---

# Process real-time events

Produce events for the bundled real-time demos, watch the scored results, and
connect the demos to your own model and agent. The real-time processor consumes
Kafka events, enriches each one with online features, scores it with a model,
an agent or a built-in rule, and publishes the result.

The processor ships with three demos:

| Demo | Input topic | Output topic | What it does |
| --- | --- | --- | --- |
| `fraud` | `kionga.transactions` | `kionga.fraud.alerts` | Adds 5-minute transaction statistics, scores the transaction, and flags scores of `0.5` or more |
| `callcenter` | `kionga.callcenter.transcripts` | `kionga.callcenter.insights` | Summarizes sentiment and intent with an agent, or with keyword sentiment |
| `recommendations` | `kionga.user.activity` | `kionga.recs.results` | Looks up profile features and returns a catalog ranked for the user's plan |

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

## Watch the results

1. Read the statistics:

    === "Console"

        Open **Real-time**. Each demo card shows `events`, `avg_latency_ms` and,
        for fraud, `flagged`, with the time of the last update. Reload the page to
        read the latest figures.

    === "API"

        ```bash
        curl -s -H "Authorization: Bearer $KIONGA_TOKEN" \
          "$KIONGA_URL/api/v1/realtime" | python -m json.tool
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
    FRAUD_MODEL_ENDPOINT=http://kionga-serve-fraud-scorer:5001   # the model's endpoint_url
    CALLCENTER_AGENT_ID=agt-...                                   # the agent's ID
    ```

3. Recreate the processor:

    ```bash
    docker compose -f deploy/compose.yaml up -d realtime-processor
    ```

## Verify

1. **Produce:** each `python -m realtime.produce` command prints `produced <n>
   event(s) to <topic>`, for example `produced 5 event(s) to kionga.transactions`.
2. **Process:** `GET /api/v1/realtime` returns the demo under `demos`, and its
   `events` count grows by the number of events you produced. On the **Real-time**
   page, the card replaces `No events processed yet.` with the figures.
3. **Consume:** the processor log shows `realtime processor consuming
   ['kionga.transactions', 'kionga.callcenter.transcripts', 'kionga.user.activity']`.
   Read it with `docker compose -f deploy/compose.yaml logs realtime-processor`.
4. **Connect:** after you recreate the processor and produce events again, the
   results on the output topics carry `"source": "model"` for fraud and
   `"source": "agent"` for the call center, instead of `"source": "rule"`.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| The **Real-time** page shows `No events processed yet.` | The processor is not running, or it has not read your events. | Check that the `realtime-processor` service is running, then produce events again. See [Troubleshooting](../operations/troubleshooting.md). |
| `python -m realtime.produce` fails with an `httpx` error | `KAFKA_REST_URL` is unset, so the producer uses `http://localhost:8082`, or the Kafka REST proxy is down. | Run the command where `KAFKA_REST_URL` is set, such as a Jupyter workbench terminal, and check the Kafka REST proxy. |
| The processor log shows `kafka batch failed (<error>); recreating consumer` once | While Kafka reassigns its consumer group, the processor can time out on a read. | Wait. The processor recreates its consumer, fetches the uncommitted records again and continues, and statistics resume. |
| The same `kafka batch failed (<error>)` line repeats | The model endpoint or the agent returns an error for an event, so the processor does not commit that batch and fetches it again. | Correct `FRAUD_MODEL_ENDPOINT` or `CALLCENTER_AGENT_ID`, or clear the variable to use the built-in rule, and recreate the processor. |
| Results still carry `"source": "rule"` | The variable is empty, or you did not recreate the processor after you changed `deploy/.env`. | Set `FRAUD_MODEL_ENDPOINT` or `CALLCENTER_AGENT_ID` in `deploy/.env`, and run `docker compose -f deploy/compose.yaml up -d realtime-processor`. |

## Related pages

- [Deploy a model](models-serving.md) for fraud scoring.
- [Build and deploy an agent](agents.md) for transcript analysis.
- [Use the built-in feature store](features.md).
