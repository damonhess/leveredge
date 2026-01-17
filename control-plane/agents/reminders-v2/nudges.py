#!/usr/bin/env python3
"""
Contextual Nudge Generator for REMINDERS-V2

Generates context-aware, ADHD-friendly nudges and motivational messages:
- Time-of-day appropriate messaging
- Task-context aware nudges
- Focus/energy level responses
- Motivational check-ins
- Break reminders
"""

import random
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass

# Import patterns if available
try:
    from patterns import UserPatterns
except ImportError:
    UserPatterns = None


class NudgeType(str, Enum):
    FOCUS_CHECK = "focus_check"
    BREAK_REMINDER = "break_reminder"
    MOTIVATION = "motivation"
    TASK_NUDGE = "task_nudge"
    ENERGY_CHECK = "energy_check"
    CELEBRATION = "celebration"
    GENTLE_REDIRECT = "gentle_redirect"
    HYDRATION = "hydration"
    MOVEMENT = "movement"
    PROGRESS = "progress"
    ADHD_SUPPORT = "adhd_support"


@dataclass
class NudgeContext:
    """Context for generating appropriate nudges"""
    time_of_day: str  # morning, afternoon, evening, night
    energy_level: Optional[str] = None  # low, medium, high
    focus_score: Optional[int] = None  # 1-10
    current_task: Optional[str] = None
    tasks_completed_today: int = 0
    hours_worked: float = 0
    last_break: Optional[datetime] = None
    mood: Optional[str] = None


