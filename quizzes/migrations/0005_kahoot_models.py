# Generated manually for Kahoot Mode models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def generate_pin():
    import random
    import string
    return ''.join(random.choices(string.digits, k=6))


class Migration(migrations.Migration):

    dependencies = [
        ("quizzes", "0004_profile_and_notification"),
    ]

    operations = [
        migrations.CreateModel(
            name="KahootQuiz",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("creator", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="kahoot_quizzes", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="KahootQuestion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.TextField()),
                ("image", models.ImageField(blank=True, null=True, upload_to="kahoot/questions/")),
                ("option_a", models.CharField(max_length=200)),
                ("option_b", models.CharField(max_length=200)),
                ("option_c", models.CharField(max_length=200)),
                ("option_d", models.CharField(max_length=200)),
                ("correct_option", models.CharField(choices=[("A", "A - Qizil"), ("B", "B - Ko'k"), ("C", "C - Sariq"), ("D", "D - Yashil")], max_length=1)),
                ("time_limit", models.PositiveIntegerField(default=20, help_text="Vaqt limiti (soniyalarda)")),
                ("order", models.PositiveIntegerField(default=0)),
                ("quiz", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="questions", to="quizzes.kahootquiz")),
            ],
            options={
                "ordering": ["order", "id"],
            },
        ),
        migrations.CreateModel(
            name="KahootSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("pin", models.CharField(max_length=6, unique=True)),
                ("status", models.CharField(choices=[("LOBBY", "Lobby - Kutish"), ("PLAYING", "Playing - O'yin"), ("FINISHED", "Finished - Tugagan")], default="LOBBY", max_length=10)),
                ("current_question_index", models.IntegerField(default=-1)),
                ("question_start_time", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("host", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="hosted_sessions", to=settings.AUTH_USER_MODEL)),
                ("quiz", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sessions", to="quizzes.kahootquiz")),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="KahootPlayer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nickname", models.CharField(max_length=30)),
                ("avatar_id", models.PositiveIntegerField(choices=[(i, f"Avatar {i}") for i in range(1, 16)], default=1)),
                ("score", models.IntegerField(default=0)),
                ("session_key", models.CharField(blank=True, max_length=100)),
                ("joined_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="players", to="quizzes.kahootsession")),
            ],
            options={
                "ordering": ["-score", "joined_at"],
                "unique_together": {("session", "nickname")},
            },
        ),
        migrations.CreateModel(
            name="KahootAnswer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("selected_option", models.CharField(choices=[("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")], max_length=1)),
                ("is_correct", models.BooleanField(default=False)),
                ("time_taken", models.FloatField(default=0)),
                ("points_earned", models.IntegerField(default=0)),
                ("answered_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("player", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="answers", to="quizzes.kahootplayer")),
                ("question", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="player_answers", to="quizzes.kahootquestion")),
            ],
            options={
                "unique_together": {("player", "question")},
            },
        ),
    ]
