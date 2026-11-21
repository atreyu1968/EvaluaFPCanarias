"""Edición profesional ilustrada: cuatro PDF A4, portada, índice y capítulos paginados."""
from pathlib import Path
import argparse
import html
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
import fitz

ROOT=Path(__file__).resolve().parents[1]
NAVY=colors.HexColor('#173850')
TEAL=colors.HexColor('#087e80')
MUTED=colors.HexColor('#526a7b')
SOFT=colors.HexColor('#edf5f7')
WHITE=colors.white
VERSION='1.2.10-AG-CN-beta.5'
S={
'title':ParagraphStyle('title',fontName='Helvetica-Bold',fontSize=23,leading=27,textColor=NAVY,spaceAfter=10),
'cover':ParagraphStyle('cover',fontName='Helvetica-Bold',fontSize=33,leading=39,textColor=NAVY,spaceAfter=15),
'lead':ParagraphStyle('lead',fontName='Helvetica',fontSize=13,leading=18,textColor=MUTED,spaceAfter=12),
'heading':ParagraphStyle('heading',fontName='Helvetica-Bold',fontSize=12,leading=15,textColor=TEAL,spaceBefore=7,spaceAfter=3,keepWithNext=True),
'body':ParagraphStyle('body',fontName='Helvetica',fontSize=10.5,leading=14.6,textColor=NAVY,spaceAfter=6),
'step':ParagraphStyle('step',fontName='Helvetica',fontSize=10.5,leading=14.6,leftIndent=15,firstLineIndent=-15,textColor=NAVY,spaceAfter=5),
'caption':ParagraphStyle('caption',fontName='Helvetica',fontSize=8.3,leading=11,textColor=MUTED,spaceBefore=4,spaceAfter=8),
'index':ParagraphStyle('index',fontName='Helvetica',fontSize=11,leading=15,textColor=NAVY,spaceAfter=5),
'callout':ParagraphStyle('callout',fontName='Helvetica',fontSize=10,leading=14,textColor=NAVY),
}

