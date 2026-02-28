from io import BytesIO
import logging

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from PIL import Image, UnidentifiedImageError
from rembg import remove

app = FastAPI(title="AI Background Remover API", version="1.0.0")
logger = logging.getLogger("bg-remover")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/remove-bg")
async def remove_bg(file: UploadFile = File(...)) -> StreamingResponse:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload a valid image file.")

    try:
        raw_bytes = await file.read()
        with Image.open(BytesIO(raw_bytes)) as img:
            img.verify()
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=400, detail="Unsupported or invalid image.") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to read image.") from exc

    try:
        output_bytes = remove(raw_bytes)
        if isinstance(output_bytes, bytes):
            result_stream = BytesIO(output_bytes)
        else:
            result_stream = BytesIO()
            output_bytes.save(result_stream, format="PNG")
        result_stream.seek(0)
    except Exception as exc:
        logger.exception("Background removal failed")
        raise HTTPException(status_code=500, detail=f"Background removal failed: {exc}") from exc

    return StreamingResponse(
        result_stream,
        media_type="image/png",
        headers={"Content-Disposition": 'inline; filename="removed-bg.png"'},
    )
