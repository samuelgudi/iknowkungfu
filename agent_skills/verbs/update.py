"""update verb — thin wrapper around clients.skill_discovery.update.refresh."""
from clients.skill_discovery.update import refresh


def run(args) -> int:
    return refresh()