# Each record: chapter title, screenshot key, purpose, numbered procedure, control.
COMMON=[
('Conoce tu espacio docente','inicio',
 'La pantalla de inicio organiza las cinco tareas habituales del profesor; la aplicación conserva el trabajo en el equipo.',
 ['Selecciona un módulo de trabajo y pulsa Seleccionar para fijarlo como contexto de tus tareas.',
  'Entra en Preparar el módulo para revisar el currículo y la programación. Escoge Crear una prueba cuando los criterios estén configurados.',
  'Recoge los trabajos del alumnado, revisa cada corrección y entra en Consultar el cuaderno para registrar o comprobar calificaciones.',
  'Pulsa Cambiar a modo avanzado para acceder a herramientas académicas y de almacenamiento. Cambiar de modo no altera notas ni documentos.'],
 'Comprueba siempre el ciclo, el grupo y el curso académico antes de introducir una evidencia. Los datos DEMO visibles en las capturas son ficticios.'),
('Alta de un módulo y programación','preparar',
 'El asistente admite una programación existente o un borrador nuevo. No presupone que todos los centros empleen una plantilla idéntica.',
 ['En Preparar módulo, crea un módulo con año académico, Canarias, ciclo, curso y grupo. Selecciona el módulo de referencia cuando esté disponible.',
  'Elige la opción de importar una programación o elaborar un borrador. Conserva el documento aprobado por el centro como referencia.',
  'Revisa cada RA, cada CE y su correspondencia con la normativa. Rectifica la extracción cuando sea inexacta y conserva las fuentes originales.',
  'Comprueba horas, calendario y unidades. Guarda la programación revisada y consulta el cuaderno para validar la política de evaluación.'],
 'El catálogo y la IA son ayudas de trabajo: la vigencia del currículo, las optativas y las horas deben contrastarse con las fuentes oficiales y la programación del centro.'),
('Diseño de exámenes y rúbricas','examenes',
 'Las pruebas se vinculan a resultados de aprendizaje y criterios de evaluación para que la corrección aporte evidencias curriculares.',
 ['Escoge el módulo, título y tipo de prueba. Marca los RA o CE que realmente vas a evaluar.',
  'En el asistente detallado configura dificultad, cantidad de preguntas, modelos y duración; adjunta materiales si procede.',
  'Si utilizas IA, revisa los enunciados, soluciones, rúbricas, puntos y referencias. No distribuyas una propuesta sin comprobarla.',
  'Genera los PDF disponibles y diferencia la documentación del alumnado de las soluciones reservadas al docente.'],
 'Verifica que cada pregunta aporta evidencia del CE seleccionado. En ejercicios fiscales de Canarias utiliza IGIC y confirma el tipo aplicable al supuesto.'),
('Registro de entregas','entregas',
 'El registro vincula cada trabajo al alumnado y a la prueba correspondiente. Los originales se conservan localmente.',
 ['En Cargar trabajos, selecciona el examen o modelo correcto. Selecciona el alumno por código e identidad contrastados.',
  'Añade los PDF o fotografías en orden. Comprueba que se leen las respuestas y no se han omitido páginas.',
  'Confirma la carga y comprueba que se muestra la entrega registrada. No dupliques el mismo trabajo por error.',
  'Abre Corregir trabajos y selecciona la entrega que acabas de comprobar.'],
 'Utiliza nombres de archivo que no expongan información innecesaria. Los documentos reales nunca deben utilizarse en una demostración pública.'),
('Visor y corrección asistida','correcciones',
 'El visor muestra los originales y las propuestas de corrección. Toda calificación sugerida por IA debe ser contrastada por el docente.',
 ['Selecciona la entrega en revisión y examina todas las páginas del original.',
  'Si cuentas con autorización para utilizar IA, solicita la transcripción; contrasta el texto con la imagen, especialmente cifras y signos.',
  'Revisa la rúbrica, las respuestas y los comentarios. Corrige errores de lectura, modifica la nota cuando proceda y documenta la decisión.',
  'Valida las correcciones y consulta el informe justificativo o el cuaderno. No repitas una llamada a la API sin necesidad.'],
 'La nota provisional no equivale a una calificación definitiva. El profesorado es responsable de validar las evidencias y la corrección.'),
('Cuaderno: configuración y calificaciones','evaluacion',
 'El cuaderno profesional separa configuración, unidades e instrumentos, registro de notas y revisión de resultados.',
 ['Abre Evaluación y confirma el módulo. Comprueba los pesos de RA y CE y las advertencias de coherencia.',
  'Valida expresamente la política de calificación conforme a la programación. Define unidades, trimestres e instrumentos y sus CE asociados.',
  'Registra notas manuales, importa un CSV o integra correcciones validadas. Identifica los criterios mediante RA/CE, por ejemplo RA1/a.',
  'Revisa la cobertura de evidencias; si falta una puntuación o una revisión de empresa, resuelve la incidencia antes de cerrar.'],
 'Un CE parcialmente evaluado no se considera superado por un mero redondeo. La aplicación no debe sustituir el juicio docente.'),
('Revisión final y exportación','evaluacion',
 'La nota calculable y el cierre docente son dos estados distintos. La exportación exige contrastar el significado de cada archivo.',
 ['Consulta los resultados de cada evaluación y el detalle por RA/CE. Comprueba alumnos, criterios y evidencias pendientes.',
  'Valida el cierre únicamente después de contrastar las evidencias y justificar la decisión. Una modificación posterior puede desactualizarlo.',
  'Abre Exportar informes y conectar con Additio. Escoge PDF individual, Excel, CSV o el paquete de configuración que corresponda.',
  'En Additio verifica códigos, relaciones RA/CE, pesos y orden de alumnos; distingue seguimiento provisional de calificación definitiva.'],
 'No uses la exportación provisional como si fuese un acta oficial. Mantén el informe de cierre y sus referencias en el expediente correspondiente.'),
('Herramientas avanzadas','avanzado',
 'El modo avanzado agrupa las herramientas que no forman parte del trabajo diario de todos los profesores.',
 ['Desde Inicio, abre herramientas avanzadas o utiliza el cambio de modo del menú lateral.',
  'Entra en Formación en empresa para planes, tutores, asistencia y valoraciones; en Expediente académico para revisar cierres y antecedentes.',
  'Consulta Decisiones académicas únicamente con hechos documentados; no adoptes una decisión automática a partir de una simulación.',
  'Accede a Editar RA, CE y pesos o IA y almacenamiento cuando necesites revisar la configuración.'],
 'Los registros de la aplicación complementan, pero no sustituyen, los procedimientos oficiales del centro ni las plataformas administrativas.'),
('Formación en empresa (FEOE)','feoe',
 'La aplicación permite conservar un seguimiento local de empresas, estancias, planes formativos y valoraciones de aprendizaje.',
 ['Registra la empresa o entidad, el centro de trabajo y el contacto profesional. Identifica al alumno y a ambos tutores.',
  'Introduce fechas, horas y horario y referencia los documentos contrastados. Selecciona el lugar de desarrollo de los RA y los CE asociados.',
  'Confirma el registro documental tras revisar la aplicabilidad de los requisitos; registra la asistencia efectiva y las incidencias.',
  'Transcribe la valoración cualitativa del tutor de empresa y revisa su integración en el módulo. Consulta las evidencias desde el cuaderno.'],
 'La confirmación local no autoriza una estancia ni emite un anexo oficial. Superado/no superado no se transforma automáticamente en nota numérica.'),
('Expediente y decisiones académicas','expediente',
 'El expediente agrupa cierres y antecedentes disponibles e identifica posibles datos incompletos o inconsistentes.',
 ['Selecciona el módulo de referencia, el alumno y la sesión correspondiente. Revisa cuidadosamente la identidad y las coincidencias de grupo.',
  'Comprueba módulos pendientes, ámbitos comunes, antecedentes de otros cursos y cierres vigentes.',
  'Contrasta la decisión académica con la normativa aplicable y las actas oficiales; documenta el acuerdo y su motivación.',
  'Conserva el informe interno cuando proceda. Si hay información ausente, no la des por supuesta ni cierres una decisión definitiva.'],
 'El registro local no constituye el expediente académico oficial ni acredita por sí solo promoción, titulación o acceso a empresa.'),
('Configuración de IA y privacidad','ajustes',
 'La gestión local no necesita una clave API. Las llamadas de IA sí transmiten información al proveedor seleccionado.',
 ['En Ajustes comprueba el proveedor, la URL y los modelos admitidos. Consulta las condiciones del servicio y la autorización del centro.',
  'Si decides usar una clave, guárdala mediante el mecanismo disponible. En modo portable usa una contraseña maestra robusta.',
  'No introduzcas datos personales innecesarios en los mensajes. Revisa permisos, costes y el resultado antes de validar.',
  'Comprueba las carpetas de SQLite, originales y copias. Usa un almacenamiento cifrado y protege el acceso físico al equipo.'],
 'La protección de la clave API no cifra la base de datos ni los documentos. La aplicación no garantiza por sí sola el cumplimiento de protección de datos.'),
('Copias de seguridad y recuperación','copias',
 'La copia ZIP contiene una instantánea SQLite, originales y un manifiesto de integridad SHA-256. Evita realizarla mientras grabas datos.',
 ['Accede a Ajustes > Almacenamiento y crea una copia ZIP. Guárdala en una ubicación segura distinta del dispositivo principal.',
  'Conserva el archivo completo. El manifiesto detecta alteraciones, pero no autentica el origen ni protege la confidencialidad.',
  'Abre Recuperar una copia de seguridad, selecciona una copia local compatible y confirma la recuperación independiente.',
  'Comprueba la carpeta nueva que devuelve la aplicación. No se sustituye la base activa. Cierra el programa y contrasta los datos antes de cambiar la configuración.'],
 'Las copias antiguas sin manifiesto no se restauran por este procedimiento. No borres la carpeta original y nunca recuperes copias de origen desconocido.'),
]

