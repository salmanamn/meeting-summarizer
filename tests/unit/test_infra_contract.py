"""Terraform (Azure) and the code and the local stand-ins must describe the same contracts (D43).

Locally the Event Grid stub plays the manifest subscription and scripts/init_stores.py creates the containers; on
Azure Terraform creates all of it. These tests read the Terraform as text (no terraform binary needed) and fail
when one side changes without the other.
"""

import json
import re
from pathlib import Path

import pytest

from meeting.manifest import MANIFEST_NAME
from meeting.settings import load

ROOT = Path(__file__).resolve().parents[2]
MODULES = ROOT / "infra" / "modules"
STACK_MAIN = MODULES / "stack" / "main.tf"
STACK_RBAC = MODULES / "stack" / "rbac.tf"
STACK_VARIABLES = MODULES / "stack" / "variables.tf"
EVENTS_MAIN = MODULES / "blobevents" / "main.tf"
FUNCTION_APP = ROOT / "src" / "function_app.py"

# Settings the stack sets that src/meeting/settings.py doesn't read, and who does read them.
HOST_SETTINGS = {  # the Functions host (the trigger's identity-based connection) and DefaultAzureCredential
    "AZURE_CLIENT_ID",
    "RecordingsStorage__queueServiceUri",
    "RecordingsStorage__credential",
    "RecordingsStorage__clientId",
}


def block(text: str, kind: str, name: str) -> str:
    """Body of a top-level `<kind> "<name>" {` block (or `resource "<type>" "<name>" {`)."""
    found = re.search(rf'^{kind} "{name}" \{{\n(.*?)^\}}', text, re.DOTALL | re.MULTILINE)
    assert found, f'{kind} "{name}" not found'
    return found.group(1)


def argument(body: str, name: str) -> str:
    value = re.search(rf"^\s*{name}\s*=\s*(.+)$", body, re.MULTILINE)
    assert value, f"argument {name} not found"
    return value.group(1).strip()


def tf_default(variable: str) -> str:
    body = block(STACK_VARIABLES.read_text(), "variable", variable)
    return argument(body, "default").strip('"')


def stack_locals() -> dict[str, str]:
    """name = "string" assignments in the stack's locals blocks."""
    return dict(re.findall(r'^\s+(\w+)\s*=\s*"([^"$]*)"', STACK_MAIN.read_text(), re.MULTILINE))


def stack_settings() -> set[str]:
    """App setting names the stack sets: the keys of app_settings, openai_settings and speech_settings."""
    text = STACK_MAIN.read_text()
    start = text.index("  openai_settings = ")
    end = text.index("  # What the laptop scripts need")
    return set(re.findall(r"^\s{4,6}(\w+)\s+=", text[start:end], re.MULTILINE))


@pytest.fixture(scope="module")
def stub() -> dict:
    config = json.loads((ROOT / "emulators" / "eventgrid" / "subscriptions.json").read_text())
    (subscription,) = config["subscriptions"]
    return subscription


def test_the_manifest_subscription_filters_as_the_local_stub(stub):
    names = stack_locals()
    events = EVENTS_MAIN.read_text()
    begins = argument(events, "subject_begins_with").strip('"')
    ends = argument(events, "subject_ends_with").strip('"')
    assert begins.replace("${var.incoming_container_name}", names["incoming_container"]) == stub["subjectBeginsWith"]
    assert ends.replace("${var.manifest_name}", names["manifest_name"]) == stub["subjectEndsWith"]
    assert argument(events, "included_event_types") == json.dumps(stub["includedEventTypes"])
    assert int(tf_default("event_max_delivery_attempts")) == stub["maxDeliveryAttempts"]
    assert names["manifest_name"] == MANIFEST_NAME


def test_the_webhook_is_the_blobs_extension_of_the_triggered_function(stub):
    """The webhook names the function by its Python name; the stub calls the same path locally (D15, D40)."""
    source = FUNCTION_APP.read_text()
    trigger = re.search(r"@app\.blob_trigger\((.*?)\)\n\s*def (\w+)\(", source, re.DOTALL)
    assert trigger, "no blob-triggered function in function_app.py"
    assert tf_default("trigger_function_name") == trigger.group(2)
    assert stub["endpoint"].endswith(f"/runtime/webhooks/blobs?functionName=Host.Functions.{trigger.group(2)}")
    webhook = argument(block(STACK_MAIN.read_text(), "module", "blobevents"), "webhook_url")
    assert "/runtime/webhooks/blobs?functionName=Host.Functions.${var.trigger_function_name}&code=" in webhook
    assert "blobs_extension_key" in webhook
    # The trigger's connection and path are the settings and containers the stack creates.
    assert 'connection="RecordingsStorage"' in trigger.group(1)
    assert f'path="{stack_locals()["incoming_container"]}/{{meeting_id}}/{MANIFEST_NAME}"' in trigger.group(1)
    assert "source=func.BlobSource.EVENT_GRID" in trigger.group(1)


