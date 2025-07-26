# backend/tasks.py
from dotenv import load_dotenv
from datetime import datetime
import json
from flask import current_app      # not needed?
from apscheduler.schedulers.background import BackgroundScheduler

from models import User, db, CrawlJob, CrawlResult
from mailer import send_crawl_finished_email
from crawler import run_crawler

load_dotenv()

scheduler = BackgroundScheduler()
app = None


def init_scheduler(flask_app):
    global app
    app = flask_app

    with app.app_context():
        jobs = CrawlJob.query.all()

        for job in jobs:
            start = job.next_run_at
            if not start:
                continue  # skip if no scheduled time

            job_id = f"job_{job.id}"
            misfire_grace = 3600 # 1h misfire grace time

            try:
                if job.frequency == 'Daily':
                    scheduler.add_job(
                        run_crawl_job,
                        trigger='cron',
                        hour=start.hour,
                        minute=start.minute,
                        day_of_week='*',
                        start_date=start,
                        id=job_id,
                        args=[job.id],
                        replace_existing=True,
                        misfire_grace_time=misfire_grace
                    )
                    app.logger.info(f"→ Scheduled DAILY job {job.id} at {start} UTC")

                elif job.frequency == 'Weekly':
                    weekday = start.strftime('%a').lower()
                    scheduler.add_job(
                        run_crawl_job,
                        trigger='cron',
                        day_of_week=weekday,
                        hour=start.hour,
                        minute=start.minute,
                        start_date=start,
                        id=job_id,
                        args=[job.id],
                        replace_existing=True,
                        misfire_grace_time=misfire_grace
                    )
                    app.logger.info(f"→ Scheduled WEEKLY job {job.id} on {weekday} at {start} UTC")

                else:
                    scheduler.add_job(
                        run_crawl_job,
                        trigger='date',
                        run_date=start,
                        id=job_id,
                        args=[job.id],
                        replace_existing=True,
                        misfire_grace_time=misfire_grace
                    )
                    app.logger.info(f"→ Scheduled ONE-TIME job {job.id} at {start} UTC")

            except Exception as e:
                app.logger.exception(f"Failed to schedule job {job.id}: {e}")

    scheduler.start()
    app.logger.info("APScheduler started")

def schedule_crawl_job(
    url: str,
    mode: str,
    value: str,
    job_name: str,
    start_time_str: str,
    is_recurring: bool,
    frequency: str,
    user_id: int,
) -> int:
    """
    Create a new scheduled crawl job, persist it, and add it to APScheduler.

    Returns the new job's ID.
    """
    global app

    start_time = datetime.fromisoformat(start_time_str)

    with app.app_context():
        new_job = CrawlJob(
            name=job_name,
            url=url,
            extraction_mode=mode,
            extraction_value=value,
            next_run_at=start_time,
            recurring=is_recurring,
            frequency=(frequency if is_recurring else None),
            created_at=datetime.utcnow(),
            user_id=user_id,
        )
        db.session.add(new_job)
        db.session.commit()
        job_id = new_job.id

    if is_recurring:
        if frequency == 'Daily':
            scheduler.add_job(
                run_crawl_job,
                'cron',
                hour=start_time.hour,
                minute=start_time.minute,
                day_of_week='*',
                start_date=start_time if start_time > datetime.utcnow() else None,
                id=f"job_{job_id}",
                args=[job_id],
                replace_existing=True,
            )
        elif frequency == 'Weekly':
            weekday = start_time.strftime('%a').lower()
            scheduler.add_job(
                run_crawl_job,
                'cron',
                day_of_week=weekday,
                hour=start_time.hour,
                minute=start_time.minute,
                start_date=start_time if start_time > datetime.utcnow() else None,
                id=f"job_{job_id}",
                args=[job_id],
                replace_existing=True,
            )
    else:
        scheduler.add_job(
            run_crawl_job,
            'date',
            run_date=start_time,
            id=f"job_{job_id}",
            args=[job_id],
            replace_existing=True,
        )

    return job_id


def run_crawl_job(job_id: int):
    global app
    with app.app_context():
        job = CrawlJob.query.get(job_id)
        if not job:
            current_app.logger.error(f"No job found with id {job_id}")
            return

        current_app.logger.info(f"Starting scheduled crawl job {job.id} for URL: {job.url}")

        results = run_crawler(job.url,
                              job.extraction_mode,
                              job.extraction_value or '')

        new_result = CrawlResult(
            job_id=job.id,
            user_id=job.user_id,
            url=job.url,
            extraction_mode=job.extraction_mode,
            extraction_value=job.extraction_value,
            ran_at=datetime.utcnow(),
            data=json.dumps(results),
        )
        db.session.add(new_result)
        db.session.commit()

        current_app.logger.info(f"Crawl job {job.id} completed, results saved.")

        user = User.query.get(job.user_id)
        if user and user.verified and user.username:
            base = app.config.get("BASE_URL", "http://localhost:5051")
            result_url = f"{base}/results/{new_result.id}"

            try:
                send_crawl_finished_email(
                    to_email=user.username,
                    job_name=job.name or "Unnamed job",
                    ran_at=new_result.ran_at,
                    result_url=result_url
                )
                current_app.logger.info(f"Successfully sent crawl completion email to {user.username}")
            except Exception as e:
                current_app.logger.exception(f"Failed to send crawl completion email: {e}")
        else:
            current_app.logger.warning(f"Email not sent: user {job.user_id} missing or unverified")
