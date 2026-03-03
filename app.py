import os
import sys
import json
import string
import struct
import random
import io
import zipfile
from flask import Flask, render_template, jsonify, request, send_from_directory, send_file
from flask_cors import CORS
from pypdf import PdfWriter, PdfReader
import pikepdf
from PIL import Image, ImageOps
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4, LEGAL
import fitz  # PyMuPDF
from docx import Document

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

VERSION = "1.8"

# Maps for sizes
SIZE_MAP = {
    'A4': A4,
    'LETTER': letter,
    'LEGAL': LEGAL
}

def parse_range(range_str, max_pages):
    pages = []
    if not range_str: return list(range(max_pages))
    parts = range_str.split(',')
    for part in parts:
        try:
            part = part.strip()
            if '-' in part:
                start, end = map(int, part.split('-'))
                pages.extend(range(start-1, end))
            else:
                pages.append(int(part)-1)
        except: continue
    return [p for p in pages if 0 <= p < max_pages]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process-pdf', methods=['POST'])
def process_pdf():
    try:
        tool = request.form.get('tool')
        files = request.files.getlist('files')
        
        if not files:
            return "No files provided", 400

        output = io.BytesIO()
        ext = 'pdf'
        mtype = 'application/pdf'

        if tool == 'merge':
            merger = PdfWriter()
            for f in files:
                reader = PdfReader(f)
                for page in reader.pages:
                    merger.add_page(page)
            merger.write(output)
        
        elif tool == 'split':
            range_str = request.form.get('range', '')
            reader = PdfReader(files[0])
            writer = PdfWriter()
            target_pages = parse_range(range_str, len(reader.pages))
            for p in target_pages:
                writer.add_page(reader.pages[p])
            writer.write(output)

        elif tool == 'compress':
            with pikepdf.open(files[0]) as pdf:
                pdf.save(output, compress_streams=True)

        elif tool == 'protect':
            password = request.form.get('password', '')
            reader = PdfReader(files[0])
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            writer.encrypt(password)
            writer.write(output)

        elif tool == 'unlock':
            password = request.form.get('password', '')
            with pikepdf.open(files[0], password=password) as pdf:
                pdf.save(output)

        elif tool == 'rotate':
            angle = int(request.form.get('angle', 90))
            reader = PdfReader(files[0])
            writer = PdfWriter()
            for page in reader.pages:
                page.rotate(angle)
                writer.add_page(page)
            writer.write(output)

        elif tool == 'delete':
            pages_to_del = request.form.get('pages', '')
            reader = PdfReader(files[0])
            writer = PdfWriter()
            max_p = len(reader.pages)
            to_del = set(parse_range(pages_to_del, max_p))
            for i in range(max_p):
                if i not in to_del:
                    writer.add_page(reader.pages[i])
            writer.write(output)

        elif tool == 'watermark':
            text = request.form.get('text', 'TOXIC')
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=letter)
            can.setFont("Helvetica", 40)
            can.setStrokeColorRGB(0.5, 0.5, 0.5, 0.3)
            can.saveState()
            can.translate(300, 500)
            can.rotate(45)
            can.drawCentredString(0, 0, text)
            can.restoreState()
            can.save()
            packet.seek(0)
            watermark_reader = PdfReader(packet)
            watermark_page = watermark_reader.pages[0]
            reader = PdfReader(files[0])
            writer = PdfWriter()
            for page in reader.pages:
                page.merge_page(watermark_page)
                writer.add_page(page)
            writer.write(output)

        elif tool == 'reorder':
            order_str = request.form.get('order', '')
            reader = PdfReader(files[0])
            writer = PdfWriter()
            try:
                order = [int(x.strip())-1 for x in order_str.replace(';',',').split(',') if x.strip()]
                for p in order:
                    if 0 <= p < len(reader.pages):
                        writer.add_page(reader.pages[p])
                writer.write(output)
            except Exception as e:
                return f"Invalid order format: {str(e)}", 400

        elif tool == 'img2pdf':
            images = []
            for f in files:
                img = Image.open(f)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                images.append(img)
            if images:
                images[0].save(output, format='PDF', save_all=True, append_images=images[1:])

        elif tool == 'txt2pdf':
            text = files[0].read().decode('utf-8', errors='ignore')
            can = canvas.Canvas(output, pagesize=letter)
            width, height = letter
            text_obj = can.beginText(40, height - 40)
            text_obj.setFont("Helvetica", 12)
            for line in text.split('\n'):
                text_obj.textLine(line)
            can.drawText(text_obj)
            can.showPage()
            can.save()

        elif tool == 'pdf2img':
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w') as zf:
                doc = fitz.open(stream=files[0].read(), filetype="pdf")
                for i in range(len(doc)):
                    page = doc.load_page(i)
                    pix = page.get_pixmap(dpi=150)
                    img_data = pix.tobytes("jpg")
                    zf.writestr(f'page_{i+1}.jpg', img_data)
                doc.close()
            zip_buffer.seek(0)
            return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name='toxic_images.zip')

        elif tool == 'grayscale':
            doc = fitz.open(stream=files[0].read(), filetype="pdf")
            out_pdf = fitz.open()
            for page in doc:
                pix = page.get_pixmap(colorspace=fitz.csGRAY, dpi=150)
                img_bytes = pix.tobytes("png")
                
                # Create a new 1-page PDF from this image with same dimensions
                img_pdf_bytes = fitz.open("pdf", fitz.open("png", img_bytes).convert_to_pdf())
                out_pdf.insert_pdf(img_pdf_bytes)
            out_pdf.save(output, garbage=4, deflate=True)
            out_pdf.close()
            doc.close()

        elif tool == 'extract_text':
            doc = fitz.open(stream=files[0].read(), filetype="pdf")
            full_text = ""
            for page in doc:
                full_text += page.get_text()
            doc.close()
            output.write(full_text.encode('utf-8'))
            ext = 'txt'
            mtype = 'text/plain'

        elif tool == 'repair':
            with pikepdf.open(files[0]) as pdf:
                pdf.save(output)

        elif tool == 'pagenum':
            start_num = int(request.form.get('start', 1))
            pos = request.form.get('position', 'center').lower()
            reader = PdfReader(files[0])
            writer = PdfWriter()
            for i, page in enumerate(reader.pages):
                packet = io.BytesIO()
                can = canvas.Canvas(packet, pagesize=(page.mediabox.width, page.mediabox.height))
                can.setFont("Helvetica", 10)
                txt = str(start_num + i)
                width = page.mediabox.width
                x = float(width) / 2 if pos == 'center' else (40 if pos == 'left' else float(width) - 40)
                can.drawCentredString(x, 20, txt)
                can.save()
                packet.seek(0)
                num_reader = PdfReader(packet)
                page.merge_page(num_reader.pages[0])
                writer.add_page(page)
            writer.write(output)

        elif tool == 'invert':
            doc = fitz.open(stream=files[0].read(), filetype="pdf")
            out_pdf = fitz.open()
            for page in doc:
                pix = page.get_pixmap(dpi=150)
                # Invert logic via PIL
                img = ImageOps.invert(Image.open(io.BytesIO(pix.tobytes("png"))).convert('RGB'))
                img_io = io.BytesIO()
                img.save(img_io, format='png')
                img_io.seek(0)
                
                # Insert as a new high-quality page
                img_pdf_bytes = fitz.open("pdf", fitz.open("png", img_io.read()).convert_to_pdf())
                out_pdf.insert_pdf(img_pdf_bytes)
                
            out_pdf.save(output, garbage=4, deflate=True)
            out_pdf.close()
            doc.close()

        elif tool == 'flatten':
            doc = fitz.open(stream=files[0].read(), filetype="pdf")
            out_pdf = fitz.open()
            for page in doc:
                pix = page.get_pixmap(dpi=200)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                img_pdf_bytes = io.BytesIO()
                img.save(img_pdf_bytes, format='PDF')
                img_pdf_bytes.seek(0)
                img_pdf = fitz.open("pdf", img_pdf_bytes.read())
                out_pdf.insert_pdf(img_pdf)
            out_pdf.save(output, garbage=4, deflate=True)
            out_pdf.close()
            doc.close()

        elif tool == 'crop':
            margin_pct = float(request.form.get('margin', 10)) / 100.0
            doc = fitz.open(stream=files[0].read(), filetype="pdf")
            for page in doc:
                rect = page.rect
                x_delta, y_delta = rect.width * margin_pct, rect.height * margin_pct
                page.set_cropbox(fitz.Rect(rect.x0 + x_delta, rect.y0 + y_delta, rect.x1 - x_delta, rect.y1 - y_delta))
            doc.save(output)
            doc.close()

        elif tool == 'pdf2word':
            try:
                doc = fitz.open(stream=files[0].read(), filetype="pdf")
                word_doc = Document()
                for page in doc:
                    # Get blocks instead of raw text to better handle layout
                    blocks = page.get_text("blocks")
                    # Sort blocks by y coordinate, then x coordinate
                    blocks.sort(key=lambda b: (b[1], b[0]))
                    
                    for b in blocks:
                        text_block = b[4].strip()
                        if text_block:
                            # Sanitize text to remove control characters that break docx
                            clean_text = "".join(c for c in text_block if c.isprintable() or c in "\n\r\t")
                            word_doc.add_paragraph(clean_text)
                    
                    if len(doc) > 1:
                        word_doc.add_page_break()
                
                doc.close()
                word_doc.save(output)
                ext = 'docx'
                mtype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            except Exception as e:
                return f"Word Conversion Failed: {str(e)}", 500

        elif tool == 'resize':
            target_size_name = request.form.get('size', 'A4').upper()
            target_size = SIZE_MAP.get(target_size_name, A4)
            reader = PdfReader(files[0])
            writer = PdfWriter()
            for page in reader.pages:
                page.scale_to(target_size[0], target_size[1])
                writer.add_page(page)
            writer.write(output)

        elif tool == 'header':
            text = request.form.get('text', 'CONFIDENTIAL')
            reader = PdfReader(files[0])
            writer = PdfWriter()
            for page in reader.pages:
                packet = io.BytesIO()
                can = canvas.Canvas(packet, pagesize=(page.mediabox.width, page.mediabox.height))
                can.setFont("Helvetica", 10)
                can.drawCentredString(float(page.mediabox.width) / 2, float(page.mediabox.height) - 30, text)
                can.save()
                packet.seek(0)
                h_reader = PdfReader(packet)
                page.merge_page(h_reader.pages[0])
                writer.add_page(page)
            writer.write(output)

        elif tool == 'extract_img':
            doc = fitz.open(stream=files[0].read(), filetype="pdf")
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w') as zf:
                for i in range(len(doc)):
                    page = doc.load_page(i)
                    for idx, img in enumerate(page.get_images(full=True)):
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]
                        zf.writestr(f'page{i+1}_img{idx+1}.{image_ext}', image_bytes)
            doc.close()
            zip_buffer.seek(0)
            return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name='toxic_extract_img_output.zip')

        elif tool == 'remove_blank':
            doc = fitz.open(stream=files[0].read(), filetype="pdf")
            out_pdf = fitz.open()
            for page in doc:
                text = page.get_text().strip()
                if text or page.get_images():
                    out_pdf.insert_pdf(doc, from_page=page.number, to_page=page.number)
            out_pdf.save(output)
            out_pdf.close()
            doc.close()

        elif tool == 'redact':
            text_to_redact = request.form.get('text', '')
            doc = fitz.open(stream=files[0].read(), filetype="pdf")
            if text_to_redact:
                for page in doc:
                    areas = page.search_for(text_to_redact)
                    for rect in areas:
                        page.add_redact_annot(rect, fill=(0, 0, 0))
                    page.apply_redactions()
            doc.save(output)
            doc.close()

        elif tool == 'remove_annots':
            doc = fitz.open(stream=files[0].read(), filetype="pdf")
            for page in doc:
                for annot in page.annots():
                    page.delete_annot(annot)
            doc.save(output)
            doc.close()

        else:
            return f"Tool '{tool}' not implemented", 501

        output.seek(0)
        return send_file(output, mimetype=mtype, as_attachment=True, download_name=f'toxic_{tool}_output.{ext}')

    except Exception as e:
        return str(e), 500

@app.route('/service-worker.js')
def sw(): return send_from_directory('static', 'service-worker.js')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

if __name__ == "__main__":
    import threading
    import webbrowser
    threading.Timer(1.5, lambda: webbrowser.open_new("http://127.0.0.1:5001")).start()
    app.run(port=5001, debug=False)