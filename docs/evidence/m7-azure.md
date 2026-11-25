# M7: the Azure evening, started 2026-11-24T22:52:26Z

## E1 apply (run 45505138848)
```
[1mPlan:[0m [0m42 to add, 0 to change, 0 to destroy.
[36;1mconftest test --no-color --policy ../../policy plan.json | grep -E "^FAIL|tests,"[0m
50 tests, 50 passed, 0 warnings, 0 failures, 0 exceptions
[36;1m  terraform show -no-color tfplan | grep -E '^  # |^Plan:|^No changes' | sed "s/${ARM_SUBSCRIPTION_ID}/***/g"[0m
Apply complete! Resources: 42 added, 0 changed, 0 destroyed.[0m
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
[1mPlan:[0m [0m1 to add, 1 to change, 0 to destroy.
[36;1mconftest test --no-color --policy ../../policy plan.json | grep -E "^FAIL|tests,"[0m
50 tests, 50 passed, 0 warnings, 0 failures, 0 exceptions
[36;1m  terraform show -no-color tfplan | grep -E '^  # |^Plan:|^No changes' | sed "s/${ARM_SUBSCRIPTION_ID}/***/g"[0m
Apply complete! Resources: 1 added, 1 changed, 0 destroyed.[0m
```

## E8 destroy (run 45512212455)
```
[1mPlan:[0m [0m0 to add, 0 to change, 43 to destroy.
[36;1m  terraform show -no-color tfplan | grep -E '^  # |^Plan:|^No changes' | sed "s/${ARM_SUBSCRIPTION_ID}/***/g"[0m
OK   az signed in as ffef284a…
OK   deleted Application Insights Smart Detection
Apply complete! Resources: 0 added, 0 changed, 43 destroyed.[0m
[36;1mtest "$(az group exists --name "$RESOURCE_GROUP")" = false && echo "OK   $RESOURCE_GROUP deleted"[0m
[36;1mtest "$left" = 0 && echo "OK   no soft-deleted Cognitive Services account from $RESOURCE_GROUP"[0m
OK   az signed in as ffef284a…
OK   rg-meet-azure deleted
OK   no soft-deleted Cognitive Services account from rg-meet-azure
```

