"""Checks the companion ERP guard when that local checkout is available."""
import importlib.util
import os
from pathlib import Path

import pytest

ERP = Path(os.environ.get('ERP_PROJECT_ROOT', '.runtime/optional-erp-checkout'))
ERP_GUARD = ERP / 'src/agent/database_target.py'


@pytest.mark.skipif(not ERP_GUARD.is_file(), reason='local companion ERP guard is not available')
def test_erp_guard_rejects_rag_and_superuser():
    spec = importlib.util.spec_from_file_location('erp_database_target', ERP_GUARD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for role in ['erp_agent', 'erp_app']:
        module.validate_target('erp_agent', role, False)
    for database, role, superuser in [('zhanggui_dev', 'erp_app', False), ('erp_agent', 'postgres', True), ('erp_agent', 'erp_agent', True)]:
        with pytest.raises(RuntimeError):
            module.validate_target(database, role, superuser)
