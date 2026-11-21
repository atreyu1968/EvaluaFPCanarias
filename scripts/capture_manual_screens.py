"""Capturas reales del frontend beta.5 en Chromium, con una base temporal ficticia."""
from pathlib import Path
import argparse
import hashlib
import os
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def seed(app):
    from PIL import Image, ImageDraw
    data=app.data
    folder=data.STORAGE/'demo_manual'
    folder.mkdir(parents=True,exist_ok=True)
    original=folder/'respuesta_demo.jpg'
    im=Image.new('RGB',(850,1100),'white')
    draw=ImageDraw.Draw(im)
    draw.text((55,55),'EVALÚAFP CANARIAS - DOCUMENTO FICTICIO',fill='black')
    draw.text((55,100),'DEMO-01 | Técnica Contable | Pregunta 1',fill='black')
    draw.text((55,165),'Compra de mercaderías: 1.000 EUR + IGIC 7 %.',fill='black')
    draw.text((55,205),'Debe: compras 1.000; IGIC soportado 70.',fill='black')
    draw.text((55,245),'Haber: proveedores 1.070.',fill='black')
    for y in range(315,1030,45):
        draw.line((55,y,795,y),fill='#ccd5dd',width=1)
    im.save(original,quality=91)
    digest=hashlib.sha256(original.read_bytes()).hexdigest()
    with data.connect() as d:
        mid=d.execute('INSERT INTO modules(academic_year,cycle,name,group_name,created_at,territory) VALUES(?,?,?,?,?,?)',
            ('2026-2027','CFGM Gestión Administrativa','Técnica Contable','DEMO 1A',data.now(),'Canarias')).lastrowid
        for idx,description in enumerate(('Identifica elementos patrimoniales (ejemplo ficticio).','Registra operaciones contables (ejemplo ficticio).'),1):
            ra=d.execute('INSERT INTO outcomes(module_id,code,description,weight) VALUES(?,?,?,50)',
                         (mid,'RA'+str(idx),description)).lastrowid
            for code,desc in [('a','Interpreta los datos del supuesto.'),('b','Verifica la solución obtenida.')]:
                cid=d.execute('INSERT INTO criteria(outcome_id,code,description,weight) VALUES(?,?,?,50)',(ra,code,desc)).lastrowid
                if idx==1 and code=='a':
                    first=cid
        sid=d.execute('INSERT INTO students(module_id,code,name) VALUES(?,?,?)',(mid,'DEMO-01','Alumno/a ficticio 01')).lastrowid
        d.execute('INSERT INTO students(module_id,code,name) VALUES(?,?,?)',(mid,'DEMO-02','Alumno/a ficticio 02'))
        eid=d.execute('INSERT INTO exams(module_id,title,kind,total_points,created_at,status) VALUES(?,?,?,?,?,?)',
                    (mid,'Prueba de demostración · Registro contable','desarrollo',10,data.now(),'draft')).lastrowid
        d.execute('INSERT INTO exam_questions(exam_id,criterion_id,number,kind,prompt,points) VALUES(?,?,?,?,?,?)',
                (eid,first,1,'desarrollo','Registra la compra ficticia indicada.',10))
        sub=d.execute('INSERT INTO submissions(exam_id,student_id,storage_path,status,created_at) VALUES(?,?,?,?,?)',
                    (eid,sid,str(folder),'received',data.now())).lastrowid
        fid=d.execute('INSERT INTO source_files(submission_id,sequence,original_name,local_path,mime,sha256,page_count) VALUES(?,?,?,?,?,?,1)',
                    (sub,1,original.name,str(original),'image/jpeg',digest)).lastrowid
        d.execute('INSERT INTO pages(submission_id,file_id,page_number,source_page,image_path,sha256) VALUES(?,?,1,1,?,?)',
                    (sub,fid,str(original),digest))
    return mid


def capture(destination):
    from playwright.sync_api import sync_playwright
    destination=Path(destination).resolve()
    destination.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='efp_manual_demo_') as temp:
        os.environ['EVALUAFP_CANARIAS_PORTABLE_HOME']=temp
        os.environ['EVALUAFP_CANARIAS_PORTABLE']='1'
        os.environ.pop('EVALUAFP_CANARIAS_DATA_DIR',None)
        import app
        server,url=app.start()
        try:
            mid=seed(app)
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True)
                page=browser.new_page(viewport={'width':1440,'height':980},device_scale_factor=1,
                                      locale='es-ES')
                page.goto(url+'?launch='+app.TOKEN,wait_until='networkidle')
                page.wait_for_function("typeof window.page === 'function'")
                def shot(name,section,advanced=False,selector=None):
                    page.evaluate("""async args => {
                       S.advanced=args.advanced; syncMode();
                       S.moduleId=args.mid; S.evaluationModuleId=args.mid; S.examModuleId=args.mid;
                       await window.page(args.section);
                    }""",{'advanced':advanced,'mid':mid,'section':section})
                    page.wait_for_load_state('networkidle')
                    page.wait_for_function("""() => document.querySelector('#main') &&
                       !document.querySelector('#main .loading') &&
                       !document.querySelector('#main').innerText.includes('No se ha podido abrir esta pantalla') &&
                       document.querySelector('#main').innerText.trim().length > 20""",timeout=20000)
                    if selector:
                        page.locator(selector).first.scroll_into_view_if_needed()
                    else:
                        page.evaluate('window.scrollTo(0,0)')
                    page.screenshot(path=str(destination/(name+'.png')),animations='disabled')
                    print('Captura real:',name)
                shot('inicio','inicio')
                shot('preparar','preparar')
                shot('examenes','examenes')
                shot('entregas','entregas')
                shot('correcciones','correcciones')
                shot('evaluacion','evaluacion')
                shot('avanzado','inicio',True)
                shot('feoe','feoe',True)
                shot('expediente','expediente',True)
                shot('decisiones','decisiones',True)
                shot('ajustes','ajustes',True)
                shot('copias','ajustes',True,'#main a[href="/api/backup"]')
                browser.close()
        finally:
            server.shutdown()
            server.server_close()


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,required=True)
    capture(parser.parse_args().out)