class NudgeGenerator:
    """
    Generates contextual nudges and motivational messages.

    Designed with ADHD-friendly principles:
    - Short, clear messages
    - Positive, non-judgmental tone
    - Action-oriented suggestions
    - Acknowledgment of struggles
    - Celebration of small wins
    """

    def __init__(self):
        self._init_message_templates()

    def _init_message_templates(self):
        """Initialize message templates organized by type and context"""

        # Morning greetings and motivations
        self.morning_greetings = [
            "Good morning! Ready to tackle today? What's your first small win going to be?",
            "Rise and shine! Remember: one task at a time. You've got this.",
            "Morning! Today is a fresh start. What one thing will move you forward?",
            "Good morning! Your brain is fresh - perfect time for that challenging task.",
            "Hey there! Coffee + one focused task = winning morning.",
        ]

        # Afternoon check-ins
        self.afternoon_checkins = [
            "Afternoon check-in! How's your energy? Maybe time for a quick reset?",
            "Halfway through the day! Take a breath. What's next on your list?",
            "Post-lunch slump is normal. A quick walk or stretch can help!",
            "Afternoon vibes! Have you had water recently? Hydration helps focus.",
            "Quick pulse check: Still on track? Or time to adjust priorities?",
        ]

        # Evening wind-downs
        self.evening_messages = [
            "Evening reflection time. What did you accomplish today? Celebrate it!",
            "Winding down? Great time to prep tomorrow's top 3 priorities.",
            "Evening check: Ready to close out work mode? You've earned rest.",
            "Day's wrapping up. What's one thing you're proud of from today?",
            "Evening reminder: Rest is productive too. You did great today.",
        ]

        # Focus check nudges
        self.focus_checks = [
            "Quick focus check: Still on task? If you drifted, that's okay - just gently redirect.",
            "Hey! How's that focus going? Remember: progress over perfection.",
            "Focus pulse: Are you working on what matters most right now?",
            "Gentle nudge: If you're stuck, try the 2-minute rule. What's the tiniest next step?",
            "Focus check-in! If your mind wandered, no judgment - just come back.",
        ]

        # Break reminders
        self.break_reminders = [
            "Time for a break! Your brain needs rest to work well. Step away for a few minutes.",
            "Break time! Stand up, stretch, look at something far away. Your focus will thank you.",
            "Hey, you've been at it a while. A short break actually boosts productivity!",
            "Pause reminder: Get some water, stretch, breathe. You're doing great.",
            "Break check: When did you last move? A 5-min walk works wonders.",
        ]

        # Motivational messages (ADHD-specific)
        self.adhd_motivations = [
            "Remember: ADHD brains are creative powerhouses. Work with your brain, not against it.",
            "Feeling scattered? That's okay. Pick ONE thing. Just one. You can do one thing.",
            "Your brain works differently, not worse. Trust your unique process.",
            "Hyperfocus is a superpower when aimed right. What deserves that energy today?",
            "Overwhelmed? Break it down smaller. Then smaller again. Now do just that first bit.",
            "Progress isn't linear, and that's fine. Every step forward counts.",
            "Waiting mode got you stuck? Set a timer for 5 mins and just start. Momentum will follow.",
            "Your worth isn't measured by productivity. But also: you're more capable than you know.",
            "Task switching feeling hard? That's the ADHD tax. Be patient with yourself.",
            "Remember: done is better than perfect. Ship it, fix it later.",
        ]

        # Low energy responses
        self.low_energy_responses = [
            "Low energy is valid. What's ONE small thing you can do? That counts.",
            "Energy dip? Try: water, snack, 5-minute walk, then reassess.",
            "Tired is okay. Maybe this is a 'light tasks only' moment?",
            "Low fuel day? Focus on maintenance tasks. Save the big stuff for peak hours.",
            "Energy flagging? Your body might need food, water, or a quick rest.",
        ]

        # High energy / focus responses
        self.high_energy_responses = [
            "Riding a wave of focus? Amazing! What's the most important thing to tackle?",
            "High energy detected! This is prime time for challenging tasks.",
            "You're in the zone! Protect this time - it's golden.",
            "Focus mode activated! Remember to hydrate but keep that momentum.",
            "Peak performance time! What will you accomplish in this power hour?",
        ]

        # Task completion celebrations
        self.celebrations = [
            "You finished it! That's a win. Take a moment to feel good about it.",
            "Task complete! See? You can do hard things.",
            "Done! Check that off. Every completed task builds momentum.",
            "Nice work! That task is behind you now. What's next?",
            "Completed! Your future self thanks you for that.",
        ]

        # Gentle redirects (for when distracted)
        self.gentle_redirects = [
            "Hey, no judgment, but: is this what you meant to be doing right now?",
            "Gentle reality check: Current activity aligned with goals?",
            "Quick question: Is this task, or is this avoidance? (Both are valid, just check in.)",
            "Distraction happens. Notice it, acknowledge it, then choose what's next.",
            "Plot twist: You don't have to finish the distraction. You can just... go back.",
        ]

        # Context-specific nudges
        self.context_nudges = {
            "coding": [
                "Coding tip: If stuck for 15+ mins, explain the problem out loud (rubber duck!)",
                "Code break: Stand up, reset, then come back with fresh eyes.",
                "Debugging? The answer often comes after stepping away. Trust the process.",
            ],
            "writing": [
                "Writer's block? Just write badly first. Edit later. Get words down.",
                "Writing tip: Set a timer for 10 mins of pure flow. No editing allowed.",
                "Stuck on words? Talk it out first, then transcribe your thoughts.",
            ],
            "meeting": [
                "Meeting coming up! Take 2 minutes to prep your key points.",
                "Post-meeting: Capture actions while fresh. 2 minutes now saves 20 later.",
                "Meetings done? Reset with a quick break before diving into focus work.",
            ],
            "admin": [
                "Admin tasks dragging? Try the 2-minute rule: if it takes less, do it now.",
                "Batch similar admin tasks. Your brain will thank you for the efficiency.",
                "Admin mode: Set a timer and power through. Then reward yourself.",
            ],
            "creative": [
                "Creative work? Let yourself explore. Constraints come later.",
                "Creativity tip: Change your environment for fresh inspiration.",
                "Stuck creatively? Feed your brain: take a walk, read something, look at art.",
            ],
        }

        # Hydration and movement reminders
        self.hydration_reminders = [
            "Water check! Your brain is 80% water - keep it hydrated.",
            "Quick H2O reminder. Dehydration = brain fog. Take a sip!",
            "Hydration station! When did you last drink water?",
        ]

        self.movement_reminders = [
            "Movement break! A quick stretch goes a long way.",
            "Body check: How long since you moved? Even a 1-min stretch helps.",
            "Stand, stretch, shake it out. Movement = better thinking.",
        ]

    def get_nudge_by_type(
        self,
        nudge_type: NudgeType,
        patterns: Optional[Any] = None,  # UserPatterns
        context: Optional[NudgeContext] = None
    ) -> str:
        """Get a specific type of nudge"""

        if nudge_type == NudgeType.FOCUS_CHECK:
            return random.choice(self.focus_checks)
        elif nudge_type == NudgeType.BREAK_REMINDER:
            return random.choice(self.break_reminders)
        elif nudge_type == NudgeType.MOTIVATION:
            return random.choice(self.adhd_motivations)
        elif nudge_type == NudgeType.ENERGY_CHECK:
            if context and context.energy_level == "low":
                return random.choice(self.low_energy_responses)
            elif context and context.energy_level == "high":
                return random.choice(self.high_energy_responses)
            return random.choice(self.focus_checks)
        elif nudge_type == NudgeType.CELEBRATION:
            return random.choice(self.celebrations)
        elif nudge_type == NudgeType.GENTLE_REDIRECT:
            return random.choice(self.gentle_redirects)
        elif nudge_type == NudgeType.HYDRATION:
            return random.choice(self.hydration_reminders)
        elif nudge_type == NudgeType.MOVEMENT:
            return random.choice(self.movement_reminders)
        elif nudge_type == NudgeType.ADHD_SUPPORT:
            return random.choice(self.adhd_motivations)
        else:
            return random.choice(self.focus_checks)

    def get_contextual_nudge(
        self,
        context: Optional[str] = None,
        time_of_day: str = "afternoon",
        patterns: Optional[Any] = None
    ) -> str:
        """Generate a context-aware nudge"""

        # Try to match specific context
        if context:
            context_lower = context.lower()
            for ctx_key, messages in self.context_nudges.items():
                if ctx_key in context_lower:
                    return random.choice(messages)

        # Fall back to time-based nudge
        return self._get_time_based_nudge(time_of_day)

    def _get_time_based_nudge(self, time_of_day: str) -> str:
        """Get nudge appropriate for time of day"""
        if time_of_day == "morning":
            return random.choice(self.morning_greetings)
        elif time_of_day == "afternoon":
            return random.choice(self.afternoon_checkins)
        elif time_of_day == "evening":
            return random.choice(self.evening_messages)
        else:
            return random.choice(self.adhd_motivations)

    def get_adhd_checkin(
        self,
        time_of_day: str = "afternoon",
        patterns: Optional[Any] = None
    ) -> str:
        """Generate an ADHD-friendly check-in message"""

        # Mix of focus check and motivation
        options = [
            *self.focus_checks,
            *self.adhd_motivations[:3],
        ]

        # Add time-appropriate elements
        if time_of_day == "morning":
            options.extend(self.morning_greetings[:2])
        elif time_of_day == "afternoon":
            options.extend(self.afternoon_checkins[:2])
        elif time_of_day == "evening":
            options.extend(self.evening_messages[:2])

        return random.choice(options)

    def get_adhd_motivation(
        self,
        time_of_day: str = "afternoon",
        task_count: int = 0,
        patterns: Optional[Any] = None
    ) -> str:
        """Get motivational message tailored for ADHD"""

        base = random.choice(self.adhd_motivations)

        # Add context about task count
        if task_count > 10:
            base += " Remember: you don't have to do everything today. Pick your top 3."
        elif task_count > 5:
            base += " You've got a manageable load. One at a time!"
        elif task_count > 0:
            base += " Nice, focused list! You can totally handle this."
        else:
            base += " Clean slate today - what one thing will you start?"

        return base

    def get_checkin_response(
        self,
        mood: Optional[int] = None,
        focus: Optional[int] = None,
        energy: Optional[str] = None,
        current_task: Optional[str] = None,
        blockers: Optional[str] = None
    ) -> str:
        """Generate response to a check-in based on reported state"""

        responses = []

        # Mood response
        if mood is not None:
            if mood <= 3:
                responses.append("Thanks for sharing how you're feeling. It's okay to have tough days.")
            elif mood <= 6:
                responses.append("Middle-of-the-road mood - that's workable.")
            else:
                responses.append("Great mood! That's awesome to hear.")

        # Energy response
        if energy:
            if energy == "low":
                responses.append(random.choice(self.low_energy_responses))
            elif energy == "high":
                responses.append(random.choice(self.high_energy_responses))

        # Focus response
        if focus is not None:
            if focus <= 3:
                responses.append("Focus feeling scattered? That's okay. Try one small, concrete task to build momentum.")
            elif focus >= 8:
                responses.append("Strong focus! Protect this time - it's valuable.")

        # Blocker response
        if blockers:
            responses.append(f"Noted blocker: '{blockers[:50]}...' - Sometimes naming it helps. What's one tiny step around it?")

        # Task context
        if current_task:
            responses.append(f"Working on '{current_task[:30]}' - you've got this!")

        if not responses:
            responses.append("Thanks for checking in! Every moment of awareness counts.")

        return " ".join(responses[:2])  # Limit response length

    def get_focus_suggestions(
        self,
        focus_score: Optional[int] = None,
        energy_level: Optional[str] = None
    ) -> List[str]:
        """Get actionable focus improvement suggestions"""

        suggestions = []

        if focus_score is not None and focus_score <= 5:
            suggestions.extend([
                "Try the Pomodoro technique: 25 mins work, 5 mins break",
                "Remove distractions: phone away, close extra tabs",
                "Write down your ONE current task and put it visible",
                "Change your environment - sometimes a new spot helps",
                "Put on focus music or white noise",
            ])

        if energy_level == "low":
            suggestions.extend([
                "Take a 10-15 minute power nap if possible",
                "Go for a quick 5-minute walk outside",
                "Have a healthy snack - protein helps",
                "Drink a glass of water",
                "Do some light stretching",
            ])
        elif energy_level == "high":
            suggestions.extend([
                "Tackle your hardest task right now",
                "Set an ambitious timer and race it",
                "Batch similar tasks together",
                "Use this energy for creative/complex work",
            ])

        if not suggestions:
            suggestions = [
                "Start with a 2-minute task to build momentum",
                "Write down your top 3 priorities",
                "Take a 5-minute movement break",
            ]

        return suggestions[:5]

    def get_deadline_nudge(
        self,
        task_title: str,
        hours_remaining: float,
        priority: str = "normal"
    ) -> str:
        """Generate appropriate nudge for approaching deadline"""

        if hours_remaining <= 0:
            return f"OVERDUE: '{task_title}' needs attention! What's stopping you? Let's problem-solve."
        elif hours_remaining <= 1:
            return f"URGENT: '{task_title}' is due in under an hour! Time to focus and finish."
        elif hours_remaining <= 4:
            return f"Heads up: '{task_title}' is due soon ({hours_remaining:.1f} hours). Time to prioritize it."
        elif hours_remaining <= 24:
            return f"Reminder: '{task_title}' is due within 24 hours. Plan when you'll tackle it."
        else:
            days = hours_remaining / 24
            return f"Future deadline: '{task_title}' in {days:.1f} days. Consider starting early!"

    def get_break_suggestion(self, break_type: str = "short") -> str:
        """Get specific break activity suggestion"""

        short_breaks = [
            "Stand up and stretch for 2 minutes",
            "Look at something 20 feet away for 20 seconds (eye break)",
            "Take 5 deep breaths",
            "Drink some water",
            "Step outside for fresh air",
            "Do 10 jumping jacks",
            "Walk to another room and back",
        ]

        long_breaks = [
            "Take a 15-minute walk outside",
            "Have a healthy snack",
            "Do a 10-minute meditation",
            "Call a friend or family member",
            "Listen to a favorite song",
            "Read something non-work related",
            "Do some light exercise",
        ]

        if break_type == "short":
            return f"Break suggestion: {random.choice(short_breaks)}"
        else:
            return f"Break suggestion: {random.choice(long_breaks)}"

    def get_progress_celebration(self, tasks_completed: int, streak_days: int = 0) -> str:
        """Generate celebration for progress"""

        if tasks_completed == 1:
            msg = "First task of the day done! Momentum started."
        elif tasks_completed <= 3:
            msg = f"{tasks_completed} tasks done! You're building momentum."
        elif tasks_completed <= 5:
            msg = f"{tasks_completed} tasks completed! You're on fire today!"
        else:
            msg = f"WOW - {tasks_completed} tasks done! Incredible productivity!"

        if streak_days > 0:
            msg += f" That's {streak_days} days in a row. Keep the streak alive!"

        return msg