def test_attempts_agree_with_the_host():
    host = json.loads((ROOT / "src" / "host.json").read_text())
    assert int(tf_default("job_max_attempts")) == host["extensions"]["blobs"]["poisonBlobThreshold"]
    assert int(tf_default("job_max_attempts")) == load({}).job_max_attempts


def test_names_are_the_code_defaults():
    """Containers, database and collection: what Terraform creates is what the code uses when nothing is set."""
    defaults, names = load({}), stack_locals()
    assert (names["incoming_container"], names["transcripts_container"]) == (
        defaults.incoming_container,
        defaults.transcripts_container,
    )
    cosmos = block(STACK_MAIN.read_text(), "module", "cosmos")
    assert argument(cosmos, "database_name").strip('"') == defaults.cosmos_database
    assert argument(cosmos, "jobs_container_name").strip('"') == defaults.jobs_container
    assert 'partition_key_paths = ["/id"]' in (MODULES / "cosmos" / "main.tf").read_text()


def test_every_app_setting_is_read_by_someone():
    """A setting name with a typo would be silently ignored on Azure and the code would use its laptop default."""
    read = set(re.findall(r'env\.get\("(\w+)"', (ROOT / "src" / "meeting" / "settings.py").read_text()))
    assert {"RecordingsStorage__blobServiceUri", "COSMOS_ENDPOINT", "JOB_MAX_ATTEMPTS"} <= read  # the regex works
    assert stack_settings() - read - HOST_SETTINGS == set()  # M6 read the last reserved names (D44, D46)


def test_azure_never_falls_back_to_a_laptop_connection():
    """On Azure the recordings and Cosmos are reached by identity: the URI setting is there, a key never is."""
    names = stack_settings()
    assert {"RecordingsStorage__blobServiceUri", "COSMOS_ENDPOINT", "OPENAI_BASE_URL", "CHAT_MODEL"} <= names
    assert names.isdisjoint({"RecordingsStorage", "COSMOS_KEY", "OPENAI_API_KEY", "AzureWebJobsStorage"})


def test_speech_reads_recordings_without_a_cycle():
    """D3, D41: the recordings account trusts the Speech account, and Speech may call only the recordings' blob
    host, built from the account's name (taking it from the account resource would be a dependency cycle)."""
    stack = STACK_MAIN.read_text()
    recordings = block(stack, "module", "recordings")
    assert argument(recordings, "name") == "local.recordings_account"
    assert argument(recordings, "resource_instance_ids") == "var.components.speech ? [module.speech[0].account_id] : []"
    assert argument(block(stack, "module", "speech"), "allowed_fqdns") == "[local.recordings_blob_host]"
    assert argument(stack, "recordings_blob_host") == '"${local.recordings_account}.blob.${var.storage_suffix}"'
    rbac = block(STACK_RBAC.read_text(), 'resource "azurerm_role_assignment"', "speech_reads_incoming")
    assert argument(rbac, "scope") == "module.recordings.container_ids[local.incoming_container]"
    assert argument(rbac, "role_definition_id").endswith('${local.role_ids.storage_blob_data_reader}"')


def test_event_grid_dead_letters_have_their_own_storage_account():
    """Project 3 D25: the topic identity's role must be account-scoped (D24), so the account holds only
    dead-letters, never the host's package or the recordings."""
    stack = STACK_MAIN.read_text()
    events = block(stack, "module", "blobevents")
    assert argument(events, "deadletter_storage_account_id") == "module.deadletter[0].account_id"
    assert argument(block(stack, "module", "deadletter"), "containers") == "[local.deadletter_container]"
    assert argument(block(stack, "module", "storage"), "containers") == "[local.deployment_container]"
    text = EVENTS_MAIN.read_text()
    role = block(text, 'resource "azurerm_role_assignment"', "topic_deadletter")
    assert argument(role, "scope") == "var.deadletter_storage_account_id"
    assert re.search(r"^\s*storage_account_id\s*=\s*var\.deadletter_storage_account_id$", text, re.MULTILINE)


def stack_literal(name: str) -> str:
    """The value of `NAME = "literal"` in the stack's settings maps."""
    value = re.search(rf'^\s+{name}\s+=\s+"([^"]*)"', STACK_MAIN.read_text(), re.MULTILINE)
    assert value, f"{name} is not a literal in the stack"
    return value.group(1)


def test_the_stack_s_settings_select_speech_and_entra():
    """D44, D46: on Azure the code must pick Speech batch transcription (no Whisper model is deployed) and an Entra
    token for Azure OpenAI (local auth is off). SPEECH_ENDPOINT's value is unknown until apply: any URL stands in."""
    names = stack_settings()
    assert {"SPEECH_ENDPOINT", "SPEECH_REGION", "OPENAI_AUTH"} <= names
    assert "STT_ENGINE" not in names  # the endpoint alone decides; a stray STT_ENGINE=whisper would break Azure
    azure = load(
        {"SPEECH_ENDPOINT": "https://spch.cognitiveservices.azure.com/", "OPENAI_AUTH": stack_literal("OPENAI_AUTH")}
    )
    assert (azure.stt_engine, azure.openai_auth) == ("speech", "entra")


