"""La consulta de módulos se basa en referencias, no en currículo certificado."""
import unittest
from canarias_modules import list_modules, SOURCE_URL, BASIC_SOURCE_URL

class ModuleReferenceTests(unittest.TestCase):
    def test_cycle_counts_and_unique_codes(self):
        for cycle, count in [
            ("CFGM Gestión Administrativa", 15),
            ("CFGS Administración y Finanzas", 16),
            ("CFGS Asistencia a la Dirección", 15),
        ]:
            with self.subTest(cycle=cycle):
                record = list_modules(cycle, "2026-2027")
                self.assertEqual(record["count"], count)
                self.assertEqual(len({m["code"] for m in record["modules"]}), count)
                self.assertTrue(all(m["hours_confirmed"] is False for m in record["modules"]))
                self.assertTrue(all(m["curriculum_confirmed"] is False for m in record["modules"]))
                self.assertEqual(record["source_url"], SOURCE_URL)
    def test_medio_contable(self):
        item = next(m for m in list_modules("CFGM Gestión Administrativa","2026-2027")["modules"]
                    if m["code"] == "0441")
        self.assertEqual((item["name"], item["course"], item["reference_annual_hours"]),
                         ("Técnica contable",1,96))
    def test_superior_rrhh(self):
        item = next(m for m in list_modules("CFGS Administración y Finanzas","2026-2027")["modules"]
                    if m["code"] == "0652")
        self.assertEqual((item["name"], item["course"], item["reference_annual_hours"]),
                         ("Gestión de recursos humanos",2,138))
    def test_basic_includes_general_and_professional_fields(self):
        item = list_modules("CFGB Servicios Administrativos","2026-2027")
        self.assertEqual(item["count"], 16)
        self.assertEqual(item["source_url"], BASIC_SOURCE_URL)
        self.assertEqual(len([x for x in item["modules"] if x["code"] is None]), 4)
        self.assertTrue(all(x["curriculum_confirmed"] is False for x in item["modules"]))
        module = next(x for x in item["modules"] if x["code"] == "3002")
        self.assertEqual((module["name"],module["course"],module["reference_annual_hours"]),
                         ("Aplicaciones básicas de ofimática",2,302))
        self.assertFalse(any(x["name"] == "Tutoría" for x in item["modules"]))
    def test_other_cycles_disallowed(self):
        with self.assertRaises(ValueError):
            list_modules("CFGM Cuidados Auxiliares", "2026-2027")
    def test_course_filter_keeps_reference_metadata(self):
        for cycle, total, first, second in [
            ("CFGB Servicios Administrativos",16,8,8),
            ("CFGM Gestión Administrativa",15,8,7),
            ("CFGS Administración y Finanzas",16,8,8),
            ("CFGS Asistencia a la Dirección",15,8,7),
        ]:
            with self.subTest(cycle=cycle):
                one=list_modules(cycle,"2026-2027",course="1")
                two=list_modules(cycle,"2026-2027",course=2)
                self.assertEqual((one["count"],two["count"],one["total_count"]),
                                 (first,second,total))
                self.assertTrue(all(m["course"]==1 and not m["curriculum_confirmed"]
                                    for m in one["modules"]))
                self.assertTrue(all(m["course"]==2 and not m["hours_confirmed"]
                                    for m in two["modules"]))
                self.assertEqual((one["filter_course"],two["filter_course"]),(1,2))
    def test_bad_course_filter_is_rejected(self):
        for course in ("0","3","1;DROP",True):
            with self.subTest(course=course), self.assertRaises(ValueError):
                list_modules("CFGM Gestión Administrativa","2026-2027",course=course)
    def test_invalid_academic_year(self):
        with self.assertRaises(ValueError):
            list_modules("CFGM Gestión Administrativa", "2026-2026")
if __name__ == "__main__":
    unittest.main()
