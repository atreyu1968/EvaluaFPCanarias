"""Protección contra CE inventados y generación agrupada por varios criterios."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from docx import Document

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import logic


class CurriculumSpeedTests(unittest.TestCase):
    def test_programming_without_verbatim_ce_does_not_create_any(self):
        program = ('Programación didáctica de Técnica Contable. Código del módulo: 0299. '
                   'RA1: Identifica los principios básicos de la contabilidad. '
                   'RA2: Aplica técnicas de registro en el diario y mayor. '
                   'Los criterios a) a f) se trabajarán mediante prácticas. '
                   'Cada RA representa 20 % y la FE 25 %. Se identifican los RA204.')
        response={'outcomes':[
            {'code':'RA1','description':'Identifica los principios básicos de la contabilidad.','weight':20,
             'criteria':[{'code':'RA1.a','description':'Se ha reconocido la normativa contable con exactitud.','weight':16.6}]},
            {'code':'RA2','description':'Aplica técnicas de registro en el diario y mayor.','weight':20,
             'criteria':[{'code':'RA2.b','description':'Aplica el asiento contable mediante el libro mayor.','weight':20}]}],
            'warnings':[]}
        with patch.object(logic.ia,'chat',return_value=(response,'modelo-simulado')):
            proposal=logic.analyze_program(program)
        self.assertEqual(len(proposal['outcomes']),2)
        self.assertEqual(sum(len(x['criteria']) for x in proposal['outcomes']),0)
        self.assertEqual(proposal['coverage']['ce_discarded'],2)
        self.assertTrue(any('0441' in w for w in proposal['warnings']))
        self.assertTrue(any('RA204' in w for w in proposal['warnings']))

    def test_verbatim_ce_with_code_is_accepted(self):
        program='RA2: Registra operaciones contables. a) Se han registrado las operaciones en los libros contables.'
        response={'outcomes':[{'code':'RA2','description':'Registra operaciones contables.','weight':None,
                   'criteria':[{'code':'RA2.a','description':'Se han registrado las operaciones en los libros contables.','weight':None}]}]}
        with patch.object(logic.ia,'chat',return_value=(response,'simulado')):
            output=logic.analyze_program(program)
        self.assertEqual(len(output['outcomes'][0]['criteria']),1)
        self.assertEqual(output['outcomes'][0]['criteria'][0]['code'],'RA2.a')

    def test_batched_generation_calls_are_fewer_than_per_criterion(self):
        criteria=[{'id':i+1,'code':f'RA2.{chr(97+i)}',
                   'description':f'Competencia {i} registros contables',
                   'outcome_weight':100,'criterion_weight':10} for i in range(10)]
        slots=logic.allocate_slots(criteria,10,'test',10)
        calls=[]
        def fake_chat(role,prompt,images=None):
            templates=json.loads(prompt.split('PLAN DE PREGUNTAS: ',1)[1].split('\n',1)[0])
            calls.append(len(templates))
            return {'questions':[{'number':s['number'],
                     'prompt':f'¿Cuál es la solución a la operación contable del CE {s["criterion_code"]} en el lote {len(calls)} y apartado {s["number"]}? ' + str(len(calls)*100+s['number'])*40,
                     'options':['A) Correcta','B) Incorrecta','C) Tercera','D) Cuarta'],
                     'correct_option':'A','ideal_answer':'Respuesta correcta A',
                     'rubric':[{'criterion':'respuesta correcta','weight_pct':100}]} for s in templates]},'simulado'
        progress=[]
        with patch.object(logic.ia,'chat',side_effect=fake_chat):
            models,bank,model=logic.build_exam_models('Examen','test',10,slots,3,'medio',progress=lambda a,b,c: progress.append((a,b,c)))
        self.assertEqual(len(bank),30)
        self.assertEqual([len(m) for m in models],[10,10,10])
        self.assertLessEqual(len(calls),5, f'Se hicieron {len(calls)} solicitudes, antes eran al menos 10')
        self.assertEqual(progress[-1][0:2],(30,30))
        codes=[[(q['criterion_id'],q['number']) for q in m] for m in models]
        self.assertEqual(codes[0],codes[1])
        self.assertEqual(len({logic.question_fingerprint(q['prompt']) for m in models for q in m}),30)

    def test_shared_passages_not_repeated_in_prompt(self):
        slots=[{'number':1,'criterion_id':1,'criterion_code':'RA1.a','criterion_description':'Define los activos',
                'kind':'test','points':5},
               {'number':2,'criterion_id':1,'criterion_code':'RA1.a','criterion_description':'Define los activos',
                'kind':'test','points':5}]
        passage={'id':22,'filename':'libro.txt','location_kind':'bloque','location_number':1,
                 'body':'La cuenta contable registra movimientos de la empresa. ' * 8,'material_id':2}
        generated={'number':1,'prompt':'¿Qué registra una cuenta contable?',
                   'options':['A) Movimientos','B) Productos','C) Horas','D) Clases'],
                   'correct_option':'A','ideal_answer':'Movimientos','rubric':[],
                   'source':{'passage_id':22,'evidence':'La cuenta contable registra movimientos'}}
        def fake_chat(role,prompt,images=None):
            self.assertEqual(prompt.count('PASO ID 22 |'),1)
            self.assertIn('PREGUNTA 2 (CE RA1.a): pasajes permitidos 22',prompt)
            return {'questions':[{**generated,'number':i} for i in (1,2)]},'simulado'
        with patch.object(logic.ia,'chat',side_effect=fake_chat):
            questions,_=logic.generate_exam('Prueba','test',10,slots,sources={1:[passage],2:[passage]})
        self.assertEqual(len(questions),2)

if __name__=='__main__':unittest.main()

class DocxOrderTests(unittest.TestCase):
    def test_paragraphs_and_table_cells_preserve_document_order(self):
        import tempfile
        from docx import Document
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'orden.docx'
            doc=Document()
            doc.add_paragraph('RA2: Reconoce operaciones en libros.')
            table=doc.add_table(rows=1,cols=2)
            table.cell(0,0).text='a)'
            table.cell(0,1).text='Se han registrado los asientos contables en los libros.'
            doc.add_paragraph('Fin de los criterios.')
            doc.save(path)
            text=logic.extract_program(path)
            self.assertLess(text.index('RA2:'),text.index('a)'))
            self.assertLess(text.index('a)'),text.index('Fin de los criterios.'))


class NumberedRaTests(unittest.TestCase):
    def test_official_numbered_ra_and_tabular_criterion(self):
        text=('Resultados de aprendizaje y criterios de evaluación\n'
              '1. Reconoce los elementos de un patrimonio económico clasificándolos correctamente.\n'
              'Criterios de evaluación:\n'
              'a) | Se han identificado las partes fundamentales del patrimonio empresarial.\n'
              'Duración: 55 horas.')
        reply={'outcomes':[{'code':'RA1',
               'description':'Reconoce los elementos de un patrimonio económico clasificándolos correctamente.',
               'weight':None,'criteria':[{'code':'RA1.a',
               'description':'Se han identificado las partes fundamentales del patrimonio empresarial.',
               'weight':None}]}]}
        with patch.object(logic.ia,'chat',return_value=(reply,'simulado')):
            result=logic.analyze_program(text)
        self.assertEqual(result['coverage']['ra_accepted'],1)
        self.assertEqual(result['coverage']['ce_accepted'],1)
