#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: download_latest.sh [--workspace <path>] [--version <version>] [--url <url>] [--file <path>] [--out <dir>] [--release-notes <text>]

When no URL or file is supplied, a placeholder IPA is generated for pipeline smoke tests.
USAGE
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(cd "$SCRIPT_DIR/../../.." && pwd)"
VERSION="${SOURCE_VERSION:-}"
SOURCE_URL="${TEST_IPA_URL:-}"
SOURCE_FILE="${TEST_IPA_PATH:-}"
OUTPUT_ROOT=""
RELEASE_NOTES="${SOURCE_RELEASE_NOTES:-Sample build for automation smoke test}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace)
      WORKSPACE="$(cd "$2" && pwd)"
      shift 2
      ;;
    --version)
      VERSION="$2"
      shift 2
      ;;
    --url)
      SOURCE_URL="$2"
      shift 2
      ;;
    --file)
      SOURCE_FILE="$2"
      shift 2
      ;;
    --out)
      OUTPUT_ROOT="$2"
      shift 2
      ;;
    --release-notes)
      RELEASE_NOTES="$2"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

VERSION=${VERSION:-$(date +%Y%m%dT%H%M%SZ)}
OUTPUT_ROOT=${OUTPUT_ROOT:-$WORKSPACE/downloads/ios}
TARGET_DIR="$OUTPUT_ROOT/$VERSION"
mkdir -p "$TARGET_DIR"

filename="source.ipa"
if [[ -n "$SOURCE_URL" ]]; then
  filename="${SOURCE_URL##*/}"
  if [[ -z "$filename" || "$filename" == */ ]]; then
    filename="source-${VERSION}.ipa"
  fi
  dest="$TARGET_DIR/$filename"
  echo "Downloading IPA from $SOURCE_URL -> $dest"
  curl -fL "$SOURCE_URL" -o "$dest"
elif [[ -n "$SOURCE_FILE" ]]; then
  filename="$(basename "$SOURCE_FILE")"
  dest="$TARGET_DIR/$filename"
  echo "Copying IPA from $SOURCE_FILE -> $dest"
  cp "$SOURCE_FILE" "$dest"
else
  dest="$TARGET_DIR/dummy-${VERSION}.ipa"
  echo "Generating placeholder IPA at $dest"
  python3 - "$dest" <<'PY'
import sys
from pathlib import Path
import zipfile

dest = Path(sys.argv[1])
dest.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(dest, "w") as zf:
    zf.writestr(
        "Payload/Automation.app/Info.plist",
        """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">
<plist version=\"1.0\">
<dict>
  <key>CFBundleIdentifier</key>
  <string>com.example.automation</string>
  <key>CFBundleName</key>
  <string>Automation</string>
  <key>CFBundleShortVersionString</key>
  <string>0.0.0</string>
  <key>CFBundleVersion</key>
  <string>0</string>
</dict>
</plist>
""",
    )
    zf.writestr("Payload/Automation.app/dummy.txt", "Generated placeholder for pipeline smoke test\n")
print(dest)
PY
fi

echo "IPA stored at $dest"

if [[ -n "${GITHUB_ENV:-}" ]]; then
  {
    echo "IOS_BINARY_PATH=$dest"
    echo "IOS_BINARY_VERSION=$VERSION"
    echo "IOS_RELEASE_NOTES=$RELEASE_NOTES"
  } >> "$GITHUB_ENV"
fi

metadata_path="$TARGET_DIR/metadata.json"
python3 - "$dest" "$metadata_path" "$VERSION" "$RELEASE_NOTES" <<'PY'
import json
import sys
from pathlib import Path

source = Path(sys.argv[1])
metadata_path = Path(sys.argv[2])
version = sys.argv[3]
notes = sys.argv[4]

metadata = {
    "filename": source.name,
    "path": str(source),
    "version": version,
    "release_notes": notes,
    "size_bytes": source.stat().st_size,
}
metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
PY

echo "Metadata written to $metadata_path"
