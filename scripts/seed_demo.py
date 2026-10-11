"""Create reviewed demo tickets using the configured real AI provider."""

import time
from datetime import datetime, timedelta

from app.database import Base, SessionLocal, engine, upgrade_sqlite_schema
from app.models import ReviewAction, Ticket, TicketStatus, Urgency
from app.services.ai_analyzer import AnalysisError, analyze_ticket

DEMO_TICKETS = [
    ("Charged twice", "I was charged twice for my monthly subscription."),
    ("Login loop", "I complete login but the app immediately returns me to the sign-in page."),
    ("Add SCIM", "Please add SCIM provisioning for our enterprise workspace."),
    ("Change profile email", "How do I change my profile email address?"),
    ("Refund question", "Can I get a refund after an accidental renewal?"),
    ("Dashboard outage", "Our whole team sees a blank dashboard and cannot work."),
    ("Press contact", "A journalist would like a product comment for an article."),
    ("Export failure", "CSV exports fail, but I can view reports in the browser."),
    ("Dark mode", "Please add a dark mode for agents working overnight."),
    ("MFA phone lost", "I replaced my phone and cannot complete MFA."),
    ("Invoice download", "Where can I download last month's invoice?"),
    ("Webhook latency", "Our webhooks are delayed by twenty minutes today."),
    ("Thank you", "Your support team fixed my issue quickly. Thank you."),
    ("Bulk assignment", "We need to assign hundreds of tickets in bulk."),
    ("Account deletion", "Please explain how to permanently delete my workspace."),
]


def main() -> None:
    Base.metadata.create_all(bind=engine)
    upgrade_sqlite_schema()
    db = SessionLocal()
    now = datetime.utcnow()
    created = reviewed = 0

    try:
        for index, (subject, body) in enumerate(DEMO_TICKETS):
            ticket = Ticket(subject=subject, body=body, created_at=now - timedelta(hours=48 - index * 2))
            db.add(ticket)
            db.commit()
            db.refresh(ticket)
            created += 1
            print(f"[{index + 1}/{len(DEMO_TICKETS)}] analyzing: {subject}", flush=True)

            try:
                analysis = analyze_ticket(subject, body)
            except AnalysisError as exc:
                print(f"  skipped: {exc}", flush=True)
                continue

            ticket.category = analysis.category
            ticket.urgency = analysis.urgency
            ticket.ai_category = analysis.category
            ticket.ai_urgency = analysis.urgency
            ticket.ai_summary = analysis.summary
            ticket.ai_suggested_reply = analysis.suggested_reply
            ticket.analyzed_at = ticket.created_at + timedelta(minutes=10 + index)
            ticket.status = TicketStatus.analyzed

            action = [ReviewAction.approved, ReviewAction.edited, ReviewAction.rejected][index % 3]
            ticket.review_action = action
            ticket.reviewed_by = ["Asha", "Mina", "Dev"][index % 3]
            ticket.reviewed_at = ticket.analyzed_at + timedelta(minutes=5 + index * 2)
            if action == ReviewAction.approved:
                ticket.final_reply = ticket.ai_suggested_reply
            elif action == ReviewAction.edited:
                ticket.final_reply = f"Hello, thanks for contacting us about {subject.lower()}. We are reviewing this now."

            # Deliberate human corrections make AI-agreement metrics meaningful.
            if index == 4:
                ticket.category = "billing"
                ticket.urgency = Urgency.medium
            elif index == 6:
                ticket.category = "other"
                ticket.urgency = Urgency.low
            elif index == 11:
                ticket.urgency = Urgency.high

            ticket.status = TicketStatus.reviewed
            db.commit()
            reviewed += 1
            print(f"  reviewed: {action.value}", flush=True)
            time.sleep(1)
    finally:
        db.close()

    print(f"Created {created} demo tickets; reviewed {reviewed}.")


if __name__ == "__main__":
    main()
