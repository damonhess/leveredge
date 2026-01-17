# REMINDERS-V2 - Proactive Reminders Agent

**Port: 8065**

A smart reminder system designed with ADHD-friendly principles, featuring user pattern-based timing optimization, context-aware nudges, and motivational check-ins.

## Features

### 1. Smart Reminder Timing
- Analyzes user activity patterns to determine optimal reminder times
- Learns from response times and adjusts scheduling accordingly
- Respects quiet hours and low-activity periods
- Adapts to morning/evening person preferences

### 2. Context-Aware Nudges
- Task-specific nudges (coding, writing, meetings, admin, creative)
- Time-of-day appropriate messaging
- Energy-level based suggestions
- Focus score responses

### 3. Deadline Approaching Alerts
- Integrates with Supabase (aria_tasks table) for task deadlines
- Google Calendar event reminders (when configured)
- Progressive urgency levels (approaching, imminent, overdue)
- Automatic priority escalation

### 4. Daily Briefing
- Morning briefing at 8 AM with day's overview
- Task summary with due today / overdue counts
- Calendar events for the day
- Personalized focus suggestions based on patterns
- Motivational element included

### 5. ADHD-Friendly Motivational Check-ins
- Non-judgmental, supportive messaging
- Focus checks during work sessions
- Break reminders based on focus duration patterns
- Celebration of small wins
- Gentle redirects when distracted
- Energy and mood tracking

## API Endpoints

### Health Check
```
GET /health
```
Returns agent status, scheduler state, and reminder statistics.

### Schedule Reminder
```
POST /schedule
```
Schedule a new reminder with optional smart timing.

**Request Body:**
```json
{
  "title": "Review PRs",
  "message": "Check pending pull requests in the repo",
  "scheduled_time": null,
  "reminder_type": "standard",
  "priority": "normal",
  "repeat_pattern": "weekdays",
  "context": {"repo": "main-app"},
  "tags": ["dev", "review"],
  "user_id": "default",
  "use_smart_timing": true
}
```

**Reminder Types:** standard, deadline, checkin, briefing, motivational, context_nudge

**Priority Levels:** low, normal, high, urgent

**Repeat Patterns:** none, daily, weekdays, weekly, biweekly, monthly

### Get Pending Reminders
```
GET /pending?user_id=default&include_context=false
```
Returns all pending reminders for a user.

### Manual Trigger
```
POST /trigger
```
Manually trigger reminder/deadline checks.

**Request Body:**
```json
{
  "user_id": "default",
  "force": false,
  "check_types": ["deadline", "checkin", "briefing", "motivation"]
}
```

### Get User Patterns
```
GET /patterns/{user_id}
```
Returns analyzed activity patterns including:
- Peak focus hours
- Best response hours
- Preferred days
- Average response time
- Focus duration estimates

### Record Check-in
```
POST /checkin
```
Record an ADHD-friendly check-in with mood/focus/energy data.

**Request Body:**
```json
{
  "user_id": "default",
  "mood_score": 7,
  "focus_score": 6,
  "energy_level": "medium",
  "current_task": "Writing documentation",
  "blockers": null
}
```

### Get Briefing
```
GET /briefing/{user_id}?briefing_type=daily
```
Generate and return a daily or quick briefing.

### Cancel Reminder
```
DELETE /reminder/{reminder_id}
```
Cancel a pending reminder.

### Send Contextual Nudge
```
POST /nudge?user_id=default&context=coding&nudge_type=focus_check
```
Send an immediate context-aware nudge.

## Integration

### HERMES (Notifications)
Reminders are sent via HERMES (port 8014) for Telegram delivery.

**Environment Variable:**
```
HERMES_URL=http://hermes:8014
```

### Event Bus
All significant events are logged to the Event Bus (port 8099).

**Environment Variable:**
```
EVENT_BUS_URL=http://event-bus:8099
```

### Supabase (Tasks)
Task deadlines are fetched from the `aria_tasks` table.

**Environment Variables:**
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-key
```

### Google Calendar (Optional)
Calendar events can be fetched for deadline alerts.

**Environment Variable:**
```
GOOGLE_CALENDAR_CREDENTIALS=/path/to/credentials.json
```

## Scheduled Jobs

The agent runs several background jobs via APScheduler:

| Job | Interval | Description |
|-----|----------|-------------|
| reminder_check | 1 minute | Check and trigger due reminders |
| deadline_check | 15 minutes | Check for approaching deadlines |
| adhd_checkin | 2 hours | Send motivational check-ins |
| morning_briefing | 8:00 AM daily | Send daily briefing |

## Data Storage

### SQLite Database
Default path: `/app/data/reminders_v2.db`

Tables:
- `reminders` - Scheduled reminders
- `activity_log` - User activity for pattern analysis
- `checkins` - Check-in history
- `briefings` - Briefing delivery history

### Patterns JSON
Default path: `/app/data/patterns.json`

Stores derived user patterns for quick access.

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export HERMES_URL=http://localhost:8014
export EVENT_BUS_URL=http://localhost:8099
export REMINDERS_DB_PATH=/tmp/reminders_v2.db
export PATTERNS_PATH=/tmp/patterns.json

# Run the agent
python reminders_v2.py
```

## Docker

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py .

# Data directory for SQLite and patterns
RUN mkdir -p /app/data

ENV REMINDERS_DB_PATH=/app/data/reminders_v2.db
ENV PATTERNS_PATH=/app/data/patterns.json

EXPOSE 8065

CMD ["python", "reminders_v2.py"]
```

## Pattern Analysis

The pattern analyzer tracks:

- **Peak Focus Hours**: When user is most focused (based on activity and response times)
- **Peak Activity Hours**: When user is most active
- **Best Response Hours**: When user responds fastest to notifications
- **Preferred Days**: Days with highest activity
- **Focus Duration**: Estimated typical focus session length
- **Chronotype**: Morning person vs evening person

Patterns are updated based on:
- Response times to reminders
- Check-in data (mood, focus, energy)
- Activity timestamps
- Task completion patterns

## ADHD-Friendly Design Principles

1. **Short, Clear Messages**: All nudges are concise and actionable
2. **Non-Judgmental Tone**: Never shame for missed tasks or low focus
3. **Progress Celebration**: Acknowledge and celebrate small wins
4. **Flexible Scheduling**: Reminders adapt to user's natural rhythms
5. **Energy Awareness**: Suggests appropriate tasks based on energy level
6. **Break Reminders**: Encourages healthy work patterns
7. **One Thing Focus**: Encourages focusing on single tasks vs overwhelming lists

## Example Nudge Messages

**Morning:**
> "Good morning! Ready to tackle today? What's your first small win going to be?"

**Focus Check:**
> "Quick focus check: Still on task? If you drifted, that's okay - just gently redirect."

**ADHD Motivation:**
> "Remember: ADHD brains are creative powerhouses. Work with your brain, not against it."

**Low Energy:**
> "Low energy is valid. What's ONE small thing you can do? That counts."

**Celebration:**
> "You finished it! That's a win. Take a moment to feel good about it."
