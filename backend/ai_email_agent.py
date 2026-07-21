"""
StartupSphere — AI Email Automation Agent
==========================================
Uses APScheduler + Claude AI (via anthropic) to send
personalized, AI-written emails based on user activity.

Schedules:
  - Every day 9 AM  → Inactive user reminders (7+ days)
  - Every day 10 AM → Access request reminders (3+ days pending)
  - Every day 11 AM → Milestone congratulations (10+ likes)
  - Every Monday 8 AM → Weekly digest email
"""

import os
import anthropic
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

load_dotenv()

# ── Anthropic client ──
claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


# ── Helper: generate personalized email content via Claude ──
def generate_email_content(prompt: str) -> str:
    """Calls Claude to generate personalized email HTML body."""
    try:
        response = claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        print(f"[AI AGENT] Claude error: {e}")
        return None


# ── Helper: send email via existing email_utils ──
def _send(to_email: str, subject: str, html_body: str):
    from email_utils import send_email
    result = send_email(to_email, subject, html_body)
    if result:
        print(f"[AI AGENT] ✅ Sent '{subject}' to {to_email}")
    else:
        print(f"[AI AGENT] ❌ Failed to send to {to_email}")


# ──────────────────────────────────────────────
# TASK 1: Inactive User Reminder
# Runs daily at 9 AM — finds users inactive 7+ days
# ──────────────────────────────────────────────
def send_inactive_reminders():
    print("[AI AGENT] Running: Inactive user reminder task")
    try:
        from database import SessionLocal
        import models

        db = SessionLocal()
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)

        inactive_users = db.query(models.User).filter(
            models.User.is_verified == True,
            models.User.is_banned == False,
            models.User.last_login_at != None,
            models.User.last_login_at < cutoff,
        ).all()

        print(f"[AI AGENT] Found {len(inactive_users)} inactive users")

        for user in inactive_users:
            days_inactive = (datetime.now(timezone.utc) - user.last_login_at).days

            prompt = f"""Write a short, warm, encouraging email to bring back an inactive StartupSphere user.

User info:
- Name: {user.name}
- Days since last login: {days_inactive}
- Platform: StartupSphere (startup idea sharing platform)

Requirements:
- Friendly, motivating tone
- Mention they might be missing new startup ideas
- Encourage them to log in and check new ideas or submit theirs
- Keep it SHORT (3-4 sentences max)
- Return ONLY the HTML email body (no subject, no preamble)
- Use inline styles, dark background (#06061a), purple accent (#6c63ff)
- Include a "Visit StartupSphere" button linking to http://127.0.0.1:5500/frontend/ideas.html"""

            html = generate_email_content(prompt)
            if html:
                _send(user.email, f"Hey {user.name}, we miss you! 🚀", html)

        db.close()
    except Exception as e:
        print(f"[AI AGENT] Inactive reminder error: {e}")


# ──────────────────────────────────────────────
# TASK 2: Access Request Reminder
# Runs daily at 10 AM — reminds idea owners of pending requests 3+ days old
# ──────────────────────────────────────────────
def send_access_request_reminders():
    print("[AI AGENT] Running: Access request reminder task")
    try:
        from database import SessionLocal
        import models

        db = SessionLocal()
        cutoff = datetime.now(timezone.utc) - timedelta(days=3)

        pending = db.query(models.AccessRequest).filter(
            models.AccessRequest.status == "pending",
            models.AccessRequest.created_at < cutoff,
        ).all()

        # Group by idea owner
        owner_requests = {}
        for req in pending:
            owner = req.idea.author
            if owner.id not in owner_requests:
                owner_requests[owner.id] = {"owner": owner, "requests": []}
            owner_requests[owner.id]["requests"].append(req)

        print(f"[AI AGENT] Found {len(owner_requests)} owners with pending requests")

        for owner_id, data in owner_requests.items():
            owner = data["owner"]
            requests = data["requests"]

            req_details = "\n".join([
                f"- '{req.idea.title}' requested by {req.requester.name}"
                for req in requests
            ])

            prompt = f"""Write a brief reminder email to a startup founder on StartupSphere about pending access requests.

Founder: {owner.name}
Pending requests:
{req_details}

Requirements:
- Professional yet friendly tone
- Remind them people are waiting to see their idea
- Encourage them to log in and respond (accept or reject)
- Keep it SHORT (3-4 sentences)
- Return ONLY the HTML email body
- Use inline styles, dark background (#06061a), purple accent (#6c63ff)
- Include a "Review Requests" button linking to http://127.0.0.1:5500/frontend/dashboard.html"""

            html = generate_email_content(prompt)
            if html:
                count = len(requests)
                _send(owner.email,
                      f"⏳ {count} pending access request{'s' if count > 1 else ''} on your idea{'s' if count > 1 else ''}",
                      html)

        db.close()
    except Exception as e:
        print(f"[AI AGENT] Access request reminder error: {e}")


