#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt
python manage.py shell -c "from quizzes.models import User; User.objects.create_superuser('algoarchitect', 'bekzodbekismoilov005@mail.com', 'adu-it-ki-1215') if not User.objects.filter(username='algoarchitect').exists() else None"
python manage.py collectstatic --no-input
python manage.py migrate
