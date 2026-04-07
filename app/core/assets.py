from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ASSET_VERSION_FILE = REPO_ROOT / "frontend" / ".asset-version"
DEFAULT_ASSET_VERSION = "miniapp_dev"


def get_asset_version() -> str:
    try:
        value = ASSET_VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return DEFAULT_ASSET_VERSION
    return value or DEFAULT_ASSET_VERSION
