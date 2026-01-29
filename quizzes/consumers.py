# Kahoot Mode WebSocket Consumer
import asyncio
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class KahootConsumer(AsyncWebsocketConsumer):
    """
    Real-time WebSocket consumer for Kahoot game sessions.
    Handles: player join, host controls, answer submission, score updates.
    """

    async def connect(self):
        self.session_pin = self.scope['url_route']['kwargs']['session_pin']
        self.room_group_name = f'kahoot_{self.session_pin}'
        self.player_id = None
        self.is_host = False

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Notify others if player left
        if self.player_id:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'player_left',
                    'player_id': self.player_id,
                }
            )

    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        data = json.loads(text_data)
        action = data.get('action')

        if action == 'host_join':
            await self.handle_host_join(data)
        elif action == 'player_join':
            await self.handle_player_join(data)
        elif action == 'player_ready':
            await self.handle_player_ready(data)
        elif action == 'start_game':
            await self.handle_start_game()
        elif action == 'next_question':
            await self.handle_next_question()
        elif action == 'submit_answer':
            await self.handle_submit_answer(data)
        elif action == 'show_results':
            await self.handle_show_results()
        elif action == 'end_game':
            await self.handle_end_game()
        elif action == 'kick_player':
            await self.handle_kick_player(data)

    # ==================== HOST ACTIONS ====================

    async def handle_host_join(self, data):
        """Host joins the session"""
        self.is_host = True
        session = await self.get_session()
        if session:
            players = await self.get_players_list()
            payload = {
                'type': 'host_connected',
                'session_pin': self.session_pin,
                'quiz_title': session['quiz_title'],
                'total_questions': session['total_questions'],
                'max_players': session.get('max_players', 50),
                'players': players,
                'status': session.get('status', 'LOBBY'),
            }
            
            # Agar o'yin davom etayotgan bo'lsa, joriy savolni yuborish
            if session.get('status') == 'PLAYING' and session.get('current_question_index', -1) >= 0:
                current_q = await self.get_current_question_data()
                if current_q:
                    payload['current_question'] = current_q
            
            await self.send(text_data=json.dumps(payload))

    async def handle_player_join(self, data):
        """Player joins the session"""
        player_id = data.get('player_id')
        nickname = data.get('nickname')
        avatar_id = data.get('avatar_id')
        
        self.player_id = player_id
        
        # Notify all (including host) about new player
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'player_joined',
                'player_id': player_id,
                'nickname': nickname,
                'avatar_id': avatar_id,
            }
        )

    async def handle_player_ready(self, data):
        """
        O'yinchi game sahifasiga o'tdi va WebSocket tayyor.
        Agar o'yin allaqachon boshlangan bo'lsa, joriy savolni yuborish.
        """
        player_id = data.get('player_id')
        if not player_id:
            return
        
        self.player_id = player_id
        
        # Sessiya holatini tekshirish
        session = await self.get_session()
        if not session:
            return
        
        # Agar o'yin PLAYING holatida bo'lsa va savol mavjud bo'lsa
        if session.get('status') == 'PLAYING':
            current_index = session.get('current_question_index', -1)
            
            # Joriy savolni olish
            if current_index >= 0:
                question_data = await self.get_current_question_data()
                
                if question_data:
                    # O'yinchining bu savolga javob berganligini tekshirish
                    has_answered = await self.check_player_answered(player_id, question_data.get('question_id'))
                    
                    # Player scoreni yuborish
                    player_score = await self.get_player_score(player_id)
                    
                    # O'yinchiga shaxsiy xabar yuborish
                    await self.send(text_data=json.dumps({
                        'type': 'sync_current_state',
                        'status': 'PLAYING',
                        'current_score': player_score,
                        'question': {
                            'question_id': question_data.get('question_id'),
                            'index': question_data.get('index'),
                            'total': question_data.get('total'),
                            'text': question_data.get('text', ''),
                            'image': question_data.get('image'),
                            'options': {
                                'A': question_data.get('options', {}).get('A', ''),
                                'B': question_data.get('options', {}).get('B', ''),
                                'C': question_data.get('options', {}).get('C', ''),
                                'D': question_data.get('options', {}).get('D', ''),
                            },
                            'time_limit': question_data.get('time_limit', 20),
                            'has_answered': has_answered,
                        }
                    }))
                    return
        
        # Agar LOBBY yoki FINISHED holatida bo'lsa
        await self.send(text_data=json.dumps({
            'type': 'sync_current_state',
            'status': session.get('status', 'LOBBY'),
        }))

    async def handle_kick_player(self, data):
        """Host o'yinchini kick qiladi (faqat LOBBY holatida)"""
        if not self.is_host:
            return
        session = await self.get_session()
        if not session or session.get('status') != 'LOBBY':
            return
        player_id = data.get('player_id')
        if not player_id:
            return
        removed = await self.remove_player_from_session(player_id)
        if removed:
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'player_kicked', 'player_id': player_id},
            )

    async def handle_start_game(self):
        """Host starts the game"""
        if not self.is_host:
            return
        
        await self.update_session_status('PLAYING')
        
        # Notify all players to switch to game screen
        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'game_started'},
        )
        
        # O'yinchilar sahifaga o'tib WebSocket ulanishini o'rnatishi uchun kutish
        await asyncio.sleep(2.0)
        
        # Birinchi savolni yuborish
        session = await self.get_session()
        if session and session.get('total_questions', 0) > 0:
            await self.handle_next_question()

    async def handle_next_question(self):
        """Move to next question"""
        if not self.is_host:
            return
        
        question_data = await self.advance_to_next_question()
        
        if question_data:
            # Player va Host uchun savol matni va variant matnlari aniq yuboriladi
            payload = {
                'type': 'show_question',
                'question': {
                    'question_id': question_data.get('question_id'),
                    'index': question_data.get('index'),
                    'total': question_data.get('total'),
                    'text': question_data.get('text', ''),
                    'image': question_data.get('image'),
                    'options': {
                        'A': question_data.get('options', {}).get('A', ''),
                        'B': question_data.get('options', {}).get('B', ''),
                        'C': question_data.get('options', {}).get('C', ''),
                        'D': question_data.get('options', {}).get('D', ''),
                    },
                    'time_limit': question_data.get('time_limit', 20),
                },
            }
            await self.channel_layer.group_send(self.room_group_name, payload)
        else:
            # No more questions, end game
            await self.handle_end_game()

    async def handle_submit_answer(self, data):
        """Player submits answer"""
        player_id = data.get('player_id')
        selected_option = data.get('selected_option')
        time_taken = data.get('time_taken', 0)
        
        result = await self.save_answer(player_id, selected_option, time_taken)
        
        # Send feedback to the player who answered
        await self.send(text_data=json.dumps({
            'type': 'answer_result',
            'is_correct': result['is_correct'],
            'points_earned': result['points_earned'],
            'total_score': result['total_score'],
            'rank': result['rank'],
        }))
        
        # Notify host about answer count
        answer_count = await self.get_answer_count()
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'answer_count_update',
                'count': answer_count['count'],
                'total': answer_count['total'],
            }
        )

    async def handle_show_results(self):
        """Show results after question timer ends"""
        if not self.is_host:
            return
        
        results = await self.get_question_results()
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'question_results',
                'results': results,
            }
        )

    async def handle_end_game(self):
        """End the game and show podium"""
        await self.update_session_status('FINISHED')
        
        podium = await self.get_podium()
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'game_ended',
                'podium': podium,
            }
        )

    # ==================== GROUP MESSAGE HANDLERS ====================

    async def player_joined(self, event):
        await self.send(text_data=json.dumps({
            'type': 'player_joined',
            'player_id': event['player_id'],
            'nickname': event['nickname'],
            'avatar_id': event['avatar_id'],
        }))

    async def player_left(self, event):
        await self.send(text_data=json.dumps({
            'type': 'player_left',
            'player_id': event['player_id'],
        }))

    async def game_started(self, event):
        await self.send(text_data=json.dumps({
            'type': 'game_started',
        }))

    async def show_question(self, event):
        # Player va Host uchun savol matni va options (A,B,C,D) yuboriladi
        q = event.get('question') or {}
        await self.send(text_data=json.dumps({
            'type': 'show_question',
            'question': {
                'question_id': q.get('question_id'),
                'index': q.get('index'),
                'total': q.get('total'),
                'text': q.get('text', ''),
                'image': q.get('image'),
                'options': {
                    'A': q.get('options', {}).get('A', ''),
                    'B': q.get('options', {}).get('B', ''),
                    'C': q.get('options', {}).get('C', ''),
                    'D': q.get('options', {}).get('D', ''),
                },
                'time_limit': q.get('time_limit', 20),
            },
        }))

    async def answer_count_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'answer_count_update',
            'count': event['count'],
            'total': event['total'],
        }))

    async def question_results(self, event):
        await self.send(text_data=json.dumps({
            'type': 'question_results',
            'results': event['results'],
        }))

    async def game_ended(self, event):
        await self.send(text_data=json.dumps({
            'type': 'game_ended',
            'podium': event['podium'],
        }))

    async def player_kicked(self, event):
        await self.send(text_data=json.dumps({
            'type': 'player_kicked',
            'player_id': event['player_id'],
        }))

    # ==================== DATABASE OPERATIONS ====================

    @database_sync_to_async
    def get_session(self):
        from .models import KahootSession
        try:
            session = KahootSession.objects.select_related('quiz').get(pin=self.session_pin)
            return {
                'quiz_title': session.quiz.title,
                'total_questions': session.quiz.questions.count(),
                'status': session.status,
                'current_question_index': session.current_question_index,
                'max_players': getattr(session, 'max_players', 50) or 50,
            }
        except KahootSession.DoesNotExist:
            return None

    @database_sync_to_async
    def remove_player_from_session(self, player_id):
        from .models import KahootSession, KahootPlayer
        try:
            session = KahootSession.objects.get(pin=self.session_pin)
            deleted, _ = KahootPlayer.objects.filter(session=session, id=player_id).delete()
            return deleted > 0
        except KahootSession.DoesNotExist:
            return False

    @database_sync_to_async
    def get_players_list(self):
        from .models import KahootSession
        try:
            session = KahootSession.objects.get(pin=self.session_pin)
            players = list(session.players.values('id', 'nickname', 'avatar_id', 'score'))
            return players
        except KahootSession.DoesNotExist:
            return []

    @database_sync_to_async
    def update_session_status(self, status):
        from .models import KahootSession
        KahootSession.objects.filter(pin=self.session_pin).update(status=status)

    @database_sync_to_async
    def get_current_question_data(self):
        """Joriy savolni (index o'zgartirmasdan) qaytaradi"""
        from .models import KahootSession
        try:
            session = KahootSession.objects.select_related('quiz').get(pin=self.session_pin)
            questions = list(session.quiz.questions.all().order_by('order'))
            if session.current_question_index < 0 or session.current_question_index >= len(questions):
                return None
            q = questions[session.current_question_index]
            return {
                'index': session.current_question_index,
                'total': len(questions),
                'text': q.text,
                'image': q.image.url if q.image else None,
                'options': {'A': q.option_a, 'B': q.option_b, 'C': q.option_c, 'D': q.option_d},
                'time_limit': q.time_limit,
                'question_id': q.id,
            }
        except KahootSession.DoesNotExist:
            return None

    @database_sync_to_async
    def check_player_answered(self, player_id, question_id):
        """O'yinchi bu savolga javob berganmi?"""
        from .models import KahootAnswer
        try:
            return KahootAnswer.objects.filter(
                player_id=player_id,
                question_id=question_id
            ).exists()
        except:
            return False

    @database_sync_to_async
    def get_player_score(self, player_id):
        """O'yinchining hozirgi balini olish"""
        from .models import KahootPlayer
        try:
            player = KahootPlayer.objects.get(id=player_id)
            return player.score
        except:
            return 0

    @database_sync_to_async
    def advance_to_next_question(self):
        from .models import KahootSession
        try:
            session = KahootSession.objects.select_related('quiz').get(pin=self.session_pin)
            session.current_question_index += 1
            session.question_start_time = timezone.now()
            session.save()
            
            questions = list(session.quiz.questions.all().order_by('order'))
            if session.current_question_index < len(questions):
                q = questions[session.current_question_index]
                return {
                    'index': session.current_question_index,
                    'total': len(questions),
                    'text': q.text,
                    'image': q.image.url if q.image else None,
                    'options': {
                        'A': q.option_a,
                        'B': q.option_b,
                        'C': q.option_c,
                        'D': q.option_d,
                    },
                    'time_limit': q.time_limit,
                    'question_id': q.id,
                }
            return None
        except KahootSession.DoesNotExist:
            return None

    @database_sync_to_async
    def save_answer(self, player_id, selected_option, time_taken):
        from .models import KahootSession, KahootPlayer, KahootQuestion, KahootAnswer
        try:
            session = KahootSession.objects.get(pin=self.session_pin)
            player = KahootPlayer.objects.get(id=player_id, session=session)
            question = session.get_current_question()
            
            if not question:
                return {'is_correct': False, 'points_earned': 0, 'total_score': 0, 'rank': 0}
            
            is_correct = (selected_option == question.correct_option)
            
            # Ball hisoblash: 1000 * (Qolgan_Vaqt / Umumiy_Vaqt)
            if is_correct:
                remaining_time = max(0, question.time_limit - time_taken)
                points = int(1000 * (remaining_time / question.time_limit))
            else:
                points = 0
            
            # Javobni saqlash
            answer, created = KahootAnswer.objects.update_or_create(
                player=player,
                question=question,
                defaults={
                    'selected_option': selected_option,
                    'is_correct': is_correct,
                    'time_taken': time_taken,
                    'points_earned': points,
                }
            )
            
            # Umumiy balni yangilash
            if created or points > 0:
                player.score = sum(a.points_earned for a in player.answers.all())
                player.save()
            
            # Joriy o'rin (rank)
            all_players = list(session.players.order_by('-score', 'joined_at'))
            rank = next((i + 1 for i, p in enumerate(all_players) if p.id == player.id), 0)
            
            return {
                'is_correct': is_correct,
                'points_earned': points,
                'total_score': player.score,
                'rank': rank,
            }
        except Exception as e:
            print(f"Error saving answer: {e}")
            return {'is_correct': False, 'points_earned': 0, 'total_score': 0, 'rank': 0}

    @database_sync_to_async
    def get_answer_count(self):
        from .models import KahootSession
        try:
            session = KahootSession.objects.get(pin=self.session_pin)
            question = session.get_current_question()
            if not question:
                return {'count': 0, 'total': 0}
            
            count = question.player_answers.filter(player__session=session).count()
            total = session.players.count()
            return {'count': count, 'total': total}
        except:
            return {'count': 0, 'total': 0}

    @database_sync_to_async
    def get_question_results(self):
        from .models import KahootSession
        try:
            session = KahootSession.objects.get(pin=self.session_pin)
            question = session.get_current_question()
            if not question:
                return {}
            
            # Har bir variant uchun javoblar soni
            from django.db.models import Count
            answer_counts = {
                'A': question.player_answers.filter(player__session=session, selected_option='A').count(),
                'B': question.player_answers.filter(player__session=session, selected_option='B').count(),
                'C': question.player_answers.filter(player__session=session, selected_option='C').count(),
                'D': question.player_answers.filter(player__session=session, selected_option='D').count(),
            }
            
            # Top 5 o'yinchi
            top_players = list(session.players.order_by('-score')[:5].values('nickname', 'score', 'avatar_id'))
            
            return {
                'correct_option': question.correct_option,
                'answer_counts': answer_counts,
                'top_players': top_players,
            }
        except:
            return {}

    @database_sync_to_async
    def get_podium(self):
        from .models import KahootSession
        try:
            session = KahootSession.objects.get(pin=self.session_pin)
            top3 = list(session.players.order_by('-score')[:3].values('nickname', 'score', 'avatar_id'))
            return top3
        except:
            return []