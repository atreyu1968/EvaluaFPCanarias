"""Pruebas de seguridad portable, trayectorias USB, evaluación y notas manuales."""
import json
from contextlib import closing
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import app
import database
import evaluacion
import ia
import storage_config

class Version100Tests(unittest.TestCase):
    def test_portable_root_relative_config_and_drive_moves(self):
        with tempfile.TemporaryDirectory() as temp:
            home=Path(temp)/'pendrive_A';home.mkdir()
            marker=home/'EvaluaFP.portable.json'
            marker.write_text(json.dumps({'data_dir':'Datos_FP','backup_dir':'Seguridad_Copias'}),encoding='utf-8')
            with patch.object(storage_config,'APP_HOME',home),patch.object(storage_config,'PORTABLE',True),patch.object(storage_config,'PORTABLE_FILE',marker),patch.dict(os.environ,{'EVALUAFP_DATA_DIR':''}):
                datadir,backups=storage_config._configured_folders()
                self.assertEqual(datadir.resolve(),(home/'Datos_FP').resolve())
                self.assertEqual(backups.resolve(),(home/'Seguridad_Copias').resolve())
                self.assertEqual(storage_config.resolve_folder('Datos_FP'),datadir)
                self.assertRaisesRegex(ValueError,'misma unidad|subcarpeta',storage_config.resolve_folder,'.')

    def test_aes_gcm_encrypt_unlock_and_wrong_password(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'api_cifrada.json'
            with patch.object(storage_config,'PORTABLE',True), patch.object(ia,'secret_file',return_value=path):
                ia.lock_secret()
                self.assertFalse(ia.secret_saved())
                _,persist=ia.set_secret('sk-una-clave-de-prueba-no-real','contraseña_segura_de_prueba_2026')
                self.assertTrue(persist)
                self.assertNotIn('sk-una-clave',path.read_text(encoding='utf-8'))
                self.assertEqual(ia.get_secret(),'sk-una-clave-de-prueba-no-real')
                ia.lock_secret()
                self.assertTrue(ia.secret_saved())
                self.assertFalse(ia.key_available())
                with self.assertRaisesRegex(ValueError,'Contraseña incorrecta'):
                    ia.unlock_secret('CONTRASEÑA_DISTINTA')
                self.assertTrue(ia.unlock_secret('contraseña_segura_de_prueba_2026'))
                self.assertEqual(ia.get_secret(),'sk-una-clave-de-prueba-no-real')
                ia.lock_secret()

    def test_relocate_copies_sqlite_preserving_source_and_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            home=Path(temp);src=home/'origen';dst=home/'destino'
            oldbacks=home/'copias_antiguas';newbacks=home/'copias_nuevas'
            (src/'datos').mkdir(parents=True);(src/'almacen').mkdir(parents=True)
            (oldbacks).mkdir();(oldbacks/'copia.zip').write_bytes(b'ZIP-DE-PRUEBA')
            original=src/'almacen'/'doc.pdf';original.write_bytes(b'ORIGINAL PDF')
            with closing(sqlite3.connect(src/'datos'/'evaluafp.sqlite3')) as d, d:
                d.execute('CREATE TABLE programmings (id INTEGER PRIMARY KEY,local_path TEXT)')
                d.execute('INSERT INTO programmings(local_path) VALUES(?)',(str(original),))
            marker=home/'EvaluaFP.portable.json'
            marker.write_text('{}',encoding='utf-8')
            with patch.dict(os.environ,{},clear=False),patch.object(storage_config,'APP_HOME',home),\
                 patch.object(storage_config,'PORTABLE_FILE',marker),patch.object(storage_config,'PORTABLE',True),\
                 patch.object(storage_config,'DATA_DIR',src),patch.object(storage_config,'BACKUP_DIR',oldbacks):
                with patch.dict(os.environ,{'EVALUAFP_DATA_DIR':''}):
                    result=storage_config.relocate('destino','copias_nuevas')
            self.assertTrue(result['restart_required'])
            self.assertTrue(original.exists())
            self.assertEqual((dst/'almacen'/'doc.pdf').read_bytes(),b'ORIGINAL PDF')
            self.assertTrue((newbacks/'copia.zip').exists())
            with closing(sqlite3.connect(dst/'datos'/'evaluafp.sqlite3')) as d:
                self.assertEqual(Path(d.execute('SELECT local_path FROM programmings').fetchone()[0]).resolve(),(dst/'almacen'/'doc.pdf').resolve())
            self.assertEqual(json.loads(marker.read_text(encoding='utf-8'))['data_dir'],'destino')

    def test_sqlite_migration_closes_both_connections_on_windows(self):
        """Una conexión activa bloquearía TemporaryDirectory en Windows (WinError 32).

        No depende de Linux/Windows: instrumenta close() y comprueba que
        relocate libera origen y destino antes de devolver el control.
        """
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            src = home / 'origen'
            dst = home / 'destino'
            (src / 'datos').mkdir(parents=True)
            (src / 'almacen').mkdir()
            with closing(sqlite3.connect(src/'datos'/'evaluafp.sqlite3')) as db, db:
                db.execute('CREATE TABLE programmings(id INTEGER PRIMARY KEY, local_path TEXT)')
                db.execute('INSERT INTO programmings(local_path) VALUES(?)',
                           (str(src/'almacen'/'prueba.pdf'),))
            (src / 'almacen' / 'prueba.pdf').write_bytes(b'prueba')
            marker = home / 'EvaluaFP.portable.json'
            marker.write_text('{}', encoding='utf-8')
            handles = []
            real_connect = sqlite3.connect

            class TrackedConnection(sqlite3.Connection):
                def close(self):
                    self.cerrada = True
                    return super().close()

            def tracked_connect(*args, **kwargs):
                kwargs['factory'] = TrackedConnection
                conn = real_connect(*args, **kwargs)
                conn.cerrada = False
                handles.append(conn)
                return conn

            with patch.dict(os.environ, {'EVALUAFP_DATA_DIR': ''}), \
                 patch.object(storage_config, 'APP_HOME', home), \
                 patch.object(storage_config, 'PORTABLE_FILE', marker), \
                 patch.object(storage_config, 'PORTABLE', True), \
                 patch.object(storage_config, 'DATA_DIR', src), \
                 patch.object(storage_config, 'BACKUP_DIR', home/'copias_antiguas'), \
                 patch.object(storage_config.sqlite3, 'connect', side_effect=tracked_connect):
                result = storage_config.relocate('destino', 'copias_nuevas')

            self.assertTrue(result['restart_required'])
            self.assertEqual(len(handles), 2)
            self.assertTrue(all(conn.cerrada for conn in handles),
                            'Queda una conexión SQLite abierta al terminar la migración')
            self.assertTrue((dst / 'datos' / 'evaluafp.sqlite3').is_file())
            with closing(sqlite3.connect(dst/'datos'/'evaluafp.sqlite3')) as db:
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            # El cierre del directorio temporal no debe encontrar archivos retenidos.

    def test_programming_conflict_125_percent_blocks_grade(self):
        database.init()
        with database.connect() as d:
            d.execute('INSERT INTO modules(academic_year,cycle,name,group_name,created_at) VALUES(?,?,?,?,?)',
                      ('2026-27','CFGM','Técnica Contable - evaluación','2A',database.now()))
            mid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
            d.execute('INSERT INTO students(module_id,code,name) VALUES(?,?,?)',(mid,'EVA002','Prueba Evaluación'))
            stid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
            cids=[]
            for x in range(1,6):
                d.execute('INSERT INTO outcomes(module_id,code,description,weight) VALUES(?,?,?,?)',(mid,f'RA{x}',f'Resultado {x}',20))
                ra=d.execute('SELECT last_insert_rowid()').fetchone()[0]
                d.execute('INSERT INTO criteria(outcome_id,code,description,weight) VALUES(?,?,?,?)',(ra,f'RA{x}.a','Criterio de prueba',100))
                cids.append(d.execute('SELECT last_insert_rowid()').fetchone()[0])
            evaluations=evaluacion.summary(d,mid)
            self.assertTrue(any('política' in w.lower() for w in evaluations['warnings']))
            with self.assertRaisesRegex(ValueError,'justif'):
                evaluacion.update_settings(d,{'module_id':mid,'enterprise_mode':'integrated','enterprise_weight':25,'validated':True})
            evaluacion.update_settings(d,{'module_id':mid,'enterprise_mode':'separate','enterprise_weight':25,
                        'validated':True,'teacher_note':'Revisión que no modifica los pesos RA de la programación'})
            self.assertTrue(any('125' in w for w in evaluacion.summary(d,mid)['warnings']))
            evaluacion.update_settings(d,{'module_id':mid,'enterprise_mode':'integrated','enterprise_weight':0,
                        'validated':True,'teacher_note':'La evidencia dual queda integrada en los RA; validación de prueba.'})
            uid=evaluacion.add_unit(d,{'module_id':mid,'code':'UT1','title':'Diario y mayor','term':1,'criteria_ids':[cids[1]]})
            self.assertEqual(uid,evaluacion.summary(d,mid)['units'][0]['id'])
            for x,cid in enumerate(cids,1):
                iid=evaluacion.add_instrument(d,{'module_id':mid,'title':f'Portfolio RA{x}',
                             'kind':'portfolio','term':1 if x<3 else 2,'targets':[{'criterion_id':cid,'weight':100}]})
                evaluacion.put_score(d,{'instrument_id':iid,'criterion_id':cid,'student_id':stid,'score':8,'comment':'Evaluado con rúbrica'})
            grade=evaluacion.summary(d,mid)['students'][0]
            self.assertEqual(grade['final_score'],8)
            self.assertTrue(all(x['passed'] for x in grade['outcomes']))
            with self.assertRaisesRegex(ValueError,'justificación'):
                evaluacion.close_student(d,mid,stid,'corto')
            closure=evaluacion.close_student(d,mid,stid,'Evidencias revisadas según la programación y rúbricas.')
            self.assertEqual(closure['score'],8)
            st=evaluacion.summary(d,mid,stid)['students'][0]
            self.assertTrue(st['closure']['current'])
            import eval_pdf
            payload=eval_pdf.report(d,mid,stid)
            self.assertTrue(payload.startswith(b'%PDF-'))
            first=d.execute('SELECT id,criterion_id,instrument_id FROM evaluation_scores WHERE student_id=? LIMIT 1',(stid,)).fetchone()
            evaluacion.put_score(d,{'student_id':stid,'criterion_id':first['criterion_id'],
                                  'instrument_id':first['instrument_id'],'score':7,'comment':'Revisión posterior'})
            self.assertFalse(evaluacion.summary(d,mid,stid)['students'][0]['closure']['current'])

    def test_separate_company_calculation_requires_75_plus_25(self):
        database.init()
        with database.connect() as d:
            d.execute('INSERT INTO modules(academic_year,cycle,name,group_name,created_at) VALUES(?,?,?,?,?)',
                      ('2026-27','CFGM','FE dual calculable','3C',database.now()))
            mid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
            d.execute('INSERT INTO students(module_id,code,name) VALUES(?,?,?)',(mid,'DUAL','Alumno FE'))
            st=d.execute('SELECT last_insert_rowid()').fetchone()[0]
            d.execute('INSERT INTO outcomes(module_id,code,description,weight) VALUES(?,?,?,?)',(mid,'RA1','Prueba',75))
            ra=d.execute('SELECT last_insert_rowid()').fetchone()[0]
            d.execute('INSERT INTO criteria(outcome_id,code,description,weight) VALUES(?,?,?,?)',(ra,'RA1.a','Prueba',100))
            c=d.execute('SELECT last_insert_rowid()').fetchone()[0]
            evaluacion.update_settings(d,{'module_id':mid,'enterprise_mode':'separate','enterprise_weight':25,'validated':True,
                      'teacher_note':'Ajuste formal de pesos para alcanzar 100 %'})
            i=evaluacion.add_instrument(d,{'module_id':mid,'title':'Prueba aula','kind':'examen','term':1,'targets':[{'criterion_id':c,'weight':100}]})
            evaluacion.put_score(d,{'instrument_id':i,'student_id':st,'criterion_id':c,'score':8})
            fe=evaluacion.add_instrument(d,{'module_id':mid,'title':'Informe tutor dual','kind':'empresa','term':3,
                                          'targets':[{'criterion_id':c,'weight':100}]})
            self.assertIsNone(evaluacion.summary(d,mid,st)['students'][0]['final_score'])
            evaluacion.put_score(d,{'instrument_id':fe,'student_id':st,'criterion_id':c,'score':6})
            self.assertEqual(evaluacion.summary(d,mid,st)['students'][0]['final_score'],7.5)

    def test_csv_validation_all_or_nothing(self):
        database.init()
        with database.connect() as d:
            d.execute('INSERT INTO modules(academic_year,cycle,name,group_name,created_at) VALUES(?,?,?,?,?)',
                      ('2026-27','CFGM','Importación Evaluación','X',database.now()))
            mid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
            d.execute('INSERT INTO outcomes(module_id,code,description,weight) VALUES(?,?,?,?)',(mid,'RA1','Prueba',100))
            rid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
            d.execute('INSERT INTO criteria(outcome_id,code,description,weight) VALUES(?,?,?,?)',(rid,'RA1.a','Test',100))
            cid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
            d.execute('INSERT INTO students(module_id,code,name) VALUES(?,?,?)',(mid,'AAA','Estudiante A'))
            iid=evaluacion.add_instrument(d,{'module_id':mid,'title':'Prueba de importación','term':1,
                 'kind':'externo','targets':[{'criterion_id':cid,'weight':100}]})
            with self.assertRaisesRegex(ValueError,'Fila 3'):
                evaluacion.import_csv(d,iid,b'codigo_alumno;criterio;nota;comentario\nAAA;RA1.a;8;Bien\nDESCONOCIDO;RA1.a;5;No\n')
            self.assertEqual(d.execute('SELECT COUNT(*) FROM evaluation_scores WHERE instrument_id=?',(iid,)).fetchone()[0],0)
            number=evaluacion.import_csv(d,iid,b'codigo_alumno;criterio;nota;comentario\nAAA;RA1.a;8;Bien\n')
            self.assertEqual(number,1)

if __name__=='__main__':unittest.main()