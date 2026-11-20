"""Regresiones: multipart de navegadores con nombres de archivo UTF-8."""
import io
import sys
import unittest
from email.header import Header
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app


def submit_file(filename, payload=b'Contenido', *, field='document', encoded=False):
    boundary = '----EvaluaFPtestBoundary'
    if encoded:
        parameter = "filename*=UTF-8''" + quote(filename, safe='')
    else:
        parameter = 'filename="' + filename.replace('\\', '\\\\') + '"'
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="module_id"\r\n\r\n17\r\n'
        f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; {parameter}\r\n'
        f'Content-Type: application/octet-stream\r\n\r\n'
    ).encode('utf-8') + payload + f'\r\n--{boundary}--\r\n'.encode()
    handler = SimpleNamespace(headers={
        'Content-Length': str(len(body)),
        'Content-Type': f'multipart/form-data; boundary={boundary}'
    }, rfile=io.BytesIO(body))
    return app.multipart(handler)


class UploadUnicodeTests(unittest.TestCase):
    def test_reproduces_old_parser_header_object(self):
        import email
        filename = 'Programación Didáctica — Técnica Contable 2026_2027.docx'
        content_type='multipart/form-data; boundary=----test'
        raw=(f'------test\r\nContent-Disposition: form-data; name="document"; filename="{filename}"\r\n'
             'Content-Type: application/octet-stream\r\n\r\nxx\r\n------test--\r\n').encode('utf-8')
        msg=email.message_from_bytes(f'MIME-Version: 1.0\r\nContent-Type: {content_type}\r\n\r\n'.encode()+raw)
        self.assertIsInstance(msg.get_payload()[0].get('Content-Disposition'), Header)

    def test_word_filename_accents_and_em_dash(self):
        name='Programación Didáctica — Técnica Contable 2026_2027.docx'
        fields, files=submit_file(name,b'PK\x03\x04prueba')
        self.assertEqual(fields, {'module_id':'17'})
        self.assertEqual(files,[('document',name,b'PK\x03\x04prueba')])

    def test_pdf_filename_accents(self):
        name='Evaluación 1º trimestre.pdf'
        fields,files=submit_file(name,b'%PDF-1.7')
        self.assertEqual(files[0][1], name)

    def test_ascii_and_windows_path(self):
        _,files=submit_file('C:\\documentos\\UD1.docx',b'PK...')
        self.assertEqual(files[0][1], 'UD1.docx')

    def test_rfc2231_encoded_filename(self):
        name='Programación contable 2026 — Málaga.docx'
        _,files=submit_file(name,b'PK...',encoded=True)
        self.assertEqual(files[0][1],name)

    def test_unchanged_binary_content(self):
        original=b'\xff\x00\x80\x01\r\n\x03' * 200
        _,files=submit_file('Documento — A.pdf',original)
        self.assertEqual(files[0][2],original)

if __name__ == '__main__':
    unittest.main()
