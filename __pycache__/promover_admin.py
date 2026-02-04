from app import create_app
from models import db, Usuario

EMAIL_ADMIN = "stella.dini@dinicompanyoficial.com"

app = create_app()

with app.app_context():
    u=Usuario.query.filter_by(email=EMAIL_ADMIN).first()

    if not u:
        raise SystemExit(f"Esse email não existe no banco: {EMAIL_ADMIN}")

    u.is_admin = True
    db.session.commit()
    print("OK! Agora is_admin =", u.is_admin, "para", u.email)