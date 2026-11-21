"""Regresión de las reglas académicas: datos de expediente ficticios."""
import unittest
from canarias_academic_decisions import evaluate

GB='CFGB Servicios Administrativos'
GM='CFGM Gestión Administrativa'
GS='CFGS Administración y Finanzas'


def query(action,cycle=GB,**kw):
    return evaluate({'cycle':cycle,'action':action,'academic_year':'2026-2027',
                     'modality':'presencial_ordinaria',**kw})


class AcademicDecisionTests(unittest.TestCase):
    def promotion(self,cycle=GB,session='extraordinaria',n=1,h='6',common=1,total='30',complete=True):
        return query('promotion',cycle,session=session,pending_modules=n,pending_hours=h,
                     pending_common=common,total_hours=total,record_complete=complete)['status']

    def test_gb_ordinaria_no_promocion_con_pendientes(self):
        self.assertEqual(self.promotion(session='ordinaria'),'extraordinaria')
        self.assertEqual(self.promotion(session='ordinaria',n=0,h=0,common=0),'cumple')

    def test_gb_extraordinaria_limites(self):
        self.assertEqual(self.promotion(),'posible')
        self.assertEqual(self.promotion(h='6.0001'),'no_cumple')
        self.assertEqual(self.promotion(common=2),'no_cumple')
        self.assertEqual(self.promotion(n=0,h=0,common=2),'posible')
        self.assertEqual(self.promotion(total=25),'revision')

    def test_gm_gs_limites_y_excepcion(self):
        for cycle in (GM,GS):
            self.assertEqual(self.promotion(cycle,n=2,h=6),'cumple')
            self.assertEqual(self.promotion(cycle,n=2,h='6.0001'),'no_cumple')
            self.assertEqual(self.promotion(cycle,n=1,h=7),'excepcion')
        self.assertEqual(self.promotion(complete=False),'pendiente')

    def test_permanencia(self):
        self.assertEqual(query('permanence',years_used=4,record_complete=True)['status'],'limite')
        self.assertEqual(query('permanence',GM,years_used=3,cycle_years=2,record_complete=True)['remaining'],1)

    def test_feoe_y_certificacion_especifica(self):
        raw={'course':2,'age_16':'superado','prl':'superado','annex_v':'superado',
             'specific_certificate':'no_requerido','conditions_confirmed':True}
        self.assertEqual(query('feoe',**raw)['status'],'cumple')
        self.assertEqual(query('feoe',**{**raw,'course':1})['status'],'no_cumple')
        self.assertEqual(query('feoe',**{**raw,'prl':'no_superado'})['status'],'no_cumple')
        self.assertEqual(query('feoe',**{**raw,'specific_certificate':'pendiente'})['status'],'pendiente')
        self.assertFalse(query('feoe',**raw)['official_decision'])

    def test_titulacion_no_anticipada(self):
        raw={'modules':'superado','project':'superado','common':'superado',
             'feoe':'superado','record_complete':True}
        self.assertEqual(query('graduation',**raw)['status'],'cumple')
        self.assertEqual(query('graduation',**{**raw,'feoe':'pendiente'})['status'],'pendiente')
        self.assertEqual(query('graduation',**{**raw,'common':'no_superado'})['status'],'no_cumple')
        self.assertEqual(query('graduation',GM,**{**raw,'project':'no_superado'})['status'],'no_cumple')

    def test_fuera_del_alcance(self):
        result=evaluate({'cycle':GB,'academic_year':'2025-2026','modality':'presencial_ordinaria','action':'promotion'})
        self.assertEqual(result['status'],'revision')