PLATFORMS={
'WINDOWS':('Manual de usuario','Windows 10/11 · x64',[
('Requisitos y preparación',None,'El archivo es un ejecutable portable para Windows de 64 bits. No necesita instalar Python.',
 ['Comprueba que el equipo utiliza Windows 10/11 x64 y dispone de Microsoft Edge WebView2 Runtime compatible.',
 'En GitHub Releases identifica el ZIP de Windows x64 correspondiente a la beta.5 cuando esté publicado. Descarga también su fichero SHA-256.',
 'En PowerShell ejecuta Get-FileHash -Algorithm SHA256 "ruta_del_paquete.zip" y compara la huella completa.',
 'Elige una carpeta local o USB escribible; conserva espacio suficiente y una copia externa de datos anteriores.'],
 'La beta no está firmada comercialmente. No desactives las protecciones de Windows ni las políticas TIC del centro.'),
('Extracción y primer arranque',None,'La configuración portable y el ejecutable deben permanecer juntos.',
 ['Extrae todos los archivos del ZIP en una carpeta nueva. No ejecutes el EXE desde el comprimido.',
 'Comprueba que EvaluaFPCanarias.exe y EvaluaFPCanarias.portable.json están juntos. Abre el EXE con doble clic.',
 'Verifica que se abre la ventana nativa y que la carpeta de datos indicada en Ajustes pertenece al dispositivo elegido.',
 'Crea un módulo ficticio; cierra y vuelve a iniciar. Comprueba que los datos persisten antes de usar información real.'],
 'Si no abre, consulta WebView2, permisos y registros de arranque de la carpeta de datos. No borres la instalación anterior.'),
]),
'LINUX':('Manual de usuario','Linux · x64',[
('Requisitos y preparación',None,'El paquete Linux se construye en Ubuntu 22.04 x64 y utiliza una interfaz gráfica compatible con Qt WebEngine.',
 ['Comprueba arquitectura x86-64 y una sesión gráfica funcional. La compatibilidad con todas las distribuciones no está garantizada.',
 'Descarga el TAR.GZ y su huella SHA-256 de la publicación preliminar beta.5 cuando esté disponible.',
 'En terminal ejecuta sha256sum archivo.tar.gz y compara el resultado con el fichero de huella.',
 'Usa una carpeta escribible en tu sesión de usuario. Conserva un respaldo externo de versiones anteriores.'],
 'No ejecutes la aplicación como root. Si faltan bibliotecas gráficas, consulta el departamento TIC y la documentación de tu distribución.'),
('Extracción y primer arranque',None,'El lanzador suministrado fija la ubicación portable y conserva la estructura del paquete.',
 ['Extrae mediante el gestor de archivos o tar -xzf archivo.tar.gz. Mantén la carpeta completa y las bibliotecas internas.',
 'Entra en la carpeta extraída. Si es necesario, concede permiso al lanzador con chmod +x INICIAR_EVALUAFP.sh.',
 'Ejecuta ./INICIAR_EVALUAFP.sh desde una terminal de la sesión gráfica. Comprueba la ventana de inicio.',
 'En Ajustes verifica rutas de datos y copias. Crea un módulo ficticio y reinicia para comprobar la persistencia.'],
 'Si falla, conserva el mensaje de terminal sin datos personales; comprueba bibliotecas Qt, los permisos y la arquitectura.'),
]),
'MACOS':('Manual de usuario','macOS · Intel y Apple Silicon',[
('Requisitos y elección del paquete',None,'Se distribuyen dos aplicaciones distintas para Mac, sin notarización de Apple; la construcción utiliza macOS 15.',
 ['Abre el menú Apple > Acerca de este Mac. Si aparece Procesador Intel selecciona macos_x64; si aparece Chip de Apple selecciona macos_arm64.',
 'Descarga el ZIP de la arquitectura correcta y su huella SHA-256 cuando se publique la beta.5.',
 'Ejecuta shasum -a 256 archivo.zip en Terminal y compara el resultado completo.',
 'Conserva la versión anterior y copia externa. Utiliza una carpeta escribible que no restrinja la escritura de datos.'],
 'No está garantizada la compatibilidad con sistemas anteriores. No desactives Gatekeeper de forma global. Consulta las políticas del centro ante avisos.'),
('Extracción y primer arranque',None,'El lanzador .command establece la ruta portable antes de abrir el ejecutable de la aplicación.',
 ['Extrae el ZIP completo sin separar la carpeta .app, el lanzador INICIAR_EVALUAFP.command y el archivo de configuración.',
 'Abre el lanzador incluido. Si macOS bloquea la apertura, comprueba la procedencia, la huella y los permisos conforme a las políticas TIC.',
 'Comprueba que se muestra la ventana y que la arquitectura corresponde a tu Mac.',
 'Abre Ajustes y verifica el almacenamiento. Crea un módulo ficticio, reinicia y comprueba los datos persistentes.'],
 'Ante un fallo conserva el diagnóstico sin datos personales. No modifiques globalmente las opciones de seguridad ni mezcles binarios de arquitecturas distintas.'),
]),
}

