"""Regresión 1.2.0: consulta BOE simulada, PDF/Word y protección nacional."""
from __future__ import annotations
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import boe_discovery as boe
import official_document_tables as table


class FakeHTTP:
    def __init__(self,url,payload):self.url=url;self.body=json.dumps(payload,ensure_ascii=False).encode()
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def geturl(self):return self.url
    def read(self,size):return self.body[:size]


class DiscoveryTests(unittest.TestCase):
    def mock_open(self, request, timeout):
        url=request.full_url
        if url.endswith('/analisis'):
            data={'status':'OK','data':{'afectada_por':[{'identificador':'BOE-A-2024-3000','tipo':'Modifica'}]}}
        elif url.endswith('/metadatos'):
            data={'status':'OK','data':{'identificador':'BOE-A-2011-19533','titulo':'Real Decreto 1584/2011, título de Administración y Finanzas','fecha_publicacion':'20111215'}}
        else:
            data={'status':'OK','data':[
             {'identificador':'BOE-A-2011-19533','titulo':'Real Decreto 1584/2011, título de Técnico Superior en Administración y Finanzas','fecha_publicacion':'20111215'},
             {'identificador':'BOE-A-2021-900','titulo':'Ley general de tributos'},
             {'identificador':'BOE-A-2011-19533','titulo':'Duplicado'}]}
        return FakeHTTP(url,data)

    def test_search_boe_matches_title_without_auto_approval(self):
        result=boe.search_title('CFGS Administración y Finanzas','Comunidad de Madrid','2026-2027',opener=self.mock_open)
        self.assertEqual(result['records'][0]['id'],'BOE-A-2011-19533')
        self.assertEqual(result['records'][0]['status'],'resultado_para_revision')
        self.assertEqual(len(result['records']),2)
        self.assertIn('NO cubre todas',result['notice'])

    def test_search_params_are_fixed_official_and_only_cycle(self):
        seen=[]
        def opener(request,timeout):
            seen.append(request.full_url)
            return self.mock_open(request,timeout)
        boe.search_title('Gestión Administrativa','Canarias','2027-2028',opener=opener)
        self.assertEqual(len(seen),1)
        self.assertTrue(seen[0].startswith(boe.API+'?'))
        self.assertNotIn('profesor',seen[0].lower())
        self.assertIn('query=',seen[0])

    def test_inspection_does_not_assert_current_curriculum(self):
        result=boe.inspect_boe_id('BOE-A-2011-19533',opener=self.mock_open)
        self.assertEqual(result['id'],'BOE-A-2011-19533')
        self.assertTrue(result['approval_required'])
        self.assertIn('currículo aplicable',result['notice'])
        self.assertTrue(result['has_legal_analysis'])

    def test_strict_ids_region_and_course(self):
        for identifier in ('https://evil.com','BOE-A-2024-1/../../x','BOE-A-2026-1?x=2'):
            with self.subTest(identifier=identifier),self.assertRaises(ValueError):
                boe.inspect_boe_id(identifier,opener=self.mock_open)
        with self.assertRaises(ValueError):
            boe.search_title('Gestión Administrativa','Comunidad de Marte','2026-2027',opener=self.mock_open)
        with self.assertRaises(ValueError):
            boe.search_title('Gestión Administrativa','Galicia','2029-2029',opener=self.mock_open)

    def test_list_and_nested_result_api_variants(self):
        row={'identificador':'BOE-A-2020-100','titulo':'RD de prueba'}
        for value in (row,[row],{'data':row},{'data':{'items':[row]}}):
            with self.subTest(value=value):
                self.assertEqual(len(boe.parse_search_result(value)),1)

    def test_invalid_or_redirected_api_response_does_not_appear_credible(self):
        def bad_opener(req,timeout):return FakeHTTP('https://example.com/redirect',{'data':[]})
        with self.assertRaisesRegex(ValueError,'redirigido'):
            boe.search_title('Administración y Finanzas','Canarias','2026-2027',opener=bad_opener)
        def bad_body(req,timeout):
            obj=FakeHTTP(req.full_url,{})
            obj.body=b'<html>Error</html>'
            return obj
        with self.assertRaisesRegex(ValueError,'datos estructurados'):
            boe.search_title('Administración y Finanzas','Canarias','2026-2027',opener=bad_body)


