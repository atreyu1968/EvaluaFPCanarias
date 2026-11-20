"""Exportación Additio/Excel con validación docente y controles antiformulas."""
import csv
import io
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import database
import evaluacion
import exportaciones

class ExportTests(unittest.TestCase):
    def setUp(self):
        database.init()
        with database.connect() as d:
            d.execute('INSERT INTO modules(academic_year,cycle,name,group_name,created_at) VALUES(?,?,?,?,?)',
                ('2026-2027','CFGM','Técnica Contable','1A',database.now()))
            self.mid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
            d.execute('INSERT INTO students(module_id,code,name) VALUES(?,?,?)',(self.mid,'ALU001','Pérez Gómez, Ana María'))
            self.sid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
            d.execute('INSERT INTO students(module_id,code,name) VALUES(?,?,?)',(self.mid,'ALU002','=HYPERLINK("malicioso")'))
            d.execute('INSERT INTO outcomes(module_id,code,description,weight) VALUES(?,?,?,?)',(self.mid,'RA1','Aplica técnicas',100))
            ra=d.execute('SELECT last_insert_rowid()').fetchone()[0]
            d.execute('INSERT INTO criteria(outcome_id,code,description,weight) VALUES(?,?,?,?)',(ra,'RA1.a','Registra asientos',100))
            self.cid=d.execute('SELECT last_insert_rowid()').fetchone()[0]
            evaluacion.update_settings(d,{'module_id':self.mid,'enterprise_mode':'integrated','enterprise_weight':0,
                'validated':True,'teacher_note':'La formación en empresa se considera integrada en los RA del módulo.'})
            self.iid=evaluacion.add_instrument(d,{'module_id':self.mid,'term':1,'title':'Examen con rúbrica',
                'kind':'examen','targets':[{'criterion_id':self.cid,'weight':100}]})
            evaluacion.put_score(d,{'instrument_id':self.iid,'criterion_id':self.cid,'student_id':self.sid,
                'score':7.5,'comment':'Aplicación correcta'})

    def test_csv_students_can_be_mapped_in_additio(self):
        with database.connect() as d:
            raw,kind,name=exportaciones.export_additio(d,self.mid,'alumnos')
        s=raw.decode('utf-8-sig')
        rows=list(csv.reader(io.StringIO(s),delimiter=';'))
        self.assertEqual(rows[0],['Codigo','Nombre','Apellidos'])
        bycode={r[0]:r for r in rows[1:]}
        self.assertEqual(bycode['ALU001'],['ALU001','Ana María','Pérez Gómez'])
        self.assertTrue(bycode['ALU002'][1].startswith("'=HYPERLINK"),'Se debe neutralizar una fórmula CSV maliciosa.')

    def test_final_not_transferred_until_teacher_closure(self):
        with database.connect() as d:
            raw,_,_=exportaciones.export_additio(d,self.mid,'notas')
            rows=list(csv.reader(io.StringIO(raw.decode('utf-8-sig')),delimiter=';'))
            bycode={r[0]:r for r in rows[1:]}
            self.assertTrue(all(x=='' for x in bycode['ALU001'][2:]))
            evaluacion.close_student(d,self.mid,self.sid,'Rúbrica comprobada manualmente por docente.')
        with database.connect() as d:
            raw,_,_=exportaciones.export_additio(d,self.mid,'notas')
            rows=list(csv.reader(io.StringIO(raw.decode('utf-8-sig')),delimiter=';'))
            bycode={r[0]:r for r in rows[1:]}
            self.assertEqual(rows[0][2],f'EFP{self.mid}_RA1')
            self.assertEqual(rows[0][3],'1.a')
            self.assertEqual(bycode['ALU001'][2:],['7.5','7.5'], 'Solo RA y CE, nunca instrumentos.')

    def test_excel_real_xlsx_and_tsv(self):
        with database.connect() as d:
            blob,mime,name=exportaciones.export_excel(d,self.mid,'xlsx')
            tsv,mime2,name2=exportaciones.export_additio(d,self.mid,'pegar')
            group_xlsx,_,group_name=exportaciones.additio_students_xlsx(d,self.mid)
        self.assertEqual(blob[:2],b'PK')
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            self.assertIsNone(z.testzip())
            self.assertTrue(any(n.startswith('xl/worksheets/sheet') for n in z.namelist()))
            self.assertIn('Additio RA CE',z.read('xl/workbook.xml').decode())
        self.assertIn(b'\t',tsv)
        self.assertTrue(name2.endswith('.tsv'))
        self.assertTrue(name.endswith('.xlsx'))
        self.assertTrue(group_name.endswith('.xlsx'))
        with zipfile.ZipFile(io.BytesIO(group_xlsx)) as z:
            self.assertIsNone(z.testzip())
            self.assertEqual(len([n for n in z.namelist() if n.startswith('xl/worksheets/sheet') and n.endswith('.xml')]),1)


if __name__=='__main__':unittest.main()
