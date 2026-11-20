"""Regresiones 1.2.9: anexos tabulados, saltos de línea e IA verificable."""
from __future__ import annotations

import io
import unittest
from unittest.mock import patch

import calendar_annex
import calendar_ai
import calendar_document

HEAD=('Calendario escolar Canarias 2026-2027. '
      'Formación Profesional FP Grado D.\n')
FRAGMENT=(HEAD+'Etapa | Inicio de clases | Fin de clases\n'
          'Formación Profesional | 16/09/2026 | 22/06/2027\n'
          'Vacaciones de Navidad del 23/12/2026 al 08/01/2027.\n'
          'Día no lectivo: 12/10/2026 por Fiesta Nacional.\n')


class CalendarAnnexTests(unittest.TestCase):
    def test_fp_only_table_and_original_evidence(self):
        matrix=[
            ['Etapa','Inicio de clases','Final de clases'],
            ['Bachillerato','15/09/2026','20/06/2027'],
            ['Formación Profesional (FP)','16/09/2026','22/06/2027'],
            ['Primaria','10/09/2026','20/06/2027']]
        records=calendar_annex.table_records(matrix,'tabla 1')
        self.assertEqual(len(records),2)
        self.assertTrue(all('fila 3' in r['location'] for r in records))
        self.assertTrue(all('16/09/2026' in r['excerpt'] for r in records))
        self.assertTrue(all('Bachillerato' not in r['excerpt'] for r in records))
        self.assertFalse(calendar_annex.table_records([['Inicio','Fin'],['16/09/2026','22/06/2027']],'tabla'))

    def test_docx_multi_stage_table_recognised_without_transferring_dates(self):
        from docx import Document
        doc=Document()
        doc.add_paragraph(HEAD.strip())
        table=doc.add_table(rows=4,cols=3)
        data=[['Etapa','Inicio de clases','Fin de clases'],
              ['Bachillerato','15/09/2026','20/06/2027'],
              ['FP Grado D','16/09/2026','22/06/2027'],
              ['ESO','13/09/2026','21/06/2027']]
        for row,cells in zip(table.rows,data):
            for cell,value in zip(row.cells,cells):cell.text=value
        buf=io.BytesIO();doc.save(buf)
        report=calendar_document.preview_document('anexo.docx',buf.getvalue(),'Canarias','2026-2027')
        self.assertTrue(report['scope_ok'])
        self.assertEqual(report['candidates']['start_date'][0]['value'],'2026-09-16')
        self.assertEqual(report['candidates']['end_date'][0]['value'],'2027-06-22')
        self.assertEqual(len(report['candidates']['start_date']),1)
        self.assertIn('Encabezados:',report['candidates']['start_date'][0]['excerpt'])

    def test_pdf_line_splits_and_page_evidence(self):
        import fitz
        pdf=fitz.open()
        page=pdf.new_page()
        page.insert_text((40,50),HEAD.strip(),fontsize=10)
        page.insert_text((40,75),'Inicio de clases de FP:',fontsize=10)
        page.insert_text((40,90),'16/09/2026',fontsize=10)
        page.insert_text((40,120),'Fin de clases de FP:',fontsize=10)
        page.insert_text((40,135),'22/06/2027',fontsize=10)
        raw=pdf.tobytes();pdf.close()
        report=calendar_document.preview_document('anexo.pdf',raw,'Canarias','2026-2027')
        self.assertTrue(report['scope_ok'])
        self.assertEqual(report['candidates']['start_date'][0]['value'],'2026-09-16')
        self.assertEqual(report['candidates']['end_date'][0]['value'],'2027-06-22')
        self.assertIn('página 1',report['candidates']['start_date'][0]['location'])


    def test_optional_ai_excerpt_is_prepared_locally_with_scope_and_full_dates(self):
        report=calendar_document.preview_document('calendario.txt',
                  FRAGMENT.encode('utf-8'),'Canarias','2026-2027')
        fragment=report['suggested_ai_fragment']
        self.assertIn('Canarias',fragment)
        self.assertIn('2026-2027',fragment)
        self.assertIn('16/09/2026',fragment)
        self.assertTrue(report['no_changes_saved'])
        wrong=calendar_document.preview_document('calendario.txt',
                  FRAGMENT.encode('utf-8'),'Comunidad de Madrid','2026-2027')
        self.assertEqual(wrong['suggested_ai_fragment'],'')

    def test_stitched_fragments_never_cross_pages(self):
        parts=[{'text':'Inicio de clases de FP','location':'página 1'},
               {'text':'16/09/2026','location':'página 2'}]
        extracted=calendar_annex.stitched_records(
            parts,calendar_document.DATE_RE,calendar_document.RANGE_RE,
            calendar_document.START_RE,calendar_document.END_RE,
            calendar_document.SCHOOL_RE,calendar_document.VACATION_RE)
        self.assertEqual(len(extracted),2)


