from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout, login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
import json
import uuid
from django.utils import timezone

from .models import User, Test, Question, Option, UserResult
from .decorators import superuser_required, admin_required, role_required
from .utils import generate_certificate


def index(request):
    """Home page"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'quizzes/index.html')


def register(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        
        errors = []
        
        # Validate username
        if not username:
            errors.append('Username is required.')
        elif User.objects.filter(username=username).exists():
            errors.append('Username already exists.')
        
        # Validate passwords
        if password1 != password2:
            errors.append('Passwords do not match.')
        elif len(password1) < 8:
            errors.append('Password must be at least 8 characters long.')
        else:
            try:
                validate_password(password1)
            except ValidationError as e:
                errors.extend(e.messages)
        
        # Validate email (optional but must be unique if provided)
        if email and User.objects.filter(email=email).exists():
            errors.append('Email already exists.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'quizzes/register.html')
        
        # Create user with default role 'USER'
        user = User.objects.create_user(
            username=username,
            email=email if email else None,
            password=password1,
            role='USER'
        )
        
        messages.success(request, 'Account created successfully! Please login.')
        return redirect('login')
    
    return render(request, 'quizzes/register.html')


@require_http_methods(["POST"])
@login_required
def logout_view(request):
    """Logout view that only accepts POST requests (Django 5.0+ requirement)"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('index')


@login_required
def dashboard(request):
    """Route users to their role-specific dashboard"""
    user = request.user
    
    if user.is_superuser_role():
        return redirect('superuser_dashboard')
    elif user.is_admin_role():
        return redirect('admin_dashboard')
    else:
        return redirect('user_dashboard')


@superuser_required
def superuser_dashboard(request):
    """Superuser dashboard with global statistics"""
    from django.db.models import Count, Q, Avg
    
    total_users = User.objects.count()
    total_admins = User.objects.filter(role='ADMIN').count()
    total_tests = Test.objects.count()
    total_private_tests = Test.objects.filter(is_private=True).count()
    total_results = UserResult.objects.count()
    
    # Recent admin activity
    recent_tests = Test.objects.select_related('creator').order_by('-created_at')[:10]
    
    # Admin activity stats
    admin_stats = User.objects.filter(role='ADMIN').annotate(
        tests_created=Count('created_tests'),
        total_results=Count('created_tests__results')
    ).order_by('-tests_created')[:10]
    
    # All users with their statistics
    users_with_stats = User.objects.annotate(
        tests_taken=Count('test_results', distinct=True),
        total_score=Avg('test_results__percentage')
    ).order_by('-date_joined')
    
    context = {
        'total_users': total_users,
        'total_admins': total_admins,
        'total_tests': total_tests,
        'total_private_tests': total_private_tests,
        'total_results': total_results,
        'recent_tests': recent_tests,
        'admin_stats': admin_stats,
        'users_with_stats': users_with_stats,
    }
    return render(request, 'quizzes/superuser_dashboard.html', context)


@admin_required
def admin_dashboard(request):
    """Admin dashboard for managing tests"""
    user = request.user
    tests = Test.objects.filter(creator=user).select_related('creator').prefetch_related('questions', 'results')
    
    # Statistics for admin's tests
    total_tests = tests.count()
    total_results = UserResult.objects.filter(test__creator=user).count()
    total_questions = Question.objects.filter(test__creator=user).count()
    
    context = {
        'tests': tests,
        'total_tests': total_tests,
        'total_results': total_results,
        'total_questions': total_questions,
    }
    return render(request, 'quizzes/admin_dashboard.html', context)


@login_required
def user_dashboard(request):
    """User dashboard with available tests and progress"""
    user = request.user
    
    # Get available tests (public or private tests user is allowed to access)
    all_tests = Test.objects.select_related('creator').prefetch_related('allowed_users')
    available_tests = [test for test in all_tests if test.can_access(user)]
    
    # User's test results
    results = UserResult.objects.filter(user=user).select_related('test').order_by('-completed_at')[:10]
    
    # Calculate overall statistics
    total_taken = results.count()
    avg_score = sum(r.percentage for r in results) / total_taken if total_taken > 0 else 0
    
    # Prepare chart data
    chart_labels = [r.test.title[:20] + '...' if len(r.test.title) > 20 else r.test.title for r in results[:5]]
    chart_scores = [round(r.percentage, 1) for r in results[:5]]
    
    context = {
        'available_tests': available_tests,
        'results': results,
        'total_taken': total_taken,
        'avg_score': round(avg_score, 1),
        'chart_labels': json.dumps(chart_labels),
        'chart_scores': json.dumps(chart_scores),
    }
    return render(request, 'quizzes/user_dashboard.html', context)


