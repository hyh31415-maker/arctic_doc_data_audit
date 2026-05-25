.PHONY: init download-arcticgro download-candidates preprocess build-matrix report test

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

report:
	$(PYTHON) -m arctic_doc_data_audit.cli report

test:
	$(PYTHON) -m pytest