def test_one_delivery_waits_for_speech_within_the_function_timeout():
    """D45: a delivery polls at most SPEECH_WAIT_SECONDS, then transcribes nothing more and leaves the rest to the
    next delivery; the summary still needs time after it, inside host.json's functionTimeout."""
    host = json.loads((ROOT / "src" / "host.json").read_text())
    hours, minutes, seconds = (int(x) for x in host["functionTimeout"].split(":"))
    timeout = hours * 3600 + minutes * 60 + seconds
    assert load({}).speech_wait_seconds + 600 <= timeout  # ten minutes left for the summary and the writes


def test_speech_reads_the_blob_host_the_app_writes_to():
    """The job hands Speech a URL on RecordingsStorage__blobServiceUri; the only host Speech may call is the
    recordings account's blob host (D41). Both come from the same account."""
    stack = STACK_MAIN.read_text()
    assert argument(stack, "RecordingsStorage__blobServiceUri") == "module.recordings.primary_blob_endpoint"
    assert argument(block(stack, "module", "recordings"), "name") == "local.recordings_account"


def settings_block(start: str, end: str) -> set[str]:
    """Setting names assigned between two markers of the stack's main.tf."""
    text = STACK_MAIN.read_text()
    body = text[text.index(start) : text.index(end, text.index(start))]
    return set(re.findall(r"^\s+(\w+)\s+=", body, re.MULTILINE)) - {"client_settings", "openai_settings"}


def laptop_settings() -> set[str]:
    """The names in client_settings, what scripts/azure_env.sh exports on the laptop (D49)."""
    text = STACK_MAIN.read_text()
    start = text.index("  client_settings = merge(")
    merged = text[start : text.index("\n  )\n", start)]
    names = settings_block("  client_settings = merge(", "\n  )\n")
    maps = {  # the stack's setting maps a merge can take in, each up to the marker after it
        "openai_settings": ("  openai_settings = ", "  speech_settings = "),
        "speech_settings": ("  speech_settings = ", "  # Endpoints and names only."),
    }
    for local_name, (begin, end) in maps.items():
        if f"local.{local_name}" in merged:
            names |= settings_block(begin, end) - {"speech_settings"}
    assert "var.extra_app_settings" not in merged and "local.app_settings," not in merged
    return names


def test_laptop_settings_never_select_speech_and_never_carry_a_key():
    """D49: the laptop summarises the Whisper transcript with the stack's model, so its settings must reach the
    recordings, Cosmos and Azure OpenAI by Entra ID and leave the transcriber on Whisper (D44: SPEECH_ENDPOINT would
    switch it); the operator signs in as themself, so no AZURE_CLIENT_ID either."""
    names = laptop_settings()
    assert {"RecordingsStorage__blobServiceUri", "TRANSCRIPTS_CONTAINER", "COSMOS_ENDPOINT", "OPENAI_AUTH"} <= names
    assert not {n for n in names if n.startswith(("SPEECH_", "STT_"))}
    assert names.isdisjoint({"AZURE_CLIENT_ID", "RecordingsStorage", "COSMOS_KEY", "OPENAI_API_KEY"})
    read = set(re.findall(r'env\.get\("(\w+)"', (ROOT / "src" / "meeting" / "settings.py").read_text()))
    assert names <= read
    laptop = load(
        {
            **{n: "https://x.example/" for n in names},
            "OPENAI_AUTH": stack_literal("OPENAI_AUTH"),
            "SUMMARY_MAX_TOKENS": "6000",
        }
    )
    assert (laptop.stt_engine, laptop.openai_auth, laptop.cosmos_key) == ("whisper", "entra", "")


def test_the_operator_reads_transcripts_and_uploads_recordings_on_one_container_each():
    """D49: the operator's three roles, each on the one resource it is for (the plan only knows their names)."""
    rbac = STACK_RBAC.read_text()
    expected = {
        "operator_upload": (
            "module.recordings.container_ids[local.incoming_container]",
            "storage_blob_data_contributor",
        ),
        "operator_transcripts": (
            "module.recordings.container_ids[local.transcripts_container]",
            "storage_blob_data_reader",
        ),
        "operator_openai": ("module.openai[0].account_id", "cognitive_openai_user"),
    }
    for name, (scope, role) in expected.items():
        body = block(rbac, 'resource "azurerm_role_assignment"', name)
        assert argument(body, "scope") == scope, name
        assert argument(body, "role_definition_id").endswith(f'${{local.role_ids.{role}}}"'), name
        assert argument(body, "principal_id") == "var.operator_object_id", name
        assert argument(body, "principal_type") == '"User"', name
    operator = set(re.findall(r'^resource "azurerm_role_assignment" "(operator\w*)"', rbac, re.MULTILINE))
    assert operator == set(expected)