@admin_required
def test_create(request):
    """Create a new test"""
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        is_private = request.POST.get('is_private') == 'on'
        time_limit = int(request.POST.get('time_limit', 15))
        
        test = Test.objects.create(
            title=title,
            description=description,
            is_private=is_private,
            time_limit=time_limit,
            creator=request.user
        )
        
        # Handle allowed users for private tests
        if is_private:
            allowed_user_ids = request.POST.getlist('allowed_users')
            test.allowed_users.set(User.objects.filter(id__in=allowed_user_ids))
        
        messages.success(request, f'Test "{test.title}" created successfully!')
        return redirect('test_edit', test_id=test.id)
    
    # GET request - show form
    users = User.objects.filter(role='USER').order_by('username')
    context = {'users': users}
    return render(request, 'quizzes/test_create.html', context)


@admin_required
def test_edit(request, test_id):
    """Edit an existing test"""
    test = get_object_or_404(Test, id=test_id)
    
    # Check if user is the creator
    if test.creator != request.user and not request.user.is_superuser_role():
        messages.error(request, 'You can only edit tests you created.')
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        test.title = request.POST.get('title')
        test.description = request.POST.get('description', '')
        test.is_private = request.POST.get('is_private') == 'on'
        test.time_limit = int(request.POST.get('time_limit', 15))
        test.save()
        
        # Handle allowed users
        if test.is_private:
            allowed_user_ids = request.POST.getlist('allowed_users')
            test.allowed_users.set(User.objects.filter(id__in=allowed_user_ids))
        else:
            test.allowed_users.clear()
        
        messages.success(request, 'Test updated successfully!')
        return redirect('test_edit', test_id=test.id)
    
    # GET request
    questions = test.questions.all().prefetch_related('options')
    users = User.objects.filter(role='USER').order_by('username')
    allowed_user_ids = list(test.allowed_users.values_list('id', flat=True))
    
    context = {
        'test': test,
        'questions': questions,
        'users': users,
        'allowed_user_ids': allowed_user_ids,
    }
    return render(request, 'quizzes/test_edit.html', context)


@admin_required
def question_add(request, test_id):
    """Add a question to a test"""
    test = get_object_or_404(Test, id=test_id)
    
    if test.creator != request.user and not request.user.is_superuser_role():
        return HttpResponseForbidden()
    
    if request.method == 'POST':
        question_text = request.POST.get('question_text')
        options = request.POST.getlist('option_text')
        correct_option = int(request.POST.get('correct_option', 0))
        
        # Get next order number
        last_question = test.questions.last()
        order = last_question.order + 1 if last_question else 0
        
        question = Question.objects.create(
            test=test,
            text=question_text,
            order=order
        )
        
        # Create options
        for idx, option_text in enumerate(options):
            if option_text.strip():
                Option.objects.create(
                    question=question,
                    text=option_text,
                    is_correct=(idx == correct_option),
                    order=idx
                )
        
        messages.success(request, 'Question added successfully!')
        return redirect('test_edit', test_id=test.id)
    
    return redirect('test_edit', test_id=test.id)


@admin_required
def question_delete(request, question_id):
    """Delete a question"""
    question = get_object_or_404(Question, id=question_id)
    
    if question.test.creator != request.user and not request.user.is_superuser_role():
        return HttpResponseForbidden()
    
    test_id = question.test.id
    question.delete()
    messages.success(request, 'Question deleted successfully!')
    return redirect('test_edit', test_id=test_id)


