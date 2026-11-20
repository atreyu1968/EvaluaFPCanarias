"""Pruebas del ámbito cerrado Canarias · Administración y Gestión."""
import unittest
import canarias_ag as ag


class CanaryAdminScopeTests(unittest.TestCase):
    def test_expected_degrees(self):
        self.assertEqual(len(ag.CYCLES), 4)
        self.assertEqual({c["grade"] for c in ag.CYCLES}, {"Básico", "Medio", "Superior"})

    def test_canarias_accepted(self):
        self.assertEqual(ag.ensure_territory("CN"), "Canarias")
        self.assertEqual(ag.ensure_territory("Canarias"), "Canarias")

    def test_other_territory_denied(self):
        for region in ("Andalucía", "Madrid", "", None):
            with self.subTest(region=region), self.assertRaises(ValueError):
                ag.ensure_territory(region)

    def test_cycle_variants(self):
        self.assertEqual(ag.canonical_cycle("Técnico en Gestión Administrativa"),
                         "CFGM Gestión Administrativa")
        self.assertEqual(ag.canonical_cycle("Administración y Finanzas"),
                         "CFGS Administración y Finanzas")
        self.assertEqual(ag.canonical_cycle("CFGB Servicios Administrativos"),
                         "CFGB Servicios Administrativos")

    def test_other_families_denied(self):
        for name in ("CFGS Automoción", "Técnico en Farmacia", "", "CFGM Gestión Comercial"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                ag.canonical_cycle(name)

    def test_no_unverified_curriculum_data(self):
        catalog = ag.public_catalog()
        self.assertEqual(catalog["module_catalog_status"], "pendiente_de_contraste")
        self.assertEqual(catalog["verified_modules"], [])
        self.assertEqual(catalog["verified_outcomes"], [])
        self.assertEqual(catalog["verified_criteria"], [])
        catalog["cycles"][0]["name"] = "mutado"
        self.assertNotEqual(ag.CYCLES[0]["name"], "mutado")


if __name__ == "__main__":
    unittest.main()