class DocumentTablesTests(unittest.TestCase):
    @staticmethod
    def make_docx():
        from docx import Document
        d=Document();t=d.add_table(rows=1,cols=4)
        for cell,val in zip(t.rows[0].cells,table.HEADER):cell.text=val
        for code,name,annual,weekly in [('0650','Proceso integral de la actividad comercial','202','6'),('0651','Comunicación y atención al cliente','170','5')]:
            row=t.add_row().cells
            for cell,val in zip(row,[code,name,annual,weekly]):cell.text=val
        stream=io.BytesIO();d.save(stream);return stream.getvalue()

    def test_docx_table_import_is_draft_only(self):
        result=table.preview_document('horas.docx',self.make_docx())
        self.assertEqual(result['count'],2)
        self.assertEqual(result['rows'][0]['weekly_hours'],6)
        self.assertTrue(result['requires_teacher_confirmation'])
        self.assertTrue(result['table'].startswith('Código;Módulo;'))

    def test_text_rows_with_code_only(self):
        text='0650 Proceso integral de la actividad comercial 202 6\n'
        rows=table._rows_from_text(text)
        self.assertEqual(rows[0],['0650','Proceso integral de la actividad comercial','202','6'])
        self.assertEqual(table._rows_from_text('Proceso integral de la actividad comercial 202 6'),[])
        self.assertEqual(table._rows_from_text('0650 Proceso 2027 62'),[])

    def test_pdf_text_table_extraction(self):
        import fitz
        doc=fitz.open();page=doc.new_page()
        page.insert_text((55,55),'0650 Proceso integral de la actividad comercial 202 6',fontsize=11)
        page.insert_text((55,80),'0651 Comunicacion y atencion al cliente 170 5',fontsize=11)
        raw=doc.tobytes();doc.close()
        result=table.preview_document('anexo.pdf',raw)
        self.assertEqual(result['count'],2)
        self.assertFalse(result['ocr_used'])

    def test_reject_conflicting_duplicate_codes(self):
        doc=table._rows_from_table([table.HEADER,['0650','Módulo A','202','6'],['0650','Módulo B','120','4']])
        self.assertEqual(len(doc),2)
        from unittest.mock import patch
        with patch.object(table,'_parse_docx',return_value=(doc,0,False)):
            with self.assertRaisesRegex(ValueError,'incompatibles'):
                table.preview_document('anexo.docx',b'PKfake')

    def test_reject_bad_files_and_no_guessing(self):
        for filename,blob in [('horas.exe',b'1'),('horas.pdf',b'PKxxx'),('horas.docx',b'bad')]:
            with self.subTest(filename=filename),self.assertRaises(ValueError):
                table.preview_document(filename,blob)
        from docx import Document
        d=Document();d.add_paragraph('202 horas y 6 semanales')
        stream=io.BytesIO();d.save(stream)
        with self.assertRaisesRegex(ValueError,'No se han identificado tablas'):
            table.preview_document('vacio.docx',stream.getvalue())

    def test_frontend_and_server_routes_are_present(self):
        root=Path(__file__).resolve().parents[1]
        app=(root/'app.py').read_text(encoding='utf8');js=(root/'web/app.js').read_text(encoding='utf8')
        for route in ('/api/national/document-preview','/api/national/boe-search','/api/national/boe-inspect'):
            self.assertIn(route,app);self.assertIn(route,js)
        for action in ('national-document-preview','national-boe-search','national-boe-inspect','national-boe-add'):
            self.assertIn("action==='"+action+"'",js)

if __name__=='__main__':unittest.main()
