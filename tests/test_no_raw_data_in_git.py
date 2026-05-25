from __future__ import annotations

from arctic_doc_data_audit.paths import project_root
from arctic_doc_data_audit.qc.checks import gitignore_excludes_raw


def test_gitignore_excludes_raw_and_generated_data() -> None:
    assert gitignore_excludes_raw(project_root())