DIDACTIC=[
('Alcance curricular de la edición canaria','preparar','La edición se dirige a los cuatro ciclos de Administración y Gestión: CFGB Servicios Administrativos, CFGM Gestión Administrativa, CFGS Administración y Finanzas y CFGS Asistencia a la Dirección.',
 ['Identifica el ciclo, módulo, curso, año académico y grupo. Contrasta el plan formativo aplicable.',
 'Comprueba los resultados y criterios con la fuente oficial vigente y el acuerdo del departamento.',
 'No confundas un índice histórico o una propuesta de IA con una programación aprobada. Añade optativas y ajustes solo tras contrastarlos.',
 'Vincula las evidencias a los criterios reales y registra los cambios curriculares relevantes.'],
 'Estas capturas utilizan un grupo ficticio de Técnica Contable y descripciones inventadas para la demostración; no son transcripciones normativas.'),
('Supuesto práctico: ponderación por RA y CE','evaluacion','Ejemplo no normativo: dos RA al 50 % y dos CE al 50 % dentro de cada RA. Cada CE tiene un peso global del 25 %.',
 ['Si la programación prevé prueba al 60 % y portfolio al 40 % dentro de cada CE, registra ambos instrumentos y comprueba que suman 100 %.',
 'Para RA1/a, una prueba de 8 y portfolio de 6 dan 7,2. Para RA1/b, una prueba de 7 y portfolio de 9 dan 7,8.',
 'Si ambos CE están completos y la política aprobada lo permite, RA1 promedia 7,5. Repite el cálculo para RA2.',
 'Contrasta cobertura, mínimos y criterios de superación. Una evidencia ausente impide considerar completa la calificación.'],
 'Los pesos, umbrales y condiciones del ejemplo son ilustrativos, no obligatorios. La programación aprobada prevalece.'),
('Ámbitos comunes y recuperación en Grado Básico','avanzado','Las materias de ámbitos comunes utilizan competencias específicas y criterios, no el cuaderno RA/CE profesional.',
 ['Desde Preparar módulo selecciona la materia correspondiente. Confirma el currículo antes de crear actividades.',
 'En el cuaderno competencial registra evidencias observables y niveles; examina los planes de refuerzo y recuperación.',
 'Para la consolidación, contrasta materias, horas, sesión, calificaciones y acuerdo del equipo docente.',
 'Mantén las evidencias de recuperación y sus fuentes; registra la decisión motivada según el procedimiento oficial.'],
 'No transformes una media orientativa o un nivel competencial en una calificación oficial sin la revisión y el acuerdo que correspondan.'),
('Decisiones académicas: comprobación documental','decisiones','Los asistentes de promoción, permanencia, acceso a empresa y titulación ayudan a organizar datos confirmados.',
 ['Escoge la acción y revisa modalidad, curso y convocatoria. Comprueba las horas, requisitos, pendientes y situaciones especiales.',
 'Consulta las fuentes oficiales actuales y contrasta los datos con las actas, el expediente y los acuerdos del centro.',
 'Si una condición no se ha confirmado, déjala pendiente. No sustituyas las comprobaciones oficiales por el resultado de un cálculo.',
 'Conserva el acuerdo motivado y su referencia cuando proceda. Revisa cualquier cambio posterior en evidencias o antecedentes.'],
 'Las decisiones regladas corresponden a los órganos competentes. Los resultados de la aplicación son orientativos y requieren verificación jurídica.'),
]

