'use strict';
const shots={
 programaciones:['assets/screenshots/programaciones.webp','Importa la programación, comprueba RA/CE y vincula materiales de consulta.'],
 examenes:['assets/screenshots/examenes.webp','Diseña modelos A–F con rúbricas, problemas y exportación PDF.'],
 correcciones:['assets/screenshots/correcciones.webp','Consulta los originales en pantalla y revisa la corrección asistida por IA.'],
 evaluacion:['assets/screenshots/evaluacion.webp','Registra evidencias, pondera resultados y criterios y prepara la exportación.']
};
const shotImg=document.getElementById('screen-image');
const cap=document.getElementById('screen-caption');
for(const button of document.querySelectorAll('.screen-tab')){
 button.addEventListener('click',()=>{
  document.querySelectorAll('.screen-tab').forEach(b=>{b.classList.toggle('active',b===button);b.setAttribute('aria-selected',String(b===button))});
  const id=button.dataset.shot;shotImg.src=shots[id][0];shotImg.alt='Captura real de '+button.textContent.trim()+' con datos ficticios de demostración';cap.textContent=shots[id][1];
 });
}
const dlg=document.getElementById('lightbox');
document.getElementById('zoom-shot')?.addEventListener('click',()=>{document.getElementById('lightbox-image').src=shotImg.src;document.getElementById('lightbox-caption').textContent=cap.textContent;dlg.showModal()});
dlg?.addEventListener('click',event=>{if(event.target===dlg)dlg.close()});
function updateWeights(){const a=Math.max(1,Math.min(30,Number(document.getElementById('count-ra1').value)||1));const b=Math.max(1,Math.min(30,Number(document.getElementById('count-ra2').value)||1));const p=a/(a+b)*100;const fmt=n=>n.toLocaleString('es-ES',{minimumFractionDigits:2,maximumFractionDigits:2})+' %';document.getElementById('weight-ra1').textContent=fmt(p);document.getElementById('weight-ra2').textContent=fmt(100-p);document.getElementById('weight-ce').textContent=fmt(100/(a+b));document.getElementById('bar-ra1').style.width=p+'%';document.getElementById('bar-ra2').style.width=(100-p)+'%'}
document.querySelectorAll('#count-ra1,#count-ra2').forEach(el=>el.addEventListener('input',updateWeights));
