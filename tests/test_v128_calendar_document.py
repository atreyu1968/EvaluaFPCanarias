"""Regresiones 1.2.8: fechas explícitas con evidencia, sin introducir normas ficticias."""
from __future__ import annotations
import io
import unittest

import calendar_document as calendar
import territorial_profiles as territories

DOCUMENT='''Consejería de Educación de Canarias
Calendario escolar Formación Profesional (FP) Grado D, curso 2026-2027.
Inicio de las clases: 16 de septiembre de 2026.
Fin de las clases: 22 de junio de 2027.
Vacaciones de Navidad del 23 de diciembre de 2026 al 8 de enero de 2027.
Vacaciones de Semana Santa del 22 de marzo de 2027 al 26 de marzo de 2027.
Día no lectivo: 12/10/2026 por fiesta nacional.
'''


class CalendarDocumentTests(unittest.TestCase):
    def preview(self, text=DOCUMENT, region='Canarias', year='2026-2027'):
        return calendar.preview_document('calendario.txt',text.encode('utf8'),region,year)

    def test_literal_dates_are_traced_to_lines_and_non_declarative(self):
        result=self.preview()
        self.assertTrue(result['scope_ok'])
        self.assertEqual(result['candidates']['start_date'][0]['value'],'2026-09-16')
        self.assertEqual(result['candidates']['end_date'][0]['value'],'2027-06-22')
        self.assertEqual(len(result['candidates']['vacation_periods']),2)
        self.assertEqual(result['candidates']['vacation_periods'][0]['value']['start'],'2026-12-23')
        self.assertEqual(result['candidates']['vacation_periods'][0]['value']['end'],'2027-01-08')
        self.assertEqual(result['candidates']['regional_non_teaching_days'][0]['value']['date'],'2026-10-12')
        for group in result['candidates'].values():
            for candidate in group:
                self.assertIn('línea',candidate['location'])
                self.assertTrue(candidate['excerpt'])
        self.assertTrue(result['no_changes_saved'])
        self.assertTrue(result['requires_teacher_confirmation'])
        self.assertEqual(len(result['sha256']),64)

    def test_no_missing_year_invention_and_conflicting_start_dates(self):
        text=DOCUMENT.replace('16 de septiembre de 2026','16 de septiembre')
        self.assertFalse(self.preview(text)['candidates'].get('start_date'))
        conflict=DOCUMENT+'Inicio de las clases FP: 17 de septiembre de 2026.\n'
        x=self.preview(conflict)
        self.assertFalse(x['candidates'].get('start_date'))
        self.assertTrue(any('incompatibles' in w for w in x['warnings']))
        self.assertEqual(x['candidates']['end_date'][0]['value'],'2027-06-22')

    def test_scope_requires_year_region_and_fp_text(self):
        missing_region=self.preview(DOCUMENT.replace('Canarias','Otro lugar'))
        self.assertFalse(missing_region['scope_ok'])
        self.assertFalse(missing_region['scope']['territory_match'])
        missing_stage=self.preview(DOCUMENT.replace('Formación Profesional (FP) Grado D','Educación'))
        self.assertFalse(missing_stage['scope_ok'])
        wrong_year=self.preview(DOCUMENT.replace('curso 2026-2027','curso 2025-2026'))
        self.assertFalse(wrong_year['scope_ok'])
        self.assertIn('2025-2026',wrong_year['scope']['courses_in_document'])
        for code,region in territories.TERRITORIES:
            if region!='Canarias':
                self.assertFalse(self.preview(region=region)['scope_ok'])

    def test_heading_of_other_educational_stage_blocks_following_dates(self):
        text=(DOCUMENT+'\nBachillerato\nInicio de las clases: 15 de septiembre de 2026.\n'
             'Fin de las clases: 20 de junio de 2027.\n')
        report=self.preview(text)
        self.assertEqual(report['candidates']['start_date'][0]['value'],'2026-09-16')
        self.assertEqual(report['candidates']['end_date'][0]['value'],'2027-06-22')
        self.assertEqual(len(report['candidates']['start_date']),1)
        self.assertEqual(len(report['candidates']['end_date']),1)

    def test_bad_extensions_magic_size_and_out_of_year(self):
        for name,blob in [('example.exe',b'abc'),('scan.pdf',b'PDF-content'),('fake.docx',b'fake')]:
            with self.subTest(name=name),self.assertRaises(ValueError):
                calendar.preview_document(name,blob,'Canarias','2026-2027')
        with self.assertRaises(ValueError):
            calendar.preview_document('c.pdf',b'0'*(15*1024*1024+1),'Canarias','2026-2027')
        text=DOCUMENT.replace('16 de septiembre de 2026','16 de septiembre de 2028')
        self.assertFalse(self.preview(text)['candidates'].get('start_date'))

    def test_docx_paragraph_and_table_locations(self):
        from docx import Document
        d=Document()
        d.add_paragraph('Calendario escolar Formación Profesional FP, Canarias, curso 2026-2027.')
        d.add_paragraph('Inicio de las clases: 16 de septiembre de 2026.')
        tbl=d.add_table(rows=1,cols=1)
        tbl.cell(0,0).text='Vacaciones de Navidad del 23 de diciembre de 2026 al 8 de enero de 2027.'
        out=io.BytesIO();d.save(out)
        result=calendar.preview_document('calendario.docx',out.getvalue(),'Canarias','2026-2027')
        self.assertTrue(result['scope_ok'])
        self.assertEqual(result['candidates']['start_date'][0]['location'],'párrafo 2')
        self.assertEqual(result['candidates']['vacation_periods'][0]['location'],'tabla 1, fila 1')

    def test_pdf_extracts_pages_without_ocr(self):
        import fitz
        pdf=fitz.open();page=pdf.new_page()
        page.insert_text((50,60),'Calendario escolar FP Canarias curso 2026-2027.',fontsize=11)
        page.insert_text((50,80),'Inicio de las clases: 16 de septiembre de 2026.',fontsize=11)
        raw=pdf.tobytes();pdf.close()
        report=calendar.preview_document('fuente.pdf',raw,'Canarias','2026-2027')
        self.assertTrue(report['scope_ok'])
        self.assertEqual(report['candidates']['start_date'][0]['location'],'página 1')
        self.assertFalse(report['ocr_used'])

    def test_non_fp_stage_line_not_used_for_dates(self):
        text=DOCUMENT+'Bachillerato: inicio de las clases 15 de septiembre de 2026.\n'
        report=self.preview(text)
        self.assertEqual(report['candidates']['start_date'][0]['value'],'2026-09-16')
        self.assertEqual(len(report['candidates']['start_date']),1)


if __name__=='__main__':unittest.main()