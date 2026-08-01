# Publishing Ouroboros at ouroboros.beart.cc

Public gallery = **static GitHub Pages** with demo runs baked in.
Live API remains available via Docker.

## Live URLs

| URL | Status |
|-----|--------|
| https://ouroboros.beart.cc/ | **Primary** — Cloudflare CNAME → `damasker.github.io` (DNS only) |
| https://damasker.github.io/ouroboros/ | Redirects to custom domain once Pages `cname` is set |

Repo: https://github.com/Damasker/ouroboros

## 1. Cloudflare DNS for `ouroboros.beart.cc`

`beart.cc` already uses Cloudflare NS (`lex` / `zainab`).

In [Cloudflare Dashboard](https://dash.cloudflare.com) → **beart.cc** → **DNS** → **Add record**:

| Type  | Name        | Target               | Proxy status      | TTL  |
|-------|-------------|----------------------|-------------------|------|
| CNAME | `ouroboros` | `damasker.github.io` | **DNS only** (grey) | Auto |

Then in GitHub → repo **Settings → Pages → Custom domain** set `ouroboros.beart.cc`
(or re-deploy with `WRITE_CNAME=1`).

Enable **Enforce HTTPS** after the certificate provisions (~1–15 min).

Optional API (if you have a Cloudflare token with `Zone.DNS` edit):

```bash
export CF_API_TOKEN=...
export CF_ZONE_ID=...   # Zone ID for beart.cc
curl -X POST "https://api.cloudflare.com/client/v4/zones/$CF_ZONE_ID/dns_records" \
  -H "Authorization: Bearer $CF_API_TOKEN" -H "Content-Type: application/json" \
  --data '{"type":"CNAME","name":"ouroboros","content":"damasker.github.io","proxied":false,"ttl":1}'
```

Rebuild with CNAME file:

```bash
WRITE_CNAME=1 make publish-site DOMAIN=ouroboros.beart.cc
```

## 2. Local static build

Default export builds the **detail ladder** (`detail-01` … `detail-18`, `oned.cells_per_segment` = 1…18).  
Classic demos: `python scripts/export_public_site.py --classic-demos`.

```bash
make publish-site DOMAIN=ouroboros.beart.cc
# optional offline campaign under results/campaigns/detail_sweep:
make detail-sweep
python3 -m http.server 8080 --directory site
```

## 3. Docker (live `/runs` API)

```bash
docker build -f Dockerfile.web -t ouroboros-web .
docker run --rm -p 8765:8765 ouroboros-web
```

Point nginx/Caddy at the container if you prefer a VPS behind `ouroboros.beart.cc`.
