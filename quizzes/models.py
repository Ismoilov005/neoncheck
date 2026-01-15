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
