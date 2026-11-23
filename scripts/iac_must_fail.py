#!/usr/bin/env python3
"""IaC must fail: break one property of a real plan at a time and require the Conftest gate to reject it.

The input is `terraform show -json` of the full-stack plan (infra/envs/local, -var full_stack=true, D43). The
unmodified plan must pass; every mutation must produce at least one `deny`. A mutation whose target resource
is missing from the plan is STALE (update it together with the Terraform). Stdlib only; needs conftest on PATH.

Usage: python3 scripts/iac_must_fail.py <plan.json> [--policy infra/policy] [--list]
"""

import argparse
import copy
import json
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_OTHER = "/subscriptions/x/resourceGroups/rg-x/providers/Microsoft.OperationalInsights/workspaces/law-x"
OWNER = "8e3af657-a8ff-443c-a75c-2fe8c4bcb635"
DEADLETTER_CONTAINER = "eventgrid-deadletter"
COSMOS_CONTRIBUTOR = "00000000-0000-0000-0000-000000000002"


@dataclass(frozen=True)
class Mutation:
    name: str
    type: str  # resource type to change (the first instance in the plan)
    apply: Callable[[dict], None]  # mutates rc["change"]["after"] (or the plan, for type "<plan>")


def setter(key: str, value) -> Callable[[dict], None]:
    def run(after: dict) -> None:
        after[key] = value

    return run


def find(plan: dict, what: Callable[[dict], bool], label: str) -> dict:
    for rc in plan["resource_changes"]:
        if rc["change"]["after"] is not None and what(rc):
            return rc
    raise LookupError(label)


def speech(plan: dict) -> dict:
    return find(
        plan,
        lambda rc: rc["type"] == "azurerm_cognitive_account" and rc["change"]["after"]["kind"] == "SpeechServices",
        "the Speech account",
    )


def module_of_container(plan: dict, name: str) -> str:
    rc = find(plan, lambda r: r["type"] == "azurerm_storage_container" and r["change"]["after"]["name"] == name, name)
    return rc["module_address"]


def drop_cosmos_diagnostics(plan: dict) -> None:
    before = len(plan["resource_changes"])
    plan["resource_changes"] = [
        rc
        for rc in plan["resource_changes"]
        if not (rc["type"] == "azurerm_monitor_diagnostic_setting" and ".module.cosmos" in rc["address"])
    ]
    if len(plan["resource_changes"]) == before:
        raise LookupError("cosmos diagnostic setting")


def add_setting(name: str) -> Callable[[dict], None]:
    def run(plan: dict) -> None:
        plan["output_changes"]["summary"]["after"]["app_setting_names"].append(name)

    return run


def drop_setting(name: str) -> Callable[[dict], None]:
    def run(plan: dict) -> None:
        names = plan["output_changes"]["summary"]["after"]["app_setting_names"]
        if name not in names:
            raise LookupError(f"app setting {name}")
        names.remove(name)

    return run


def openai_subdomain_removed(plan: dict) -> None:
    """As if custom_subdomain_name were deleted from the module: null and no longer 'known after apply'."""
    rc = find(plan, lambda r: r["type"] == "azurerm_cognitive_account", "azurerm_cognitive_account")
    rc["change"]["after"]["custom_subdomain_name"] = None
    rc["change"].get("after_unknown", {}).pop("custom_subdomain_name", None)


def speech_without_system_identity(plan: dict) -> None:
    speech(plan)["change"]["after"]["identity"] = [{"type": "UserAssigned"}]


def speech_fqdns(value: list) -> Callable[[dict], None]:
    """As if the module set this allowlist: a known list, no longer 'known after apply'."""

    def run(plan: dict) -> None:
        rc = speech(plan)
        rc["change"]["after"]["fqdns"] = value
        rc["change"].get("after_unknown", {}).pop("fqdns", None)

    return run


def deadletter_into_host_storage(plan: dict) -> None:
    """As if the dead-letter container were created in the Function App's host storage again (Project 3 D25)."""
    dead = find(
        plan,
        lambda r: r["type"] == "azurerm_storage_container" and r["change"]["after"]["name"] == DEADLETTER_CONTAINER,
        "dead-letter container",
    )
    dead["module_address"] = module_of_container(plan, "app-package")