class CalendarAIGuardsTests(unittest.TestCase):
    def run_model(self,proposals,fragment=FRAGMENT,consent=True):
        with patch.object(calendar_ai.ia,'chat',return_value=({'proposals':proposals},'modelo_pruebas')) as mock:
            result=calendar_ai.interpret(fragment,'Canarias','2026-2027',consent)
            self.assertEqual(mock.call_count,1)
            return result

    def test_literal_source_quote_and_teacher_confirmed_status(self):
        proposals=[
            {'field':'start_date','date':'2026-09-16',
             'evidence_quote':'Formación Profesional | 16/09/2026 | 22/06/2027',
             'heading_quote':'Etapa | Inicio de clases | Fin de clases'},
            {'field':'end_date','date':'2027-06-22',
             'evidence_quote':'Formación Profesional | 16/09/2026 | 22/06/2027',
             'heading_quote':'Etapa | Inicio de clases | Fin de clases'},
            {'field':'vacation_periods','date':'2026-12-23','date_end':'2027-01-08',
             'evidence_quote':'Vacaciones de Navidad del 23/12/2026 al 08/01/2027.'},
            {'field':'regional_non_teaching_days','date':'2026-10-12',
             'evidence_quote':'Día no lectivo: 12/10/2026 por Fiesta Nacional.'}
        ]
        result=self.run_model(proposals)
        self.assertEqual(result['candidate_count'],4)
        self.assertEqual(result['candidates']['start_date'][0]['value'],'2026-09-16')
        self.assertEqual(result['candidates']['end_date'][0]['value'],'2027-06-22')
        self.assertEqual(result['candidates']['vacation_periods'][0]['value']['end'],'2027-01-08')
        self.assertEqual(result['ai_model'],'modelo_pruebas')
        self.assertTrue(result['no_changes_saved'])
        self.assertTrue(result['requires_teacher_confirmation'])

    def test_forged_dates_quotes_column_mapping_and_other_stage_rejected(self):
        proposals=[
            {'field':'start_date','date':'2026-09-17','evidence_quote':'Formación Profesional | 16/09/2026 | 22/06/2027',
             'heading_quote':'Etapa | Inicio de clases | Fin de clases'},
            {'field':'start_date','date':'2026-09-16','evidence_quote':'Inicio FP 16/09/2026 que no está en el documento'},
            {'field':'end_date','date':'2026-09-16','evidence_quote':'Formación Profesional | 16/09/2026 | 22/06/2027',
             'heading_quote':'Etapa | Inicio de clases | Fin de clases'},
            {'field':'start_date','date':'2026-09-15','evidence_quote':'Bachillerato inicio clases 15/09/2026'}
        ]
        report=self.run_model(proposals)
        self.assertEqual(report['candidate_count'],0)
        self.assertEqual(len(report['warnings']),5)

    def test_no_external_call_without_consent_or_wrong_scope(self):
        with patch.object(calendar_ai.ia,'chat') as mock:
            with self.assertRaises(ValueError):
                calendar_ai.interpret(FRAGMENT,'Canarias','2026-2027',False)
            with self.assertRaises(ValueError):
                calendar_ai.interpret(FRAGMENT,'Canarias','2027-2028',True)
            with self.assertRaises(ValueError):
                calendar_ai.interpret(FRAGMENT,'Comunidad de Madrid','2026-2027',True)
            mock.assert_not_called()

    def test_conflicts_rejected_and_unrelated_ai_keys_ignored(self):
        fragment=(HEAD+'Inicio de clases FP: 16/09/2026.\nInicio de clases FP: 17/09/2026.\n')
        result=self.run_model([
           {'field':'start_date','date':'2026-09-16','evidence_quote':'Inicio de clases FP: 16/09/2026.'},
           {'field':'start_date','date':'2026-09-17','evidence_quote':'Inicio de clases FP: 17/09/2026.'},
           {'field':'teacher','date':'2026-09-16','evidence_quote':'Inicio de clases FP: 16/09/2026.'}
        ],fragment)
        self.assertFalse(result['candidates']['start_date'])
        self.assertTrue(any('incompatibles' in w for w in result['warnings']))

if __name__=='__main__':
    unittest.main()
