import shutil
from pathlib import Path
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.orm_models import Version

BASE_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = BASE_DIR / "artifacts"
DEPLOYMENTS_DIR = BASE_DIR / "deployments"

class ArtifactManager:
    @staticmethod
    def _model_folder(model_id: int, model_name: str) -> Path:
        """Return path for a model's artifact folder."""
        safe_name = model_name.replace(" ", "_")
        return ARTIFACTS_DIR / f"{model_id}_{safe_name}"

    @staticmethod
    def _version_folder(model_id: int, model_name: str, version: str) -> Path:
        """Return path for a specific version folder."""
        return ArtifactManager._model_folder(model_id, model_name) / "versions" / version

    @staticmethod
    async def save_version_file(model_id: int, model_name: str, file_path: Path, db: AsyncSession) -> tuple[str, str]:
        """
        Save uploaded file into artifacts/version folder.
        Auto-increments version number based on DB.
        Returns (artifact_uri, version_label).
        """
        # Query latest version for this model
        result = await db.execute(
            select(Version).where(Version.model_id == model_id).order_by(Version.created_at.desc())
        )
        latest_version = result.scalars().first()
        next_version_num = 1 if not latest_version else latest_version.model_id + 1
        version_label = f"v{next_version_num}"

        version_folder = ArtifactManager._version_folder(model_id, model_name, version_label)
        version_folder.mkdir(parents=True, exist_ok=True)

        dest_file = version_folder / file_path.name
        if dest_file.exists():
            # Avoid duplicacy by appending timestamp
            timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
            dest_file = version_folder / f"{file_path.stem}_{timestamp}{file_path.suffix}"

        shutil.copy(file_path, dest_file)
        return str(dest_file), version_label

    @staticmethod
    async def deploy_version(version_id: int, artifact_uri: str, environment: str) -> str:
        """Copy artifact into deployments/{environment}. Returns deployment path."""
        env_folder = DEPLOYMENTS_DIR / environment.lower()
        env_folder.mkdir(parents=True, exist_ok=True)

        src_file = Path(artifact_uri)
        if not src_file.exists():
            raise FileNotFoundError(f"Artifact not found: {artifact_uri}")

        dest_file = env_folder / src_file.name
        if dest_file.exists():
            # Avoid overwriting by appending timestamp
            timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
            dest_file = env_folder / f"{src_file.stem}_{timestamp}{src_file.suffix}"

        shutil.copy(src_file, dest_file)
        return str(dest_file)

    @staticmethod
    async def rollback_deployment(deployment_id: int, artifact_uri: str) -> str:
        """Move artifact into deployments/rollback folder."""
        rollback_folder = DEPLOYMENTS_DIR / "rollback"
        rollback_folder.mkdir(parents=True, exist_ok=True)

        src_file = Path(artifact_uri)
        if not src_file.exists():
            raise FileNotFoundError(f"Deployment artifact not found: {artifact_uri}")

        dest_file = rollback_folder / src_file.name
        if dest_file.exists():
            timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
            dest_file = rollback_folder / f"{src_file.stem}_{timestamp}{src_file.suffix}"

        shutil.copy(src_file, dest_file)
        return str(dest_file)

    @staticmethod
    async def retry_deployment(deployment_id: int, artifact_uri: str) -> str:
        """Copy artifact into deployments/retry folder."""
        retry_folder = DEPLOYMENTS_DIR / "retry"
        retry_folder.mkdir(parents=True, exist_ok=True)

        src_file = Path(artifact_uri)
        if not src_file.exists():
            raise FileNotFoundError(f"Deployment artifact not found: {artifact_uri}")

        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
        dest_file = retry_folder / f"{src_file.stem}_retry_{timestamp}{src_file.suffix}"

        shutil.copy(src_file, dest_file)
        return str(dest_file)
