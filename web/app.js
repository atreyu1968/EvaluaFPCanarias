'use strict';
const S = {page:'inicio', modules:[], moduleId:null, moduleDetails:null, exams:[], examId:null,
  examModuleId:null, examDetails:null, submissions:[], subId:null, subDetails:null,
  uploadExamId:null, uploadStudentId:null, queue:[], pageIndex:0, proposal:null, aiSettings:null, busy:false, manualDraft:null};
S.calendarVersions=null;S.calendarVersionDiff=null;S.generalCalendarLibrary=null;S.generalCalendarDiff=null;S.calendarDocumentPreview=null;S.calendarDocumentModuleId=null;S.calendarAiPreview=null;S.calendarAiModuleId=null;S.calendarAiFragment='';
S.boeCandidates=null;S.boeInspection=null;S.boeSelectedId='';S.nationalDocumentPreview=null;
S.curriculumHistory=null;S.curriculumHistoryDiff=null;S.normativeMonitor=null;S.calendarVersions=null;S.calendarVersionDiff=null;S.curriculumSourceFile=null;S.curriculumSourceKind='';
S.todofpTitleSearch=null;S.todofpTitleGrade='Superior';S.todofpTitleQuery='';
S.catalogResults=null;S.catalogPreview=null;S.catalogPreviewScope=null;S.catalogTableText='';S.catalogPicked=null;S.curriculumReview=null;S.feoeMinimumPreview=null;S.aiPreview=null;S.unitProposal=null;S.autoProposedModuleId=null;S.importPreview=null;S.preparePath=null;S.prepareStep=0;S.wizardDraft=null;S.prepareInfo=null;S.advanced=false;S.creatingModule=false;
const E = s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const V = v=>v==null?'No indicada':String(v)+' %';
const $ = sel=>document.querySelector(sel);
const $all = sel=>[...document.querySelectorAll(sel)];
const token=$('meta[name="app-token"]').content;
function startIntro(){
 const overlay=$('#intro-overlay');if(!overlay)return;
 overlay.hidden=true;return; // El inicio guiado sustituye al cartel temporal obligatorio.
 let remaining=10;let timer=null;
 function dismiss(){if(timer)clearInterval(timer);overlay.hidden=true;}
 $('#dismiss-intro')?.addEventListener('click',dismiss);
 timer=setInterval(()=>{remaining=Math.max(0,remaining-1);const el=$('#intro-count');if(el)el.textContent=String(remaining);if(!remaining)dismiss();},1000);
}
/** Solicita crear uno o varios alumnos, sin dar de alta ninguno hasta confirmar. */
function promptNewStudents(moduleId,codes=[]){
 return new Promise(resolve=>{
  const dialog=$('#students-dialog'),form=$('#students-create-form');
  const fields=$('#students-dialog-fields'),err=$('#students-dialog-error');
  const values=codes.length?codes:[''];
  $('#students-dialog-title').textContent=codes.length?'Alumnos no registrados: '+codes.length:'Crear alumno';
  $('#students-dialog-help').textContent=codes.length?
    'Estos códigos aparecen en el ZIP pero no en el módulo. Escriba el nombre y apellidos de cada alumno para continuar con la importación. No se ha guardado ningún examen todavía.':
    'Introduzca el código y el nombre del alumno. Se incorporará al módulo actual.';
  $('#save-students').textContent=codes.length?'Crear alumnos y continuar':'Guardar alumno';
  err.hidden=true;err.textContent='';
  fields.innerHTML=values.map((code,i)=>`<div class="student-field-grid">
    <div class="field"><label for="new-code-${i}">Código</label><input id="new-code-${i}" data-student-code required maxlength="60" pattern="[A-Za-z0-9][A-Za-z0-9_.-]*" value="${E(code)}" ${codes.length?'readonly':''}></div>
    <div class="field"><label for="new-name-${i}">Nombre y apellidos</label><input id="new-name-${i}" data-student-name required maxlength="160" autocomplete="off" placeholder="Nombre y apellidos"></div>
  </div>`).join('');
  let settled=false;
  const finish=value=>{if(settled)return;settled=true;form.removeEventListener('submit',submit);$('#cancel-students').removeEventListener('click',cancel);dialog.removeEventListener('cancel',onCancel);if(dialog.open)dialog.close();resolve(value);};
  const cancel=()=>finish(null),onCancel=(ev)=>{ev.preventDefault();finish(null)};
  const submit=async ev=>{
    ev.preventDefault();ev.stopPropagation();
    if(!form.reportValidity())return;
    const codes=[...fields.querySelectorAll('[data-student-code]')];
    const names=[...fields.querySelectorAll('[data-student-name]')];
    const students=codes.map((input,i)=>({code:input.value.trim(),name:names[i].value.trim()}));
    const btn=$('#save-students');btn.disabled=true;err.hidden=true;
    try{
      const result=await API('/api/students/bulk','POST',{module_id:Number(moduleId),students});
      finish(result.created);
    }catch(e){err.textContent=e.message;err.hidden=false;}finally{btn.disabled=false;}
  };
  form.addEventListener('submit',submit);
  $('#cancel-students').addEventListener('click',cancel);
  dialog.addEventListener('cancel',onCancel);
  dialog.showModal();fields.querySelector('[data-student-name]')?.focus();
 });
}

// Todas las consultas tienen un límite. Las lecturas de una pantalla anterior
// se cancelan al navegar para que no sobrescriban la pantalla nueva.
let navigationController = null;
let navigationRevision = 0;
async function API(path, method='GET', payload=null){
 const isRead=method.toUpperCase()==='GET';
 const timeout=path==='/api/backup/recover'?600000:isRead ? 20000 : (path.includes('/api/programming-builder/propose')||path.includes('/api/programming-builder/improve')||path.includes('/api/programming-builder/enrich-units') ? 240000 : 180000);
 const controller=new AbortController();
 const navigationSignal=isRead ? navigationController?.signal : null;
 const onNavigationAbort=()=>controller.abort('navigation');
 if(navigationSignal){
   if(navigationSignal.aborted)controller.abort('navigation');
   else navigationSignal.addEventListener('abort',onNavigationAbort,{once:true});
 }
 const timer=setTimeout(()=>controller.abort('timeout'),timeout);
 const opts={method,headers:{'X-App-Token':token},signal:controller.signal};
 if(payload instanceof FormData)opts.body=payload;
 else if(payload!==null){opts.headers['Content-Type']='application/json';opts.body=JSON.stringify(payload);}
 try{
   let res;
   try{res=await fetch(path,opts);}catch(e){
     if(controller.signal.aborted){
       if(controller.signal.reason==='navigation')throw Error('La consulta anterior se canceló al cambiar de pantalla.');
       throw Error('La consulta ha superado el tiempo máximo de espera. Comprueba la conexión con EvalúaFP e inténtalo de nuevo.');
     }
     throw Error('Sin comunicación con el servicio local: '+e.message);
   }
   let body;
   try{body=await res.json();}catch(e){
     if(controller.signal.aborted)throw Error(controller.signal.reason==='navigation'?'Consulta cancelada al navegar.':'Tiempo de espera agotado.');
     throw Error('El servicio local devolvió una respuesta no válida. HTTP '+res.status);
   }
   if(!res.ok){const err=Error(body?.error||'Error HTTP '+res.status);err.code=body?.code;err.module_id=body?.module_id;err.missing_students=body?.missing_students;throw err;}
   return body;
 }finally{
   clearTimeout(timer);
   if(navigationSignal)navigationSignal.removeEventListener('abort',onNavigationAbort);
 }
}
function toast(text,err=false){const root=$('#toast');if(!root)return;while(root.children.length>=2)root.firstElementChild.remove();let el=document.createElement('div');el.className='toast'+(err?' error':'');el.textContent=text;root.append(el);setTimeout(()=>el.remove(),4300);}
function setLoading(text){$('#main').innerHTML='<div class="loading">'+E(text||'Cargando…')+'</div>';}
async function busy(work,ok){
 if(S.busy)return;
 S.busy=true;let original=document.body.style.cursor;document.body.style.cursor='progress';
 try{const result=await work();if(ok)toast(ok);return result;}
 catch(e){console.error(e);toast(e.message||'Error no identificado',true);return null;}
 finally{S.busy=false;document.body.style.cursor=original;}
}
function titles(){return {feoe:'Formación en empresa',expediente:'Expediente académico',decisiones:'Decisiones académicas',inicio:'Mi espacio docente',preparar:'Preparar mi módulo',programaciones:'Edición avanzada de la programación',examenes:'Exámenes y rúbricas',
 entregas:'Registro de entregas',correcciones:'Visor y correcciones',evaluacion:'Evaluación del módulo',ajustes:'Configuración local e IA'};}
async function page(name){
 const revision=++navigationRevision;
 if(navigationController)navigationController.abort('navigation');
 navigationController=new AbortController();
 S.page=name;
 if(['feoe','expediente','decisiones','programaciones','ajustes'].includes(name)){S.advanced=true;syncMode();}
 $('#page-title').textContent=titles()[name]||name;
 $all('[data-page]').forEach(el=>el.classList.toggle('active',el.dataset.page===name));
 setLoading();
 try{
 const supported=['inicio','preparar','programaciones','examenes','entregas','correcciones','evaluacion','ajustes','decisiones','expediente','feoe'];
 if(!supported.includes(name))throw Error('No se reconoce la sección solicitada: '+name);
 if(name==='inicio')await viewHome();
 if(name==='decisiones')await viewAcademicDecisions();
 if(name==='expediente')await viewCycleRecord();
 if(name==='feoe')await viewFeoe();
 if(name==='preparar')await viewPrepare();
 if(name==='programaciones')await viewPrograms();
 if(name==='examenes')await viewExams();
 if(name==='entregas')await viewUploads();
 if(name==='correcciones')await viewCorrections();
 if(name==='ajustes')await viewSettings();
 if(name==='evaluacion')await viewEvaluation();
 }catch(ex){
  if(revision!==navigationRevision)return;
  console.error(ex);
  $('#main').innerHTML='<section class="panel"><h2>No se ha podido abrir esta pantalla</h2><p class="hint danger-note">'+E(ex?.message||'Error desconocido')+'</p><div class="actions"><button type="button" class="btn secondary" data-action="retry-page">Reintentar</button><button type="button" class="btn mutedbtn" data-page="inicio">Volver al inicio</button></div></section>';
 }
}
async function listModules(){S.modules=await API('/api/modules');return S.modules;}
async function listExams(){S.exams=await API('/api/exams');return S.exams;}
async function listSubs(){S.submissions=await API('/api/submissions');return S.submissions;}
function opt(items,sel,fn){return items.map(i=>`<option value="${E(i.id)}" ${String(i.id)===String(sel)?'selected':''}>${E(fn(i))}</option>`).join('');}
function empty(msg){return `<div class="empty">${E(msg)}</div>`;}
function labelStatus(status){const map={received:'Recibido',transcribed:'Transcrito',proposed:'Pendiente de validación',validated:'Validado'};
 return `<span class="status ${E(status)}">${E(map[status]||status)}</span>`;}
function intro(text){return `<p class="lead">${E(text)}</p>`;}
function academicDecisionFields(action){
 const field=(label,body)=>`<div class="field"><label>${label}</label>${body}</div>`;
 const state=(name,label)=>field(label,`<select name="${name}"><option value="pendiente">Pendiente de comprobar</option><option value="superado">Sí / superado</option><option value="no_superado">No / no superado</option></select>`);
 const num=(name,label,max,step='1',min='0')=>field(label,`<input name="${name}" type="number" min="${min}" max="${max}" step="${step}" required>`);
 const check=(name,label)=>`<label class="checkbox-card"><input type="checkbox" name="${name}"> ${label}</label>`;
 if(action==='promotion')return field('Sesión final',`<select name="session"><option value="ordinaria">Ordinaria / final de primero GM y GS</option><option value="extraordinaria">Extraordinaria de GB</option></select>`)+num('pending_modules','Número de módulos profesionales pendientes a efectos de promoción',100)+num('pending_hours','Horas semanales de los módulos pendientes',2000,'0.0001')+num('total_hours','Carga horaria semanal total de primero (misma unidad)',2000,'0.0001','0.0001')+num('pending_common','Ámbitos comunes no superados (solo GB; en ordinaria cuenta cualquier materia insuficiente)',2)+`<p class="small">En GM/GS excluye del recuento los módulos en que solo queda pendiente la FEOE y se han alcanzado los RA del centro. Esta comprobación se refiere a primero → segundo, no a itinerarios de tres cursos.</p>`+check('record_complete','He comprobado todo el expediente, las horas y los criterios de promoción aplicables.');
 if(action==='permanence')return num('years_used','Cursos académicos de permanencia consumidos',20)+check('record_complete','He contrastado el expediente y las renuncias o autorizaciones aplicables.');
 if(action==='feoe')return field('Curso',`<select name="course"><option value="1">Primero</option><option value="2">Segundo</option></select>`)+state('age_16','Edad mínima de 16 años al inicio de la estancia')+state('prl','Competencias preventivas necesarias')+state('annex_v','Valoración colegiada de PRL documentada y aplicable')+field('Certificación específica solicitada por la empresa',`<select name="specific_certificate"><option value="pendiente">Requerida o sin comprobar</option><option value="no_requerido">No requerida</option><option value="expedido">Expedida por el centro</option></select>`)+check('conditions_confirmed','He comprobado plan formativo, condiciones de incorporación y calendario.');
 return state('modules','Todos los módulos profesionales, incluidos pendientes de primero')+state('common','Todos los ámbitos comunes (solo GB)')+state('project','Proyecto intermodular')+field('FEOE',`<select name="feoe"><option value="pendiente">Pendiente</option><option value="superado">Superada</option><option value="no_superado">No superada</option><option value="exencion_resuelta">Exención concedida y contrastada, cuando proceda</option></select>`)+check('record_complete','He comprobado la totalidad del expediente y la procedencia de las exenciones.');
}
function cycleRecordMarkup(r){
 const table=rows=>rows.length?`<div class="tablewrap"><table><thead><tr><th>Módulo / materia</th><th>Estado</th><th>Calificación registrada</th><th>Observaciones</th></tr></thead><tbody>${rows.map(x=>`<tr><td>${E(x.name)}${x.group?` · ${E(x.group)}`:''}</td><td>${E(x.status.replaceAll('_',' '))}</td><td>${E(x.score??'—')}</td><td>${E(x.warning||'')}${x.closure_id?' · Registro '+Number(x.closure_id):''}</td></tr>`).join('')}</tbody></table></div>`:empty('Sin registros vinculables.');
 return `<section class="panel"><h2>${E(r.student.name)} · ${E(r.student.code)}</h2><p>${E(r.cycle)} · ${r.course}.º · ${E(r.group)} · ${E(r.academic_year)} · ${E(r.session)}</p><p class="hint warning">${E(r.notice)} Los acuerdos de ámbito pueden repetirse en las materias que lo integran; no se cuentan como notas independientes.</p><p><a href="${E(r.index_source)}" target="_blank" rel="noopener noreferrer">Índice de referencia</a></p>${table(r.items)}
 ${r.unclassified.length?`<h3>Registros sin clasificación inequívoca</h3><ul>${r.unclassified.map(x=>`<li>${E(x.name)} · ${Number(x.id)}</li>`).join('')}</ul>`:''}
 ${r.course===2?`<h3>Antecedentes candidatos de primero</h3><p>Contrasta su convocatoria, identidad, equivalencias y validez en el expediente oficial.</p>${table(r.previous_candidates)}`:''}
 <p class="small">Huella del expediente: ${E(r.sha256)}</p></section>
 <section class="panel"><h2>Registrar actuación o acuerdo motivado</h2><p>Los datos de la comprobación se introducen tras revisar el expediente completo. La aplicación no determina automáticamente pendientes, horas ni exenciones a partir de este índice histórico.</p><form id="cycle-record-action"><select name="action"><option value="permanence" ${S.cycleRecordAction==='permanence'?'selected':''}>Permanencia</option><option value="feoe" ${S.cycleRecordAction==='feoe'?'selected':''}>Formación en empresa</option>${r.course===1?`<option value="promotion" ${S.cycleRecordAction==='promotion'?'selected':''}>Promoción</option>`:`<option value="graduation" ${S.cycleRecordAction==='graduation'?'selected':''}>Titulación</option>`}</select><button type="submit" class="btn secondary">Seleccionar</button></form>
 <form id="cycle-record-agreement" class="formgrid">${academicDecisionFields(S.cycleRecordAction||'permanence').replace(/<div class="field"><label>Sesión final<\/label>[\s\S]*?<\/div>/,'')}<div class="field"><label>Acuerdo, actuación o revisión motivada</label><textarea name="agreement" maxlength="8000" required></textarea></div><div class="field"><label>Referencia de la sesión o documento</label><input name="meeting_ref" maxlength="500" required></div><label class="checkbox-card"><input type="checkbox" name="teacher_confirmed" required> He contrastado el expediente oficial y la actuación registrada. No constituye acta oficial.</label><button type="submit" class="btn">Comprobar y registrar</button></form><div id="cycle-decision-result"></div></section>
 <section class="panel"><h2>Historial de actuaciones del expediente seleccionado</h2>${r.records.length?r.records.map(x=>`<details><summary>${E(x.created_at)} · ${E(x.action)} · ${E(x.result.status)} · ${x.current_snapshot?'Misma instantánea':'Instantánea anterior o convocatoria distinta'}</summary><p>${E(x.result.reason)}</p><p>${E(x.agreement)}</p><p>${E(x.meeting_ref)}</p><p><a href="/api/cycle-record/agreement.html?module_id=${Number(r.module_id)}&amp;student_id=${Number(r.student.id)}&amp;record_id=${Number(x.id)}">Descargar informe interno imprimible</a></p></details>`).join(''):empty('Sin actuaciones registradas en este módulo de referencia.')}</section>`;
}
async function viewCycleRecord(){
 await listModules();
 const roster=S.cycleRecordRoster,report=S.cycleRecordReport;
 $('#main').innerHTML=`<section class="welcome-card"><p class="welcome-kicker">CANARIAS · SEGUIMIENTO DEL CICLO</p><h2>Expediente académico interno</h2><p>Consulta módulos y ámbitos del mismo grupo sin mezclar notas provisionales y definitivas. Los antecedentes se contrastan con el expediente oficial.</p></section>
 <section class="panel"><form id="cycle-record-roster"><div class="field"><label>Módulo de referencia (del grupo y curso)</label><select name="module_id" required>${opt(S.modules,roster?.module.id||S.moduleId,m=>m.name+' · '+m.academic_year+' · '+(m.group_name||'Sin grupo'))}</select></div><button type="submit" class="btn secondary">Consultar alumnado</button></form>
 ${roster?`<form id="cycle-record-report" class="formgrid"><div class="field"><label>Alumno en ${E(roster.module.name)}</label><select name="student_id" required>${opt(roster.students,report?.student.id,x=>x.name+' · '+x.code)}</select></div><div class="field"><label>Convocatoria de consulta</label><select name="session"><option value="ordinaria" ${report?.session==='ordinaria'?'selected':''}>Ordinaria</option><option value="extraordinaria" ${report?.session==='extraordinaria'?'selected':''}>Extraordinaria</option></select></div><button type="submit" class="btn">Consultar expediente</button></form>`:''}</section>${report?cycleRecordMarkup(report):''}`;
}
async function viewAcademicDecisions(){
 const actions={promotion:'Promoción de primero a segundo',permanence:'Permanencia',feoe:'Acceso a formación en empresa',graduation:'Titulación'};
 const action=S.academicAction||'promotion';
 $('#main').innerHTML=`<section class="welcome-card"><p class="welcome-kicker">CANARIAS · CURSO 2026–2027</p><h2>Comprobación de decisiones académicas</h2><p>Asistente de consulta para ciclos A&amp;G de dos cursos, nueva ordenación presencial ordinaria. Introduce datos contrastados. No se guardan datos personales ni se emiten actas, certificados o decisiones oficiales.</p></section>
 <section class="panel"><form id="academic-action"><div class="field"><label>Comprobación</label><select name="action">${Object.entries(actions).map(([k,v])=>`<option value="${k}" ${action===k?'selected':''}>${E(v)}</option>`).join('')}</select></div><button class="btn secondary" type="submit">Seleccionar</button></form></section>
 <section class="panel"><form id="academic-evaluate" class="formgrid"><div class="field"><label>Ciclo</label><select name="cycle" required>${agCycleOptions()}</select></div>${academicDecisionFields(action)}<button class="btn" type="submit">Comprobar requisitos</button></form><div id="academic-result"></div></section>`;
}
function feoeDetail(info){
 if(!info.stay)return '';
 const st=info.stay,targets=info.targets,selected=new Set(targets.map(t=>t.outcome_id));
 const fields=(name,label)=>`<div class="field"><label>${label}</label><input name="${name}" required maxlength="500"></div>`;
 const check=`<label class="checkbox-card"><input type="checkbox" name="teacher_confirmed" required> Confirmo haber contrastado la documentación.</label>`;
 return `<section class="panel"><h2>Plan de estancia ${Number(st.id)}</h2><p>${E(st.start_date)} a ${E(st.end_date)} · ${E(st.regime)} · ${E(st.planned_hours)} h previstas / ${E(info.actual_hours)} h registradas.</p><p>Tutor del centro: ${E(st.center_tutor)} · Tutor de empresa: ${E(st.company_tutor)}</p><p>${E(st.schedule)}</p><p>${E(info.notice)}</p><details><summary>Referencias documentales</summary><ul>${Object.entries(st.documents).map(([k,v])=>`<li>${E(k)}: ${E(v||'Pendiente')}</li>`).join('')}</ul></details>
 ${!info.confirmation?`<form id="feoe-target" class="formgrid"><h3>Incorporar RA al plan</h3><div class="field"><label>Resultado de aprendizaje</label><select name="outcome_id" required>${opt(info.curriculum.filter(r=>!selected.has(r.id)),null,r=>r.module_name+' · '+r.code+' · '+r.description.slice(0,85))}</select></div><details><summary>Consultar criterios e identificadores</summary>${info.curriculum.filter(r=>!selected.has(r.id)).map(r=>`<p><b>${E(r.module_name)} · ${E(r.code)}</b></p><ul>${r.criteria.map(c=>`<li>ID ${Number(c.id)} · ${E(c.code)} · ${E(c.description)}</li>`).join('')}</ul>`).join('')}</details><div class="field"><label>ID de CE (separados por comas, opcional)</label><input name="criterion_ids"></div><div class="field"><label>Lugar</label><select name="location"><option value="empresa">Empresa</option><option value="compartido">Centro y empresa</option><option value="centro">Centro</option></select></div><div class="field"><label>Actividades previstas</label><textarea name="activities" required maxlength="8000"></textarea></div><button type="submit" class="btn">Añadir RA</button></form><form id="feoe-confirm" class="formgrid"><h3>Confirmación documental del plan</h3>${fields('reference','Referencia del plan firmado y contrastado')}${check}<button type="submit" class="btn secondary">Confirmar registro del plan</button></form>`:'<p>Plan confirmado documentalmente. Las modificaciones requieren revisión del centro.</p>'}</section>
 <section class="panel"><h2>Resultados de aprendizaje del plan</h2>${targets.length?targets.map(t=>`<details><summary>${E(t.snapshot.module_name)} · ${E(t.snapshot.code)} · ${E(t.location)} · ${E(t.valuations[0]?.status||'Sin valoración')}</summary><p>${E(t.snapshot.description)}</p><p>${E(t.activities)}</p><ul>${t.snapshot.criteria.filter(c=>t.snapshot.selected_criterion_ids.includes(c.id)).map(c=>`<li>${E(c.code)} · ${E(c.description)}</li>`).join('')}</ul>
 ${info.confirmation&&t.location!=='centro'?`<form id="feoe-valuation-${Number(t.id)}" data-target="${Number(t.id)}" class="formgrid"><div class="field"><label>Valoración del tutor de empresa</label><select name="status"><option value="superado">Superado</option><option value="no_superado">No superado</option></select></div>${fields('report_ref','Referencia del informe del tutor de empresa')}<div class="field"><label>Observaciones</label><textarea name="observations" required maxlength="4000"></textarea></div>${check}<button class="btn" type="submit">Registrar valoración</button></form>`:''}
 ${t.valuations.map((v,i)=>`<p>${E(v.created_at)} · ${E(v.status)} · ${E(v.report_ref)} · ${E(v.observations)}</p>${v.reviews.map(r=>`<p>Revisión docente: ${E(r.notes)} · ${E(r.created_at)}</p>`).join('')}${i===0?`<form id="feoe-review-${Number(v.id)}" data-valuation="${Number(v.id)}" class="formgrid"><div class="field"><label>Integración de la evidencia en la evaluación (sin nota automática)</label><textarea name="notes" required maxlength="4000"></textarea></div>${check}<button class="btn secondary" type="submit">Registrar revisión docente</button></form>`:''}`).join('')}</details>`).join(''):empty('No hay RA en el plan.')}</section>
 <section class="panel"><h2>Asistencia</h2>${info.confirmation?`<form id="feoe-attendance" class="formgrid"><div class="field"><label>Fecha</label><input type="date" name="day" min="${E(st.start_date)}" max="${E(st.end_date)}" required></div><div class="field"><label>Horas efectivas</label><input type="number" name="hours" min="0" max="24" step="0.01" required></div><div class="field"><label>Estado</label><select name="status"><option value="asistencia">Asistencia</option><option value="parcial">Parcial</option><option value="ausencia_justificada">Ausencia justificada</option><option value="ausencia_no_justificada">Ausencia no justificada</option></select></div><div class="field"><label>Observaciones</label><textarea name="notes" maxlength="4000"></textarea></div><button type="submit" class="btn">Registrar día</button></form>`:''}<p>Horas efectivas: ${E(info.actual_hours)}. Las revisiones del mismo día no duplican horas.</p><ul>${info.attendance.map(a=>`<li>${E(a.day)} · ${E(a.status)} · ${E(a.hours)} h</li>`).join('')}</ul><details><summary>Historial de asistencia</summary><ul>${info.attendance_history.map(a=>`<li>${E(a.day)} · ${E(a.hours)} h · ${E(a.status)} · ${E(a.notes)} · ${E(a.created_at)}</li>`).join('')}</ul></details></section>`;
}
async function viewFeoe(){
 await listModules();
 const info=await API('/api/feoe'+(S.feoeStay?'?stay_id='+Number(S.feoeStay):'')),roster=S.feoeRoster;
 const input=(name,label,optional=false)=>`<div class="field"><label>${label}</label><input name="${name}" ${optional?'':'required'} maxlength="500"></div>`;
 $('#main').innerHTML=`<section class="welcome-card"><p class="welcome-kicker">CANARIAS · FORMACIÓN EN EMPRESA</p><h2>Seguimiento FEOE</h2><p>Registro local complementario a GDCAN. No sustituye convenios, anexos, autorizaciones ni la evaluación docente.</p><p>${info.sources.map(u=>`<a href="${E(u)}" target="_blank" rel="noopener noreferrer">Normativa ${E(u.split('/').slice(-2).join('/'))}</a>`).join(' · ')}</p></section>
 <section class="panel"><h2>Empresas colaboradoras</h2><form id="feoe-company" class="formgrid">${input('name','Empresa / organismo equiparado')}${input('workplace','Centro de trabajo')}${input('contact','Contacto profesional (opcional)',true)}<button type="submit" class="btn secondary">Registrar empresa</button></form><ul>${info.companies.map(c=>`<li>${E(c.name)} · ${E(c.workplace)}</li>`).join('')}</ul></section>
 <section class="panel"><h2>Nueva estancia</h2><form id="feoe-roster"><div class="field"><label>Módulo de referencia del grupo</label><select name="module_id" required>${opt(S.modules,roster?.module.id,m=>m.name+' · '+m.academic_year+' · '+(m.group_name||'Sin grupo'))}</select></div><button type="submit" class="btn secondary">Consultar alumnado</button></form>
 ${roster&&info.companies.length&&roster.students.length?`<form id="feoe-stay" class="formgrid"><div class="field"><label>Alumno</label><select name="student_id">${opt(roster.students,null,x=>x.name+' · '+x.code)}</select></div><div class="field"><label>Empresa</label><select name="company_id">${opt(info.companies,null,x=>x.name+' · '+x.workplace)}</select></div>${input('center_tutor','Tutor del centro')}${input('company_tutor','Tutor de empresa')}<div class="field"><label>Régimen</label><select name="regime"><option value="general">General</option><option value="intensivo">Intensivo</option></select></div><div class="field"><label>Inicio</label><input type="date" name="start_date" required></div><div class="field"><label>Fin</label><input type="date" name="end_date" required></div><div class="field"><label>Horas previstas</label><input type="number" name="planned_hours" min="0.01" max="2000" step="0.01" required></div><div class="field"><label>Horario y calendario previsto</label><textarea name="schedule" required maxlength="4000"></textarea></div>${[['convenio','Convenio'],['plan','Plan formativo'],['prl','Acreditación de competencias PRL'],['anexo_v','Anexo V o constancia de aplicabilidad'],['edad','Comprobación de edad'],['incorporacion','Autorización o constancia documental de incorporación']].map(([k,l])=>input(k,l)).join('')}<button type="submit" class="btn">Registrar estancia</button></form>`:''}</section>
 <section class="panel"><h2>Estancias registradas</h2><form id="feoe-select"><select name="stay_id">${opt(info.stays,S.feoeStay,x=>x.student_name+' · '+x.company_name+' · '+x.start_date)}</select><button type="submit" class="btn secondary">Abrir estancia</button></form></section>${feoeDetail(info)}`;
}
function syncMode(){
 $('#advanced-nav').hidden=!S.advanced;
 const toggle=$('#toggle-advanced');toggle.textContent=S.advanced?'Cambiar a modo guiado':'Cambiar a modo avanzado';
 toggle.setAttribute('aria-expanded',String(S.advanced));
 document.body.classList.toggle('advanced-mode',S.advanced);
}
async function viewHome(){
 await listModules();
 const selected=S.modules.find(m=>Number(m.id)===Number(S.moduleId))||S.modules[0];
 S.moduleId=selected?.id||null;
 const tasks=[['preparar','1','Preparar el módulo','Configurar currículo, programación y criterios.'],['examenes','2','Crear una prueba','Preparar actividades, exámenes y rúbricas.'],['entregas','3','Recoger trabajos','Registrar entregas para revisar.'],['correcciones','4','Corregir trabajos','Revisar y validar las correcciones.'],['evaluacion','5','Consultar el cuaderno','Registrar calificaciones y consultar el progreso.']];
 const advanced=[['feoe','Formación en empresa'],['expediente','Expediente académico'],['decisiones','Decisiones académicas'],['programaciones','Editar RA, CE y pesos'],['ajustes','IA, almacenamiento y copias']];
 $('#main').innerHTML=`<section class="welcome-card compact-welcome"><p class="welcome-kicker">ADMINISTRACIÓN Y GESTIÓN · CANARIAS</p><h2>${selected?'¿Qué necesitas hacer hoy?':'Empieza por preparar tu primer módulo'}</h2><p>${selected?'Selecciona el módulo y la tarea. Los datos se guardan localmente.':'Puedes importar una programación o crear un borrador guiado.'}</p><div class="welcome-module">Modo ${S.advanced?'avanzado':'guiado'}</div></section>
 ${selected?`<section class="panel home-context"><form id="home-context" class="formrow"><div class="field grow"><label for="home-module">Módulo de trabajo</label><select name="module_id" id="home-module">${opt(S.modules,selected.id,m=>m.name+' · '+m.group_name+' · '+m.academic_year)}</select></div><button type="submit" class="btn secondary">Seleccionar</button></form><p class="small">${E(selected.cycle)} · ${E(selected.territory)}</p></section>`:''}
 <section class="panel home-workflow"><h2>Tu trabajo paso a paso</h2>${tasks.map(([page,step,title,description],i)=>`<button type="button" class="workflow-task" data-action="home-task" data-target="${page}"><span class="workflow-number">${step}</span><span class="workflow-text"><strong>${E(title)}</strong><small>${E(description)}</small></span><span class="workflow-arrow">›</span></button>`).join('')}</section>
 ${S.advanced?`<section class="panel"><h2>Herramientas avanzadas</h2><div class="advanced-grid">${advanced.map(([page,title])=>`<button type="button" class="btn secondary" data-page="${page}">${E(title)}</button>`).join('')}</div></section>`:`<section class="panel"><h2>¿Necesitas otras herramientas?</h2><p class="small">Formación en empresa, expediente, decisiones y configuración están disponibles en modo avanzado.</p><button type="button" class="btn secondary" data-action="home-advanced">Abrir herramientas avanzadas</button></section>`}
 <p class="small">Las propuestas de IA y los cálculos requieren revisión del docente. No se modifica ninguna calificación por cambiar de modo.</p>`;
}
/* 1.1 — Preparación curricular sin JSON ni decisiones automáticas no confirmadas. */
const TERRITORY_NAMES=['Canarias'];
function territoryOptions(selected){return (!selected?'<option value="" disabled selected>Seleccione la comunidad autónoma o ciudad</option>':'')+TERRITORY_NAMES.map(name=>`<option value="${E(name)}" ${String(selected)===name?'selected':''}>${E(name)}</option>`).join('');}

const AG_CYCLES=[
  {name:'CFGB Servicios Administrativos',grade:'Grado Básico'},
  {name:'CFGM Gestión Administrativa',grade:'Grado Medio'},
  {name:'CFGS Administración y Finanzas',grade:'Grado Superior'},
  {name:'CFGS Asistencia a la Dirección',grade:'Grado Superior'}
];
function agCycleOptions(){
 return '<option value="" selected disabled>Seleccione un ciclo de Administración y Gestión</option>'+
   AG_CYCLES.map(c=>'<option value="'+E(c.name)+'">'+E(c.grade+' · '+c.name.replace(/^CFG[BMS]+\s+/,''))+'</option>').join('');
}

async function loadAGModuleSuggestions(form){
 const list=form.querySelector('#ag-module-list'),pick=form.querySelector('#ag-module-pick'),note=form.querySelector('#ag-module-note'),source=form.querySelector('#ag-module-source');
 if(!list||!pick||!note)return;
 const cycle=form.elements.cycle?.value||'',year=form.elements.academic_year?.value||'',course=form.querySelector('#ag-course-filter')?.value||'';
 list.innerHTML='';pick.innerHTML='<option value="">Seleccione primero un ciclo</option>';
 if(source)source.textContent='';
 if(!cycle){note.textContent='Seleccione un ciclo para consultar sus módulos.';return;}
 note.textContent='Consultando el índice documental de módulos de Canarias…';
 try{
   const url='/api/canarias-ag/modules?cycle='+encodeURIComponent(cycle)+
       '&academic_year='+encodeURIComponent(year)+'&territory=Canarias'+
       (course?'&course='+encodeURIComponent(course):'');
   const data=await API(url);
   if(!form.isConnected||form.elements.cycle?.value!==cycle||form.elements.academic_year?.value!==year||
      (form.querySelector('#ag-course-filter')?.value||'')!==course)return;
   const modules=data.modules||[];
   list.innerHTML=modules.map(m=>'<option value="'+E(m.name)+
      '" label="'+E((m.code||'Sin código RD')+' · '+m.course+'º · '+m.reference_annual_hours+' h (referencia de 2024)')+'"></option>').join('');
   pick.innerHTML='<option value="">Seleccione un módulo o escríbalo manualmente</option>'+
      modules.map(m=>'<option value="'+E(m.name)+'" data-reference-code="'+E(m.code||'')+
          '" data-reference-course="'+Number(m.course)+'">'+
          E((m.code||'Sin código RD')+' · '+m.name+' · '+m.course+'º')+'</option>').join('');
   const regulation=data.state_title_regulation||{};
   if(source&&/^https:\/\/www\.boe\.es\/eli\/es\/rd\//.test(regulation.url||'')){
     source.innerHTML='<a href="'+E(regulation.url)+'" target="_blank" rel="noopener noreferrer">Consultar norma estatal del título</a> · '+
       E(regulation.title||'BOE')+'. Referencia para contrastar RA/CE: no acredita por sí sola el currículo autonómico vigente.';
   }
   const annex=cycle.startsWith('CFGB')?'V':'VI';
   note.textContent=data.count+' referencias del anexo '+annex+' de 2024'+
      (course?' para '+course+'º curso':'')+'. La lista no acredita la vigencia para '+year+
      ', ni importa automáticamente horas, RA o CE. Compruebe la normativa de su módulo.';
 }catch(err){
   if(form.isConnected)note.textContent='No se ha podido consultar el índice. Escriba la denominación del módulo manualmente.';
 }
}
function agReferencePanel(ref){
 if(!ref)return '';
 return `<section class="panel" aria-label="Procedencia documental del módulo">
 <h3>Referencia documental conservada (pendiente de revisión)</h3>
 <p><strong>${E(ref.course)}.º · ${E(ref.module_code||'Sin código RD')} · ${E(ref.module_name)}</strong></p>
 <p>Distribución orientativa de ${E(ref.reference_academic_year)}: ${E(ref.reference_annual_hours)} horas anuales y ${E(ref.reference_weekly_hours)} horas semanales. <b>No son horas confirmadas del curso actual.</b></p>
 <p class="small"><a href="${E(ref.source_url)}" target="_blank" rel="noopener noreferrer">Consultar anexo de origen</a>
 (${E(ref.source_title)}, p. ${E(ref.source_page)}).
 <a href="${E(ref.state_title_url)}" target="_blank" rel="noopener noreferrer">Consultar norma estatal del título</a>.</p>
 <p class="hint warning">El índice de 2024 no verifica su vigencia actual. No se han incorporado ni confirmado resultados de aprendizaje, criterios de evaluación, ponderaciones u horas lectivas a partir de esta referencia.</p>
 </section>`;
}
function resolveAGCycle(text){
 const norm=String(text||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
 if(norm.includes('servicios administrativos'))return 'CFGB Servicios Administrativos';
 if(norm.includes('gestion administrativa'))return 'CFGM Gestión Administrativa';
 if(norm.includes('administracion y finanzas'))return 'CFGS Administración y Finanzas';
 if(norm.includes('asistencia a la direccion'))return 'CFGS Asistencia a la Dirección';
 return '';
}
function calendarVacationLines(cfg){return (cfg?.vacation_periods||[]).map(x=>`${x.start};${x.end};${x.label}`).join('\n');}
function calendarHolidayLines(cfg){return (cfg?.regional_non_teaching_days||[]).map(x=>`${x.date};${x.reason}`).join('\n');}
function readVacationLines(text){return String(text||'').split(/\r?\n/).map(x=>x.trim()).filter(Boolean).map(line=>{
 const parts=line.split(';');if(parts.length<2||parts.length>3)throw Error('Escriba los periodos como AAAA-MM-DD;AAAA-MM-DD;Motivo.');
 return {start:parts[0].trim(),end:parts[1].trim(),label:(parts[2]||'Vacaciones/no lectivo').trim()};
});}
function readHolidayLines(text){return String(text||'').split(/\r?\n/).map(x=>x.trim()).filter(Boolean).map(line=>{
 const n=line.indexOf(';');if(n===-1)throw Error('Escriba cada festivo como AAAA-MM-DD;Motivo.');
 return {date:line.slice(0,n).trim(),reason:line.slice(n+1).trim()};
});}
const WD_FIELDS=['source_type','region','official_module_code','official_cycle_code','fp_regime','curriculum_source_url','curriculum_source_description','center','teacher','department','academic_context','normative_references',
 'objectives','competencies','methodology','resources','inclusion','assessment','instruments','recovery','enterprise','observations',
 ...['justification','center_characteristics','student_characteristics','environment_context','identification_data',
 'qualifications','contents','learning_activities','interdisciplinarity','extracurricular','assessment_sessions',
 'grading','promotion','attendance','extraordinary_assessment']];
const GUIDE_STEPS=['Identificación','Normativa y objetivos','Metodología','Evaluación','Temporalización y FEOE','Revisión y exportación'];
const AI_EDITABLE_FIELDS=new Set(['justification','academic_context','center_characteristics','student_characteristics','environment_context',
 'objectives','competencies','qualifications','contents','learning_activities','methodology','interdisciplinarity',
 'inclusion','resources','assessment','instruments','grading','assessment_sessions','recovery','extraordinary_assessment',
 'attendance','enterprise','extracurricular','observations','normative_references']);
function aiToolbar(){
 return `<section class="guide-ai-panel"><strong>Asistente de redacción de la programación</strong>
 <p>Los apartados se rellenan inicialmente con propuestas locales editables. Si autorizas el envío de los RA y CE a tu proveedor de IA configurado, puedes obtener una redacción desarrollada sin transmitir datos del alumnado ni del profesorado.</p>
 <div class="actions"><button class="btn secondary" type="button" data-action="prepare-ai-all">Desarrollar todos los apartados con IA</button>
 <button class="btn mutedbtn" type="button" data-action="prepare-ai-local">Completar campos vacíos sin IA</button></div>
 <p class="small">La normativa y las horas se obtienen de fuentes identificadas, no de invenciones de IA. Solo se sustituyen los textos locales iniciales, nunca los modificados por el docente.</p></section>`;
}
function aiPreviewPanel(){
 const p=S.aiPreview;
 if(!p)return '';
 return `<section class="panel guide-ai-review" role="region" aria-label="Revisar nueva redacción"><h3>Revisar mejora de «${E(p.field)}»</h3>
 <p class="small">El texto original se conserva hasta que aceptes la sugerencia. Puedes modificar la propuesta antes de aplicarla.</p>
 <details><summary>Ver redacción original</summary><pre class="guide-ai-original">${E(p.original)}</pre></details>
 <label for="guide-ai-proposal">Texto sugerido por IA</label><textarea id="guide-ai-proposal" rows="8" maxlength="12000">${E(p.proposal)}</textarea>
 <div class="actions"><button type="button" class="btn" data-action="guide-ai-accept">Aplicar redacción revisada</button>
 <button type="button" class="btn mutedbtn" data-action="guide-ai-discard">Conservar texto del profesor</button></div></section>`;
}
function applyAssistantFields(result,mode='base'){
 if(!S.wizardDraft||!result||!result.fields)return {applied:0,skipped:0};
 S.wizardDraft.assistant_meta=S.wizardDraft.assistant_meta||{};
 let applied=0,skipped=0;
 for(const [key,text] of Object.entries(result.fields)){
   if(!WD_FIELDS.includes(key)||typeof text!=='string'){skipped++;continue;}
   const old=String(S.wizardDraft[key]||'');const meta=S.wizardDraft.assistant_meta[key];
   const isLocalDraft=meta&&!meta.teacher_edited&&String(meta.origin||'').startsWith('Plantillas locales');
   if(!old.trim()||(mode==='ai'&&isLocalDraft)){
     S.wizardDraft[key]=text;
     S.wizardDraft.assistant_meta[key]={origin:result.source||'Propuesta local',teacher_edited:false};applied++;
   }else skipped++;
 }
 return {applied,skipped};
}

function guideWeights(info){
 const ras=info.outcomes||[],ces=info.criteria||[];
 const automatic=ras.length>0&&ras.every(r=>r.weight_origin==='default')&&ces.every(c=>c.weight_origin==='default');
 return `<fieldset class="guide-fieldset guide-weights"><legend>Cuadrícula de RA, CE y ponderaciones</legend>
 <p class="small">Puedes dejar la ponderación automática, que da el mismo valor global a cada CE, o desactivarla y editar todos los pesos. Los CE de cada RA y el conjunto de RA deben sumar 100,00 %.</p>
 <label class="guide-confirm"><input type="checkbox" id="guide-automatic-weights" ${automatic?'checked':''}> Ponderación automática por número de CE</label>
 <div class="guide-weight-scroll"><table class="guide-weight-table"><caption>Distribución de RA y CE confirmados</caption>
 <thead><tr><th>RA</th><th>CE asociado</th><th>Peso del RA (%)</th><th>Peso del CE dentro del RA (%)</th></tr></thead><tbody>
 ${ras.map(ra=>{const mine=ces.filter(c=>Number(c.outcome_id)===Number(ra.id));return mine.map((ce,i)=>`<tr data-weight-ra-row="${Number(ra.id)}">
 <td>${i?'<span class="small">↳</span>':`<strong>${E(ra.code)}</strong>`}</td>
 <td><strong>${E(ce.code)}</strong><span class="small" title="${E(ce.description)}">${E(ce.description.slice(0,60))}</span></td>
 <td>${i?'':`<input data-weight-ra="${Number(ra.id)}" type="number" step="0.01" min="0.01" max="100" value="${ra.weight==null?'':Number(ra.weight).toFixed(2)}" ${automatic?'disabled':''}>`}</td>
 <td><input data-weight-ce="${Number(ce.id)}" data-weight-parent="${Number(ra.id)}" type="number" step="0.01" min="0.01" max="100" value="${ce.weight==null?'':Number(ce.weight).toFixed(2)}" ${automatic?'disabled':''}></td></tr>`).join('');}).join('')}
 </tbody></table></div>
 <div class="actions"><button type="button" class="btn secondary" data-action="guide-save-weights">Confirmar ponderaciones</button></div>
 <p class="small">La modificación queda registrada y no se aplicará si ya hay calificaciones finales cerradas.</p></fieldset>`;
}
function guideField(name,label,hint='',rows=3){
 const value=E(S.wizardDraft?.[name]||'');
 const meta=S.wizardDraft?.assistant_meta?.[name];
 const origin=meta?(meta.teacher_edited?'Modificado por docente':meta.origin):'';
 return `<div class="field guide-field"><div class="guide-field-heading"><label for="guide-${name}">${E(label)}</label>
 ${AI_EDITABLE_FIELDS.has(name)?`<button class="btn mutedbtn smallbtn" type="button" data-action="prepare-ai-improve" data-field="${E(name)}">Mejorar redacción con IA</button>`:''}</div>
 ${rows===1?`<input id="guide-${name}" name="${name}" value="${value}" maxlength="12000">`:
 `<textarea id="guide-${name}" name="${name}" rows="${rows}" maxlength="12000">${value}</textarea>`}
 ${origin?`<span class="small guide-origin">Origen: ${E(origin)}</span>`:''}
 ${hint?`<small class="small">${E(hint)}</small>`:''}</div>`;
}
function fmtOfficialDate(value){
 const s=String(value||'');return /^\d{8}$/.test(s)?s.slice(6,8)+'/'+s.slice(4,6)+'/'+s.slice(0,4):s;
}
function boeDiscoveryPanel(){
 const found=S.boeCandidates;
 const inspect=S.boeInspection;
 return `<section class="guide-calendar-summary"><h3>Buscar legislación estatal por ciclo (BOE)</h3>
 <p class="small">Consulta opcional a la base de legislación consolidada del BOE. No envía textos docentes ni información del alumnado. Solo muestra normas candidatas; confirma el título, módulo y disposiciones de tu comunidad autónoma.</p>
 <div class="actions"><button class="btn secondary" type="button" data-action="national-boe-search">Buscar normas del ciclo en el BOE</button>
 <div class="field" style="flex:1;min-width:220px"><label>O introducir identificador BOE-A-AAAA-NNN</label><input id="national-boe-id" value="${E(S.boeSelectedId||'')}" placeholder="BOE-A-2011-19533"></div>
 <button class="btn secondary" type="button" data-action="national-boe-inspect">Comprobar identificación y modificaciones</button></div>
 ${found?`<div class="guide-review-line"><strong>${found.records.length} normas candidatas</strong> · ${E(found.academic_year)}
 <p class="small">${E(found.notice)}</p>
 ${found.records.length?`<div class="guide-weight-scroll"><table class="guide-metrics-table"><thead><tr><th>Norma</th><th>Fecha de publicación</th><th>Opciones</th></tr></thead><tbody>
 ${found.records.map(r=>`<tr><td><b>${E(r.id)}</b><br>${E(r.title)}</td><td>${E(fmtOfficialDate(r.publication_date||'Consultar BOE'))}</td><td><button class="btn mutedbtn smallbtn" type="button" data-action="national-boe-pick" data-boe-id="${E(r.id)}">Revisar</button><a href="${E(r.url)}" target="_blank" rel="noopener noreferrer">Ver BOE</a></td></tr>`).join('')}
 </tbody></table></div>`:'<p class="hint warning">La búsqueda no encontró normas consolidadas. No significa que el título no exista. Consulta el BOE y el boletín autonómico con los enlaces oficiales.</p>'}</div>`:''}
 ${inspect?`<div class="guide-review-line"><h4>Norma consultada: ${E(inspect.id)}</h4>
 <p><b>${E(inspect.title)}</b></p><p>Publicación: ${E(fmtOfficialDate(inspect.publication_date||'No proporcionada'))}. Última actualización informada: ${E(fmtOfficialDate(inspect.last_update||'No proporcionada'))}.</p>
 <p><b>Estado de consolidación informado:</b> ${E(inspect.consolidation_state||'No indicado')} · <b>Relaciones posteriores publicadas:</b> ${Number(inspect.reported_amendment_count||0)}</p>
 ${(inspect.reported_amendments||[]).length?`<details><summary>Consultar normas que modifican o afectan a esta disposición</summary><ul>${inspect.reported_amendments.map(ref=>`<li><a href="${E(ref.url)}" target="_blank" rel="noopener noreferrer">${E(ref.id)}</a> · ${E(ref.type||'Relación normativa')} · ${E(ref.title||'')}</li>`).join('')}</ul></details>`:'<p class="small">La consulta no devuelve relaciones posteriores identificables; esto no significa que no existan modificaciones.</p>'}
 <p class="small">${E(inspect.notice)}</p>
 <div class="actions"><a href="${E(inspect.url)}" target="_blank" rel="noopener noreferrer">Abrir la norma en el BOE</a>
 <button class="btn secondary" type="button" data-action="national-boe-add">Añadir a mi borrador como norma pendiente de revisión</button></div></div>`:''}
 </section>`;
}
function catalogCreationForm(){return $('#prepare-create')||$('#create-module');}
function catalogScopeFromForm(){
 const form=catalogCreationForm();if(!form)throw Error('Abra primero el formulario de creación de un módulo.');
 return {region:form.elements.territory?.value||'',academic_year:form.elements.academic_year?.value.trim()||''};
}
function catalogResultsMarkup(){
 const data=S.catalogResults;
 const preview=S.catalogPreview;
 return `${data?`<p class="small">${data.count} módulos encontrados para ${E(data.territory)} · ${E(data.academic_year)}. ${E(data.notice)}</p>
 ${data.entries?.length?`<div class="guide-weight-scroll"><table class="guide-metrics-table"><thead><tr><th>Ciclo y código</th><th>Módulo</th><th>Procedencia</th><th></th></tr></thead><tbody>
 ${data.entries.map(entry=>`<tr><td><b>${E(entry.title_name)}</b><br>${E(entry.title_code)} · ${E(entry.grade)} · ${E(entry.family)}</td><td>${E(entry.module_code)} · ${E(entry.module_name)}</td><td><a href="${E(entry.source_url)}" target="_blank" rel="noopener noreferrer">Consultar fuente</a></td>
 <td><button type="button" class="btn mutedbtn smallbtn" data-action="catalog-choose" data-catalog-id="${entry.id}">Utilizar módulo</button></td></tr>`).join('')}</tbody></table></div>`:'<p class="hint">No existen fichas locales que coincidan. Puedes introducir el módulo manualmente o importar una tabla confirmada por el centro.</p>'}`:'<p class="small">Busca módulos que otro docente haya contrastado en este equipo. No son un catálogo oficial nacional completo.</p>'}
 ${preview?`<div class="guide-review-line"><p><strong>Vista previa: ${preview.count} módulos de ${preview.titles} títulos</strong>. ${E(preview.notice)}</p>
 <div class="guide-weight-scroll"><table class="guide-metrics-table"><thead><tr><th>Código título / ciclo</th><th>Código módulo / nombre</th><th>Grado y familia</th></tr></thead><tbody>
 ${preview.rows.slice(0,20).map(x=>`<tr><td>${E(x.title_code)} · ${E(x.cycle)}</td><td>${E(x.module_code)} · ${E(x.module)}</td><td>${E(x.grade)} · ${E(x.family)}</td></tr>`).join('')}
 </tbody></table></div><p class="small">${preview.count>20?'Se muestran las primeras 20 filas; se comprobarán todas al importar.':''} Comprueba que la tabla pertenece a la comunidad y curso que has seleccionado.</p>
 <button class="btn" type="button" data-action="catalog-import">Guardar filas confirmadas en el catálogo local</button></div>`:''}`;
}
function updateCatalogResults(){const el=$('#catalog-results');if(el)el.innerHTML=catalogResultsMarkup();}
function todofpTitlesPanel(place){
 const data=S.todofpTitleSearch;
 return `<div class="guide-calendar-details" id="todofp-title-index"><h4>Encontrar el ciclo en el índice estatal de TodoFP</h4>
 <p class="small">Elige el grado y escribe parte del nombre: no es necesario conocer ni pegar la dirección web de la ficha. Los códigos de título y las horas deben comprobarse en la disposición autonómica.</p>
 <div class="formgrid"><div class="field"><label for="todofp-title-grade">Tipo de oferta</label>
 <select id="todofp-title-grade">${['Básico','Medio','Superior','Especialización'].map(v=>`<option ${v===S.todofpTitleGrade?'selected':''}>${E(v)}</option>`).join('')}</select></div>
 <div class="field"><label for="todofp-title-query">Buscar por nombre del ciclo o especialización</label>
 <input id="todofp-title-query" maxlength="120" value="${E(S.todofpTitleQuery||'')}" placeholder="Ej.: Administración y Finanzas"></div></div>
 <div class="actions"><button type="button" class="btn secondary" data-action="todofp-search-titles">Buscar títulos en TodoFP</button></div>
 ${data?`<p class="small"><strong>${data.count} coincidencias</strong> · ${E(data.grade)} · ${E(data.territory)} · ${E(data.academic_year)}. ${E(data.notice)}</p>
 ${data.results?.length?`<div class="guide-weight-scroll"><table class="guide-metrics-table"><thead><tr><th>Título localizado</th><th>Opciones</th></tr></thead><tbody>
 ${data.results.map((v,i)=>`<tr><td><strong>${E(v.name)}</strong><br><span class="small">Código del título: pendiente de verificar</span></td><td>
 <button type="button" class="btn mutedbtn smallbtn" data-action="todofp-open-title" data-title-index="${i}">Examinar módulos y fuentes</button>
 <a href="${E(v.url)}" target="_blank" rel="noopener noreferrer">Abrir ficha</a></td></tr>`).join('')}</tbody></table></div>`:'<p class="hint">No se han encontrado títulos con ese texto en el índice consultado. Prueba otro nombre o utiliza el enlace manual de más abajo.</p>'}
 ${data.truncated?'<p class="small">Se muestra un máximo de 65 resultados. Acota la búsqueda.</p>':''}`:''}</div>`;
}
function todofpExplorerPanel(place){
 const result=S.todofpResult;
 const allowed=result&&result.region&&(place==='catalog'||place==='builder');
 return `<section class="guide-calendar-summary" id="todofp-explorer"><h3>Consultar ficha estatal de un ciclo y sus currículos autonómicos (TodoFP)</h3>
 ${todofpTitlesPanel(place)}
 <p class="small">O pega el enlace HTTPS de la ficha del ciclo en el portal oficial TodoFP. La aplicación localizará los módulos indicados y, cuando existan, los enlaces a currículo y modificaciones de tu comunidad. <b>Esta ficha no acredita horas, códigos ausentes ni implantación territorial.</b></p>
 <div class="actions"><div class="field" style="flex:1;min-width:260px"><label>Enlace oficial del ciclo o de su página «Currículos CCAA»</label>
 <input id="todofp-url" type="url" maxlength="700" value="${E(S.todofpURL||'')}" placeholder="https://www.todofp.es/que-estudiar/familias-profesionales/...html"></div>
 <button class="btn secondary" type="button" data-action="todofp-explore">Consultar fuentes del territorio y curso</button></div>
 ${allowed?`<div class="guide-review-line"><p><b>${result.profile?E(result.profile.title):'Currículos autonómicos'}</b> · ${E(result.region)} · ${E(result.academic_year)}</p>
 ${result.profile?`<p>${result.profile.modules_count} módulos identificados en la ficha estatal. Los códigos en blanco no se han inventado.</p>
 <div class="guide-weight-scroll"><table class="guide-metrics-table"><thead><tr><th>Código indicado</th><th>Módulo</th>${place==='catalog'?'<th>Acción</th>':''}</tr></thead><tbody>
 ${result.profile.modules.slice(0,35).map((m,i)=>`<tr><td>${E(m.code||'Sin código en esta ficha')}</td><td>${E(m.name)}${m.optional?' · Optativo':''}</td>
 ${place==='catalog'?`<td><button type="button" class="btn mutedbtn smallbtn" data-action="todofp-select-module" data-todofp-index="${i}">Utilizar nombre</button></td>`:''}</tr>`).join('')}</tbody></table></div>`:''}
 <p><b>Fuentes de ${E(result.region)}:</b> ${Number(result.regional_curricula?.count||0)} referencias localizadas.</p>
 ${(result.regional_curricula?.links||[]).length?`<div class="guide-weight-scroll"><table class="guide-metrics-table"><thead><tr><th>Tipo</th><th>Documento</th></tr></thead><tbody>
 ${result.regional_curricula.links.map(x=>`<tr><td>${E(x.type)}</td><td><a target="_blank" rel="noopener noreferrer" href="${E(x.url)}">${E(x.label)}</a></td></tr>`).join('')}</tbody></table></div>`:
 '<p class="hint">TodoFP no ha ofrecido referencias para este ámbito, o la página no se ha podido consultar. Hay que revisar el boletín correspondiente.</p>'}
 ${result.profile?.state_norm_url?`<p>Normativa estatal: <a href="${E(result.profile.state_norm_url)}" target="_blank" rel="noopener noreferrer">Consultar Real Decreto del título</a></p>`:''}
 ${result.suitable_for_current_module===false?'<p class="hint warning">Atención: el ciclo o módulo consultado no coincide con el seleccionado. No añadas estos enlaces como si pertenecieran al currículo de tu módulo.</p>':''}
 <p class="small">${E(result.notice)}</p>
 ${place==='builder'&&(result.regional_curricula?.links?.length||result.profile?.state_norm_url)?'<button type="button" class="btn secondary" data-action="todofp-add-refs">Añadir enlaces al borrador como referencias pendientes de revisión</button>':''}
 </div>`:''}</section>`;
}
function catalogPanel(){return `<section class="panel" id="catalog-fp-panel"><h2>Catálogo de títulos y módulos · Biblioteca del centro</h2>
 <p>Busca módulos ya registrados para <strong>la comunidad y el curso seleccionados arriba</strong>, o importa la tabla de una disposición revisada. No se copiarán RA, CE ni horas a otra administración.</p>
 <div class="formgrid"><div class="field"><label for="catalog-query">Buscar por código, ciclo, familia o módulo</label><input id="catalog-query" maxlength="100" placeholder="Ej.: 0650, Gestión Administrativa, Sanidad"></div>
 <div class="actions"><button type="button" class="btn secondary" data-action="catalog-search">Buscar en el catálogo local</button></div></div>
 <details class="guide-calendar-details"><summary>Importar tabla de títulos y módulos (CSV o copiada de Excel)</summary>
 <p class="small">Introduce seis columnas: <b>Código título;Ciclo;Grado;Familia;Código módulo;Módulo</b>. Ejemplo de estructura, con códigos ficticios:</p>
 <pre class="small">Código título;Ciclo;Grado;Familia;Código módulo;Módulo
DEMO001;Ciclo de ejemplo;Superior;Administración y Gestión;9999;Módulo de ejemplo</pre>
 <textarea id="catalog-table" maxlength="120000" rows="5" placeholder="Pega aquí los datos obtenidos de la disposición oficial o de la tabla revisada.">${E(S.catalogTableText||'')}</textarea>
 <div class="formgrid"><div class="field"><label>URL HTTPS de la disposición o catálogo oficial consultado</label><input id="catalog-source-url" type="url" maxlength="800" placeholder="https://www.boe.es/..."></div>
 <div class="field"><label>Título, fecha y versión de la fuente</label><input id="catalog-source-title" maxlength="700" placeholder="Norma curricular, anexo y modificaciones comprobadas"></div></div>
 <label class="guide-confirm"><input id="catalog-confirmed" type="checkbox"> Confirmo que he contrastado código, título, módulos, territorio, curso y fuente, y que deseo conservar estas fichas en el centro.</label>
 <div class="actions"><button type="button" class="btn secondary" data-action="catalog-preview">Comprobar tabla antes de guardar</button></div>
 <p class="small">Para evitar sustituciones accidentales, las discrepancias con fichas existentes se rechazan. Las horas, RA/CE y notas no se modifican.</p></details>
 ${todofpExplorerPanel('catalog')}
 <div id="catalog-results">${catalogResultsMarkup()}</div>
 <p class="small">Fuentes oficiales de referencia: <a href="https://todofp.es/catalogos-registros-sistema-fp.html" rel="noopener noreferrer" target="_blank">Catálogo Nacional de Ofertas y Catálogo Modular</a> · <a href="https://www.todofp.es/que-estudiar/material-descargable.html" rel="noopener noreferrer" target="_blank">Títulos y catálogos descargables de TodoFP</a>.</p></section>`;}
function calendarDocumentPanel(){
 const draft=S.wizardDraft||S.prepareInfo?.draft||{};
 const report=S.calendarDocumentPreview;
 const matching=report&&report.region===draft.region&&
   report.academic_year===S.prepareInfo?.module?.academic_year&&
   Number(S.calendarDocumentModuleId)===Number(S.moduleId);
 const scope=matching?report:null;
 const sections=[
  ['start_date','Inicio de clases'],['end_date','Fin de clases'],
  ['vacation_periods','Periodos no lectivos y vacaciones'],
  ['regional_non_teaching_days','Festivos o días no lectivos']
 ];
 const candidates=scope?.candidates||{};
 const hasValues=sections.some(([field])=>(candidates[field]||[]).length);
 const rows=sections.flatMap(([field,label])=>(candidates[field]||[]).map((candidate,index)=>{
  const value=typeof candidate.value==='string'?candidate.value:
    field==='vacation_periods'?`${candidate.value.start} a ${candidate.value.end}`:
    candidate.value.date;
  return `<label class="guide-review-line" style="display:block;margin:8px 0">
   <input type="checkbox" data-calendar-import-field="${E(field)}" data-calendar-import-index="${index}">
   <strong>${E(label)}: ${E(value)}</strong> · ${E(candidate.label)}
   <small class="small" style="display:block">${E(candidate.location)} · ${E(candidate.excerpt)}</small></label>`;
 })).join('');
 return `<details class="guide-calendar-details" id="calendar-document-panel" ${scope?'open':''}>
 <summary>Leer calendario escolar desde PDF, Word o texto (vista previa sin IA)</summary>
 <p class="small">Adjunta la resolución oficial del curso y territorio seleccionados, preferiblemente con texto seleccionable. Se buscarán exclusivamente fechas literales en líneas que indiquen inicio, fin, vacaciones o días no lectivos. Ningún dato se guarda ni valida automáticamente.</p>
 <div class="field"><label for="calendar-document-file">Resolución o anexo de calendario (PDF, DOCX, TXT o MD; máximo 15 MB)</label>
 <input type="file" id="calendar-document-file" accept=".pdf,.docx,.txt,.md"></div>
 <label class="guide-confirm"><input id="calendar-document-ocr" type="checkbox"> Intentar OCR en páginas escaneadas (Tesseract español instalado; máximo 8 páginas).</label>
 <button type="button" class="btn secondary" data-action="calendar-document-preview">Extraer fechas y mostrar fuentes</button>
 ${scope?`<div class="guide-review-line"><h4>Vista previa: ${E(scope.filename)} · ${Number(scope.candidate_count)} propuesta(s)</h4>
 <p class="small">Archivo SHA-256: <code>${E(scope.sha256)}</code>. Etapa FP: ${scope.scope?.fp_match?'mencionada':'no identificada'}; comunidad: ${scope.scope?.territory_match?'mencionada':'sin acreditación literal'}; curso: ${scope.scope?.academic_year_match?'mencionado':'sin acreditación literal'}.</p>
 ${!scope.scope_ok?'<p class="hint warning">No se ha acreditado conjuntamente territorio, curso y etapa FP en el texto. Las fechas son solo orientativas y no se pueden cargar automáticamente.</p>':''}
 ${(scope.warnings||[]).length?`<details><summary>Advertencias (${scope.warnings.length})</summary><div class="hint warning">${scope.warnings.map(x=>`<p>${E(x)}</p>`).join('')}</div></details>`:''}
 ${rows||'<p class="small">No se ha obtenido ninguna fecha inequívoca.</p>'}
 ${scope.scope_ok&&scope.suggested_ai_fragment?`<div class="actions"><button type="button" class="btn secondary" data-action="calendar-copy-ai-excerpt">Preparar fragmento del documento para revisarlo con IA (sin enviarlo)</button></div>`:''}
 ${scope.scope_ok&&hasValues?`<label class="guide-confirm"><input id="calendar-document-confirm" type="checkbox"> He cotejado el documento con la administración educativa, el curso y la etapa FP Grado D. Comprendo que la extracción no determina la vigencia ni confirma el calendario del centro.</label>
 <div class="actions"><button type="button" class="btn secondary" data-action="calendar-document-use">Cargar solo las fechas marcadas como borrador</button></div>`:''}
 <p class="small">${E(scope.notice)}</p></div>`:''}</details>`;
}
function calendarAiPanel(){
 const draft=S.wizardDraft||S.prepareInfo?.draft||{};
 const report=S.calendarAiPreview;
 const matching=report&&report.region===draft.region&&
   report.academic_year===S.prepareInfo?.module?.academic_year&&
   Number(S.calendarAiModuleId)===Number(S.moduleId);
 const scope=matching?report:null;
 const sections=[
  ['start_date','Inicio de clases'],['end_date','Fin de clases'],
  ['vacation_periods','Periodos no lectivos y vacaciones'],
  ['regional_non_teaching_days','Festivos o días no lectivos']
 ];
 const candidates=scope?.candidates||{};
 const hasValues=sections.some(([field])=>(candidates[field]||[]).length);
 const rows=sections.flatMap(([field,label])=>(candidates[field]||[]).map((candidate,index)=>{
  const value=typeof candidate.value==='string'?candidate.value:
    field==='vacation_periods'?`${candidate.value.start} a ${candidate.value.end}`:
    candidate.value.date;
  return `<label class="guide-review-line" style="display:block;margin:8px 0">
   <input type="checkbox" data-calendar-ai-field="${E(field)}" data-calendar-ai-index="${index}">
   <strong>${E(label)}: ${E(value)}</strong> · ${E(candidate.label)}
   <small class="small" style="display:block">${E(candidate.location)} · ${E(candidate.excerpt)}</small></label>`;
 })).join('');
 return `<details class="guide-calendar-details" id="calendar-ai-panel" ${scope?'open':''}>
 <summary>Interpretar un fragmento del calendario con IA (opcional)</summary>
 <p class="small">Solo se enviará al proveedor configurado el fragmento que copie aquí. La IA debe aportar una cita literal para cada fecha y la aplicación rechazará propuestas sin respaldo textual. No se envía el PDF ni los datos del alumnado.</p>
 <div class="field"><label for="calendar-ai-fragment">Fragmento de resolución o tabla oficial (máximo 12.000 caracteres)</label>
 <textarea id="calendar-ai-fragment" rows="7" maxlength="12000" placeholder="Copie aquí la comunidad, el curso, la etapa FP, las cabeceras de la tabla y las filas pertinentes...">${E(S.calendarAiFragment||'')}</textarea></div>
 <label class="guide-confirm"><input type="checkbox" id="calendar-ai-authorize"> Autorizo expresamente el envío de este fragmento al proveedor de IA configurado. He evitado incluir datos personales.</label>
 <button type="button" class="btn secondary" data-action="calendar-ai-analyze">Interpretar fragmento con IA y verificar sus citas</button>
 ${scope?`<div class="guide-review-line"><h4>Propuesta IA sin validar: ${E(scope.filename)} · ${Number(scope.candidate_count)} propuesta(s)</h4>
 <p class="small">Archivo SHA-256: <code>${E(scope.sha256)}</code>. Modelo: ${E(scope.ai_model||'no indicado')}. Etapa FP: ${scope.scope?.fp_match?'mencionada':'no identificada'}; comunidad: ${scope.scope?.territory_match?'mencionada':'sin acreditación literal'}; curso: ${scope.scope?.academic_year_match?'mencionado':'sin acreditación literal'}.</p>
 ${!scope.scope_ok?'<p class="hint warning">No se ha acreditado conjuntamente territorio, curso y etapa FP en el texto. Las fechas son solo orientativas y no se pueden cargar automáticamente.</p>':''}
 ${(scope.warnings||[]).length?`<details><summary>Advertencias (${scope.warnings.length})</summary><div class="hint warning">${scope.warnings.map(x=>`<p>${E(x)}</p>`).join('')}</div></details>`:''}
 ${rows||'<p class="small">No se ha obtenido ninguna fecha inequívoca.</p>'}
 ${scope.scope_ok&&hasValues?`<label class="guide-confirm"><input id="calendar-ai-confirm" type="checkbox"> He cotejado el documento con la administración educativa, el curso y la etapa FP Grado D. Comprendo que la extracción no determina la vigencia ni confirma el calendario del centro.</label>
 <div class="actions"><button type="button" class="btn secondary" data-action="calendar-ai-use">Cargar solo las fechas marcadas como borrador</button></div>`:''}
 <p class="small">${E(scope.notice)}</p></div>`:''}</details>`;
}
function generalCalendarLibraryPanel(){
 const d=S.wizardDraft||{},cfg=d.schedule||{},data=S.generalCalendarLibrary;
 const ok=data&&data.territory===d.region&&data.academic_year===S.prepareInfo?.module?.academic_year;
 const versions=ok?(data.versions||[]):[],dif=S.generalCalendarDiff;
 return `<details class="guide-calendar-details" id="general-calendar-library" ${versions.length?'open':''}>
 <summary>Biblioteca de calendarios generales FP del territorio (${versions.length} versiones)</summary>
 <p class="small">Reutiliza fechas generales de FP del mismo territorio y curso. Estas fichas se han revisado por docentes en este equipo: <b>no están certificadas ni sincronizadas con los boletines oficiales</b>. No incluyen horarios, evaluaciones, FEOE, días de centro o festivos municipales/insulares.</p>
 ${!ok?'<p class="hint warning">Guarde primero la comunidad del módulo y recargue el asistente para consultar este territorio y curso.</p>':''}
 ${ok&&versions.length?`<div class="guide-weight-scroll"><table class="guide-metrics-table"><thead><tr><th>Revisión</th><th>Fechas generales</th><th>Fuente</th><th>Acciones</th></tr></thead><tbody>
 ${versions.map((v,i)=>`<tr><td><b>n.º ${Number(v.revision)}</b><div class="small">${E(v.reviewed_at)}</div></td>
 <td>${E(v.schedule?.start_date||'Sin inicio')} a ${E(v.schedule?.end_date||'Sin fin')}
 <div class="small">${(v.schedule?.vacation_periods||[]).length} periodos; ${(v.schedule?.regional_non_teaching_days||[]).length} días generales</div></td>
 <td><a href="${E(v.source_url)}" target="_blank" rel="noopener noreferrer">${E(v.source_title)}</a>
 ${v.correction_urls?.length?`<div class="small">${v.correction_urls.map((u,j)=>`<a href="${E(u)}" target="_blank" rel="noopener noreferrer">Corrección ${j+1}</a>`).join(' · ')}</div>`:''}</td>
 <td><div class="actions"><button class="btn secondary smallbtn" type="button" data-action="general-calendar-apply" data-id="${Number(v.id)}">Cargar propuesta general</button>
 ${i<versions.length-1?`<button class="btn mutedbtn smallbtn" type="button" data-action="general-calendar-compare" data-old="${Number(versions[i+1].id)}" data-new="${Number(v.id)}">Comparar</button>`:''}</div></td></tr>`).join('')}
 </tbody></table></div>`:'<p class="small">Todavía no hay fechas generales revisadas para este territorio y curso.</p>'}
 ${ok&&dif?`<div class="guide-review-line"><b>Comparación de revisiones ${Number(dif.old?.revision)} y ${Number(dif.new?.revision)}</b>
 ${dif.changes?.length?`<div class="guide-weight-scroll"><table class="guide-metrics-table"><thead><tr><th>Campo</th><th>Anterior</th><th>Posterior</th></tr></thead><tbody>
 ${dif.changes.map(c=>`<tr><td>${E(c.label)}</td><td>${E(JSON.stringify(c.previous).slice(0,450))}</td><td>${E(JSON.stringify(c.current).slice(0,450))}</td></tr>`).join('')}</tbody></table></div>`:'<p>Coinciden las fechas y fuentes.</p>'}</div>`:''}
 <p class="small">Para archivar una nueva revisión general, complete el formulario con las fechas, los festivos generales y la disposición oficial. <b>Quite de la lista general las fiestas insulares, municipales y del centro</b> y, si procede, introdúzcalas como días adicionales del centro.</p>
 <label class="guide-confirm"><input type="checkbox" id="general-calendar-scope-confirm"> Confirmo que he contrastado comunidad, curso y norma, y que los festivos generales no contienen fiestas propias de un municipio, isla o centro. La ficha será una referencia revisada por docente, no una norma verificada automáticamente.</label>
 <button class="btn secondary" type="button" data-action="general-calendar-save">Archivar calendario general y su fuente para este curso</button>
 <p class="small">${E(data?.notice||'')}${cfg.island?' Revise específicamente las fiestas de la isla seleccionada.':''}</p>
 </details>`;
}
function calendarVersionsPanel(){
 const data=S.calendarVersions, draft=S.wizardDraft||{},sch=draft.schedule||{};
 if(!data)return `<div class="guide-calendar-details"><p class="small">Las fuentes y las versiones se mostrarán al guardar la comunidad y el centro.</p></div>`;
 const links=data.source_directory?.links||[];
 const scoped=data.territory===draft.region&&data.academic_year===S.prepareInfo?.module?.academic_year&&
   data.center===draft.center&&data.municipality===(sch.municipality||'')&&data.island===(sch.island||'');
 const versions=scoped?(data.versions||[]):[];
 const dif=S.calendarVersionDiff;
 return `<details class="guide-calendar-details" ${versions.length?'open':''}><summary>Fuentes oficiales e historial de calendarios del centro (${versions.length} versiones)</summary>
 <p class="small">Consulta la disposición aplicable a FP Grado D, la última corrección y los días municipales o del centro. <b>Los enlaces son puntos de consulta; no validan automáticamente las fechas.</b></p>
 <div class="actions">${links.map(link=>`<a class="btn secondary smallbtn" href="${E(link.url)}" target="_blank" rel="noopener noreferrer">${E(link.title)}</a>`).join('')}</div>
 <p class="small">${E(data.source_directory?.notice||'')} El calendario que se guarde queda archivado con su fuente y no se reutiliza para otro curso.</p>
 ${!scoped?`<p class="hint warning">El centro, municipio, isla, comunidad o curso aún no coinciden con la ficha guardada. Guarde los cambios antes de consultar o recuperar versiones.</p>`:''}
 ${versions.length?`<div class="guide-weight-scroll"><table class="guide-metrics-table"><thead><tr><th>Versión</th><th>Fecha de revisión</th><th>Procedencia</th><th>Acciones</th></tr></thead><tbody>
 ${versions.map((v,i)=>`<tr><td><b>n.º ${Number(v.revision)}</b></td><td>${E(v.reviewed_at)}</td><td><a href="${E(v.source_url)}" target="_blank" rel="noopener noreferrer">${E(v.source_title)}</a>
 ${v.correction_urls?.length?`<div class="small">Correcciones: ${v.correction_urls.map((u,j)=>`<a href="${E(u)}" target="_blank" rel="noopener noreferrer">${j+1}</a>`).join(' · ')}</div>`:''}
 </td><td><div class="actions"><button type="button" class="btn mutedbtn smallbtn" data-action="calendar-load-version" data-id="${Number(v.id)}">Cargar como propuesta</button>
 ${i<versions.length-1?`<button type="button" class="btn secondary smallbtn" data-action="calendar-compare" data-old="${Number(versions[i+1].id)}" data-new="${Number(v.id)}">Comparar</button>`:''}</div></td></tr>`).join('')}
 </tbody></table></div>`:'<p class="small">Todavía no existen versiones guardadas para este centro, municipio, territorio y curso.</p>'}
 ${scoped&&dif?`<div class="guide-review-line"><h4>Cambios entre las versiones ${Number(dif.old?.revision)} y ${Number(dif.new?.revision)}</h4>
 ${dif.changes?.length?`<div class="guide-weight-scroll"><table class="guide-metrics-table"><thead><tr><th>Elemento</th><th>Anterior</th><th>Posterior</th></tr></thead><tbody>${dif.changes.map(change=>`<tr><td>${E(change.label)}</td><td>${E(JSON.stringify(change.previous).slice(0,650))}</td><td>${E(JSON.stringify(change.current).slice(0,650))}</td></tr>`).join('')}</tbody></table></div>`:'<p>Las fechas, los festivos y las fuentes coinciden.</p>'}
 <p class="small">${E(dif.notice)}</p></div>`:''}
 <p class="small">Cargar una versión no cambia el horario semanal, las unidades, la FEOE ni las calificaciones y desmarca la confirmación del calendario.</p>
 </details>`;
}
function nationalSourcesPanel(){
 const record=S.nationalSources;
 if(!record)return `<p class="small">Las fuentes oficiales se consultarán cuando abra esta sección.</p>`;
 const source=record.sources||{};
 return `<section class="guide-calendar-summary"><h3>Localizar fuentes oficiales · ${E(source.territory||'')} · ${E(source.academic_year||'')}</h3>
 <p class="small">Abre el directorio del Ministerio o el portal de tu administración, localiza la disposición correspondiente a tu título y curso y comprueba sus modificaciones. EvalúaFP no considerará oficial ningún dato solo por estar enlazado aquí.</p>
 <div class="actions">${(source.links||[]).map(x=>`<a class="btn secondary smallbtn" href="${E(x.url)}" target="_blank" rel="noopener noreferrer">${E(x.label)}</a>`).join('')}</div>
 ${record.hours_record?`<p class="small"><strong>Ficha horaria reutilizable del mismo curso:</strong> ${fmtSchoolNumber(record.hours_record.total_hours)} h totales · ${fmtSchoolNumber(record.hours_record.weekly_hours)} h/semana · ${E(record.hours_record.source_title||'Fuente docente guardada')}.</p>`:''}
 ${record.calendar_record?`<p class="small"><strong>Calendario guardado para el mismo centro:</strong> ${E(record.calendar_record.center)} · ${E(record.calendar_record.academic_year)}.</p>`:''}
 </section>`;
}

function normativeMonitorPanel(){
 const record=S.normativeMonitor||{sources:[],events:[],notice:''};
 let html='<div class="guide-calendar-details"><h4>Vigilancia de cambios publicados en el BOE</h4>';
 html+='<p class="small">Consulta bajo demanda. Se compara la información de la API pública del BOE, no el texto completo de la norma ni los boletines autonómicos. Nunca se modifican automáticamente RA, CE ni notas.</p>';
 if(!record.module_code){return html+'<p class="hint warning">'+E(record.notice||'Guarde primero el código oficial del módulo.')+'</p></div>';}
 html+='<div class="formrow"><div class="field grow"><label>Identificador oficial del BOE asociado a este módulo</label><input id="monitor-boe-id" type="text" maxlength="24" placeholder="BOE-A-AAAA-NNN"></div>';
 html+='<button type="button" class="btn secondary" data-action="boe-monitor-check">Consultar cambios</button></div>';
 const sources=record.sources||[];
 if(!sources.length){html+='<p class="small">Todavía no hay disposiciones vigiladas. Puedes consultar un ID oficial, o archivar una fuente curricular del BOE para que aparezca aquí.</p>';}
 for(const source of sources){
   const status=source.review_pending?'Cambio pendiente de revisión':source.last_checked?'Última consulta registrada':'Pendiente de primera consulta';
   html+='<div class="guide-review-line"><strong>'+E(source.boe_id)+'</strong> · '+E(status);
   html+='<p class="small">'+E(source.source_title||'Disposición BOE')+(source.last_checked?' · Consultada: '+E(source.last_checked):'')+'</p>';
   html+='<div class="actions"><a class="btn mutedbtn smallbtn" href="https://www.boe.es/buscar/act.php?id='+E(source.boe_id)+'" target="_blank" rel="noopener noreferrer">Abrir BOE</a>';
   html+='<button type="button" class="btn secondary smallbtn" data-action="boe-monitor-check" data-boe-id="'+E(source.boe_id)+'">Comprobar de nuevo</button>';
   if(source.review_pending){html+='<button type="button" class="btn secondary smallbtn" data-action="boe-monitor-ack" data-boe-id="'+E(source.boe_id)+'">Registrar revisión docente</button>';}
   html+='</div></div>';
 }
 if(record.events?.length){
   html+='<details><summary>Historial de diferencias de metadatos ('+record.events.length+')</summary>';
   for(const event of record.events){
     const oldIds=(event.before?.reported_amendments||[]).map(x=>x.id).join(', ')||'Ninguna informada';
     const newIds=(event.after?.reported_amendments||[]).map(x=>x.id).join(', ')||'Ninguna informada';
     html+='<p class="small"><strong>'+E(event.boe_id)+'</strong> · '+E(event.observed_at)+'<br>Fecha de actualización: '+E(event.before?.last_update||'No indicada')+' → '+E(event.after?.last_update||'No indicada')+'<br>Referencias antes: '+E(oldIds)+'<br>Referencias después: '+E(newIds)+'</p>';
   }
   html+='</details>';
 }
 html+='<p class="small">'+E(record.notice||'La ausencia de cambios observados no demuestra vigencia normativa.')+'</p></div>';
 return html;
}
function curriculumReviewPanel(){
 const info=S.prepareInfo||{},module=info.module||{},draft=S.wizardDraft||info.draft||{};
 const report=S.curriculumReview;
 const history=S.curriculumHistory;
 const diff=S.curriculumHistoryDiff;
 return `<section class="guide-calendar-summary"><h3>Extracción contrastable de RA y CE (sin IA)</h3>
 <p class="small">Selecciona una programación o un currículo oficial con el <b>nombre y código del módulo</b> y sus RA/CE completos. Se presenta una vista previa con páginas o párrafos; no se cambia ninguna calificación ni ponderación.</p>
 <form id="curriculum-review-form" class="formgrid">
 <input type="hidden" name="module_id" value="${Number(S.moduleId||0)}">
 <div class="field"><label>Código oficial del módulo</label><input type="text" name="module_code" pattern="[0-9]{4}" maxlength="4" required value="${E(draft.official_module_code||'')}" placeholder="0650"></div>
 <div class="field"><label>Clase de documento</label><select name="document_kind"><option value="programacion">Programación didáctica</option><option value="norma_oficial">Disposición curricular oficial</option></select></div>
 <div class="field"><label>PDF, DOCX, TXT o MD (máx. 15 MB)</label><input name="document" type="file" accept=".pdf,.docx,.txt,.md" required></div>
 <div class="actions"><button class="btn secondary" type="submit">Previsualizar RA y CE sin modificar datos</button></div></form>
 ${report?`<div class="guide-review-line"><h4>Resultados encontrados: ${Number(report.summary?.ra||0)} RA y ${Number(report.summary?.ce||0)} CE</h4>
 <p>Documento: ${E(report.source?.filename||'')} · Huella SHA-256: <code>${E(report.source?.sha256||'')}</code></p>
 <p class="hint warning">Revisión docente obligatoria. La extracción no confirma la vigencia del currículo. Los RA/CE existentes y sus notas no se modifican.</p>
 <div class="guide-weight-scroll"><table class="guide-metrics-table"><thead><tr><th>RA/CE</th><th>Enunciado extraído</th><th>Procedencia</th></tr></thead><tbody>
 ${(report.outcomes||[]).flatMap(ra=>[ra,...(ra.criteria||[])]).map(x=>`<tr><td>${E(x.code)}</td><td>${E(x.description)}</td><td>${E((x.locations||[]).join(', '))}</td></tr>`).join('')}
 </tbody></table></div>
 <p><b>Diferencias frente al módulo actual:</b> ${Object.keys(report.comparison?.counts||{}).length?Object.entries(report.comparison.counts).map(([type,count])=>`${E(type)}: ${Number(count)}`).join(' · '):'Sin diferencias detectadas'}.</p>
 <details><summary>Propuesta de ponderaciones iguales (no aplicada)</summary><div class="guide-weight-scroll"><table class="guide-metrics-table"><thead><tr><th>RA</th><th>Peso en el módulo</th><th>CE</th><th>Peso global CE</th></tr></thead><tbody>
 ${(report.default_weight_proposal||[]).flatMap(ra=>ra.criteria.map(ce=>`<tr><td>${E(ra.code)}</td><td>${E(ra.module_weight_pct)} %</td><td>${E(ce.code)}</td><td>${E(ce.module_weight_pct)} %</td></tr>`)).join('')}
 </tbody></table></div></details>
 ${report.existing_ra_count?'<p class="hint warning">Existen criterios previamente registrados: solo se ofrece comparación; nunca se sustituyen automáticamente.</p>':'<p class="small">Esta vista previa no guarda RA/CE. Tras revisarlos, puede incorporarlos mediante los controles curriculares existentes.</p>'}
 ${report.document_kind==='norma_oficial'?`<div class="guide-calendar-details"><h4>Conservar una versión de esta disposición para futuras comparaciones</h4>
 <p class="small">Se conservará el texto de RA/CE extraído, la fuente y la huella SHA-256, no el PDF original. No se aprobarán ni sustituirán criterios ni calificaciones.</p>
 <div class="formgrid"><div class="field"><label>Enlace público HTTPS a la disposición</label><input type="url" id="curriculum-version-url" maxlength="800" value="${E(draft.curriculum_source_url||'')}" placeholder="https://www.boe.es/..."></div>
 <div class="field"><label>Título, fecha y versión de la disposición</label><input id="curriculum-version-title" maxlength="700" value="${E(draft.curriculum_source_description||'')}" placeholder="Real Decreto / Orden / modificación"></div></div>
 <label class="guide-confirm"><input id="curriculum-version-confirm" type="checkbox"> He comprobado que este documento corresponde a mi territorio, curso y módulo y deseo archivarlo para comparar versiones.</label>
 <button type="button" class="btn secondary" data-action="curriculum-history-save">Archivar esta versión de RA/CE sin modificar el currículo</button></div>`:''}
 </div>`:''}
 <div class="guide-calendar-details"><h4>Historial de fuentes curriculares del módulo</h4>
 <p class="small">Las versiones se guardan por módulo, comunidad y curso. Son referencias aportadas y revisadas por docentes; ninguna se considera vigente automáticamente.</p>
 ${history?.versions?.length?`<div class="guide-weight-scroll"><table class="guide-metrics-table"><thead><tr><th>Registro</th><th>Disposición / fuente</th><th>RA / CE</th><th>Comparar</th></tr></thead><tbody>${history.versions.map((v,i)=>`<tr><td>#${Number(v.id)} · ${E(v.recorded_at)}</td><td><a href="${E(v.source_url)}" rel="noopener noreferrer" target="_blank">${E(v.source_title)}</a><div class="small">${E(v.document)}</div></td><td>${v.ra} / ${v.ce}</td><td>${i<history.versions.length-1?`<button class="btn mutedbtn smallbtn" type="button" data-action="curriculum-history-compare" data-old="${history.versions[i+1].id}" data-new="${v.id}">Comparar con anterior</button>`:'Primera versión'}</td></tr>`).join('')}</tbody></table></div>`:'<p class="small">Aún no hay versiones archivadas para este módulo y curso. Introduce y guarda el código oficial para empezar.</p>'}
 ${diff?`<div class="guide-review-line"><h4>Cambios entre #${Number(diff.old?.id)} y #${Number(diff.new?.id)}</h4>
 <p>${diff.differences?.length?Object.entries(diff.counts||{}).map(([k,v])=>`${E(k)}: ${v}`).join(' · '):'Los RA/CE extraídos no han cambiado.'}</p>
 ${diff.differences?.length?`<div class="guide-weight-scroll"><table class="guide-metrics-table"><thead><tr><th>Código</th><th>Tipo de cambio</th><th>Texto anterior</th><th>Texto nuevo</th></tr></thead><tbody>${diff.differences.map(x=>`<tr><td>${E(x.code)}</td><td>${E(x.state)}</td><td>${E(x.old)}</td><td>${E(x.new)}</td></tr>`).join('')}</tbody></table></div>`:''}
 <p class="small">${E(diff.notice||'')}</p></div>`:''}
 </div>
 ${normativeMonitorPanel()}
 </section>`;
}

function wizardStepMarkup(step, info){
 const d=S.wizardDraft,m=info.module;
 switch(step){
 case 0:return `<h2>1. Identificación del módulo</h2><p class="small">Los datos del ciclo y módulo se han tomado de su ficha local. No es necesario volver a escribirlos.</p>
 <div class="guide-review-line"><b>Módulo:</b> ${E(m.name)} · ${E(m.cycle)} · ${E(m.academic_year)}</div>
 <div class="formgrid"><div class="field guide-field"><label for="guide-region">Administración educativa competente</label><select id="guide-region" name="region" required>${territoryOptions(d.region)}</select><small class="small">Las fuentes y el calendario dependen de esta selección y del curso académico.</small></div>
 ${guideField('official_module_code','Código oficial del módulo (si se conoce)','Ej.: 0650. Evita confundir módulos con nombres parecidos.',1)}
 ${guideField('official_cycle_code','Código del ciclo o título (si se conoce)','Para vincular el currículo sin ambigüedades.',1)}
 <div class="field"><label for="guide-fp_regime">Régimen de formación profesional</label><select id="guide-fp_regime" name="fp_regime"><option value="pendiente" ${!d.fp_regime||d.fp_regime==='pendiente'?'selected':''}>Por determinar</option><option value="general" ${d.fp_regime==='general'?'selected':''}>General</option><option value="intensivo" ${d.fp_regime==='intensivo'?'selected':''}>Intensivo</option></select></div>
 ${guideField('center','Centro educativo','',1)}
 ${guideField('teacher','Docente responsable','',1)}${guideField('department','Departamento','',1)}</div>
 ${guideField('academic_context','Punto de partida y diagnóstico inicial','No incluya datos personales del alumnado.')}${guideField('identification_data','Datos identificativos y características del módulo')}
 ${guideField('justification','Justificación y principios de la programación')}
 ${guideField('center_characteristics','Características del centro y medios disponibles')}
 ${guideField('student_characteristics','Características generales del grupo')}
 ${guideField('environment_context','Entorno de aprendizaje y sector productivo')}`;
 case 1:return `<h2>2. Normativa y objetivos</h2><p class="hint warning">EvalúaFP no inventa normativa ni sustituye su revisión. Contraste la identificación del título y el currículo vigente en su comunidad autónoma.</p>
 ${nationalSourcesPanel()}
 ${boeDiscoveryPanel()}
 ${todofpExplorerPanel('builder')}
 ${guideField('curriculum_source_url','URL del currículo oficial aplicable','BOE, boletín autonómico o web oficial. Debe corresponder al territorio y curso indicados.',1)}
 ${guideField('curriculum_source_description','Título, identificación y versión de la disposición curricular','Indique la fecha y las modificaciones comprobadas.',1)}
 <label class="guide-confirm"><input type="checkbox" name="curriculum-confirmed" ${d.curriculum_confirmed?'checked':''}> He contrastado que el currículo y sus RA/CE corresponden a mi ciclo, módulo, comunidad y curso.</label>
 ${guideField('normative_references','Referencias normativas verificadas','Indique las normas, su fecha y fuentes. No se rellenan automáticamente con referencias no comprobadas.')}
 ${guideField('objectives','Objetivos del módulo y su contribución al ciclo')}
 ${guideField('competencies','Competencias profesionales, personales y sociales relacionadas')}
 ${guideField('qualifications','Cualificaciones profesionales y estándares de competencia')}`;
 case 2:return `<h2>3. Metodología y recursos</h2>
 ${guideField('methodology','Metodología didáctica','Explique estrategias, actividades y organización de la enseñanza.')}
 ${guideField('resources','Recursos, materiales y herramientas')}
 ${guideField('inclusion','Atención a las diferencias individuales y accesibilidad')}
 ${guideField('contents','Contenidos didácticos asociados a los RA y CE')}
 ${guideField('learning_activities','Situaciones de aprendizaje y actividades')}
 ${guideField('interdisciplinarity','Interdisciplinariedad y coordinación entre módulos')}`;
 case 3:return `<h2>4. Evaluación y recuperación</h2><p class="hint">Los pesos de RA y CE se toman de la estructura curricular confirmada. Este documento no cambia las calificaciones ni la política de evaluación guardada.</p>
 ${guideField('assessment','Procedimientos y criterios de calificación','Explique cómo se obtienen las evidencias y cómo se realiza el cálculo.')}
 ${guideField('instruments','Instrumentos de evaluación','Exámenes, prácticas, portafolio, observación, proyectos, etc.')}
 ${guideField('recovery','Actividades y procedimientos de recuperación','Indique medidas para RA/CE no superados.')}
 ${guideField('grading','Criterios de calificación y ponderaciones')}
 ${guideField('assessment_sessions','Sesiones de evaluación')}
 ${guideField('extraordinary_assessment','Evaluación extraordinaria y pruebas pendientes')}
 ${guideField('promotion','Promoción y continuidad formativa')}
 ${guideField('attendance','Asistencia y evaluación continua')}
 ${guideWeights(info)}`;
 case 4:return `<h2>5. Temporalización y formación en empresa (FEOE)</h2>
 <p class="small">El calendario se calcula con la carga horaria del módulo, las sesiones por día y los días no lectivos. <b>Nunca se presuponen seis horas por semana.</b> Revisa las fuentes, confirma las horas y ajusta unidades y FEOE.</p>
 <div class="guide-calendar-summary">${S.calendarInfo?.profile?`
 <strong>Calendario de referencia: ${E(S.calendarInfo.territory)} · ${E(m.academic_year)}</strong>
 <p>${E(S.calendarInfo.profile.source_description)}. ${E(S.calendarInfo.notice)}</p>
 <p>Vacaciones: ${(d.schedule?.vacation_periods||[]).map(p=>E(p.start+' a '+p.end)).join(' · ')||'Sin periodos registrados'}.</p>
 <p>${(S.calendarInfo.profile.source_urls||[]).map((link,i)=>`<a target="_blank" rel="noopener noreferrer" href="${E(link)}">Fuente oficial ${i+1}</a>`).join(' · ')}</p>
 `:`<strong>Calendario sin ficha incorporada para ${E(d.region)} · ${E(m.academic_year)}</strong>
 <p>Introduce fechas, vacaciones, festivos locales y del centro y la fuente oficial. EvalúaFP no aplicará fechas de otra comunidad ni de otro curso. <a href="https://www.todofp.es/" rel="noopener noreferrer" target="_blank">Consultar recursos de FP</a>.</p>`}</div>
  ${nationalSourcesPanel()}
 ${calendarDocumentPanel()}
 ${calendarAiPanel()}
 <div class="guide-hours-source"><h3>Datos horarios procedentes de la ficha curricular</h3>
 ${info.hours_reference?`<p>Coincidencia por ciclo y denominación: <b>${E(info.hours_reference.title)} (${E(info.hours_reference.code)})</b>. ${info.hours_reference.course?'Curso del ciclo '+E(info.hours_reference.course)+'. ':''} ${info.hours_reference.source==='biblioteca_local'?'Ficha local revisada por docente':'Referencia de catálogo pendiente de comprobar'}. Horas propuestas: <b>${fmtSchoolNumber(info.hours_reference.total_hours)} h totales</b> · <b>${fmtSchoolNumber(info.hours_reference.weekly_hours)} h/semana</b>.</p><p><a href="${E(info.hours_reference.source_url)}" target="_blank" rel="noopener noreferrer">Abrir la fuente horaria indicada</a>${d.region==='Canarias'?' · Comprueba también las modificaciones posteriores del Gobierno de Canarias':''}</p>`:
 `<p class="hint warning">No se ha encontrado una coincidencia curricular inequívoca. No se inventarán horas: consulta el currículo estatal o autonómico y completa las dos cifras.</p>`}
 <p class="small">Los datos de la ficha son una referencia sujeta a comprobación. Las horas de tu centro pueden responder a una organización específica autorizada.</p>
 <details class="guide-calendar-details"><summary>Ayuda IA · interpretar un fragmento oficial con las horas del módulo</summary>
 <p class="small">Copia desde el boletín un extracto que contenga <strong>código o nombre del módulo, horas anuales y horas semanales</strong>. La IA solo propondrá valores si puede señalar una cita literal y la fila coincide. No se transmite ninguna programación ni información personal.</p>
 <textarea id="national-hours-excerpt" rows="5" maxlength="14000" placeholder="Pega aquí la fila o tabla publicada en el boletín oficial..."></textarea>
 <div class="actions"><button class="btn secondary" type="button" data-action="national-ai-extract-hours">Interpretar extracto con IA</button></div>
 ${S.nationalHoursPreview?`<div class="guide-review-line"><b>Propuesta sin aplicar:</b> ${fmtSchoolNumber(S.nationalHoursPreview.total_hours)} h totales y ${fmtSchoolNumber(S.nationalHoursPreview.weekly_hours)} h/semana.<p class="small">Cita de la fuente: ${E(S.nationalHoursPreview.literal_quote)}</p>
 <button type="button" class="btn" data-action="national-ai-apply-hours">Usar cifras propuestas (pendientes de confirmación)</button></div>`:''}
 </details></div>
 <details class="guide-calendar-details"><summary>Importar las horas de todo el ciclo desde una tabla oficial (CSV o Excel copiado)</summary>
 <p class="small">La tabla debe corresponder al <strong>mismo ciclo, territorio y curso</strong>. Copia cuatro columnas desde Excel/Calc o un CSV, con encabezados <b>Código; Módulo; Horas totales; Horas semanales</b>. No se utilizará IA ni se enviarán datos a Internet.</p>
 <div class="guide-fieldset"><label for="national-table-file"><b>O seleccionar documento oficial PDF/Word</b></label>
 <input id="national-table-file" type="file" accept=".pdf,.docx">
 <label class="guide-confirm"><input id="national-ocr" type="checkbox"> Intentar OCR si el PDF contiene páginas escaneadas (requiere Tesseract en este equipo; máximo 8 páginas)</label>
 <button type="button" class="btn secondary" data-action="national-document-preview">Leer tabla del archivo sin guardar datos</button>
 <p class="small">El documento no sale de tu ordenador. Se reconocen únicamente filas donde figuran código, módulo, horas totales y horas semanales. Revisa cada cifra y la fuente antes de importarla.</p></div>
 <textarea id="national-hour-table" rows="5" maxlength="80000" placeholder="Código;Módulo;Horas totales;Horas semanales&#10;0650;Proceso integral de la actividad comercial;202;6">${E(S.nationalTableText||'')}</textarea>
 <div class="actions"><button type="button" class="btn secondary" data-action="national-table-preview">Comprobar filas</button></div>
 ${S.nationalTablePreview?`<div class="guide-review-line"><p><strong>${S.nationalTablePreview.count} módulos detectados</strong></p>
 <div class="guide-weight-scroll"><table class="guide-metrics-table"><thead><tr><th>Código</th><th>Módulo</th><th>Horas totales</th><th>Horas/semana</th></tr></thead><tbody>
 ${S.nationalTablePreview.rows.slice(0,15).map(x=>`<tr><td>${E(x.code)}</td><td>${E(x.name)}</td><td>${fmtSchoolNumber(x.total_hours)}</td><td>${fmtSchoolNumber(x.weekly_hours)}</td></tr>`).join('')}
 </tbody></table></div><p class="small">Para guardar se usarán la URL y la descripción de la disposición horaria indicadas más abajo. No se sustituirán otras fichas ya confirmadas.</p>
 <button type="button" class="btn" data-action="national-table-import">Guardar todas las filas para este ciclo y curso</button></div>`:''}
 </details>
 <fieldset class="guide-fieldset"><legend>Horas y fechas del módulo</legend>
 <div class="formgrid">
 <div class="field"><label>Horas semanales del módulo (fuente revisable)</label><input name="schedule-weekly-hours" type="number" min="0.01" max="40" step="0.01" value="${E(d.schedule?.weekly_hours||'')}" required></div>
 <div class="field"><label>Horas totales del módulo</label><input name="schedule-total-hours" type="number" min="0.01" max="2500" step="0.01" value="${E(d.schedule?.total_hours||'')}" placeholder="Consultar ficha curricular" required></div>
 <div class="field"><label>Inicio de las clases</label><input name="schedule-start-date" type="date" value="${E(d.schedule?.start_date||'')}" required></div>
 <div class="field"><label>Fin de las clases</label><input name="schedule-end-date" type="date" value="${E(d.schedule?.end_date||'')}" required></div>
 ${d.region==='Canarias'?`<div class="field"><label>Isla</label><select name="schedule-island">${['Tenerife','Gran Canaria','La Palma','Lanzarote','Fuerteventura','La Gomera','El Hierro','La Graciosa'].map(x=>`<option ${x===(d.schedule?.island||'Tenerife')?'selected':''}>${x}</option>`).join('')}</select></div>`:''}
 <div class="field"><label>Municipio (para festivos locales)</label><input name="schedule-municipality" maxlength="120" value="${E(d.schedule?.municipality||'')}" placeholder="Municipio del centro"></div></div>
 <details class="guide-calendar-details"><summary>Horario por días · precisión de los festivos</summary>
 <p class="small">Si no lo indicas, se estimará un reparto uniforme entre lunes y viernes. Para descontar festivos por sesiones reales, introduce las horas que impartes cada día. La suma debe coincidir con las horas semanales.</p>
 <div class="guide-weekdays">${['Lunes','Martes','Miércoles','Jueves','Viernes'].map((day,i)=>`<label>${day}<input data-weekday="${i}" type="number" min="0" max="12" step="0.5" value="${E(d.schedule?.weekday_hours?.[i]||'')}" placeholder="0"></label>`).join('')}</div></details>
 <div class="formgrid"><div class="field"><label>Cierre de la 1.ª evaluación</label><input name="schedule-term-1" type="date" value="${E(d.schedule?.evaluation_ends?.[0]||'')}"></div>
 <div class="field"><label>Cierre de la 2.ª evaluación</label><input name="schedule-term-2" type="date" value="${E(d.schedule?.evaluation_ends?.[1]||'')}"></div>
 <div class="field"><label>Cierre de la 3.ª evaluación</label><input name="schedule-term-3" type="date" value="${E(d.schedule?.evaluation_ends?.[2]||'')}"></div>
 <div class="field"><label>Días no lectivos adicionales (uno por línea)</label><textarea name="schedule-extra-days" rows="2" placeholder="2027-02-08">${E((d.schedule?.extra_non_teaching_days||[]).join('\n'))}</textarea></div></div>
 <div class="guide-calendar-details"><h3>Vacaciones y festivos del curso ${E(m.academic_year)}</h3>
 <p class="small">Cada línea representa un periodo o día no lectivo. Puedes editar, añadir o eliminar fechas. Las propuestas de calendario son editables, pero debes contrastarlas con la normativa aplicable.</p>
 <div class="formgrid"><div class="field"><label>Vacaciones (inicio;fin;motivo)</label><textarea name="schedule-vacations" rows="4" placeholder="2026-12-23;2027-01-08;Navidad">${E(calendarVacationLines(d.schedule))}</textarea></div>
 <div class="field"><label>Festivos autonómicos, insulares y nacionales (fecha;motivo)</label><textarea name="schedule-regional-days" rows="4" placeholder="2026-10-12;Fiesta Nacional">${E(calendarHolidayLines(d.schedule))}</textarea></div>
 <div class="field"><label>URL de la resolución de calendario escolar del curso y comunidad</label><input name="schedule-calendar-source" type="url" maxlength="800" value="${E(d.schedule?.calendar_source_url||'')}" placeholder="https://..."></div>
 <div class="field"><label>Descripción y fecha de la fuente</label><input name="schedule-calendar-source-description" maxlength="700" value="${E(d.schedule?.calendar_source_description||'')}" placeholder="Resolución y correcciones aplicables"></div>
 <div class="field"><label>Enlaces a correcciones o modificaciones (una URL HTTPS por línea)</label>
 <textarea name="schedule-calendar-corrections" rows="2" placeholder="https://www.boe.es/...">${E((d.schedule?.calendar_correction_urls||[]).join('\n'))}</textarea></div></div></div>
 ${generalCalendarLibraryPanel()}
 ${calendarVersionsPanel()}
 <div class="formgrid"><div class="field"><label>URL de la norma que fija las horas de este módulo</label>
 <input type="url" name="schedule-hours-source" maxlength="800" value="${E(d.schedule?.hours_source_url||'')}" placeholder="https://www.boe.es/... o boletín autonómico"></div>
 <div class="field"><label>Nombre y versión de la disposición horaria</label>
 <input name="schedule-hours-description" maxlength="700" value="${E(d.schedule?.hours_source_description||'')}" placeholder="Anexo, resolución, fecha y modificaciones"></div></div>
  <label class="guide-confirm"><input name="schedule-hours-confirmed" type="checkbox" ${d.schedule?.hours_confirmed?'checked':''}> Confirmo las horas totales y semanales tras comprobar el título, el curso y la distribución horaria que corresponde a mi módulo.</label>
 <p class="small">Fuente del dato: ${E(d.schedule?.hours_source_description||'Entrada del docente sin referencia automática')} ${d.schedule?.hours_source_url?`· <a href="${E(d.schedule.hours_source_url)}" target="_blank" rel="noopener noreferrer">Ver disposición</a>`:''}</p>
 <label class="guide-confirm"><input name="schedule-confirmed" type="checkbox" ${d.schedule?.calendar_confirmed?'checked':''}> He comprobado el calendario específico de mi centro y sus días no lectivos.</label>
 <div class="actions"><button type="button" class="btn secondary" data-action="national-save-hours">Guardar horas contrastadas para reutilizarlas en el mismo curso</button>
 <button type="button" class="btn secondary" data-action="national-save-calendar">Guardar calendario verificado para el mismo centro y curso</button>
 ${S.nationalSources?.calendar_record?`<button type="button" class="btn mutedbtn" data-action="national-apply-calendar">Cargar calendario que ya está guardado para este centro</button>`:''}</div>
 <p class="small">Las fichas guardadas identifican al docente como persona que las ha contrastado. Nunca se trasladan automáticamente a otro curso académico, comunidad o centro.</p>
 </fieldset>
 <fieldset class="guide-fieldset"><legend>Unidades por evaluación</legend>
 <label class="guide-confirm"><input type="checkbox" name="guide-units-auto" ${d.units_mode!=='manual'?'checked':''}> Organización automática: una unidad por RA</label>
 <div class="formgrid"><div class="field"><label>Número de unidades (modo personalizado)</label><input id="guide-unit-count" type="number" min="1" max="100" step="1" value="${E(d.units?.length||3)}"></div>
 <div class="field"><label>Crear cuadrícula manual</label><button class="btn secondary" type="button" data-action="prepare-manual-units">Preparar unidades editables</button></div></div>
 <div class="actions"><button class="btn secondary" type="button" data-action="prepare-propose-units">Proponer una unidad por RA</button>
 <button class="btn secondary" type="button" data-action="prepare-enrich-units">Preparar instrumentos y recursos con IA</button></div>
 ${S.unitProposal?`<section class="guide-ai-review"><h3>Propuesta de IA para las unidades</h3>
 <p class="small">Las sugerencias se incorporan únicamente a instrumentos y recursos vacíos o todavía genéricos. Conservaremos lo que ya haya escrito el docente.</p>
 <div class="guide-weight-scroll"><table class="guide-metrics-table"><thead><tr><th>Unidad</th><th>Instrumentos propuestos</th><th>Recursos propuestos</th></tr></thead><tbody>
 ${S.unitProposal.units.map(u=>`<tr><td>${E(u.code)}</td><td>${E(u.instruments)}</td><td>${E(u.resources)}</td></tr>`).join('')}</tbody></table></div>
 <div class="actions"><button type="button" class="btn" data-action="prepare-accept-unit-ai">Aceptar sugerencias sin sobrescribir textos docentes</button>
 <button type="button" class="btn mutedbtn" data-action="prepare-dismiss-unit-ai">Descartar sugerencias</button></div></section>`:''}
 <p class="small">La propuesta se obtiene de los RA/CE confirmados. Revisa las horas asignadas: no cambia las ponderaciones ni instrumentos existentes.</p>
 <div class="guide-units">${(d.units||[]).map((u,i)=>`<div class="guide-unit" data-unit-row="${i}">
 <div class="formrow guide-unit-top"><strong>Unidad ${i+1}</strong><button type="button" class="btn smallbtn mutedbtn" data-action="prepare-remove-unit" data-index="${i}">Eliminar</button></div>
 <div class="formgrid"><div class="field"><label>Código</label><input data-unit="code" maxlength="30" value="${E(u.code)}" required></div>
 <div class="field"><label>Nombre de unidad</label><input data-unit="title" maxlength="220" value="${E(u.title)}" required></div>
 <div class="field"><label>Evaluación</label><select data-unit="term">${[1,2,3].map(t=>`<option value="${t}" ${t===Number(u.term)?'selected':''}>${t}.ª evaluación</option>`).join('')}</select></div>
 <div class="field"><label>Horas de la unidad</label><input data-unit="hours" type="number" min="0.5" max="1000" step="0.5" value="${E(u.hours)}" required></div></div>
 <div class="formgrid"><div class="field"><label>Instrumentos de evaluación</label><textarea data-unit="instruments" rows="2" placeholder="Prueba práctica, portafolio…">${E(u.instruments||'')}</textarea></div>
 <div class="field"><label>Recursos previstos</label><textarea data-unit="resources" rows="2" placeholder="Equipos, software, supuestos…">${E(u.resources||'')}</textarea></div></div>
 <details><summary>CE asociados a esta unidad (${(u.criteria_codes||[]).length})</summary>
 <div class="guide-ce-checks">${(info.criteria||[]).map(c=>`<label><input type="checkbox" data-unit-ce="${E(c.code)}" ${(u.criteria_codes||[]).includes(c.code)?'checked':''}> <b>${E(c.code)}</b> · ${E((c.description||'').slice(0,125))}</label>`).join('')||'<p class="hint warning">Primero incorpora RA/CE.</p>'}</div></details>
 </div>`).join('')}</div>
 <div class="actions"><button class="btn secondary" type="button" data-action="prepare-add-unit">+ Añadir unidad</button></div></fieldset>
 <fieldset class="guide-fieldset"><legend>Formación en empresa u organismo equiparado (FEOE)</legend>
 <p class="small">Marca los CE que se prevé trabajar en empresa. El intervalo del 10–20 % de criterios es una referencia editable de esta planificación, no una regla legal general; debe comprobarse también la distribución de RA del ciclo y el régimen de dual.</p>
 <div class="formgrid"><div class="field"><label>Inicio previsto FEOE</label><input name="schedule-feoe-start" type="date" value="${E(d.schedule?.feoe_start||'')}"></div>
 <div class="field"><label>Fin previsto FEOE</label><input name="schedule-feoe-end" type="date" value="${E(d.schedule?.feoe_end||'')}"></div>
 <div class="field"><label>Horas semanales en el centro durante FEOE</label><input name="schedule-feoe-center-hours" type="number" min="0" max="40" step="0.5" value="${E(d.schedule?.feoe_center_hours_weekly??'')}" placeholder="Sin descontar hasta confirmar"></div>
 <div class="field"><label>Porcentaje orientativo de CE para FEOE</label><input name="schedule-feoe-target" type="number" min="10" max="20" step="1" value="${E(d.schedule?.feoe_target_percent??15)}"></div></div>
 <div class="actions"><button type="button" class="btn secondary" data-action="prepare-propose-feoe">Proponer CE para FEOE</button></div>
 <div class="guide-ce-checks guide-feoe-checks">${(info.criteria||[]).map(c=>`<label><input type="checkbox" data-feoe-ce="${E(c.code)}" ${(d.schedule?.feoe_criteria_codes||[]).includes(c.code)?'checked':''}> <b>${E(c.code)}</b> · ${E((c.description||'').slice(0,130))}</label>`).join('')}</div>
 <div class="guide-feoe-export panel"><h3>Programa formativo mínimo en empresa · Documento independiente</h3>
 <p class="small">Se proponen tareas breves y comprensibles relacionadas con CE reales, y evidencias que debe observar la empresa. Puedes redactarlas de nuevo con IA, corregirlas y descargarlas en un documento aparte. Los CE complejos necesitan medios específicos y no deben darse por superados mediante tareas genéricas.</p>
 <div class="actions"><button class="btn secondary" type="button" data-action="feoe-minimum-preview">Preparar propuesta mínima</button>
 <button class="btn secondary" type="button" data-action="feoe-minimum-ai">Mejorar propuesta con IA</button></div>
 ${renderFeoeMinimumPreview(info)}
 <p class="small">Una vez guardada la propuesta, puedes descargar este documento sin descargar la programación completa.</p>
 <div class="actions"><a class="btn secondary" download href="/api/programming-builder/${m.id}/feoe-minimum.docx">Descargar programa mínimo · Word</a>
 <a class="btn secondary" download href="/api/programming-builder/${m.id}/feoe-minimum.pdf">Descargar programa mínimo · PDF</a></div>
 <p class="small">El programa individual se acordará con la empresa y cumplirá los requisitos de la administración educativa competente. Esta propuesta pedagógica no sustituye el plan o trámite oficial de la comunidad.</p>
 </div>
 </fieldset>
 <fieldset class="guide-fieldset"><legend>Actividades complementarias y extraescolares</legend>
 <p class="small">Se proponen actividades contextualizadas, que el docente puede editar, eliminar o dejar sin fecha hasta que el centro las autorice.</p>
 <div class="guide-activities">${(d.activities||[]).map((a,i)=>`<div class="guide-unit" data-activity-row="${i}"><div class="formrow guide-unit-top"><strong>Actividad ${i+1}</strong><button type="button" class="btn mutedbtn smallbtn" data-action="prepare-remove-activity" data-index="${i}">Eliminar</button></div>
 <div class="formgrid"><div class="field"><label>Tipo</label><select data-activity="type"><option value="complementaria" ${a.type==='complementaria'?'selected':''}>Complementaria (horario lectivo)</option><option value="extraescolar" ${a.type==='extraescolar'?'selected':''}>Extraescolar</option></select></div>
 <div class="field"><label>Nombre</label><input data-activity="title" value="${E(a.title)}" required></div>
 <div class="field"><label>Fecha prevista</label><input data-activity="date" type="date" value="${E(a.date||'')}"></div>
 <div class="field"><label>Unidad vinculada</label><input data-activity="unit_code" value="${E(a.unit_code||'')}" placeholder="UD01"></div>
 <div class="field"><label>Objetivo/actividad</label><textarea data-activity="description" rows="2">${E(a.description||'')}</textarea></div>
 <div class="field"><label>Recursos y organización</label><textarea data-activity="resources" rows="2">${E(a.resources||'')}</textarea></div></div></div>`).join('')}</div>
 <button type="button" class="btn secondary" data-action="prepare-add-activity">+ Añadir actividad</button></fieldset>
 ${guideField('enterprise','Plan de formación en empresa y coordinación','Registra los acuerdos del centro y las evidencias previstas; la propuesta no añade un peso extra a la nota.')}
 ${guideField('extracurricular','Actividades complementarias y extraescolares previstas','Completa el plan de salidas, autorizaciones y relación con RA/CE.')}`;
 case 5:return `<h2>6. Revisión del borrador</h2><p>EvalúaFP ha preparado la estructura del documento a partir de los campos cumplimentados y el currículo que hayas confirmado.</p>
 <p class="hint warning"><strong>Documento de trabajo.</strong> Esta versión no constituye una programación oficialmente aprobada. Revisa su adecuación normativa y los acuerdos del departamento.</p>
 <div class="guide-review-line"><b>RA y CE:</b> ${info.counts.ra} resultados y ${info.counts.ce} criterios · ${info.counts.units} unidades guardadas</div>
 ${renderDiagnosis(info)}
 ${renderCalendarSummary(info.calendar_plan)}
 <p class="small">Los apartados identificados en la programación de referencia se han distribuido entre los pasos anteriores. Todos son editables y sus propuestas se etiquetan según su origen.</p>
 ${guideField('observations','Observaciones finales de la programación','Anotaciones internas para su revisión institucional.')}
 <div class="actions"><button class="btn secondary" data-action="prepare-finish" type="button">Guardar borrador</button></div>
 <h3>Descargar borrador editable</h3><p class="small">Las exportaciones se generan desde el último borrador guardado; guarda las observaciones finales antes de descargarlas.</p>
 <div class="actions"><a class="btn" href="/api/programming-builder/${m.id}/export.docx" download>Word (.docx)</a>
 <a class="btn secondary" href="/api/programming-builder/${m.id}/export.pdf" download>PDF</a>
 <a class="btn mutedbtn" href="/api/programming-builder/${m.id}/export.md" download>Markdown</a></div>
 <h3>Descargar únicamente el programa formativo mínimo FEOE</h3><p class="small">Documento separado, editable y provisional, con criterios, tareas sencillas, evidencias y seguimiento. Usa primero «Preparar propuesta mínima» en el paso 5 si deseas revisar y guardar las tareas.</p>
 <div class="actions"><a class="btn secondary" href="/api/programming-builder/${m.id}/feoe-minimum.docx" download>Programa FEOE en Word</a>
 <a class="btn secondary" href="/api/programming-builder/${m.id}/feoe-minimum.pdf" download>Programa FEOE en PDF</a></div>`;
 }
 return '';
}
function renderFeoeMinimumPreview(info){
 const p=S.feoeMinimumPreview;
 if(!p||Number(p.module?.id)!==Number(S.moduleId))return '';
 return `<section class="guide-feoe-preview"><div class="guide-review-line"><b>${E(p.count)} criterios de ${E(p.total_criteria)}</b> · ${fmtSchoolNumber(p.percentage)} % del módulo</div>
 <p class="small">Origen: ${E(p.source)}. ${E(p.selection)}.</p>
 ${(p.warnings||[]).length?`<details><summary>${p.warnings.length} advertencias y comprobaciones pendientes</summary><ul>${p.warnings.map(w=>`<li>${E(w)}</li>`).join('')}</ul></details>`:''}
 <div class="guide-weight-scroll"><table class="guide-metrics-table guide-feoe-minimal"><thead><tr><th>RA / CE</th><th>Relación con el criterio oficial</th><th>Ejemplo de tarea sencilla (editable)</th><th>Evidencia observable (editable)</th><th>Apoyo (editable)</th></tr></thead>
 <tbody>${p.rows.map((r,i)=>`<tr data-minimum-row="${i}"><td><b>${E(r.ra_code)} / ${E(r.criteria_code)}</b><div class="small">${E(r.fit)}</div></td>
 <td>${E(r.description)}</td><td><textarea data-feoe-min="activity" rows="4" maxlength="1500">${E(r.activity)}</textarea></td>
 <td><textarea data-feoe-min="evidence" rows="4" maxlength="1500">${E(r.evidence)}</textarea></td>
 <td><textarea data-feoe-min="support" rows="4" maxlength="1000">${E(r.support)}</textarea></td></tr>`).join('')}</tbody></table></div>
 <label class="guide-confirm"><input type="checkbox" id="feoe-minimum-confirm"> He revisado la relación entre las tareas y los CE y entiendo que deben concretarse con cada empresa.</label>
 <div class="actions"><button type="button" class="btn" data-action="feoe-minimum-accept">Guardar programa FEOE revisado</button>
 <button type="button" class="btn mutedbtn" data-action="feoe-minimum-discard">Descartar propuesta</button></div>
 </section>`;
}
function collectFeoeMinimumFields(){
 const p=S.feoeMinimumPreview;
 if(!p)return;
 document.querySelectorAll('[data-minimum-row]').forEach((tr,i)=>{
  const row=p.rows[i];if(!row)return;
  for(const k of ['activity','evidence','support']){
   const el=tr.querySelector('[data-feoe-min="'+k+'"]');if(el)row[k]=el.value;
  }
 });
}
function fmtSchoolNumber(n){
 const v=Number(n);
 return Number.isFinite(v)?new Intl.NumberFormat('es-ES',{minimumFractionDigits:2,maximumFractionDigits:2}).format(v):'Pendiente';
}
function fmtSchoolDate(iso){
 if(!/^\d{4}-\d{2}-\d{2}$/.test(String(iso||'')))return 'Pendiente';
 const [year,month,day]=iso.split('-');return `${day}/${month}/${year}`;
}
function monthGroups(weeks){
 const groups=[];
 for(const w of weeks){
  const ym=String(w.start).slice(0,7);
  if(groups.length&&groups[groups.length-1].code===ym)groups[groups.length-1].span++;
  else{
   const dt=new Date(`${ym}-01T12:00:00Z`);
   const label=new Intl.DateTimeFormat('es-ES',{month:'long',year:'numeric',timeZone:'UTC'}).format(dt);
   groups.push({code:ym,label,span:1});
  }
 }
 return groups;
}
function renderCalendarSummary(plan){
 if(!plan?.configured)return '<p class="hint warning">Falta configurar la temporalización.</p>';
 const units=plan.units||[],weeks=plan.gantt_weeks||[];
 const months=monthGroups(weeks).map(group=>`<th class="gantt-month" scope="colgroup" colspan="${group.span}">${E(group.label)}</th>`).join('');
 const dateColumns=weeks.map(w=>`<th class="gantt-week" scope="col" title="Semana natural del ${fmtSchoolDate(w.start)} al ${fmtSchoolDate(w.end)}"><span>${E(fmtSchoolDate(w.start).slice(0,5))}</span><span>${E(fmtSchoolDate(w.end).slice(0,5))}</span></th>`).join('');
 const body=units.map(u=>`<tr><th class="gantt-unit-col" scope="row">${E(u.code)}<span class="small">${E(u.title)}</span></th>
 <td class="gantt-data-col">${fmtSchoolNumber(u.hours)} h</td><td class="gantt-data-col">${Number(u.term)}.ª</td>
 ${weeks.map(w=>`<td class="${u.start&&u.end&&u.start<=w.end&&u.end>=w.start?'gantt-bar-term-'+u.term:''}" title="${E(u.code)} · ${E(u.title)} · ${fmtSchoolDate(u.start)} a ${fmtSchoolDate(u.end)} · semana del ${fmtSchoolDate(w.start)} al ${fmtSchoolDate(w.end)}"></td>`).join('')}</tr>`).join('');
 const feoe=plan.feoe?.start&&plan.feoe?.end?`<tr><th class="gantt-unit-col" scope="row">FEOE<span class="small">Estancia en empresa</span></th><td class="gantt-data-col">—</td><td class="gantt-data-col">—</td>${weeks.map(w=>`<td class="${plan.feoe.start<=w.end&&plan.feoe.end>=w.start?'gantt-feoe':''}" title="FEOE · semana del ${fmtSchoolDate(w.start)} al ${fmtSchoolDate(w.end)}"></td>`).join('')}</tr>`:'';
 return `<section class="guide-calendar-summary"><h3>Temporalización prevista</h3>
 <table class="guide-metrics-table"><caption>Resumen de horas previstas y disponibles</caption><thead><tr><th>Indicador</th><th>Valor</th><th>Unidad</th></tr></thead><tbody>
 <tr><td>Horas semanales del módulo</td><td>${fmtSchoolNumber(plan.config.weekly_hours)}</td><td>h/semana</td></tr>
 <tr><td>Horas lectivas disponibles</td><td>${fmtSchoolNumber(plan.capacity)}</td><td>h</td></tr>
 <tr><td>Horas planificadas en unidades</td><td>${fmtSchoolNumber(plan.planned)}</td><td>h</td></tr>
 <tr><td>CE seleccionados para FEOE</td><td>${E(plan.feoe?.count||0)} de ${E(plan.feoe?.criteria_total||0)}</td><td>${fmtSchoolNumber(plan.feoe?.percent||0)} %</td></tr></tbody></table>
 <table class="guide-metrics-table"><caption>Distribución de las unidades por evaluación</caption><thead><tr><th>Evaluación</th><th>Horas disponibles</th><th>Horas programadas</th></tr></thead><tbody>${(plan.terms||[]).map(t=>`<tr><td>${Number(t.term)}.ª evaluación</td><td>${fmtSchoolNumber(t.capacity)} h</td><td>${fmtSchoolNumber(t.planned)} h</td></tr>`).join('')}</tbody></table>
 ${plan.warnings?.length?`<div class="hint warning"><strong>Alertas del calendario</strong><ul>${plan.warnings.map(x=>`<li>${E(x)}</li>`).join('')}</ul></div>`:''}
 <h3>Diagrama de Gantt · escala semanal</h3>
 <p class="small"><strong>Cómo leer el encabezado:</strong> la fila superior indica el <strong>mes y año</strong>; cada columna inferior corresponde a <strong>una semana natural</strong>. La primera fecha es el inicio y la segunda el final de esa semana (formato día/mes). <strong>No son horas.</strong> Las horas se muestran a la izquierda, por unidad.</p>
 <div class="guide-gantt-scroller"><table class="guide-gantt"><caption>Calendario semanal de las unidades didácticas y FEOE; fechas de inicio y final de cada semana</caption>
 <thead><tr><th class="gantt-unit-col" rowspan="2" scope="col">Unidad didáctica</th><th rowspan="2" scope="col">Horas (h)</th><th rowspan="2" scope="col">Evaluación</th>${months}</tr><tr>${dateColumns}</tr></thead><tbody>${body}${feoe}</tbody></table></div>
 <div class="guide-gantt-legend">Azul: 1.ª evaluación · Verde azulado: 2.ª · Violeta: 3.ª · Verde: periodo previsto de FEOE</div>
 <p class="small"><strong>Importante:</strong> una barra representa el intervalo previsto, no el número de horas impartidas cada semana. El Gantt se recalcula al guardar cambios de horario, fechas, festivos y unidades.</p></section>`;
}
function renderDiagnosis(info){
 const er=info.errors||[],wa=info.warnings||[];
 return `<div class="guide-diagnosis">
 <h3>Comprobación curricular</h3>
 ${!er.length?'<div class="guide-ok">✓ No faltan RA/CE para comenzar a preparar evaluaciones.</div>':`<div class="hint danger-note"><b>Debe revisar:</b><ul>${er.map(x=>`<li>${E(x)}</li>`).join('')}</ul></div>`}
 ${wa.length?`<details><summary>${wa.length} recomendaciones o cuestiones pendientes</summary><ul>${wa.map(x=>`<li>${E(x)}</li>`).join('')}</ul></details>`:'<p class="small">No se han detectado otras cuestiones pendientes con las comprobaciones automáticas.</p>'}
 </div>`;
}
const EXTRA_IMPORT_FIELDS=[
 ['justification','Justificación y principios'],['center_characteristics','Centro educativo'],
 ['student_characteristics','Alumnado'],['environment_context','Entorno productivo'],
 ['identification_data','Identificación'],['qualifications','Cualificaciones'],
 ['contents','Contenidos'],['learning_activities','Distribución de actividades'],
 ['interdisciplinarity','Interdisciplinariedad'],['extracurricular','Salidas y actividades extraescolares'],
 ['assessment_sessions','Sesiones de evaluación'],['grading','Calificación'],
 ['promotion','Promoción'],['attendance','Asistencia'],
 ['extraordinary_assessment','Evaluación extraordinaria']];
function renderImportPreview(data){
 const fields=Object.entries(data.fields||{});
 const stat=data.statistics||{};const mh=data.proposed_hours||{};
 const unknown=(data.sections||[]).filter(s=>!s.field||!data.field_labels[s.field]);
 return `<section class="panel import-panel"><h2>Importación completa: ${E(data.filename)}</h2>
 <div class="hint"><b>Extracción local (sin enviar el documento a una IA).</b> El texto original permanece guardado. La legislación, las horas y las calificaciones del documento no han sido verificadas oficialmente.</div>
 <div class="import-stats"><div><b>${stat.pages||'—'}</b><span>Páginas</span></div><div><b>${stat.sections_detected||0}</b><span>Apartados detectados</span></div><div><b>${stat.fields_identified||0}</b><span>Campos recuperados</span></div><div><b>${stat.additional_sections||0}</b><span>Otros apartados</span></div></div>
 <p>Revisa las propuestas. Marca lo que quieras incorporar al borrador. <strong>Los campos que ya tenían contenido están desmarcados</strong> para conservar tus cambios. Puedes editar cualquier texto antes de incorporarlo.</p>
 <form id="guided-content-import"><div class="import-fields">${fields.map(([key,value])=>{
    const existing=Boolean(data.existing_fields?.[key]);
    return `<details class="import-field"><summary><label class="import-select" onclick="event.stopPropagation()"><input type="checkbox" data-import-field="${E(key)}" ${existing?'':'checked'}> Incorporar</label><strong>${E(data.field_labels[key]||key)}</strong><span>${existing?'Ya existe: no sustituir salvo confirmación':'Recuperado del documento'}</span></summary>
    <div class="field"><label>Texto extraído (puedes corregirlo)</label><textarea data-import-edit="${E(key)}" rows="8" maxlength="12000">${E(value)}</textarea></div></details>`;
 }).join('')}</div>
 <details class="import-field"><summary><strong>Horas identificadas en el documento</strong><span>Confirmación opcional</span></summary>
 ${mh.total_hours!=null&&mh.weekly_hours!=null?`<p>El documento menciona <b>${mh.total_hours.toFixed(2)} horas totales</b> y <b>${mh.weekly_hours.toFixed(2)} horas semanales</b>. Estos valores <strong>no están contrastados</strong> con el currículo vigente.</p><label class="checkbox-card"><input type="checkbox" name="accept_document_hours" value="1"> Usar estas horas provisionales en mi planificación (no son una verificación normativa)</label>`:
 '<p>No se han encontrado horas totales y semanales inequívocas. Confírmalas desde la ficha del módulo o la normativa oficial.</p>'}</details>
 <details class="import-field"><summary><strong>Unidades didácticas y evaluación</strong><span>${data.proposed_units?.length||0} unidades detectadas</span></summary>
 ${(data.proposed_units||[]).length?`<p>Se identificaron títulos y evaluación. <b>No se inventan las horas</b> que no constan en la tabla. Puedes indicar las horas para importar estas unidades.</p><label class="checkbox-card"><input type="checkbox" name="accept_units" value="1"> Incorporar las unidades con las horas que indique</label>
 <div class="import-units"><table><thead><tr><th>Unidad</th><th>Título recuperado</th><th>Evaluación</th><th>Horas por asignar</th></tr></thead><tbody>${data.proposed_units.map(u=>`<tr><td>${E(u.code)}</td><td>${E(u.title)}</td><td>${u.term}ª</td><td><input type="number" data-import-unit-hours min="0.01" max="1000" step="0.01" placeholder="0,00 h" aria-label="Horas de ${E(u.code)}"></td></tr>`).join('')}</tbody></table></div>`:'<p>La distribución temporal queda recogida en los apartados originales importados. No hay filas de unidades suficientemente claras para automatizar su alta.</p>'}</details>
 <details class="import-field"><summary><strong>Criterios compartidos con la FEOE</strong><span>${data.proposed_feoe_criteria?.length||0} CE detectados</span></summary>
 ${(data.proposed_feoe_criteria||[]).length?`<p>El documento señala estos criterios para la formación en empresa. Verifícalos con el plan de formación: son propuestas documentales, no una validación normativa.</p>
 <div class="guide-ce-checks">${data.proposed_feoe_criteria.map(item=>`<div><b>${E(item.code)}</b> · Página ${item.page}</div>`).join('')}</div>
 <label class="checkbox-card"><input type="checkbox" name="accept_feoe_criteria" value="1"> Utilizar estos CE en la planificación FEOE, sustituyendo la selección actual.</label>`:
 '<p>No se ha identificado una lista inequívoca de CE relacionados con FEOE.</p>'}</details>
 <details class="import-field"><summary><strong>Otros apartados conservados</strong><span>${unknown.length} apartados no clasificados</span></summary>
 <p>También se conserva el texto de los epígrafes no identificados, para que no se pierda ninguna parte.</p>
 ${unknown.map(sec=>`<div class="guide-review-line"><b>${E(sec.title)}</b> · Página ${sec.page_start}<p>${E(sec.body.slice(0,420))}${sec.body.length>420?'…':''}</p></div>`).join('')}</details>
 <label class="checkbox-card"><input type="checkbox" name="keep_source_sections" value="1" checked> Conservar los apartados completos con las páginas de procedencia como anexo y copia consultable.</label>
 <div class="hint warning">Los RA/CE requieren una revisión curricular independiente: tras guardar, utiliza «RA y CE (IA)» o la consulta oficial, y valida los resultados antes de aplicarlos.</div>
 <div class="actions"><button class="btn" type="submit">Guardar los apartados seleccionados</button><button class="btn mutedbtn" type="button" data-action="discard-import-preview">Volver sin aplicar cambios</button></div>
 </form></section>`;
}
function guidedProposalMarkup(){
 const p=S.proposal;
 if(!p)return '';
 if(!Array.isArray(p.outcomes))return `<section class="hint warning">No se han recuperado RA y CE. Revise el documento y la fuente.</section>`;
 return `<section class="panel guide-proposal"><h2>Revisa el currículo propuesto</h2><p>Corrige los enunciados y las ponderaciones antes de incorporarlos. Los campos sin peso expreso recibirán la ponderación automática por CE, salvo que ya exista una decisión docente anterior.</p>
 ${p.source==='BOC'?`<p class="small">Fuente autonómica: <a href="${E(p.source_url)}" target="_blank" rel="noopener noreferrer">${E(p.source_title)}</a> · Anexo ${E(p.source_annex)} · SHA-256 <code>${E(p.source_sha256)}</code></p>`:''}
 ${(p.warnings||[]).length?`<div class="hint warning"><b>Advertencias:</b><ul>${p.warnings.map(w=>`<li>${E(w)}</li>`).join('')}</ul></div>`:''}
 <form id="guided-review">${p.outcomes.map((ra,i)=>`<section class="guide-ra" data-guide-ra="${i}">
 <div class="formgrid"><div class="field"><label>Código RA</label><input name="ra-code" required value="${E(ra.code)}"></div>
 <div class="field"><label>Peso sobre el módulo (%)</label><input name="ra-weight" type="number" min="0" max="100" step="0.01" value="${E(ra.weight??'')}" placeholder="Automático si se deja vacío"></div></div>
 <div class="field"><label>Descripción del RA</label><textarea name="ra-description" required rows="2">${E(ra.description)}</textarea></div>
 ${(ra.criteria||[]).map((ce,j)=>`<div class="guide-ce" data-guide-ce="${j}">
 <div class="formgrid"><div class="field"><label>Código CE</label><input name="ce-code" required value="${E(ce.code)}"></div>
 <div class="field"><label>Peso dentro del RA (%)</label><input name="ce-weight" type="number" min="0" max="100" step="0.01" value="${E(ce.weight??'')}" placeholder="Automático"></div></div>
 <div class="field"><label>Descripción del CE</label><textarea name="ce-description" rows="2" required>${E(ce.description)}</textarea></div>
 </div>`).join('')}</section>`).join('')}
 <label class="checkbox-card"><input type="checkbox" name="teacher_confirmed" required> <span>He contrastado el currículo con la programación o fuente oficial y confirmo los RA y CE que se guardarán.</span></label>
 <div class="actions"><button class="btn" type="submit">Confirmar y utilizar este currículo</button>
 <button class="btn mutedbtn" type="button" data-action="prepare-discard-proposal">Descartar propuesta</button></div></form></section>`;
}
function guidedReadProposal(form){
 return [...form.querySelectorAll('[data-guide-ra]')].map(box=>({
   code:box.querySelector('[name=ra-code]').value.trim(),description:box.querySelector('[name=ra-description]').value.trim(),
   weight:box.querySelector('[name=ra-weight]').value||null,
   criteria:[...box.querySelectorAll('[data-guide-ce]')].map(ce=>({
     code:ce.querySelector('[name=ce-code]').value.trim(),description:ce.querySelector('[name=ce-description]').value.trim(),
     weight:ce.querySelector('[name=ce-weight]').value||null
   }))
 }));
}
function scopeConsolidationMarkup(report){
 const sessions={trimestre1:'Primer trimestre',trimestre2:'Segundo trimestre',trimestre3:'Tercer trimestre',ordinaria:'Final ordinaria',extraordinaria:'Final extraordinaria'};
 const grades=['IN','SU','BI','NT','SB'];
 const gradeOptions=grades.map(g=>`<option value="${g}">${g}</option>`).join('');
 const rows=report.rows;
 return `<section class="welcome-card"><p class="welcome-kicker">CFGB · CONSOLIDACIÓN DEL ÁMBITO</p><h2>${E(report.ambito)}</h2><p>${report.course}.º · ${E(report.group)} · ${E(report.academic_year)}</p><button class="btn secondary" type="button" data-action="scope-back-notebook">Volver al cuaderno</button></section>
 <section class="panel"><h2>Evaluación</h2><form id="scope-select-session" class="formgrid"><div class="field"><label>Periodo</label><select name="session">${Object.entries(sessions).map(([k,v])=>`<option value="${k}" ${k===report.session?'selected':''}>${E(v)}</option>`).join('')}</select></div><button class="btn secondary" type="submit">Consultar</button></form><p><a href="${E(report.source_url)}" target="_blank" rel="noopener noreferrer">Normativa de evaluación de Canarias</a></p><p>Las valoraciones se registran expresamente por materia. La media final no genera automáticamente una calificación oficial.</p>
 ${Object.entries(report.matches).map(([k,items])=>`<p>${E(k)}: ${items.length===1?E(items[0].name):'Pendiente: materia ausente o duplicada'}</p>`).join('')}</section>
 ${rows.length?`<section class="panel"><h2>Registrar valoración de esta materia</h2><form id="scope-matter-grade" class="formgrid"><div class="field"><label>Alumno</label><select name="student_id">${opt(rows.map(r=>r.student),null,x=>x.name+' · '+x.code)}</select></div><div class="field"><label>Valoración docente</label><select name="grade">${gradeOptions}</select></div><div class="field"><label>Carga horaria de la materia (horas semanales)</label><input type="number" name="hours" min="0.0001" max="1000" step="0.0001" required></div><div class="field"><label>Fuente de las horas semanales contrastadas</label><input name="hours_source" required maxlength="1000"></div><div class="field"><label>Justificación de la valoración y evidencias</label><textarea name="rationale" required maxlength="4000"></textarea></div><label class="checkbox-card"><input type="checkbox" name="teacher_confirmed" required> Confirmo la valoración y las horas contrastadas.</label><button class="btn" type="submit">Guardar valoración</button></form></section>`:empty('Registra primero el alumnado de esta materia.')}
 <section class="panel"><h2>Estado del alumnado</h2>${rows.map(r=>`<details><summary>${E(r.student.name)} · ${r.calculation?(r.calculation.passed?'Propuesta: superado':'Propuesta: no superado'):(r.blockers.length?'Pendiente':'Valoraciones trimestrales completas')}</summary><ul>${r.matters.map(m=>`<li>${E(m.module_name)}: ${E(m.grade)} · ${E(m.hours)} horas · ${E(m.hours_source)}</li>`).join('')}${r.blockers.map(b=>`<li>${E(b)}</li>`).join('')}</ul>
 ${r.calculation?`<p>Media ponderada orientativa: ${Number(r.calculation.mean).toFixed(4)}. La decisión de superación se calcula sin redondear.</p>${r.decision?`<p>Última decisión registrada: ${E(r.decision.grade)} · ${r.decision.current?'Vigente respecto a las valoraciones registradas':'Desactualizada: revisar'} · ${E(r.decision.meeting_ref)}</p>`:''}<form id="scope-team-decision-${Number(r.student.id)}" data-student="${Number(r.student.id)}" data-grade-ids="${E(JSON.stringify(r.matters.map(m=>m.id)))}" class="formgrid"><div class="field"><label>Calificación acordada</label><select name="grade">${(r.calculation.passed?grades.slice(1):['IN']).map(g=>`<option value="${g}">${g}</option>`).join('')}</select></div><div class="field"><label>Referencia de la sesión</label><input name="meeting_ref" required maxlength="500"></div><div class="field"><label>Motivación del acuerdo</label><textarea name="rationale" required maxlength="4000"></textarea></div><label class="checkbox-card"><input type="checkbox" name="team_confirmed" required> He verificado identidad, cargas horarias y acuerdo del equipo docente.</label><button class="btn" type="submit">Registrar acuerdo</button></form>`:''}</details>`).join('')}</section>`;
}
function scopeRecoveryMarkup(book,recovery){
 const students=Object.fromEntries(book.students.map(x=>[x.id,x]));
 const url='/api/common-scopes/export.xlsx?module_id='+Number(S.moduleId)+'&session='+encodeURIComponent(S.scopeSession||'ordinaria');
 const plans=recovery.plans;
 return `<section class="panel"><h2>Planes de refuerzo y recuperación</h2><p>${E(recovery.notice)}</p><p><a href="${E(url)}">Descargar informe colectivo Excel</a></p>
 ${book.students.length?`<details><summary>Informes individuales Excel</summary><ul>${book.students.map(x=>`<li><a href="${E(url+'&student_id='+Number(x.id))}">${E(x.name)} · ${E(x.code)}</a></li>`).join('')}</ul></details>`:''}
 ${book.teacher_reviewed&&book.students.length&&book.criteria.length?`<details><summary>Crear plan individualizado</summary><form id="scope-create-plan" class="formgrid"><div class="field"><label>Alumno</label><select name="student_id">${opt(book.students,null,x=>x.name+' · '+x.code)}</select></div><div class="field"><label>Tipo</label><select name="kind"><option value="refuerzo">Refuerzo</option><option value="recuperacion">Recuperación</option><option value="pendiente_primero">Ámbito pendiente de primero</option></select></div><div class="field"><label>Criterios (códigos separados por comas)</label><input name="criterion_codes" required><details><summary>Consultar criterios actuales de la materia</summary><ul>${book.criteria.map(c=>`<li>${E(c.code)} · ${E(c.description)}</li>`).join('')}</ul></details></div>
 <div class="field"><label>Origen del pendiente de primero (solo para ese tipo)</label><button class="btn secondary" type="button" data-action="scope-find-origins">Buscar registros del curso anterior</button><div id="scope-origin-results"></div><label class="checkbox-card"><input type="checkbox" name="origin_confirmed"> He contrastado la identidad y el pendiente con la documentación del centro.</label></div>
 <div class="field"><label>Objetivos</label><textarea name="objectives" required maxlength="4000"></textarea></div><div class="field"><label>Actuaciones y actividades</label><textarea name="actions" required maxlength="8000"></textarea></div><div class="field"><label>Instrumentos y evidencias previstas</label><textarea name="instruments" required maxlength="4000"></textarea></div><div class="field"><label>Fecha prevista de revisión</label><input type="date" name="due_date" required></div><button type="submit" class="btn">Crear plan</button></form></details>`:'<p class="hint">Revisa el currículo y registra alumnado para crear planes.</p>'}
 ${plans.length?plans.map(p=>`<details><summary>${E(students[p.student_id]?.name||'Alumno')} · ${E(p.kind)} · ${E(p.status)} · ${E(p.due_date)}</summary><p>Objetivos: ${E(p.objectives)}</p><p>Actuaciones: ${E(p.actions)}</p><p>Instrumentos: ${E(p.instruments)}</p><ul>${p.snapshot.criteria.map(c=>`<li>${E(c.code)} · ${E(c.description)}</li>`).join('')}</ul>${p.origin_module_id?`<p>Origen: materia ${Number(p.origin_module_id)}, acuerdo ${Number(p.snapshot.origin_decision_id)}.</p>`:''}
 <form id="scope-review-plan-${Number(p.id)}" data-plan="${Number(p.id)}" class="formgrid"><div class="field"><label>Estado del seguimiento</label><select name="status"><option value="en_curso">En curso</option><option value="revisado">Revisado</option><option value="finalizado">Finalizado</option><option value="no_superado">No superado en el plan</option></select></div><div class="field"><label>Observaciones de la revisión</label><textarea name="observations" required maxlength="8000"></textarea></div><div class="field"><label>ID de evidencias, separados por comas (opcional)</label><input name="evidence_ids"><details><summary>Referencias del alumno en esta materia</summary><ul>${book.history.filter(e=>e.student_id===p.student_id&&e.level!=='NE'&&p.snapshot.criteria.some(c=>c.code===e.criterion_code)).map(e=>`<li>ID ${Number(e.id)} · ${E(e.criterion_code)} · ${E(e.level)} · ${E(e.created_at)}</li>`).join('')}</ul></details></div><label class="checkbox-card"><input type="checkbox" name="teacher_confirmed" required> Confirmo la revisión (sin modificar calificaciones).</label><button type="submit" class="btn secondary">Registrar revisión</button></form>
 <h3>Historial de revisiones</h3>${p.reviews.map(r=>`<p>${E(r.created_at)} · ${E(r.status)} · ${E(r.observations)} · Evidencias: ${E(r.evidence.map(e=>e.id).join(', '))}</p>`).join('')||'<p>Sin revisiones.</p>'}</details>`).join(''):empty('No hay planes registrados.')}</section>`;
}
function scopeNotebookMarkup(book){
 const students=Object.fromEntries(book.students.map(x=>[x.id,x]));
 const activities=Object.fromEntries(book.activities.map(x=>[x.id,x]));
 const instrumentLabels={observacion:'Observación',rubrica:'Rúbrica',lista_cotejo:'Lista de cotejo',prueba:'Prueba',portfolio:'Portafolio',proyecto:'Proyecto',otro:'Otro'};
 const ready=book.teacher_reviewed&&book.criteria.length;
 const usable=book.activities.filter(x=>x.criteria_current);
 const options=usable.map(a=>`<optgroup label="${E(a.title)}">${a.criteria.map(c=>`<option value="${Number(a.id)}|${E(c.code)}">${E(c.code)} · ${E(c.description.slice(0,90))}</option>`).join('')}</optgroup>`).join('');
 const renderEvidence=rows=>rows.length?`<div class="tablewrap"><table><thead><tr><th>Alumno</th><th>Actividad / criterio</th><th>Valoración</th><th>Observación / referencia</th><th>Registro</th></tr></thead><tbody>${rows.map(e=>`<tr><td>${E(students[e.student_id]?.name||'Alumno')}</td><td>${E(activities[e.activity_id]?.title||'Actividad')} · ${E(e.criterion_code)}</td><td>${E(e.level)}</td><td>${E(e.notes)} ${E(e.evidence_ref)}</td><td>${E(e.created_at)}</td></tr>`).join('')}</tbody></table></div>`:empty('Sin evidencias registradas.');
 return `<section class="welcome-card"><p class="welcome-kicker">CFGB · CUADERNO COMPETENCIAL</p><h2>${E(book.profile.ambito)}</h2><p>${E(book.notice)} NE = no evaluado; no equivale a suspenso.</p><button class="btn secondary" data-action="scope-edit-curriculum">Volver al currículo</button> <button class="btn" data-action="scope-open-consolidation">Consolidar calificaciones del ámbito</button></section>
 <section class="panel"><h2>Alumnado de la materia (${book.students.length})</h2><form id="scope-add-student" class="formgrid"><div class="field"><label>Código</label><input name="code" required maxlength="100"></div><div class="field"><label>Nombre</label><input name="name" required maxlength="250"></div><button type="submit" class="btn secondary">Registrar alumno</button></form>
 ${book.students.length?`<details><summary>Ver alumnado registrado</summary><ul>${book.students.map(x=>`<li>${E(x.name)} · ${E(x.code)}</li>`).join('')}</ul></details>`:''}</section>
 ${!ready?'<p class="hint warning">Confirma primero los criterios del currículo. Las evidencias históricas permanecen visibles, pero se bloquean las nuevas valoraciones.</p>':`<section class="panel"><h2>Nueva actividad evaluable</h2><form id="scope-add-activity" class="formgrid"><div class="field"><label>Título de la actividad</label><input name="title" required maxlength="250"></div><div class="field"><label>Situación de aprendizaje</label><input name="situation" required maxlength="2000"></div><div class="field"><label>Instrumento</label><select name="instrument">${Object.entries(instrumentLabels).map(([k,v])=>`<option value="${k}">${E(v)}</option>`).join('')}</select></div><div class="field"><label>Evaluación</label><select name="term"><option value="1">Primera</option><option value="2">Segunda</option><option value="3">Tercera</option></select></div><div class="field"><label>Fecha</label><input type="date" name="activity_date" required></div><div class="field"><label>Criterios de la actividad</label>${book.criteria.map(c=>`<label class="checkbox-card"><input type="checkbox" name="criterion_codes" value="${E(c.code)}"> ${E(c.code)} · ${E(c.description)}</label>`).join('')}</div><button type="submit" class="btn">Guardar actividad</button></form></section>`}
 <section class="panel"><h2>Actividades (${book.activities.length})</h2>${book.activities.length?book.activities.map(a=>`<details><summary>${E(a.title)} · ${E(a.activity_date)} · ${E(instrumentLabels[a.instrument]||a.instrument)}</summary><p>${E(a.situation)} · Evaluación ${a.term}</p>${a.criteria_current?'':'<p class="hint warning">Currículo modificado: actividad histórica, no admite nuevas evidencias.</p>'}<ul>${a.criteria.map(c=>`<li>${E(c.code)} · ${E(c.description)}</li>`).join('')}</ul></details>`).join(''):empty('Aún no hay actividades.')}</section>
 ${ready&&book.students.length&&usable.length?`<section class="panel"><h2>Registrar o revisar una evidencia</h2><form id="scope-add-evidence" class="formgrid"><div class="field"><label>Alumno</label><select name="student_id">${opt(book.students,null,x=>x.name+' · '+x.code)}</select></div><div class="field"><label>Actividad y criterio</label><select name="activity_criterion">${options}</select></div><div class="field"><label>Valoración de la evidencia</label><select name="level"><option value="NE">NE · No evaluado</option><option value="IN">IN · Insuficiente</option><option value="SU">SU · Suficiente</option><option value="BI">BI · Bien</option><option value="NT">NT · Notable</option><option value="SB">SB · Sobresaliente</option></select></div><div class="field"><label>Observación</label><textarea name="notes" rows="3" maxlength="4000"></textarea></div><div class="field"><label>Referencia de evidencia (texto; no se sube ningún archivo)</label><input name="evidence_ref" maxlength="500"></div><button class="btn" type="submit">Guardar nueva valoración</button><p class="small">Una revisión de la misma actividad, alumno y criterio conserva las anteriores en el historial.</p></form></section>`:''}
 <section class="panel"><h2>Seguimiento individual</h2>${book.students.length?book.students.map(st=>{const ev=book.latest_evidence.filter(e=>e.student_id===st.id);const seen=new Set(ev.filter(e=>e.level!=='NE'&&activities[e.activity_id]?.criteria_current).map(e=>e.criterion_code));return `<details><summary>${E(st.name)} · ${seen.size}/${book.criteria.length} criterios actuales con evidencia valorada</summary>${renderEvidence(ev)}</details>`}).join(''):empty('Registra alumnado para iniciar el seguimiento.')}</section>
 <section class="panel"><details><summary>Historial de valoraciones (${book.history.length})</summary>${renderEvidence(book.history)}</details></section>`;
}
function commonScopeMarkup(info){
 const p=info.profile,d=info.draft;
 const rows=Array.from({length:p.max_competencies},(_,i)=>{
   const code=String(i+1),c=d.competencies.find(x=>x.code===code)||{description:'',descriptors:'',criteria:[]};
   return `<details class="panel" ${c.description?'open':''}><summary><strong>Competencia específica ${code}</strong> ${c.description?'· Incorporada':''}</summary>
    <div class="scope-competency" data-code="${code}"><div class="field"><label>Enunciado oficial (dejar vacío si no se incorpora)</label><textarea name="scope-description" rows="3">${E(c.description)}</textarea></div>
    <div class="field"><label>Descriptores operativos</label><input name="scope-descriptors" value="${E(c.descriptors)}" placeholder="CCL1, CD1…"></div>
    <div class="field"><label>Criterios: una línea por criterio, con número | enunciado | descriptores opcionales</label><textarea name="scope-criteria" rows="4" placeholder="${code}.1 | Enunciado literal | Descriptores">${E(c.criteria.map(x=>[x.code,x.description,x.descriptors].join(' | ')).join('\n'))}</textarea></div></div></details>`;
 });
 return `<section class="welcome-card"><p class="welcome-kicker">CFGB · ÁMBITOS COMUNES</p><h2>${E(p.ambito)}</h2><p>Borrador de aportación de la materia al ámbito. No es una calificación oficial independiente ni un currículo completo del ámbito.</p></section>
 <section class="panel"><h2>Fuente y revisión</h2><p><a href="${E(p.source_url)}" target="_blank" rel="noopener noreferrer">${E(p.source_title)}</a> · <a href="${E(p.annex_url)}" target="_blank" rel="noopener noreferrer">Anexo de ámbitos comunes (PDF)</a>.</p>
 <p>Transcribe las competencias y los criterios que se trabajan en tu programación. Conserva la numeración del ámbito; no se generan RA ni se asignan pesos automáticamente.</p><p>Guardado: ${E(info.updated_at||'Sin borrador guardado')}</p></section><section class="panel"><h2>Consultar currículo del ámbito</h2><p>Obtén una referencia completa del ámbito y selecciona los elementos de tu materia. No se modifica el borrador guardado.</p><button type="button" class="btn secondary" data-action="scope-official">Consultar anexo oficial</button><div id="scope-official-preview"></div></section>
 <form id="common-scope-draft">${rows.join('')}<section class="panel"><div class="field"><label>Saberes básicos de la materia (bloques y enunciados)</label><textarea name="saberes" rows="8">${E(d.saberes)}</textarea></div>
 <label class="checkbox-card"><input type="checkbox" name="teacher_reviewed" ${d.teacher_reviewed?'checked':''}> He contrastado los elementos introducidos con la fuente oficial. Esta revisión no certifica la totalidad del ámbito.</label>
 <button class="btn" type="submit">Guardar borrador competencial</button></section></form>`;
}
async function viewPrepare(){
 await listModules();
 if(!S.moduleId||!S.modules.some(x=>Number(x.id)===Number(S.moduleId)))S.moduleId=S.modules[0]?.id||null;
 if(!S.moduleId||S.creatingModule){$('#main').innerHTML=`<div class="welcome-card"><p class="welcome-kicker">PASO INICIAL</p><h2>Prepara tu primer módulo</h2>
 <p>Solo necesitamos los datos básicos. Después podrás incorporar una programación existente, crear un borrador o configurar la evaluación.</p></div>
 <section class="panel"><h2>Datos del módulo profesional</h2><form id="prepare-create" class="formgrid">
 <div class="field"><label>Curso académico</label><input name="academic_year" required value="2026-2027"></div>
 <div class="field"><label>Comunidad autónoma / ámbito educativo</label><select name="territory" required>${territoryOptions('Canarias')}</select></div>
 <div class="field"><label>Ciclo formativo</label><select name="cycle" required>${agCycleOptions()}</select></div>
 <div class="field"><label for="ag-course-filter">Curso del ciclo (filtro opcional)</label><select id="ag-course-filter"><option value="">Primero y segundo</option><option value="1">1.º curso</option><option value="2">2.º curso</option></select></div>
 <div class="field"><label for="ag-module-pick">Elegir módulo de la lista de referencia</label><select id="ag-module-pick"><option value="">Seleccione primero un ciclo</option></select></div>
 <div class="field"><label>Nombre del módulo (editable)</label><input name="name" required list="ag-module-list" placeholder="Selecciona del listado o escribe el nombre"><datalist id="ag-module-list"></datalist><p class="small" id="ag-module-note">Elige un ciclo para consultar módulos de referencia.</p><p class="small" id="ag-module-source"></p></div>
 <div class="field"><label>Grupo (opcional)</label><input name="group_name" placeholder="1.º A"></div>
 <input type="hidden" name="reference_course"><input type="hidden" name="reference_code">
 <input type="hidden" name="catalog_entry_id"><p class="small" data-catalog-selection></p>
 <button class="btn" type="submit">Crear módulo y continuar</button></form></section>${catalogPanel()}`;return;}
 const mid=Number(S.moduleId);
 const scope=await API('/api/common-scopes/draft?module_id='+mid);
 if(scope.profile){
   let markup;
   if(S.scopeNotebookModule===mid){
     if(S.scopeConsolidationModule===mid){
       markup=scopeConsolidationMarkup(await API('/api/common-scopes/consolidation?module_id='+mid+'&session='+encodeURIComponent(S.scopeSession||'ordinaria')));
     }else{
       const [book,recovery]=await Promise.all([API('/api/common-scopes/notebook?module_id='+mid),API('/api/common-scopes/recovery?module_id='+mid)]);
       if(S.page!=='preparar'||Number(S.moduleId)!==mid)return;
       markup=scopeNotebookMarkup(book)+scopeRecoveryMarkup(book,recovery);
     }
   }else{
     markup=`<section class="panel"><button class="btn" data-action="scope-open-notebook">Abrir cuaderno de evaluación competencial</button></section>`+commonScopeMarkup(scope);
   }
   if(S.page!=='preparar'||Number(S.moduleId)!==mid)return;
   $('#main').innerHTML=`<section class="guide-context"><div class="field"><label>Materia que estás preparando</label><select id="prepare-module">${opt(S.modules,mid,m=>m.name+' · '+m.academic_year)}</select></div><button type="button" class="btn secondary" data-action="prepare-new-module">+ Nuevo módulo</button></section>`+markup;
   return;
 }
 const info=await API('/api/programming-builder/'+Number(S.moduleId));S.prepareInfo=info;
 if(info.draft?.official_module_code){S.curriculumHistory=await API('/api/curriculum/history?module_id='+Number(S.moduleId));}
 else {S.curriculumHistory={versions:[],count:0};S.curriculumHistoryDiff=null;}
 S.normativeMonitor=await API('/api/national/boe-monitor?module_id='+Number(S.moduleId));
 if(S.preparePath==='create'&&[1,4].includes(S.prepareStep)){
   S.nationalSources=await API('/api/national/sources?module_id='+Number(S.moduleId));
 }
 if(S.preparePath==='create'&&S.prepareStep===4){
    const region=S.wizardDraft?.region||info.draft.region;
    S.calendarInfo=await API('/api/territories/calendar?region='+encodeURIComponent(region)+'&academic_year='+encodeURIComponent(info.module.academic_year));
 S.calendarVersions=await API('/api/national/calendar/versions?module_id='+Number(S.moduleId));
 S.generalCalendarLibrary=await API('/api/national/general-calendar?module_id='+Number(S.moduleId));
 }
 if(!S.wizardDraft)S.wizardDraft=JSON.parse(JSON.stringify(info.draft));
 const moduleSelector=`<section class="guide-context"><div class="field"><label>Módulo que estás preparando</label>
 <select id="prepare-module">${opt(S.modules,S.moduleId,m=>m.name+' · '+m.academic_year)}</select></div>
 <button type="button" class="btn secondary" data-action="prepare-new-module">+ Nuevo módulo</button>
 <span class="badge">${info.counts.ra} RA · ${info.counts.ce} CE</span></section>${agReferencePanel(info.module_reference)}`;
 if(!S.preparePath){
 const choices=[
 ['import','file-up','Ya tengo una programación','Recuperar todo lo aprovechable: normativa, metodología, evaluación, unidades, recursos, actividades, horas y currículo.'],
 ['create','book-open','Crear mi programación','Redactar un borrador editable utilizando el currículo confirmado.'],
 ['evaluation','list-checks','Solo configurar la evaluación','Preparar RA, CE y criterios para usar pruebas y calificaciones, sin generar una programación completa.']];
 $('#main').innerHTML=`${moduleSelector}<div class="welcome-card"><p class="welcome-kicker">PREPARACIÓN DE MÓDULOS</p>
 <h2>¿Cómo quieres empezar?</h2><p>Elige la opción que más se ajuste a tu situación. Puedes volver y cambiarla cuando lo necesites.</p></div>
 <div class="guide-choices">${choices.map(([key,icon,title,description])=>`<button class="guide-choice" type="button" data-action="prepare-select-path" data-path="${key}">
 <strong>${E(title)}</strong><span>${E(description)}</span><b>Continuar →</b></button>`).join('')}</div>
 ${renderDiagnosis(info)}${info.updated_at?`<section class="panel"><h2>Borrador guardado</h2><p>Última actualización: ${E(info.updated_at)}</p>
 <button type="button" class="btn secondary" data-action="prepare-wizard-open">Editar el borrador</button></section>`:''}
 <div class="actions"><button class="btn mutedbtn" data-page="programaciones">Edición manual de RA y CE (avanzado)</button></div>`;return;
 }
 const back=`<button class="btn mutedbtn" type="button" data-action="prepare-overview">← Cambiar de opción</button>`;
 if(S.importPreview){$('#main').innerHTML=moduleSelector+`<div class="actions">${back}</div>`+renderImportPreview(S.importPreview);return;}
 if(S.proposal){$('#main').innerHTML=moduleSelector+`<div class="actions">${back}</div>`+guidedProposalMarkup();return;}
 if(S.preparePath==='import'){
 const moduleDetail=await API('/api/modules/'+Number(S.moduleId));
 $('#main').innerHTML=`${moduleSelector}<div class="actions">${back}</div><section class="panel"><h2>Importa tu programación actual</h2>
 <p>No es necesario utilizar una plantilla específica. EvalúaFP conservará el original y te propondrá los RA y CE que pueda acreditar mediante su texto.</p>
 <form id="guided-upload"><input type="hidden" name="module_id" value="${Number(S.moduleId)}"><div class="field"><label>Documento (PDF, DOCX, TXT o MD)</label>
 <input type="file" accept=".pdf,.docx,.txt,.md" name="document" required></div><div class="actions"><button class="btn" type="submit">Guardar documento</button></div></form></section>
 ${curriculumReviewPanel()}
 <section class="panel"><h2>Programaciones guardadas</h2>${moduleDetail.programmings?.length?moduleDetail.programmings.map(p=>`<div class="guide-document">
 <span><b>${E(p.filename)}</b><small>${p.text_length} caracteres extraídos</small></span>
 <div class="actions"><button class="btn secondary smallbtn" type="button" data-action="review-all-program" data-id="${p.id}" ${p.text_length?'':'disabled'}>Revisar TODA la programación</button><button class="btn mutedbtn smallbtn" type="button" data-action="guided-analyze" data-id="${p.id}" ${p.text_length?'':'disabled'}>RA y CE (IA)</button></div></div>`).join(''):empty('Aún no has importado ninguna programación.')}
 <p class="small">Las propuestas de IA se revisan antes de guardarse. Los PDF escaneados sin texto seleccionable requieren OCR previo.</p></section>
 ${renderDiagnosis(info)}<div class="actions"><button class="btn secondary" data-action="prepare-select-path" data-path="create">Continuar al borrador editable →</button></div>`;return;
 }
 if(!info.counts.ce){
 $('#main').innerHTML=`${moduleSelector}<div class="actions">${back}</div><section class="panel"><h2>Primero, incorpora el currículo de tu módulo</h2>
 <p>Para evitar RA y CE inventados, EvalúaFP necesita los enunciados desde una fuente comprobable.</p>
 ${curriculumReviewPanel()}
 ${boeDiscoveryPanel()}
 ${todofpExplorerPanel('builder')}
 ${info.canarias_curriculum_hint?`<div class="guide-review-line"><strong>Currículo autonómico canario disponible</strong><p>${E(info.canarias_curriculum_hint.source_title)} · anexo ${E(info.canarias_curriculum_hint.source_annex)} · ${Number(info.canarias_curriculum_hint.expected_ra)} RA / ${Number(info.canarias_curriculum_hint.expected_ce)} CE.</p><p><a href="${E(info.canarias_curriculum_hint.source_url)}" target="_blank" rel="noopener noreferrer">Abrir el BOC y su PDF firmado</a>. Las horas del documento no se confirman automáticamente.</p><button class="btn" type="button" data-action="guided-boc">Recuperar RA y CE del currículo canario</button></div>`:''}
 ${info.curriculum_source_hint?`<p class="hint"><strong>Fuente estatal localizada:</strong> ${E(info.curriculum_source_hint.boe_id)} · módulo ${E(info.curriculum_source_hint.module_code)} · ${Number(info.curriculum_source_hint.expected_ra)} RA y ${Number(info.curriculum_source_hint.expected_ce)} CE de la publicación original. Comprueba la normativa aplicable al curso antes de confirmar.</p>`:''}
 <div class="field"><label>Identificador del BOE (si lo conoces)</label><input id="guide-boe" placeholder="BOE-A-AAAA-NNN" value="${E(info.curriculum_source_hint?.boe_id||S.boeSelectedId||'')}"></div>
 <div class="actions"><button class="btn" type="button" data-action="guided-boe">Consultar RA y CE en el BOE</button>
 <button class="btn secondary" data-action="prepare-select-path" data-path="import">Importar una programación existente</button>
 <button class="btn mutedbtn" data-page="programaciones">Introducir RA/CE manualmente</button></div>
 <p class="hint warning">Comprueba la correspondencia del título, módulo, curso y normas autonómicas antes de aprobar cualquier propuesta.</p></section>`;return;
 }
 if(S.preparePath==='create'&&S.autoProposedModuleId!==Number(S.moduleId)){
   S.autoProposedModuleId=Number(S.moduleId);
   try{
     const result=await API('/api/programming-builder/propose','POST',{
         module_id:Number(S.moduleId),region:S.wizardDraft.region||'Canarias',mode:'base'});
     applyAssistantFields(result,'base');
   }catch(err){S.autoProposedModuleId=null;console.warn('No se ha podido rellenar el borrador local:',err);}
 }
 if(S.preparePath==='evaluation'){
   $('#main').innerHTML=`${moduleSelector}<div class="actions">${back}</div><section class="panel">
   <h2>Tu evaluación, preparada en tres pasos</h2>
   <p>El currículo confirmado del módulo tiene <b>${info.counts.ra} RA</b> y <b>${info.counts.ce} CE</b>. Puedes utilizarlo sin generar otra programación completa.</p>
   ${renderDiagnosis(info)}
   <form id="prepare-minimum"><div class="field"><label>¿Cómo se evaluará el módulo? (opcional)</label>
   <textarea name="assessment" rows="3" placeholder="Instrumentos, notas, criterios de superación...">${E(S.wizardDraft.assessment||'')}</textarea></div>
   <div class="field"><label>Recuperación (opcional)</label><textarea name="recovery" rows="2">${E(S.wizardDraft.recovery||'')}</textarea></div>
   <div class="actions"><button class="btn secondary" type="submit">Guardar configuración básica</button></div></form>
   <div class="guide-choices" style="margin-top:18px"><button type="button" class="guide-choice" data-page="examenes"><strong>Crear un examen</strong><span>Genera pruebas y rúbricas vinculadas a CE.</span><b>Ir a exámenes →</b></button>
   <button type="button" class="guide-choice" data-page="evaluacion"><strong>Configurar el cuaderno</strong><span>Instrumentos, evidencias, ponderaciones y notas.</span><b>Ir a evaluación →</b></button></div>
   <p class="small">Las ponderaciones específicas, los instrumentos de calificación y el tratamiento de empresa se confirman en «Evaluación».</p></section>`;return;
 }
 const steps=GUIDE_STEPS.map((name,i)=>`<span class="guide-step ${i===S.prepareStep?'current':''} ${i<S.prepareStep?'done':''}">${i+1}. ${E(name)}</span>`).join('');
 $('#main').innerHTML=`${moduleSelector}<div class="actions">${back}</div><div class="guide-steps">${steps}</div>
 <section class="panel"><form id="prepare-wizard-form">${aiToolbar()}${aiPreviewPanel()}${wizardStepMarkup(S.prepareStep,info)}
 <div class="actions guide-wizard-actions">${S.prepareStep>0?'<button type="button" class="btn secondary" data-action="prepare-wizard-back">← Anterior</button>':''}
 ${S.prepareStep<5?'<button class="btn" type="submit">Guardar y continuar →</button>':''}</div></form></section>${S.prepareStep===1?curriculumReviewPanel():''}`;
}
function collectWizardFields(){
 const form=$('#prepare-wizard-form');if(!form||!S.wizardDraft)return;
 const previousRegion=String(S.wizardDraft.region||'Canarias');
 S.wizardDraft.assistant_meta=S.wizardDraft.assistant_meta||{};
 for(const key of WD_FIELDS){const el=form.elements[key];if(el){
    const next=String(el.value||'');const old=String(S.wizardDraft[key]||'');
    if(old!==next)S.wizardDraft.assistant_meta[key]={origin:'Docente',teacher_edited:true};
    S.wizardDraft[key]=next;
 }}
 // La carga horaria de una comunidad no se traslada a otra al cambiar el ámbito.
 if(previousRegion!==String(S.wizardDraft.region||'Canarias')){
   S.generalCalendarLibrary=null;S.generalCalendarDiff=null;
   S.calendarDocumentPreview=null;S.calendarDocumentModuleId=null;S.calendarAiPreview=null;S.calendarAiModuleId=null;S.calendarAiFragment='';
   const cfg=S.wizardDraft.schedule||{};
   Object.assign(cfg,{region:S.wizardDraft.region,island:'',municipality:'',
    calendar_confirmed:false,calendar_profile_id:'',calendar_source_url:'',
    calendar_source_description:'',calendar_correction_urls:[],calendar_academic_year:'',
    start_date:'',end_date:'',evaluation_ends:['','',''],
    vacation_periods:[],regional_non_teaching_days:[],extra_non_teaching_days:[],
    hours_confirmed:false,weekly_hours:0,total_hours:0,weekday_hours:[0,0,0,0,0],
    hours_source_url:'',hours_source_description:'Pendiente de consultar fuente horaria del territorio seleccionado'});
   S.wizardDraft.curriculum_confirmed=false;
   S.wizardDraft.schedule=cfg;
 }
 if(S.prepareStep===1){S.wizardDraft.curriculum_confirmed=Boolean(form.elements['curriculum-confirmed']?.checked);}
 if(S.prepareStep===4){
 S.wizardDraft.units=[...form.querySelectorAll('[data-unit-row]')].map(box=>({
  code:box.querySelector('[data-unit=code]').value,title:box.querySelector('[data-unit=title]').value,
  term:Number(box.querySelector('[data-unit=term]').value),hours:Number(box.querySelector('[data-unit=hours]').value),
  criteria_codes:[...box.querySelectorAll('input[data-unit-ce]:checked')].map(el=>el.dataset.unitCe),
  instruments:box.querySelector('[data-unit=instruments]')?.value||'',resources:box.querySelector('[data-unit=resources]')?.value||''
 }));
 const cfg=S.wizardDraft.schedule||{};
 const field=k=>form.elements[k]?.value||'';
 const previousHours=[Number(cfg.weekly_hours||0),Number(cfg.total_hours||0)];
 cfg.weekly_hours=Number(field('schedule-weekly-hours'));
 cfg.region=S.wizardDraft.region||'Canarias';
 S.wizardDraft.units_mode=form.elements['guide-units-auto']?.checked?'auto':'manual';
 cfg.hours_confirmed=Boolean(form.elements['schedule-hours-confirmed']?.checked);
 cfg.total_hours=Number(field('schedule-total-hours')||0);
 const enteredHourUrl=field('schedule-hours-source').trim();
 const enteredHourDescription=field('schedule-hours-description').trim();
 if(previousHours.some((v,i)=>Math.abs(v-[cfg.weekly_hours,cfg.total_hours][i])>0.001)){
   cfg.hours_source_description=enteredHourDescription||'Horario introducido por el docente; pendiente de contrastar';
   cfg.hours_source_url=enteredHourUrl;
 }
 cfg.hours_source_url=enteredHourUrl;cfg.hours_source_description=enteredHourDescription;
 cfg.start_date=field('schedule-start-date');cfg.end_date=field('schedule-end-date');
 cfg.island=field('schedule-island');cfg.municipality=field('schedule-municipality');
 cfg.weekday_hours=[...form.querySelectorAll('[data-weekday]')].map(x=>Number(x.value||0));
 cfg.evaluation_ends=[1,2,3].map(i=>field('schedule-term-'+i));
 cfg.extra_non_teaching_days=field('schedule-extra-days').split(/[\s,;]+/).filter(Boolean);
 cfg.vacation_periods=readVacationLines(field('schedule-vacations'));
 cfg.regional_non_teaching_days=readHolidayLines(field('schedule-regional-days'));
 cfg.calendar_source_url=field('schedule-calendar-source').trim();
 cfg.calendar_source_description=field('schedule-calendar-source-description').trim();
 cfg.calendar_correction_urls=field('schedule-calendar-corrections').split(/[\r\n]+/).map(x=>x.trim()).filter(Boolean);
 cfg.calendar_confirmed=Boolean(form.elements['schedule-confirmed']?.checked);
 cfg.feoe_start=field('schedule-feoe-start');cfg.feoe_end=field('schedule-feoe-end');
 cfg.feoe_center_hours_weekly=field('schedule-feoe-center-hours')===''?null:Number(field('schedule-feoe-center-hours'));
 cfg.feoe_target_percent=Number(field('schedule-feoe-target')||15);
 cfg.feoe_criteria_codes=[...form.querySelectorAll('input[data-feoe-ce]:checked')].map(x=>x.dataset.feoeCe);
 S.wizardDraft.schedule=cfg;
 S.wizardDraft.activities=[...form.querySelectorAll('[data-activity-row]')].map(box=>Object.fromEntries(
 ['type','title','date','unit_code','description','resources'].map(k=>[k,box.querySelector('[data-activity='+k+']')?.value||''])));
 }
}
async function saveWizardPage(){
 collectWizardFields();
 if(S.prepareStep===4&&S.wizardDraft.units.some(u=>!u.code||!u.title||!Number.isFinite(u.hours)||u.hours<=0)){
  toast('Complete el código, el nombre y las horas de cada unidad.',true);return false;
 }
 S.wizardDraft.source_type=S.preparePath==='evaluation'?'evaluation':'create';
 const result=await busy(()=>API('/api/programming-builder/save','POST',{
  module_id:Number(S.moduleId),draft:S.wizardDraft}),'Borrador guardado localmente.');
 return !!result;
}

async function viewPrograms(){
 await listModules();
 if(S.moduleId && !S.modules.some(x=>x.id===Number(S.moduleId)))S.moduleId=null;
 if(!S.moduleId && S.modules.length) S.moduleId=S.modules[0].id;
 S.moduleDetails=S.moduleId?await API('/api/modules/'+S.moduleId):null;
 const d=S.moduleDetails;
 $('#main').innerHTML=`${intro('Importe la programación en PDF, DOCX o texto. Los CE sin peso indicado se ponderan por igual y cada RA recibe un peso proporcional al número de CE; las ponderaciones expresas se respetan y pueden editarse.')}
 <div class="panel"><h2>Nuevo módulo formativo</h2><form id="create-module" class="formgrid">
 <div class="field"><label>Curso académico</label><input required name="academic_year" value="2026-2027" placeholder="2026-2027"></div>
 <div class="field"><label>Comunidad autónoma / ámbito educativo</label><select name="territory" required>${territoryOptions('Canarias')}</select></div>
 <div class="field"><label>Ciclo formativo</label><select required name="cycle">${agCycleOptions()}</select></div>
 <div class="field"><label for="ag-course-filter">Curso del ciclo (filtro opcional)</label><select id="ag-course-filter"><option value="">Primero y segundo</option><option value="1">1.º curso</option><option value="2">2.º curso</option></select></div>
 <div class="field"><label for="ag-module-pick">Elegir módulo de la lista de referencia</label><select id="ag-module-pick"><option value="">Seleccione primero un ciclo</option></select></div>
 <div class="field"><label>Módulo profesional (editable)</label><input required name="name" list="ag-module-list" placeholder="Selecciona del listado o escribe el nombre"><datalist id="ag-module-list"></datalist><p class="small" id="ag-module-note">Elige un ciclo para consultar módulos de referencia.</p><p class="small" id="ag-module-source"></p></div>
 <div class="field"><label>Grupo</label><input name="group_name" placeholder="1.º A"></div>
 <input type="hidden" name="reference_course"><input type="hidden" name="reference_code">
 <input type="hidden" name="catalog_entry_id"><p class="small" data-catalog-selection></p>
 <button class="btn" type="submit">Crear módulo</button></form></div>
 ${catalogPanel()}
 ${S.modules.length?`<div class="panel"><div class="formrow"><div class="field grow"><label>Trabajar con el módulo</label><select id="module-select">${opt(S.modules,S.moduleId,m=>m.name+' · '+m.academic_year)}</select></div></div></div>`:empty('Cree el primer módulo para comenzar.')}
 ${d?renderModule(d):''}`;
}
function renderModule(d){const {module:m,outcomes,criteria,students,programmings,materials}=d;
 const rs=outcomes.map(r=>`<div class="item"><div class="grow"><div class="title">${E(r.code)} · ${E(r.description)}</div>
 <div class="detail">Ponderación del RA sobre el módulo: <b>${V(r.weight)}</b> · ${E(r.weight_origin==='default'?'Automática por número de CE':r.weight_origin==='manual'?'Personalizada por el docente':r.weight_origin==='programming'?'Programación':'Existente')}</div></div>
 <div class="right"><button class="btn secondary smallbtn" data-action="edit-outcome" data-id="${r.id}">Editar RA</button></div></div>
 ${criteria.filter(c=>c.outcome_id===r.id).map(c=>`<div class="item" style="margin-left:17px;background:#fafdff"><div class="grow"><div class="title">${E(c.code)}</div><div class="detail">${E(c.description)}</div>
 <div class="detail">Peso dentro del RA: <b>${V(c.weight)}</b> · ${E(c.weight_origin==='default'?'Automático, igual por CE':c.weight_origin==='manual'?'Personalizado':c.weight_origin==='programming'?'Programación':'Existente')}</div></div><button class="btn mutedbtn smallbtn" data-action="edit-criterion" data-id="${c.id}">Editar CE</button></div>`).join('')}`).join('');
 const proposal=S.proposal?`<div class="panel"><h2>Propuesta de extracción pendiente de revisión</h2><div class="hint warning">Revise todos los pesos y descripciones. Un valor null significa que no se indica una ponderación expresa. Al confirmar, EvalúaFP asignará pesos iguales a los CE y proporcionales a su número para los RA, salvo valores expresos. Los pesos se podrán editar posteriormente.</div>
 ${S.proposal.warnings?.length?`<p class="small">Advertencias: ${S.proposal.warnings.map(E).join(' · ')}</p>`:''}
 ${S.proposal.coverage?`<div class="hint"><strong>Control de cobertura:</strong> RA citados: ${S.proposal.coverage.ra_cited} · RA acreditados: ${S.proposal.coverage.ra_accepted} · CE propuestos por IA: ${S.proposal.coverage.ce_proposed} · CE acreditados: ${S.proposal.coverage.ce_accepted} · CE descartados: ${S.proposal.coverage.ce_discarded}. <strong>Solo los acreditados se ofrecen para importar.</strong></div>`:''}
 ${/t[eé]cnica contable/i.test(m.name)?`<p class="small">Para este módulo puede contrastar los enunciados oficiales de RA y CE en el <a target="_blank" rel="noopener noreferrer" href="https://www.boe.es/eli/es/rd/2009/10/30/1631">RD 1631/2009 (Técnica Contable, código 0441)</a>. Esta consulta no cambia los pesos de la programación.</p>`:''}

 <form id="apply-proposal"><div class="field"><label>Resultados y criterios propuestos (JSON editable)</label><textarea rows="15" name="outcomes_json">${E(JSON.stringify(S.proposal.outcomes,null,2))}</textarea></div>
 <div class="actions"><button class="btn" type="submit">Confirmar e importar RA/CE</button><button type="button" class="btn secondary" data-action="discard-proposal">Descartar</button></div></form></div>`:'';
 return `<div class="grid2"><section class="panel"><h2>Programaciones originales</h2>
 <form id="upload-program"><input type="hidden" name="module_id" value="${m.id}">
 <div class="field"><label>PDF, DOCX, TXT o Markdown</label><input required name="document" type="file" accept=".pdf,.docx,.txt,.md"></div><div class="actions"><button class="btn" type="submit">Guardar original y extraer texto</button></div></form>
 <div class="hint" style="margin-top:14px"><strong>Consulta de normativa oficial en caso de duda</strong>
 <p>Obtenga RA y CE de una disposición del BOE. Se mostrará una propuesta para revisión, sin inventar ponderaciones normativas ni modificar notas. Se aplicarán los pesos automáticos docentes cuando no consten.</p>
 <label>Identificador de la disposición (BOE-A-AAAA-NNN)</label><input id="official-boe-id" placeholder="BOE-A-AAAA-NNN (opcional para módulos indexados)">
 <button type="button" class="btn secondary" data-action="official-curriculum" style="margin-top:8px">Consultar RA/CE en el BOE</button></div>
 ${programmings.length?`<div class="section-title">Documentos guardados</div><div class="itemlist">${programmings.map(p=>`<div class="item"><div><b>${E(p.filename)}</b><div class="small">${p.text_length} caracteres de texto extraído</div></div><button class="btn secondary smallbtn" data-action="analyze-program" data-id="${p.id}">Analizar con IA</button></div>`).join('')}</div>`:empty('No hay programación cargada.')}
 </section><section class="panel"><h2>Material didáctico asociado a la programación</h2>
 <p class="small">Suba apuntes, unidades didácticas o libros de texto en PDF, DOCX, TXT o MD. Se conserva cada original y se extrae texto por página (PDF) o bloque (otros formatos). Si hay material activo, <strong>la IA solo podrá generar preguntas con pasajes de ese material</strong> y se guardará la referencia exacta de cada pregunta.</p>
 ${programmings.length?`<form id="upload-material"><input type="hidden" name="module_id" value="${m.id}">
 <div class="field"><label>Programación a la que se asocia</label><select name="programming_id">${opt(programmings,programmings[0].id,p=>p.filename)}</select></div>
 <div class="field"><label>Archivos de material (se admiten varios)</label><input required name="documents" type="file" multiple accept=".pdf,.docx,.txt,.md"></div>
 <div class="actions"><button class="btn" type="submit">Incorporar a la biblioteca local</button></div></form>`:empty('Primero debe subir una programación para poder asociar los materiales.')}
 ${materials.length?`<div class="section-title">Biblioteca documental (${materials.length} archivo/s)</div><div class="itemlist">${materials.map(x=>`<div class="item"><div class="grow"><b>${E(x.filename)}</b><div class="small">Programación #${x.programming_id} · ${x.unit_count} páginas/bloques · ${x.chunk_count} pasajes · original guardado</div></div><div class="actions"><a class="btn smallbtn mutedbtn" href="/api/materials/${x.id}/original">Original</a><button type="button" class="btn smallbtn ${x.active?'secondary':'mutedbtn'}" data-action="toggle-material" data-id="${x.id}" data-active="${x.active?1:0}">${x.active?'Activo · desactivar':'Inactivo · activar'}</button></div></div>`).join('')}</div>`:empty('Todavía no hay materiales de consulta.')}
 <p class="hint">Los PDF escaneados sin capa de texto deben procesarse con OCR antes de subirlos. No se envía el libro completo a la IA: únicamente los pasajes necesarios para redactar preguntas.</p>
 </section><section class="panel"><h2>Alumnado del módulo</h2><form id="create-student" class="formrow"><input type="hidden" name="module_id" value="${m.id}">
 <div class="field grow"><label>Código identificador</label><input name="code" required placeholder="ALU001"></div>
 <div class="field grow"><label>Nombre y apellidos</label><input name="name" required placeholder="Nombre del alumno/a"></div>
 <button class="btn" type="submit">Añadir</button></form><p class="small">Se recomienda utilizar códigos no identificativos en los nombres de archivos y cargas ZIP.</p>
 ${students.length?`<div class="itemlist">${students.map(s=>`<div class="item"><b>${E(s.name)}</b><span class="badge">${E(s.code)}</span></div>`).join('')}</div>`:empty('Aún no se ha registrado alumnado.')}</section></div>
 ${proposal}
 <section class="panel"><div class="subhead"><h2>Resultados de aprendizaje y criterios de evaluación</h2><span class="badge">${outcomes.length} RA · ${criteria.length} CE</span></div>
 ${rs||empty('No hay RA o criterios. Impórtelos con IA o añádalos manualmente.')}
 <div class="grid2" style="margin-top:19px"><form id="create-outcome"><h3>Añadir RA manualmente</h3><div class="formgrid">
 <div class="field"><label>Código RA</label><input required name="code" placeholder="RA1"></div>
 <div class="field"><label>Peso RA (%)</label><input name="weight" type="number" min="0" max="100" step=".01" placeholder="Automático si vacío"></div></div>
 <div class="field"><label>Descripción del RA</label><textarea required name="description"></textarea></div>
 <button type="submit" class="btn secondary">Guardar RA</button></form>
 <form id="create-criterion"><h3>Añadir CE manualmente</h3>
 <div class="field"><label>Resultado al que pertenece</label><select required name="outcome_id">${opt(outcomes,'',r=>r.code)}</select></div>
 <div class="formgrid"><div class="field"><label>Código CE</label><input required name="code" placeholder="RA1.a"></div>
 <div class="field"><label>Peso dentro del RA (%)</label><input type="number" step=".01" min="0" max="100" name="weight" placeholder="Automático si vacío"></div></div>
 <div class="field"><label>Descripción del criterio</label><textarea required name="description"></textarea></div>
 <button class="btn secondary" type="submit" ${!outcomes.length?'disabled':''}>Guardar CE</button></form></div></section>`;
}
function quickExamMarkup(d){
 if(!d?.criteria?.length)return `<section class="panel"><h2>Antes de crear una prueba</h2>
 <p>Necesitas incorporar y confirmar al menos un criterio de evaluación.</p><button class="btn" data-page="preparar" type="button">Preparar módulo</button></section>`;
 const raOptions=d.outcomes.map(r=>`<div class="quick-ra"><label class="checkbox-card"><input class="ra-checkbox" type="checkbox" data-ra="${r.id}">
 <span><strong>${E(r.code)} · ${E(r.description)}</strong><small>Seleccionar todos los criterios de este RA</small></span></label>
 <details><summary>Elegir criterios de ${E(r.code)}</summary>
 <div class="quick-ce">${d.criteria.filter(c=>c.outcome_id===r.id).map(c=>`<label class="checkbox-card"><input type="checkbox" name="criteria_ids" data-parent="${r.id}" value="${c.id}">
 <span><b>${E(c.code)}</b> · ${E(c.description)}</span></label>`).join('')}</div></details></div>`).join('');
 return `<section class="panel quick-exam"><div class="subhead"><h2>Crear un examen en tres decisiones</h2><span class="badge">Asistente sencillo</span></div>
 <p class="small">1. Ponle título. 2. Elige tipo y preguntas. 3. Marca qué RA o CE quieres evaluar.</p>
 <form id="generate-exam-quick">
 <div class="formgrid"><div class="field"><label>Módulo</label><select name="module_id" id="quick-exam-module">${opt(S.modules,S.examModuleId,m=>m.name+' · '+m.academic_year)}</select></div>
 <div class="field"><label>Título de la prueba</label><input name="title" required placeholder="Prueba de la unidad 2"></div>
 <div class="field"><label>Tipo de examen</label><select name="kind"><option value="desarrollo">Preguntas de desarrollo</option>
 <option value="test">Tipo test</option><option value="mixto">Mixto</option><option value="problemas">Problemas prácticos</option></select></div>
 <div class="field"><label>Número de preguntas</label><input type="number" name="question_count" min="1" max="30" value="5" required></div></div>
 <input type="hidden" name="programming_id" value="${d.programmings?.[0]?.id||''}">
 <input type="hidden" name="difficulty" value="medio"><input type="hidden" name="model_count" value="1">
 <input type="hidden" name="problem_count" value="0"><input type="hidden" name="center_name" value="">
 <input type="hidden" name="exam_date" value=""><input type="hidden" name="duration_minutes" value="60">
 <input type="hidden" name="total_points" value="10"><input type="hidden" name="instructions" value="">
 <h3>Resultados y criterios que deseas evaluar</h3><div class="quick-criteria">${raOptions}</div>
 <div class="actions"><button class="btn" type="submit">Generar examen con IA</button></div>
 <p class="small">La generación requiere una API de IA configurada. La prueba podrá revisarse y descargarse antes de utilizarla.</p>
 </form></section>`;
}

async function viewExams(){
 await Promise.all([listModules(),listExams()]);
 if(!S.examModuleId&&S.modules.length)S.examModuleId=S.modules[0].id;
 const d=S.examModuleId?await API('/api/modules/'+S.examModuleId):null;
 const selected=S.examId?await API('/api/exams/'+S.examId).catch(()=>null):null;
 S.examDetails=selected;
 $('#main').innerHTML=`${intro('Elige los criterios que deseas evaluar y genera tu prueba. Puedes utilizar el asistente sencillo o abrir las opciones detalladas.')}
 ${!S.advanced?quickExamMarkup(d):''}
 <details class="advanced-exam" ${S.advanced?'open':''}><summary>${S.advanced?'Configuración detallada de la prueba':'Más opciones: dificultad, modelos, problemas y rúbricas'}</summary>
 <section class="panel"><h2>Generar nuevo examen con IA</h2>${S.modules.length?`<form id="generate-exam">
 <div class="formgrid"><div class="field"><label>Módulo</label><select id="exam-module" name="module_id">${opt(S.modules,S.examModuleId,m=>m.name+' · '+m.academic_year)}</select></div>
 <div class="field"><label>Título</label><input required name="title" placeholder="Prueba de la unidad 2"></div>
 <div class="field"><label>Tipo</label><select name="kind"><option value="desarrollo">Desarrollo</option><option value="test">Tipo test</option><option value="mixto">Mixto</option><option value="problemas">Solo problemas prácticos</option></select></div>
 <div class="field"><label>Programación de referencia</label><select name="programming_id">${opt(d?.programmings||[],d?.programmings?.[0]?.id,p=>p.filename)}</select></div>
 <div class="field"><label>Dificultad</label><select name="difficulty"><option value="bajo">Baja · conceptos y aplicación directa</option><option value="medio" selected>Media · aplicación habitual</option><option value="alto">Alta · análisis y casos complejos</option></select></div>
 <div class="field"><label>Modelos distintos</label><input type="number" name="model_count" min="1" max="6" value="1" required></div>
 <div class="field"><label>Preguntas</label><input type="number" name="question_count" min="1" max="30" value="5" required></div>
 <div class="field"><label>Número de problemas prácticos</label><input type="number" name="problem_count" min="0" max="30" value="0" required><small>Si selecciona «Solo problemas prácticos», serán todas las preguntas. En otros tipos, sustituye ese número de preguntas por problemas.</small></div>
 <div class="field"><label>Centro educativo</label><input name="center_name" maxlength="140" placeholder="Nombre del centro"></div>
 <div class="field"><label>Fecha del examen</label><input type="date" name="exam_date"></div>
 <div class="field"><label>Duración (minutos)</label><input name="duration_minutes" type="number" min="10" max="480" value="60"></div>
 <div class="field"><label>Puntos totales</label><input type="number" name="total_points" min="1" max="100" step=".01" value="10" required></div></div>
 <div class="hint"><strong>Descarga:</strong> tras generar los modelos podrá descargar cada PDF con su encabezado y el ZIP de todos los modelos. Los problemas llevan datos, apartados, solución desarrollada y espacio de operaciones. <strong>Las respuestas y rúbricas solo figuran en el PDF del docente.</strong></div>
 <div class="hint"><strong>Banco ampliado:</strong> se solicitará a la IA un mínimo del triple de preguntas de cada modelo, manteniendo las ponderaciones de cada CE. Los modelos A, B, C… recibirán preguntas diferentes y no repetirán enunciados. Se conservará el banco completo en SQLite. <strong>Cuantos más modelos y preguntas, mayor uso de la API.</strong></div>
 <div class="field"><label>Instrucciones adicionales (opcional)</label><textarea name="instructions" placeholder="Nivel de dificultad, contenidos específicos, calculadora permitida..."></textarea></div>
 <div class="hint">${(d?.materials||[]).some(x=>x.active)?'<strong>Generación obligatoriamente fundamentada:</strong> hay materiales didácticos activos. Cada pregunta incluirá una cita literal verificada y el documento/página o bloque de origen. Antes de contactar con la IA se solicitará autorización para enviar fragmentos al proveedor.':'No hay material didáctico activo. La IA formulará las preguntas a partir de los CE seleccionados.'}</div>
 <div class="section-title">Resultados de aprendizaje / criterios seleccionados</div>
 ${d&&d.criteria.length?d.outcomes.map(r=>`<div><label class="checkbox-card"><input type="checkbox" data-ra="${r.id}" class="ra-checkbox"><span><strong>${E(r.code)} · ${E(r.description)}</strong><span class="small">Peso del RA: ${V(r.weight)} · seleccionar todos sus criterios</span></span></label>
 ${d.criteria.filter(c=>c.outcome_id===r.id).map(c=>`<label class="checkbox-card" style="margin-left:16px"><input type="checkbox" name="criteria_ids" value="${c.id}" data-parent="${r.id}"><span><strong>${E(c.code)} · ${E(c.description)}</strong><span class="small">Peso del CE: ${V(c.weight)} · RA: ${V(c.outcome_weight)}</span></span></label>`).join('')}</div>`).join(''):empty('Este módulo no tiene criterios. Complete antes la programación.')}
 <div class="actions"><button type="submit" class="btn" ${!d?.criteria?.length?'disabled':''}>Generar examen y rúbrica</button></div></form>`:empty('Cree un módulo en Programaciones.')}</section>
 </details>
 <section class="panel"><details><summary><strong>Crear un examen manual y clasificar sus preguntas por RA/CE</strong></summary>
 <p class="small">Introduzca sus propias preguntas (test, desarrollo o problemas). Puede asignar sus CE manualmente o pedir a la IA que proponga, a partir del currículo validado, los RA/CE que realmente evalúa cada pregunta. Se admite más de un CE por pregunta; la suma de porcentajes de una pregunta debe ser 100 %. Revise las propuestas antes de guardar.</p>
 <form id="manual-exam"><div class="formgrid"><div class="field"><label>Módulo</label><select name="module_id">${opt(S.modules,S.examModuleId,x=>x.name)}</select></div>
 <div class="field"><label>Título</label><input name="title" required value="${E(S.manualDraft?.title||'')}" placeholder="Examen redactado por el docente"></div>
 <div class="field"><label>Centro educativo</label><input name="center_name" placeholder="Nombre del centro"></div>
 <div class="field"><label>Duración (minutos)</label><input name="duration_minutes" type="number" min="10" max="480" value="60"></div></div>
 <div class="field"><label>Preguntas, puntuaciones y rúbricas (lista JSON)</label><textarea name="questions_json" rows="10" required>${E(S.manualDraft?.questions_json||JSON.stringify(d?.criteria?.length?[{
   kind:'desarrollo',prompt:'Desarrolle la respuesta a la cuestión propuesta.',points:10,
   ideal_answer:'Describa aquí la respuesta modelo antes de utilizar el examen.',rubric:[{criterion:'Exactitud de los contenidos',weight_pct:100}]
 }]:[],null,2))}</textarea></div>
 <div class="actions"><button class="btn secondary" type="button" data-action="manual-align">Analizar preguntas y proponer RA/CE con IA</button>
 <button class="btn" type="submit" ${!d?.criteria?.length?'disabled':''}>Guardar examen manual</button></div>
 <div class="hint" id="manual-curriculum-result">La IA únicamente propone vínculos a criterios ya existentes en el módulo. Si falta el currículo, impórtelo desde la programación o la normativa oficial antes de analizar. La clasificación no genera ni califica respuestas.</div>
 <label class="checkbox-card"><input type="checkbox" id="manual-confirm" required><span>He revisado los RA, CE, porcentajes y justificaciones asignados a todas las preguntas. Confirmo esta distribución como docente.</span></label>
 </form></details></section>
 <section class="panel"><div class="subhead"><h2>Exámenes disponibles</h2><span class="badge">${S.exams.length} exámenes</span></div>
 ${S.exams.length?`<div class="itemlist">${S.exams.map(e=>`<div class="item"><div><div class="title">${E(e.title)}</div><div class="detail">${E(e.module_name)} · ${e.question_count} preguntas · ${e.total_points} puntos · ${E(e.difficulty)} · modelo ${E(e.variant_label)} · ${e.submissions_count} entregas${e.bank_size?` · Banco ${e.bank_size} preguntas`:''}</div></div>
 <div class="right">${e.batch_id?`<button class="btn mutedbtn smallbtn" data-action="view-bank" data-id="${e.batch_id}">Banco</button>`:''}<button class="btn secondary smallbtn" data-action="open-exam" data-id="${e.id}">Ver preguntas</button><a class="btn mutedbtn smallbtn" href="/api/exams/${e.id}/pdf">PDF modelo ${E(e.variant_label)}</a>${e.batch_id?`<a class="btn mutedbtn smallbtn" href="/api/exam-batches/${e.batch_id}/pdf.zip">ZIP modelos</a><a class="btn mutedbtn smallbtn" href="/api/exam-batches/${e.batch_id}/soluciones.zip">ZIP solucionarios (docente)</a>`:''}</div></div>`).join('')}</div>`:empty('Todavía no hay exámenes.')}</section>
 ${selected?renderExam(selected):''}`;
}
function renderExam(e){return `<section class="panel"><div class="subhead"><h2>Examen: ${E(e.exam.title)} <span class="badge">${E(e.exam.difficulty)} · Modelo ${E(e.exam.variant_label)}</span></h2><div class="right"><a class="btn secondary" href="/api/exams/${e.exam.id}/pdf">Descargar PDF alumnado</a><a class="btn mutedbtn" href="/api/exams/${e.exam.id}/soluciones.pdf">PDF soluciones y rúbrica</a></div></div>
 ${e.questions.map(q=>`<div class="answer"><h3>${q.kind==='problema'?'Problema práctico':'Pregunta'} ${q.number} · ${E(q.criterion_code)} · ${q.points} puntos</h3><p>${E(q.prompt)}</p>
 ${q.kind==='test'?`<p class="small">${q.options.map(E).join('<br>')}</p><div class="badge green">Respuesta: ${E(q.correct_option)}</div>`:`<p class="small"><strong>Respuesta modelo:</strong> ${E(q.ideal_answer)}</p>`}
 ${(q.source_refs||[]).map(s=>`<div class="hint"><strong>Fuente documental verificada:</strong> ${E(s.filename)} · ${E(s.location_kind)} ${E(s.location_number)}<p class="small">Pasaje utilizado: «${E(s.evidence)}»</p><a class="btn smallbtn mutedbtn" href="/api/materials/${s.material_id}/original">Consultar documento original</a></div>`).join('')}
 <div class="section-title">Rúbrica</div>${q.rubric.map(r=>`<p class="rubric-item">${E(r.criterion)} · ${r.weight_pct}% de la pregunta</p>`).join('')}</div>`).join('')}</section>`;}
async function viewUploads(){
 await Promise.all([listExams(),listSubs()]);
 if(!S.uploadExamId&&S.exams.length)S.uploadExamId=S.exams[0].id;
 const exam=S.exams.find(e=>e.id===Number(S.uploadExamId));
 const d=exam?await API('/api/modules/'+exam.module_id):null;
 $('#main').innerHTML=`${intro('Seleccione un examen y un alumno. Las páginas se conservarán en el mismo orden de selección. Cada PDF aporta sus páginas interiores de forma consecutiva; puede alternar fotografías y PDF.')}
 <section class="panel"><h2>Importar un examen manuscrito multipágina</h2>
 ${S.exams.length?`<form id="upload-submission"><div class="formgrid"><div class="field"><label>Examen</label><select id="upload-exam" name="exam_id">${opt(S.exams,S.uploadExamId,x=>x.title+' · '+x.module_name)}</select></div>
 <div class="field"><label>Alumno/a</label><div class="student-select-controls"><select name="student_id" required>${opt(d?.students||[],S.uploadStudentId||'',x=>x.name+' ('+x.code+')')}</select>
 <button type="button" class="btn secondary smallbtn" data-action="create-upload-student" data-module-id="${exam.module_id}">+ Crear alumno</button></div>
 ${!d?.students?.length?'<small class="small">No hay alumnos registrados. Pulse «Crear alumno» para continuar.</small>':''}</div></div>
 <div class="grid2" style="margin-top:14px"><div class="field"><label>Seleccionar varios archivos (PDF, JPEG, PNG, WEBP, BMP)</label>
 <input type="file" id="upload-pages" multiple accept=".pdf,.jpg,.jpeg,.png,.webp,.bmp,image/*,application/pdf"></div>
 <div class="field"><label>Añadir fotografía desde móvil</label><input type="file" id="upload-camera" capture="environment" accept="image/*"></div></div>
 <div class="hint">Los PDF se descomponen en páginas numeradas y las fotografías se almacenan en su secuencia. No se modifica el archivo original. Use los controles para corregir el orden antes de enviar.</div>
 <div class="section-title">Cola de archivos en orden de lectura · ${S.queue.length} elemento(s)</div>
 ${S.queue.length?`<ol class="filequeue">${S.queue.map((f,i)=>`<li><span class="filename">${E(f.name)} <span class="small">(${Math.ceil(f.size/1024)} KB)</span></span><div class="actions" style="margin:0"><button type="button" class="btn smallbtn mutedbtn" data-action="queue-up" data-index="${i}" ${!i?'disabled':''}>↑</button><button type="button" class="btn smallbtn mutedbtn" data-action="queue-down" data-index="${i}" ${i===S.queue.length-1?'disabled':''}>↓</button><button type="button" class="btn smallbtn danger" data-action="queue-remove" data-index="${i}">×</button></div></li>`).join('')}</ol>`:empty('No se han seleccionado archivos.')}
 <div class="actions"><button type="submit" class="btn" ${!S.queue.length||!d?.students?.length?'disabled':''}>Guardar entrega y originales</button></div></form>`:empty('Genere primero un examen.')}</section>
 <section class="panel"><h2>Importación masiva de distintos alumnos mediante ZIP</h2><p class="small">Cree un ZIP con una carpeta por código de alumno, por ejemplo ALU001/001.jpg, ALU001/002.jpg, ALU002/001.pdf. Los archivos de cada carpeta se ordenan por nombre numérico. Si falta algún alumno, la aplicación mostrará un formulario para registrarlo antes de importar el ZIP. Los códigos deben coincidir exactamente.</p>
 <form id="upload-batch"><div class="formrow"><div class="field grow"><label>Examen</label><select name="exam_id">${opt(S.exams,S.uploadExamId,x=>x.title)}</select></div><div class="field grow"><label>ZIP de varios alumnos</label><input name="archive" type="file" accept=".zip" required></div><button class="btn secondary" type="submit" ${!S.exams.length?'disabled':''}>Importar lote</button></div></form></section>
 <section class="panel"><h2>Entregas archivadas</h2>${S.submissions.length?`<div class="itemlist">${S.submissions.map(s=>`<div class="item"><div><div class="title">${E(s.student_name)} · ${E(s.student_code)}</div><div class="detail">${E(s.exam_title)} · ${s.page_count} páginas · ${E(s.created_at)}</div></div><div class="right">${labelStatus(s.status)}<button class="btn smallbtn secondary" data-action="open-sub" data-id="${s.id}">Ver original</button></div></div>`).join('')}</div>`:empty('Todavía no hay entregas.')}</section>`;
}
async function viewCorrections(){
 await listSubs();
 S.gradebook=await API('/api/gradebook');
 if(S.subId&&!S.submissions.some(x=>x.id===Number(S.subId)))S.subId=null;
 if(!S.subId&&S.submissions.length)S.subId=S.submissions[0].id;
 S.subDetails=S.subId?await API('/api/submissions/'+S.subId):null;
 $('#main').innerHTML=`${intro('El visor enlaza cada pregunta con sus páginas originales y la transcripción. La nota de la IA es provisional: puede corregir la lectura manuscrita, modificar la calificación y documentar la validación.')}
 ${S.submissions.length?`<section class="panel"><div class="formrow"><div class="field grow"><label>Entrega a revisar</label><select id="review-select">${opt(S.submissions,S.subId,x=>x.student_name+' — '+x.exam_title+' ('+x.status+')')}</select></div>
 ${S.subDetails?labelStatus(S.subDetails.submission.status):''}</div></section>`:empty('No hay entregas. Suba un examen en la sección Entregas escaneadas.')}
 ${S.subDetails?renderReview(S.subDetails):''}
 ${renderGradebook(S.gradebook)}`;
}
function renderGradebook(book){
 const rows=book?.exams||[];
 return `<section class="panel"><div class="subhead"><h2>Registro consolidado de evaluaciones</h2><button class="btn secondary" data-action="export-gradebook">Exportar CSV</button></div>
 <p class="small">Se muestran notas finales únicamente cuando todas las preguntas del examen están validadas. El desglose por CE reúne las preguntas de exámenes validados, sin sustituir el cálculo de la evaluación global definido por la programación didáctica.</p>
 ${rows.length?`<div class="table-wrap"><table><thead><tr><th>Curso</th><th>Módulo</th><th>Alumno/a</th><th>Examen</th><th>Validación</th><th>Nota / 10</th></tr></thead>
 <tbody>${rows.map(r=>`<tr><td>${E(r.academic_year)}</td><td>${E(r.module_name)}</td><td>${E(r.student_name)} <span class="small">${E(r.student_code)}</span></td><td>${E(r.exam_title)}</td><td>${labelStatus(r.status)}<div class="small">${r.validated_questions}/${r.question_count} preguntas</div></td><td><strong>${r.out_of_ten??'Pendiente'}</strong></td></tr>`).join('')}</tbody></table></div>`:empty('No hay evaluaciones registradas.')}
 ${(book?.criteria||[]).length?`<details style="margin-top:17px"><summary>Ver desglose de puntos por RA y CE (${book.criteria.length} registros)</summary><div class="table-wrap"><table><thead><tr><th>Alumno/a</th><th>Módulo</th><th>RA</th><th>CE</th><th>Puntos</th><th>Preguntas evaluadas</th></tr></thead><tbody>
 ${book.criteria.map(r=>`<tr><td>${E(r.student_name)}</td><td>${E(r.module_name)}</td><td>${E(r.outcome_code)}</td><td>${E(r.criterion_code)}</td><td>${r.scored} / ${r.maximum}</td><td>${r.evaluated_questions}</td></tr>`).join('')}</tbody></table></div></details>`:''}</section>`;
}

function renderReview(item){
 const {submission:s,pages,corrections,unassigned,sources}=item;
 const cur=pages[S.pageIndex]||pages[0];
 return `<div class="viewer-layout"><section class="panel viewer-panel"><div class="subhead"><h2>Original escaneado</h2><span class="badge">${pages.length} páginas</span></div>
 <p class="small">${E(s.student_name)} · ${E(s.exam_title)}</p>
 ${cur?`<div class="pagepreview"><img id="large-page" src="/api/pages/${cur.id}/image" alt="Página ${cur.page_number} del examen" title="Pulse para ampliar"></div>
 <div class="thumbnails">${pages.map((p,i)=>`<button type="button" class="thumb ${i===S.pageIndex?'selected':''}" data-action="select-page" data-index="${i}"><img src="/api/pages/${p.id}/image" loading="lazy" alt="Miniatura ${p.page_number}"><small>p. ${p.page_number}</small></button>`).join('')}</div>`:empty('No se han registrado páginas.')}
 <h3>Archivos originales conservados</h3><div class="itemlist">${sources.map(f=>`<div class="item"><div><b>${E(f.original_name)}</b><div class="small">${f.page_count} página(s) · SHA-256: ${E(f.sha256.slice(0,15))}…</div></div><a class="btn smallbtn secondary" href="/api/source/${f.id}">Original</a></div>`).join('')}</div>
 <div class="actions"><a class="btn secondary" target="_blank" href="/print/report/${s.id}">Informe imprimible</a><button type="button" class="btn mutedbtn" data-action="show-audit" data-id="${s.id}">Auditoría</button></div><div id="audit-info"></div></section>
 <section class="panel"><div class="subhead"><h2>Corrección por preguntas</h2>${labelStatus(s.status)}</div>
 <div class="hint">La transcripción se hace página a página teniendo a la vista la anterior. Una respuesta que continúa en la siguiente hoja debe mantener el mismo número de pregunta; cualquier texto sin asignación se mostrará abajo.</div>
 <div class="actions"><button class="btn" data-action="transcribe" data-id="${s.id}">${s.current_run_id?'Volver a transcribir con IA':'Transcribir manuscritos con IA'}</button>
 <button class="btn secondary" data-action="grade" data-id="${s.id}" ${!s.current_run_id?'disabled':''}>Corregir con IA y rúbricas</button></div>
 <p class="small">La transcripción y corrección requieren conexión con la API seleccionada. Repetir un análisis puede generar costes adicionales y reiniciar la revisión del examen.</p>
 ${corrections.map(r=>`<article class="answer"><h3>Pregunta ${r.number} · ${E(r.outcome_code)} / ${E(r.criterion_code)}</h3>
 <p>${E(r.prompt)}</p><div class="two-score"><span>Máximo: <strong>${r.points} puntos</strong></span>
 <span>IA: <strong>${r.ai_score===null?'Sin corregir':r.ai_score}</strong></span><span>Docente: <strong>${r.teacher_score===null?'Pendiente':r.teacher_score}</strong></span>
 ${r.needs_review?'<span class="badge orange">Revisión recomendada</span>':''}</div>
 <p class="small">Páginas asignadas: ${r.page_numbers.length?r.page_numbers.map(n=>`<button class="btn smallbtn mutedbtn" data-action="select-page" data-index="${n-1}">${n}</button>`).join(' '):'No identificadas'}</p>
 <form class="edit-transcription" data-cid="${r.id}"><div class="field"><label>Transcripción (editable)</label><textarea name="transcription" rows="4">${E(r.transcription)}</textarea></div>
 <div class="actions"><button type="submit" class="btn mutedbtn smallbtn">Guardar transcripción corregida</button></div></form>
 ${(r.source_refs||[]).length?`<div class="small">Fuente del enunciado: ${r.source_refs.map(s=>`${E(s.filename)} · ${E(s.location_kind)} ${E(s.location_number)}`).join(' · ')}</div>`:''}
 ${r.ai_feedback?`<p><strong>Justificación de IA:</strong> ${E(r.ai_feedback)}</p>`:''}
 ${r.rubric_result.length?`<div class="section-title">Aplicación de rúbrica</div>${r.rubric_result.map(a=>`<div class="rubric-item"><strong>${E(a.criterion||'Indicador')}: ${E(a.points)} / ${E(a.max_points)}</strong><p>${E(a.justification||'')}</p>${a.evidence?`<span class="small">Evidencia: «${E(a.evidence)}»</span>`:''}${a.evidence_warning?`<p class="small">⚠ ${E(a.evidence_warning)}</p>`:''}</div>`).join('')}`:''}
 <form class="validate" data-cid="${r.id}"><div class="formrow"><div class="field"><label>Nota validada (máx. ${r.points})</label><input class="score-input" type="number" name="score" min="0" max="${r.points}" step=".01" required value="${r.teacher_score??r.ai_score??''}"></div>
 <div class="field grow"><label>Justificación o comentario docente</label><input name="comment" value="${E(r.teacher_comment)}" placeholder="Obligatoria si modifica la nota de IA"></div><button type="submit" class="btn secondary">Validar nota</button></div></form>
 ${r.status==='validated'?'<p class="badge green">✓ Pregunta validada</p>':''}</article>`).join('')||empty('Primero transcriba las páginas con IA para identificar las respuestas.')}
 ${unassigned.length?`<div class="hint warning"><b>Fragmentos sin asignar — revisión obligatoria</b>${unassigned.map(u=>`<p>Pág. ${u.page_number}: ${E(u.text)}</p>`).join('')}</div>`:''}
 <div class="actions"><a class="btn" href="/print/report/${s.id}" target="_blank">Generar informe justificativo</a></div></section></div>`;
}
async function viewEvaluation(){
 const [modules]=await Promise.all([listModules(),listExams()]);
 if(!modules.length){$('#main').innerHTML=empty('Primero cree un módulo desde Programaciones.');return;}
 S.evaluationModuleId=modules.some(m=>Number(m.id)===Number(S.evaluationModuleId))?Number(S.evaluationModuleId):Number(S.moduleId||modules[0].id);
 const scope=await API('/api/common-scopes/draft?module_id='+S.evaluationModuleId);
 if(scope.profile){
   $('#main').innerHTML=`<section class="panel"><div class="field"><label>Selecciona módulo o materia</label><select id="evaluation-module">${opt(modules,S.evaluationModuleId,m=>m.name+' · '+m.academic_year)}</select></div><h2>Evaluación competencial del ámbito</h2><p>Esta materia utiliza competencias específicas, no el cuaderno de RA y CE profesionales.</p><button type="button" class="btn" data-action="eval-scope-notebook">Abrir cuaderno competencial</button></section>`;return;
 }
 const x=await API('/api/evaluation?module_id='+encodeURIComponent(S.evaluationModuleId));S.evalData=x;
 const students=x.students||[],criteria=x.criteria||[],units=x.units||[],instruments=x.instruments||[],policy=x.settings;
 const feoeEvidence=(await API('/api/feoe/module-evidence?module_id='+Number(S.evaluationModuleId))).evidence;
 const cefmt=c=>`${c.ra_code} · ${c.code} — ${c.description.slice(0,80)}`;
 const rowsCE=criteria.map(c=>`<label class="checkbox-card"><input type="checkbox" name="criteria_ids" value="${c.id}"><span><strong>${E(c.ra_code)} · ${E(c.code)}</strong><span class="small">${E(c.description)}</span></span></label>`).join('');
 const options=criteria.map(c=>`<div class="eval-target"><label><input type="checkbox" name="target_${c.id}"> ${E(c.ra_code)} / ${E(c.code)}</label><label>Peso instrumento en este CE (%) <input type="number" name="weight_${c.id}" min=".01" max="100" step=".01" value="100"></label></div>`).join('');
 const examChoices=(S.exams||[]).filter(e=>Number(e.module_id)===Number(S.evaluationModuleId));
 $('#main').innerHTML=`${intro('Cuaderno de evaluación por unidades, trimestres, RA y CE. Integra correcciones validadas de exámenes, calificaciones manuales y notas importadas desde CSV. Ninguna nota final se publica si las ponderaciones o evidencias son incompletas.')}
 <section class="panel"><div class="formrow"><div class="field grow"><label>Módulo profesional</label><select id="evaluation-module">${opt(modules,S.evaluationModuleId,m=>m.name+' · '+m.academic_year)}</select></div><span class="badge">${students.length} alumnos · ${units.length} unidades · ${instruments.length} instrumentos</span></div></section>
 ${x.warnings.length?`<section class="hint warning"><strong>Incidencias que impiden calcular una calificación definitiva</strong><ul>${x.warnings.map(w=>`<li>${E(w)}</li>`).join('')}</ul></section>`:''}
 <details class="eval-section" ${S.advanced||feoeEvidence.length?'open':''}><summary>Formación en empresa <small>${feoeEvidence.length} evidencias</small></summary><section class="panel"><h2>Evidencias cualitativas FEOE del módulo</h2><p>Consulta las valoraciones del tutor de empresa y las revisiones del profesorado. No se convierten automáticamente en notas.</p><button type="button" class="btn secondary" data-page="feoe">Abrir seguimiento FEOE</button>
 ${feoeEvidence.length?`<div class="table-wrap"><table><thead><tr><th>Alumno</th><th>RA / CE</th><th>Empresa</th><th>Valoración</th><th>Revisión docente</th></tr></thead><tbody>${feoeEvidence.map(r=>`<tr><td>${E(r.student_name)}</td><td>${E(r.ra_code)} · ${E(r.criterion_codes.join(', '))}${r.current_curriculum?'':' · Currículo modificado'}</td><td>${E(r.company_name)}</td><td>${E(r.valuation?.status||'Pendiente')} · ${E(r.valuation?.observations||'')}</td><td>${E(r.teacher_review?.notes||'Pendiente de revisión')}</td></tr>`).join('')}</tbody></table></div>`:empty('Sin evidencias de empresa vinculadas a planes confirmados.')}</section></details>
 <details class="eval-section" ${S.advanced||!policy.validated?'open':''}><summary>1. Configurar criterios de calificación <small>${policy.validated?'Política validada':'Pendiente de validar'}</small></summary><section class="panel"><h2>Criterios de calificación y tratamiento de la formación en empresa</h2>
 <p class="small">Comprueba la programación de este módulo y valida una política coherente. La aplicación no modifica automáticamente los pesos originales.</p>
 <form id="eval-policy"><div class="formgrid"><div class="field"><label>Tratamiento de empresa</label><select name="enterprise_mode">
 <option value="unresolved" ${policy.enterprise_mode==='unresolved'?'selected':''}>Pendiente de aclarar</option>
 <option value="integrated" ${policy.enterprise_mode==='integrated'?'selected':''}>Evidencias de empresa integradas en RA</option>
 <option value="separate" ${policy.enterprise_mode==='separate'?'selected':''}>Empresa con porcentaje final independiente</option></select></div>
 <div class="field"><label>Peso FE independiente (%)</label><input name="enterprise_weight" type="number" min="0" max="100" step=".01" value="${E(policy.enterprise_weight)}"></div>
 <div class="field"><label>Nota mínima CE superado</label><input name="criterion_pass_mark" type="number" min="0" max="10" step=".1" value="${E(policy.criterion_pass_mark)}"></div>
 <div class="field"><label>% mínimo de CE superados para RA</label><input name="ra_min_criteria_pct" type="number" min="0" max="100" step="1" value="${E(policy.ra_min_criteria_pct)}"></div></div>
 <div class="field"><label>Justificación de la interpretación adoptada</label><textarea name="teacher_note" placeholder="Acuerdo o modificación de programación revisada por el equipo docente">${E(policy.teacher_note)}</textarea></div>
 <label><input name="validated" type="checkbox" ${policy.validated?'checked':''}> Confirmo, como docente, esta política de cálculo</label>
 <div class="actions"><button class="btn" type="submit">Guardar política</button></div></form></section></details>
 <details class="eval-section" ${S.advanced||!instruments.length?'open':''}><summary>2. Preparar unidades e instrumentos <small>${units.length} unidades · ${instruments.length} instrumentos</small></summary><div class="grid2"><section class="panel"><h2>Unidades de evaluación</h2>
 <form id="eval-unit"><div class="formgrid"><div class="field"><label>Código</label><input name="code" required placeholder="UD01"></div>
 <div class="field"><label>Unidad / situación de aprendizaje</label><input name="title" required placeholder="Diario y mayor"></div>
 <div class="field"><label>Trimestre</label><select name="term"><option value="1">1.ª evaluación</option><option value="2">2.ª evaluación</option><option value="3">3.ª evaluación</option></select></div></div>
 <div class="section-title">CE trabajados (pueden estar en varias unidades)</div><div class="eval-scroll">${rowsCE||empty('Primero añada RA y CE.')}</div>
 <button class="btn secondary" type="submit">Crear unidad</button></form>
 ${units.length?`<div class="itemlist" style="margin-top:12px">${units.map(u=>`<div class="item"><b>${E(u.code)} · ${E(u.title)}</b><span class="badge">${u.term}.ª eval. · ${u.criteria_ids.length} CE</span></div>`).join('')}</div>`:''}</section>
 <section class="panel"><h2>3. Instrumentos de calificación</h2>
 <form id="eval-instrument"><div class="formgrid"><div class="field"><label>Nombre del instrumento</label><input required name="title" placeholder="Práctica de asientos"></div>
 <div class="field"><label>Tipo</label><select name="kind">${['examen','practica','problemas','portfolio','proyecto','observacion','empresa','externo'].map(k=>`<option value="${k}">${E(k)}</option>`).join('')}</select></div>
 <div class="field"><label>Evaluación</label><select name="term"><option value="1">1.ª</option><option value="2">2.ª</option><option value="3">3.ª</option></select></div>
 <div class="field"><label>Unidad (opcional)</label><select name="unit_id"><option value="">Sin vincular</option>${opt(units,'',u=>u.code+' · '+u.title)}</select></div>
 <div class="field"><label>Examen generado (si existe)</label><select name="exam_id"><option value="">Sin vincular</option>${opt(examChoices,'',e=>e.title+' · '+e.variant_label)}</select></div></div>
 <div class="section-title">CE evaluados y peso de este instrumento dentro de cada CE</div>
 <div class="eval-scroll">${options||empty('Primero configure los criterios.')}</div>
 <p class="small">Los porcentajes de todos los instrumentos de un mismo CE deben sumar 100 %. P. ej., prueba escrita 60 %, portfolio 40 %.</p>
 <button class="btn secondary" type="submit">Crear instrumento</button></form></section></div></details>
 <section class="panel"><h2>3. Registrar notas</h2>
 ${instruments.length?`<div class="field" style="max-width:600px"><label>Instrumento a calificar</label><select id="eval-instrument-select">${opt(instruments,S.evalInstrumentId||instruments[0].id,i=>i.term+'ª · '+i.title+' ('+i.kind+')')}</select></div>`:empty('Cree un instrumento para introducir calificaciones.')}
 <div id="eval-scores"></div></section>
 <section class="panel"><h2>4. Revisar y validar resultados</h2>
 <p class="small">Las notas trimestrales son instantáneas provisionales de los instrumentos de cada período; las notas finales requieren evidencias completas, pesos correctos y validación de la política.</p>
 <div class="table-wrap"><table><thead><tr><th>Alumno/a</th><th>1.ª</th><th>2.ª</th><th>3.ª</th><th>RA</th><th>Nota final calculable</th></tr></thead><tbody>${students.map(st=>`<tr><td><b>${E(st.name)}</b><div class="small">${E(st.code)}</div></td>
 ${st.terms.map(t=>`<td>${t.score??'—'} <small>${t.completed}/${t.expected}</small></td>`).join('')}
 <td>${st.outcomes.map(ra=>`<div class="small">${E(ra.code)}: ${ra.score??'—'} ${ra.passed?'✓':''}</div>`).join('')}</td>
 <td>${st.closure?.current?`<span class="badge green">Validada: ${st.closure.score}/10</span>`:
 st.closure?'<span class="badge orange">Cierre desactualizado</span>':
 st.final_score===null?'<span class="badge orange">Pendiente</span>':`<strong>${st.final_score} / 10</strong><div class="small">Antes del cierre docente</div>`}
 <div class="actions"><a class="btn smallbtn secondary" href="/api/evaluation/${S.evaluationModuleId}/student/${st.student_id}.pdf">Informe PDF</a>
 ${st.final_score!==null?`<button type="button" class="btn smallbtn" data-action="eval-close" data-id="${st.student_id}">Validar cierre</button>`:''}</div></td></tr>`).join('')}</tbody></table></div>
 <details class="eval-section" ${S.advanced?'open':''}><summary>Exportar informes y conectar con Additio</summary><div class="actions" style="flex-wrap:wrap"><button class="btn secondary" data-action="export-evaluation" type="button">Resultados CSV</button>
 <a class="btn secondary" href="/api/evaluation/${S.evaluationModuleId}/export/xlsx">Excel completo (.xlsx)</a>
 <a class="btn secondary" href="/api/evaluation/${S.evaluationModuleId}/export/xls">Excel clásico (.xls)</a>
 <a class="btn secondary" href="/api/evaluation/${S.evaluationModuleId}/export/additio-alumnos.xlsx">Additio: importar grupo Excel</a>
 <a class="btn secondary" href="/api/evaluation/${S.evaluationModuleId}/export/additio-alumnos.csv">Grupo CSV</a>
 <a class="btn" href="/api/evaluation/${S.evaluationModuleId}/export/additio-configuracion.zip">Additio: configurar RA y CE (ZIP)</a>
 <a class="btn secondary" href="/api/evaluation/${S.evaluationModuleId}/export/additio-ra.xlsx">RA: hoja de configuración</a>
 <a class="btn secondary" href="/api/evaluation/${S.evaluationModuleId}/export/additio-ce.xlsx">CE: importar desde Excel</a>
 <a class="btn secondary" href="/api/evaluation/${S.evaluationModuleId}/export/additio-ce-detalle.xlsx">RA/CE: ponderaciones y relaciones</a>
 <a class="btn secondary" href="/api/evaluation/${S.evaluationModuleId}/export/additio-notas.xlsx">Additio: notas RA/CE Excel</a>
 <a class="btn secondary" href="/api/evaluation/${S.evaluationModuleId}/export/additio-notas.csv">Additio: notas RA/CE CSV</a>
 <a class="btn secondary" href="/api/evaluation/${S.evaluationModuleId}/export/additio-seguimiento.csv">RA/CE seguimiento provisional CSV</a>
 <a class="btn secondary" href="/api/evaluation/${S.evaluationModuleId}/export/additio-estado.csv">Estado de validación (separado)</a>
 <a class="btn secondary" href="/api/evaluation/${S.evaluationModuleId}/export/additio-pegar.tsv">Additio: copiar/pegar TSV</a></div>
 <p class="small">Para Additio se exportan exclusivamente las calificaciones curriculares RA/CE, sin columnas de exámenes, portfolios ni instrumentos. El paquete de configuración contiene el listado de RA (alta revisada por docente), los CE en el formato de una columna y una tabla de ponderaciones. Las notas definitivas solo se exportan con cierre docente vigente; el archivo de seguimiento provisional está identificado por separado. Compruebe el orden de alumnos y los códigos en Additio antes de trasladar las calificaciones.</p></details></section>`;
 S.evalInstrumentId=instruments.some(i=>Number(i.id)===Number(S.evalInstrumentId))?Number(S.evalInstrumentId):instruments[0]?.id||null;
 renderEvalScores();
}
function renderEvalScores(){
 const x=S.evalData, iid=Number(S.evalInstrumentId);if(!x)return;
 const instrument=x.instruments.find(i=>i.id===iid),area=$('#eval-scores');if(!area)return;
 if(!instrument){area.innerHTML=empty('Seleccione un instrumento.');return;}
 const ces=instrument.targets.map(t=>x.criteria.find(c=>c.id===t.criterion_id)).filter(Boolean);
 area.innerHTML=`<div class="actions"><button class="btn secondary" type="button" data-action="download-eval-template">Descargar plantilla CSV</button>
 ${instrument.exam_id?`<button class="btn secondary" type="button" data-action="sync-eval-exam" data-id="${instrument.id}">Importar notas validadas del examen</button>`:''}</div>
 <form id="eval-import" class="formrow" style="margin:15px 0"><input type="hidden" name="instrument_id" value="${iid}"><div class="field grow"><label>Importar notas CSV (codigo_alumno;criterio;nota;comentario). Indica RA/CE, por ejemplo RA1/a.</label><input type="file" name="csv" accept=".csv,text/csv" required></div><button type="submit" class="btn secondary">Importar CSV</button></form>
 <div class="table-wrap"><table><thead><tr><th>Alumno</th>${ces.map(c=>`<th>${E(c.ra_code)} · ${E(c.code)}</th>`).join('')}</tr></thead><tbody>
 ${x.students.map(st=>`<tr><td><strong>${E(st.name)}</strong><div class="small">${E(st.code)}</div></td>${ces.map(c=>{
 const rec=x.scores.find(r=>r.student_id===st.student_id&&r.instrument_id===iid&&r.criterion_id===c.id);
 return `<td><div class="formrow"><input class="eval-score-input" type="number" min="0" max="10" step=".01" data-student="${st.student_id}" data-criterion="${c.id}" value="${rec?E(rec.score):''}" placeholder="—"><button type="button" class="btn smallbtn secondary" data-action="eval-save-score" data-student="${st.student_id}" data-criterion="${c.id}" data-instrument="${iid}">Guardar</button></div><div class="small">${rec?E(rec.origin)+' · '+E(rec.comment||''):''}</div></td>`;}).join('')}</tr>`).join('')}</tbody></table></div>`;
}
async function viewSettings(){
 const a=await API('/api/settings');S.aiSettings=a;
 const backups=(await API('/api/backup/list')).archives;
 $('#main').innerHTML=`${intro('OpenAI o API compatible. Datos, SQLite y originales guardados localmente; en modo USB todas las rutas se guardan relativas al dispositivo.')}
 <section class="panel"><h2>Proveedor de IA</h2><form id="save-settings"><div class="formgrid">
 ${[['provider','Proveedor (etiqueta)'],['base_url','URL base de API'],['model_analysis','Modelo: análisis de programación'],['model_generation','Modelo: generación'],['model_vision','Modelo: visión manuscrita'],['model_correction','Modelo: corrección']].map(([key,label])=>`<div class="field"><label>${label}</label><input name="${key}" required value="${E(a[key])}"></div>`).join('')}</div>
 <div class="field" style="margin-top:12px;max-width:650px"><label>Nueva clave API (dejar en blanco para conservarla)</label><input type="password" name="api_key" autocomplete="new-password" placeholder="${a.api_key_saved?'Clave previamente guardada':'Introduzca su clave'}"></div>
 ${a.portable?`<div class="field" style="max-width:650px"><label>Contraseña maestra para cifrar una NUEVA clave API (mín. 12 caracteres)</label><input type="password" name="master_password" autocomplete="new-password" placeholder="No se conserva en el dispositivo"></div>`:''}
 <div class="actions"><button class="btn" type="submit">Guardar configuración</button><span class="badge ${a.api_key_unlocked?'green':'orange'}">${a.api_key_unlocked?'API desbloqueada':a.api_key_saved?'API cifrada: bloqueada':'Clave no configurada'}</span></div></form>
 ${a.portable?`<div class="hint">La clave se conserva cifrada con AES-256-GCM y una contraseña maestra mediante scrypt, no mediante hash. Introduzca la contraseña cada vez que inicie el programa en otro equipo. No se guarda ni en HTML ni en SQLite.</div>
 <form id="unlock-api" class="formrow"><div class="field grow"><label>Desbloquear clave guardada en este pendrive</label><input type="password" name="master_password" autocomplete="off" required></div><button class="btn secondary" type="submit">Desbloquear</button><button class="btn mutedbtn" type="button" data-action="lock-api">Bloquear</button></form>`:
 `<p class="hint">En una instalación fija, la clave se conserva en el gestor de credenciales de Windows (cuando esté disponible); no se copia automáticamente al USB.</p>`}</section>
 <div class="grid2"><section class="panel"><h2>Almacenamiento ${a.portable?'PORTÁTIL (USB)':'local'}</h2>
 <p><strong>Ejecutable / proyecto</strong></p><pre class="path">${E(a.app_dir)}</pre>
 <p><strong>SQLite</strong></p><pre class="path">${E(a.data_dir)}${E('/datos/evaluafp.sqlite3')}</pre>
 <p><strong>Originales</strong></p><pre class="path">${E(a.data_dir)}${E('/almacen')}</pre>
 <p><strong>Copias de seguridad</strong></p><pre class="path">${E(a.backup_dir)}</pre>
 <form id="change-storage"><div class="field"><label>Carpeta de datos (en USB, ruta relativa al EXE)</label><input required name="data_dir" value="${E(a.data_dir_edit)}"></div>
 <div class="field"><label>Carpeta de copias de seguridad</label><input required name="backup_dir" value="${E(a.backup_dir_edit)}"></div>
 <div class="actions"><button class="btn secondary" type="submit">Migrar datos y cambiar carpetas</button></div></form>
 <p class="small">El cambio copia documentos y SQLite, actualiza las rutas guardadas y exige reiniciar EvalúaFP. Los archivos antiguos se conservan como medida de seguridad.</p>
 <div class="actions"><a class="btn secondary" href="/api/backup">Crear copia ZIP en la carpeta elegida y descargarla</a></div>
 <p class="small">En modo USB, la copia incluye la clave API solo en su formato cifrado, nunca la contraseña maestra. Los expedientes del ZIP no están cifrados.</p>
 <details class="eval-section"><summary>Recuperar una copia de seguridad</summary><div class="panel"><p>Se creará una carpeta nueva junto a tu carpeta de datos. No se sustituirá ni se activará la base de datos en uso. Solo se admiten copias con manifiesto de integridad.</p>
 <button class="btn secondary" type="button" data-action="backup-list-refresh">Actualizar lista de copias</button>
 ${backups.length?`<form id="backup-recover"><div class="field"><label for="backup-choice">Copia local</label><select id="backup-choice" name="name" required>${backups.map(b=>`<option value="${E(b.name)}">${E(b.name)} · ${(b.size/1048576).toFixed(1)} MB</option>`).join('')}</select></div><label><input type="checkbox" name="confirmed" required> Confirmo que deseo recuperar los datos en una carpeta independiente.</label><div class="actions"><button class="btn" type="submit">Verificar y recuperar</button></div></form>`:empty('No hay copias ZIP locales en la carpeta configurada.')}<div id="backup-recovery-result" role="status"></div></div></details></section>
 <section class="panel"><h2>Seguridad de los datos del alumnado</h2>
 <p>El programa no requiere Internet para consultar las notas, exámenes o SQLite. Las solicitudes de IA sí transmitirán los textos o imágenes necesarios al proveedor elegido.</p>
 <div class="hint warning">Un pendrive convencional no protege la base SQLite ni los PDF ante robo o extravío. Utilice un dispositivo USB con cifrado de unidad (por ejemplo, BitLocker To Go) y realice copias en otra ubicación segura.</div>
 <p>Evite desconectar el pendrive mientras EvalúaFP esté abierto. Las notas propuestas por IA exigen siempre validación humana.</p></section></div>`;
}
function downloadText(value,name,mime){const url=URL.createObjectURL(new Blob([value],{type:mime}));
 const anchor=document.createElement('a');anchor.href=url;anchor.download=name;anchor.click();setTimeout(()=>URL.revokeObjectURL(url),2000);}
function formObject(form){return Object.fromEntries(new FormData(form).entries());}
async function doSubmit(form){
 const id=form.id;
 if(id==='backup-recover'){
   const dest=$('#backup-recovery-result');
   const result=await busy(()=>API('/api/backup/recover','POST',{name:form.elements.name.value,confirmed:form.elements.confirmed.checked}));
   if(result&&dest?.isConnected){dest.innerHTML=`<p><strong>Recuperación verificada.</strong> Los datos actuales permanecen intactos.</p><pre class="path">${E(result.path)}</pre><p>La carpeta recuperada no se ha activado. Cierra EvalúaFP y consulta el procedimiento de configuración del almacenamiento antes de usarla.</p>`;form.elements.confirmed.checked=false;}
   return;
 }
 if(id==='home-context'){
   const mid=Number(form.elements.module_id.value);
   if(!S.modules.some(m=>Number(m.id)===mid))throw Error('Seleccione un módulo disponible.');
   S.moduleId=mid;S.evaluationModuleId=mid;S.examModuleId=mid;S.evalInstrumentId=null;
   S.preparePath=null;S.wizardDraft=null;S.proposal=null;S.autoProposedModuleId=null;
   S.cycleRecordRoster=null;S.cycleRecordReport=null;S.feoeRoster=null;S.feoeStay=null;
   await page('inicio');return;
 }
 if(id==='prepare-create'){
   const result=await busy(()=>API('/api/modules','POST',formObject(form)),'Módulo creado.');
   if(result){S.moduleId=result.id;S.autoProposedModuleId=null;S.creatingModule=false;S.wizardDraft=null;S.preparePath=null;await page('preparar');}return;
 }
 if(id==='curriculum-review-form'){
   const formData=new FormData(form);
   const result=await busy(()=>API('/api/curriculum/review-preview','POST',formData),
     'Vista previa curricular creada. Revisa enunciados, procedencia y diferencias.');
   if(result){S.curriculumReview=result;S.curriculumSourceFile=form.querySelector('[name=document]')?.files?.[0]||null;S.curriculumSourceKind=formData.get('document_kind');await page('preparar');}
   return;
 }
 if(id==='guided-upload'){
   const result=await busy(()=>API('/api/programmings/upload','POST',new FormData(form)),'Documento original guardado.');
   if(result){
     if(!result.characters){toast('El documento no contiene texto extraíble. Conviértelo mediante OCR o utiliza Word.',true);await page('preparar');return;}
     const preview=await busy(()=>API('/api/programmings/'+result.id+'/import-preview'));
     if(preview){S.importPreview=preview;S.proposal=null;await page('preparar');}
     else {toast('Se guardó el original. Usa «Revisar TODA la programación» para reintentar.',true);await page('preparar');}
   }return;
 }
 if(id==='guided-content-import'){
   const proposal=S.importPreview;if(!proposal)return;
   const selected=[...form.querySelectorAll('[data-import-field]:checked')].map(el=>el.dataset.importField);
   const edited={};
   for(const key of selected){const input=form.querySelector('[data-import-edit="'+key+'"]');if(input)edited[key]=input.value;}
   const hoursAccepted=Boolean(form.querySelector('[name=accept_document_hours]:checked'));
   const unitsAccepted=Boolean(form.querySelector('[name=accept_units]:checked'));
   const feoeAccepted=Boolean(form.querySelector('[name=accept_feoe_criteria]:checked'));
   const hours=unitsAccepted?[...form.querySelectorAll('[data-import-unit-hours]')].map(el=>el.value):[];
   if(unitsAccepted&&hours.some(x=>!x||!Number.isFinite(Number(x))||Number(x)<=0)){
     toast('Para incorporar unidades, indica las horas de cada una. No se inventarán duraciones.',true);return;
   }
   if(!selected.length&&!hoursAccepted&&!unitsAccepted&&!feoeAccepted&&!form.querySelector('[name=keep_source_sections]:checked')){
     toast('Selecciona algún contenido que quieras incorporar.',true);return;
   }
   const result=await busy(()=>API('/api/programmings/apply-content','POST',{
     programming_id:proposal.programming_id,accepted_fields:selected,edited_fields:edited,
     accept_document_hours:hoursAccepted,accept_units:unitsAccepted,unit_hours:hours,
     accept_feoe_criteria:feoeAccepted,
     keep_source_sections:Boolean(form.querySelector('[name=keep_source_sections]:checked'))
   }),'Apartados confirmados y conservados en el borrador.');
   if(result){S.importPreview=null;S.wizardDraft=null;S.preparePath='import';await page('preparar');}
   return;
 }
 if(id==='feoe-roster'){const r=await busy(()=>API('/api/cycle-record/roster?module_id='+Number(form.elements.module_id.value)));if(r){S.feoeRoster=r;await page('feoe');}return;}
 if(id==='feoe-select'){S.feoeStay=Number(form.elements.stay_id.value)||null;await page('feoe');return;}
 if(id.startsWith('feoe-')){
   const b=formObject(form);let action=id.slice(5);const raw={...b,stay_id:Number(S.feoeStay)};
   if(id==='feoe-stay'){raw.module_id=Number(S.feoeRoster.module.id);raw.student_id=Number(b.student_id);raw.company_id=Number(b.company_id);}
   if(id==='feoe-target'){raw.outcome_id=Number(b.outcome_id);raw.criterion_ids=String(b.criterion_ids||'').split(',').map(x=>x.trim()).filter(Boolean).map(Number);}
   if(id.startsWith('feoe-valuation-')){action='valuation';raw.target_id=Number(form.dataset.target);}
   if(id.startsWith('feoe-review-')){action='review';raw.valuation_id=Number(form.dataset.valuation);}
   raw.teacher_confirmed=Boolean(form.elements.teacher_confirmed?.checked);
   const r=await busy(()=>API('/api/feoe/'+action,'POST',raw),'Registro FEOE guardado.');if(r){if(action==='stay')S.feoeStay=r.id;await page('feoe');}return;
 }
 if(id==='cycle-record-roster'){
   const mid=Number(form.elements.module_id.value);const result=await busy(()=>API('/api/cycle-record/roster?module_id='+mid));
   if(result){S.cycleRecordRoster=result;S.cycleRecordReport=null;S.cycleRecordAction='permanence';await page('expediente');}return;
 }
 if(id==='cycle-record-report'){
   const mid=Number(S.cycleRecordRoster.module.id),sid=Number(form.elements.student_id.value),session=form.elements.session.value;
   const result=await busy(()=>API('/api/cycle-record/report?module_id='+mid+'&student_id='+sid+'&session='+encodeURIComponent(session)));
   if(result){S.cycleRecordReport=result;S.cycleRecordAction='permanence';await page('expediente');}return;
 }
 if(id==='cycle-record-action'){S.cycleRecordAction=form.elements.action.value;await page('expediente');return;}
 if(id==='cycle-record-agreement'){
   const b=formObject(form),r=S.cycleRecordReport;if(!r)return;
   const facts={...b,action:S.cycleRecordAction||'permanence',cycle_years:2};
   delete facts.agreement;delete facts.meeting_ref;delete facts.teacher_confirmed;
   for(const key of ['pending_modules','pending_common','years_used','course'])if(key in b)facts[key]=Number(b[key]);
   for(const key of ['record_complete','conditions_confirmed'])facts[key]=Boolean(form.elements[key]?.checked);
   const result=await busy(()=>API('/api/cycle-record/decision','POST',{module_id:r.module_id,student_id:r.student.id,decision:{session:r.session,report_sha256:r.sha256,facts,agreement:b.agreement,meeting_ref:b.meeting_ref,teacher_confirmed:form.elements.teacher_confirmed.checked}}),'Actuación registrada en el historial local.');
   if(result){S.cycleRecordReport=await API('/api/cycle-record/report?module_id='+r.module_id+'&student_id='+r.student.id+'&session='+encodeURIComponent(r.session));await page('expediente');}return;
 }
 if(id==='academic-action'){S.academicAction=form.elements.action.value;await page('decisiones');return;}
 if(id==='academic-evaluate'){
   const b=formObject(form),target=$('#academic-result');
   const raw={...b,academic_year:'2026-2027',modality:'presencial_ordinaria',action:S.academicAction||'promotion',cycle_years:2};
   for(const key of ['pending_modules','pending_common','years_used','course'])if(key in b)raw[key]=Number(b[key]);
   for(const key of ['record_complete','conditions_confirmed'])raw[key]=Boolean(form.elements[key]?.checked);
   const result=await busy(()=>API('/api/academic-decisions/evaluate','POST',raw));
   if(!result||!target.isConnected)return;
   target.innerHTML=`<section class="panel"><h3>${E(result.status.replaceAll('_',' ').toUpperCase())}</h3><p>${E(result.reason)}</p><p>Versión de reglas: ${E(result.rules_version)}. No constituye una decisión oficial.</p><ul>${result.sources.map(u=>`<li><a href="${E(u)}" target="_blank" rel="noopener noreferrer">${E(u)}</a></li>`).join('')}</ul></section>`;return;
 }
 if(id==='scope-create-plan'){
   const b=formObject(form),origin=String(b.origin||'').split('|');
   const plan={student_id:Number(b.student_id),kind:b.kind,criterion_codes:String(b.criterion_codes||'').split(',').map(x=>x.trim()).filter(Boolean),objectives:b.objectives,actions:b.actions,instruments:b.instruments,due_date:b.due_date,origin_confirmed:form.elements.origin_confirmed.checked,origin_module_id:Number(origin[0]),origin_student_id:Number(origin[1]),origin_decision_id:Number(origin[2])};
   const result=await busy(()=>API('/api/common-scopes/recovery-create','POST',{module_id:Number(S.moduleId),plan}),'Plan individualizado guardado.');if(result)await page('preparar');return;
 }
 if(id.startsWith('scope-review-plan-')){
   const b=formObject(form),review={plan_id:Number(form.dataset.plan),status:b.status,observations:b.observations,evidence_ids:String(b.evidence_ids||'').split(',').map(x=>x.trim()).filter(Boolean).map(Number),teacher_confirmed:form.elements.teacher_confirmed.checked};
   const result=await busy(()=>API('/api/common-scopes/recovery-review','POST',{module_id:Number(S.moduleId),review}),'Revisión registrada.');if(result)await page('preparar');return;
 }
 if(id==='scope-select-session'){S.scopeSession=form.elements.session.value;await page('preparar');return;}
 if(id==='scope-matter-grade'){
   const b=formObject(form);const result=await busy(()=>API('/api/common-scopes/matter-grade','POST',{module_id:Number(S.moduleId),valuation:{student_id:Number(b.student_id),session:S.scopeSession||'ordinaria',grade:b.grade,hours:b.hours,hours_source:b.hours_source,rationale:b.rationale,teacher_confirmed:form.elements.teacher_confirmed.checked}}),'Valoración docente registrada.');
   if(result)await page('preparar');return;
 }
 if(id.startsWith('scope-team-decision-')){
   const b=formObject(form);const result=await busy(()=>API('/api/common-scopes/team-decision','POST',{module_id:Number(S.moduleId),decision:{student_id:Number(form.dataset.student),grade_ids:JSON.parse(form.dataset.gradeIds),session:S.scopeSession||'ordinaria',grade:b.grade,meeting_ref:b.meeting_ref,rationale:b.rationale,team_confirmed:form.elements.team_confirmed.checked}}),'Acuerdo registrado en el historial local.');
   if(result)await page('preparar');return;
 }
 if(id==='scope-add-student'){
   const b=formObject(form);const result=await busy(()=>API('/api/students','POST',{module_id:Number(S.moduleId),code:b.code,name:b.name}),'Alumno registrado.');
   if(result)await page('preparar');return;
 }
 if(id==='scope-add-activity'){
   const b=formObject(form),criterion_codes=Array.from(form.querySelectorAll('[name=criterion_codes]:checked')).map(el=>el.value);
   const result=await busy(()=>API('/api/common-scopes/activity','POST',{module_id:Number(S.moduleId),activity:{title:b.title,situation:b.situation,instrument:b.instrument,term:Number(b.term),activity_date:b.activity_date,criterion_codes}}),'Actividad guardada.');
   if(result)await page('preparar');return;
 }
 if(id==='scope-add-evidence'){
   const b=formObject(form),parts=String(b.activity_criterion||'').split('|');
   const result=await busy(()=>API('/api/common-scopes/evidence','POST',{module_id:Number(S.moduleId),evidence:{activity_id:Number(parts[0]),criterion_code:parts[1],student_id:Number(b.student_id),level:b.level,notes:b.notes,evidence_ref:b.evidence_ref}}),'Valoración registrada con historial.');
   if(result)await page('preparar');return;
 }
 if(id==='common-scope-draft'){
   const competencies=[];
   for(const block of form.querySelectorAll('.scope-competency')){
     const description=block.querySelector('[name=scope-description]').value.trim();
     const descriptors=block.querySelector('[name=scope-descriptors]').value.trim();
     const lines=block.querySelector('[name=scope-criteria]').value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
     if(!description&&!descriptors&&!lines.length)continue;
     const criteria=[];
     for(const line of lines){
       const cols=line.split('|').map(x=>x.trim());
       if(cols.length<2||cols.length>3){toast('Cada criterio requiere número | enunciado | descriptores opcionales.',true);return;}
       criteria.push({code:cols[0],description:cols[1],descriptors:cols[2]||''});
     }
     competencies.push({code:block.dataset.code,description,descriptors,criteria});
   }
   const result=await busy(()=>API('/api/common-scopes/save','POST',{module_id:Number(S.moduleId),draft:{competencies,saberes:form.elements.saberes.value,teacher_reviewed:form.elements.teacher_reviewed.checked}}),'Borrador competencial guardado.');
   if(result)await page('preparar');return;
 }
 if(id==='guided-review'){
   if(!form.elements.teacher_confirmed.checked){toast('Revise los RA y CE antes de confirmar.',true);return;}
   const outcomes=guidedReadProposal(form);
   const result=await busy(()=>API('/api/programmings/apply','POST',{
     module_id:Number(S.moduleId),outcomes,
     source_url:S.proposal?.source_url||null,consulted_at:S.proposal?.consulted_at||null
   }),'Currículo confirmado.');
   if(result){S.proposal=null;await page('preparar');}return;
 }
 if(id==='prepare-minimum'){
   S.wizardDraft.assessment=form.elements.assessment.value;
   S.wizardDraft.recovery=form.elements.recovery.value;
   S.wizardDraft.source_type='evaluation';
   const result=await busy(()=>API('/api/programming-builder/save','POST',{
     module_id:Number(S.moduleId),draft:S.wizardDraft}),'Configuración básica guardada.');
   if(result)await page('preparar');return;
 }
 if(id==='prepare-wizard-form'){
   const ok=await saveWizardPage();
   if(ok){S.prepareStep=Math.min(5,S.prepareStep+1);await page('preparar');}
   return;
 }
 if(id==='change-storage'){
   if(!confirm('Se copiarán SQLite y los originales a la nueva carpeta. Es necesario cerrar y volver a abrir la aplicación después. ¿Continuar?'))return;
   const result=await busy(()=>API('/api/storage/change','POST',formObject(form)),'Carpetas migradas; reinicie EvalúaFP.');
   if(result?.restart_required)alert('La migración ha finalizado. Cierre EvalúaFP y vuelva a abrirlo. No borre los datos antiguos hasta comprobar todo.');
   return;
 }
 if(id==='unlock-api'){
   const result=await busy(()=>API('/api/settings/unlock','POST',formObject(form)),'Clave API desbloqueada.');
   if(result)await page('ajustes');return;
 }
 if(id==='eval-policy'){
   const body=formObject(form);body.module_id=S.evaluationModuleId;body.validated=form.elements.validated.checked;
   const result=await busy(()=>API('/api/evaluation/policy','POST',body),'Política de evaluación guardada.');
   if(result)await page('evaluacion');return;
 }
 if(id==='eval-unit'){
   const body=formObject(form);body.module_id=S.evaluationModuleId;
   body.criteria_ids=[...form.querySelectorAll('input[name=criteria_ids]:checked')].map(e=>Number(e.value));
   const result=await busy(()=>API('/api/evaluation/unit','POST',body),'Unidad creada.');
   if(result)await page('evaluacion');return;
 }
 if(id==='eval-instrument'){
   const body=formObject(form);body.module_id=S.evaluationModuleId;
   body.targets=S.evalData.criteria.filter(c=>form.elements['target_'+c.id]?.checked).map(c=>({criterion_id:c.id,weight:Number(form.elements['weight_'+c.id].value)}));
   if(!body.unit_id)delete body.unit_id;if(!body.exam_id)delete body.exam_id;
   const result=await busy(()=>API('/api/evaluation/instrument','POST',body),'Instrumento creado.');
   if(result){S.evalInstrumentId=result.id;await page('evaluacion');}return;
 }
 if(id==='eval-import'){
   const result=await busy(()=>API('/api/evaluation/import','POST',new FormData(form)),'Calificaciones importadas y registradas.');
   if(result)await page('evaluacion');return;
 }
 if(id==='create-module'){
 const result=await busy(()=>API('/api/modules','POST',formObject(form)),'Módulo creado.');
 if(result){S.moduleId=result.id;S.proposal=null;S.preparePath=null;await page('preparar');}return;}
 if(id==='create-student'){
 const result=await busy(()=>API('/api/students','POST',formObject(form)),'Alumno registrado.');
 if(result)await page('programaciones');return;}
 if(id==='create-outcome'||id==='create-criterion'){
 let b=formObject(form);if(id==='create-outcome')b.module_id=S.moduleId;
 const result=await busy(()=>API('/api/'+(id==='create-outcome'?'outcomes':'criteria'),'POST',b),'Criterio actualizado.');
 if(result)await page('programaciones');return;}
   if(id==='upload-material'){
    const result=await busy(()=>API('/api/materials/upload','POST',new FormData(form)),'Material documental incorporado.');
    if(result){toast(result.created.length+' archivos y '+result.created.reduce((n,x)=>n+x.passages,0)+' pasajes registrados.');await page('programaciones');}return;}
 if(id==='upload-program'){
 const result=await busy(()=>API('/api/programmings/upload','POST',new FormData(form)),'Programación original guardada.');
 if(result){toast('Texto extraído: '+result.characters+' caracteres.');await page('programaciones');}return;}
 if(id==='apply-proposal'){
 let parsed;
 try{parsed=JSON.parse(form.querySelector('[name=outcomes_json]').value)}catch(e){toast('JSON no válido: '+e.message,true);return;}
 const result=await busy(()=>API('/api/programmings/apply','POST',{module_id:S.moduleId,outcomes:parsed,
      source_url:S.proposal?.source_url||null, consulted_at:S.proposal?.consulted_at||null}),'RA y CE confirmados.');
 if(result){S.proposal=null;await page('programaciones');}return;}
 if(id==='manual-exam'){
   let q;
   try{q=JSON.parse(form.elements.questions_json.value);}catch(ex){toast('Preguntas JSON no válidas: '+ex.message,true);return;}
   const result=await busy(()=>API('/api/exams/manual','POST',{
      module_id:Number(form.elements.module_id.value),title:form.elements.title.value,questions:q,
      center_name:form.elements.center_name.value,duration_minutes:Number(form.elements.duration_minutes.value),
      teacher_confirmed_curriculum:document.getElementById('manual-confirm')?.checked===true
   }),'Examen manual archivado.');
   if(result){S.manualDraft=null;S.examId=result.id;await page('examenes');}return;
 }
 if(id==='generate-exam'||id==='generate-exam-quick'){
 const f=formObject(form);
 f.criteria_ids=[...form.querySelectorAll('[name=criteria_ids]:checked')].map(i=>Number(i.value));
 if(!f.criteria_ids.length){toast('Seleccione al menos un criterio de evaluación.',true);return;}
   if(S.modules.length){
     const detail=await API('/api/modules/'+Number(f.module_id));
     if((detail.materials||[]).some(m=>m.active)){
       if(!confirm('Se enviarán PASAJES de los materiales didácticos del módulo al proveedor de IA seleccionado. Confirme que dispone de los permisos y condiciones de uso adecuados. ¿Autoriza el envío?'))return;
       f.authorize_external_transfer=true;
     }
   }
    const bankTarget=Number(f.question_count)*Math.max(3,Number(f.model_count)||1);
    const info=document.createElement('div');info.className='panel';info.setAttribute('role','status');
    info.innerHTML='<h3>Generando examen con IA</h3><p id="exam-progress-detail"></p><p class="small">El generador agrupa varios CE por petición. Se conservan las rúbricas, el banco triple y las preguntas distintas. No cierre la aplicación.</p>';
    form.parentNode.insertBefore(info,form.nextSibling);
    const began=Date.now();
    const tick=()=>{const detail=info.querySelector('#exam-progress-detail');if(detail)detail.textContent=`Banco solicitado: al menos ${bankTarget} preguntas · ${f.model_count} modelo(s) · ${Math.floor((Date.now()-began)/1000)} s transcurridos. Esperando respuesta del proveedor...`;};
    tick();const timer=setInterval(tick,1000);
    let result;
    try{result=await busy(()=>API('/api/exams/generate','POST',f), 'Generados '+f.model_count+' modelo(s) y banco de preguntas.');}
    finally{clearInterval(timer);info.remove();}
    if(result){S.examId=result.id;await page('examenes');}return;}
 if(id==='upload-submission'){
 const f=new FormData();const d=formObject(form);
 f.append('exam_id',d.exam_id);f.append('student_id',d.student_id);
 S.queue.forEach(file=>f.append('pages',file,file.name));
 toast('Importando originales y creando páginas de lectura.');
 const result=await busy(()=>API('/api/submissions/upload','POST',f),'Entrega archivada con originales.');
 if(result){S.queue=[];S.subId=result.id;S.pageIndex=0;await page('correcciones');}return;}
 if(id==='upload-batch'){
 const f=new FormData(form);
 toast('Comprobando códigos del ZIP e importando exámenes...');
 let result;
 try{result=await API('/api/submissions/batch','POST',f);}
 catch(e){
   if(e.code!=='MISSING_STUDENTS'){toast(e.message,true);return;}
   const missing=e.missing_students||[];
   const created=await promptNewStudents(e.module_id,missing);
   if(!created){toast('Importación cancelada. No se ha importado ningún examen.',true);return;}
   // El File del ZIP permanece en FormData: no exige volver a seleccionarlo.
   try{result=await API('/api/submissions/batch','POST',f);}
   catch(retryError){toast(retryError.message,true);return;}
 }
 if(result){toast(result.created.length+' alumnos y '+result.created.reduce((n,x)=>n+x.pages,0)+' páginas registradas.');await page('entregas');}return;}
 if(id==='save-settings'){
 const body=formObject(form);if(!body.api_key)delete body.api_key;
 const result=await busy(()=>API('/api/settings','POST',body),'Configuración guardada.');
 if(result){if(result.api_key_persistent===false)toast('La clave solo permanecerá en memoria durante esta sesión.');await page('ajustes');}return;}
 if(form.classList.contains('edit-transcription')){
 const result=await busy(()=>API('/api/corrections/transcription','POST',{
 correction_id:Number(form.dataset.cid),transcription:form.elements.transcription.value}),'Transcripción corregida; deberá repetirse la evaluación IA.');
 if(result)await page('correcciones');return;}
 if(form.classList.contains('validate')){
 const result=await busy(()=>API('/api/corrections/validate','POST',{
 correction_id:Number(form.dataset.cid),score:Number(form.elements.score.value),comment:form.elements.comment.value}), 'Calificación validada por el docente.');
 if(result)await page('correcciones');return;}
}
document.addEventListener('submit',event=>{
 if(event.target.matches('form')){event.preventDefault();doSubmit(event.target).catch(e=>toast(e.message,true));}
});
document.addEventListener('change',async event=>{
 if(event.target.id==='guide-automatic-weights'){
    const mode=Boolean(event.target.checked);
    $all('[data-weight-ra],[data-weight-ce]').forEach(input=>input.disabled=mode);
    return;
 }

 try {
 const el=event.target;
 if(el.id==='ag-module-pick'){
   const form=el.closest('#prepare-create,#create-module');
   if(form){
      form.elements.name.value=el.value||'';
      form.dataset.agPickedName=el.value||'';
      const ref=el.selectedOptions?.[0];
      form.elements.reference_course.value=ref?.dataset.referenceCourse||'';
      form.elements.reference_code.value=ref?.dataset.referenceCode||'';
      if(form.elements.catalog_entry_id?.value){form.elements.catalog_entry_id.value='';S.catalogPicked=null;}
      const note=form.querySelector('[data-catalog-selection]');
      if(note)note.textContent='La lista orientativa no confirma el currículo ni sus horas.';
   }
   return;
 }
 if(el.closest('#prepare-create,#create-module') &&
    (['cycle','name','territory','academic_year'].includes(el.name)||el.id==='ag-course-filter')){
   const form=el.form;
   if(el.name==='cycle'||el.name==='academic_year'||el.id==='ag-course-filter'){
      if(form.dataset.agPickedName&&form.elements.name.value===form.dataset.agPickedName)form.elements.name.value='';
      form.dataset.agPickedName='';
      form.elements.reference_course.value='';
      form.elements.reference_code.value='';
   }else if(el.name==='name'&&el.value!==form.dataset.agPickedName){
      const pick=form.querySelector('#ag-module-pick');if(pick)pick.value='';
      form.dataset.agPickedName='';
      form.elements.reference_course.value='';
      form.elements.reference_code.value='';
   }
   if(form?.elements.catalog_entry_id?.value){
      form.elements.catalog_entry_id.value='';S.catalogPicked=null;
      const note=form.querySelector('[data-catalog-selection]');
      if(note)note.textContent='Selección del catálogo anulada al modificar el módulo o el ámbito.';
   }
   if(el.name==='cycle'||el.name==='academic_year'||el.id==='ag-course-filter')await loadAGModuleSuggestions(form);
   if(el.name==='territory'||el.name==='academic_year'){
      S.catalogResults=null;S.catalogPreview=null;S.catalogPreviewScope=null;updateCatalogResults();
      S.todofpResult=null;S.todofpTitleSearch=null; // No arrastrar títulos o fuentes de otro curso/territorio.
      const explorer=$('#todofp-explorer');if(explorer)explorer.outerHTML=todofpExplorerPanel('catalog');
   }
   return;
 }
 if(el.id==='guide-region'){
   S.nationalSources=null;S.boeCandidates=null;S.boeInspection=null;S.todofpResult=null;S.todofpTitleSearch=null;
   const newRegion=el.value;const oldRegion=S.wizardDraft?.region;
   if(oldRegion!==newRegion){
     collectWizardFields();
     const calendar=await API('/api/territories/calendar?region='+encodeURIComponent(newRegion)+'&academic_year='+encodeURIComponent(S.prepareInfo.module.academic_year));
     S.wizardDraft.region=newRegion;
     S.wizardDraft.schedule={...S.wizardDraft.schedule,...calendar.schedule_defaults,
       region:newRegion,hours_confirmed:false,weekly_hours:0,total_hours:0,weekday_hours:[0,0,0,0,0],
       hours_source_url:'',hours_source_description:'Pendiente de comprobar las horas del módulo en '+newRegion};
     for(const field of ['normative_references','identification_data']){
       if(!S.wizardDraft.assistant_meta?.[field]?.teacher_edited){S.wizardDraft[field]='';delete S.wizardDraft.assistant_meta?.[field];}
     }
     S.wizardDraft.curriculum_confirmed=false;
     S.autoProposedModuleId=null;S.calendarInfo=null;
     await page('preparar');
     toast('Territorio cambiado: se han reiniciado las horas y los datos del calendario anterior.');
   }return;
 }
  if(el.id==='prepare-module'){S.todofpTitleSearch=null;S.todofpResult=null;S.curriculumReview=null;S.curriculumHistory=null;S.curriculumHistoryDiff=null;S.normativeMonitor=null;S.calendarVersions=null;S.calendarVersionDiff=null;S.generalCalendarLibrary=null;S.generalCalendarDiff=null;S.calendarDocumentPreview=null;S.calendarDocumentModuleId=null;S.calendarAiPreview=null;S.calendarAiModuleId=null;S.calendarAiFragment='';S.curriculumSourceFile=null;S.boeCandidates=null;S.boeInspection=null;S.boeSelectedId='';S.moduleId=Number(el.value);S.preparePath=null;S.autoProposedModuleId=null;S.wizardDraft=null;S.proposal=null;await page('preparar');return;}
 if(el.id==='module-select'){S.moduleId=el.value;S.proposal=null;await page('programaciones');}
 if(el.id==='evaluation-module'){S.evaluationModuleId=Number(el.value);S.evalInstrumentId=null;await page('evaluacion');}
 if(el.id==='eval-instrument-select'){S.evalInstrumentId=Number(el.value);renderEvalScores();}
 if(el.id==='quick-exam-module'){S.examModuleId=el.value;await page('examenes');}
 if(el.id==='exam-module'){S.examModuleId=el.value;await page('examenes');}
 if(el.id==='upload-exam'){S.uploadExamId=el.value;S.uploadStudentId=null;S.queue=[];await page('entregas');}
 if(el.id==='review-select'){S.subId=el.value;S.pageIndex=0;await page('correcciones');}
 if(el.id==='upload-pages'||el.id==='upload-camera'){
  S.queue.push(...[...el.files]);await page('entregas');
 }
 if(el.classList.contains('ra-checkbox')){
  $all(`[name=criteria_ids][data-parent="${el.dataset.ra}"]`).forEach(x=>x.checked=el.checked);
 }
 }catch(error){if(error?.message?.includes('canceló al cambiar de pantalla'))return;console.error(error);toast(error?.message||'Error al actualizar la selección.',true);}
});
document.querySelector('#toggle-advanced')?.addEventListener('click',()=>{
 S.advanced=!S.advanced;syncMode();
 // No reconstruir los formularios en uso; se aplica al abrir la siguiente vista.
 if(S.page==='inicio')page('inicio');
});
document.addEventListener('click',async event=>{
 try {
 const tab=event.target.closest('[data-page]');if(tab){await page(tab.dataset.page);return;}
 if(event.target.id==='large-page'){event.target.classList.toggle('zoom');return;}
 const el=event.target.closest('[data-action]');if(!el)return;
 const action=el.dataset.action;const id=Number(el.dataset.id);const index=Number(el.dataset.index);
 if(action==='eval-scope-notebook'){S.moduleId=Number(S.evaluationModuleId);S.scopeNotebookModule=S.moduleId;S.scopeConsolidationModule=null;await page('preparar');return;}
 if(action==='backup-list-refresh'){await page('ajustes');return;}
 if(action==='home-advanced'){S.advanced=true;syncMode();await page('inicio');return;}
 if(action==='home-task'){
   const destination=el.dataset.target;
   if(!S.moduleId&&destination!=='preparar'){await page('preparar');return;}
   if(destination==='evaluacion'||destination==='examenes'){
     const mid=Number(S.moduleId);
     const scope=await API('/api/common-scopes/draft?module_id='+mid);
     if(S.page!=='inicio'||Number(S.moduleId)!==mid)return;
     if(scope.profile){
       S.scopeNotebookModule=destination==='evaluacion'?mid:null;S.scopeConsolidationModule=null;
       await page('preparar');return;
     }
     if(destination==='evaluacion'){S.evaluationModuleId=mid;S.evalInstrumentId=null;}
     else S.examModuleId=mid;
   }
   await page(destination);return;
 }
 if(action==='boe-monitor-check'){
   const boe_id=el.dataset.boeId||$('#monitor-boe-id')?.value.trim()||'';
   if(!boe_id){toast('Introduzca un identificador del BOE.',true);return;}
   if(!confirm('¿Ha comprobado que esta disposición corresponde al módulo y desea consultar sus metadatos oficiales? El resultado no acreditará vigencia jurídica.'))return;
   const result=await busy(()=>API('/api/national/boe-monitor/check','POST',{module_id:Number(S.moduleId),boe_id,teacher_confirmed:true}));
   if(result){
      toast(result.status==='cambio_detectado'?'Se han observado diferencias: revisión docente necesaria.':result.status==='referencia_inicial'?'Referencia inicial registrada.':'Consulta completada: sin nuevas diferencias observadas.');
      await page('preparar');
   }return;
 }
 if(action==='boe-monitor-ack'){
   const boe_id=el.dataset.boeId;
   const note=prompt('Indique qué ha comprobado en la disposición y qué revisión curricular queda pendiente (mínimo 12 caracteres):','');
   if(note===null)return;
   if(!confirm('¿Registrar que ha examinado el aviso? No se valida automáticamente la norma ni se modifican los criterios.'))return;
   const result=await busy(()=>API('/api/national/boe-monitor/ack','POST',{module_id:Number(S.moduleId),boe_id,note,teacher_confirmed:true}));
   if(result){toast('Se ha registrado la revisión docente de la alerta.');await page('preparar');}return;
 }
 if(action==='curriculum-history-save'){
   if(!S.curriculumSourceFile||!S.curriculumReview){toast('Vuelve a seleccionar y previsualizar el documento original.',true);return;}
   if(S.curriculumSourceKind!=='norma_oficial'){toast('El historial normativo solo admite disposiciones oficiales.',true);return;}
   if(!$('#curriculum-version-confirm')?.checked){toast('Confirma la revisión de la fuente y su ámbito antes de archivarla.',true);return;}
   const f=new FormData();f.append('module_id',String(S.moduleId));
   f.append('module_code',String(S.curriculumReview.module_code));f.append('document_kind','norma_oficial');
   f.append('source_url',$('#curriculum-version-url')?.value||'');f.append('source_title',$('#curriculum-version-title')?.value||'');
   f.append('teacher_confirmed','true');f.append('document',S.curriculumSourceFile);
   const result=await busy(()=>API('/api/curriculum/history/store','POST',f),'Fuente curricular archivada, sin alterar RA ni CE.');
   if(result){S.curriculumHistoryDiff=result.change||null;await page('preparar');}
   return;
 }
 if(action==='curriculum-history-compare'){
   const old=Number(el.dataset.old),newer=Number(el.dataset.new);
   const result=await busy(()=>API('/api/curriculum/history-compare?module_id='+Number(S.moduleId)+'&old='+old+'&new='+newer));
   if(result){S.curriculumHistoryDiff=result;await page('preparar');}return;
 }
 if(action==='national-boe-search'){
   collectWizardFields();
   const m=S.prepareInfo?.module;
   const result=await busy(()=>API('/api/national/boe-search','POST',{
     cycle:m.cycle, region:S.wizardDraft?.region||'Canarias',academic_year:m.academic_year
   }),'Búsqueda oficial completada; revisa los candidatos.');
   if(result){S.boeCandidates=result;S.boeInspection=null;await page('preparar');}return;
 }
 if(action==='national-boe-pick'){
   S.boeSelectedId=el.dataset.boeId;
   const result=await busy(()=>API('/api/national/boe-inspect','POST',{boe_id:S.boeSelectedId}));
   if(result){S.boeInspection=result;collectWizardFields();await page('preparar');}return;
 }
 if(action==='national-boe-inspect'){
   S.boeSelectedId=$('#national-boe-id')?.value.trim().toUpperCase()||'';
   const result=await busy(()=>API('/api/national/boe-inspect','POST',{boe_id:S.boeSelectedId}));
   if(result){S.boeInspection=result;collectWizardFields();await page('preparar');}return;
 }
 if(action==='national-boe-add'){
   if(!S.boeInspection)return;
   if(!confirm('La norma consultada es una candidata. ¿Añadir su enlace a las referencias para revisarlo, sin declararla curricularmente aplicable?'))return;
   collectWizardFields();
   const r=S.boeInspection;const line='Norma pendiente de comprobar: '+r.title+' · '+r.url;
   const old=S.wizardDraft.normative_references||'';
   if(!old.includes(r.url))S.wizardDraft.normative_references=old?(old+'\n'+line):line;
   S.wizardDraft.curriculum_confirmed=false;
   S.wizardDraft.assistant_meta=S.wizardDraft.assistant_meta||{};
   S.wizardDraft.assistant_meta.normative_references={origin:'BOE (candidata pendiente de revisión)',teacher_edited:true};
   const saved=await busy(()=>API('/api/programming-builder/save','POST',{
      module_id:Number(S.moduleId),draft:S.wizardDraft}),
      'Referencia guardada como pendiente de revisión; no se ha dado por verificado el currículo.');
   if(saved)await page('preparar');return;
 }

 if(action==='calendar-document-preview'){
   const file=$('#calendar-document-file')?.files?.[0];
   if(!file){toast('Selecciona una resolución PDF, Word o texto.',true);return;}
   if(file.size>15*1024*1024){toast('El calendario supera 15 MB.',true);return;}
   collectWizardFields();
   const m=S.prepareInfo?.module;
   if(!m){toast('Selecciona un módulo antes de importar el calendario.',true);return;}
   const form=new FormData();
   form.append('module_id',String(S.moduleId));
   form.append('region',S.wizardDraft?.region);
   form.append('academic_year',m.academic_year);
   form.append('document',file);
   form.append('allow_ocr',$('#calendar-document-ocr')?.checked?'true':'false');
   const result=await busy(()=>API('/api/national/calendar-document-preview','POST',form));
   if(result){
     S.calendarDocumentPreview=result;S.calendarDocumentModuleId=Number(S.moduleId);
     toast(result.candidate_count+' fechas/periodos encontrados; revisa la procedencia antes de cargarlos.');
     await page('preparar');
   }return;
 }
 if(action==='calendar-document-use'){
   const report=S.calendarDocumentPreview,m=S.prepareInfo?.module;
   if(!report||!report.scope_ok||report.region!==S.wizardDraft?.region||
      report.academic_year!==m?.academic_year||Number(S.calendarDocumentModuleId)!==Number(S.moduleId)){
      toast('La vista previa corresponde a otro módulo, territorio o curso. Repite la extracción.',true);return;}
   if(!$('#calendar-document-confirm')?.checked){
     toast('Coteja primero el documento y confirma el contexto escolar.',true);return;}
   const selected={};
   $all('[data-calendar-import-field]:checked').forEach(input=>{
     const name=input.dataset.calendarImportField,idx=Number(input.dataset.calendarImportIndex);
     const candidate=report.candidates?.[name]?.[idx];
     if(candidate)(selected[name]??=[]).push(JSON.parse(JSON.stringify(candidate.value)));
   });
   if(!Object.keys(selected).length){toast('Marca al menos una fecha o periodo.',true);return;}
   if(!confirm('Se sustituirán solamente los campos seleccionados (por ejemplo, vacaciones o festivos). El calendario quedará SIN confirmar, sin modificar horas, FEOE, notas ni RA/CE. ¿Continuar?'))return;
   collectWizardFields();
   const next={...S.wizardDraft.schedule};
   if(selected.start_date)next.start_date=selected.start_date[0];
   if(selected.end_date)next.end_date=selected.end_date[0];
   if(next.start_date&&next.end_date&&next.start_date>=next.end_date){
     toast('El fin del curso no puede ser anterior al inicio.',true);return;}
   if(selected.vacation_periods)next.vacation_periods=selected.vacation_periods;
   if(selected.regional_non_teaching_days)next.regional_non_teaching_days=selected.regional_non_teaching_days;
   next.calendar_confirmed=false;next.calendar_profile_id='';
   S.wizardDraft.schedule=next;S.calendarDocumentPreview=null;S.calendarDocumentModuleId=null;
   toast('Fechas cargadas en el borrador sin confirmar. Completa las fuentes y los festivos locales.');
   await page('preparar');return;
 }

 if(action==='calendar-copy-ai-excerpt'){
   const report=S.calendarDocumentPreview;
   if(!report||!report.scope_ok||report.region!==S.wizardDraft?.region||
      report.academic_year!==S.prepareInfo?.module?.academic_year||
      Number(S.calendarDocumentModuleId)!==Number(S.moduleId)){
       toast('El documento no corresponde a este territorio, curso o módulo.',true);return;
   }
   S.calendarAiFragment=report.suggested_ai_fragment||'';
   S.calendarAiPreview=null;S.calendarAiModuleId=null;
   toast('Fragmento preparado en el cuadro de IA. Revísalo antes de autorizar cualquier envío.');
   collectWizardFields();await page('preparar');return;
 }
 if(action==='calendar-ai-analyze'){
   const fragment=$('#calendar-ai-fragment')?.value.trim()||'';
   if(fragment.length<35||fragment.length>12000){
     toast('Copia entre 35 y 12.000 caracteres con el territorio, curso y etapa FP.',true);return;
   }
   if(!$('#calendar-ai-authorize')?.checked){
     toast('Debes autorizar expresamente el envío del fragmento a tu proveedor de IA.',true);return;
   }
   collectWizardFields();
   const module=S.prepareInfo?.module;
   if(!module)return;
   if(!confirm('¿Autorizas enviar exclusivamente este fragmento a la IA configurada? No se enviarán archivos ni calificaciones.'))return;
   const result=await busy(()=>API('/api/national/calendar-ai-interpret','POST',{
      module_id:Number(S.moduleId),region:S.wizardDraft.region,
      academic_year:module.academic_year,fragment,authorize_ai:true
   }));
   if(result){S.calendarAiFragment=fragment;S.calendarAiPreview=result;
     S.calendarAiModuleId=Number(S.moduleId);
     toast(result.candidate_count+' propuestas IA con fechas y citas comprobadas en el texto.');
     await page('preparar');}
   return;
 }
 if(action==='calendar-ai-use'){
   const report=S.calendarAiPreview,m=S.prepareInfo?.module;
   if(($('#calendar-ai-fragment')?.value||'').trim()!==S.calendarAiFragment){
      toast('Has modificado el fragmento después del análisis. Repite la comprobación con IA.',true);return;
   }
   if(!report||!report.scope_ok||report.region!==S.wizardDraft?.region||
      report.academic_year!==m?.academic_year||Number(S.calendarAiModuleId)!==Number(S.moduleId)){
      toast('La vista previa corresponde a otro módulo, territorio o curso. Repite la extracción.',true);return;}
   if(!$('#calendar-ai-confirm')?.checked){
     toast('Coteja primero el documento y confirma el contexto escolar.',true);return;}
   const selected={};
   $all('[data-calendar-ai-field]:checked').forEach(input=>{
     const name=input.dataset.calendarAiField,idx=Number(input.dataset.calendarAiIndex);
     const candidate=report.candidates?.[name]?.[idx];
     if(candidate)(selected[name]??=[]).push(JSON.parse(JSON.stringify(candidate.value)));
   });
   if(!Object.keys(selected).length){toast('Marca al menos una fecha o periodo.',true);return;}
   if(!confirm('Se sustituirán solamente los campos seleccionados (por ejemplo, vacaciones o festivos). El calendario quedará SIN confirmar, sin modificar horas, FEOE, notas ni RA/CE. ¿Continuar?'))return;
   collectWizardFields();
   const next={...S.wizardDraft.schedule};
   if(selected.start_date)next.start_date=selected.start_date[0];
   if(selected.end_date)next.end_date=selected.end_date[0];
   if(next.start_date&&next.end_date&&next.start_date>=next.end_date){
     toast('El fin del curso no puede ser anterior al inicio.',true);return;}
   if(selected.vacation_periods)next.vacation_periods=selected.vacation_periods;
   if(selected.regional_non_teaching_days)next.regional_non_teaching_days=selected.regional_non_teaching_days;
   next.calendar_confirmed=false;next.calendar_profile_id='';
   S.wizardDraft.schedule=next;S.calendarAiPreview=null;S.calendarAiModuleId=null;
   toast('Fechas cargadas en el borrador sin confirmar. Completa las fuentes y los festivos locales.');
   await page('preparar');return;
 }
 if(action==='national-document-preview'){
   const file=$('#national-table-file')?.files?.[0];
   if(!file){toast('Selecciona un PDF o DOCX con la tabla horaria.',true);return;}
   const form=new FormData();form.append('document',file);form.append('allow_ocr',$('#national-ocr')?.checked?'true':'false');
   const result=await busy(()=>API('/api/national/document-preview','POST',form));
   if(result){collectWizardFields();S.nationalTableText=result.table;S.nationalTablePreview=result;
     toast('Se han reconocido '+result.count+' módulos; revisa las filas y la disposición antes de guardarlas.');
     await page('preparar');}return;
 }
 if(action==='todofp-search-titles'){
   const grade=$('#todofp-title-grade')?.value||'Superior';
   const query=$('#todofp-title-query')?.value.trim()||'';
   const inWizard=S.preparePath==='create'&&Boolean(S.prepareInfo?.module)&&Boolean($('#prepare-wizard-form'));
   if(inWizard)collectWizardFields();
   const scope=inWizard?{region:S.wizardDraft.region,academic_year:S.prepareInfo.module.academic_year}:catalogScopeFromForm();
   const data=await busy(()=>API('/api/national/todofp/search-titles','POST',{grade,query,...scope}),
      'Índice de títulos consultado. Comprueba las fichas y la norma aplicable.');
   if(data){S.todofpTitleGrade=grade;S.todofpTitleQuery=query;S.todofpTitleSearch=data;
     S.todofpResult=null;const panel=$('#todofp-explorer');
     if(panel)panel.outerHTML=todofpExplorerPanel(inWizard?'builder':'catalog');else await page('preparar');}
   return;
 }
 if(action==='todofp-open-title'){
   const data=S.todofpTitleSearch;
   const inWizard=S.preparePath==='create'&&Boolean(S.prepareInfo?.module)&&Boolean($('#prepare-wizard-form'));
   if(inWizard)collectWizardFields();
   const scope=inWizard?{region:S.wizardDraft.region,academic_year:S.prepareInfo.module.academic_year}:catalogScopeFromForm();
   if(!data||scope.region!==data.territory||scope.academic_year!==data.academic_year){
      toast('El índice pertenece a otra comunidad o curso. Repita la búsqueda.',true);return;}
   const record=data.results?.[Number(el.dataset.titleIndex)];if(!record)return;
   const found=await busy(()=>API('/api/national/todofp/explore','POST',{url:record.url,...scope,
       cycle_name:inWizard?S.prepareInfo.module.cycle:'',module_name:inWizard?S.prepareInfo.module.name:''}),
       'Ficha consultada. Comprueba los módulos y los currículos autonómicos.');
   if(found){S.todofpResult=found;S.todofpURL=record.url;
     const panel=$('#todofp-explorer');if(panel)panel.outerHTML=todofpExplorerPanel(inWizard?'builder':'catalog');
     else await page('preparar');}return;
 }
 if(action==='todofp-explore'){
   const src=$('#todofp-url')?.value.trim()||'';
   if(!src){toast('Indique el enlace oficial a la ficha TodoFP del ciclo.',true);return;}
   const inWizard=S.preparePath==='create'&&Boolean(S.prepareInfo?.module)&&Boolean($('#prepare-wizard-form'));
   if(inWizard)collectWizardFields();
   const scope=inWizard?{region:S.wizardDraft.region,academic_year:S.prepareInfo.module.academic_year}:catalogScopeFromForm();
   const result=await busy(()=>API('/api/national/todofp/explore','POST',{url:src,...scope,
     cycle_name:inWizard?S.prepareInfo.module.cycle:'',module_name:inWizard?S.prepareInfo.module.name:''}),
     'Ficha consultada: revise el currículo y las modificaciones de la comunidad.');
   if(result){
     S.todofpURL=src;S.todofpResult=result;
     // No reconstruir el formulario de creación: conservar comunidad,
     // curso, nombre y grupo que el docente ya ha escrito.
     const panel=$('#todofp-explorer');
     if(panel)panel.outerHTML=todofpExplorerPanel(inWizard?'builder':'catalog');
     else await page('preparar');
   }return;
 }
 if(action==='todofp-select-module'){
   const current=S.todofpResult;
   const form=catalogCreationForm();
   const scope=catalogScopeFromForm();
   if(!form||!current?.profile||scope.region!==current.region||scope.academic_year!==current.academic_year){
     toast('Compruebe de nuevo comunidad y curso antes de utilizar un nombre.',true);return;
   }
   const found=current.profile.modules[Number(el.dataset.todofpIndex)];
   if(!found)return;
   form.elements.cycle.value=resolveAGCycle(current.profile.title);
   form.elements.name.value=found.name;
   form.elements.catalog_entry_id.value='';S.catalogPicked=null;
   const note=form.querySelector('[data-catalog-selection]');
   if(note)note.textContent='Denominación orientativa de TodoFP; compruebe los códigos en la norma aplicable. No se han confirmado RA, CE ni horas.';
   toast('Denominación propuesta: revise la normativa antes de guardar el módulo.');return;
 }
 if(action==='todofp-add-refs'){
   const result=S.todofpResult;
   if(!S.wizardDraft||!result||!S.prepareInfo||result.suitable_for_current_module===false||result.region!==S.wizardDraft.region||result.academic_year!==S.prepareInfo.module.academic_year){
      toast('La consulta no corresponde a este módulo, curso o comunidad. Repita la búsqueda.',true);return;
   }
   if(!confirm('Los enlaces son solo candidatos para consulta. ¿Añadirlos al borrador como pendientes, sin confirmar automáticamente el currículo?'))return;
   collectWizardFields();
   const refs=[...(result.regional_curricula?.links||[]).map(x=>({label:x.label,url:x.url}))];
   if(result.profile?.state_norm_url)refs.unshift({label:'Norma estatal del título',url:result.profile.state_norm_url});
   let old=S.wizardDraft.normative_references||'';
   for(const r of refs){if(!old.includes(r.url))old+=(old?'\n':'')+'FUENTE LOCALIZADA POR TODOFP, PENDIENTE DE COMPROBAR ('+result.region+', '+result.academic_year+'): '+r.label+' · '+r.url;}
   S.wizardDraft.normative_references=old;
   S.wizardDraft.curriculum_confirmed=false;
   S.wizardDraft.assistant_meta=S.wizardDraft.assistant_meta||{};
   S.wizardDraft.assistant_meta.normative_references={origin:'Directorios TodoFP (pendiente de validar)',teacher_edited:true};
   const saved=await busy(()=>API('/api/programming-builder/save','POST',{module_id:Number(S.moduleId),draft:S.wizardDraft}),
        'Fuentes candidatas guardadas para revisión; currículo sin confirmar.');
   if(saved)await page('preparar');return;
 }
 if(action==='catalog-search'){
   const scope=catalogScopeFromForm();
   const query=$('#catalog-query')?.value.trim()||'';
   const result=await busy(()=>API('/api/national/catalog?region='+encodeURIComponent(scope.region)+
      '&academic_year='+encodeURIComponent(scope.academic_year)+'&q='+encodeURIComponent(query)));
   if(result){S.catalogResults=result;S.catalogPreview=null;updateCatalogResults();}return;
 }
 if(action==='catalog-choose'){
   const entry=(S.catalogResults?.entries||[]).find(x=>Number(x.id)===Number(el.dataset.catalogId));
   if(!entry)return;
   const scope=catalogScopeFromForm();
   if(scope.region!==S.catalogResults.territory||scope.academic_year!==S.catalogResults.academic_year){
      toast('Has cambiado comunidad o curso. Repite la búsqueda antes de seleccionar.',true);return;
   }
   const form=catalogCreationForm();
   form.elements.cycle.value=resolveAGCycle(entry.title_name);
   form.elements.name.value=entry.module_name;
   // Una ficha curricular del centro y una referencia histórica son orígenes
   // distintos; nunca deben adjuntarse a la misma creación por accidente.
   form.elements.reference_course.value='';
   form.elements.reference_code.value='';
   form.dataset.agPickedName='';
   const agPick=form.querySelector('#ag-module-pick');
   if(agPick)agPick.value='';
   form.elements.catalog_entry_id.value=entry.id;
   S.catalogPicked=entry;
   const note=form.querySelector('[data-catalog-selection]');
   if(note)note.textContent='Se utilizará la ficha '+entry.title_code+'/'+entry.module_code+
      '. Los RA/CE y las horas continuarán pendientes de confirmación.';
   toast('Módulo seleccionado del catálogo local; comprueba el grupo antes de crearlo.');return;
 }
 if(action==='catalog-preview'){
   const scope=catalogScopeFromForm();
   const table=$('#catalog-table')?.value||'';
   const result=await busy(()=>API('/api/national/catalog/preview','POST',{table,...scope}));
   if(result){S.catalogTableText=table;S.catalogPreview=result;S.catalogPreviewScope=scope;updateCatalogResults();}return;
 }
 if(action==='catalog-import'){
   const scope=catalogScopeFromForm();
   if(!S.catalogPreview||!S.catalogTableText)return;
   if(S.catalogTableText!==($('#catalog-table')?.value||'') ||
      scope.region!==S.catalogPreviewScope?.region || scope.academic_year!==S.catalogPreviewScope?.academic_year){
     toast('La tabla, comunidad o curso han cambiado desde la vista previa. Vuelve a comprobar las filas.',true);return;
   }
   if(!$('#catalog-confirmed')?.checked){toast('Confirma la procedencia, comunidad y curso de todas las fichas.',true);return;}
   const source_url=$('#catalog-source-url')?.value.trim()||'';
   const source_title=$('#catalog-source-title')?.value.trim()||'';
   if(!source_url||!source_title){toast('Indica el enlace HTTPS y título completo de la disposición.',true);return;}
   if(!confirm('¿Guardar '+S.catalogPreview.count+' fichas para '+scope.region+' · '+scope.academic_year+'? No se sustituirán otras fichas existentes.'))return;
   const result=await busy(()=>API('/api/national/catalog/import','POST',{
     ...scope,table:S.catalogTableText,source_url,source_title,teacher_confirmed:true,replace_existing:false
   }),'Fichas del catálogo guardadas con su fuente.');
   if(result){toast(result.added+' nuevas, '+result.unchanged+' ya existentes.');
     S.catalogPreview=null;S.catalogTableText='';
     S.catalogResults=await API('/api/national/catalog?region='+encodeURIComponent(scope.region)+
        '&academic_year='+encodeURIComponent(scope.academic_year));
     const field=$('#catalog-table');if(field)field.value='';updateCatalogResults();
   }return;
 }
 if(action==='national-table-preview'){
   const text=$('#national-hour-table')?.value.trim()||'';
   if(!text){toast('Pega primero las filas copiadas de Excel o del anexo.',true);return;}
   const result=await busy(()=>API('/api/national/table-preview','POST',{table:text}));
   if(result){S.nationalTablePreview=result;S.nationalTableText=text;
     collectWizardFields();await page('preparar');}
   return;
 }
 if(action==='national-table-import'){
   const preview=S.nationalTablePreview;
   if(!preview)return;
   collectWizardFields();
   const cfg=S.wizardDraft.schedule;
   if(!cfg.hours_source_url||!cfg.hours_source_description){toast('Indica debajo la URL y el nombre de la disposición de la que procede la tabla.',true);return;}
   if(!confirm('Confirmas que las '+preview.count+' filas proceden de la disposición citada y corresponden a este ciclo, comunidad y curso? Se guardarán en la biblioteca de este equipo.'))return;
   const result=await busy(()=>API('/api/national/table-import','POST',{
      module_id:Number(S.moduleId),table:S.nationalTableText,
      source_url:cfg.hours_source_url,source_title:cfg.hours_source_description,
      teacher_confirmed:true,replace_existing:false
   }),'Fichas horarias del ciclo guardadas.');
   if(result){toast('Guardados '+result.records_saved+' registros; '+result.records_unchanged+' existentes respetados.');
     S.nationalTablePreview=null;S.nationalTableText='';S.nationalSources=null;await page('preparar');}
   return;
 }
 if(action==='national-ai-extract-hours'){
   const fragment=$('#national-hours-excerpt')?.value.trim()||'';
   if(!fragment){toast('Copia primero el fragmento del boletín.',true);return;}
   if(!confirm('Se enviará únicamente el fragmento que has copiado a tu proveedor de IA. ¿Lo autorizas?'))return;
   const result=await busy(()=>API('/api/national/extract-hours','POST',{
     module_id:Number(S.moduleId),fragment,authorize_ai:true
   }),'Propuesta extraída. Comprueba la cita literal.');
   if(result){S.nationalHoursPreview=result;
     const panel=$('#national-hours-excerpt')?.closest('details');
     collectWizardFields();await page('preparar');
   }return;
 }
 if(action==='national-ai-apply-hours'){
   const proposal=S.nationalHoursPreview;
   if(!proposal)return;
   if(!confirm('Estas cifras proceden de una propuesta de IA. ¿Aplicarlas como valores todavía pendientes de verificación docente?'))return;
   collectWizardFields();
   const cfg=S.wizardDraft.schedule;
   cfg.total_hours=proposal.total_hours;cfg.weekly_hours=proposal.weekly_hours;
   cfg.hours_confirmed=false;cfg.hours_source_url='';
   cfg.hours_source_description='Propuesta IA basada en un extracto. Falta aportar y comprobar la norma oficial.';
   S.nationalHoursPreview=null;await page('preparar');return;
 }
 if(action==='national-save-hours'){
   collectWizardFields();
   const c=S.wizardDraft?.schedule||{};
   if(!c.hours_confirmed||!c.hours_source_url||!c.hours_source_description){toast('Confirma las horas y escribe la URL y el título de la disposición oficial.',true);return;}
   if(!confirm('Guardar estas horas y su fuente como ficha revisada por ti para el mismo módulo, territorio y curso. ¿Continuar?'))return;
   if(!await saveWizardPage())return;
   const result=await busy(()=>API('/api/national/save-hours','POST',{
     module_id:Number(S.moduleId),teacher_confirmed:true,total_hours:c.total_hours,
     weekly_hours:c.weekly_hours,source_url:c.hours_source_url,source_title:c.hours_source_description
   }),'Ficha horaria guardada con su fuente.');
   if(result){S.nationalSources=null;await page('preparar');}return;
 }

 if(action==='general-calendar-compare'){
   const old=Number(el.dataset.old),newer=Number(el.dataset.new);
   const result=await busy(()=>API('/api/national/general-calendar/compare?module_id='+Number(S.moduleId)+'&old='+old+'&new='+newer));
   if(result){S.generalCalendarDiff=result;collectWizardFields();await page('preparar');}return;
 }
 if(action==='general-calendar-apply'){
   collectWizardFields();
   const data=S.generalCalendarLibrary,yr=S.prepareInfo?.module?.academic_year;
   if(!data||data.territory!==S.wizardDraft?.region||data.academic_year!==yr){
     toast('Las fechas disponibles corresponden a otra comunidad o curso.',true);return;}
   const found=(data.versions||[]).find(v=>Number(v.id)===Number(el.dataset.id));
   if(!found)return;
   if(!confirm('Cargar las fechas generales de esta revisión como BORRADOR. Mantendrá horario, evaluaciones, municipio, isla y días adicionales, pero debe comprobar de nuevo sus fiestas locales e insulares. No modifica notas, RA/CE ni FEOE. ¿Continuar?'))return;
   const next={...S.wizardDraft.schedule};
   const fields=['start_date','end_date','vacation_periods','regional_non_teaching_days','calendar_source_url',
     'calendar_source_description','calendar_correction_urls','calendar_academic_year'];
   for(const key of fields)next[key]=JSON.parse(JSON.stringify(found.schedule[key]));
   if(next.start_date&&next.end_date&&next.start_date>=next.end_date){
     toast('Las fechas de inicio y fin no son compatibles.',true);return;}
   next.calendar_profile_id='';next.calendar_confirmed=false;
   S.wizardDraft.schedule=next;S.generalCalendarDiff=null;
   toast('Calendario general cargado sin confirmar. Verifica fiestas locales/insulares y PGA del centro.');
   await page('preparar');return;
 }
 if(action==='general-calendar-save'){
   collectWizardFields();
   const cfg=S.wizardDraft?.schedule||{};
   if(!$('#general-calendar-scope-confirm')?.checked){
     toast('Confirma que las fechas generales no incluyen fiestas de isla, municipio o centro.',true);return;}
   if(!cfg.calendar_confirmed||!cfg.calendar_source_url||!cfg.calendar_source_description){
     toast('Guarda y confirma antes el calendario y la disposición principal.',true);return;}
   if(!confirm('Archivar una referencia de calendario general para este territorio y curso, excluyendo cualquier campo de centro o horario. No se declarará verificación jurídica automática. ¿Continuar?'))return;
   if(!await saveWizardPage())return;
   const result=await busy(()=>API('/api/national/general-calendar/save','POST',{
      module_id:Number(S.moduleId),teacher_confirmed:true,general_scope_confirmed:true
   }),'Referencia general archivada en la biblioteca local.');
   if(result){S.generalCalendarLibrary=null;S.generalCalendarDiff=null;
     toast(result.record?.unchanged?'La última revisión ya tenía estas fechas.':
       'Calendario general guardado como revisión n.º '+result.record?.revision+'.');
     await page('preparar');}return;
 }

 if(action==='calendar-compare'){
   const old=Number(el.dataset.old),newer=Number(el.dataset.new);
   const result=await busy(()=>API('/api/national/calendar/compare?module_id='+Number(S.moduleId)+'&old='+old+'&new='+newer));
   if(result){S.calendarVersionDiff=result;collectWizardFields();await page('preparar');}return;
 }
 if(action==='calendar-load-version'){
   const stored=S.calendarVersions;
   const version=(stored?.versions||[]).find(v=>Number(v.id)===Number(el.dataset.id));
   if(!version)return;
   collectWizardFields();
   const c=S.wizardDraft?.schedule||{};
   const valid=stored.territory===S.wizardDraft.region&&stored.academic_year===S.prepareInfo?.module?.academic_year&&
     stored.center===S.wizardDraft.center&&stored.municipality===(c.municipality||'')&&stored.island===(c.island||'');
   if(!valid){toast('La ficha corresponde a otro centro, municipio, isla, curso o comunidad.',true);return;}
   if(!confirm('Cargar la versión '+version.revision+' como propuesta editable. El calendario quedará SIN confirmar y no alterará horas, FEOE, unidades ni notas. ¿Continuar?'))return;
   const keys=['region','island','municipality','start_date','end_date','evaluation_ends','vacation_periods',
     'regional_non_teaching_days','extra_non_teaching_days','calendar_profile_id','calendar_academic_year',
     'calendar_source_url','calendar_source_description','calendar_correction_urls'];
   for(const key of keys)if(Object.hasOwn(version.schedule,key))c[key]=JSON.parse(JSON.stringify(version.schedule[key]));
   c.calendar_confirmed=false;S.wizardDraft.schedule=c;S.calendarVersionDiff=null;
   toast('Versión cargada para revisión docente. Debes confirmar las fechas y el centro.');await page('preparar');return;
 }
 if(action==='national-save-calendar'){
   collectWizardFields();
   const c=S.wizardDraft?.schedule||{};
   if(!c.calendar_confirmed||!c.calendar_source_url||!S.wizardDraft.center){toast('Antes de guardar confirma el calendario, identifica su fuente y escribe el centro en el paso 1.',true);return;}
   if(!confirm('Guardar calendario, festivos y evaluaciones para este centro, territorio y curso. ¿Continuar?'))return;
   if(!await saveWizardPage())return;
   const result=await busy(()=>API('/api/national/save-calendar','POST',{
     module_id:Number(S.moduleId),teacher_confirmed:true
   }),'Calendario del centro guardado.');
   if(result){S.nationalSources=null;S.calendarVersions=null;S.calendarVersionDiff=null;
     toast(result.record?.revision?.unchanged?'Esta ficha coincide con la última versión.':'Calendario archivado como nueva versión '+result.record?.revision?.revision+'.');
     await page('preparar');}return;
 }
 if(action==='national-apply-calendar'){
   const saved=S.nationalSources?.calendar_record;
   if(!saved)return;
   if(!confirm('La ficha guardada sustituirá las fechas y festivos de este módulo. No modificará horas, unidades ni FEOE. ¿Aplicar?'))return;
   collectWizardFields();
   Object.assign(S.wizardDraft.schedule,JSON.parse(JSON.stringify(saved.schedule)));
   S.wizardDraft.schedule.calendar_confirmed=false;
   toast('Fechas cargadas: debes confirmarlas para este módulo.');
   await page('preparar');return;
 }
 if(action==='retry-page'){await page(S.page);return;}
 if(action==='prepare-new-module'){S.creatingModule=true;S.preparePath=null;await page('preparar');return;}
 if(action==='prepare-select-path'){
   S.preparePath=el.dataset.path;S.prepareStep=0;S.proposal=null;S.unitProposal=null;
   if(S.wizardDraft)S.wizardDraft.source_type=S.preparePath;
   await page('preparar');return;
 }
 if(action==='prepare-overview'){S.preparePath=null;await page('preparar');return;}
 if(action==='prepare-discard-proposal'){S.proposal=null;await page('preparar');return;}
 if(action==='review-all-program'){
   const result=await busy(()=>API('/api/programmings/'+id+'/import-preview'));
   if(result){S.importPreview=result;S.proposal=null;S.preparePath='import';await page('preparar');}return;
 }
 if(action==='discard-import-preview'){
   S.importPreview=null;await page('preparar');return;
 }
 if(action==='guided-analyze'){
   if(!confirm('Se enviará el texto de la programación al proveedor de IA configurado. No incluya datos personales innecesarios. ¿Autoriza el análisis?'))return;
   const result=await busy(()=>API('/api/programmings/analyze','POST',{programming_id:id}));
   if(result){S.proposal=result;await page('preparar');}return;
 }
 if(action==='scope-find-origins'){
   const form=el.closest('form'),target=form.querySelector('#scope-origin-results'),mid=Number(S.moduleId),sid=Number(form.elements.student_id.value);
   const result=await busy(()=>API('/api/common-scopes/recovery-origins?module_id='+mid+'&student_id='+sid));
   if(!result||!target.isConnected||Number(S.moduleId)!==mid||Number(form.elements.student_id.value)!==sid)return;
   target.innerHTML=result.origins.length?`<label>Materia de origen</label><select name="origin">${result.origins.map(o=>`<option value="${Number(o.module_id)}|${Number(o.student_id)}|${Number(o.decision_id)}">${E(o.name)} · ${E(o.academic_year)} · ${E(o.group)}</option>`).join('')}</select>${result.origins.map(o=>`<details><summary>Criterios de ${E(o.name)} · ${E(o.group)}</summary><ul>${o.criteria.map(c=>`<li>${E(c.code)} · ${E(c.description)}</li>`).join('')}</ul></details>`).join('')}`:empty('No hay un acuerdo extraordinario insuficiente vigente y verificable del curso anterior.');
   return;
 }
 if(action==='scope-open-consolidation'){
   S.scopeConsolidationModule=Number(S.moduleId);S.scopeSession='ordinaria';
   try{await page('preparar');}catch(ex){S.scopeConsolidationModule=null;throw ex;}return;
 }
 if(action==='scope-back-notebook'){S.scopeConsolidationModule=null;await page('preparar');return;}
 if(action==='scope-open-notebook'){
   if(!confirm('Abre el cuaderno con el currículo guardado. Los cambios del formulario que no hayas guardado se descartarán. ¿Continuar?'))return;
   S.scopeNotebookModule=Number(S.moduleId);await page('preparar');return;
 }
 if(action==='scope-edit-curriculum'){
   S.scopeNotebookModule=null;S.scopeConsolidationModule=null;await page('preparar');return;
 }
 if(action==='scope-official'){
   if(!confirm('Se descargará el PDF institucional del anexo 1. ¿Autoriza la consulta?'))return;
   const mid=Number(S.moduleId),target=$('#scope-official-preview');
   const result=await busy(()=>API('/api/common-scopes/official','POST',{module_id:mid,authorize_official_query:true}));
   if(!result||Number(S.moduleId)!==mid||$('#scope-official-preview')!==target)return;
   S.commonScopeReference={mid,result};
   target.innerHTML=`<p class="hint warning">${E(result.notice)}</p><p class="small">${E(result.consulted_at)} · SHA-256 ${E(result.source_sha256)}</p>`+
     result.competencies.map(c=>`<details><summary>Competencia ${E(c.code)} · ${c.criteria.length} criterios</summary><p>${E(c.description)}</p><p class="small">${E(c.descriptors)}</p><ul>${c.criteria.map(ce=>`<li>${E(ce.code)}. ${E(ce.description)} <small>${E(ce.descriptors)}</small></li>`).join('')}</ul><button class="btn secondary smallbtn" type="button" data-action="scope-copy-competency" data-code="${E(c.code)}">Añadir al borrador sin guardar</button></details>`).join('')+
     `<details><summary>Saberes básicos del ámbito · referencia completa</summary><textarea rows="12" readonly>${E(result.saberes_reference)}</textarea></details>`;
   return;
 }
 if(action==='scope-copy-competency'){
   const ref=S.commonScopeReference;
   if(!ref||ref.mid!==Number(S.moduleId))return;
   const c=ref.result.competencies.find(x=>x.code===el.dataset.code);
   const block=Array.from(document.querySelectorAll('.scope-competency')).find(x=>x.dataset.code===el.dataset.code);
   if(!c||!block)return;
   if(Array.from(block.querySelectorAll('textarea,input')).some(x=>x.value.trim())){toast('La competencia contiene datos; no se sobrescribe. Revísala manualmente.',true);return;}
   block.querySelector('[name=scope-description]').value=c.description;
   block.querySelector('[name=scope-descriptors]').value=c.descriptors;
   block.querySelector('[name=scope-criteria]').value=c.criteria.map(x=>[x.code,x.description,x.descriptors].join(' | ')).join('\n');
   block.closest('details').open=true;
   const checked=$('#common-scope-draft [name=teacher_reviewed]');if(checked)checked.checked=false;
   toast('Competencia añadida al formulario. Revisa y guarda el borrador.');return;
 }
 if(action==='guided-boc'){
   if(!confirm('Se consultará el BOC de Canarias. Contraste el PDF firmado y revise los RA y CE antes de guardarlos. ¿Continuar?'))return;
   const result=await busy(()=>API('/api/curriculum/official','POST',{
     module_id:Number(S.moduleId),source_kind:'BOC',authorize_official_query:true}));
   if(result){S.proposal=result;S.preparePath='create';await page('preparar');}return;
 }
 if(action==='guided-boe'){
   const boe=$('#guide-boe')?.value.trim();
   if(!confirm('Se consultará la disposición del BOE seleccionada. Revise la correspondencia con el módulo y la normativa autonómica. ¿Continuar?'))return;
   const result=await busy(()=>API('/api/curriculum/official','POST',{
     module_id:Number(S.moduleId),boe_id:boe||null,authorize_official_query:true}));
   if(result){S.proposal=result;S.preparePath='create';await page('preparar');}return;
 }
 if(action==='prepare-wizard-back'){
   const ok=await saveWizardPage();if(ok){S.prepareStep=Math.max(0,S.prepareStep-1);await page('preparar');}return;
 }
 if(action==='prepare-wizard-open'){
   S.preparePath='create';S.prepareStep=0;await page('preparar');return;
 }
 if(action==='prepare-ai-local'||action==='prepare-ai-all'){
   collectWizardFields();
   const useAi=action==='prepare-ai-all';
   if(useAi&&!confirm('Se enviarán al proveedor de IA configurado el nombre del módulo, el ciclo y sus RA/CE confirmados. No se enviará el nombre del centro ni datos personales. ¿Autoriza generar las propuestas?'))return;
   const result=await busy(()=>API('/api/programming-builder/propose','POST',{
      module_id:Number(S.moduleId),region:S.wizardDraft.region||'Canarias',mode:useAi?'ai':'base',authorize_ai:useAi}));
   if(result){const stats=applyAssistantFields(result,useAi?'ai':'base');
     toast(`${stats.applied} apartados completados · ${stats.skipped} conservados. Puedes editar todo.`);
     await page('preparar');}return;
 }
 if(action==='prepare-ai-improve'){
   collectWizardFields();
   const field=el.dataset.field;const value=String(S.wizardDraft[field]||'');
   if(!value.trim()){toast('Escribe primero algún texto en este apartado.',true);return;}
   if(!confirm('Se enviará este texto al proveedor de IA configurado para mejorarlo. Evita incluir datos personales del alumnado. Tu redacción NO se sustituirá sin confirmación. ¿Autorizar?'))return;
   const result=await busy(()=>API('/api/programming-builder/improve','POST',{
      module_id:Number(S.moduleId),field,text:value,authorize_ai:true}));
   if(result){S.aiPreview=result;await page('preparar');}return;
 }
 if(action==='guide-ai-discard'){S.aiPreview=null;await page('preparar');return;}
 if(action==='guide-ai-accept'){
   collectWizardFields();const text=$('#guide-ai-proposal')?.value.trim();
   if(!text){toast('La propuesta de texto está vacía.',true);return;}
   const key=S.aiPreview?.field;
   if(!key||!WD_FIELDS.includes(key))return;
   S.wizardDraft[key]=text;
   S.wizardDraft.assistant_meta=S.wizardDraft.assistant_meta||{};
   S.wizardDraft.assistant_meta[key]={origin:'IA revisada y aceptada por docente',teacher_edited:true};
   S.aiPreview=null;await page('preparar');toast('Redacción aceptada. No se ha alterado el currículo ni los pesos.');return;
 }
 if(action==='prepare-propose-units'){
   collectWizardFields();
   if(S.wizardDraft.units?.length&&!confirm('Se sustituirá la distribución actual de unidades. ¿Continuar?'))return;
   const result=await busy(()=>API('/api/programming-builder/propose-units','POST',{
       module_id:Number(S.moduleId),schedule:S.wizardDraft.schedule,region:S.wizardDraft.region||'Canarias'}));
   if(result){S.wizardDraft.units=result.units;toast('Unidades calculadas según las horas reales indicadas y los CE del currículo.');await page('preparar');}
   return;
 }
 if(action==='prepare-manual-units'){
   collectWizardFields();
   const n=Number($('#guide-unit-count')?.value||0);
   if(!Number.isInteger(n)||n<1||n>100)return toast('Indica un número entre 1 y 100 unidades.',true);
   if(S.wizardDraft.units.length&&!confirm('Se sustituirá la cuadrícula actual de unidades; el currículo no se modificará. ¿Continuar?'))return;
   S.wizardDraft.units_mode='manual';
   S.wizardDraft.units=Array.from({length:n},(_,i)=>({code:'UD'+String(i+1).padStart(2,'0'),
       title:'Unidad didáctica por definir',term:Math.min(3,1+Math.floor(i*3/n)),hours:1,
       criteria_codes:[],instruments:'',resources:''}));
   await page('preparar');toast('Cuadrícula creada. Asigna todos los CE y horas antes de finalizar.');return;
 }
 if(action==='guide-save-weights'){
   collectWizardFields();
   const automatic=Boolean($('#guide-automatic-weights')?.checked);
   if(!confirm(automatic?'¿Aplicar el reparto igualitario por CE y recalcular todos los pesos automáticos? Si ya hay pesos del departamento, se sustituirán.':'¿Guardar las ponderaciones personalizadas de todos los RA y CE? Las sumas deben ser exactamente 100,00 %.'))return;
   const info=S.prepareInfo||{};
   const rows=(info.outcomes||[]).map(ra=>({id:Number(ra.id),weight:Number($(`[data-weight-ra="${ra.id}"]`)?.value),
     criteria:(info.criteria||[]).filter(c=>Number(c.outcome_id)===Number(ra.id))
         .map(c=>({id:Number(c.id),weight:Number($(`[data-weight-ce="${c.id}"]`)?.value)}))}));
   const result=await busy(()=>API('/api/programming-builder/weights','POST',{module_id:Number(S.moduleId),
      mode:automatic?'automatic':'manual',rows,teacher_confirmed:true}),'Ponderaciones actualizadas tras validación.');
   if(result)await page('preparar');return;
 }
 if(action==='prepare-enrich-units'){
   collectWizardFields();const units=S.wizardDraft.units||[];
   if(!units.length)return toast('Crea primero las unidades y sus CE asociados.',true);
   if(!confirm('Se enviarán a tu proveedor de IA los títulos y CE asociados a las unidades, sin datos personales. ¿Autorizas este envío?'))return;
   const result=await busy(()=>API('/api/programming-builder/enrich-units','POST',{
     module_id:Number(S.moduleId),units,authorize_ai:true}));
   if(result){S.unitProposal=result;await page('preparar');}return;
 }
 if(action==='prepare-dismiss-unit-ai'){S.unitProposal=null;await page('preparar');return;}
 if(action==='prepare-accept-unit-ai'){
   collectWizardFields();
   let changed=0;
   for(const proposal of S.unitProposal?.units||[]){
     const found=(S.wizardDraft.units||[]).find(x=>x.code===proposal.code);
     if(!found)continue;
     for(const field of ['instruments','resources']){
       const text=String(found[field]||'');
       if(!text.trim()||text.includes('(propuesta revisable)')||text.includes('(adaptar al centro)')){
         found[field]=proposal[field];changed++;
       }
     }
   }
   S.unitProposal=null;await page('preparar');
   toast(`Se han incorporado ${changed} campos. Los textos ya personalizados se han conservado.`);return;
 }
 if(action==='feoe-minimum-preview'||action==='feoe-minimum-ai'){
   if(action==='feoe-minimum-ai'&&!confirm('Se enviarán los RA y CE seleccionados a tu proveedor de IA. No se enviarán datos del alumnado o de la empresa. ¿Autorizar y continuar?'))return;
   const ok=await saveWizardPage();if(!ok)return;
   const result=await busy(()=>action==='feoe-minimum-ai'
       ?API('/api/programming-builder/feoe-minimum/ai','POST',{module_id:Number(S.moduleId),authorize_ai:true})
       :API('/api/programming-builder/'+Number(S.moduleId)+'/feoe-minimum'));
   if(result){S.feoeMinimumPreview=result;await page('preparar');}return;
 }
 if(action==='feoe-minimum-discard'){S.feoeMinimumPreview=null;await page('preparar');return;}
 if(action==='feoe-minimum-accept'){
   if(!$('#feoe-minimum-confirm')?.checked)return toast('Confirma que has revisado los criterios y las tareas.',true);
   collectFeoeMinimumFields();
   const result=await busy(()=>API('/api/programming-builder/feoe-minimum/accept','POST',{
     module_id:Number(S.moduleId),teacher_confirmed:true,
     rows:S.feoeMinimumPreview.rows.map(r=>({criteria_code:r.criteria_code,
       activity:r.activity,evidence:r.evidence,support:r.support,assessment_role:r.assessment_role}))
   }),'Propuesta FEOE revisada y guardada.');
   if(result){S.wizardDraft=null;S.feoeMinimumPreview=null;await page('preparar');}
   return;
 }
 if(action==='prepare-propose-feoe'){
   collectWizardFields();const ce=S.prepareInfo.criteria||[];
   if(!ce.length)return toast('No existen CE confirmados.',true);
   if(S.wizardDraft.schedule.feoe_criteria_codes.length&&!confirm('Se sustituirán las marcas FEOE actuales. ¿Continuar?'))return;
   const n=ce.length,p=Number(S.wizardDraft.schedule.feoe_target_percent||15);
   let count=Math.max(1,Math.round(n*p/100));
   const low=Math.ceil(n*.10),high=Math.floor(n*.20);
   if(low<=high)count=Math.min(high,Math.max(low,count));
   const selected=[];const used=new Set();
   // Primero se diversifica la selección entre RA; después, se completan los cupos.
   for(const x of ce){if(!used.has(x.ra_code)&&selected.length<count){selected.push(x.code);used.add(x.ra_code);}}
   for(const x of ce){if(selected.length>=count)break;if(!selected.includes(x.code))selected.push(x.code);}
   S.wizardDraft.schedule.feoe_criteria_codes=selected;
   toast('Propuesta FEOE preparada. Verifica que responde al plan de formación acordado.');
   await page('preparar');return;
 }
 if(action==='prepare-add-activity'){
   collectWizardFields();S.wizardDraft.activities=S.wizardDraft.activities||[];
   S.wizardDraft.activities.push({type:'complementaria',title:'Visita didáctica a empresa del sector (propuesta, pendiente de autorización)',date:'',unit_code:'',
      description:'Observación y análisis de procesos profesionales vinculados con los RA y CE del módulo.',resources:'Autorizaciones, coordinación con la entidad, transporte si procede.'});
   await page('preparar');return;
 }
 if(action==='prepare-remove-activity'){
   collectWizardFields();S.wizardDraft.activities.splice(index,1);await page('preparar');return;
 }
 if(action==='prepare-add-unit'){
   collectWizardFields();
   const used=new Set((S.wizardDraft.units||[]).map(u=>String(u.code||'').toUpperCase()));
   let n=1;
   while(used.has('UD'+String(n).padStart(2,'0')))n++;
   S.wizardDraft.units.push({code:'UD'+String(n).padStart(2,'0'),title:'Nueva unidad',term:1,hours:1,criteria_codes:[],instruments:'Prueba práctica y portafolio (propuesta editable)',resources:'Aula con equipamiento informático y materiales didácticos (adaptar al centro)'});
   await page('preparar');return;
 }
 if(action==='prepare-remove-unit'){
   collectWizardFields();S.wizardDraft.units.splice(index,1);await page('preparar');return;
 }
 if(action==='prepare-finish'){
   collectWizardFields();
   const result=await busy(()=>API('/api/programming-builder/save','POST',{
     module_id:Number(S.moduleId),draft:S.wizardDraft}),'Borrador guardado.');
   if(result)await page('preparar');return;
 }
 if(action==='lock-api'){
  const result=await busy(()=>API('/api/settings/lock','POST',{}),'Clave API bloqueada.');if(result)await page('ajustes');return;
 }
 if(action==='eval-close'){
   const reason=prompt('Escriba la justificación docente del cierre de esta nota final (mínimo 10 caracteres):',
                       'Calificación final revisada de acuerdo con las evidencias, RA, CE y ponderaciones validadas.');
   if(reason===null)return;
   const result=await busy(()=>API('/api/evaluation/close','POST',{module_id:S.evaluationModuleId,
                         student_id:id,justification:reason}),'Calificación final cerrada y registrada.');
   if(result)await page('evaluacion');return;
 }
 if(action==='eval-save-score'){
   const student=Number(el.dataset.student),criterion=Number(el.dataset.criterion),instrument=Number(el.dataset.instrument);
   const field=document.querySelector(`input.eval-score-input[data-student="${student}"][data-criterion="${criterion}"]`);
   if(!field||field.value===''){toast('Introduzca una nota entre 0 y 10.',true);return;}
   const comment=prompt('Comentario justificativo de la calificación (opcional):','');if(comment===null)return;
   const result=await busy(()=>API('/api/evaluation/score','POST',{student_id:student,criterion_id:criterion,
                      instrument_id:instrument,score:Number(field.value),comment}),'Nota registrada.');
   if(result)await page('evaluacion');return;
 }
 if(action==='sync-eval-exam'){
  if(!confirm('Se incorporarán únicamente las correcciones ya validadas por el docente. ¿Continuar?'))return;
  const result=await busy(()=>API('/api/evaluation/sync-exam','POST',{instrument_id:id}),'Notas de examen sincronizadas.');
  if(result){toast('Importadas '+result.imported+' evidencias, omitidas '+result.skipped+'.');await page('evaluacion');}return;
 }
 if(action==='download-eval-template'){
  const ins=S.evalData.instruments.find(i=>i.id===Number(S.evalInstrumentId));
  if(!ins)return;
  const csv='\ufeffcodigo_alumno;criterio;nota;comentario\r\n'+S.evalData.students.flatMap(st=>ins.targets.map(t=>{
    const c=S.evalData.criteria.find(c=>c.id===t.criterion_id);
    const quote=v=>'"'+String(v??'').replace(/"/g,'""')+'"';
    return [quote(st.code),quote(c.ra_code+'/'+c.code),'',''].join(';');
  })).join('\r\n');
  downloadText(csv,'plantilla_notas_'+ins.id+'.csv','text/csv;charset=utf-8');return;
 }
 if(action==='export-evaluation'){
  const rows=[['Código','Alumno/a','1ª evaluación','2ª evaluación','3ª evaluación','Calificación global calculable','Estado']];
  for(const st of S.evalData.students)rows.push([st.code,st.name,...st.terms.map(t=>t.score??''),st.final_score??'',st.status]);
  downloadText('\ufeff'+rows.map(r=>r.map(v=>'"'+String(v).replace(/"/g,'""')+'"').join(';')).join('\r\n'),
     'evaluacion_modulo_'+S.evaluationModuleId+'.csv','text/csv;charset=utf-8');return;
 }
 if(action==='view-bank'){
   const info=await API('/api/exam-batches/'+id);
   const content=info.questions.map((q,i)=>`${i+1}. [${q.criterion_code} · ${q.kind}${q.assigned_variant?' · Modelo '+q.assigned_variant:' · Reserva'}] ${q.prompt}`).join('\n\n');
   const blob=new Blob([`BANCO DE PREGUNTAS · ${info.batch.title}\nDificultad: ${info.batch.difficulty}\nModelos: ${info.batch.model_count}\nTotal: ${info.batch.bank_size}\n\n`+content],{type:'text/plain;charset=utf-8'});
   const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`Banco_EvaluaFP_${id}.txt`;a.click();setTimeout(()=>URL.revokeObjectURL(url),5000);
   toast('Banco exportado con preguntas asignadas y de reserva.');return;
 }
 if(action==='export-gradebook'){
   const rows=[['Curso','Módulo','Código','Alumno/a','Examen','Estado','Nota 0-10']];
   for(const r of (S.gradebook?.exams||[]))rows.push([r.academic_year,r.module_name,r.student_code,r.student_name,r.exam_title,r.status,r.out_of_ten??'']);
   rows.push([]);rows.push(['Desglose por criterios']);rows.push(['Módulo','Código','Alumno/a','RA','CE','Puntos logrados','Puntos máximos']);
   for(const r of (S.gradebook?.criteria||[]))rows.push([r.module_name,r.student_code,r.student_name,r.outcome_code,r.criterion_code,r.scored,r.maximum]);
   const csv='\ufeff'+rows.map(row=>row.map(cell=>'"'+String(cell??'').replace(/"/g,'""')+'"').join(';')).join('\r\n');
   const blob=new Blob([csv],{type:'text/csv;charset=utf-8'});const url=URL.createObjectURL(blob);
   const a=document.createElement('a');a.href=url;a.download='evaluafp_registro_evaluaciones.csv';a.click();URL.revokeObjectURL(url);return;
 }
 if(action==='create-upload-student'){
   const created=await promptNewStudents(Number(el.dataset.moduleId));
   if(created?.length){S.uploadStudentId=created[0].id;toast('Alumno registrado correctamente.');await page('entregas');}
   return;
 }
 if(action==='open-sub'){S.subId=id;S.pageIndex=0;await page('correcciones');return;}
 if(action==='open-exam'){S.examId=id;await page('examenes');return;}
 if(action==='select-page'){S.pageIndex=index;await page('correcciones');return;}
 if(action==='queue-up'||action==='queue-down'||action==='queue-remove'){
   if(action==='queue-remove')S.queue.splice(index,1);
   else{const j=index+(action==='queue-up'?-1:1);[S.queue[index],S.queue[j]]=[S.queue[j],S.queue[index]];}
   await page('entregas');return;}
 if(action==='toggle-material'){
   const active=el.dataset.active==='1';
   if(active&&!confirm('Desactivar este material permitirá generar exámenes sin utilizarlo. ¿Confirmar?'))return;
   const result=await busy(()=>API('/api/materials/active','POST',{module_id:S.moduleId,material_id:id,active:!active}),'Estado del material actualizado.');
   if(result)await page('programaciones');return;}
 if(action==='discard-proposal'){S.proposal=null;await page('programaciones');return;}
 if(action==='manual-official'){
   const form=$('#manual-exam');if(!form)return;
   const moduleId=Number(form.elements.module_id.value);
   const boeId=prompt('Identificador del BOE que contiene el currículo (en blanco si el módulo específico del ciclo está indexado):','');
   if(boeId===null)return;
   if(!confirm('Se consultará el BOE para obtener RA y CE oficiales. No se enviarán exámenes ni datos del alumnado. ¿Continuar?'))return;
   const result=await busy(()=>API('/api/curriculum/official','POST',{
      module_id:moduleId,boe_id:boeId||null,authorize_official_query:true}));
   if(result){
     S.manualDraft={module_id:moduleId,title:form.elements.title.value,
       questions_json:form.elements.questions_json.value};
     S.moduleId=moduleId;S.examModuleId=moduleId;S.proposal=result;
     await page('programaciones');toast('Revise y confirme el currículo. Las preguntas manuales permanecerán en borrador.');
   }
   return;
 }
 if(action==='manual-align'){
   const form=$('#manual-exam');if(!form)return;
   let qs;
   try{qs=JSON.parse(form.elements.questions_json.value);if(!Array.isArray(qs))throw Error('Se requiere una lista JSON de preguntas.');}
   catch(ex){toast('Revise primero el JSON de preguntas: '+ex.message,true);return;}
   const moduleId=Number(form.elements.module_id.value);
   const catalogue=await busy(()=>API('/api/modules/'+moduleId));
   if(!catalogue)return;
   if(!catalogue.criteria?.length){
     toast('Este módulo aún no tiene CE. Consulte primero el currículo oficial o la programación.',true);
     $('#manual-curriculum-result').innerHTML='No hay criterios validados para clasificar las preguntas. <button type="button" class="btn secondary" data-action="manual-official">Consultar el currículo oficial en el BOE</button>';
     return;
   }
   if(!confirm('Se enviarán los enunciados y las descripciones de RA/CE al proveedor de IA elegido. No se enviarán datos de alumnos. ¿Autorizar este análisis?'))return;
   toast('Comparando las preguntas con los RA y CE confirmados.');
   const result=await busy(()=>API('/api/exams/manual/classify','POST',{module_id:Number(form.elements.module_id.value),questions:qs}));
   if(!result)return;
   const entries=[];
   for(const assign of result.assignments){
     const q=qs[assign.number-1];
     if(assign.criteria?.length){
       q.criteria_allocations=assign.criteria.map(a=>({criterion_id:a.criterion_id,weight_pct:a.weight_pct,confidence:a.confidence,rationale:a.rationale}));
       delete q.criterion_id;
       entries.push('<strong>Pregunta '+assign.number+'</strong>: '+assign.criteria.map(a=>E(a.ra_code)+' / '+E(a.criterion_code)+' ('+E(a.weight_pct)+' %) — '+E(a.rationale)).join('; '));
     }else{
       delete q.criteria_allocations;delete q.criterion_id;
       entries.push('<strong>Pregunta '+assign.number+'</strong>: <b>pendiente de asignación docente</b>');
     }
   }
   form.elements.questions_json.value=JSON.stringify(qs,null,2);
   const warnings=(result.warnings||[]).map(w=>'<li>'+E(w)+'</li>').join('');
   $('#manual-curriculum-result').innerHTML='<strong>Propuesta curricular con '+E(result.model)+'</strong><div>'+entries.map(e=>'<p>'+e+'</p>').join('')+'</div>'+(warnings?'<ul>'+warnings+'</ul>':'')+
      '<p>Los datos se han incorporado al JSON para que pueda modificarlos. Compruebe que los porcentajes suman 100 % y confirme antes de guardar.</p>'+
      (result.needs_review?'<button type="button" class="btn secondary" data-action="manual-official">Consultar el currículo oficial para completar CE</button>':'');
   $('#manual-confirm').checked=false;
   toast(result.needs_review?result.needs_review+' preguntas sin correspondencia clara: revise manualmente.':'Propuestas incorporadas. Revise y confirme antes de guardar.');
   return;
 }
 if(action==='official-curriculum'){
   const raw=$('#official-boe-id')?.value.trim();
   if(!confirm('Se consultará únicamente la normativa oficial del BOE, sin enviar datos personales ni exámenes. La propuesta requiere revisión docente. ¿Continuar?'))return;
   toast('Consultando el texto oficial y extrayendo RA y CE sin ponderaciones.');
   const result=await busy(()=>API('/api/curriculum/official','POST',{
      module_id:Number(S.moduleId),boe_id:raw||null,authorize_official_query:true}));
   if(result){S.proposal=result;await page('programaciones');}
   return;
 }
 if(action==='analyze-program'){
  toast('Analizando la programación. Verifique después los pesos propuestos.');
  const result=await busy(()=>API('/api/programmings/analyze','POST',{programming_id:id}),'RA y CE extraídos: pendiente de confirmación.');
  if(result){S.proposal=result;await page('programaciones');}return;}
 if(action==='edit-outcome'||action==='edit-criterion'){
   const isRa=action==='edit-outcome';
   const r=(isRa?S.moduleDetails.outcomes:S.moduleDetails.criteria).find(x=>x.id===id);
   const code=prompt('Código:',r.code);if(code===null)return;
   const description=prompt('Descripción:',r.description);if(description===null)return;
   const weight=prompt('Ponderación (%) — en blanco para peso automático:',r.weight??'');if(weight===null)return;
   const body={id,code,description,weight};
   if(isRa)body.module_id=S.moduleId;else body.outcome_id=r.outcome_id;
   const result=await busy(()=>API('/api/'+(isRa?'outcomes':'criteria'),'POST',body),'Ponderación y criterio guardados.');
   if(result)await page('programaciones');return;}
 if(action==='transcribe'||action==='grade'){
    if(!confirm('Se enviarán '+(action==='transcribe'?'las páginas escaneadas':'las respuestas transcritas')+' al proveedor de IA configurado. Confirme que el centro ha autorizado este tratamiento y que el proveedor es adecuado. ¿Continuar?'))return;
    if(action==='transcribe' && S.subDetails?.submission?.current_run_id && !confirm('Se creará una nueva transcripción y se invalidará la revisión actual. ¿Continuar?'))return;
    if(action==='grade' && S.subDetails?.submission?.status==='validated' && !confirm('Se perderán las validaciones actuales y se generarán nuevas propuestas. ¿Continuar?'))return;
    toast(action==='transcribe'?'Analizando imágenes en orden, con continuidad de respuestas.':'Corrigiendo cada pregunta con la rúbrica.');
    const result=await busy(()=>API('/api/submissions/'+(action==='transcribe'?'transcribe':'correct'),'POST',
      {submission_id:id,authorize_external_transfer:true}),action==='transcribe'?'Transcripción completa.':'Propuestas de calificación generadas.');
    if(result)await page('correcciones');return;}
 if(action==='show-audit'){
   const list=await busy(()=>API('/api/audit/'+id));
   if(!list)return;
   const holder=$('#audit-info');
   holder.innerHTML=`<h3>Historial de operaciones</h3><div class="itemlist">${list.map(a=>`<div class="item"><div><b>${E(a.action)}</b><div class="small">${E(a.at)} · ${E(a.entity)} #${E(a.entity_id)}</div><details><summary class="small">Detalles</summary><pre class="small">${E(a.details_json)}</pre></details></div></div>`).join('')}</div>`;
   return;}
 } catch(error){if(error?.message?.includes('canceló al cambiar de pantalla'))return;console.error(error);toast(error?.message||'Error al realizar la acción.',true);}
});
startIntro();
page('inicio');
