
from __future__ import annotations
import csv, json
from datetime import datetime, timedelta
from io import StringIO, BytesIO
from urllib.parse import urljoin, urldefrag

import requests
from bs4 import BeautifulSoup
from flask import (
   Blueprint, request, jsonify, session, abort,
   current_app, send_file
)
from mailer import send_crawl_finished_email
from models import db, User, CrawlJob, CrawlResult
from crawler import run_crawler

api_bp = Blueprint("api", __name__, url_prefix="/api")  # create blueprint

# Helper functions
def _require_user() -> User:
   auth = request.headers.get("Authorization", "")
   if auth.startswith("Bearer "):
       key  = auth.split(None, 1)[1].strip()
       user = User.query.filter_by(api_key=key, verified=True).first()
       if user:
           return user

   uid = session.get("user_id")
   if uid:
       user = User.query.get(uid)
       if user:
           return user
   abort(401)

def _extract(url: str, mode: str, value: str, limit: int = 30):
   hdrs = {
       "User-Agent": "Mozilla/5.0 (compatible; Crawlernaut/1.0)",
       "Accept":  "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
       "Accept-Language": "en-US,en;q=0.5",
   }
   try:
       resp = requests.get(url, headers=hdrs, timeout=10)
       resp.raise_for_status()
   except Exception as e:
       return [], f"fetch_error: {e}"

   if mode == "depth":
       try:
           depth = int(value)
       except ValueError:
           return [], "invalid depth"
       return run_crawler(url, "max_pages", depth), None

   soup = BeautifulSoup(resp.text, "html.parser")
   out: list[dict] = []

   if mode == "tag":
       for el in soup.find_all(value, limit=limit):
           out.append({
               "content": el.get_text(strip=True),
               "url": el.get("href")
           })

   elif mode == "css":
       for el in soup.select(value)[:limit]:
           out.append({
               "content": el.get_text(strip=True),
               "url": el.get("href")
           })

   elif mode == "image":
       for img in soup.find_all("img", limit=limit):
           src = img.get("src") or img.get("data-src") or img.get("data-lazy-src") or ""
           if not src or src.startswith("data:"):
               continue
           alt = img.get("alt", "").strip() or "(no alt)"
           full, _ = urldefrag(urljoin(resp.url, src))
           out.append({"alt": alt, "src": full})

   elif mode == "text":
       body = soup.find("body")
       para = body.find("p") if body else None
       out  = [{"text": para.get_text(strip=True) if para else ""}]

   else:
       return [], f"unsupported mode '{mode}'"

   return out, None
 

@api_bp.post("/crawl")
def crawl_now():
    payload = request.get_json(silent=True) or {}
    url   = (payload.get("url")   or "").strip()
    mode  = (payload.get("mode")  or "").strip()
    value = (payload.get("value") or "").strip()
    name  = (payload.get("name")  or "").strip()

    if not url or not mode:
        return jsonify(msg="url and mode required"), 400
    if mode in {"tag", "css"} and not value:
        return jsonify(msg="value required for tag/css"), 400

    rows, err = _extract(url, mode, value)
    if err:
        current_app.logger.error("Extraction error: %s", err)
        return jsonify(msg=err), 500

    user = None
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.split(None, 1)[1].strip()
        user = User.query.filter_by(api_key=token, verified=True).first()
    # session
    if not user and "user_id" in session:
        user = User.query.get(session["user_id"])

    # if not logged in, return just the data
    if not user:
        return jsonify(data=rows), 200

    job = CrawlJob(
        user_id=user.id,
        name=name or "(adhoc)",
        url=url,
        extraction_mode=mode,
        extraction_value=value,
        next_run_at=None,
        recurring=False,
    )
    db.session.add(job)
    db.session.flush()  

    result = CrawlResult(
        user_id=user.id,
        job_id=job.id,
        url=url,
        extraction_mode=mode,
        extraction_value=value,
        data=json.dumps(rows),
    )
    db.session.add(result)
    db.session.commit()
    return jsonify(
        msg="ok",
        data=rows,
        result_id=result.id,
        job_id=job.id
    ), 200


