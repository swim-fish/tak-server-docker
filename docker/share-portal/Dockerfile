FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir "qrcode[pil]==8.2" "Flask==3.1.2" "gunicorn==23.0.0" \
    && groupadd --gid 10001 share \
    && useradd --uid 10001 --gid 10001 --no-create-home share \
    && mkdir -p /app /state /files \
    && chown -R share:share /state /files

COPY scripts/share_portal.py scripts/share_admin_flask.py scripts/share_admin.js scripts/build_icu_qr.py /app/
COPY docker/share-portal/templates/ /app/templates/

USER 10001:10001
WORKDIR /app

CMD ["gunicorn", "--workers", "1", "--threads", "4", "--timeout", "90", "--bind", "0.0.0.0:8765", "share_portal:app"]
