#!/usr/bin/env bash
set -euo pipefail

OS_NAME=$(uname -s)

if [[ "$OS_NAME" == "Darwin" ]]; then
  echo "Detected macOS host. Installing dependencies via Homebrew."
  if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew not found. Please install Homebrew manually from https://brew.sh" >&2
    exit 1
  fi
  brew bundle --file=- <<'BREW'
tap "homebrew/cask"
tap "homebrew/cask-versions"
tap "homebrew/core"
brew "node@20"
brew "python@3.11"
brew "mitmproxy"
brew "carthage"
brew "watchman"
brew "apktool"
cask "android-sdk"
BREW
  for prefix in /usr/local /opt/homebrew; do
    if [[ -d "$prefix/opt/node@20" ]]; then
      export PATH="$prefix/opt/node@20/bin:$PATH"
    fi
    if [[ -d "$prefix/opt/python@3.11" ]]; then
      export PATH="$prefix/opt/python@3.11/libexec/bin:$PATH"
    fi
  done
  brew link --overwrite node@20 >/dev/null 2>&1 || true
  brew link --overwrite python@3.11 >/dev/null 2>&1 || true
else
  echo "Detected Linux host. Installing dependencies via apt."
  sudo apt-get update
  sudo apt-get install -y \
    nodejs npm \
    python3 python3-pip python3-venv \
    openjdk-17-jdk \
    mitmproxy \
    apktool \
    unzip zip wget git rsync
fi

echo "Installing Appium and platform dependencies"
npm install -g appium@next
appium driver install xcuitest || true
appium driver install uiautomator2 || true

if [[ -f automation/ios/package.json ]]; then
  npm install --prefix automation/ios
fi
if [[ -f automation/android/package.json ]]; then
  npm install --prefix automation/android
fi

pip3 install -r automation/ios/requirements.txt -r automation/android/requirements.txt 2>/dev/null || true

cat <<EOF
Bootstrap complete. Ensure the following are configured:
- Xcode command-line tools (macOS): xcode-select --install
- Required iOS simulators downloaded (e.g., Xcode -> Preferences -> Components)
- Android SDK + AVD created per .automation/config.yaml
