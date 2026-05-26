.PHONY: init download-arcticgro download-candidates preprocess build-matrix complete-data-sources audit-candidate-labels model-readiness freeze-data qa-data fix-gee-failures discover-wqp-characteristics gee-auth-check run-gee-extraction complete-basin-context finalize-candidate-sources report test

PYTHON ?= python

init:
	$(PYTHON) -m arctic_doc_data_audit.cli init

download-arcticgro:
	$(PYTHON) -m arctic_doc_data_audit.cli download --source arcticgro

download-candidates:
	$(PYTHON) -m arctic_doc_data_audit.cli download --source wqp_usgs --dry-run
	$(PYTHON) -m arctic_doc_data_audit.cli download --source datastream --dry-run
	$(PYTHON) -m arctic_doc_data_audit.cli download --source arctic_data_center --dry-run
	$(PYTHON) -m arctic_doc_data_audit.cli download --source partners_mdpi --dry-run

preprocess:
	$(PYTHON) -m arctic_doc_data_audit.cli preprocess --all

build-matrix:
	$(PYTHON) -m arctic_doc_data_audit.cli build-training-matrix

complete-data-sources:
	$(PYTHON) -m arctic_doc_data_audit.cli complete-data-sources --all

audit-candidate-labels:
	$(PYTHON) -m arctic_doc_data_audit.cli audit-candidate-labels

model-readiness:
	$(PYTHON) -m arctic_doc_data_audit.cli model-readiness

freeze-data:
	$(PYTHON) -m arctic_doc_data_audit.cli freeze-data --freeze-id data_freeze_$(shell powershell -NoProfile -Command "Get-Date -Format yyyyMMdd")_v1

qa-data:
	$(PYTHON) -m arctic_doc_data_audit.cli qa-data

fix-gee-failures:
	$(PYTHON) -m arctic_doc_data_audit.cli fix-gee-failures --all

discover-wqp-characteristics:
	$(PYTHON) -m arctic_doc_data_audit.cli discover-wqp-characteristics

gee-auth-check:
	$(PYTHON) -m arctic_doc_data_audit.cli gee-auth-check

run-gee-extraction:
	$(PYTHON) -m arctic_doc_data_audit.cli run-gee-extraction --all

complete-basin-context:
	$(PYTHON) -m arctic_doc_data_audit.cli complete-basin-context

finalize-candidate-sources:
	$(PYTHON) -m arctic_doc_data_audit.cli finalize-candidate-sources --defer-datastream

report:
	$(PYTHON) -m arctic_doc_data_audit.cli report

test:
	$(PYTHON) -m pytest
