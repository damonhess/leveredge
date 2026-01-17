# ARIA Telegram Bot Commands

Complete documentation for all bot commands and their usage.

---

## Quick Reference

| Command | Description | Example |
|---------|-------------|---------|
| `/status` | System and ARIA status | `/status` |
| `/tasks` | View and manage tasks | `/tasks`, `/tasks add Buy groceries` |
| `/remind` | Set a reminder | `/remind 30m Call John` |
| `/workout` | Workout management | `/workout`, `/workout log pushups 50` |
| `/meals` | Meal planning and logging | `/meals`, `/meals log lunch salad` |
| `/help` | Show available commands | `/help` |

---

## Detailed Command Documentation

### /status

Check the current status of ARIA and connected systems.

**Usage:**
```
/status
```

**Response includes:**
- ARIA availability
- Active workflows status
- Last sync time
- Current context summary
- Any pending tasks or reminders

**Example Response:**
```
ARIA Status Report

System: Online
Last Activity: 2 minutes ago
Active Sessions: 1

Today's Summary:
- Tasks completed: 3/7
- Workout: Completed (Push day)
- Meals logged: 2/3
- Reminders pending: 1

Current Focus: Deep work block until 2pm
```

---

### /tasks

View, add, and manage your tasks.

**Usage:**
```
/tasks                          # List today's tasks
/tasks all                      # List all active tasks
/tasks add <description>        # Add a new task
/tasks done <task_id>           # Mark task as complete
/tasks priority <id> <1-5>      # Set task priority
```

**Examples:**
```
/tasks
/tasks add Buy groceries for dinner
/tasks add Call dentist priority:high due:tomorrow
/tasks done 123
/tasks priority 123 1
```

**Response Format:**
```
Today's Tasks (3 pending, 2 complete)

High Priority:
[ ] Finish project proposal (due today)

Normal Priority:
[ ] Review emails
[ ] Call John back

Completed:
[x] Morning workout
[x] Team standup

Quick add: /tasks add <description>
```

**Natural Language Support:**
You can also just send a message like:
- "Add task: buy milk"
- "I need to remember to call the doctor"
- "Remind me to submit the report tomorrow"

ARIA will automatically create tasks from natural language.

---

### /remind

Set reminders for future times.

**Usage:**
```
/remind <time> <message>
```

**Time Formats:**
- `10m`, `30m`, `1h`, `2h` - Minutes/hours from now
- `tomorrow` - Tomorrow at 9am
- `tomorrow 3pm` - Specific time tomorrow
- `monday` - Next Monday at 9am
- `monday 2pm` - Next Monday at 2pm
- `2024-01-15 14:00` - Specific date and time

**Examples:**
```
/remind 30m Check oven
/remind 1h Call John back
/remind tomorrow Review project status
/remind monday 9am Team meeting prep
/remind 2h Take break and stretch
```

**Response:**
```
Reminder set!

When: In 30 minutes (2:30 PM)
Message: Check oven

I'll notify you here on Telegram.
```

**Reminder Delivery:**
- Reminders are delivered via Telegram message
- If you miss a reminder, it will be marked as "pending"
- Use `/remind list` to see pending reminders

---

### /workout

Manage workouts, view routines, and log exercise.

**Usage:**
```
/workout                        # Today's workout
/workout today                  # Same as above
/workout log <exercise> <reps>  # Log an exercise
/workout complete               # Mark workout as done
/workout skip                   # Skip today's workout
/workout history                # View recent workouts
```

**Examples:**
```
/workout
/workout log pushups 50
/workout log bench press 135lbs 3x8
/workout log running 5km 28min
/workout complete
```

**Response Format:**
```
Today's Workout: Push Day (Chest/Shoulders/Triceps)

Exercises:
1. Bench Press - 4x8 @ 135lbs
2. Overhead Press - 3x10 @ 75lbs
3. Incline Dumbbell Press - 3x12 @ 40lbs
4. Lateral Raises - 3x15 @ 20lbs
5. Tricep Pushdowns - 3x12 @ 50lbs
6. Dips - 3x10 bodyweight

Duration: ~45 min
Rest: 90 sec between sets

Log progress: /workout log <exercise> <weight> <sets>x<reps>
```

**Logging Exercises:**

The bot understands various formats:
- `/workout log pushups 50` - 50 total reps
- `/workout log bench 135 3x8` - 3 sets of 8 at 135lbs
- `/workout log squat 225lbs 5x5` - 5 sets of 5 at 225lbs
- `/workout log running 5k` - 5km run
- `/workout log walking 30min` - 30 minute walk

**Voice Logging:**
You can also send a voice message like:
"I just did 50 pushups and 30 situps"

ARIA will parse and log the exercises automatically.

---

### /meals

Meal planning, suggestions, and food logging.

**Usage:**
```
/meals                          # Today's meal plan
/meals suggest <meal>           # Get meal suggestions
/meals log <meal> <description> # Log a meal
/meals macros                   # View today's macros
/meals history                  # Recent meal history
```

