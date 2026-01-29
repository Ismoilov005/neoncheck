# Generated manually
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quizzes', '0007_alter_kahootanswer_id_alter_kahootplayer_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='kahootsession',
            name='max_players',
            field=models.PositiveIntegerField(default=50, help_text="Maksimal o'yinchilar soni"),
        ),
    ]
