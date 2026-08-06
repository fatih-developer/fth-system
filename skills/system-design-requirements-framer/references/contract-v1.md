# System Design Contract v1.0

This skill carries the contract locally so it remains usable if sibling skill paths change. The state is an object with `contract_version: "1.0"`, `design_id` (`SD-*`), `mode` (`interview|production`), `status`, and these top-level collections:

`problem`, `functional_requirements` (`FR-*`), `non_functional_requirements` (`NFR-*`), `constraints`, `out_of_scope`, `assumptions` (`ASM-*`), `estimates` (`EST-*`), `architecture`, `interfaces`, `data_topology`, `decisions` (`DEC-*`), `failure_modes` (`FM-*`), `validation_findings` (`SDV-*`), `open_questions`, and `traceability`.

Every stable record has `id`, `status`, `source`, `confidence`, and, where applicable, `related_ids`. Facts describe supplied evidence; assumptions describe provisional beliefs; estimates describe calculations; decisions describe selected and rejected alternatives; findings describe validation results. Do not relabel one category as another.
