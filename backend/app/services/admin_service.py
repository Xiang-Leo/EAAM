"""
backend/app/services/admin_service.py
-------------------------------------
Authentication, upload, and import helpers for the admin workflow.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

import pandas as pd
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    AdminSession,
    AdminUpload,
    AdminUser,
    AuditLog,
    BackupJob,
    DataImportJob,
    FunctionalAbundance,
    FunctionalFeature,
    Sample,
    Taxon,
    TaxonomyAbundance,
)

PBKDF2_ITERATIONS = 200_000
ALLOWED_EXTENSIONS = {".csv", ".tsv"}


def log_audit(
    db: Session,
    user: AdminUser | None,
    action: str,
    target_type: str | None = None,
    target_id: str | int | None = None,
    status_value: str = "success",
    detail: str | dict | None = None,
) -> None:
    if isinstance(detail, dict):
        detail_text = json.dumps(detail, ensure_ascii=False)
    else:
        detail_text = detail
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            username=user.username if user else None,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            status=status_value,
            detail=detail_text,
        )
    )
    db.commit()


def _hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt, digest = stored_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations),
    ).hex()
    return hmac.compare_digest(candidate, digest)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def ensure_default_admin(db: Session) -> None:
    settings = get_settings()
    existing = db.query(AdminUser).filter(AdminUser.username == settings.ADMIN_USERNAME).first()
    if existing:
        return
    db.add(
        AdminUser(
            username=settings.ADMIN_USERNAME,
            password_hash=_hash_password(settings.ADMIN_PASSWORD),
            role="admin",
        )
    )
    db.commit()


def login(db: Session, username: str, password: str) -> tuple[str, AdminUser, datetime]:
    ensure_default_admin(db)
    user = db.query(AdminUser).filter(AdminUser.username == username).first()
    if user is None or not _verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=get_settings().ADMIN_TOKEN_TTL_HOURS)
    db.add(AdminSession(token_hash=_hash_token(token), user_id=user.id, expires_at=expires_at))
    db.commit()
    log_audit(db, user, "admin.login", "admin_user", user.id)
    return token, user, expires_at


def create_admin_user(db: Session, current_user: AdminUser, username: str, password: str, role: str) -> AdminUser:
    username = username.strip()
    if not username:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Username is required.")
    if len(password) < 8:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password must be at least 8 characters.")
    existing = db.query(AdminUser).filter(AdminUser.username == username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Admin username already exists.")
    user = AdminUser(username=username, password_hash=_hash_password(password), role=role or "admin")
    db.add(user)
    db.commit()
    db.refresh(user)
    log_audit(db, current_user, "admin.create_user", "admin_user", user.id, detail={"username": username, "role": role})
    return user


def list_admin_users(db: Session) -> list[AdminUser]:
    return db.query(AdminUser).order_by(AdminUser.created_at.desc()).all()


def get_user_by_token(db: Session, token: str) -> AdminUser:
    session = (
        db.query(AdminSession)
        .filter(AdminSession.token_hash == _hash_token(token))
        .filter(AdminSession.expires_at > datetime.utcnow())
        .first()
    )
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin session is missing or expired.",
        )
    user = db.query(AdminUser).filter(AdminUser.id == session.user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin user not found.")
    return user


def infer_data_type(filename: str, data_type: str = "auto") -> str:
    if data_type and data_type != "auto":
        return data_type
    lower = filename.lower()
    if "metadata" in lower or "sample" in lower:
        return "samples"
    if "genefamil" in lower or "_ko_" in lower or "ko" in lower:
        return "gene_family"
    if "pathabundance" in lower or "pathway" in lower:
        return "pathway"
    return "unknown"


def _safe_filename(filename: str) -> str:
    stem = Path(filename).stem
    suffix = Path(filename).suffix.lower()
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._") or "upload"
    return f"{cleaned}_{uuid.uuid4().hex[:12]}{suffix}"


def save_upload(db: Session, file: UploadFile, data_type: str, user: AdminUser) -> AdminUpload:
    original = file.filename or "upload"
    suffix = Path(original).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only CSV and TSV files are supported.",
        )

    upload_dir = Path(get_settings().ADMIN_UPLOAD_DIR).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)

    stored = _safe_filename(original)
    path = upload_dir / stored
    with path.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    record = AdminUpload(
        original_filename=original,
        stored_filename=stored,
        path=str(path),
        content_type=file.content_type,
        size_bytes=path.stat().st_size,
        data_type=infer_data_type(original, data_type),
        uploaded_by=user.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    log_audit(db, user, "upload.create", "upload", record.id, detail={"filename": original, "data_type": record.data_type})
    return record


def list_uploads(db: Session) -> list[AdminUpload]:
    return db.query(AdminUpload).order_by(AdminUpload.created_at.desc()).all()


def list_jobs(db: Session) -> list[DataImportJob]:
    return db.query(DataImportJob).order_by(DataImportJob.created_at.desc()).all()


def list_backups(db: Session) -> list[BackupJob]:
    return db.query(BackupJob).order_by(BackupJob.created_at.desc()).all()


def list_audit_logs(db: Session, limit: int = 100) -> list[AuditLog]:
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()


def _write_report(path: Path, lines: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_table(path: Path, sep: str) -> pd.DataFrame:
    return pd.read_csv(path, sep=sep, dtype=str, keep_default_na=False)


def _read_header(path: Path, sep: str) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        first_line = handle.readline().rstrip("\n\r")
    return first_line.split(sep)


def _mapping_value(mapping: dict | None, key: str, default: str) -> str:
    if not mapping:
        return default
    value = mapping.get(key)
    return str(value).strip() if value else default


def preview_upload(db: Session, upload: AdminUpload, max_rows: int = 5) -> dict:
    data_type = infer_data_type(upload.original_filename, upload.data_type)
    path = Path(upload.path)
    sep = "\t" if path.suffix.lower() == ".tsv" else ","
    header = _read_header(path, sep)
    df = _read_table(path, sep).head(max_rows)
    rows = df.to_dict(orient="records")
    sample_ids = set(_sample_map(db))

    if data_type == "samples":
        required = ["sample_id", "province", "region", "dynasty"]
        sample_columns: list[str] = []
    elif data_type == "gene_family":
        required = ["feature_id"]
        sample_columns = header[1:]
    elif data_type == "pathway":
        required = ["feature_id", "feature_name", "stratification"]
        sample_columns = header[3:]
    else:
        required = []
        sample_columns = []

    validation = []
    missing_required = [col for col in required if col not in header]
    if missing_required:
        validation.append(f"Missing expected columns: {', '.join(missing_required)}")
    if sample_columns:
        validation.extend(_validate_sample_columns(sample_columns, sample_ids))

    return {
        "upload_id": upload.id,
        "filename": upload.original_filename,
        "data_type": data_type,
        "columns": header,
        "required_fields": required,
        "sample_columns": sample_columns,
        "preview_rows": rows,
        "validation": validation,
    }


def _sample_map(db: Session) -> dict[str, int]:
    return {sample.sample_id: sample.id for sample in db.query(Sample).all()}


def _validate_sample_columns(columns: list[str], sample_ids: set[str]) -> list[str]:
    errors: list[str] = []
    seen: dict[str, int] = {}
    for index, name in enumerate(columns, start=1):
        if not name.strip():
            errors.append(f"Empty sample column at position {index}.")
            continue
        seen[name] = seen.get(name, 0) + 1
    for name, count in seen.items():
        if count > 1:
            errors.append(f"Duplicate sample column: {name} appears {count} times.")
    missing = sorted({name for name in columns if name.strip()} - sample_ids)
    if missing:
        errors.append(f"Sample IDs not found in samples table: {', '.join(missing[:50])}")
        if len(missing) > 50:
            errors.append(f"... and {len(missing) - 50} more missing sample IDs.")
    return errors


def _to_float(value: str, row_number: int, column: str, errors: list[str]) -> float:
    if value == "":
        return 0.0
    try:
        return float(value)
    except ValueError:
        errors.append(f"Invalid abundance at row {row_number}, column {column}: {value!r}")
        return 0.0


def _upsert_samples(db: Session, path: Path, mapping: dict | None = None) -> tuple[int, list[str]]:
    df = _read_table(path, ",")
    rename = {
        _mapping_value(mapping, "sample_id", "sample_id"): "sample_id",
        _mapping_value(mapping, "province", "province"): "province",
        _mapping_value(mapping, "region", "region"): "region",
        _mapping_value(mapping, "dynasty", "dynasty"): "dynasty",
        _mapping_value(mapping, "period", "period"): "period",
        _mapping_value(mapping, "estimated_year", "estimated_year"): "estimated_year",
        _mapping_value(mapping, "sex", "sex"): "sex",
        _mapping_value(mapping, "subsistence_pattern", "subsistence_pattern"): "subsistence_pattern",
        _mapping_value(mapping, "site_name", "site_name"): "site_name",
        _mapping_value(mapping, "latitude", "latitude"): "latitude",
        _mapping_value(mapping, "longitude", "longitude"): "longitude",
        _mapping_value(mapping, "source", "source"): "source",
        _mapping_value(mapping, "source_url", "source_url"): "source_url",
    }
    df = df.rename(columns={src: dst for src, dst in rename.items() if src in df.columns})
    required = {"sample_id", "province", "region", "dynasty"}
    errors: list[str] = []
    missing = required - set(df.columns)
    if missing:
        return 0, [f"samples metadata is missing required columns: {', '.join(sorted(missing))}"]

    inserted_or_updated = 0
    for _, row in df.iterrows():
        sid = str(row.get("sample_id", "")).strip()
        if not sid:
            errors.append("Encountered a row with empty sample_id.")
            continue

        sample = db.query(Sample).filter(Sample.sample_id == sid).first()
        if sample is None:
            sample = Sample(sample_id=sid)
            db.add(sample)

        def text(col: str) -> str | None:
            value = str(row.get(col, "")).strip()
            return value or None

        def integer(col: str) -> int | None:
            value = str(row.get(col, "")).strip()
            if not value:
                return None
            try:
                return int(float(value))
            except ValueError:
                errors.append(f"Invalid integer for sample {sid}, column {col}: {value!r}")
                return None

        def number(col: str) -> float | None:
            value = str(row.get(col, "")).strip()
            if not value:
                return None
            try:
                return float(value)
            except ValueError:
                errors.append(f"Invalid number for sample {sid}, column {col}: {value!r}")
                return None

        sample.province = text("province")
        sample.region = text("region")
        sample.dynasty = text("dynasty")
        sample.period = text("period")
        sample.estimated_year = integer("estimated_year")
        sample.sex = text("sex")
        sample.subsistence_pattern = text("subsistence_pattern")
        sample.site_name = text("site_name")
        sample.latitude = number("latitude")
        sample.longitude = number("longitude")
        sample.source = text("source_url") or text("source")
        inserted_or_updated += 1

    if errors:
        return 0, errors
    db.commit()
    return inserted_or_updated, []


def _get_or_create_feature(
    db: Session,
    feature_type: str,
    feature_id: str,
    feature_name: str | None,
    stratification: str,
    raw_name: str,
) -> FunctionalFeature:
    existing = (
        db.query(FunctionalFeature)
        .filter(
            FunctionalFeature.feature_type == feature_type,
            FunctionalFeature.feature_id == feature_id,
            FunctionalFeature.stratification == stratification,
        )
        .first()
    )
    if existing:
        if feature_name and not existing.feature_name:
            existing.feature_name = feature_name
        return existing
    feature = FunctionalFeature(
        feature_type=feature_type,
        feature_id=feature_id,
        feature_name=feature_name,
        stratification=stratification,
        raw_name=raw_name,
    )
    db.add(feature)
    db.flush()
    return feature


def _import_gene_family(db: Session, upload: AdminUpload, mapping: dict | None = None) -> tuple[int, list[str]]:
    path = Path(upload.path)
    raw_header = _read_header(path, "\t")
    feature_col = _mapping_value(mapping, "feature_id", "feature_id")
    raw_errors = _validate_sample_columns([col for col in raw_header if col != feature_col], set(_sample_map(db)))
    if raw_errors:
        return 0, raw_errors

    df = _read_table(path, "\t")
    errors: list[str] = []
    if feature_col not in df.columns:
        return 0, [f"KO table must contain feature_id column '{feature_col}'."]
    if feature_col != "feature_id":
        df = df.rename(columns={feature_col: "feature_id"})

    sample_columns = [c for c in df.columns if c != "feature_id"]
    sample_ids = _sample_map(db)
    errors.extend(_validate_sample_columns(sample_columns, set(sample_ids)))
    if errors:
        return 0, errors

    db.query(FunctionalAbundance).filter(FunctionalAbundance.source_upload_id == upload.id).delete()
    inserted = 0
    batch: list[dict] = []

    for row_index, row in df.iterrows():
        raw_feature_id = str(row["feature_id"]).strip()
        if not raw_feature_id:
            errors.append(f"Empty feature_id at row {row_index + 2}.")
            continue
        feature = _get_or_create_feature(
            db,
            feature_type="gene_family",
            feature_id=raw_feature_id,
            feature_name=None,
            stratification="unstratified",
            raw_name=raw_feature_id,
        )
        for sample_col in sample_columns:
            abundance = _to_float(str(row[sample_col]).strip(), row_index + 2, sample_col, errors)
            batch.append(
                {
                    "sample_id": sample_ids[sample_col],
                    "feature_id": feature.id,
                    "abundance": abundance,
                    "source_upload_id": upload.id,
                }
            )
            if len(batch) >= 5000:
                db.bulk_insert_mappings(FunctionalAbundance, batch)
                inserted += len(batch)
                batch.clear()

    if errors:
        db.rollback()
        return 0, errors
    if batch:
        db.bulk_insert_mappings(FunctionalAbundance, batch)
        inserted += len(batch)
    db.commit()
    return inserted, []


def _import_pathway(db: Session, upload: AdminUpload, mapping: dict | None = None) -> tuple[int, list[str]]:
    path = Path(upload.path)
    raw_header = _read_header(path, "\t")
    feature_id_col = _mapping_value(mapping, "feature_id", "feature_id")
    feature_name_col = _mapping_value(mapping, "feature_name", "feature_name")
    stratification_col = _mapping_value(mapping, "stratification", "stratification")
    metadata_cols = {feature_id_col, feature_name_col, stratification_col}
    raw_errors = _validate_sample_columns([col for col in raw_header if col not in metadata_cols], set(_sample_map(db)))
    if raw_errors:
        return 0, raw_errors

    df = _read_table(path, "\t")
    required = {"feature_id", "feature_name", "stratification"}
    errors: list[str] = []
    rename = {
        feature_id_col: "feature_id",
        feature_name_col: "feature_name",
        stratification_col: "stratification",
    }
    df = df.rename(columns={src: dst for src, dst in rename.items() if src in df.columns})
    missing = required - set(df.columns)
    if missing:
        return 0, [f"Pathway table is missing required columns: {', '.join(sorted(missing))}"]

    sample_columns = [c for c in df.columns if c not in required]
    sample_ids = _sample_map(db)
    errors.extend(_validate_sample_columns(sample_columns, set(sample_ids)))
    if errors:
        return 0, errors

    db.query(FunctionalAbundance).filter(FunctionalAbundance.source_upload_id == upload.id).delete()
    inserted = 0
    batch: list[dict] = []

    for row_index, row in df.iterrows():
        feature_id = str(row["feature_id"]).strip()
        feature_name = str(row["feature_name"]).strip()
        stratification = str(row["stratification"]).strip() or "unstratified"
        if not feature_id:
            errors.append(f"Empty feature_id at row {row_index + 2}.")
            continue
        raw_name = f"{feature_id}: {feature_name}|{stratification}"
        feature = _get_or_create_feature(
            db,
            feature_type="pathway",
            feature_id=feature_id,
            feature_name=feature_name or None,
            stratification=stratification,
            raw_name=raw_name,
        )
        for sample_col in sample_columns:
            abundance = _to_float(str(row[sample_col]).strip(), row_index + 2, sample_col, errors)
            batch.append(
                {
                    "sample_id": sample_ids[sample_col],
                    "feature_id": feature.id,
                    "abundance": abundance,
                    "source_upload_id": upload.id,
                }
            )
            if len(batch) >= 5000:
                db.bulk_insert_mappings(FunctionalAbundance, batch)
                inserted += len(batch)
                batch.clear()

    if errors:
        db.rollback()
        return 0, errors
    if batch:
        db.bulk_insert_mappings(FunctionalAbundance, batch)
        inserted += len(batch)
    db.commit()
    return inserted, []


def run_import(db: Session, upload: AdminUpload, user: AdminUser, field_mapping: dict | None = None) -> DataImportJob:
    data_type = infer_data_type(upload.original_filename, upload.data_type)
    job = DataImportJob(
        upload_id=upload.id,
        data_type=data_type,
        status="running",
        created_by=user.id,
        field_mapping=json.dumps(field_mapping or {}, ensure_ascii=False),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    upload_path = Path(upload.path)
    report_dir = upload_path.parent / "reports"
    log_path = report_dir / f"import_{job.id}.log"
    error_path = report_dir / f"import_{job.id}_errors.txt"

    log_lines = [
        f"Import job: {job.id}",
        f"File: {upload.original_filename}",
        f"Data type: {data_type}",
        f"Started at: {job.created_at.isoformat()}Z",
    ]

    try:
        if data_type == "samples":
            count, errors = _upsert_samples(db, upload_path, field_mapping)
            success_message = f"Imported or updated {count} samples."
        elif data_type == "gene_family":
            count, errors = _import_gene_family(db, upload, field_mapping)
            success_message = f"Imported {count} gene-family abundance records."
        elif data_type == "pathway":
            count, errors = _import_pathway(db, upload, field_mapping)
            success_message = f"Imported {count} pathway abundance records."
        else:
            errors = [f"Cannot infer data type for file: {upload.original_filename}"]
            success_message = ""

        if errors:
            _write_report(error_path, errors)
            job.status = "failed"
            job.message = f"Import failed with {len(errors)} validation error(s)."
            job.error_report_path = str(error_path)
            log_lines.extend(["Status: failed", job.message, f"Error report: {error_path}"])
        else:
            job.status = "success"
            job.message = success_message
            log_lines.extend(["Status: success", success_message])
    except Exception as exc:
        db.rollback()
        _write_report(error_path, [f"Unexpected import error: {exc}"])
        job.status = "failed"
        job.message = f"Unexpected import error: {exc}"
        job.error_report_path = str(error_path)
        log_lines.extend(["Status: failed", job.message])

    job.completed_at = datetime.utcnow()
    job.log_path = str(log_path)
    _write_report(log_path, log_lines)
    db.add(job)
    db.commit()
    db.refresh(job)
    log_audit(db, user, "import.run", "import_job", job.id, status_value=job.status, detail={"upload_id": upload.id, "message": job.message})
    return job


def _sqlite_database_path() -> Path:
    url = get_settings().DATABASE_URL
    if not url.startswith("sqlite"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Database backup and restore currently support SQLite deployments only.",
        )
    if url.startswith("sqlite:////"):
        raw_path = "/" + url.removeprefix("sqlite:////")
    elif url.startswith("sqlite:///"):
        raw_path = url.removeprefix("sqlite:///")
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported SQLite database URL: {url}",
        )
    return Path(raw_path).resolve()


def _backup_dir() -> Path:
    path = Path(get_settings().ADMIN_UPLOAD_DIR).resolve() / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def create_database_backup(db: Session, user: AdminUser, label: str | None = None) -> BackupJob:
    source = _sqlite_database_path()
    if not source.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Database file not found: {source}")

    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_label = re.sub(r"[^A-Za-z0-9_.-]+", "_", (label or "manual")).strip("._") or "manual"
    filename = f"eaam_{safe_label}_{stamp}.db"
    destination = _backup_dir() / filename
    shutil.copy2(source, destination)

    backup = BackupJob(
        status="success",
        action="backup",
        filename=filename,
        path=str(destination),
        size_bytes=destination.stat().st_size,
        message=f"Backup created from {source}.",
        created_by=user.id,
    )
    db.add(backup)
    db.commit()
    db.refresh(backup)
    log_audit(db, user, "backup.create", "backup", backup.id, detail={"filename": filename})
    return backup


def restore_database_backup(db: Session, backup_id: int, user: AdminUser) -> BackupJob:
    backup = db.query(BackupJob).filter(BackupJob.id == backup_id, BackupJob.action == "backup").first()
    if backup is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found.")

    source = Path(backup.path)
    if not source.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup file is missing.")

    destination = _sqlite_database_path()
    pre_restore_name = f"eaam_pre_restore_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.db"
    pre_restore_path = _backup_dir() / pre_restore_name

    # Ensure all pending ORM changes are flushed before replacing the SQLite file.
    db.commit()

    from app.database import engine

    engine.dispose()
    if destination.exists():
        shutil.copy2(destination, pre_restore_path)
    shutil.copy2(source, destination)

    restore_record = BackupJob(
        status="success",
        action="restore",
        filename=source.name,
        path=str(source),
        size_bytes=source.stat().st_size,
        message=f"Restored backup {backup.id}. Pre-restore copy: {pre_restore_path.name}",
        created_by=user.id,
    )
    db.add(restore_record)
    db.commit()
    db.refresh(restore_record)
    log_audit(db, user, "backup.restore", "backup", backup.id, detail={"restore_record": restore_record.id})
    return restore_record


def delete_imported_data(db: Session, job_id: int) -> tuple[DataImportJob, int]:
    job = db.query(DataImportJob).filter(DataImportJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job not found.")
    if job.data_type == "samples":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Sample metadata imports cannot be deleted automatically because samples may be shared by other data.",
        )
    if job.data_type not in {"gene_family", "pathway"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Deleting imported data is not supported for data type: {job.data_type}",
        )

    deleted = (
        db.query(FunctionalAbundance)
        .filter(FunctionalAbundance.source_upload_id == job.upload_id)
        .delete(synchronize_session=False)
    )
    orphan_ids = [
        feature_id
        for (feature_id,) in (
            db.query(FunctionalFeature.id)
            .outerjoin(FunctionalAbundance, FunctionalAbundance.feature_id == FunctionalFeature.id)
            .filter(FunctionalAbundance.id.is_(None))
            .all()
        )
    ]
    if orphan_ids:
        db.query(FunctionalFeature).filter(FunctionalFeature.id.in_(orphan_ids)).delete(
            synchronize_session=False
        )

    job.status = "deleted"
    job.message = f"Deleted {deleted} functional abundance records from this import."
    job.completed_at = datetime.utcnow()
    db.add(job)
    db.commit()
    db.refresh(job)
    # caller records current user in the route because this helper historically did not need it
    return job, deleted


def update_sample_metadata(db: Session, user: AdminUser, sample_pk: int, values: dict) -> Sample:
    sample = db.query(Sample).filter(Sample.id == sample_pk).first()
    if sample is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample not found.")

    allowed = {
        "sample_id",
        "province",
        "region",
        "dynasty",
        "period",
        "estimated_year",
        "sex",
        "subsistence_pattern",
        "site_name",
        "latitude",
        "longitude",
        "source",
    }
    before = {field: getattr(sample, field) for field in allowed}
    for field, value in values.items():
        if field not in allowed:
            continue
        setattr(sample, field, value if value != "" else None)
    db.commit()
    db.refresh(sample)
    after = {field: getattr(sample, field) for field in allowed}
    changed = {field: {"before": before[field], "after": after[field]} for field in allowed if before[field] != after[field]}
    log_audit(db, user, "sample.update", "sample", sample.id, detail=changed)
    return sample


def get_admin_stats(db: Session) -> dict:
    database_path = _sqlite_database_path()
    database_size = database_path.stat().st_size if database_path.exists() else 0

    import_status_rows = (
        db.query(DataImportJob.status)
        .all()
    )
    status_counts: dict[str, int] = {}
    for (job_status,) in import_status_rows:
        status_counts[job_status] = status_counts.get(job_status, 0) + 1

    functional_by_type: dict[str, int] = {}
    for feature_type, count in (
        db.query(FunctionalFeature.feature_type, FunctionalFeature.id)
        .all()
    ):
        functional_by_type[feature_type] = functional_by_type.get(feature_type, 0) + 1

    return {
        "sample_count": db.query(Sample).count(),
        "taxon_count": db.query(Taxon).count(),
        "taxonomy_abundance_count": db.query(TaxonomyAbundance).count(),
        "functional_feature_count": db.query(FunctionalFeature).count(),
        "functional_abundance_count": db.query(FunctionalAbundance).count(),
        "upload_count": db.query(AdminUpload).count(),
        "import_job_count": db.query(DataImportJob).count(),
        "backup_count": db.query(BackupJob).filter(BackupJob.action == "backup").count(),
        "database_size_bytes": database_size,
        "database_path": str(database_path),
        "import_status_counts": status_counts,
        "functional_feature_counts": functional_by_type,
    }
