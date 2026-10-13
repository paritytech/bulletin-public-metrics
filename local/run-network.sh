#!/usr/bin/env bash
# Starts the local network with polkadot-sdk stable2609 binaries.
set -euo pipefail
cd "$(dirname "$0")"
BIN=~/github/polkadot-bulletin-chain/.polkadot-binaries
NODE=$BIN/polkadot-node/polkadot-stable2609/darwin-aarch64
ZOMBIE=$BIN/zombienet/v1.3.138/darwin-aarch64/zombienet
export PATH="$NODE:$PATH"
POLKADOT_BINARY_PATH=$NODE/polkadot \
POLKADOT_PARACHAIN_BINARY_PATH=$NODE/polkadot-omni-node \
  "$ZOMBIE" -p native spawn network.toml