def package_into_recordings(plan: dict) -> None:
    """As if the deployment package container moved into the recordings account (D38)."""
    package = find(
        plan,
        lambda r: r["type"] == "azurerm_storage_container" and r["change"]["after"]["name"] == "app-package",
        "app-package container",
    )
    package["module_address"] = module_of_container(plan, "incoming")


def host_trusts_resource_instance(plan: dict) -> None:
    host = module_of_container(plan, "app-package")
    rc = find(
        plan,
        lambda r: r["type"] == "azurerm_storage_account" and r.get("module_address") == host,
        "host storage account",
    )
    rc["change"]["after"]["network_rules"][0]["private_link_access"] = [{"endpoint_resource_id": "/x"}]


def trusted_services_bypass(after: dict) -> None:
    after["network_rules"][0]["bypass"] = ["AzureServices"]


def deadletter_to_another_container(after: dict) -> None:
    destinations = after.get("storage_blob_dead_letter_destination") or []
    if not destinations:
        raise LookupError("storage_blob_dead_letter_destination")
    destinations[0]["storage_blob_container_name"] = "transcripts"


def any_blob(after: dict) -> None:
    after["subject_filter"][0]["subject_ends_with"] = ""


def unbounded_retries(after: dict) -> None:
    after["retry_policy"][0]["max_delivery_attempts"] = 30


def provisioned_sku(after: dict) -> None:
    after["sku"][0]["name"] = "GlobalProvisionedManaged"


def role_to_owner(after: dict) -> None:
    after["role_definition_id"] = after["role_definition_id"].rsplit("/", 1)[0] + "/" + OWNER


def operator_writes_jobs(plan: dict) -> None:
    rc = find(
        plan,
        lambda r: r["type"] == "azurerm_cosmosdb_sql_role_assignment" and r["name"] == "operator",
        "operator's Cosmos role",
    )
    after = rc["change"]["after"]
    after["role_definition_id"] = f"/sqlRoleDefinitions/{COSMOS_CONTRIBUTOR}"


MUTATIONS = [
    Mutation("storage-shared-key", "azurerm_storage_account", setter("shared_access_key_enabled", True)),
    Mutation("storage-public-blobs", "azurerm_storage_account", setter("allow_nested_items_to_be_public", True)),
    Mutation("storage-tls-1.0", "azurerm_storage_account", setter("min_tls_version", "TLS1_0")),
    Mutation("container-public", "azurerm_storage_container", setter("container_access_type", "blob")),
    Mutation("storage-trusted-services-bypass", "azurerm_storage_account", trusted_services_bypass),
    Mutation("host-trusts-a-resource-instance", "<plan>", host_trusts_resource_instance),
    Mutation("package-in-recordings-account", "<plan>", package_into_recordings),
    Mutation("deadletter-shares-host-storage", "<plan>", deadletter_into_host_storage),
    Mutation("cosmos-account-keys", "azurerm_cosmosdb_account", setter("local_authentication_enabled", True)),
    Mutation("cosmos-provisioned-throughput", "azurerm_cosmosdb_account", setter("capabilities", [])),
    Mutation("jobs-other-partition-key", "azurerm_cosmosdb_sql_container", setter("partition_key_paths", ["/stage"])),
    Mutation(
        "topic-other-source",
        "azurerm_eventgrid_system_topic",
        setter("topic_type", "Microsoft.Resources.ResourceGroups"),
    ),
    Mutation(
        "events-every-type",
        "azurerm_eventgrid_system_topic_event_subscription",
        setter("included_event_types", ["Microsoft.Storage.BlobCreated", "Microsoft.Storage.BlobDeleted"]),
    ),
    Mutation("events-every-blob", "azurerm_eventgrid_system_topic_event_subscription", any_blob),
    Mutation(
        "events-cloudevents-schema",
        "azurerm_eventgrid_system_topic_event_subscription",
        setter("event_delivery_schema", "CloudEventSchemaV1_0"),
    ),
    Mutation(
        "events-not-a-webhook",
        "azurerm_eventgrid_system_topic_event_subscription",
        setter("webhook_endpoint", []),
    ),
    Mutation("events-unbounded-retries", "azurerm_eventgrid_system_topic_event_subscription", unbounded_retries),
    Mutation(
        "events-no-deadletter",
        "azurerm_eventgrid_system_topic_event_subscription",
        setter("storage_blob_dead_letter_destination", []),
    ),
    Mutation(
        "events-deadletter-elsewhere",
        "azurerm_eventgrid_system_topic_event_subscription",
        deadletter_to_another_container,
    ),
    Mutation(
        "function-basic-auth-publish",
        "azurerm_function_app_flex_consumption",
        setter("webdeploy_publish_basic_authentication_enabled", True),
    ),
    Mutation(
        "function-storage-connection-string",
        "azurerm_function_app_flex_consumption",
        setter("storage_authentication_type", "StorageAccountConnectionString"),
    ),
    Mutation("function-http-allowed", "azurerm_function_app_flex_consumption", setter("https_only", False)),
    Mutation("function-python-3.12", "azurerm_function_app_flex_consumption", setter("runtime_version", "3.12")),
    Mutation("appinsights-local-auth", "azurerm_application_insights", setter("local_authentication_enabled", True)),
    Mutation("openai-api-keys", "azurerm_cognitive_account", setter("local_auth_enabled", True)),
    Mutation("openai-no-subdomain", "<plan>", openai_subdomain_removed),
    Mutation("openai-outbound-open", "azurerm_cognitive_account", setter("outbound_network_access_restricted", False)),
    Mutation("openai-provisioned-throughput", "azurerm_cognitive_deployment", provisioned_sku),
    Mutation("speech-user-assigned-identity", "<plan>", speech_without_system_identity),
    Mutation("speech-calls-two-hosts", "<plan>", speech_fqdns(["streca.blob.core.windows.net", "example.com"])),
    Mutation("speech-calls-another-host", "<plan>", speech_fqdns(["example.com"])),
    Mutation(
        "diagnostics-other-workspace",
        "azurerm_monitor_diagnostic_setting",
        setter("log_analytics_workspace_id", WORKSPACE_OTHER),
    ),
    Mutation("diagnostics-missing", "<plan>", drop_cosmos_diagnostics),
    Mutation("role-owner", "azurerm_role_assignment", role_to_owner),
    Mutation("role-to-user", "azurerm_role_assignment", setter("principal_type", "User")),
    Mutation("operator-writes-jobs", "<plan>", operator_writes_jobs),
    Mutation("setting-connection-string", "<plan>", add_setting("RecordingsStorage")),
    Mutation("setting-api-key", "<plan>", add_setting("OPENAI_API_KEY")),
    Mutation("setting-trigger-queue-missing", "<plan>", drop_setting("RecordingsStorage__queueServiceUri")),
]


