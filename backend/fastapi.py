from fastapi import FastAPI, APIRouter, Request, Path, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict
from datetime import datetime as dt, timedelta
import httpx
import os
import logging
import jwt
from azure.storage.blob import BlobSasPermissions, generate_blob_sas
from pydantic import BaseModel
from urllib.parse import urlparse, urlencode, urlunparse, parse_qsl, quote

logger = logging.getLogger("uvicorn")
app = FastAPI()
router = APIRouter()

def get_db():
    pass

def get_current_active_user():
    pass

def get_user_with_sub_service(user_sub, db):
    pass

def is_user_allowed_to_access_candidate(user, doc_id, db):
    pass

def is_user_allowed_to_access_job_post(user, doc_id, db):
    pass

def get_candidate_service(doc_id, db):
    pass

def get_job_post_service(doc_id, db):
    pass

def update_blob(blob_name, file_content):
    pass


@router.post("/onlyoffice/callback")
async def onlyoffice_callback(
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        body = await request.json()
        logger.info(f"OnlyOffice callback received: {body}")
        
        status = body.get('status', 0)
        if status == 2:  # Document ready to be saved
            document_url = body.get('url')
            key = body.get('key')
            
            if not document_url or not key:
                logger.error("Missing document_url or key in callback")
                return {"error": 1, "message": "Missing required parameters"}
            
            try:
                timestamp = key[:14]
                remaining_parts = key[14:].split('__')
                if len(remaining_parts) < 4:
                    raise ValueError("Invalid key format")
                
                blob_name, doc_type, doc_id, user_sub = remaining_parts[:4]
                user = get_user_with_sub_service(user_sub, db)
                if not user:
                    raise HTTPException(status_code=404, detail="User not found")
                
                if doc_type == "candidate":
                    if not is_user_allowed_to_access_candidate(user, doc_id, db):
                        raise HTTPException(status_code=403, detail="Not authorized")
                elif doc_type == "job_post":
                    if not is_user_allowed_to_access_job_post(user, doc_id, db):
                        raise HTTPException(status_code=403, detail="Not authorized")

                async with httpx.AsyncClient() as client:
                    response = await client.get(document_url)
                    response.raise_for_status()
                    file_content = response.content

                update_blob(blob_name, file_content)
                logger.info(f"Successfully saved document for {doc_type} {doc_id}")
                return {"error": 0}
            
            except Exception as inner_e:
                logger.error(f"Error processing document: {inner_e}")
                return {"error": 1, "message": str(inner_e)}
        
        if status in {1, 6}:
            return {"error": 0}
        
        return {"error": 0}
                
    except Exception as e:
        logger.error(f"Error in onlyoffice_callback: {e}")
        return {"error": 1, "message": str(e)}


@router.post("/onlyoffice/token/{type}/{id}")
async def generate_onlyoffice_token(
    type: str = Path(..., regex="^(candidate|job_post)$"),
    id: str = Path(...),
    current_user: User = Depends(get_current_active_user),
    payload: Dict = Body(...),
    db: Session = Depends(get_db)
):
    try:
        if type == "candidate":
            if not is_user_allowed_to_access_candidate(current_user, id, db):
                raise HTTPException(status_code=403, detail="Not authorized")
            candidate = get_candidate_service(id, db)
            blob_url = candidate.generated_docx_url
        elif type == "job_post":
            if not is_user_allowed_to_access_job_post(current_user, id, db):
                raise HTTPException(status_code=403, detail="Not authorized")
            job_post = get_job_post_service(id, db)
            blob_url = job_post.generated_docx_url

        backend_url = os.getenv("BACKEND_URL")
        timestamp = int(dt.now(tz=dt.timezone.utc).timestamp())
        document_key = f"{type}_{id}_{timestamp}"

        env = os.getenv("DB_ENV", "default")
        container = os.getenv(f"{env.upper()}_BLOB_CONTAINER")
        account_name = os.getenv(f"{env.upper()}_BLOB_ACT_NAME")
        account_key = os.getenv(f"{env.upper()}_BLOB_ACT_KEY")

        blob_name = blob_url.split(f"{container}/")[1]
        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=container,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True, write=True),
            expiry=dt.now(tz=dt.timezone.utc) + timedelta(hours=1)
        )

        blob_url = f"{blob_url}?{sas_token}"
        parsed_url = urlparse(blob_url)
        query_params = parse_qsl(parsed_url.query)
        encoded_query = urlencode(query_params, doseq=True, safe=':', quote_via=quote)
        blob_url = urlunparse(parsed_url._replace(query=encoded_query))

        jwt_payload = {
            "document": {
                "fileType": "docx",
                "key": f"{dt.now().strftime('%Y%m%d%H%M%S')}{blob_name}__{type}__{id}__{current_user.sub}",
                "title": blob_name,
                "url": f"{backend_url}/project/proxy_document?blob_url={blob_url}",
                "permissions": {...},
            },
            "documentType": "word",
            "editorConfig": {...},
        }

        secret_key = os.getenv("ONLY_OFFICE_SECRET_KEY")
        if not secret_key:
            raise HTTPException(status_code=500, detail="OnlyOffice secret key not configured")
        token = jwt.encode(jwt_payload, secret_key, algorithm="HS256")
        
        return {"token": token, "blob_url": blob_url}
    except Exception as e:
        logger.error(f"Error generating OnlyOffice token: {e}")
        raise HTTPException(status_code=400, detail=str(e))



@router.get("/proxy_document")
async def proxy_document(
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        # Get the full URL and extract blob_url more safely
        full_url = str(request.url)
        blob_url_start = full_url.find('blob_url=') + 9
        encoded_blob_url = full_url[blob_url_start:]
        
        # Decode the URL only once and preserve special characters
        decoded_url = urllib.parse.unquote(encoded_blob_url)
        logger.info(f"Accessing blob URL: {decoded_url}")
        
        async with httpx.AsyncClient() as client:
            # Pass the decoded URL directly to the request
            response = await client.get(
                decoded_url,
                # headers={
                #     'x-ms-version': '2020-04-08',
                #     'Accept': 'application/json'
                # },
                follow_redirects=True
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch document: {response.status_code}")
                logger.error(f"Response content: {response.text}")
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch document")

            return StreamingResponse(
                io.BytesIO(response.content),
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={
                    "Content-Disposition": "attachment; filename=document.docx",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Expose-Headers": "Content-Disposition"
                }
            )

    except Exception as e:
        logger.error(f"Error proxying document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to proxy document: {str(e)}")

app.include_router(router)
