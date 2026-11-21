"""Genera manuales PDF desde las fuentes Markdown de la beta.5."""
from pathlib import Path
import argparse
import html
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
import fitz

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'docs'/'manuales'
MANUALS=('WINDOWS','LINUX','MACOS','DIDACTICO_CANARIAS')
NAVY=colors.HexColor('#173850')
TEAL=colors.HexColor('#087e80')
MUTED=colors.HexColor('#526a7b')
styles={
    'title':ParagraphStyle('Title',fontName='Helvetica-Bold',fontSize=22,leading=26,
                           textColor=NAVY,spaceAfter=12,keepWithNext=True),
    'heading':ParagraphStyle('Heading',fontName='Helvetica-Bold',fontSize=13,leading=16,
                             textColor=TEAL,spaceBefore=11,spaceAfter=5,keepWithNext=True),
    'body':ParagraphStyle('Body',fontName='Helvetica',fontSize=10.5,leading=15,
                          textColor=NAVY,spaceAfter=5,splitLongWords=True),
    'list':ParagraphStyle('List',fontName='Helvetica',fontSize=10.5,leading=15,
                          textColor=NAVY,leftIndent=14,firstLineIndent=-14,spaceAfter=4),
}


def paragraph(text):
    text=html.escape(text)
    return re.sub(r'\x60([^\x60]+)\x60',r'<font name="Courier" size="9">\1</font>',text)


def footer(canvas,doc):
    width,height=A4
    canvas.setStrokeColor(TEAL)
    canvas.setLineWidth(.5)
    canvas.line(20*mm,height-15*mm,width-20*mm,height-15*mm)
    canvas.setFont('Helvetica-Bold',8)
    canvas.setFillColor(MUTED)
    canvas.drawString(20*mm,height-12*mm,'EVALÚAFP CANARIAS  |  DOCUMENTACIÓN DE USUARIO')
    canvas.line(20*mm,15*mm,width-20*mm,15*mm)
    canvas.setFont('Helvetica',8)
    canvas.drawString(20*mm,10*mm,'1.2.10-AG-CN-beta.5  |  Versión preliminar')
    canvas.drawRightString(width-20*mm,10*mm,str(doc.page))


def build(source,destination):
    story=[]
    title=source.stem
    for line in source.read_text(encoding='utf-8').splitlines():
        line=line.strip()
        if not line:
            continue
        if line.startswith('# '):
            title=line[2:]
            story.append(Paragraph(paragraph(title),styles['title']))
        elif line.startswith('## '):
            story.append(Paragraph(paragraph(line[3:]),styles['heading']))
        elif re.match(r'^(\d+\. |- )',line):
            story.append(Paragraph(paragraph(line),styles['list']))
        else:
            story.append(Paragraph(paragraph(line),styles['body']))
    doc=SimpleDocTemplate(str(destination),pagesize=A4,leftMargin=20*mm,
        rightMargin=20*mm,topMargin=23*mm,bottomMargin=22*mm,
        title=title,author='EvalúaFP Canarias')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    # Comprobación de estructura, texto y renderizado de todas las páginas.
    with fitz.open(destination) as pdf:
        if not pdf.page_count or title.split(' · ')[0] not in pdf[0].get_text():
            raise RuntimeError('Manual PDF incompleto: '+source.name)
        for page in pdf:
            if len(page.get_text().strip())<80:
                raise RuntimeError('Página sin contenido: '+source.name)
            page.get_pixmap(matrix=fitz.Matrix(1,1),alpha=False)
        print(destination.name,pdf.page_count,'páginas renderizadas')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,default=ROOT/'dist'/'manuales')
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    for name in MANUALS:
        build(SOURCE/(name+'.md'),args.out/('EvaluaFPCanarias_beta5_'+name+'.pdf'))


if __name__=='__main__':
    main()
