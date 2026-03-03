import unittest

import all as allmod


class YangdoBoardSlugTests(unittest.TestCase):
    def test_resolve_board_slug_prefers_cli_override(self):
        original_yangdo = allmod.YANGDO_CALCULATOR_BOARD_SLUG
        original_mna = allmod.MNA_BOARD_SLUG
        try:
            allmod.YANGDO_CALCULATOR_BOARD_SLUG = "yangdo_ai"
            allmod.MNA_BOARD_SLUG = "mna"
            self.assertEqual(allmod._resolve_yangdo_page_board_slug("calc"), "calc")
        finally:
            allmod.YANGDO_CALCULATOR_BOARD_SLUG = original_yangdo
            allmod.MNA_BOARD_SLUG = original_mna

    def test_resolve_board_slug_uses_yangdo_setting(self):
        original_yangdo = allmod.YANGDO_CALCULATOR_BOARD_SLUG
        original_mna = allmod.MNA_BOARD_SLUG
        try:
            allmod.YANGDO_CALCULATOR_BOARD_SLUG = "yangdo_ai"
            allmod.MNA_BOARD_SLUG = "mna"
            self.assertEqual(allmod._resolve_yangdo_page_board_slug(""), "yangdo_ai")
        finally:
            allmod.YANGDO_CALCULATOR_BOARD_SLUG = original_yangdo
            allmod.MNA_BOARD_SLUG = original_mna

    def test_resolve_board_slug_falls_back_to_mna(self):
        original_yangdo = allmod.YANGDO_CALCULATOR_BOARD_SLUG
        original_mna = allmod.MNA_BOARD_SLUG
        try:
            allmod.YANGDO_CALCULATOR_BOARD_SLUG = ""
            allmod.MNA_BOARD_SLUG = "mna"
            self.assertEqual(allmod._resolve_yangdo_page_board_slug(""), "mna")
        finally:
            allmod.YANGDO_CALCULATOR_BOARD_SLUG = original_yangdo
            allmod.MNA_BOARD_SLUG = original_mna


if __name__ == "__main__":
    unittest.main()
