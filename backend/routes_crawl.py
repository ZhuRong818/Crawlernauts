from datetime import datetime
from flask import Blueprint, request, jsonify
from mailer import send_crawl_finished_email


crawl_bp = Blueprint("crawl", __name__)




@crawl_bp.post("/crawl")
def crawl_now():
    data = request.get_json(silent=True) or {}
    url   = (data.get("url") or "").strip()
    mode  = (data.get("mode") or "").strip()
    value = data.get("value")  # may be None or empty string


    if not url or not mode:
        return jsonify(msg="Missing url or mode"), 400
    if mode in {"tag", "css"} and not value:
        if not value:
            return jsonify(msg="Missing value for mode 'tag' or 'css'"), 400


    try:
        results = run_crawler(url, mode, value)
        return jsonify(data=results), 200
    except Exception as e:
        return jsonify(msg=str(e)), 500


# scheudle futue jobs
@crawl_bp.post("/crawl/schedule")
def schedule_crawl():
    data = request.get_json(silent=True) or {}
    url = data.get("url")
    mode  = data.get("mode")
    value  = data.get("value")
    job_name = data.get("jobName")
    scheduled_time = data.get("scheduledTime")
    is_recurring = bool(data.get("isRecurring"))
    frequency= data.get("frequency")


    if not url or not mode or not job_name or not scheduled_time or not frequency:
        return jsonify(msg="Missing url, mode, job_name, scheduled_time, or frequency"), 400


    try:
        run_at = datetime.fromisoformat(scheduled_time)
    except ValueError:
        return jsonify(msg="Invalid scheduledTime format"), 400


    if run_at >= datetime(2036, 1, 1):
        return jsonify(msg="scheduled time must be before 2036-01-01"), 400


    try:
        from tasks import schedule_crawl_job
        schedule_crawl_job(
            url,
            mode,
            value or "",
            job_name,
            is_recurring,
            frequency,
        )
        return jsonify(msg="Scheduled crawl job created"), 200
    except Exception as e:
        return jsonify(msg=str(e)), 500


def rerun_crawl_job(job_id: int):


    from models import CrawlJob, CrawlResult, db


    job = CrawlJob.query.get_or_404(job_id)


    try:
        results = run_crawler(job.url, job.extraction_mode, job.extraction_value)


        new_result = CrawlResult(
            user_id = job.user_id,
            job_id = job.id,
            url= job.url,
            extraction_mode  = job.extraction_mode,
            extraction_value = job.extraction_value,
            data= json.dumps(results),
        )
        db.session.add(new_result)
        db.session.commit()


        user_email = job.user.username
        result_url = new_result.url  # Adjust accordingly
        send_crawl_finished_email(
            to_email=user_email,
            job_name=job.name,
            ran_at=datetime.utcnow(),
            result_url=result_url
        )


        return jsonify(msg="Job rerun successfully", data=results), 200
    except Exception as e:
        return jsonify(msg=str(e)), 500





