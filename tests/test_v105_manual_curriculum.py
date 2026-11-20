"""v1.0.5: propuesta autónoma, verificación curricular y ponderación plural de CE."""
from __future__ import annotations
import io
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import manual_alignment
import curriculum_official
import database
import app


def mock_db():
    db=sqlite3.connect(':memory:')
    db.row_factory=sqlite3.Row
    db.executescript('''CREATE TABLE outcomes (id INTEGER PRIMARY KEY,module_id INTEGER,code TEXT,description TEXT,weight REAL);
    CREATE TABLE criteria (id INTEGER PRIMARY KEY,outcome_id INTEGER,code TEXT,description TEXT,weight REAL);
    INSERT INTO outcomes VALUES (1,19,'RA2','Reconoce la metodología contable y los instrumentos contables.',20);
    INSERT INTO criteria VALUES (21,1,'RA2.a','Identifica las fases y los registros del ciclo contable.',50);
    INSERT INTO criteria VALUES (22,1,'RA2.b','Reconoce el método de partida doble en operaciones contables.',50);''')
    return db

class ManualCurriculumTests(unittest.TestCase):
    def test_automatic_allocation_of_two_ce_with_evidence(self):
        d=mock_db()
        response={'assignments':[{'number':1,'status':'proposed','criteria':[
          {'criterion_id':21,'weight_pct':60,'confidence':.94,'rationale':'Se pide ordenar fases del ciclo'},
          {'criterion_id':22,'weight_pct':40,'confidence':.91,'rationale':'Se contabiliza mediante partida doble'}]}],
          'warnings':[]}
        with patch.object(manual_alignment.ia,'chat',return_value=(response,'modelo-prueba')):
            result=manual_alignment.suggest(d,19,[{'kind':'problema','prompt':'Identifique las fases del ciclo y realice el asiento con partida doble para una venta', 'points':10}])
        self.assertEqual(result['needs_review'],0)
        self.assertEqual({a['criterion_id']:a['weight_pct'] for a in result['assignments'][0]['criteria']},{21:60,22:40})
        self.assertEqual(result['assignments'][0]['criteria'][0]['ra_code'],'RA2')
        d.close()

    def test_rejects_nonexistent_criteria_from_ai(self):
        d=mock_db()
        with patch.object(manual_alignment.ia,'chat',return_value=(
            {'assignments':[{'number':1,'criteria':[{'criterion_id':999,'weight_pct':100,'confidence':1}]}]},'simulado')):
            r=manual_alignment.suggest(d,19,[{'prompt':'Explique las fases de un ejercicio contable'}])
        self.assertEqual(r['needs_review'],1)
        self.assertEqual(r['assignments'][0]['criteria'],[])
        d.close()

    def test_non_applicable_low_confidence_stays_pending(self):
        d=mock_db()
        with patch.object(manual_alignment.ia,'chat',return_value=(
            {'assignments':[{'number':1,'criteria':[{'criterion_id':21,'weight_pct':100,'confidence':.40}]}]},'simulado')):
            r=manual_alignment.suggest(d,19,[{'prompt':'Determine el procedimiento de gestión de inventarios digitales'}])
        self.assertEqual(r['needs_review'],1)
        d.close()

    def test_allocation_rejects_wrong_module_and_sum(self):
        d=mock_db();allowed={c['criterion_id']:c for c in manual_alignment.catalogue(d,19)}
        for targets in ([{'criterion_id':21,'weight_pct':30}],
                        [{'criterion_id':21,'weight_pct':50},{'criterion_id':21,'weight_pct':50}],
                        [{'criterion_id':99,'weight_pct':100}]):
            with self.assertRaises(ValueError):
                manual_alignment.validate_allocations({'criteria_allocations':targets},allowed)
        d.close()

    def test_legacy_question_assignment_is_preserved(self):
        d=mock_db();allowed={c['criterion_id']:c for c in manual_alignment.catalogue(d,19)}
        self.assertEqual(manual_alignment.validate_allocations({'criterion_id':21},allowed)[0]['weight_pct'],100)
        d.close()

    def test_official_law_parser_extracts_only_literal_criteria(self):
        html='''<html><body><h2>Módulo Profesional: Técnica Contable. Código: 0441</h2>
        <p>Resultados de aprendizaje y criterios de evaluación</p>
        <p>1. Reconoce la estructura de las masas patrimoniales de una organización.</p>
        <p>Criterios de evaluación:</p>
        <p>a) Se ha identificado el patrimonio empresarial en el ejercicio.</p>
        <p>b) Se han agrupado los elementos según su naturaleza.</p>
        <p>c) Se han clasificado las partidas en activo y pasivo.</p>
        <p>d) Se ha determinado la masa patrimonial de cada elemento.</p>
        <p>2. Clasifica los hechos económicos según sus efectos en el patrimonio.</p>
        <p>Criterios de evaluación:</p>
        <p>a) Se han identificado los hechos económicos básicos.</p>
        <p>b) Se han asentado operaciones conforme a la partida doble.</p>
        <p>c) Se han identificado las cuentas de operaciones comerciales.</p>
        <p>d) Se han relacionado cobros y pagos con derechos y obligaciones.</p>
        <h2>Módulo Profesional: Inglés. Código: 0444</h2>
        <p>1. Este texto no pertenece al módulo buscado.</p></body></html>'''
        result=curriculum_official.parse_curriculum(html,'Técnica Contable','0441')
        self.assertEqual([x['code'] for x in result['outcomes']],['RA1','RA2'])
        self.assertEqual(len(result['outcomes'][0]['criteria']),4)
        self.assertIsNone(result['outcomes'][1]['criteria'][0]['weight'])
        self.assertNotIn('Inglés',str(result))

    def test_official_url_restricted_and_consent_required(self):
        with self.assertRaises(ValueError):curriculum_official.fetch_official('Técnica Contable',consent=False)
        with self.assertRaises(ValueError):curriculum_official.fetch_official('Técnica Contable',boe_id='https://evil.example/redirect',consent=True)

    def test_weighted_gradebook_does_not_duplicate_question_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(database,'DB_FILE',Path(tmp)/'notas.sqlite'):
                database.init()
                with database.connect() as d:
                    d.execute("INSERT INTO modules(id,academic_year,cycle,name,created_at) VALUES(1,'2026-2027','GM','Técnica Contable','hoy')")
                    d.execute("INSERT INTO outcomes(id,module_id,code,description) VALUES(1,1,'RA2','Metodología contable')")
                    for cid,code in [(21,'RA2.a'),(22,'RA2.b')]:
                        d.execute('INSERT INTO criteria(id,outcome_id,code,description) VALUES(?,1,?,?)',(cid,code,code))
                    d.execute("INSERT INTO students(id,module_id,code,name) VALUES(1,1,'A001','Alumno de prueba')")
                    d.execute("INSERT INTO exams(id,module_id,title,kind,total_points,created_at) VALUES(1,1,'Examen','manual',10,'hoy')")
                    d.execute("INSERT INTO exam_questions(id,exam_id,criterion_id,number,kind,prompt,points) VALUES(1,1,21,1,'problema','Realiza el asiento y analiza el ciclo contable',10)")
                    d.execute('DELETE FROM exam_question_criteria WHERE question_id=1')
                    d.executemany('INSERT INTO exam_question_criteria(question_id,criterion_id,weight_pct,rationale) VALUES(1,?,?,?)',
                                  [(21,60,'Fases'),(22,40,'Asiento')])
                    d.execute("INSERT INTO submissions(id,exam_id,student_id,storage_path,status,created_at,current_run_id) VALUES(1,1,1,'/tmp/sub','validated','hoy',1)")
                    d.execute("INSERT INTO transcription_runs(id,submission_id,model,created_at) VALUES(1,1,'simulado','hoy')")
                    d.execute("INSERT INTO corrections(id,run_id,submission_id,question_id,transcription,page_numbers_json,teacher_score,status,created_at) VALUES(1,1,1,1,'Asiento','[]',8,'validated','hoy')")
                    book=app.gradebook(d)
                    by={x['criterion_code']:x for x in book['criteria']}
                    self.assertEqual(book['exams'][0]['out_of_ten'],8)
                    self.assertEqual(by['RA2.a']['scored'],4.8)
                    self.assertEqual(by['RA2.b']['scored'],3.2)
                    self.assertAlmostEqual(sum(x['scored'] for x in by.values()),8)
                database.init()
                with database.connect() as d:
                    vals=d.execute('SELECT criterion_id,weight_pct FROM exam_question_criteria WHERE question_id=1 ORDER BY criterion_id').fetchall()
                    self.assertEqual([(x['criterion_id'],x['weight_pct']) for x in vals],[(21,60),(22,40)])

    def test_db_migration_backfills_single_criterion(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'prueba.sqlite'
            with patch.object(database,'DB_FILE',path):
                database.init()
                with database.connect() as d:
                    d.execute("INSERT INTO modules(id,academic_year,cycle,name,created_at) VALUES(1,'2026-2027','GM','Prueba','hoy')")
                    d.execute("INSERT INTO outcomes(id,module_id,code,description) VALUES(1,1,'RA1','RA descripción')")
                    d.execute("INSERT INTO criteria(id,outcome_id,code,description) VALUES(21,1,'RA1.a','CE descripción')")
                    d.execute("INSERT INTO exams(id,module_id,title,kind,total_points,created_at) VALUES(1,1,'Prueba','manual',10,'hoy')")
                    d.execute("INSERT INTO exam_questions(id,exam_id,criterion_id,number,kind,prompt,points) VALUES(1,1,21,1,'test','Pregunta',10)")
                database.init()
                with database.connect() as d:
                    row=d.execute('SELECT * FROM exam_question_criteria WHERE question_id=1').fetchone()
                    self.assertEqual(row['criterion_id'],21)
                    self.assertEqual(row['weight_pct'],100)

if __name__ == '__main__': unittest.main()
