"""Regresiones de edición segura, IA autorizada, horas y temporalización."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import database
import program_builder
import program_assistant
import schedule_engine


class SmartProgrammingTests(unittest.TestCase):
    def setUp(self):
        database.init()
        with database.connect() as db:
            db.execute('INSERT INTO modules(academic_year,cycle,name,group_name,created_at) VALUES(?,?,?,?,?)',
                       ('2026-2027','CFGM Gestión Administrativa','Técnica contable','1º',database.now()))
            self.mid=db.execute('SELECT last_insert_rowid()').fetchone()[0]
            db.execute('INSERT INTO outcomes(module_id,code,description,weight) VALUES(?,?,?,?)',
                       (self.mid,'RA1','Aplica la metodología contable básica',100.0))
            self.ra=db.execute('SELECT last_insert_rowid()').fetchone()[0]
            for i in range(10):
                db.execute('INSERT INTO criteria(outcome_id,code,description,weight) VALUES(?,?,?,?)',
                    (self.ra,f'RA1.{chr(97+i)}',f'Reconoce y aplica el proceso contable {i+1}',10.0))

    def test_local_autofill_every_program_section_without_remote_call(self):
        with database.connect() as db:
            with patch.object(program_assistant.ia,'chat',side_effect=AssertionError('no IA request')):
                proposal=program_assistant.propose(db,self.mid,'Canarias','base')
            self.assertEqual(set(proposal['fields']),set(program_assistant.FIELD_TITLES))
            self.assertTrue(all(len(v)>50 for v in proposal['fields'].values()))
            self.assertIn('PENDIENTE DE COMPROBAR',proposal['fields']['normative_references'])
            self.assertIn('Plantillas locales',proposal['source'])
            self.assertEqual(proposal['hour_reference']['weekly_hours'],3)
            self.assertEqual(proposal['hour_reference']['total_hours'],96)
            self.assertEqual(proposal['hour_reference']['status'],'pendiente_de_contraste_docente')

    def test_hour_source_is_official_reference_unconfirmed_and_never_six(self):
        with database.connect() as db:
            info=program_builder.diagnose(db,self.mid)
            cfg=info['draft']['schedule']
            self.assertEqual(cfg['weekly_hours'],3)
            self.assertEqual(cfg['total_hours'],96)
            self.assertFalse(cfg['hours_confirmed'])
            self.assertTrue(cfg['hours_source_url'].startswith('https://'))
            self.assertIn('confirmadas por el docente', 'confirmadas por el docente')
        cfg=schedule_engine.defaults('2026-2027')
        self.assertEqual(cfg['weekly_hours'],0)
        self.assertFalse(schedule_engine.plan({'schedule':cfg,'units':[]})['configured'])

    def test_unknown_modules_have_no_fabricated_hours(self):
        with database.connect() as db:
            db.execute('INSERT INTO modules(academic_year,cycle,name,group_name,created_at) VALUES(?,?,?,?,?)',
                       ('2026-2027','CFGS Desarrollo de Aplicaciones','Módulo muy distinto','',database.now()))
            mid=db.execute('SELECT last_insert_rowid()').fetchone()[0]
            info=program_builder.diagnose(db,mid)
            self.assertIsNone(info['hours_reference'])
            self.assertEqual(info['draft']['schedule']['weekly_hours'],0)
            self.assertFalse(info['calendar_plan']['configured'])

    def test_propose_units_uses_96_hours_and_complete_ce_coverage(self):
        with database.connect() as db:
            cfg=program_builder.load(db,self.mid)['draft']['schedule']
            cfg['weekday_hours']=[1,0,1,0,1]
            result=program_assistant.propose_units(db,self.mid,cfg)
            self.assertEqual(len(result['units']),1)
            self.assertEqual(result['units'][0]['hours'],96)
            self.assertEqual(len(result['units'][0]['criteria_codes']),10)
            self.assertEqual(sum(u['hours'] for u in result['units']),96)

    def test_edit_metadata_preserved_and_word_export(self):
        with database.connect() as db:
            draft=program_builder.load(db,self.mid)['draft']
            draft['source_type']='create'
            draft['methodology']='Texto original del docente.'
            draft['assistant_meta']={'methodology':{'origin':'Docente','teacher_edited':True}}
            draft['schedule']['hours_confirmed']=True
            saved=program_builder.save(db,self.mid,draft)
            self.assertTrue(saved['saved'])
            loaded=program_builder.load(db,self.mid)['draft']
            self.assertEqual(loaded['methodology'],'Texto original del docente.')
            self.assertTrue(loaded['assistant_meta']['methodology']['teacher_edited'])
            md=program_builder.export(db,self.mid,'md')[0].decode('utf-8')
            self.assertIn('Texto original del docente.',md)
            self.assertIn('3,00 h',md)
            self.assertIn('Origen de las propuestas',md)

    def test_ai_generation_is_opt_in_and_does_not_invent_norms(self):
        with database.connect() as db:
            with patch.object(program_assistant.ia,'key_available',return_value=True),\
                 patch.object(program_assistant.ia,'chat') as chat:
                keys=set(program_assistant.AI_FIELDS)
                chat.return_value=({'fields':{k:'Propuesta pedagógica concreta y editable para el apartado '+k for k in keys}},'test-model')
                proposal=program_assistant.propose(db,self.mid,'Canarias','ai')
                self.assertEqual(proposal['fields']['normative_references'],
                                 program_assistant.base_fields(*program_assistant.module_context(db,self.mid)[:2],
                                                                program_assistant.module_context(db,self.mid)[2],region='Canarias')['normative_references'])
                prompt=json.loads(chat.call_args.args[1]);self.assertNotIn('centro',prompt)
                self.assertTrue(all(k in proposal['fields'] for k in program_assistant.FIELD_TITLES))

    def test_polish_requires_authorisation_and_rejects_lost_percentages(self):
        with database.connect() as db:
            with self.assertRaisesRegex(ValueError,'Autorice'):
                program_assistant.improve_text(db,self.mid,'assessment','Peso 30 % para RA1',False)
            with patch.object(program_assistant.ia,'key_available',return_value=True),\
                 patch.object(program_assistant.ia,'chat',return_value=({'text':'Texto corregido sin el dato'},'modelo')):
                with self.assertRaisesRegex(ValueError,'omitir'):
                    program_assistant.improve_text(db,self.mid,'assessment','Peso 30 % para RA1',True)
            with patch.object(program_assistant.ia,'key_available',return_value=True),\
                 patch.object(program_assistant.ia,'chat',return_value=({'text':'Redacción profesional: Peso 30 % para RA1.'},'modelo')):
                result=program_assistant.improve_text(db,self.mid,'assessment','Peso 30 % para RA1',True)
            self.assertEqual(result['original'],'Peso 30 % para RA1')
            self.assertTrue(result['requires_acceptance'])

    def test_non_canarian_calendar_does_not_invent_local_festivals(self):
        cfg=schedule_engine.defaults('2026-2027')
        cfg.update(region='Andalucía',weekly_hours=3,total_hours=96,weekday_hours=[1,0,1,0,1])
        report=schedule_engine.plan({'schedule':cfg,'units':[]})
        self.assertFalse(report['configured'])  # Cambio de territorio: se invalidan las fechas de Canarias
        self.assertFalse(any(x['date']=='2026-09-21' for x in report.get('non_teaching',[])))


if __name__=='__main__':unittest.main()

class ProgrammingWeightsTests(unittest.TestCase):
    """El reparto nunca pierde CE ni altera cierres de notas sin supervisión."""
    def setUp(self):
        database.init()
        with database.connect() as db:
            db.execute('INSERT INTO modules(academic_year,cycle,name,group_name,created_at) VALUES(?,?,?,?,?)',
                       ('2026-2027','CFGS Administración y Finanzas','Módulo ensayo pesos','',database.now()))
            self.mid=db.execute('SELECT last_insert_rowid()').fetchone()[0]
            self.rows=[]
            for x,qty in [(1,2),(2,3)]:
                db.execute('INSERT INTO outcomes(module_id,code,description,weight) VALUES(?,?,?,?)',
                           (self.mid,f'RA{x}',f'Resultado {x}',None))
                rid=db.execute('SELECT last_insert_rowid()').fetchone()[0]
                ce=[]
                for n in range(qty):
                    db.execute('INSERT INTO criteria(outcome_id,code,description,weight) VALUES(?,?,?,?)',
                               (rid,f'RA{x}.{chr(97+n)}','Criterio',None))
                    ce.append(db.execute('SELECT last_insert_rowid()').fetchone()[0])
                self.rows.append((rid,ce))

    def _manual_rows(self):
        a,b=self.rows
        return [{'id':a[0],'weight':40.00,'criteria':[{'id':x,'weight':50.00} for x in a[1]]},
                {'id':b[0],'weight':60.00,'criteria':[{'id':x,'weight':v} for x,v in zip(b[1],[33.33,33.33,33.34])]}]

    def test_manual_weights_valid_cents(self):
        with database.connect() as db:
            result=program_assistant.update_weights(db,self.mid,'manual',self._manual_rows(),True)
            self.assertTrue(result['saved'])
            self.assertEqual([x['weight'] for x in db.execute('SELECT weight FROM outcomes WHERE module_id=? ORDER BY id',(self.mid,))],[40,60])
            self.assertEqual(sum(r['weight'] for r in db.execute('SELECT c.weight FROM criteria c JOIN outcomes o ON o.id=c.outcome_id WHERE o.module_id=?',(self.mid,))),200)
            info=program_builder.diagnose(db,self.mid)
            self.assertTrue(all(r['weight_origin']=='manual' for r in info['outcomes']))
            self.assertTrue(all(c['weight_origin']=='manual' for c in info['criteria']))

    def test_cannot_skip_or_duplicate_criteria(self):
        with database.connect() as db:
            rows=self._manual_rows()
            rows[0]['criteria'].pop()
            with self.assertRaises(ValueError):program_assistant.update_weights(db,self.mid,'manual',rows,True)
            rows=self._manual_rows()
            rows[1]['criteria'][0]['id']=rows[0]['criteria'][0]['id']
            with self.assertRaises(ValueError):program_assistant.update_weights(db,self.mid,'manual',rows,True)

    def test_refuses_incorrect_total_percent(self):
        with database.connect() as db:
            rows=self._manual_rows()
            rows[0]['weight']=41
            with self.assertRaisesRegex(ValueError,'RA suman'):program_assistant.update_weights(db,self.mid,'manual',rows,True)
            rows=self._manual_rows()
            rows[1]['criteria'][2]['weight']=33.33
            with self.assertRaisesRegex(ValueError,'CE de'):program_assistant.update_weights(db,self.mid,'manual',rows,True)
            self.assertTrue(all(r['weight'] is None for r in db.execute('SELECT weight FROM outcomes WHERE module_id=?',(self.mid,))))

    def test_switch_automatic_uses_criteria_count(self):
        with database.connect() as db:
            program_assistant.update_weights(db,self.mid,'manual',self._manual_rows(),True)
            program_assistant.update_weights(db,self.mid,'automatic',teacher_confirmed=True)
            info=program_builder.diagnose(db,self.mid)
            self.assertEqual([r['weight'] for r in info['outcomes']],[40.,60.])
            self.assertEqual([c['weight'] for c in info['criteria']],[50.,50.,33.34,33.33,33.33])
            self.assertTrue(all(r['weight_origin']=='default' for r in info['outcomes']))

    def test_cannot_change_without_teacher_confirmation(self):
        with database.connect() as db:
            with self.assertRaisesRegex(ValueError,'confirmar'):
                program_assistant.update_weights(db,self.mid,'automatic',teacher_confirmed=False)

    def test_cannot_change_with_existing_final_closure(self):
        with database.connect() as db:
            # Cierre real asociado a un alumno de ensayo.
            db.execute('INSERT INTO students(module_id,code,name) VALUES(?,?,?)',(self.mid,'EJ01','Alumno ficticio'))
            student_id=db.execute('SELECT last_insert_rowid()').fetchone()[0]
            db.execute('''INSERT INTO evaluation_closures(module_id,student_id,score,teacher_justification,evidence_sha256,snapshot_json,validated_at)
                          VALUES(?,?,?,?,?,?,?)''', (self.mid,student_id,7.0,'Cierre de prueba','a'*64,'{}',database.now()))
            with self.assertRaisesRegex(ValueError,'cerradas'):
                program_assistant.update_weights(db,self.mid,'automatic',teacher_confirmed=True)
            db.execute('DELETE FROM evaluation_closures WHERE module_id=?',(self.mid,))

class UnitAIAssistanceTests(unittest.TestCase):
    def setUp(self):
        database.init()
        with database.connect() as db:
            db.execute('INSERT INTO modules(academic_year,cycle,name,group_name,created_at) VALUES(?,?,?,?,?)',
                       ('2026-2027','CFGM Gestión Administrativa','Técnica contable','',database.now()))
            self.mid=db.execute('SELECT last_insert_rowid()').fetchone()[0]
            db.execute('INSERT INTO outcomes(module_id,code,description,weight) VALUES(?,?,?,?)',(self.mid,'RA1','Contabiliza operaciones',100))
            rid=db.execute('SELECT last_insert_rowid()').fetchone()[0]
            db.execute('INSERT INTO criteria(outcome_id,code,description,weight) VALUES(?,?,?,?)',(rid,'RA1.a','Identifica datos contables',100))
            self.units=[{'code':'UD01','title':'Operaciones contables','criteria_codes':['RA1.a'],'hours':10,'term':1}]

    def test_unit_ai_requires_opt_in(self):
        with database.connect() as db:
            with self.assertRaisesRegex(ValueError,'autorizar'):
                program_assistant.enrich_unit_details(db,self.mid,self.units,False)

    def test_unit_ai_rejects_changed_code_or_missing_unit(self):
        with database.connect() as db:
            with patch.object(program_assistant.ia,'key_available',return_value=True),\
                 patch.object(program_assistant.ia,'chat',return_value=({'units':[{'code':'UD02','instruments':'Prueba práctica contextualizada con rúbrica clara','resources':'Aula digital, casos y materiales adaptados a las competencias'}]},'modelo')):
                with self.assertRaisesRegex(ValueError,'cambiado'):
                    program_assistant.enrich_unit_details(db,self.mid,self.units,True)

    def test_unit_ai_returns_teacher_review_without_mutation(self):
        with database.connect() as db:
            mock={'units':[{'code':'UD01','instruments':'Prueba práctica contextualizada con rúbrica y observación','resources':'Supuestos profesionales simulados, guía y hoja de cálculo'}]}
            with patch.object(program_assistant.ia,'key_available',return_value=True),\
                 patch.object(program_assistant.ia,'chat',return_value=(mock,'modelo')):
                result=program_assistant.enrich_unit_details(db,self.mid,self.units,True)
            self.assertTrue(result['requires_acceptance'])
            self.assertEqual(result['units'][0]['code'],'UD01')
            self.assertNotIn('hours',result['units'][0])

class SmartProgrammingHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app
        cls.app=app
        cls.server,cls.base=app.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close()

    def api(self,path,body=None):
        import urllib.request
        payload=None if body is None else json.dumps(body).encode('utf-8')
        request=urllib.request.Request(self.base+path,data=payload,headers={
            'X-App-Token':self.app.TOKEN,'Content-Type':'application/json'},
            method='GET' if body is None else 'POST')
        with urllib.request.urlopen(request,timeout=12) as stream:
            return json.loads(stream.read().decode('utf-8'))

    def test_proposals_hours_and_ai_consent_http(self):
        import urllib.error
        module=self.api('api/modules',{'academic_year':'2026-2027','cycle':'CFGM Gestión Administrativa',
                                      'name':'Técnica contable','group_name':'HTTP'})
        mid=module['id']
        ref=self.api(f'api/programming-builder/{mid}/hours-reference')
        self.assertEqual(ref['proposal']['weekly_hours'],3)
        result=self.api('api/programming-builder/propose',{'module_id':mid,'region':'Canarias','mode':'base'})
        self.assertEqual(len(result['fields']),len(program_assistant.FIELD_TITLES))
        with self.assertRaises(urllib.error.HTTPError) as err:
            self.api('api/programming-builder/propose',{'module_id':mid,'region':'Canarias','mode':'ai'})
        self.assertEqual(err.exception.code,400)
        with self.assertRaises(urllib.error.HTTPError) as err:
            self.api('api/programming-builder/enrich-units',{'module_id':mid,'units':[],'authorize_ai':False})
        self.assertEqual(err.exception.code,400)
