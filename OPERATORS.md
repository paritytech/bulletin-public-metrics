# Share your collator metrics with the public Bulletin dashboard

Parity runs a public dashboard of Bulletin collator metrics: liveness, bitswap
(IPFS) serving and HOP. Sharing is voluntary. The metrics contain no personal
data.

## Requirements

- polkadot-sdk `stable2609` or newer. Older releases do not export the
  bitswap metrics; releases before `stable2606-2` also lack the HOP metrics.
- `--enable-hop` for the HOP metrics.
- The reverse proxy you already run for the collator's `wss://` RPC endpoint.

## Steps

1. Add a `/metrics` route to your reverse proxy that forwards to the node's
   Prometheus port and allows only Parity's scraper IP, `51.159.191.39`.
   Your node keeps running; no restart, no new port, no new certificate.
2. Reload the proxy.
3. Send us the URL, e.g. `https://bulletin.example.org/metrics`.

The node's Prometheus port stays on localhost. Do not add `--prometheus-external`.

### nginx

Add to the `server` block that serves your `wss://` endpoint:

```nginx
location = /metrics {
    allow 51.159.191.39;
    deny all;
    proxy_pass http://127.0.0.1:9615/metrics;
}
```

Reload: `nginx -t && systemctl reload nginx`.

### Caddy

Add to the site block that serves your `wss://` endpoint, before other
handlers:

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

Reload: `systemctl reload caddy`.

## Check

From any other machine, `curl https://bulletin.example.org/metrics` must
return `403`. We confirm on our side that the scrape works.

## Stop sharing

Remove the route and reload the proxy.
