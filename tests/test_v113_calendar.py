"""Pruebas de la nueva temporalización: horario real, festivos, CE FEOE, Gantt."""
import io
import json
import unittest
import zipfile
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import schedule_engine as sch

class CalendarTests(unittest.TestCase):
    def config(self):
        c=sch.defaults('2026-2027')
        c.update(weekly_hours=6,total_hours=202,weekday_hours=[2,0,2,0,2],
                 municipality='Guía de Isora',island='Tenerife')
        return c
    def draft(self):
        return {'schedule':self.config(),'units':[
            {'code':'UD1','title':'Documentos','term':1,'hours':70,'criteria_codes':['RA1.a']},
            {'code':'UD2','title':'Asientos','term':2,'hours':60,'criteria_codes':['RA2.a']},
            {'code':'UD3','title':'Balances','term':3,'hours':72,'criteria_codes':['RA3.a']}]}
    def test_official_calendar_and_local_holidays_are_excluded(self):
        c=self.config()
        x=sch.plan(self.draft(),[{'code':'RA1.a'},{'code':'RA2.a'},{'code':'RA3.a'}])
        excluded={row['date'] for row in x['non_teaching']}
        for day in ['2026-09-21','2026-10-12','2026-11-02','2026-12-07','2026-12-08','2027-02-02','2027-03-25']:
            self.assertIn(day,excluded)
        self.assertEqual(x['terms'][0]['start'],'2026-09-16')
        self.assertEqual(x['terms'][1]['start'],'2027-01-11')  # Calendario corregido: Navidad hasta el 08/01 inclusive
        self.assertEqual(x['terms'][2]['start'],'2027-03-29')
        self.assertAlmostEqual(x['capacity'],210.0)  # Descontar también el viernes 8 de enero
    def test_weekday_specific_schedule_makes_holiday_loss_accurate(self):
        d=self.draft()
        d['schedule']['weekday_hours']=[2,0,2,0,2]
        precise=sch.plan(d)['capacity']
        d['schedule']['weekday_hours']=[0,3,0,3,0]
        alternative=sch.plan(d)['capacity']
        self.assertNotEqual(precise,alternative)
        d['schedule']['weekday_hours']=[0,0,0,0,0]
        estimate=sch.plan(d)
        self.assertTrue(any('prorratean' in x for x in estimate['warnings']))
    def test_term_overload_does_not_steal_hours_from_another_term(self):
        d=self.draft();d['units'][1]['hours']=100
        x=sch.plan(d)
        self.assertTrue(any('2.ª evaluación' in w or 'Evaluación 2' in w for w in x['warnings']))
        self.assertGreater(x['units'][1]['unscheduled_hours'],0)
        self.assertEqual(x['units'][2]['term'],3)
    def test_feoe_is_percentage_of_codes_and_not_an_extra_grade(self):
        d=self.draft()
        ce=[{'code':'RA1.'+chr(97+i)} for i in range(10)]
        d['schedule']['feoe_criteria_codes']=['RA1.a','RA1.b']
        d['schedule']['feoe_start']='2027-03-08';d['schedule']['feoe_end']='2027-05-28'
        x=sch.plan(d,ce)
        self.assertEqual(x['feoe']['percent'],20.0)
        self.assertEqual(x['feoe']['recommended_min'],1)
        self.assertEqual(x['feoe']['recommended_max'],2)
        self.assertTrue(any('No se han descontado horas' in w for w in x['warnings']))
        d['schedule']['feoe_center_hours_weekly']=2
        y=sch.plan(d,ce)
        self.assertLess(y['capacity'],x['capacity'])
        self.assertNotIn('calificaciones',json.dumps(y))
    def test_unsatisfiable_ce_10_20_range_explicit_warning(self):
        d=self.draft();d['schedule']['feoe_criteria_codes']=['RA1.a']
        x=sch.plan(d,[{'code':'RA1.a'},{'code':'RA1.b'},{'code':'RA1.c'}])
        self.assertTrue(any('no hay un número entero' in w for w in x['warnings']))
    def test_free_disposition_days_and_sundays_excluded(self):
        d=self.draft();a=sch.plan(d)['capacity']
        d['schedule']['extra_non_teaching_days']=['2027-01-11','2027-01-11','2027-01-17']
        b=sch.plan(d)['capacity']
        self.assertAlmostEqual(a-b,2.0)
    def test_reject_inconsistent_weekly_distribution_and_invalid_dates(self):
        c=self.config();c['weekday_hours']=[1,1,1,1,1]
        with self.assertRaisesRegex(ValueError,'sumar'):
            sch.clean(c)
        c=self.config();c['start_date']='2026-09-39'
        with self.assertRaisesRegex(ValueError,'fecha válida'):
            sch.clean(c)
    def test_activity_and_gantt_export_integrated(self):
        import database as data
        import program_builder
        data.init()
        with data.connect() as db:
            db.execute('INSERT INTO modules(academic_year,cycle,name,group_name,created_at) VALUES(?,?,?,?,?)',
                       ('2026-2027','CFGS Administración y Finanzas','Módulo pruebas calendario','1 A',data.now()))
            mid=db.execute('SELECT last_insert_rowid()').fetchone()[0]
            db.execute('INSERT INTO outcomes(module_id,code,description,weight) VALUES(?,?,?,?)',
                       (mid,'RA1','Resuelve el proceso profesional',100))
            ra=db.execute('SELECT last_insert_rowid()').fetchone()[0]
            db.execute('INSERT INTO criteria(outcome_id,code,description,weight) VALUES(?,?,?,?)',
                       (ra,'RA1.a','Elabora los documentos con rigor',100))
            draft={'source_type':'create','region':'Canarias',**self.draft(),
                   'activities':[{'type':'complementaria','title':'Visita a empresa (propuesta)',
                                  'date':'','unit_code':'UD1','description':'Conocer el proceso de gestión','resources':'Autorizaciones'}]}
            self.assertTrue(program_builder.save(db,mid,draft)['saved'])
            info=program_builder.diagnose(db,mid)
            self.assertTrue(info['calendar_plan']['configured'])
            self.assertEqual(info['draft']['schedule']['weekly_hours'],6)
            md=program_builder.export(db,mid,'md')[0].decode()
            self.assertIn('Temporalización y calendario escolar',md)
            self.assertIn('Instrumentos y recursos por unidad',md)
            pdf=program_builder.export(db,mid,'pdf')[0]
            self.assertTrue(pdf.startswith(b'%PDF-'))
            import fitz
            p=fitz.open(stream=pdf,filetype='pdf')
            text=' '.join(page.get_text() for page in p)
            self.assertIn('Índice de contenidos',text)
            self.assertIn('Diagrama de Gantt',text)
            self.assertIn('2026-09-16',text)
            w=program_builder.export(db,mid,'docx')[0]
            with zipfile.ZipFile(io.BytesIO(w)) as z:
                self.assertIn('word/document.xml',z.namelist())
                xml=z.read('word/document.xml').decode()
                self.assertIn('Índice de contenidos',xml)
                self.assertIn('Diagrama de Gantt',xml)
if __name__=='__main__':unittest.main()
