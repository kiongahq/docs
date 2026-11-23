---
icon: material/cube-scan
description: Search the Hugging Face Hub from Kionga, register a pinned model revision in a project, connect a personal account for private models, and download the weights in your workspace.
---

# Import a Hugging Face model

Find a trained model on the Hugging Face Hub, register a pinned revision in a
Kionga project, and download its weights in your workspace. Use Hub models as the
starting point for notebooks, training pipelines or agent tools.

Registering a model records where it comes from. It does not download the
weights or deploy an inference service.

## Before you begin

- **To search the Hub:** any signed-in user who can see **Models**. Public
  search works without a Hugging Face account.
- **To register a model:** the `models` service for a normal user, or the
  `engineer`, `operator` or `admin` role, and access to the destination project.
  Viewers can search but cannot register.
- **For private or gated models:** a Hugging Face account with access to the
  repository, and an administrator who has set the credential key on the gateway
  (see [Set the credential key](#set-the-credential-key)).

## Connect your Hugging Face account

Connect your account only when you need private or gated repositories.

1. On Hugging Face, create a read or fine-grained
   [access token](https://huggingface.co/settings/tokens) that grants only the
   repositories you need. The token starts with `hf_`.
2. In the Kionga console, open **Settings > Hugging Face account**.
3. Paste the token into **Access token** and click **Connect account**.

Kionga checks the token with the Hub and encrypts it for your account alone. It
never shows the token again, never stores it in your browser, and never puts it
in generated code or audit events. Kionga sends it only to
`https://huggingface.co`.

To remove the connection, click **Disconnect**. It removes the token from Kionga. It does not revoke the token on
Hugging Face or sign out any workspace. If a token leaks, revoke it on Hugging
Face.

## Find and register a model

1. Open **Models**. In the **Hugging Face discovery** panel, enter a
   **Repository or search phrase**, optionally choose a **Task**, and click
   **Search models**.
2. Review the model card, which the **Model card** link opens: license, required
   libraries, memory needs, intended use and limitations. A high download count
   is not a quality guarantee.
3. Click **Register in project** in the model's row. In the **Register Hub
   model** dialog, choose the **Project** and a **Revision**: a branch, tag or
   commit (default `main`).
4. Click **Register model**.

Kionga resolves the revision to its 40-character commit and stores an artifact
URI such as `hf://organization/model@<commit>`, with the repository, task,
library and license when the Hub provides them. The model starts in the
`candidate` stage with the quality gate `needs_evaluation`. Registering the same
repository and commit in the same project again is rejected; other projects can
register it independently.

You can do the same from the SDK:

```python
results = client.search_huggingface_models("sentence-transformers",
                                            task="sentence-similarity")
model = client.import_huggingface_model(
    "prj-123", "sentence-transformers/all-MiniLM-L6-v2", revision="main")
print(model.artifact_uri)
```

## Download the weights in a workspace

1. On the registered model, click **Download / notebook**. In the **Download
   model weights** dialog, click **Copy code**, or click **Download notebook**,
   then **Open JupyterLab**.
2. For private or gated models, sign in to the Hub inside that workspace. Kionga
   never copies your connected account into workspaces:

    ```python
    from kionga.huggingface import connect
    connect()  # interactive Hub login; never paste a token into saved code
    ```

3. Run the download:

    ```python
    from kionga import KiongaClient
    from kionga.huggingface import download_model

    repo = "sentence-transformers/all-MiniLM-L6-v2"
    with KiongaClient() as platform:
        model = next(m for m in platform.list_models()
                     if m.artifact_uri.startswith(f"hf://{repo}@"))
        path = download_model(model, cache_dir="/workspace/huggingface-cache")
        print(path)
    ```

    `download_model` takes the registered model, so it always downloads the
    pinned commit.

`download_model` uses the Hub's own `snapshot_download` with the registered
commit and returns the snapshot folder. Interrupted downloads can resume and
reuse cached files. `allow_patterns` limits which files it pulls (leaving out
required config, vocabulary or weight files can make the model unusable), and
`local_files_only=True` reuses the cache offline. The helper never runs
repository code and never enables `trust_remote_code`.

Downloads run in your workspace or job, within its disk and resource limits, not
on the gateway. Make sure you have room for large checkpoints first.

The JupyterLab workbench already includes the SDK with Hugging Face support. For
the browser IDE or your own machine, install it from your `sdk-python` checkout:

```bash
python -m venv .venv
source .venv/bin/activate
pip install './sdk-python[huggingface]'
```

Outside Kionga, export `KIONGA_URL` and a personal API key as `KIONGA_TOKEN`.
That key is for Kionga, not Hugging Face. In pipeline jobs, provide `HF_TOKEN`
through your deployment's secret manager, never as a parameter or in a committed
file.

## Evaluate and deploy

An imported Hub reference cannot be promoted to production or deployed through the
default serving path, because its gate is `needs_evaluation`.

1. Install the model's runtime library in your project environment, for example
   `transformers`, `sentence-transformers` or `diffusers`, and load the model from
   the snapshot folder. Assess any model that needs custom code separately.
2. Evaluate it on your own data, or fine-tune it in a [pipeline](pipelines.md).
3. Register the evaluated artifact with its metrics and a `serving_image` that can
   load it, and keep the source commit in your experiment metadata. See
   [Register, deploy and serve models](models-serving.md).

Large generative models can need a dedicated GPU inference server. Embeddings
and model calls inside agents are part of your project code.

## Set the credential key

An administrator sets the key that encrypts connected Hugging Face tokens.

1. Generate a base64-encoded 32-byte key:

    ```bash
    openssl rand -base64 32
    ```

2. Set it as `KIONGA_CREDENTIAL_KEY` on the gateway: in `deploy/.env` (never
   committed) for Compose, or from a Kubernetes Secret.
3. Recreate the gateway.

Use the same key on every gateway replica, keep it stable across restarts, and
back it up separately from the database. If you change it, users must reconnect
their accounts. Without the key, account connections are disabled and public
search still works.

## Verify

1. **Credential key:** **Settings > Hugging Face account** shows `Public
   discovery is available without an account. Connect to access private or gated
   models.` instead of `An administrator must configure KIONGA_CREDENTIAL_KEY to
   enable encrypted account connections.`, and **Connect account** is enabled.
   `GET /api/v1/settings/huggingface` returns `"configured": true`.
2. **Connect:** the **Hugging Face account** panel shows `Connected as <your Hub
   username>`, and the API returns `"connected": true` with your `username`.
3. **Register:** the model under **Models** has the stage `candidate` and the
   quality gate `needs_evaluation`, and a **Download / notebook** button in its
   row. Its `artifact_uri` has the form `hf://<repository>@<commit>`, with a
   40-character commit.
4. **Download:** the printed folder contains the model's config and weight files.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `400 invalid_token`, `Enter a Hugging Face read or fine-grained token` | The token does not start with `hf_`, or it is longer than 1,024 characters. | Paste a read or fine-grained token from your Hugging Face settings. |
| `503 not_configured`, `Account connections require KIONGA_CREDENTIAL_KEY (base64-encoded 32-byte key) on the gateway` | The gateway has no credential key. | Set the key as described in [Set the credential key](#set-the-credential-key). Public search works without it. |
| `Hugging Face denied access. Check your token and accept any gated model terms on huggingface.co` | The Hub answered `401` or `403`: the model is gated or private, or the token cannot read it. | Accept the model's terms on its Hub page, then use a token from the approved account. Registering metadata does not prove you can download the weights. |
| `Model or revision not found, or your account cannot access it` | The Hub answered `404`. | Check the repository ID, the revision, and your account's access. |
| `Hugging Face rate limit reached. Please retry later` | The Hub answered `429`. | Wait and retry. |
| `Hugging Face could not be reached. Please retry` | The gateway cannot reach the Hub. | Retry, and check the gateway's network access to `huggingface.co`. |
| `Account credential cannot be decrypted; reconnect your account` | The credential key changed since you connected. | Reconnect your account. |
| `409 conflict` when you register | The project already holds this repository at this commit. | Use the existing model, or register it in another project. |
| `Search must be 200 characters or fewer` | The search text is too long. | Shorten the search. |
| `ValueError: Expected a commit-pinned hf:// repository URI from the registry` | The model passed to `download_model` was not registered from the Hub. | Pass a model registered with **Register model** or `import_huggingface_model`. |
| A download fails | The workspace has no network access to the Hub, no free disk, no Hub login, or no access to the model. | Check each one. The Hub client in your notebook or terminal reports the details. |

## Related pages

- [Register, deploy and serve models](models-serving.md).
- [Build an agent](agents.md) that uses the model.
- [Define and run pipelines](pipelines.md) to fine-tune a model.
- Hugging Face documentation on
  [downloads](https://huggingface.co/docs/huggingface_hub/guides/download),
  [access tokens](https://huggingface.co/docs/hub/security-tokens) and
  [gated models](https://huggingface.co/docs/hub/models-gated).
