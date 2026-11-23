# CI (M4)

## PR #7 (M4) checks
```
Graphify	pass	3m27s	https://app.graphify.com/salman-s-workspace-0437bd/reviews?run=9debe666-ca24-4c8e-9758-ac22948025cc	
integration	pass	49s	https://github.com/salmanamn/meeting-summarizer/actions/runs/45236621870/job/137909918879	
lint	pass	23s	https://github.com/salmanamn/meeting-summarizer/actions/runs/45236621870/job/137909918836	
package	pass	36s	https://github.com/salmanamn/meeting-summarizer/actions/runs/45236621870/job/137909918011	
tests-must-fail	pass	46s	https://github.com/salmanamn/meeting-summarizer/actions/runs/45236621870/job/137909919369	
unit	pass	32s	https://github.com/salmanamn/meeting-summarizer/actions/runs/45236621870/job/137909918615	
```

## Gate demo, PR #8 (closed): the SHA-256 check switched off
```
integration	fail	55s	https://github.com/salmanamn/meeting-summarizer/actions/runs/45239085039/job/137918556848	
tests-must-fail	fail	20s	https://github.com/salmanamn/meeting-summarizer/actions/runs/45239085039/job/137918556324	
unit	fail	22s	https://github.com/salmanamn/meeting-summarizer/actions/runs/45239085039/job/137918556222	
Graphify	pending	0	https://graphify.com	
lint	pass	22s	https://github.com/salmanamn/meeting-summarizer/actions/runs/45239085039/job/137918555976	
package	pass	32s	https://github.com/salmanamn/meeting-summarizer/actions/runs/45239085039/job/137918556302	
mergeStateStatus at the time: BLOCKED
```

## Known-bad changes (local run)
```
OK       baseline: 276 passed in 6.42s
KILLED   any-blob-starts-a-job              tests/unit/test_manifest.py
KILLED   size-not-compared                  tests/unit/test_job.py
KILLED   type-from-the-name                 tests/unit/test_job.py
KILLED   hash-not-compared                  tests/unit/test_job.py
KILLED   no-length-limit                    tests/unit/test_job.py
KILLED   duplicate-redone                   tests/unit/test_job.py
KILLED   transcript-not-reused              tests/unit/test_job.py
KILLED   attempts-unbounded                 tests/unit/test_job.py
KILLED   model-error-retried-at-once        tests/unit/test_job.py
KILLED   schema-allows-extra-fields         tests/unit/test_summary.py
KILLED   evidence-any-string                tests/unit/test_summary.py
KILLED   owner-not-checked                  tests/unit/test_summary.py
KILLED   due-not-checked                    tests/unit/test_summary.py
KILLED   undecided-kept                     tests/unit/test_summary.py
KILLED   repeated-action-kept-as-decision   tests/unit/test_summary.py
KILLED   transcript-closes-its-block        tests/unit/test_summarize.py
KILLED   cut-off-answer-accepted            tests/unit/test_summarize.py
KILLED   answered-question-taken-on-trust   tests/unit/test_summarize.py
KILLED   encrypted-docx-read                tests/unit/test_documents.py
KILLED   pdf-pages-unbounded                tests/unit/test_documents.py
KILLED   reasoning-model-gets-temperature   tests/unit/test_summarize.py
KILLED   status-shows-system-fields         tests/unit/test_function_app.py
KILLED   package-gate-ignores-forbidden     tests/unit/test_package_size.py
23/23 mutations killed
```

## Package gate (local run)
```
- packages for Linux x86-64, Python 3.13: 605 MB unpacked
- largest: av.libs 105 MB, ctranslate2.libs 83 MB, onnxruntime 76 MB, ctranslate2 70 MB, pandas 43 MB, av 32 MB
- app package: 605 MB unpacked, 183 MB as a zip
- Whisper model stt-small: 486 MB
- package + model: 1091 MB unpacked
PACKAGE OK   81 distributions, zip 183 MB <= 200 MB, none of torch, onnxruntime-gpu, piper-tts, pytest, ruff
```

## Branch protection on main
```
{"checks":["lint","unit","tests-must-fail","integration","package"],"enforce_admins":true,"linear":true,"strict":true}
```
