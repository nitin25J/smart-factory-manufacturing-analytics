"""
Dashboard Modules Package.
Manufacturing Diagnostic Intelligence System - Phase 2.3.
"""

from scripts.app.modules.factory_overview import render_factory_overview
from scripts.app.modules.machine_health import render_machine_health
from scripts.app.modules.production_energy import render_production_energy
from scripts.app.modules.quality_efficiency import render_quality_efficiency

__all__ = [
    "render_factory_overview",
    "render_machine_health",
    "render_production_energy",
    "render_quality_efficiency",
]