ACCEPT=('Lista de comprobación y resolución de incidencias',None,
 'Realiza una prueba completa con datos ficticios antes de utilizar la beta.5 con información académica real.',
 ['Comprueba apertura, navegación, selector de módulo y persistencia después de reiniciar. Revisa que los originales y SQLite permanecen en las rutas elegidas.',
  'Prepara un módulo de demostración, crea una prueba, registra una entrega y valida una calificación de ensayo. Exporta un PDF y un Excel.',
  'Comprueba la entrada al cuaderno de ámbitos comunes, el modo avanzado, expediente y FEOE cuando proceda. Crea y recupera una copia de seguridad aislada.',
  'Ante un error registra sistema operativo, arquitectura, versión, pasos de reproducción y mensaje. No adjuntes nombres ni documentos reales.',
  'Consulta el repositorio de EvaluaFP Canarias para actualizaciones y comunica la incidencia con esos datos.'],
 'La compilación y la autoprueba de arranque no sustituyen la aceptación gráfica, funcional, pedagógica y documental en el entorno real.')

def p(text,style='body'):
    return Paragraph(html.escape(text),S[style])


def fig(story,screens,name,n):
    path=screens/(name+'.png')
    if not path.is_file():
        raise RuntimeError('Falta captura real: '+name)
    # Capturas del frontend real; se conservan proporciones.
    im=Image(str(path))
    ratio=im.imageHeight/im.imageWidth
    im.drawWidth=170*mm
    im.drawHeight=170*mm*ratio
    story.append(im)
    story.append(p('Figura '+str(n)+'. Interfaz beta.5 ejecutada en Chromium con datos ficticios. No representa el marco nativo del sistema operativo.','caption'))


