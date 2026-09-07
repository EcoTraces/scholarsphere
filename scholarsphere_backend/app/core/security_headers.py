from fastapi import FastAPI, Request

_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "Cache-Control": "no-store",
    # This API serves only JSON (plus /docs's Swagger UI outside
    # production - see app.main._expose_docs) and never renders
    # user-controlled HTML, so a strict CSP costs nothing here and closes
    # off any future accidental HTML/script response. default-src 'none'
    # denies everything not explicitly listed; frame-ancestors 'none'
    # backstops X-Frame-Options for browsers that ignore the legacy header.
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    # Isolates this origin's browsing context from cross-origin windows
    # that open it (defense-in-depth against Spectre-class side channels
    # and reverse-tabnabbing) and stops other origins from embedding this
    # API's responses as a same-origin resource.
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}

# FastAPI's built-in Swagger UI (/docs) and ReDoc (/redoc) - only ever
# served outside production, see app.main._expose_docs - load their JS/CSS
# from a CDN and use inline styles, which the strict `default-src 'none'`
# CSP above would break. /openapi.json is plain JSON and unaffected, but is
# excluded too since it only exists alongside the same docs UIs.
_CSP_EXEMPT_PATHS = frozenset({"/docs", "/redoc", "/openapi.json"})


def install_security_headers(app: FastAPI) -> None:
    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):
        response = await call_next(request)
        for name, value in _HEADERS.items():
            if name == "Content-Security-Policy" and request.url.path in _CSP_EXEMPT_PATHS:
                continue
            response.headers.setdefault(name, value)
        return response
