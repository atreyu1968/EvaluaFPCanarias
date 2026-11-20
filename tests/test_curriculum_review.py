"""Pruebas del complemento independiente de previsualización curricular."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import curriculum_review as cr


MODULE='Proceso integral de la actividad comercial'
TEXT=f'''Módulo profesional: {MODULE}\nCódigo: 0650\nRESULTADOS DE APRENDIZAJE Y CRITERIOS DE EVALUACIÓN\nRA1. Determina los elementos patrimoniales de una empresa siguiendo sus operaciones.\nCriterios de evaluación:\na) Se han identificado las fases del ciclo económico en una actividad empresarial.\nb) Se han clasificado elementos patrimoniales en distintas masas contables.\nRA2. Aplica normas de registro contable en operaciones empresariales habituales.\nCriterios de evaluación:\na) Se han definido las cuentas necesarias para los asientos contables.\nb) Se han aplicado las normas de cargo y abono de las cuentas.\nCONTENIDOS\nEsta es una sección nueva que no debe extraerse como CE.\n'''


def temporary_file(text, ext='.txt'):
    tmp=tempfile.TemporaryDirectory()
    p=Path(tmp.name)/('programa'+ext)
    p.write_text(text,encoding='utf8')
    return tmp,p


class ParsingTests(unittest.TestCase):
    def test_complete_two_ra_four_ce(self):
        tmp,p=temporary_file(TEXT)
        try:
            report=cr.preview(p,MODULE,'0650')
        finally:tmp.cleanup()
        self.assertEqual(report['summary'],{'ra':2,'ce':4})
        self.assertEqual(report['outcomes'][0]['criteria'][0]['code'],'RA1.a')
        self.assertEqual(report['outcomes'][0]['locations'],['línea 4'])
        self.assertEqual(report['status'],'pendiente_revision_docente')
        self.assertNotIn('Sección nueva',json.dumps(report))

    def test_no_fabrication_with_broken_ce_sequence(self):
        tmp,p=temporary_file(TEXT.replace('b) Se han clasificado','c) Se han clasificado'))
        try:
            with self.assertRaisesRegex(cr.CurriculumError,'secuencia alfabética'):
                cr.preview(p,MODULE,'0650')
        finally:tmp.cleanup()

    def test_no_fabrication_with_missing_ra(self):
        tmp,p=temporary_file(TEXT.replace('RA2. Aplica','RA3. Aplica'))
        try:
            with self.assertRaisesRegex(cr.CurriculumError,'secuencia completa'):
                cr.preview(p,MODULE,'0650')
        finally:tmp.cleanup()

    def test_reject_incorrect_code(self):
        tmp,p=temporary_file(TEXT)
        try:
            with self.assertRaisesRegex(cr.CurriculumError,'código oficial indicado'):
                cr.preview(p,MODULE,'0999')
        finally:tmp.cleanup()

    def test_reject_multiple_blocks_in_programming(self):
        tmp,p=temporary_file(TEXT+'\n'+TEXT)
        try:
            with self.assertRaisesRegex(cr.CurriculumError,'varios apartados'):
                cr.preview(p,MODULE,'0650')
        finally:tmp.cleanup()

    def test_scoping_legal_avoids_other_module(self):
        fake=TEXT.replace(MODULE,'Módulo distinto').replace('0650','9999')
        combined=fake+'\n'+TEXT
        tmp,p=temporary_file(combined)
        try:
            report=cr.preview(p,MODULE,'0650',document_kind='norma_oficial')
            self.assertEqual(report['summary']['ce'],4)
            self.assertEqual(report['outcomes'][0]['locations'][0],f'línea {combined.splitlines().index("RA1. Determina los elementos patrimoniales de una empresa siguiendo sus operaciones.",len(fake.splitlines()))+1}')
        finally:tmp.cleanup()

    def test_only_other_module_is_rejected(self):
        # La denominación y el código solicitados aparecen sueltos, pero el
        # apartado de RA/CE está asociado al último encabezado de OTRO módulo.
        header=f'{MODULE}\nCódigo: 0650\n'
        fake=TEXT.replace(MODULE,'Módulo distinto').replace('0650','9999')
        tmp,p=temporary_file(header+fake)
        try:
            with self.assertRaisesRegex(cr.CurriculumError,'no contiene RA y CE'):
                cr.preview(p,MODULE,'0650',document_kind='norma_oficial')
        finally:tmp.cleanup()

    def test_preview_docx(self):
        from docx import Document
        doc=Document()
        for line in TEXT.splitlines():doc.add_paragraph(line)
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'curriculo.docx';doc.save(p)
            report=cr.preview(p,MODULE,'0650')
        self.assertEqual(report['summary']['ce'],4)
        self.assertTrue(report['outcomes'][0]['locations'][0].startswith('párrafo'))

    def test_preview_pdf(self):
        import fitz
        doc=fitz.open();page=doc.new_page()
        y=55
        for line in TEXT.splitlines():
            page.insert_text((45,y),line,fontsize=9)
            y+=16
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'curriculo.pdf'
            doc.save(p);doc.close()
            report=cr.preview(p,MODULE,'0650')
        self.assertEqual(report['summary']['ra'],2)
        self.assertEqual(report['outcomes'][0]['criteria'][0]['locations'],['página 1'])

    def test_wrong_suffix_or_blob_is_rejected(self):
        tmp,p=temporary_file(TEXT,ext='.exe')
        try:
            with self.assertRaisesRegex(cr.CurriculumError,'Solo se admiten'):
                cr.preview(p,MODULE,'0650')
        finally:tmp.cleanup()


class WeightsTests(unittest.TestCase):
    def test_ceil_of_100_percent_and_global_equal(self):
        tmp,p=temporary_file(TEXT)
        try:report=cr.preview(p,MODULE,'0650')
        finally:tmp.cleanup()
        weights=cr.propose_equal_weights(report)
        self.assertEqual(sum(Decimal(x['module_weight_pct']) for x in weights),Decimal('100.00'))
        flat=[Decimal(ce['module_weight_pct']) for ra in weights for ce in ra['criteria']]
        self.assertEqual(sum(flat),Decimal('100.00'))
        self.assertLessEqual(max(flat)-min(flat),Decimal('.01'))
        for ra in weights:
            self.assertEqual(sum(Decimal(x['ra_weight_pct']) for x in ra['criteria']),Decimal('100.00'))

    def test_diff_does_not_change_data(self):
        tmp,p=temporary_file(TEXT)
        try:report=cr.preview(p,MODULE,'0650')
        finally:tmp.cleanup()
        old=[{'code':'RA1','description':'Un RA antiguo', 'weight':60, 'criteria':[
            {'code':'RA1.a','description':'Un criterio antiguo', 'weight':33.3}]}]
        snapshot=json.dumps(old,sort_keys=True)
        diff=cr.compare(report,old)
        self.assertTrue(diff['blocking'])
        self.assertIn('nuevo_ra',diff['counts'])
        self.assertIn('nuevo_ce',diff['counts'])
        self.assertIn('faltante_ce',cr.compare({'outcomes':[report['outcomes'][0]]},[
            {'code':'RA1','description':report['outcomes'][0]['description'],
             'criteria':[{'code':'RA1.a','description':report['outcomes'][0]['criteria'][0]['description']},
                         {'code':'RA1.z','description':'Criterio histórico'}]}])['counts'])
        self.assertEqual(json.dumps(old,sort_keys=True),snapshot)


if __name__=='__main__':unittest.main()
