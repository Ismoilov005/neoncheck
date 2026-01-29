# Kahoot Mode Views
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
import json

# 15 ta avatar emoji (avatar_id 1–15 uchun)
KAHOOT_AVATAR_EMOJIS = ['😀', '😎', '🤓', '😺', '🦊', '🐶', '🐱', '🦁', '🐼', '🐸', '🦄', '🐲', '🤖', '👽', '🎃']

from .models import (
    KahootQuiz, KahootQuestion, KahootSession, KahootPlayer, KahootAnswer, User
)
from .decorators import admin_required


# ==================== GUEST JOIN ====================

def kahoot_join(request):
    """Guest join page: PIN, Nickname, Avatar selection"""
    if request.method == 'POST':
        pin = request.POST.get('pin', '').strip()
        nickname = request.POST.get('nickname', '').strip()
        avatar_id = int(request.POST.get('avatar_id', 1))
        
        if not pin or not nickname:
            messages.error(request, 'PIN va Nickname kiritish shart!')
            return render(request, 'kahoot/join.html')
        
        # Session mavjudligini tekshirish
        try:
            session = KahootSession.objects.get(pin=pin, status='LOBBY')
        except KahootSession.DoesNotExist:
            messages.error(request, 'Bu PIN bilan o\'yin topilmadi yoki u allaqachon boshlangan.')
            return render(request, 'kahoot/join.html')
        
        # Nickname unikal bo'lishi kerak
        if session.players.filter(nickname=nickname).exists():
            messages.error(request, 'Bu ism allaqachon band. Boshqa ism tanlang.')
            return render(request, 'kahoot/join.html')
        
        # Maksimal o'yinchilar limiti
        max_players = getattr(session, 'max_players', 50) or 50
        if session.players.count() >= max_players:
            messages.error(request, 'O\'yin to\'ldi. Maksimal o\'yinchilar soni: ' + str(max_players))
            return render(request, 'kahoot/join.html')
        
        # Player yaratish
        player = KahootPlayer.objects.create(
            session=session,
            nickname=nickname,
            avatar_id=avatar_id,
            session_key=request.session.session_key or '',
        )
        
        # Session'da saqlash
        request.session['kahoot_player_id'] = player.id
        request.session['kahoot_session_pin'] = pin
        
        return redirect('kahoot_player_lobby', pin=pin)
    
    return render(request, 'kahoot/join.html')


def kahoot_player_lobby(request, pin):
    """Player waiting in lobby"""
    player_id = request.session.get('kahoot_player_id')
    if not player_id:
        return redirect('kahoot_join')
    
    try:
        player = KahootPlayer.objects.select_related('session', 'session__quiz').get(id=player_id)
        session = player.session
    except KahootPlayer.DoesNotExist:
        return redirect('kahoot_join')
    
    if session.pin != pin:
        return redirect('kahoot_join')
    
    # Agar o'yin boshlangan bo'lsa, avtomatik game sahifasiga yo'naltirish
    if session.status == 'PLAYING':
        return redirect('kahoot_player_game', pin=pin)
    
    avatar_id = getattr(player, 'avatar_id', 1) or 1
    avatar_emoji = KAHOOT_AVATAR_EMOJIS[avatar_id - 1] if 1 <= avatar_id <= 15 else KAHOOT_AVATAR_EMOJIS[0]
    context = {
        'player': player,
        'session': session,
        'pin': pin,
        'avatar_emoji': avatar_emoji,
    }
    return render(request, 'kahoot/player_lobby.html', context)


def kahoot_player_game(request, pin):
    """Player game screen"""
    player_id = request.session.get('kahoot_player_id')
    if not player_id:
        return redirect('kahoot_join')
    
    try:
        player = KahootPlayer.objects.select_related('session').get(id=player_id)
        session = player.session
    except KahootPlayer.DoesNotExist:
        return redirect('kahoot_join')
    
    if session.pin != pin:
        return redirect('kahoot_join')
    
    # Agar o'yin tugagan bo'lsa, podium sahifasiga yo'naltirish
    if session.status == 'FINISHED':
        return redirect('kahoot_player_podium', pin=pin)
    
    avatar_id = getattr(player, 'avatar_id', 1) or 1
    avatar_emoji = KAHOOT_AVATAR_EMOJIS[avatar_id - 1] if 1 <= avatar_id <= 15 else KAHOOT_AVATAR_EMOJIS[0]
    context = {
        'player': player,
        'session': session,
        'pin': pin,
        'avatar_emoji': avatar_emoji,
    }
    return render(request, 'kahoot/player_game.html', context)


def kahoot_player_podium(request, pin):
    """Player podium/results screen"""
    player_id = request.session.get('kahoot_player_id')
    if not player_id:
        return redirect('kahoot_join')
    
    try:
        player = KahootPlayer.objects.select_related('session').get(id=player_id)
        session = player.session
    except KahootPlayer.DoesNotExist:
        return redirect('kahoot_join')
    
    if session.pin != pin:
        return redirect('kahoot_join')
    
    # Top 3 o'yinchilar
    top_players = session.players.order_by('-score')[:3]
    all_players = session.players.order_by('-score')
    
    # O'yinchining o'rni
    player_rank = list(all_players.values_list('id', flat=True)).index(player.id) + 1 if player.id in all_players.values_list('id', flat=True) else 0
    
    context = {
        'player': player,
        'session': session,
        'pin': pin,
        'top_players': top_players,
        'player_rank': player_rank,
        'total_players': all_players.count(),
    }
    return render(request, 'kahoot/player_podium.html', context)


# ==================== HOST (ADMIN) ====================

