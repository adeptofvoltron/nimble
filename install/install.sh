#!/bin/sh
set -e

REPO="adeptofvoltron/nimble"
BINARY_NAME="nimble"
DEFAULT_INSTALL_DIR="/usr/local/bin"

# ── Detect OS ────────────────────────────────────────────────────────────────
OS=$(uname -s)
case "$OS" in
  Linux)  PLATFORM="linux" ;;
  Darwin) PLATFORM="darwin" ;;
  *)
    echo "Error: Unsupported operating system: $OS" >&2
    exit 1
    ;;
esac

# ── Detect arch (normalize aarch64 → arm64) ──────────────────────────────────
ARCH=$(uname -m)
case "$ARCH" in
  x86_64)          ARCH="x64" ;;
  aarch64 | arm64) ARCH="arm64" ;;
  *)
    echo "Error: Unsupported architecture: $ARCH" >&2
    exit 1
    ;;
esac

TARGET="${PLATFORM}-${ARCH}"

# ── Validate supported target ─────────────────────────────────────────────────
case "$TARGET" in
  linux-x64 | darwin-x64 | darwin-arm64)
    : ;;
  linux-arm64)
    echo "Error: Linux ARM64 is not yet supported. Only linux-x64 is available on Linux." >&2
    exit 1
    ;;
  *)
    echo "Error: Unsupported platform: $TARGET" >&2
    exit 1
    ;;
esac

# ── Detect WSL ───────────────────────────────────────────────────────────────
if [ -f /proc/version ] && grep -qi "microsoft" /proc/version; then
  echo "Detected WSL — using Linux installer (correct)."
fi

# ── Resolve install directory ─────────────────────────────────────────────────
INSTALL_DIR="${NIMBLE_INSTALL_DIR:-$DEFAULT_INSTALL_DIR}"

# ── Sudo check ────────────────────────────────────────────────────────────────
NEED_SUDO=false
if [ "$(id -u)" -ne 0 ]; then
  if ! [ -w "$INSTALL_DIR" ] 2>/dev/null; then
    NEED_SUDO=true
    if ! command -v sudo >/dev/null 2>&1; then
      echo "Error: Cannot write to \"$INSTALL_DIR\" and sudo is not available." >&2
      echo "       Set NIMBLE_INSTALL_DIR to a writable directory and retry." >&2
      exit 1
    fi
    echo "Nimble installs to \"$INSTALL_DIR\" and requires sudo. You may be prompted for your password."
    if ! sudo -v 2>/dev/null; then
      echo "Error: Could not obtain sudo. Set NIMBLE_INSTALL_DIR to a writable directory and retry." >&2
      exit 1
    fi
  fi
fi

# ── Fetch latest release tag ──────────────────────────────────────────────────
echo "Fetching latest Nimble release..."
LATEST=$(curl -fsSL "https://api.github.com/repos/${REPO}/releases/latest" \
  | grep '"tag_name"' | cut -d'"' -f4) || true

if [ -z "$LATEST" ]; then
  echo "Error: Could not reach GitHub Releases — if behind a proxy, set HTTPS_PROXY and retry." >&2
  exit 1
fi

case "$LATEST" in
  v*) : ;;
  *)
    echo "Error: Could not determine latest release tag (GitHub API may be rate-limiting — try again in a minute)." >&2
    exit 1
    ;;
esac

echo "Installing Nimble $LATEST ($TARGET)..."

# ── Build download URLs ───────────────────────────────────────────────────────
BASE_URL="https://github.com/${REPO}/releases/download/${LATEST}"
BINARY_URL="${BASE_URL}/nimble-${TARGET}"
CHECKSUM_URL="${BASE_URL}/nimble-${TARGET}.sha256"

# ── Download binary and checksum ──────────────────────────────────────────────
TMP_DIR=$(mktemp -d)
TMP_BIN="${TMP_DIR}/nimble"
TMP_SUM="${TMP_DIR}/nimble.sha256"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

download() {
  URL="$1"
  DEST="$2"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL --output "$DEST" "$URL" || return 1
  elif command -v wget >/dev/null 2>&1; then
    wget -q -O "$DEST" "$URL" || return 1
  else
    echo "Error: Neither curl nor wget found." >&2
    return 1
  fi
}

if ! download "$BINARY_URL" "$TMP_BIN"; then
  echo "Error: Could not reach GitHub Releases — if behind a proxy, set HTTPS_PROXY and retry." >&2
  exit 1
fi

if ! download "$CHECKSUM_URL" "$TMP_SUM"; then
  echo "Error: Could not reach GitHub Releases — if behind a proxy, set HTTPS_PROXY and retry." >&2
  exit 1
fi

# ── Verify SHA256 ─────────────────────────────────────────────────────────────
EXPECTED=$(awk '{print $1}' "$TMP_SUM")
if command -v sha256sum >/dev/null 2>&1; then
  ACTUAL=$(sha256sum "$TMP_BIN" | awk '{print $1}')
elif command -v shasum >/dev/null 2>&1; then
  ACTUAL=$(shasum -a 256 "$TMP_BIN" | awk '{print $1}')
else
  echo "Warning: No sha256sum or shasum found — skipping checksum verification." >&2
  ACTUAL="$EXPECTED"
fi

if [ "$ACTUAL" != "$EXPECTED" ]; then
  echo "Error: Download may be corrupted — retry the install." >&2
  exit 1
fi

# ── Install ───────────────────────────────────────────────────────────────────
chmod +x "$TMP_BIN"

mkdir -p "$INSTALL_DIR"

if [ "$NEED_SUDO" = true ]; then
  sudo mv "$TMP_BIN" "${INSTALL_DIR}/${BINARY_NAME}"
else
  mv "$TMP_BIN" "${INSTALL_DIR}/${BINARY_NAME}"
fi

echo ""
echo "Nimble installed! Open a new terminal to use it."
echo "  Run: nimble --help"
