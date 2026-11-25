# M7: the Azure evening, started 2026-11-24T22:52:26Z

- Regenerated in M8 (D51) from the same four runs with scripts/run_evidence.sh: the first version kept ANSI colour codes and the step commands GitHub echoes; E3 now also shows what its plan changed and the host-storage check after the apply.

## E1 apply (run 45505138848)
```
Plan: 42 to add, 0 to change, 0 to destroy.
50 tests, 50 passed, 0 warnings, 0 failures, 0 exceptions
Apply complete! Resources: 42 added, 0 changed, 0 destroyed.
OK   az signed in as ffef284a…
OK   removed azurerm's key-based AzureWebJobsStorage from func-meet-azure-q9406 and restarted it
```

## E2 deploy-code (run 45507989843)
```
OK   az signed in as ffef284a…
OK   func-meet-azure-q9406 has no key-based AzureWebJobsStorage
OK   package: 23 files
OK   deployed to func-meet-azure-q9406 (remote build done)
OK   functions: health meeting_job meeting_status 
```

## E3 apply with the manifest subscription (run 45508935508)
```
  ~ update in-place
  # module.stack.module.blobevents[0].azurerm_eventgrid_system_topic_event_subscription.manifest[0] will be created
  # module.stack.module.functionapp[0].azurerm_function_app_flex_consumption.this will be updated in-place
  ~ resource "azurerm_function_app_flex_consumption" "this" {
      ~ tags                                           = {
Plan: 1 to add, 1 to change, 0 to destroy.
50 tests, 50 passed, 0 warnings, 0 failures, 0 exceptions
Apply complete! Resources: 1 added, 1 changed, 0 destroyed.
OK   az signed in as ffef284a…
OK   removed azurerm's key-based AzureWebJobsStorage from func-meet-azure-q9406 and restarted it
```

## E8 destroy (run 45512212455)
```
Plan: 0 to add, 0 to change, 43 to destroy.
OK   az signed in as ffef284a…
OK   deleted Application Insights Smart Detection
Apply complete! Resources: 0 added, 0 changed, 43 destroyed.
OK   az signed in as ffef284a…
OK   rg-meet-azure deleted
OK   no soft-deleted Cognitive Services account from rg-meet-azure
```

