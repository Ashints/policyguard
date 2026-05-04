from fastapi import APIRouter, Depends, HTTPException , status, UploadFile, File
from script.jwt_auth import require_admin
from pathlib import Path
from script.db import users_collection
from bson import ObjectId
import shutil
import uuid
from script.db import users_collection
from script.ingest import extract_text_from_pdf, chunk_text, model, qdrant, COLLECTION_NAME,normalize_article_id
DATA_DIR = Path("data/raw/gdpr")

router=APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/user")
def get_all_users(admin=Depends(require_admin)):
    users = []
    for u in users_collection.find({}, {"password_hash": 0}):
        u["_id"] = str(u["_id"])
        users.append(u)
    return users

#disable user 
@router.patch("/users/{user_id}/disable")
def disable_user(user_id: str, _: dict = Depends(require_admin)):
    users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"is_active": False}}
    )
    return {"message": "User disabled"}

#enable user 
@router.patch("/users/{user_id}/enable")
def enable_user(user_id: str, _: dict = Depends(require_admin)):
    users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"is_active": True}}
    )
    return {"message": "User enabled"}


@router.patch("/users/{user_id}/role")
def change_role(user_id: str, role: str, _:dict=Depends(require_admin)):
    if role not in("user","admin"):
        raise HTTPException(400, "Invalid role")
    users_collection.update_one(
        {"_id":ObjectId(user_id)},
        {"$set":{"role":role}}
    )
    return {"message": f"Role updated to {role}"}

@router.post("/upload-pdf")
def upload_pdf(
    file: UploadFile = File(...),
    admin=Depends(require_admin)
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # ✅ Just use the original filename stem as-is, no normalization
    article_id = Path(file.filename).stem

    safe_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = DATA_DIR / safe_name

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        text = extract_text_from_pdf(file_path)
        if not text.strip():
            file_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail="No text extracted from PDF")

        chunks = chunk_text(text)
        vectors = model.encode(chunks, normalize_embeddings=True)

        points = []
        for chunk, vector in zip(chunks, vectors):
            points.append({
                "id": str(uuid.uuid4()),
                "vector": vector.tolist(),
                "payload": {
                    "source": "ADMIN_UPLOAD",
                    "article": article_id,    # ✅ e.g. "my_gdpr_doc", "downloaded_file"
                    "file": file.filename,
                    "text": chunk
                }
            })

        qdrant.upsert(collection_name=COLLECTION_NAME, points=points, wait=True)

    except HTTPException:
        raise
    except Exception as e:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Failed to ingest PDF: {str(e)}")

    return {
        "message": "PDF uploaded and indexed successfully",
        "filename": file.filename,
        "chunks": len(chunks)
    }