@login_required
def kahoot_dashboard(request):
    """Host dashboard: create/manage quizzes and sessions"""
    quizzes = KahootQuiz.objects.filter(creator=request.user)
    active_sessions = KahootSession.objects.filter(
        host=request.user, 
        status__in=['LOBBY', 'PLAYING']
    )
    
    context = {
        'quizzes': quizzes,
        'active_sessions': active_sessions,
    }
    return render(request, 'kahoot/dashboard.html', context)


@login_required
def kahoot_create_quiz(request):
    """Create new Kahoot quiz"""
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, 'Quiz nomi kiritilishi shart!')
            return render(request, 'kahoot/create_quiz.html')
        
        quiz = KahootQuiz.objects.create(title=title, creator=request.user)
        messages.success(request, f'Quiz "{title}" yaratildi!')
        return redirect('kahoot_edit_quiz', quiz_id=quiz.id)
    
    return render(request, 'kahoot/create_quiz.html')


@login_required
def kahoot_edit_quiz(request, quiz_id):
    """Edit quiz: add/edit questions"""
    quiz = get_object_or_404(KahootQuiz, id=quiz_id, creator=request.user)
    
    if request.method == 'POST':
        # Add new question
        text = request.POST.get('text', '').strip()
        option_a = request.POST.get('option_a', '').strip()
        option_b = request.POST.get('option_b', '').strip()
        option_c = request.POST.get('option_c', '').strip()
        option_d = request.POST.get('option_d', '').strip()
        correct = request.POST.get('correct_option', 'A')
        time_limit = int(request.POST.get('time_limit', 20))
        image = request.FILES.get('image')
        
        if text and option_a and option_b and option_c and option_d:
            order = quiz.questions.count()
            KahootQuestion.objects.create(
                quiz=quiz,
                text=text,
                option_a=option_a,
                option_b=option_b,
                option_c=option_c,
                option_d=option_d,
                correct_option=correct,
                time_limit=time_limit,
                image=image,
                order=order,
            )
            messages.success(request, 'Savol qo\'shildi!')
        else:
            messages.error(request, 'Barcha maydonlarni to\'ldiring!')
        
        return redirect('kahoot_edit_quiz', quiz_id=quiz.id)
    
    context = {
        'quiz': quiz,
        'questions': quiz.questions.all().order_by('order'),
    }
    return render(request, 'kahoot/edit_quiz.html', context)


@login_required
def kahoot_edit_question(request, question_id):
    """Tahrirlash: savol matni, variantlar, rasm"""
    question = get_object_or_404(KahootQuestion, id=question_id, quiz__creator=request.user)
    quiz = question.quiz
    if request.method == 'POST':
        question.text = request.POST.get('text', question.text).strip()
        question.option_a = request.POST.get('option_a', question.option_a).strip()
        question.option_b = request.POST.get('option_b', question.option_b).strip()
        question.option_c = request.POST.get('option_c', question.option_c).strip()
        question.option_d = request.POST.get('option_d', question.option_d).strip()
        question.correct_option = request.POST.get('correct_option', question.correct_option)
        question.time_limit = int(request.POST.get('time_limit', question.time_limit))
        if request.FILES.get('image'):
            question.image = request.FILES['image']
        question.save()
        messages.success(request, 'Savol saqlandi!')
        return redirect('kahoot_edit_quiz', quiz_id=quiz.id)
    context = {'question': question, 'quiz': quiz}
    return render(request, 'kahoot/edit_question.html', context)


@login_required
@require_POST
def kahoot_delete_question(request, question_id):
    """Delete a question"""
    question = get_object_or_404(KahootQuestion, id=question_id, quiz__creator=request.user)
    quiz_id = question.quiz.id
    question.delete()
    messages.success(request, 'Savol o\'chirildi!')
    return redirect('kahoot_edit_quiz', quiz_id=quiz_id)


@login_required
def kahoot_start_session(request, quiz_id):
    """Create new session for a quiz"""
    quiz = get_object_or_404(KahootQuiz, id=quiz_id, creator=request.user)
    
    if quiz.questions.count() == 0:
        messages.error(request, 'Quizda savollar yo\'q!')
        return redirect('kahoot_edit_quiz', quiz_id=quiz.id)
    
    # Create new session
    session = KahootSession.objects.create(quiz=quiz, host=request.user)
    
    return redirect('kahoot_host_lobby', pin=session.pin)


@login_required
def kahoot_host_lobby(request, pin):
    """Host lobby: waiting for players"""
    session = get_object_or_404(KahootSession, pin=pin, host=request.user)
    
    context = {
        'session': session,
        'quiz': session.quiz,
        'pin': pin,
    }
    return render(request, 'kahoot/host_lobby.html', context)


@login_required
def kahoot_host_game(request, pin):
    """Host game screen: show questions on big screen"""
    session = get_object_or_404(KahootSession, pin=pin, host=request.user)
    
    context = {
        'session': session,
        'quiz': session.quiz,
        'pin': pin,
        'total_questions': session.quiz.questions.count(),
    }
    return render(request, 'kahoot/host_game.html', context)


# ==================== API ENDPOINTS ====================

@require_GET
def kahoot_session_info(request, pin):
    """Get session info for AJAX"""
    try:
        session = KahootSession.objects.select_related('quiz').get(pin=pin)
        players = list(session.players.values('id', 'nickname', 'avatar_id', 'score'))
        return JsonResponse({
            'status': session.status,
            'quiz_title': session.quiz.title,
            'total_questions': session.quiz.questions.count(),
            'current_question': session.current_question_index,
            'players': players,
            'player_count': len(players),
        })
    except KahootSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)