# ──────────────────────────────────────────────
# TASK 3: Milestone Congratulations
# Runs daily at 11 AM — congrats when idea gets 10/50/100 likes
# ──────────────────────────────────────────────
def send_milestone_congratulations():
    print("[AI AGENT] Running: Milestone congratulations task")
    try:
        from database import SessionLocal
        import models

        db = SessionLocal()
        milestones = [10, 50, 100, 500]

        ideas = db.query(models.Idea).filter(
            models.Idea.status == "published"
        ).all()

        for idea in ideas:
            like_count = len(idea.likes)
            if like_count in milestones:
                owner = idea.author

                prompt = f"""Write a short, enthusiastic congratulations email to a startup founder whose idea just hit a milestone on StartupSphere.

Founder: {owner.name}
Idea title: "{idea.title}"
Milestone: {like_count} likes!

Requirements:
- Super enthusiastic, celebratory tone 🎉
- Mention the specific milestone and idea title
- Encourage them to keep building and sharing
- Keep it SHORT (3-4 sentences)
- Return ONLY the HTML email body
- Use inline styles, dark background (#06061a), purple/gold accent
- Include a "View Your Idea" button"""

                html = generate_email_content(prompt)
                if html:
                    _send(owner.email,
                          f"🎉 Your idea '{idea.title}' just hit {like_count} likes!",
                          html)

        db.close()
    except Exception as e:
        print(f"[AI AGENT] Milestone congrats error: {e}")


# ──────────────────────────────────────────────
# TASK 4: Weekly Digest
# Runs every Monday at 8 AM — top 5 new ideas this week
# ──────────────────────────────────────────────
def send_weekly_digest():
    print("[AI AGENT] Running: Weekly digest task")
    try:
        from database import SessionLocal
        import models

        db = SessionLocal()

        # Top 5 ideas from last 7 days by likes
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        new_ideas = db.query(models.Idea).filter(
            models.Idea.status == "published",
            models.Idea.created_at >= week_ago
        ).all()

        if not new_ideas:
            print("[AI AGENT] No new ideas this week, skipping digest")
            db.close()
            return

        # Sort by likes
        top_ideas = sorted(new_ideas, key=lambda i: len(i.likes), reverse=True)[:5]
        ideas_summary = "\n".join([
            f"- '{idea.title}' ({idea.category}) — {len(idea.likes)} likes"
            for idea in top_ideas
        ])

        # Send to all verified, active users
        users = db.query(models.User).filter(
            models.User.is_verified == True,
            models.User.is_banned == False,
        ).all()

        print(f"[AI AGENT] Sending weekly digest to {len(users)} users")

        for user in users:
            prompt = f"""Write a weekly digest email for a StartupSphere user showing this week's top startup ideas.

User: {user.name}
Top ideas this week:
{ideas_summary}

Requirements:
- Engaging, newsletter-style tone
- Brief intro (1 sentence) then list the ideas nicely
- End with a CTA to explore more
- Keep it concise but exciting
- Return ONLY the HTML email body
- Use inline styles, dark background (#06061a), purple accent (#6c63ff)
- Include "Explore All Ideas" button linking to http://127.0.0.1:5500/frontend/ideas.html"""

            html = generate_email_content(prompt)
            if html:
                _send(user.email, "🚀 This Week's Top Startup Ideas on StartupSphere", html)

        db.close()
    except Exception as e:
        print(f"[AI AGENT] Weekly digest error: {e}")


# ──────────────────────────────────────────────
# SCHEDULER SETUP
# ──────────────────────────────────────────────
def start_scheduler():
    """Initialize and start the APScheduler."""
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

    # Daily at 9 AM IST — inactive user reminders
    scheduler.add_job(
        send_inactive_reminders,
        CronTrigger(hour=9, minute=0),
        id="inactive_reminders",
        replace_existing=True
    )

    # Daily at 10 AM IST — access request reminders
    scheduler.add_job(
        send_access_request_reminders,
        CronTrigger(hour=10, minute=0),
        id="access_reminders",
        replace_existing=True
    )

    # Daily at 11 AM IST — milestone congratulations
    scheduler.add_job(
        send_milestone_congratulations,
        CronTrigger(hour=11, minute=0),
        id="milestone_congrats",
        replace_existing=True
    )

    # Every Monday at 8 AM IST — weekly digest
    scheduler.add_job(
        send_weekly_digest,
        CronTrigger(day_of_week="mon", hour=8, minute=0),
        id="weekly_digest",
        replace_existing=True
    )

    scheduler.start()
    print("[AI AGENT] ✅ Scheduler started!")
    print("[AI AGENT] 📅 Schedules:")
    print("[AI AGENT]   - Inactive reminders: Daily 9 AM IST")
    print("[AI AGENT]   - Access req reminders: Daily 10 AM IST")
    print("[AI AGENT]   - Milestone congrats: Daily 11 AM IST")
    print("[AI AGENT]   - Weekly digest: Every Monday 8 AM IST")
    return scheduler