**Examples:**
```
/meals
/meals suggest breakfast
/meals suggest high protein lunch
/meals log breakfast oatmeal with berries and protein shake
/meals log lunch chicken salad 500cal
/meals macros
```

**Response Format:**
```
Today's Meal Plan

Based on your goals (lean bulk, 2800 cal):

Breakfast (7am): [Not logged]
- Suggested: Oatmeal with protein, banana, almonds
- ~600 cal | 35g protein | 75g carbs | 20g fat

Lunch (12pm): [Logged: Chicken salad]
- 500 cal | 40g protein | 25g carbs | 25g fat

Dinner (6pm): [Not logged]
- Suggested: Salmon, rice, vegetables
- ~700 cal | 45g protein | 60g carbs | 25g fat

Snacks: [Not logged]
- Suggested: Greek yogurt, protein bar
- ~400 cal | 30g protein | 35g carbs | 12g fat

Daily Progress:
Calories: 500/2800 (18%)
Protein: 40/180g (22%)

Log: /meals log <meal> <description>
```

**Photo Logging:**
Send a photo of your meal with a caption, and ARIA will:
1. Analyze the image to identify foods
2. Estimate portions and calories
3. Log the meal with nutritional information

**Voice Logging:**
Send a voice message describing your meal:
"I just had a chicken breast with rice and broccoli for lunch"

---

### /help

Display available commands and quick usage guide.

**Usage:**
```
/help                           # General help
/help <command>                 # Help for specific command
```

**Examples:**
```
/help
/help remind
/help workout
```

**Response:**
```
ARIA Telegram Bot - Help

Commands:
/status - Check system status
/tasks - Manage your tasks
/remind <time> <msg> - Set a reminder
/workout - Today's workout & logging
/meals - Meal planning & logging
/help - This help message

Tips:
- Send any text and I'll respond as ARIA
- Send voice messages for hands-free interaction
- Send photos of meals for automatic logging
- Use natural language for tasks/reminders

Examples:
"What's on my schedule today?"
"Add a task to call mom"
"I just finished my workout"
"What should I eat for dinner?"

Full docs: /help <command>
```

---

## Natural Language Interactions

Beyond commands, you can interact naturally with ARIA:

### Task Management
- "I need to remember to buy groceries"
- "Add to my todo: finish the report"
- "What tasks do I have today?"
- "Mark the grocery task as done"

### Reminders
- "Remind me in 30 minutes to take a break"
- "Set a reminder for tomorrow at 9am: team meeting"
- "Don't let me forget to call John at 3pm"

### Workouts
- "What's my workout for today?"
- "I just did 50 pushups"
- "Log my morning run: 5k in 25 minutes"
- "Skip today's workout, I'm not feeling well"

### Meals
- "What should I eat for dinner?"
- "I had a chicken salad for lunch"
- "Give me a high protein breakfast idea"
- "How many calories have I eaten today?"

### General
- "How am I doing on my goals?"
- "What's my energy level tracking?"
- "Give me a quick motivation boost"
- "What should I focus on right now?"

---

## Voice Message Guidelines

When sending voice messages:

1. **Speak clearly** - Enunciate, especially for numbers and names
2. **Keep it concise** - Under 30 seconds works best
3. **State intent** - "Log my workout..." or "Remind me to..."
4. **Confirm response** - ARIA will confirm what it understood

**Voice Processing:**
- Messages are transcribed using OpenAI Whisper
- Transcription is then processed as text
- Response is sent as text (voice response coming soon)

---

## Image Message Guidelines

When sending images:

1. **Meals** - Send photos of food for automatic logging
2. **Receipts** - Send receipts for expense tracking (coming soon)
3. **Screenshots** - Send screenshots for context
4. **Whiteboard** - Capture notes or diagrams

**Image Processing:**
- Images are analyzed using GPT-4 Vision
- Food photos are identified and calories estimated
- Context is added to the conversation

**Best Practices:**
- Good lighting helps accuracy
- Center the main subject
- Add a caption for context

---

## Error Messages

| Message | Meaning | Solution |
|---------|---------|----------|
| "Unauthorized" | Your account isn't authorized | Contact admin to authorize |
| "Rate limited" | Too many messages | Wait a minute and try again |
| "Processing error" | ARIA had trouble | Try rephrasing or use a command |
| "Voice error" | Couldn't transcribe | Speak clearer, check audio quality |
| "Image error" | Couldn't analyze image | Try a clearer image |

---

## Tips and Tricks

1. **Quick logging**: Just send "50 pushups" and ARIA will log it
2. **Batch tasks**: "Add tasks: buy milk, call John, finish report"
3. **Context**: ARIA remembers your conversation context
4. **Preferences**: Tell ARIA your preferences and they'll be remembered
5. **Shortcuts**: Start messages with "!" for quick commands

---

## Privacy Notes

- All messages are processed through ARIA and logged
- Voice messages are transcribed via OpenAI Whisper
- Images are analyzed via OpenAI Vision
- Data is stored in your LeverEdge database
- No data is shared with third parties beyond processing
