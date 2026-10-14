# Metrics for the public Bulletin dashboard

Parity runs a public, read-only dashboard of Bulletin collator metrics: https://bulletin-metrics.security.parity.io. Sharing is voluntary. The metrics contain no personal data.

## What we need from you

1. Run polkadot-sdk `stable2609` or newer with `--enable-hop`.
2. Add one `/metrics` route to the reverse proxy that serves your `wss://` RPC endpoint. Allow only our scraper IP, `51.159.191.39`. No node restart, no new port, no new certificate. Do not add `--prometheus-external`.
3. Reload the proxy.
4. Tell us when it is live. We scrape your RPC domain plus `/metrics`, e.g. `wss://bulletin.example.org` → `https://bulletin.example.org/metrics`.

### nginx

In the `server` block that serves your `wss://` endpoint:

```nginx
location = /metrics {
    allow 51.159.191.39;
    deny all;
    proxy_pass http://127.0.0.1:9615/metrics;
}
```

Reload: `nginx -t && systemctl reload nginx`

### Caddy

In the site block that serves your `wss://` endpoint, before other handlers:

```caddy
@parity {
	path /metrics
	remote_ip 51.159.191.39
}
handle @parity {
	reverse_proxy 127.0.0.1:9615
}
handle /metrics {
	respond 403
}
```

Reload: `systemctl reload caddy`

### Check

From any machine other than `51.159.191.39`, `curl https://<your-domain>/metrics` must return `403`. We confirm the scrape on our side.

### Stop sharing

Remove the route and reload the proxy.

## What we collect (every 30 s)

- **Node:** block height, peer count, node version (`substrate_block_height`, `substrate_sub_libp2p_peers_count`, `substrate_build_info`).
- **Bitswap (IPFS) serving:** requests by outcome, bytes served, response time (`substrate_sub_libp2p_bitswap_*`).
- **HOP:** pool size and entries, promotions, backlog, RPC errors (`substrate_hop_*`).
- **RPC:** call counts and latency for the four HOP methods only (`hop_submit`, `hop_claim`, `hop_ack`, `hop_poolStatus`). We drop all other RPC methods at ingestion.
- **Reachability:** whether the scrape succeeded.
