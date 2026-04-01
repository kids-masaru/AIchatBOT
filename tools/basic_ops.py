"""
Basic tools - Calculator, Date, PDF processing
"""
import re
import math
import os
import sys
import tempfile
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from utils.auth import get_google_credentials

# PDF library
try:
    import fitz  # PyMuPDF
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("PyMuPDF not available", file=sys.stderr)


def calculate(expression):
    """
    Safe calculator - evaluates mathematical expressions
    Supports: +, -, *, /, **, sqrt, sin, cos, tan, log, etc.
    """
    try:
        # Clean and validate expression
        expr = expression.strip()
        
        # Replace common notation
        expr = expr.replace('×', '*').replace('÷', '/').replace('^', '**')
        expr = expr.replace('√', 'sqrt')
        
        # Allowed functions and constants
        safe_dict = {
            'sqrt': math.sqrt,
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'log': math.log,
            'log10': math.log10,
            'abs': abs,
            'round': round,
            'pi': math.pi,
            'e': math.e,
            'pow': pow,
        }
        
        # Validate - only allow safe characters
        if not re.match(r'^[\d\s\+\-\*\/\.\(\)\,a-z\_]+$', expr.lower()):
            return {"error": f"無効な文字が含まれています: {expr}"}
        
        result = eval(expr, {"__builtins__": {}}, safe_dict)
        
        # Format result
        if isinstance(result, float):
            if result.is_integer():
                result = int(result)
            else:
                result = round(result, 10)
        
        return {"success": True, "expression": expression, "result": result}
    except Exception as e:
        return {"error": f"計算エラー: {str(e)}"}


def calculate_date(operation, days=0, date_str=None):
    """
    Date calculator
    Operations: today, add_days, subtract_days, weekday, days_until
    """
    try:
        if date_str:
            base_date = datetime.strptime(date_str, '%Y-%m-%d')
        else:
            base_date = datetime.now()
        
        weekday_names = ['月', '火', '水', '木', '金', '土', '日']
        
        if operation == 'today':
            result = datetime.now()
            return {
                "success": True,
                "date": result.strftime('%Y年%m月%d日'),
                "weekday": weekday_names[result.weekday()] + '曜日',
                "time": result.strftime('%H:%M')
            }
        elif operation == 'add_days':
            result = base_date + timedelta(days=days)
            return {
                "success": True,
                "date": result.strftime('%Y年%m月%d日'),
                "weekday": weekday_names[result.weekday()] + '曜日'
            }
        elif operation == 'subtract_days':
            result = base_date - timedelta(days=days)
            return {
                "success": True,
                "date": result.strftime('%Y年%m月%d日'),
                "weekday": weekday_names[result.weekday()] + '曜日'
            }
        elif operation == 'days_until':
            target = datetime.strptime(date_str, '%Y-%m-%d')
            diff = (target - datetime.now()).days
            return {"success": True, "days": diff, "target": date_str}
        else:
            return {"error": f"Unknown operation: {operation}"}
    except Exception as e:
        return {"error": f"日付計算エラー: {str(e)}"}


def read_pdf_from_drive(file_id):
    """Download and read PDF from Google Drive"""
    try:
        if not PDF_AVAILABLE:
            return {"error": "PDF読み取り機能が利用できません"}
        
        creds = get_google_credentials()
        if not creds:
            return {"error": "Google認証エラー"}
        
        drive_service = build('drive', 'v3', credentials=creds)
        
        # Download file
        request = drive_service.files().get_media(fileId=file_id)
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(request.execute())
            tmp_path = tmp.name
        
        # Read PDF
        doc = fitz.open(tmp_path)
        text = ""
        page_count = len(doc)
        for page in doc:
            text += page.get_text()
        doc.close()
        
        # Cleanup
        os.unlink(tmp_path)
        
        # Truncate if too long
        if len(text) > 10000:
            text = text[:10000] + "\n...(以下省略)"
        
        return {"success": True, "text": text, "pages": page_count}
    except Exception as e:
        print(f"PDF error: {e}", file=sys.stderr)
        return {"error": f"PDF読み取りエラー: {str(e)}"}


def search_and_read_pdf(query, file_id=None):
    """Search Drive for PDF and read it. If file_id is provided, reads it directly."""
    try:
        creds = get_google_credentials()
        if not creds:
            return {"error": "Google認証エラー"}

        drive_service = build('drive', 'v3', credentials=creds)

        if file_id:
            # Direct read by file_id
            try:
                file_info = drive_service.files().get(fileId=file_id, fields="id, name").execute()
                pdf_result = read_pdf_from_drive(file_id)
                if pdf_result.get('success'):
                    pdf_result['filename'] = file_info.get('name', file_id)
                return pdf_result
            except Exception as e:
                return {"error": f"ファイルID '{file_id}' の読み取りエラー: {str(e)}"}

        # Search for PDF by query
        results = drive_service.files().list(
            q=f"name contains '{query}' and mimeType='application/pdf' and trashed=false",
            pageSize=1,
            fields="files(id, name)"
        ).execute()

        files = results.get('files', [])
        if not files:
            return {"error": f"'{query}'に該当するPDFが見つかりませんでした"}

        file_info = files[0]
        pdf_result = read_pdf_from_drive(file_info['id'])

        if pdf_result.get('success'):
            pdf_result['filename'] = file_info['name']

        return pdf_result
    except Exception as e:
        return {"error": str(e)}