@admin_required
@require_POST
def bulk_upload_questions(request, test_id):
    """Bulk upload questions from formatted text"""
    test = get_object_or_404(Test, id=test_id)
    
    if test.creator != request.user and not request.user.is_superuser_role():
        return JsonResponse({'error': 'You do not have permission to edit this test.'}, status=403)
    
    try:
        bulk_data = request.POST.get('bulk_data', '').strip()
        
        if not bulk_data:
            return JsonResponse({'error': 'No data provided.'}, status=400)
        
        # Get current max order number
        last_question = test.questions.last()
        current_order = last_question.order + 1 if last_question else 0
        
        # Split by ++++ to get question blocks
        question_blocks = bulk_data.split('++++')
        
        created_count = 0
        errors = []
        
        for block_idx, block in enumerate(question_blocks):
            block = block.strip()
            if not block:
                continue
            
            lines = [line.strip() for line in block.split('\n') if line.strip()]
            if len(lines) < 2:
                errors.append(f"Block {block_idx + 1}: Not enough lines (need at least question and one option)")
                continue
            
            # First line is the question text
            question_text = lines[0]
            if not question_text:
                errors.append(f"Block {block_idx + 1}: Question text is empty")
                continue
            
            # Join remaining lines and split by ====
            options_text = '\n'.join(lines[1:])
            option_parts = [opt.strip() for opt in options_text.split('====') if opt.strip()]
            
            if len(option_parts) < 2:
                errors.append(f"Block {block_idx + 1}: Need at least 2 options")
                continue
            
            # Validate that exactly one option is marked as correct
            correct_options = [opt for opt in option_parts if opt.startswith('#')]
            if len(correct_options) == 0:
                errors.append(f"Block {block_idx + 1}: No correct answer marked (use # at start of correct option)")
                continue
            elif len(correct_options) > 1:
                errors.append(f"Block {block_idx + 1}: Multiple correct answers marked (only one allowed)")
                continue
            
            # Create question
            question = Question.objects.create(
                test=test,
                text=question_text,
                order=current_order
            )
            current_order += 1
            
            # Create options
            for opt_idx, option_text in enumerate(option_parts):
                # Check if this is the correct answer
                is_correct = option_text.startswith('#')
                
                # Remove # from the beginning if present
                option_text_clean = option_text[1:].strip() if option_text.startswith('#') else option_text.strip()
                
                if not option_text_clean:
                    errors.append(f"Block {block_idx + 1}, Option {opt_idx + 1}: Option text is empty")
                    continue
                
                Option.objects.create(
                    question=question,
                    text=option_text_clean,
                    is_correct=is_correct,
                    order=opt_idx
                )
            
            created_count += 1
        
        if errors and created_count == 0:
            return JsonResponse({
                'success': False,
                'error': 'Failed to create any questions.',
                'errors': errors
            }, status=400)
        
        response_data = {
            'success': True,
            'created_count': created_count,
            'message': f'Successfully created {created_count} question(s).'
        }
        
        if errors:
            response_data['warnings'] = errors
            response_data['message'] += f' {len(errors)} warning(s) occurred.'
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        }, status=500)


@login_required
def test_take(request, test_id):
    """Take a test"""
    test = get_object_or_404(Test, id=test_id)
    
    # Check access
    if not test.can_access(request.user):
        messages.error(request, 'You do not have access to this test.')
        return redirect('user_dashboard')
    
    questions = test.questions.all().prefetch_related('options').order_by('order', 'id')
    
    if not questions.exists():
        messages.error(request, 'This test has no questions yet.')
        return redirect('user_dashboard')
    
    context = {
        'test': test,
        'questions': questions,
    }
    return render(request, 'quizzes/test_take.html', context)


