"""Pruebas HTTP del selector documental de módulos A&G Canarias."""
import json
import tempfile
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from unittest.mock import patch

import app
import database


class CanaryModulesHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix="ag_canarias_modules_http_")
        root=Path(cls.temp.name)
        cls.patches=[
            patch.object(database,"DB_FILE",root/"datos.sqlite3"),
            patch.object(database,"DATA",root),
            patch.object(database,"STORAGE",root/"almacen"),
            patch.object(database,"BACKUPS",root/"copias"),
        ]
        for p in cls.patches:p.start()
        database.STORAGE.mkdir(parents=True,exist_ok=True)
        database.BACKUPS.mkdir(parents=True,exist_ok=True)
        cls.server,cls.root=app.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        for p in reversed(cls.patches):p.stop()
        cls.temp.cleanup()

    def req(self,cycle="CFGM Gestión Administrativa",year="2026-2027",
            course=None,territory="Canarias",auth=True):
        params={"cycle":cycle,"academic_year":year,"territory":territory}
        if course is not None:params["course"]=course
        path="api/canarias-ag/modules?"+urllib.parse.urlencode(params)
        headers={"X-App-Token":app.TOKEN} if auth else {}
        req=urllib.request.Request(self.root+path,headers=headers)
        try:
            with urllib.request.urlopen(req,timeout=12) as res:
                return res.status,json.load(res)
        except urllib.error.HTTPError as exc:
            return exc.code,json.load(exc)

    def test_reference_is_retrievable_without_auto_confirmation(self):
        status,doc=self.req()
        self.assertEqual(status,200)
        self.assertEqual((doc["territory"],doc["cycle"],doc["count"]),
                         ("Canarias","CFGM Gestión Administrativa",15))
        self.assertEqual(doc["status"],"reference_requires_current_verification")
        self.assertEqual(doc["reference_academic_year"],"2024-2025")
        self.assertTrue(all(not m["curriculum_confirmed"] and not m["hours_confirmed"]
                            for m in doc["modules"]))
        self.assertTrue(doc["source_url"].startswith("https://"))
        with database.connect() as d:
            self.assertEqual(d.execute("SELECT COUNT(*) FROM modules").fetchone()[0],0)
            self.assertEqual(d.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0],0)
            self.assertEqual(d.execute("SELECT COUNT(*) FROM criteria").fetchone()[0],0)

    def test_all_four_cycles_and_optional_course_filter(self):
        for cycle,total in [
            ("CFGB Servicios Administrativos",16),
            ("CFGM Gestión Administrativa",15),
            ("CFGS Administración y Finanzas",16),
            ("CFGS Asistencia a la Dirección",15),
        ]:
            with self.subTest(cycle=cycle):
                status,doc=self.req(cycle=cycle,course="1")
                self.assertEqual(status,200)
                self.assertEqual(doc["count"],8)
                self.assertEqual(doc["total_count"],total)
                self.assertEqual(doc["filter_course"],1)
                self.assertTrue(all(m["course"]==1 for m in doc["modules"]))

    def test_invalid_inputs_and_session(self):
        self.assertIn(self.req(auth=False)[0],(401,403))
        for scope in (
            {"cycle":"CFGM Auxiliar de Enfermería"},
            {"year":"2026-2026"},
            {"territory":"Comunidad de Madrid"},
            {"course":"3"},
        ):
            with self.subTest(scope=scope):
                code,body=self.req(**scope)
                self.assertEqual(code,400)
                self.assertIn("error",body)


if __name__=="__main__":
    unittest.main()
