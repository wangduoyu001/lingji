"""AI client profile registry: each connected agent has an explicit identity."""

from __future__ import annotations

import unittest

from src.gateway.profiles import PROPOSAL_TOOLS, AIProfileRegistry


class AIProfileRegistryTests(unittest.TestCase):
    def test_zcode_profile_is_registered_with_read_and_propose_tools(self):
        registry = AIProfileRegistry()
        profile = registry.get("zcode")
        self.assertEqual(profile.display_name, "ZCode")
        self.assertEqual(profile.transport, "mcp_stdio")
        self.assertEqual(profile.allowed_tools, PROPOSAL_TOOLS)
        self.assertIn("search_memory", profile.allowed_tools)
        self.assertIn("propose_memory", profile.allowed_tools)
        self.assertFalse(profile.can_modify_core_memory, "改写 Core 仍是主人专属权限")

    def test_unknown_agent_is_rejected(self):
        with self.assertRaises(KeyError):
            AIProfileRegistry().get("not-a-real-agent")

    def test_every_default_profile_can_search_but_not_modify_core(self):
        registry = AIProfileRegistry()
        external = [item for item in registry.list() if item["agent_id"] != "lingji-local"]
        for profile in external:
            self.assertIn("search_memory", profile["allowed_tools"], profile["agent_id"])
            self.assertFalse(profile["can_modify_core_memory"], profile["agent_id"])


if __name__ == "__main__":
    unittest.main()
