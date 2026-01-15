# High-Performance Dark-Theme Online Test Platform

A comprehensive Django-based quiz platform with role-based access control (RBAC) and a modern dark-themed UI with proportional scaling design.

## Features

### Role-Based Access Control
- **Superuser**: Complete system access, manage admins and users, view global statistics
- **Admin**: Create/edit tests, manage questions, view test results for their tests
- **User**: Browse available tests, take tests, view personal performance history

### Key Features
- Real-time AJAX answer verification with visual feedback (green for correct, red for incorrect)
- Private test protection with M2M allowed_users relationship
- Test completion modal with option to save results to history
- Dark technical UI/UX with proportional scaling (responsive design using clamp, rem, vw)
- User progress tracking with Chart.js visualizations
- Secure server-side answer validation

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

3. Create a superuser:
```bash
python manage.py createsuperuser
```

4. Run the development server:
```bash
python manage.py runserver
```

## Usage

### Creating Users
- Superusers can manage user roles via the "Manage Users" page in the superuser dashboard
- Users can be assigned roles: Superuser, Admin, or User

### Admin Workflow
1. Login as an Admin
2. Navigate to Admin Dashboard
3. Create a new test (public or private)
4. Add questions with multiple choice options
5. For private tests, select allowed users
6. View results from the test edit page

### User Workflow
1. Login as a User
2. Browse available tests on the dashboard
3. Click "Take Test" to begin
4. Select answers (real-time feedback provided)
5. Submit test and choose to save to history
6. View progress charts and past results

## Technology Stack
- Django 5.0+
- SQLite (default database)
- Tailwind CSS (via CDN)
- Chart.js (for progress visualization)
- Vanilla JavaScript (for AJAX interactions)

## Project Structure
- `quizzes/` - Main application
  - `models.py` - User, Test, Question, Option, UserResult models
  - `views.py` - All views and AJAX endpoints
  - `decorators.py` - RBAC decorators
  - `urls.py` - URL routing
- `templates/quizzes/` - HTML templates with dark theme
- `static/` - Static files (if needed)

## Security Features
- Server-side answer validation (is_correct field never exposed to client)
- CSRF protection on all forms
- Role-based access control on views
- Private test access control via M2M relationship
