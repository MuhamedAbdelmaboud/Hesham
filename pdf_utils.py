"""
pdf_utils.py
وحدة استخراج النصوص من ملفات PDF
تدعم PyPDF2 و pdfplumber (بترتيب الأولوية)
"""

import io
from typing import Optional

# محاولة استيراد المكتبات المتاحة
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False


def extract_text(file) -> str:
    """
    استخراج النص من ملف PDF.
    
    Args:
        file: كائن ملف (UploadedFile من Streamlit أو مسار أو BytesIO)
    
    Returns:
        str: النص المستخرج من الملف، أو رسالة خطأ في حال الفشل
    """
    if file is None:
        return "⚠️ لم يتم تمرير أي ملف."
    
    # محاولة pdfplumber أولاً (أدق في الجداول والنصوص المعقدة)
    if PDFPLUMBER_AVAILABLE:
        try:
            text_parts = []
            # إعادة مؤشر الملف للبداية إن أمكن
            if hasattr(file, "seek"):
                file.seek(0)
            
            with pdfplumber.open(file) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        text_parts.append(page_text)
            
            result = "\n\n".join(text_parts).strip()
            if result:
                return result
        except Exception as e:
            print(f"[pdfplumber] فشل: {e}")
    
    # fallback إلى PyPDF2
    if PYPDF2_AVAILABLE:
        try:
            if hasattr(file, "seek"):
                file.seek(0)
            
            reader = PyPDF2.PdfReader(file)
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_parts.append(page_text)
            
            result = "\n\n".join(text_parts).strip()
            if result:
                return result
        except Exception as e:
            print(f"[PyPDF2] فشل: {e}")
    
    # في حال عدم توفر المكتبات أو فشل الاستخراج
    if not PDFPLUMBER_AVAILABLE and not PYPDF2_AVAILABLE:
        return "⚠️ لم يتم تثبيت pdfplumber أو PyPDF2. نفّذ: pip install pdfplumber PyPDF2"
    
    return "⚠️ لم يتم استخراج نص من الملف (قد يكون PDF صوري/ممسوح ضوئيًا)."


def get_pdf_metadata(file) -> dict:
    """
    استخراج بيانات وصفية من الـ PDF (اختياري، مفيد للـ Demo).
    """
    meta = {"pages": 0, "title": "غير معروف", "author": "غير معروف"}
    
    if file is None or not PYPDF2_AVAILABLE:
        return meta
    
    try:
        if hasattr(file, "seek"):
            file.seek(0)
        reader = PyPDF2.PdfReader(file)
        meta["pages"] = len(reader.pages)
        info = reader.metadata or {}
        meta["title"] = info.get("/Title", "غير معروف") or "غير معروف"
        meta["author"] = info.get("/Author", "غير معروف") or "غير معروف"
    except Exception:
        pass
    
    return meta