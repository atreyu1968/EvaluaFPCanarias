"""Regresiones del documento FEOE autónomo: no inventar CE ni aceptar IA errónea."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import database
import feoe_minimum
import program_builder


class FeoeMinimumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): database.init()

    def setUp(self):
        with database.connect() as db:
            db.execute('INSERT INTO modules(academic_year,cycle,name,group_name,created_at) VALUES(?,?,?,?,?)',
                       ('2026-2027','CFGS Administración y Finanzas','Módulo de prueba FEOE','Grupo',database.now()))
            self.mid=db.execute('SELECT last_insert_rowid()').fetchone()[0]
            for i in range(2):
                db.execute('INSERT INTO outcomes(module_id,code,description,weight) VALUES(?,?,?,?)',
                           (self.mid,f'RA{i+1}',f'Resultado de aprendizaje {i+1}',50))
                ra=db.execute('SELECT last_insert_rowid()').fetchone()[0]
                for j in range(5):
                    label=f'RA{i+1}.{chr(97+j)}'
                    detail=('Se han identificado documentos y datos habituales del trabajo.' if j<4 else
                            'Se han realizado trabajos en altura con maquinaria especializada.')
                    db.execute('INSERT INTO criteria(outcome_id,code,description,weight) VALUES(?,?,?,?)',
                               (ra,label,detail,20))

    def test_proposes_minimum_local_no_ai_and_official_only(self):
        with database.connect() as db:
            with patch.object(feoe_minimum.ia,'chat',side_effect=AssertionError('should never call AI')):
                p=feoe_minimum.propose(db,self.mid)
        self.assertEqual(p['count'],2)
        self.assertEqual(p['percentage'],20.0)
        self.assertEqual(len({x['criteria_code'] for x in p['rows']}),2)
        self.assertFalse(p['approved'])
        self.assertTrue(all(x['ra_code'] in ('RA1','RA2') for x in p['rows']))
        self.assertTrue(all(x['evidence'] and x['activity'] and x['support'] for x in p['rows']))

    def test_selected_criteria_respected_and_teacher_changes_persist(self):
        with database.connect() as db:
            p=feoe_minimum.propose(db,self.mid)
            p['rows'][0]['activity']='El alumno realizará una verificación sencilla de información de ejemplo.'
            saved=feoe_minimum.accept(db,self.mid,p['rows'])
            new=feoe_minimum.propose(db,self.mid)
        self.assertEqual(new['rows'][0]['activity'],p['rows'][0]['activity'])
        self.assertEqual(saved['criteria_codes'],[r['criteria_code'] for r in p['rows']])

    def test_rejects_unknown_duplicate_and_empty_activities(self):
        with database.connect() as db:
            sample=feoe_minimum.propose(db,self.mid)['rows']
            with self.assertRaisesRegex(ValueError,'no confirmado'):
                feoe_minimum.accept(db,self.mid,[dict(sample[0],criteria_code='RA99.a')])
            with self.assertRaisesRegex(ValueError,'repetir'):
                feoe_minimum.accept(db,self.mid,[sample[0],sample[0]])
            with self.assertRaisesRegex(ValueError,'Revise'):
                feoe_minimum.accept(db,self.mid,[dict(sample[0],activity='Vacío')])

    def test_ai_requires_consent_and_api_key(self):
        with database.connect() as db:
            with self.assertRaisesRegex(ValueError,'Autorice'):
                feoe_minimum.propose(db,self.mid,'ai',False)
            with patch.object(feoe_minimum.ia,'key_available',return_value=False):
                with self.assertRaisesRegex(ValueError,'API'):
                    feoe_minimum.propose(db,self.mid,'ai',True)

    def test_ai_rejects_extra_and_missing_codes(self):
        with database.connect() as db:
            with patch.object(feoe_minimum.ia,'key_available',return_value=True),patch.object(feoe_minimum.ia,'chat',return_value=({'rows':[{'criteria_code':'inventado','activity':'Actividad de ejemplo larga','evidence':'Evidencia validable sencilla','support':'Instrucciones sencillas para todos'}]},'mock')):
                with self.assertRaisesRegex(ValueError,'inválida'):
                    feoe_minimum.propose(db,self.mid,'ai',True)

    def test_ai_proposes_valid_rows_and_does_not_auto_save(self):
        with database.connect() as db:
            p=feoe_minimum.propose(db,self.mid)
            candidates=[{'criteria_code':r['criteria_code'],'activity':'Clasificar un documento de ejemplo bajo supervisión.',
              'evidence':'Una lista comprobada junto al tutor.',
              'support':'Explicación y práctica guiadas con opciones.'} for r in p['rows']]
            with patch.object(feoe_minimum.ia,'key_available',return_value=True),patch.object(feoe_minimum.ia,'chat',return_value=({'rows':candidates},'simulado')):
                result=feoe_minimum.propose(db,self.mid,'ai',True)
            self.assertIn('IA',result['source'])
            self.assertIn('Clasificar',result['rows'][0]['activity'])
            self.assertEqual(program_builder.load(db,self.mid)['draft']['feoe_tasks'],[])

    def test_ai_may_select_better_criteria_without_overwriting_teacher_choice(self):
        with database.connect() as db:
            local=feoe_minimum.propose(db,self.mid)
            alternative='RA1.c' if 'RA1.c' not in {x['criteria_code'] for x in local['rows']} else 'RA1.d'
            chosen=['RA2.a',alternative]
            candidates=[{'criteria_code':code,'activity':'Identificar y ordenar información cotidiana del trabajo.',
              'evidence':'Lista de comprobación y explicación oral del alumno.',
              'support':'Se permite ayuda inicial, modelos y práctica guiada.'} for code in chosen]
            with patch.object(feoe_minimum.ia,'key_available',return_value=True),patch.object(feoe_minimum.ia,'chat',return_value=({'rows':candidates},'mock')):
                result=feoe_minimum.propose(db,self.mid,'ai',True)
            self.assertEqual({r['criteria_code'] for r in result['rows']},set(chosen))
            self.assertIn('CE propuestos por IA',result['selection'])
            self.assertEqual(program_builder.load(db,self.mid)['draft']['schedule']['feoe_criteria_codes'],[])

    def test_exports_independent_docx_pdf_md(self):
        with database.connect() as db:
            for ext,header in (('docx',b'PK'),('pdf',b'%PDF-'),('md',b'# PROGRAMA')):
                content,mime,name=feoe_minimum.export(db,self.mid,ext)
                self.assertTrue(content.startswith(header))
                self.assertGreater(len(content),150)
                self.assertIn('Programa_Minimo_Empresa_',name)
            docx=feoe_minimum.export(db,self.mid,'docx')[0]
            from docx import Document
            import io
            doc=Document(io.BytesIO(docx))
            self.assertTrue(any('PROGRAMA FORMATIVO' in p.text for p in doc.paragraphs))
            self.assertTrue(any('RA1.' in row.cells[0].text for table in doc.tables for row in table.rows))

    def test_specialized_ce_is_labeled_if_selected(self):
        with database.connect() as db:
            draft=program_builder.load(db,self.mid)['draft']
            draft['schedule']['feoe_criteria_codes']=['RA1.e']
            program_builder.save(db,self.mid,draft)
            result=feoe_minimum.propose(db,self.mid)
            self.assertEqual(result['rows'][0]['criteria_code'],'RA1.e')
            self.assertEqual(result['rows'][0]['fit'],'Necesita entorno/tarea específica')
            self.assertTrue(any('entorno' in w for w in result['warnings']))


if __name__=='__main__':unittest.main()