def conftest(plan: dict, policy: Path) -> tuple[int, str]:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(plan, fh)
    try:
        proc = subprocess.run(  # noqa: S603 - fixed argv
            ["conftest", "test", "--no-color", "--policy", str(policy), fh.name],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=120,
        )
    finally:
        Path(fh.name).unlink()
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    fails = [line.split(" - main - ", 1)[-1] for line in lines if line.startswith("FAIL")]
    if fails:
        return proc.returncode, fails[0]
    return proc.returncode, lines[-1] if lines else proc.stderr.strip()[-200:]


def mutate(plan: dict, m: Mutation) -> dict:
    out = copy.deepcopy(plan)
    if m.type == "<plan>":
        m.apply(out)
        return out
    for rc in out["resource_changes"]:
        if rc["type"] == m.type and rc["change"]["after"] is not None:
            m.apply(rc["change"]["after"])
            return out
    raise LookupError(m.type)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("plan", type=Path, nargs="?")
    parser.add_argument("--policy", type=Path, default=ROOT / "infra" / "policy")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    if args.list or not args.plan:
        for m in MUTATIONS:
            print(f"{m.name:38} {m.type}")
        return 0 if args.list else 2

    plan = json.loads(args.plan.read_text())
    code, summary = conftest(plan, args.policy)
    if code != 0:
        print(f"ERROR    baseline: the unmodified plan fails the gate ({summary})")
        return 1
    print(f"OK       baseline: {summary}")

    problems = 0
    for m in MUTATIONS:
        try:
            mutated = mutate(plan, m)
        except LookupError as exc:
            print(f"STALE    {m.name:38} {exc} not in the plan; update the mutation")
            problems += 1
            continue
        code, summary = conftest(mutated, args.policy)
        if code != 0:
            print(f"DENIED   {m.name:38} {summary}")
        else:
            print(f"ALLOWED  {m.name:38} the gate passed it: add or fix a policy rule")
            problems += 1
    print(f"{len(MUTATIONS) - problems}/{len(MUTATIONS)} mutations denied")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
