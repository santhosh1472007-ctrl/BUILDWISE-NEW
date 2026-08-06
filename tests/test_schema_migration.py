import os
import tempfile
import unittest

from flask import Flask
from sqlalchemy import inspect, text

from app import ensure_database_schema
from models import db


class SchemaMigrationTests(unittest.TestCase):
    def test_ensure_database_schema_adds_missing_columns(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "test_schema.db")
            app = Flask(__name__)
            app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
            app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
            db.init_app(app)

            with app.app_context():
                db.session.execute(text("CREATE TABLE cpus (id INTEGER PRIMARY KEY, name VARCHAR(150) NOT NULL)"))
                db.session.commit()

                ensure_database_schema(app)

                inspector = inspect(db.engine)
                columns = [column["name"] for column in inspector.get_columns("cpus")]
                self.assertIn("brand", columns)
                self.assertIn("socket_id", columns)

            with app.app_context():
                db.session.remove()
            db.engine.dispose()
            if hasattr(db, 'engine'):
                db.engine.dispose()


if __name__ == "__main__":
    unittest.main()
