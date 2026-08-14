"""
app.py — FastAPI Web Interface for PII Redaction Tool.

Thin API wrapper around the core PII redaction engine (src.redactor).
Provides:
  - GET  /         : Interactive HTML upload UI
  - POST /redact   : Secure DOCX redaction endpoint with downloadable output
  - GET  /health   : Service health check
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from src.detector import PIIDetector
from src.redactor import redact_document

# Maximum allowed upload size (25 MB)
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024

app = FastAPI(
    title="PII Redaction Service",
    description="Automated PII detection and synthetic replacement for DOCX documents",
    version="1.0.0",
)

# Global lazy-loaded detector instance
_DETECTOR: Optional[PIIDetector] = None


def get_detector() -> PIIDetector:
    """Lazy initialize and reuse the Presidio + spaCy NLP detector."""
    global _DETECTOR
    if _DETECTOR is None:
        _DETECTOR = PIIDetector(min_score=0.5)
    return _DETECTOR


def _cleanup_temp_dir(temp_dir: str) -> None:
    """Background task to remove temporary upload and output directories."""
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass


@app.get("/health", summary="Health Check")
async def health_check() -> dict:
    """Service liveness/readiness probe."""
    return {
        "status": "OK",
        "message": "PII Redaction API Server is running.",
        "endpoints": {
            "health": "/health",
            "redact": "/redact (POST)",
        },
    }


@app.get("/", response_class=HTMLResponse, summary="Web Interface")
async def index() -> str:
    """Serve modern, secure single-page HTML interface for DOCX PII redaction."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PII Redaction Tool — DOCX Anonymizer</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #0f172a;
            --card-bg: #1e293b;
            --card-border: #334155;
            --primary: #38bdf8;
            --primary-hover: #0ea5e9;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent-green: #34d399;
            --radius: 12px;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 40px 20px;
        }
        .container {
            width: 100%;
            max-width: 680px;
        }
        .header {
            text-align: center;
            margin-bottom: 32px;
        }
        .header h1 {
            font-size: 28px;
            font-weight: 700;
            color: #fff;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header p {
            color: var(--text-muted);
            font-size: 15px;
            line-height: 1.5;
        }
        .card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: var(--radius);
            padding: 32px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
            margin-bottom: 24px;
        }
        .dropzone {
            border: 2px dashed #475569;
            border-radius: 8px;
            padding: 36px 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s ease;
            background: rgba(15, 23, 42, 0.4);
        }
        .dropzone:hover, .dropzone.dragover {
            border-color: var(--primary);
            background: rgba(56, 189, 248, 0.05);
        }
        .dropzone svg {
            width: 48px;
            height: 48px;
            fill: var(--primary);
            margin-bottom: 12px;
        }
        .dropzone p {
            color: var(--text-main);
            font-size: 15px;
            font-weight: 500;
            margin-bottom: 4px;
        }
        .dropzone span {
            color: var(--text-muted);
            font-size: 13px;
        }
        #fileInput { display: none; }
        .file-info {
            margin-top: 16px;
            padding: 10px 14px;
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 6px;
            font-size: 13px;
            color: var(--primary);
            display: none;
        }
        .btn {
            width: 100%;
            margin-top: 20px;
            padding: 14px;
            background: var(--primary);
            color: #0f172a;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s ease;
        }
        .btn:hover:not(:disabled) {
            background: var(--primary-hover);
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .status-box {
            margin-top: 16px;
            padding: 12px;
            border-radius: 6px;
            font-size: 14px;
            display: none;
        }
        .status-box.error {
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid #ef4444;
            color: #fca5a5;
        }
        .features-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-top: 24px;
        }
        .feature-item {
            background: #0f172a;
            padding: 12px;
            border-radius: 6px;
            border: 1px solid #1e293b;
            font-size: 12px;
            color: var(--text-muted);
        }
        .feature-item strong {
            color: #e2e8f0;
            display: block;
            margin-bottom: 2px;
        }
        .disclaimer {
            text-align: center;
            font-size: 12px;
            color: #64748b;
            margin-top: 24px;
            line-height: 1.5;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>PII Redaction Tool</h1>
            <p>Automated Presidio + spaCy NER detection and Faker synthetic replacement for legal & financial DOCX documents.</p>
        </div>

        <div class="card">
            <form id="redactForm">
                <div class="dropzone" id="dropzone">
                    <svg viewBox="0 0 24 24"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>
                    <p>Click or drag & drop a .docx document</p>
                    <span>Supports Word documents up to 25 MB</span>
                </div>
                <input type="file" id="fileInput" name="file" accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document">
                <div class="file-info" id="fileInfo"></div>
                <button type="submit" class="btn" id="submitBtn" disabled>Redact & Download Anonymized DOCX</button>
            </form>
            <div class="status-box" id="statusBox"></div>

            <div class="features-grid">
                <div class="feature-item"><strong>9 PII Categories</strong>Names, Emails, Phones, Orgs, Addresses, SSNs, Cards, DOBs, IPs.</div>
                <div class="feature-item"><strong>Consistent Synthetic Replacement</strong>Faker-backed deterministic global mapping across document.</div>
                <div class="feature-item"><strong>Luhn & Context Validation</strong>Credit card Luhn checks and DOB context window guards.</div>
                <div class="feature-item"><strong>DOCX Layout Preservation</strong>Preserves tables, paragraphs, and styles.</div>
            </div>
        </div>

        <p class="disclaimer">
            Security Notice: Uploaded files are processed in ephemeral memory/temp storage and immediately purged after download.
            This demonstration web service is provided for academic evaluation.
        </p>
    </div>

    <script>
        const dropzone = document.getElementById('dropzone');
        const fileInput = document.getElementById('fileInput');
        const fileInfo = document.getElementById('fileInfo');
        const submitBtn = document.getElementById('submitBtn');
        const statusBox = document.getElementById('statusBox');
        const form = document.getElementById('redactForm');

        dropzone.addEventListener('click', () => fileInput.click());
        dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
        dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                fileInput.files = e.dataTransfer.files;
                handleFileSelect();
            }
        });

        fileInput.addEventListener('change', handleFileSelect);

        function handleFileSelect() {
            if (fileInput.files.length > 0) {
                const file = fileInput.files[0];
                if (!file.name.toLowerCase().endsWith('.docx')) {
                    showError('Please select a valid .docx file.');
                    submitBtn.disabled = true;
                    return;
                }
                fileInfo.style.display = 'block';
                fileInfo.textContent = `Selected: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
                submitBtn.disabled = false;
                statusBox.style.display = 'none';
            }
        }

        function showError(msg) {
            statusBox.className = 'status-box error';
            statusBox.style.display = 'block';
            statusBox.textContent = msg;
        }

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!fileInput.files.length) return;

            submitBtn.disabled = true;
            submitBtn.textContent = 'Processing & Redacting PII...';
            statusBox.style.display = 'none';

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            try {
                const response = await fetch('/redact', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    let errMsg = 'Failed to redact document.';
                    try {
                        const errData = await response.json();
                        errMsg = errData.detail || errMsg;
                    } catch (_) {}
                    throw new Error(errMsg);
                }

                const blob = await response.blob();
                const downloadUrl = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = downloadUrl;
                a.download = 'redacted_' + fileInput.files[0].name;
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(downloadUrl);

                submitBtn.textContent = 'Redacted File Downloaded!';
                setTimeout(() => {
                    submitBtn.textContent = 'Redact & Download Anonymized DOCX';
                    submitBtn.disabled = false;
                }, 3000);
            } catch (err) {
                showError(err.message || 'An error occurred during redaction.');
                submitBtn.disabled = false;
                submitBtn.textContent = 'Redact & Download Anonymized DOCX';
            }
        });
    </script>
</body>
</html>
"""


@app.post("/redact", summary="Redact DOCX Document")
async def redact_docx_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> FileResponse:
    """
    Accepts a DOCX document, runs PII detection and synthetic replacement,
    and returns the anonymized DOCX for download.
    """
    # 1. Validate file extension
    filename = file.filename or "document.docx"
    if not filename.lower().endswith(".docx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only .docx Word documents are supported.",
        )

    # 2. Create isolated temporary directory
    temp_dir = tempfile.mkdtemp(prefix="pii_redact_")
    input_path = os.path.join(temp_dir, "input.docx")
    output_path = os.path.join(temp_dir, "redacted_output.docx")

    try:
        # 3. Read uploaded bytes with size validation
        content = await file.read()
        if len(content) > MAX_FILE_SIZE_BYTES:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024*1024)} MB.",
            )

        # 4. Check DOCX magic header (PK\x03\x04 zip archive)
        if not content.startswith(b"PK\x03\x04"):
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file content. The uploaded file is not a valid DOCX document.",
            )

        Path(input_path).write_bytes(content)

        # 5. Execute redaction using core engine
        detector = get_detector()
        redact_document(
            input_path=input_path,
            output_path=output_path,
            detector=detector,
            min_score=0.5,
        )

        if not os.path.exists(output_path):
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Redaction processing failed to generate output file.",
            )

        # 6. Schedule background cleanup of temporary files
        background_tasks.add_task(_cleanup_temp_dir, temp_dir)

        output_filename = f"redacted_{Path(filename).name}"
        return FileResponse(
            path=output_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=output_filename,
        )

    except HTTPException:
        raise
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the document.",
        ) from exc


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
