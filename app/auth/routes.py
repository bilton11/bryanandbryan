from datetime import datetime, timezone
from urllib.parse import urlsplit

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required, login_user, logout_user

from app.auth import auth_bp
from app.extensions import db, limiter
from app.models.user import User
from app.services.auth_tokens import generate_magic_token, verify_magic_token


def _safe_next(next_url: str | None) -> str:
    """Return next_url only if it is a relative URL (prevents open redirects)."""
    if not next_url:
        return url_for("main.index")
    parsed = urlsplit(next_url)
    if parsed.scheme or parsed.netloc:
        return url_for("main.index")
    return next_url


def _email_key() -> str:
    """Rate-limit key based on submitted email address."""
    return request.form.get("email", "anonymous").lower()


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per hour", methods=["POST"], key_func=lambda: request.remote_addr)
@limiter.limit("3 per hour", methods=["POST"], key_func=_email_key)
def login():
    if request.method == "GET":
        return render_template("auth/login.html")

    email = request.form.get("email", "").strip().lower()

    # Basic email validation — must have @ and a dot after the @
    if not email or "@" not in email or "." not in email.split("@", 1)[-1]:
        flash("Please enter a valid email address.", "error")
        return render_template("auth/login.html")

    token = generate_magic_token(email)
    verify_url = url_for("auth.verify", token=token, _external=True)

    mail_user = current_app.config.get("MAIL_USERNAME", "")
    mail_pass = current_app.config.get("MAIL_PASSWORD", "")
    if mail_user and mail_pass:
        _send_magic_link_email(email, verify_url, mail_user, mail_pass)
    else:
        # Development mode — print link to console and flash it
        current_app.logger.info("Magic link for %s: %s", email, verify_url)
        flash(f"[DEV] Magic link: {verify_url}", "info")

    # Always redirect to check-email (prevents email enumeration)
    return redirect(url_for("auth.check_email"))


def _send_magic_link_email(
    to_email: str, verify_url: str, mail_user: str, mail_pass: str
) -> None:
    """Send a magic link email via Gmail SMTP."""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your Bryan and Bryan sign-in link"
    msg["From"] = mail_user
    msg["To"] = to_email

    text = (
        "Sign in to Bryan and Bryan by visiting this link "
        f"(expires in 15 minutes):\n\n{verify_url}\n\n"
        "If you did not request this link, you can safely ignore this email."
    )
    html = (
        "<p>Click the link below to sign in to Bryan and Bryan. "
        "The link expires in 15 minutes.</p>"
        f'<p><a href="{verify_url}">Sign in to Bryan and Bryan</a></p>'
        "<p>If you did not request this link, you can safely ignore this email.</p>"
    )
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(mail_user, mail_pass)
        server.sendmail(mail_user, to_email, msg.as_string())


@auth_bp.route("/check-email")
def check_email():
    return render_template("auth/check_email.html")


@auth_bp.route("/verify/<token>")
def verify(token: str):
    email = verify_magic_token(token)
    if email is None:
        return render_template("auth/link_expired.html")

    # Find or create user (create-on-verify pattern)
    user = db.session.execute(
        db.select(User).where(User.email == email)
    ).scalar_one_or_none()

    if user is None:
        user = User(email=email)
        db.session.add(user)

    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()

    login_user(user, remember=True)

    next_page = _safe_next(request.args.get("next"))
    return redirect(next_page)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