@api_bp.post("/schedule")
def schedule_crawl():
   user = _require_user()
   d = request.get_json() or {}
   url = (d.get("url") or "").strip()
   mode = (d.get("mode") or "").strip()
   value = (d.get("value")or "").strip()
   when_iso  = (d.get("dateTime") or "").strip()
   recurring = bool(d.get("recurring"))
   freq= d.get("frequency") or None
   name = (d.get("name")or "").strip()

   if not url or not mode or not when_iso:
       return jsonify(msg="url, mode, dateTime required"), 400
   if mode in {"tag", "css"} and not value:
       return jsonify(msg="value required for tag/css"), 400

   try:
       run_at = datetime.fromisoformat(when_iso)
   except ValueError:
       return jsonify(msg="invalid dateTime"), 400
   if run_at < datetime.utcnow():
       return jsonify(msg="scheduled time in past"), 400

   job = CrawlJob(
       user_id=user.id,
       name=name or "(scheduled)",
       url=url,
       extraction_mode=mode,
       extraction_value=value,
       next_run_at=run_at,
       recurring=recurring,
       frequency=freq,
   )
   db.session.add(job)
   db.session.commit()
   return jsonify(msg="scheduled", job_id=job.id), 200


@api_bp.get("/jobs")
def list_jobs():
   user = _require_user()
   jobs = (CrawlJob.query
           .filter_by(user_id=user.id)
           .order_by(CrawlJob.id.desc())
           .all())
   return jsonify([j.as_dict() for j in jobs]), 200


@api_bp.get("/jobs/<int:job_id>/runs")
def list_runs(job_id):
   user = _require_user()
   job  = CrawlJob.query.get_or_404(job_id)
   if job.user_id != user.id:
       abort(403)

   db.session.expire_all()

   runs = (CrawlResult.query
           .filter_by(job_id=job.id)
           .order_by(CrawlResult.ran_at.desc())
           .all())
   return jsonify([
       {"id": r.id, "ranAt": r.ran_at.isoformat()} for r in runs
   ]), 200


@api_bp.delete("/jobs/<int:job_id>")
def delete_job(job_id):
   user = _require_user()
   job  = CrawlJob.query.get_or_404(job_id)
   if job.user_id != user.id:
       abort(403)
   db.session.delete(job)
   db.session.commit()
   return jsonify(msg="deleted"), 200


@api_bp.post("/jobs/<int:job_id>/run")
def run_job_now(job_id):
   user = _require_user()
   job  = CrawlJob.query.get_or_404(job_id)
   if job.user_id != user.id:
       abort(403)

   rows, err = _extract(job.url, job.extraction_mode, job.extraction_value)
   if err:
       return jsonify(msg=err), 500

   res = CrawlResult(
       user_id=user.id,
       job_id=job.id,
       url=job.url,
       extraction_mode=job.extraction_mode,
       extraction_value=job.extraction_value,
       data=json.dumps(rows),
   )
   db.session.add(res)

   if job.next_run_at:
       if job.recurring:
           job.next_run_at += timedelta(days=1 if job.frequency == "Daily" else 7)
       else:
           job.next_run_at = None

   db.session.commit()
   return jsonify(msg="ok", data=rows, result_id=res.id), 200


@api_bp.get("/results/<int:res_id>")
def get_result(res_id):
   user = _require_user()
   db.session.expire_all()
   res  = CrawlResult.query.get_or_404(res_id)
   if res.user_id != user.id:
       abort(403)
   return jsonify(json.loads(res.data)), 200


@api_bp.get("/results/<int:res_id>/download")
def download_result(res_id):
   user = _require_user()
   res  = CrawlResult.query.get_or_404(res_id)
   if res.user_id != user.id:
       abort(403)

   fmt  = (request.args.get("fmt") or "csv").lower()
   rows = json.loads(res.data)

   if fmt == "json":
       buf = BytesIO(json.dumps(rows, indent=2).encode())
       return send_file(
           buf,
           as_attachment=True,
           download_name=f"crawl_{res_id}.json",
           mimetype="application/json"
       )


   # default == CSV
   cols = sorted({k for r in rows for k in r})
   sio  = StringIO()
   writer = csv.DictWriter(sio, fieldnames=cols)
   writer.writeheader()
   writer.writerows(rows)

   buf = BytesIO(sio.getvalue().encode())
   return send_file(
       buf,
       as_attachment=True,
       download_name=f"crawl_{res_id}.csv",
       mimetype="text/csv"
   )