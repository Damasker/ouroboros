# Publishing Ouroboros at ouroboros.beart.cc

Public gallery is a **static GitHub Pages** site (demo runs baked in).
Full live API remains available via Docker.

## 1. GitHub Pages (ouroboros.beart.cc)

Repo workflow `.github/workflows/deploy-pages.yml` builds `site/` and deploys it.

### DNS (Cloudflare / registrar for `beart.cc`)

Create a **CNAME** record:

| Type  | Name       | Target              | Proxy |
|-------|------------|---------------------|-------|
| CNAME | `ouroboros` | `damasker.github.io` | DNS only (grey cloud) recommended until SSL issues |

GitHub also accepts these A records on the apex; for a subdomain CNAME is enough.

After DNS propagates, open https://ouroboros.beart.cc/viewer/

### Local build

```bash
make publish-site DOMAIN=ouroboros.beart.cc
# preview
python3 -m http.server 8080 --directory site
```

## 2. Docker (live server with `/runs` API)

```bash
docker build -f Dockerfile.web -t ouroboros-web .
docker run --rm -p 8765:8765 ouroboros-web
# http://HOST:8765/viewer
```

Point a reverse proxy (Caddy/nginx) at the container if you prefer a VPS over Pages.
