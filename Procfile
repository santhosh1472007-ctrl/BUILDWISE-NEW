web: python -m flask --app run.py db upgrade && gunicorn run:app --worker-class eventlet --bind 0.0.0.0:$PORT
