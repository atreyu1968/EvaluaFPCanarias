"""Regresión HTTP y SQLite: el índice de 2024 nunca valida un currículo."""
import json
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

import app
import database


class CanariasModuleReferenceHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='canarias_procedencia_http_')
        root = Path(cls.temp.name)
        cls.patches = [
            patch.object(database, 'DB_FILE', root / 'datos.sqlite3'),
            patch.object(database, 'DATA', root),
            patch.object(database, 'STORAGE', root / 'almacen'),
            patch.object(database, 'BACKUPS', root / 'copias'),
        ]
        for item in cls.patches:
            item.start()
        database.STORAGE.mkdir(parents=True, exist_ok=True)
        database.BACKUPS.mkdir(parents=True, exist_ok=True)
        cls.server, cls.base_url = app.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        for item in reversed(cls.patches):
            item.stop()
        cls.temp.cleanup()

    def send(self, path, payload=None):
        headers = {'X-App-Token': app.TOKEN}
        if payload is not None:
            headers['Content-Type'] = 'application/json'
        request = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload).encode('utf-8') if payload is not None else None,
            method='POST' if payload is not None else 'GET',
            headers=headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as error:
            return error.code, json.load(error)

    def payload(self, **changes):
        data = {
            'academic_year': '2026-2027',
            'territory': 'Canarias',
            'cycle': 'CFGM Gestión Administrativa',
            'name': 'Técnica contable',
            'group_name': '1A',
            'reference_course': '1',
            'reference_code': '0441',
        }
        data.update(changes)
        return data

    def test_create_reference_keeps_status_and_curriculum_empty(self):
        status, created = self.send('api/modules', self.payload())
        self.assertEqual(status, 200, created)
        self.assertTrue(created['historical_reference_used'])
        module_id = created['id']
        status, info = self.send(f'api/programming-builder/{module_id}')
        self.assertEqual(status, 200, info)
        ref = info['module_reference']
        self.assertEqual(ref['module_code'], '0441')
        self.assertEqual(ref['course'], 1)
        self.assertEqual(ref['reference_academic_year'], '2024-2025')
        self.assertEqual(ref['reference_annual_hours'], 96)
        self.assertEqual(ref['status'], 'reference_requires_current_verification')
        self.assertFalse(ref['hours_confirmed'])
        self.assertFalse(ref['curriculum_confirmed'])
        self.assertFalse(ref['ra_ce_imported_from_reference'])
        self.assertFalse(info['draft']['curriculum_confirmed'])
        self.assertEqual(info['draft']['official_module_code'], '')
        self.assertEqual((info['counts']['ra'], info['counts']['ce']), (0, 0))
        with database.connect() as db:
            self.assertEqual(
                db.execute('SELECT COUNT(*) FROM canarias_module_references WHERE module_id=?',
                           (module_id,)).fetchone()[0], 1
            )
            self.assertEqual(db.execute('SELECT COUNT(*) FROM outcomes WHERE module_id=?',
                                        (module_id,)).fetchone()[0], 0)

    def test_duplicate_name_resolved_by_course_and_code(self):
        for course, code in [(1, '3161'), (2, '3162')]:
            with self.subTest(course=course):
                status, created = self.send('api/modules', self.payload(
                    cycle='CFGB Servicios Administrativos',
                    name='Lengua castellana y Ciencias sociales',
                    reference_course=str(course),
                    reference_code=code,
                ))
                self.assertEqual(status, 200, created)
                _, info = self.send(f"api/programming-builder/{created['id']}")
                self.assertEqual(info['module_reference']['module_code'], code)
                self.assertEqual(info['module_reference']['course'], course)

    def test_reference_without_rd_code(self):
        status, created = self.send('api/modules', self.payload(
            cycle='CFGB Servicios Administrativos',
            name='Actividad física y bienestar emocional',
            reference_course='1',
            reference_code='',
        ))
        self.assertEqual(status, 200, created)
        _, info = self.send(f"api/programming-builder/{created['id']}")
        self.assertIsNone(info['module_reference']['module_code'])

    def test_manual_optional_module_remains_unlinked(self):
        data = self.payload(name='Optativa de gestión documental')
        data.pop('reference_code')
        data.pop('reference_course')
        status, created = self.send('api/modules', data)
        self.assertEqual(status, 200, created)
        self.assertFalse(created['historical_reference_used'])
        _, info = self.send(f"api/programming-builder/{created['id']}")
        self.assertIsNone(info['module_reference'])

    def test_mismatches_and_tampering_rejected(self):
        scenarios = (
            {'reference_course': '3'},
            {'reference_course': '2'},
            {'reference_code': '9999'},
            {'name': 'Otro módulo'},
            {'cycle': 'CFGS Administración y Finanzas'},
            {'reference_course': '', 'reference_code': '0441'},
            {'catalog_entry_id': 1},
        )
        with database.connect() as db:
            original = db.execute('SELECT COUNT(*) FROM modules').fetchone()[0]
        for change in scenarios:
            with self.subTest(change=change):
                status, body = self.send('api/modules', self.payload(**change))
                self.assertEqual(status, 400, body)
                self.assertIn('error', body)
        with database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM modules').fetchone()[0], original)


if __name__ == '__main__':
    unittest.main()
