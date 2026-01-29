from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import uuid


class User(AbstractUser):
    """Custom User model with role-based access control"""
    ROLE_CHOICES = [
        ('SUPERUSER', 'Superuser'),
        ('ADMIN', 'Admin'),
        ('USER', 'User'),
    ]
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='USER')
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def is_superuser_role(self):
        """Check if user has Superuser role"""
        return self.role == 'SUPERUSER' or self.is_superuser
    
    def is_admin_role(self):
        """Check if user has Admin role"""
        return self.role == 'ADMIN' or self.is_superuser_role()
    
    def is_user_role(self):
        """Check if user has User role (everyone)"""
        return True


class Test(models.Model):
    """Test/Quiz model with privacy controls"""
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_private = models.BooleanField(default=False)
    time_limit = models.PositiveIntegerField(default=15, help_text="Time limit in minutes")
    is_active = models.BooleanField(default=True, help_text="Whether the test is active and available")
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tests')
    allowed_users = models.ManyToManyField(User, related_name='allowed_tests', blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def can_access(self, user):
        """Check if a user can access this test"""
        if not self.is_private:
            return True
        if user.is_authenticated and (user in self.allowed_users.all() or user == self.creator or user.is_superuser_role()):
            return True
        return False


class Question(models.Model):
    """Question model for tests"""
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['order', 'id']
    
    def __str__(self):
        return f"{self.test.title} - Q{self.order + 1}"


class Option(models.Model):
    """Option model for questions - is_correct field is secure on server"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'id']
    
    def __str__(self):
        return f"{self.question} - Option {self.order + 1}"


class UserResult(models.Model):
    """Detailed results of user test attempts"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_results')
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='results')
    score = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=0)
    percentage = models.FloatField(default=0.0)
    time_spent = models.PositiveIntegerField(default=0, help_text="Time spent in seconds")
    certificate_id = models.UUIDField(default=None, editable=False, null=True, blank=True, unique=True)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    answers = models.JSONField(default=dict)  # Store question_id: option_id mappings
    
    class Meta:
        ordering = ['-completed_at', '-started_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.test.title} ({self.percentage:.1f}%)"
    
    def calculate_score(self):
        """Calculate score based on stored answers"""
        correct_count = 0
        for question_id, option_id in self.answers.items():
            try:
                option = Option.objects.get(id=option_id)
                if option.is_correct:
                    correct_count += 1
            except Option.DoesNotExist:
                pass
        
        self.score = correct_count
        if self.total_questions > 0:
            self.percentage = (correct_count / self.total_questions) * 100
        return self.score


class Profile(models.Model):
    """User profile: avatar and bio"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/%Y/%m/', blank=True, null=True)
    bio = models.TextField(blank=True, max_length=500)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.username}"


class Notification(models.Model):
    """Notification: sender, receiver, message, read status"""
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications', null=True, blank=True)
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Notification to {self.receiver.username}"


# ==================== KAHOOT MODE ====================

import random
import string


def generate_pin():
    """6 xonali unikal PIN yaratish"""
    return ''.join(random.choices(string.digits, k=6))


class KahootQuiz(models.Model):
    """Kahoot o'yin uchun viktorina"""
    title = models.CharField(max_length=200)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='kahoot_quizzes')
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class KahootQuestion(models.Model):
    """Kahoot savoli: 4 ta variant, vaqt limiti"""
    quiz = models.ForeignKey(KahootQuiz, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    image = models.ImageField(upload_to='kahoot/questions/', blank=True, null=True)
    option_a = models.CharField(max_length=200)  # Qizil - Uchburchak
    option_b = models.CharField(max_length=200)  # Ko'k - Olmos
    option_c = models.CharField(max_length=200)  # Sariq - Doira
    option_d = models.CharField(max_length=200)  # Yashil - Kvadrat
    correct_option = models.CharField(max_length=1, choices=[
        ('A', 'A - Qizil'),
        ('B', 'B - Ko\'k'),
        ('C', 'C - Sariq'),
        ('D', 'D - Yashil'),
    ])
    time_limit = models.PositiveIntegerField(default=20, help_text="Vaqt limiti (soniyalarda)")
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'id']
    
    def __str__(self):
        return f"{self.quiz.title} - Q{self.order + 1}"


class KahootSession(models.Model):
    """O'yin sessiyasi: PIN, holat"""
    STATUS_CHOICES = [
        ('LOBBY', 'Lobby - Kutish'),
        ('PLAYING', 'Playing - O\'yin'),
        ('FINISHED', 'Finished - Tugagan'),
    ]
    
    quiz = models.ForeignKey(KahootQuiz, on_delete=models.CASCADE, related_name='sessions')
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hosted_sessions')
    pin = models.CharField(max_length=6, unique=True, default=generate_pin)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='LOBBY')
    max_players = models.PositiveIntegerField(default=50, help_text="Maksimal o'yinchilar soni")
    current_question_index = models.IntegerField(default=-1)  # -1 = hali boshlanmagan
    question_start_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Session {self.pin} - {self.quiz.title}"
    
    def get_current_question(self):
        """Joriy savolni qaytarish"""
        if self.current_question_index < 0:
            return None
        questions = list(self.quiz.questions.all())
        if self.current_question_index < len(questions):
            return questions[self.current_question_index]
        return None
    
    def total_questions(self):
        return self.quiz.questions.count()


class KahootPlayer(models.Model):
    """O'yinchi: nickname, avatar, ball"""
    AVATAR_CHOICES = [(i, f'Avatar {i}') for i in range(1, 16)]  # 15 ta avatar
    
    session = models.ForeignKey(KahootSession, on_delete=models.CASCADE, related_name='players')
    nickname = models.CharField(max_length=30)
    avatar_id = models.PositiveIntegerField(choices=AVATAR_CHOICES, default=1)
    score = models.IntegerField(default=0)
    session_key = models.CharField(max_length=100, blank=True)  # Django session key
    joined_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-score', 'joined_at']
        unique_together = ['session', 'nickname']
    
    def __str__(self):
        return f"{self.nickname} ({self.score} pts)"


class KahootAnswer(models.Model):
    """O'yinchi javobi har bir savol uchun"""
    player = models.ForeignKey(KahootPlayer, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(KahootQuestion, on_delete=models.CASCADE, related_name='player_answers')
    selected_option = models.CharField(max_length=1, choices=[
        ('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D'),
    ])
    is_correct = models.BooleanField(default=False)
    time_taken = models.FloatField(default=0)  # Soniyalarda
    points_earned = models.IntegerField(default=0)
    answered_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ['player', 'question']
    
    def __str__(self):
        return f"{self.player.nickname} - Q{self.question.order + 1}: {self.selected_option}"
