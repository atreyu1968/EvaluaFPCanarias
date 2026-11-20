"""Regression for explicit Gantt scale, two decimals and tabular exports."""
import io
import re
import sys
import unittest
import zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import schedule_engine
import program_export_v113 as exports
from program_builder import _display_2

class GanttClarityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        conf=schedule_engine.defaults('2026-2027')
        conf.update(weekly_hours=6,total_hours=202,weekday_hours=[2,0,2,0,2])
        units=[{'code':'UD1','title':'Patrimonio y actividad comercial','term':1,'hours':65.0,'criteria_codes':['RA1.a']},
               {'code':'UD2','title':'Operaciones comerciales','term':2,'hours':65.0,'criteria_codes':['RA2.a']},
               {'code':'UD3','title':'Tesorería y procesos','term':3,'hours':72.0,'criteria_codes':['RA3.a']}]
        plan=schedule_engine.plan({'schedule':conf,'units':units})
        cls.result={'module':{'name':'Módulo de pruebas','cycle':'FP de Grado Superior','academic_year':'2026-2027'},
                    'draft':{'center':'Centro ficticio','teacher':'Profesor/a de pruebas'},'calendar_plan':plan}
        cls.sections=[('Temporalización y calendario escolar',[
            ('Horas semanales','6,00 h'),('Horas previstas','202,00 h')]),
            ('Instrumentos y recursos por unidad',[('UD1','Rúbrica y prueba práctica')])]

    def test_numeric_format_has_two_decimals_without_calculation_change(self):
        self.assertEqual(_display_2(6),'6,00')
        self.assertEqual(_display_2(12.345),'12,35')
        self.assertEqual(_display_2(None),'Pendiente')

    def test_pdf_landscape_gantt_month_and_week_date_headers(self):
        import fitz
        blob,mime,_=exports.export(self.result,self.sections,1,'pdf')
        pdf=fitz.open(stream=blob,filetype='pdf')
        last=pdf[-1]
        self.assertGreater(last.rect.width,1100)
        text=last.get_text()
        for mark in ['Septiembre 2026','Enero 2027','14/09','20/09',
                     'Horas (h)','65,00 h','MESES Y AÑOS','SEMANAS NATURALES']:
            self.assertIn(mark,text)
        self.assertNotRegex(text,r'14/0\s+9')

    def test_word_month_year_and_horizontal_gantt(self):
        blob,mime,_=exports.export(self.result,self.sections,1,'docx')
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            xml=z.read('word/document.xml').decode('utf8')
        self.assertIn('09/2026',xml)
        self.assertIn('01/2027',xml)
        self.assertIn('65,00 h',xml)
        self.assertIn('w:orient="landscape"',xml)
        self.assertIn('Concepto / unidad / RA-CE',xml)

    def test_ui_explains_month_and_day_axis(self):
        js=(Path(__file__).resolve().parents[1]/'web/app.js').read_text(encoding='utf-8')
        self.assertIn('Cómo leer el encabezado',js)
        self.assertIn('mes y año',js)
        self.assertIn('una semana natural',js)
        self.assertIn('fmtSchoolNumber',js)
        self.assertIn('monthGroups',js)

if __name__=='__main__':unittest.main()