@login_required
@require_POST
def check_answer(request):
    """AJAX endpoint to check if an answer is correct"""
    try:
        data = json.loads(request.body)
        option_id = int(data.get('option_id'))
        
        option = get_object_or_404(Option, id=option_id)
        is_correct = option.is_correct
        
        # Get correct option for this question if answer is wrong
        correct_option = None
        if not is_correct:
            correct_option = option.question.options.filter(is_correct=True).first()
        
        return JsonResponse({
            'is_correct': is_correct,
            'correct_option_id': correct_option.id if correct_option else None,
            'correct_option_text': correct_option.text if correct_option else None,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def submit_test(request, test_id):
    """Submit test and save results"""
    test = get_object_or_404(Test, id=test_id)
    
    if not test.can_access(request.user):
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        answers = data.get('answers', {})  # {question_id: option_id}
        save_to_history = data.get('save_to_history', False)
        time_spent = data.get('time_spent', 0)  # Time spent in seconds
        
        # Calculate results
        questions = test.questions.all()
        total_questions = questions.count()
        correct_count = 0
        
        # Validate answers and count correct ones
        for question_id, option_id in answers.items():
            try:
                option = Option.objects.get(id=option_id, question__id=question_id)
                if option.is_correct:
                    correct_count += 1
            except Option.DoesNotExist:
                pass
        
        percentage = (correct_count / total_questions * 100) if total_questions > 0 else 0
        
        # Save to history if requested
        result = None
        if save_to_history:
            # Generate certificate_id if score >= 80%
            certificate_id = None
            if percentage >= 80:
                import uuid
                certificate_id = uuid.uuid4()
            
            result = UserResult.objects.create(
                user=request.user,
                test=test,
                score=correct_count,
                total_questions=total_questions,
                percentage=percentage,
                time_spent=time_spent,
                certificate_id=certificate_id,
                completed_at=timezone.now(),
                answers=answers
            )
        
        return JsonResponse({
            'success': True,
            'score': correct_count,
            'total': total_questions,
            'percentage': round(percentage, 1),
            'result_id': result.id if result else None,
            'can_get_certificate': percentage >= 80,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def test_results(request, test_id):
    """View results for a specific test (Admin only for their tests)"""
    test = get_object_or_404(Test, id=test_id)
    
    # Check permissions
    if request.user.is_admin_role() and test.creator != request.user and not request.user.is_superuser_role():
        messages.error(request, 'You can only view results for your own tests.')
        return redirect('admin_dashboard')
    
    if request.user.role == 'USER':
        # Users can only see their own results
        results = UserResult.objects.filter(test=test, user=request.user).select_related('user').order_by('-completed_at')
    else:
        # Admins/Superusers can see all results for this test
        results = UserResult.objects.filter(test=test).select_related('user').order_by('-completed_at')
    
    context = {
        'test': test,
        'results': results,
    }
    return render(request, 'quizzes/test_results.html', context)


@login_required
def download_certificate(request, result_id):
    """Download PDF certificate for a test result"""
    result = get_object_or_404(UserResult, id=result_id)
    
    # Check if user owns this result
    if result.user != request.user:
        messages.error(request, 'You do not have permission to download this certificate.')
        return redirect('user_dashboard')
    
    # Check if result qualifies for certificate (>= 80%)
    if result.percentage < 80 or not result.certificate_id:
        messages.error(request, 'This result does not qualify for a certificate (requires 80% or higher).')
        return redirect('user_dashboard')
    
    # Generate PDF
    pdf_buffer = generate_certificate(
        user=result.user,
        test=result.test,
        percentage=result.percentage,
        certificate_id=result.certificate_id
    )
    
    # Create HTTP response with PDF
    response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
    filename = f"certificate_{result.user.username}_{result.test.title.replace(' ', '_')}_{str(result.certificate_id)[:8]}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@superuser_required
def manage_users(request):
    """Superuser page to manage users and admins"""
    users = User.objects.all().order_by('-date_joined')
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        new_role = request.POST.get('role')
        
        user = get_object_or_404(User, id=user_id)
        user.role = new_role
        user.save()
        
        messages.success(request, f'User {user.username} role updated to {user.get_role_display()}.')
        return redirect('manage_users')
    
    context = {'users': users}
    return render(request, 'quizzes/manage_users.html', context)


@login_required
def leaderboard(request):
    """Display global leaderboard with top 10 users by highest score"""
    from django.db.models import Max
    
    # Get top results (highest percentage per user per test, then average)
    top_results = UserResult.objects.filter(
        completed_at__isnull=False
    ).select_related('user', 'test').order_by('-percentage')[:50]
    
    # Aggregate by user to get their best average
    user_stats = {}
    for result in top_results:
        if result.user.id not in user_stats:
            user_stats[result.user.id] = {
                'user': result.user,
                'results': [],
                'best_score': 0,
                'avg_score': 0,
                'total_tests': 0,
                'total_time': 0,
            }
        
        user_stats[result.user.id]['results'].append(result)
        user_stats[result.user.id]['best_score'] = max(
            user_stats[result.user.id]['best_score'], 
            result.percentage
        )
    
    # Calculate averages
    for user_id, stats in user_stats.items():
        if stats['results']:
            stats['avg_score'] = sum(r.percentage for r in stats['results']) / len(stats['results'])
            stats['total_tests'] = len(stats['results'])
            stats['total_time'] = sum(r.time_spent for r in stats['results'])
    
    # Sort by best score and get top 10
    leaderboard_data = sorted(
        user_stats.values(), 
        key=lambda x: x['best_score'], 
        reverse=True
    )[:10]
    
    context = {
        'leaderboard': leaderboard_data,
    }
    return render(request, 'quizzes/leaderboard.html', context)


@superuser_required
@require_POST
def toggle_user_role(request, user_id):
    """AJAX endpoint to promote/demote user role"""
    target_user = get_object_or_404(User, id=user_id)
    
    # Prevent self-modification
    if target_user.id == request.user.id:
        return JsonResponse({'error': 'You cannot change your own role.'}, status=400)
    
    # Toggle between USER and ADMIN (superusers are not changed via this endpoint)
    if target_user.role == 'USER':
        target_user.role = 'ADMIN'
        action = 'promoted'
        new_role_display = 'Admin'
    elif target_user.role == 'ADMIN':
        target_user.role = 'USER'
        action = 'demoted'
        new_role_display = 'User'
    else:
        # Superuser or other roles - don't change
        return JsonResponse({'error': 'Cannot change superuser role via this endpoint.'}, status=400)
    
    target_user.save()
    
    return JsonResponse({
        'success': True,
        'action': action,
        'new_role': target_user.role,
        'new_role_display': new_role_display,
        'message': f'User {target_user.username} {action} to {new_role_display}.'
    })
