"""
backend/app/api/routers/admin.py
--------------------------------
Admin endpoints for login, upload, import jobs, logs, and error reports.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AdminUpload, AdminUser, AuditLog, BackupJob, DataImportJob, Sample
from app.services import admin_service
from app.schemas.sample import SampleRead

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    expires_at: str
    username: str
    role: str


class UploadRead(BaseModel):
    id: int
    original_filename: str
    size_bytes: int
    data_type: str
    created_at: str


class JobRead(BaseModel):
    id: int
    upload_id: int
    data_type: str
    status: str
    message: Optional[str]
    created_at: str
    completed_at: Optional[str]
    has_error_report: bool


class BackupRead(BaseModel):
    id: int
    action: str
    status: str
    filename: str
    size_bytes: int
    message: Optional[str]
    created_at: str


class BackupRequest(BaseModel):
    label: Optional[str] = None


class ImportRequest(BaseModel):
    field_mapping: dict[str, str] = {}


class AdminUserCreate(BaseModel):
    username: str
    password: str
    role: str = "admin"


class AdminUserRead(BaseModel):
    id: int
    username: str
    role: str
    created_at: str


class AuditLogRead(BaseModel):
    id: int
    username: Optional[str]
    action: str
    target_type: Optional[str]
    target_id: Optional[str]
    status: str
    detail: Optional[str]
    created_at: str


class UploadPreview(BaseModel):
    upload_id: int
    filename: str
    data_type: str
    columns: list[str]
    required_fields: list[str]
    sample_columns: list[str]
    preview_rows: list[dict]
    validation: list[str]


class SampleUpdate(BaseModel):
    sample_id: Optional[str] = None
    province: Optional[str] = None
    region: Optional[str] = None
    dynasty: Optional[str] = None
    period: Optional[str] = None
    estimated_year: Optional[int] = None
    sex: Optional[str] = None
    subsistence_pattern: Optional[str] = None
    site_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    source: Optional[str] = None


class AdminStats(BaseModel):
    sample_count: int
    taxon_count: int
    taxonomy_abundance_count: int
    functional_feature_count: int
    functional_abundance_count: int
    upload_count: int
    import_job_count: int
    backup_count: int
    database_size_bytes: int
    database_path: str
    import_status_counts: dict[str, int]
    functional_feature_counts: dict[str, int]


def _serialize_upload(upload: AdminUpload) -> UploadRead:
    return UploadRead(
        id=upload.id,
        original_filename=upload.original_filename,
        size_bytes=upload.size_bytes,
        data_type=upload.data_type,
        created_at=upload.created_at.isoformat() + "Z",
    )


def _serialize_job(job: DataImportJob) -> JobRead:
    return JobRead(
        id=job.id,
        upload_id=job.upload_id,
        data_type=job.data_type,
        status=job.status,
        message=job.message,
        created_at=job.created_at.isoformat() + "Z",
        completed_at=job.completed_at.isoformat() + "Z" if job.completed_at else None,
        has_error_report=bool(job.error_report_path),
    )


def _serialize_backup(backup: BackupJob) -> BackupRead:
    return BackupRead(
        id=backup.id,
        action=backup.action,
        status=backup.status,
        filename=backup.filename,
        size_bytes=backup.size_bytes,
        message=backup.message,
        created_at=backup.created_at.isoformat() + "Z",
    )


def _serialize_admin_user(user: AdminUser) -> AdminUserRead:
    return AdminUserRead(
        id=user.id,
        username=user.username,
        role=user.role,
        created_at=user.created_at.isoformat() + "Z",
    )


def _serialize_audit_log(log: AuditLog) -> AuditLogRead:
    return AuditLogRead(
        id=log.id,
        username=log.username,
        action=log.action,
        target_type=log.target_type,
        target_id=log.target_id,
        status=log.status,
        detail=log.detail,
        created_at=log.created_at.isoformat() + "Z",
    )


def get_current_admin(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token is required.",
        )
    token = authorization.split(" ", 1)[1].strip()
    return admin_service.get_user_by_token(db, token)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    token, user, expires_at = admin_service.login(db, payload.username, payload.password)
    return LoginResponse(
        token=token,
        expires_at=expires_at.isoformat() + "Z",
        username=user.username,
        role=user.role,
    )


@router.get("/me")
def me(user=Depends(get_current_admin)):
    return {"username": user.username, "role": user.role}


@router.post("/uploads", response_model=UploadRead)
def upload_file(
    file: UploadFile = File(...),
    data_type: str = Form("auto"),
    db: Session = Depends(get_db),
    user=Depends(get_current_admin),
) -> UploadRead:
    upload = admin_service.save_upload(db, file, data_type, user)
    return _serialize_upload(upload)


@router.get("/uploads", response_model=list[UploadRead])
def get_uploads(
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
) -> list[UploadRead]:
    return [_serialize_upload(upload) for upload in admin_service.list_uploads(db)]


@router.delete("/uploads/{upload_id}")
def delete_upload(
    upload_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_admin),
) -> dict:
    deleted_abundance = admin_service.delete_upload(db, upload_id, user)
    return {"status": "deleted", "deleted_abundance": deleted_abundance}


@router.get("/uploads/{upload_id}/preview", response_model=UploadPreview)
def preview_upload(
    upload_id: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
) -> dict:
    upload = db.query(AdminUpload).filter(AdminUpload.id == upload_id).first()
    if upload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found.")
    return admin_service.preview_upload(db, upload)


@router.post("/uploads/{upload_id}/import", response_model=JobRead)
def import_upload(
    upload_id: int,
    background_tasks: BackgroundTasks,
    payload: ImportRequest | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_admin),
) -> JobRead:
    upload = db.query(AdminUpload).filter(AdminUpload.id == upload_id).first()
    if upload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found.")
    field_mapping = payload.field_mapping if payload else {}
    job = admin_service.create_import_job(db, upload, user, field_mapping)
    background_tasks.add_task(admin_service.run_import_background, job.id, upload.id, user.id, field_mapping)
    return _serialize_job(job)


@router.get("/imports", response_model=list[JobRead])
def get_import_jobs(
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
) -> list[JobRead]:
    return [_serialize_job(job) for job in admin_service.list_jobs(db)]


@router.delete("/imports/{job_id}/data", response_model=JobRead)
def delete_import_data(
    job_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_admin),
) -> JobRead:
    job, _deleted = admin_service.delete_imported_data(db, job_id)
    admin_service.log_audit(db, user, "import.delete_data", "import_job", job.id, detail={"deleted": _deleted})
    return _serialize_job(job)


@router.get("/imports/{job_id}/log")
def download_log(
    job_id: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
):
    job = db.query(DataImportJob).filter(DataImportJob.id == job_id).first()
    if job is None or not job.log_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import log not found.")
    path = Path(job.log_path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import log file is missing.")
    return FileResponse(path, filename=path.name, media_type="text/plain")


@router.get("/imports/{job_id}/errors")
def download_errors(
    job_id: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
):
    job = db.query(DataImportJob).filter(DataImportJob.id == job_id).first()
    if job is None or not job.error_report_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Error report not found.")
    path = Path(job.error_report_path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Error report file is missing.")
    return FileResponse(path, filename=path.name, media_type="text/plain")


@router.get("/stats", response_model=AdminStats)
def get_stats(
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
) -> dict:
    return admin_service.get_admin_stats(db)


@router.post("/backups", response_model=BackupRead)
def create_backup(
    payload: BackupRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_admin),
) -> BackupRead:
    backup = admin_service.create_database_backup(db, user, payload.label)
    return _serialize_backup(backup)


@router.get("/backups", response_model=list[BackupRead])
def get_backups(
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
) -> list[BackupRead]:
    return [_serialize_backup(backup) for backup in admin_service.list_backups(db)]


@router.post("/backups/{backup_id}/restore", response_model=BackupRead)
def restore_backup(
    backup_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_admin),
) -> BackupRead:
    backup = admin_service.restore_database_backup(db, backup_id, user)
    return _serialize_backup(backup)


@router.get("/backups/{backup_id}/download")
def download_backup(
    backup_id: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
):
    backup = db.query(BackupJob).filter(BackupJob.id == backup_id).first()
    if backup is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found.")
    path = Path(backup.path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup file is missing.")
    return FileResponse(path, filename=backup.filename, media_type="application/octet-stream")


@router.get("/samples", response_model=list[SampleRead])
def admin_list_samples(
    limit: int = 50,
    offset: int = 0,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
) -> list[SampleRead]:
    query = db.query(Sample)
    if q:
        like = f"%{q}%"
        query = query.filter(Sample.sample_id.like(like))
    rows = query.order_by(Sample.sample_id).offset(offset).limit(limit).all()
    return [SampleRead.model_validate(row) for row in rows]


@router.patch("/samples/{sample_pk}", response_model=SampleRead)
def admin_update_sample(
    sample_pk: int,
    payload: SampleUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_admin),
) -> SampleRead:
    sample = admin_service.update_sample_metadata(
        db,
        user,
        sample_pk,
        payload.model_dump(exclude_unset=True),
    )
    return SampleRead.model_validate(sample)


@router.get("/users", response_model=list[AdminUserRead])
def admin_list_users(
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
) -> list[AdminUserRead]:
    return [_serialize_admin_user(user) for user in admin_service.list_admin_users(db)]


@router.post("/users", response_model=AdminUserRead)
def admin_create_user(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_admin),
) -> AdminUserRead:
    created = admin_service.create_admin_user(db, user, payload.username, payload.password, payload.role)
    return _serialize_admin_user(created)


@router.get("/audit-logs", response_model=list[AuditLogRead])
def admin_audit_logs(
    limit: int = 100,
    db: Session = Depends(get_db),
    _user=Depends(get_current_admin),
) -> list[AuditLogRead]:
    return [_serialize_audit_log(log) for log in admin_service.list_audit_logs(db, limit)]
