# Share your collator metrics

Requires polkadot-sdk `stable2609` or newer, started with `--enable-hop`.

Add a `/metrics` route to the reverse proxy that serves your `wss://` RPC
endpoint, reload the proxy, and send us the URL
(e.g. `https://bulletin.example.org/metrics`). Do not add `--prometheus-external`.

nginx, in the `server` block:

```nginx
location = /metrics {
    allow 51.159.191.39;
    deny all;
    proxy_pass http://127.0.0.1:9615/metrics;
}
```

Caddy, in the site block, before other handlers:

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

Check: `curl https://<your-domain>/metrics` from any other machine returns `403`.

To stop sharing, remove the route and reload the proxy.