def decor(canvas,doc):
    w,h=A4
    canvas.setFillColor(NAVY)
    canvas.rect(0,h-12*mm,w,12*mm,fill=1,stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont('Helvetica-Bold',8.5)
    canvas.drawString(20*mm,h-7.7*mm,'EVALÚAFP CANARIAS  /  ADMINISTRACIÓN Y GESTIÓN')
    canvas.setStrokeColor(TEAL)
    canvas.line(20*mm,16*mm,w-20*mm,16*mm)
    canvas.setFillColor(MUTED)
    canvas.setFont('Helvetica',8)
    canvas.drawString(20*mm,10*mm,VERSION+'  |  Versión preliminar')
    canvas.drawRightString(w-20*mm,10*mm,'Página '+str(doc.page))


def cover(canvas,doc):
    w,h=A4
    canvas.setFillColor(NAVY)
    canvas.rect(0,h-32*mm,w,32*mm,fill=1,stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont('Helvetica-Bold',15)
    canvas.drawString(20*mm,h-18*mm,'EvalúaFP Canarias')
    canvas.setFillColor(TEAL)
    canvas.rect(0,h-34*mm,w,2*mm,fill=1,stroke=0)
    canvas.setFillColor(MUTED)
    canvas.setFont('Helvetica',9)
    canvas.drawString(20*mm,16*mm,'Proyecto educativo  |  Documentación de usuario  |  Noviembre de 2026')


def build(name,screens,out):
    if name=='DIDACTICO_CANARIAS':
        title='Guía didáctica'
        subtitle='Administración y Gestión · Canarias'
        chapters=[DIDACTIC[0],COMMON[0],COMMON[1],DIDACTIC[1],
                  COMMON[2],COMMON[3],COMMON[4],COMMON[5],COMMON[6],
                  DIDACTIC[2],COMMON[8],COMMON[9],DIDACTIC[3],
                  COMMON[10],COMMON[11],ACCEPT]
    else:
        title,subtitle,first=PLATFORMS[name]
        chapters=first+COMMON+[ACCEPT]
    story=[Spacer(1,22*mm),p(title,'cover'),p(subtitle,'lead'),
           p('EDICIÓN ILUSTRADA · '+VERSION,'heading'),
           Spacer(1,5*mm)]
    fig(story,screens,'inicio',1)
    story.extend([Spacer(1,7*mm),p('Del currículo a la evaluación docente','title'),
                  p('Instalación, documentación, pruebas, evidencias, calificaciones, FEOE, almacenamiento y seguridad.','lead'),
                  p('Desarrollo: Francisco Javier González Rolo. Las capturas muestran datos exclusivamente ficticios y la interfaz web local en Chromium. Versión preliminar, pendiente de aceptación en equipos reales.'),
                  PageBreak(),p('Índice','title'),
                  p('Navegación del manual · los números corresponden a las páginas de esta edición.','lead')])
    for i,(heading,*_) in enumerate(chapters,1):
        story.append(p(f'{i:02d}. {heading}  ·····  {i+2}','index'))
    story.append(PageBreak())
    figure=1
    for i,(heading,screen,purpose,steps,control) in enumerate(chapters,1):
        story.extend([p(f'{i:02d}  /  {heading}','title'),p(purpose)])
        if screen:
            figure+=1
            fig(story,screens,screen,figure)
        story.append(p('Procedimiento','heading'))
        for j,step in enumerate(steps,1):
            story.append(p(str(j)+'. '+step,'step'))
        story.append(p('Control antes de continuar','heading'))
        t=Table([[p(control,'callout')]],colWidths=[170*mm])
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),SOFT),
          ('LINEBEFORE',(0,0),(0,-1),2,TEAL),('LEFTPADDING',(0,0),(-1,-1),10),
          ('RIGHTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),8),
          ('BOTTOMPADDING',(0,0),(-1,-1),8)]))
        story.append(t)
        if i<len(chapters):
            story.append(PageBreak())
    path=out/('EvaluaFPCanarias_beta5_'+name+'.pdf')
    doc=SimpleDocTemplate(str(path),pagesize=A4,leftMargin=20*mm,rightMargin=20*mm,
                           topMargin=20*mm,bottomMargin=22*mm,title=title+' · '+subtitle,
                           author='Francisco Javier González Rolo')
    doc.build(story,onFirstPage=cover,onLaterPages=decor)
    with fitz.open(path) as pdf:
        expected=len(chapters)+2
        if pdf.page_count!=expected:
            raise RuntimeError(f'{name}: {pdf.page_count} páginas, se esperaban {expected}; revisar maquetación')
        for i,page in enumerate(pdf):
            if len(page.get_text().strip())<80:
                raise RuntimeError('Página vacía: '+name+' '+str(i+1))
            page.get_pixmap(matrix=fitz.Matrix(1,1),alpha=False)
        # Verificar títulos e índice en la página esperada.
        for i,(heading,*_) in enumerate(chapters,1):
            if heading not in pdf[i+1].get_text().replace('\n',' '):
                raise RuntimeError('Título o índice fuera de posición: '+heading)
        print(path.name,pdf.page_count,'páginas verificadas')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,default=ROOT/'dist'/'manuales')
    parser.add_argument('--screens',type=Path,default=ROOT/'dist'/'manual_screens')
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    for name in ('WINDOWS','LINUX','MACOS','DIDACTICO_CANARIAS'):
        build(name,args.screens,args.out)

if __name__=='__main__':
    main()
