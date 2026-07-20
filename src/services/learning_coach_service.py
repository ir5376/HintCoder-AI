from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Iterable

from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.models.learning import LearningEvent, LearningMemory, LearningTrendSnapshot, ReviewSchedule


@dataclass(frozen=True)
class CoachConfig:
    review_intervals_days: tuple[int, ...] = (1, 3, 7, 30)
    recent_window_limit: int = 20
    mastery_confidence_threshold: float = 0.75
    high_hint_dependency_threshold: float = 2.0
    long_solve_time_seconds: int = 45 * 60
    difficulty_order: tuple[str, ...] = ("Easy", "Medium", "Hard")
    default_roadmap_topics: tuple[str, ...] = ("Arrays", "Graphs", "Dynamic Programming", "Implementation")
    roadmap_lengths: dict[str, int] = field(
        default_factory=lambda: {
            "7-day": 7,
            "30-day": 30,
            "interview": 28,
            "contest": 14,
        }
    )


class LearningCoachService:
    """Builds Nextep's long-term learning coach memory from content-agnostic learning events."""

    def __init__(self, session: Session, config: CoachConfig | None = None) -> None:
        self.session = session
        self.config = config or CoachConfig()

    def record_solved_problem(self, payload: dict[str, Any]) -> dict[str, Any]:
        mode = self._normalize_mode(payload.get("mode"))
        content_module = self._normalize_content_module(payload.get("content_module"))
        hints_used = int(payload.get("hints_used", payload.get("hint_level_used", 0)) or 0)
        hint_level_used = int(payload.get("hint_level_used", hints_used) or 0)
        confidence = self._clamp_confidence(payload.get("confidence"))
        reflection = self._build_reflection(payload, hints_used=hints_used, hint_level_used=hint_level_used)
        exam_report = self._build_exam_report(payload, hints_used=hints_used, confidence=confidence) if mode == "exam" else {}
        event = LearningEvent(
            event_type=payload.get("event_type", "solved_problem"),
            mode=mode,
            content_module=content_module,
            content_id=self._clean(payload.get("content_id")) or self._clean(payload.get("problem_id")) or None,
            problem_id=payload.get("problem_id"),
            external_problem_title=payload.get("external_problem_title") or payload.get("problem_title"),
            external_problem_url=payload.get("external_problem_url") or payload.get("problem_url"),
            topic=payload.get("topic"),
            difficulty=payload.get("difficulty"),
            language=payload.get("language") or payload.get("programming_language"),
            algorithm_choice=payload.get("algorithm_choice"),
            solving_time_seconds=payload.get("solving_time_seconds"),
            confidence=confidence,
            hints_used=hints_used,
            hint_level_used=max(0, min(hint_level_used, 4)),
            thinking_progress=self._clamp_confidence(payload.get("thinking_progress")),
            solved=bool(payload.get("solved", True)),
            implementation_mistakes=self._json_list(payload.get("implementation_mistakes")),
            conceptual_mistakes=self._json_list(payload.get("conceptual_mistakes")),
            insights=self._json_list(payload.get("insights")),
            reflection_json=json.dumps(reflection, ensure_ascii=False),
            reasoning_notes=payload.get("reasoning_notes"),
            coach_action=payload.get("coach_action"),
            coach_question=payload.get("coach_question"),
            execution_trace_json=json.dumps(payload.get("execution_trace") or {}, ensure_ascii=False, default=str),
            provider=payload.get("provider"),
            provider_submission_id=payload.get("provider_submission_id"),
            exam_timer_seconds=payload.get("exam_timer_seconds"),
            exam_hints_available=payload.get("exam_hints_available"),
            exam_hint_penalty_enabled=payload.get("exam_hint_penalty_enabled"),
            exam_hint_penalty_points=payload.get("exam_hint_penalty_points"),
            exam_final_score=self._calculate_exam_score(payload, hints_used=hints_used) if mode == "exam" else None,
            exam_report_json=json.dumps(exam_report, ensure_ascii=False),
        )
        self.session.add(event)
        self.session.flush()

        if event.solved and event.mode == "learning":
            self._schedule_reviews(event)

        profile = self.get_profile()
        thought_profile = self.get_thought_profile()
        self._upsert_memory("profile", "coding_dna", profile)
        self._upsert_memory("profile", "thought_profile", thought_profile)
        self._upsert_memory("analytics", "hint_analytics", self.get_hint_analytics())
        self._upsert_memory("analytics", "learning_scores", self.get_learning_scores())
        self._store_trend_snapshot("event", {"profile": profile, "thought_profile": thought_profile})
        self.session.commit()

        return {
            "learning_event_id": event.id,
            "mode": event.mode,
            "content_module": event.content_module,
            "reflection": reflection,
            "exam_report": exam_report,
            "exam_final_score": event.exam_final_score,
            "coach_report": self.generate_adaptive_coach_report(),
            "scheduled_reviews": self.get_review_queue(status="pending"),
        }

    def get_dashboard(self) -> dict[str, Any]:
        profile = self.get_profile()
        thought_profile = self.get_thought_profile()
        reviews = self.get_review_queue(status="pending")
        return {
            "learning_mode_card": self._learning_mode_card(),
            "exam_mode_card": self._exam_mode_card(),
            "hint_analytics": self.get_hint_analytics(),
            "reflection_history": self.get_reflection_history(limit=10),
            "learning_scores": self.get_learning_scores(),
            "profile_summary": profile["summary"],
            "thought_summary": thought_profile["summary"],
            "adaptive_difficulty": self.get_adaptive_difficulty(),
            "next_reviews": reviews[:10],
            "today": self.generate_adaptive_coach_report(),
        }

    def get_profile(self) -> dict[str, Any]:
        events = self._learning_events()
        solved_events = [event for event in events if event.solved]
        algorithm_counts = Counter(self._clean(event.algorithm_choice) for event in events if self._clean(event.algorithm_choice))
        language_counts = Counter(self._clean(event.language) for event in events if self._clean(event.language))
        implementation_mistakes = Counter(
            mistake for event in events for mistake in self._loads_list(event.implementation_mistakes)
        )
        conceptual_mistakes = Counter(mistake for event in events for mistake in self._loads_list(event.conceptual_mistakes))
        topic_mastery = self._topic_mastery(events)
        avg_solve_time = self._average(event.solving_time_seconds for event in solved_events)
        avg_confidence = self._average(event.confidence for event in events)
        avg_hints = self._average(event.hints_used for event in events)

        summary = []
        if algorithm_counts:
            first, second = self._top_two(algorithm_counts)
            if first and second:
                summary.append(f"User prefers {first[0]} before {second[0]}.")
            elif first:
                summary.append(f"User often reaches for {first[0]}.")
        if implementation_mistakes:
            summary.append(f"User often repeats implementation mistake: {implementation_mistakes.most_common(1)[0][0]}.")
        if conceptual_mistakes:
            summary.append(f"User often repeats conceptual mistake: {conceptual_mistakes.most_common(1)[0][0]}.")
        strong_topics = [topic for topic, data in topic_mastery.items() if data["mastery"] >= self.config.mastery_confidence_threshold]
        if strong_topics:
            summary.append(f"User performs well in {strong_topics[0]} questions.")

        return {
            "summary": summary,
            "preferred_algorithm_choices": dict(algorithm_counts.most_common()),
            "average_solving_time_seconds": avg_solve_time,
            "average_confidence": avg_confidence,
            "hint_dependency": self._hint_dependency_label(avg_hints),
            "average_hints_used": avg_hints,
            "repeated_implementation_mistakes": dict(implementation_mistakes.most_common()),
            "repeated_conceptual_mistakes": dict(conceptual_mistakes.most_common()),
            "language_preference": language_counts.most_common(1)[0][0] if language_counts else None,
            "topic_mastery": topic_mastery,
            "historical_trends": self._trend_history(limit=10),
        }

    def get_thought_profile(self) -> dict[str, Any]:
        events = self._learning_events()
        recent = events[: self.config.recent_window_limit]
        algorithm_selection_speed = self._algorithm_selection_speed(recent)
        avg_hints = self._average(event.hints_used for event in recent)
        avg_confidence = self._average(event.confidence for event in recent)
        reasoning_mistakes = Counter(mistake for event in events for mistake in self._loads_list(event.conceptual_mistakes))
        debugging_behaviour = self._debugging_behaviour(recent)

        return {
            "summary": [
                f"Algorithm selection speed is {algorithm_selection_speed}.",
                f"Hint dependency is {self._hint_dependency_label(avg_hints)}.",
                f"Debugging behaviour is {debugging_behaviour}.",
            ],
            "algorithm_selection_speed": algorithm_selection_speed,
            "debugging_behaviour": debugging_behaviour,
            "hint_dependency": self._hint_dependency_label(avg_hints),
            "confidence": avg_confidence,
            "repeated_reasoning_mistakes": dict(reasoning_mistakes.most_common()),
        }

    def get_learning_memory(self) -> dict[str, Any]:
        events = self._learning_events()
        topics = Counter(self._clean(event.topic) for event in events if self._clean(event.topic))
        insights = [insight for event in events for insight in self._loads_list(event.insights)]
        difficulties = Counter(self._clean(event.difficulty) for event in events if self._clean(event.difficulty))
        profile = self.get_profile()
        return {
            "topics": dict(topics.most_common()),
            "mistakes": {
                "implementation": profile["repeated_implementation_mistakes"],
                "conceptual": profile["repeated_conceptual_mistakes"],
            },
            "insights": insights[-30:],
            "patterns": profile["summary"],
            "favorite_language": profile["language_preference"],
            "difficulty_progression": dict(difficulties.most_common()),
            "review_history": self.get_review_queue(status=None),
        }

    def get_hint_analytics(self) -> dict[str, Any]:
        events = self._learning_events()
        if not events:
            return {
                "average_hint_level": 0.0,
                "average_hints_per_topic": {},
                "hints_by_difficulty": {},
                "improvement_over_time": [],
                "coach_language": "Hints are available as learning tools whenever you need them.",
            }

        by_topic: dict[str, list[LearningEvent]] = defaultdict(list)
        by_difficulty: dict[str, list[LearningEvent]] = defaultdict(list)
        for event in events:
            by_topic[self._clean(event.topic) or "General"].append(event)
            by_difficulty[self._clean(event.difficulty) or "Unknown"].append(event)

        return {
            "average_hint_level": self._average(event.hint_level_used for event in events),
            "average_hints_per_topic": {
                topic: self._average(event.hints_used for event in topic_events)
                for topic, topic_events in sorted(by_topic.items())
            },
            "hints_by_difficulty": {
                difficulty: self._average(event.hints_used for event in difficulty_events)
                for difficulty, difficulty_events in sorted(by_difficulty.items())
            },
            "improvement_over_time": self._hint_improvement_over_time(events),
            "coach_language": self._hint_coach_language(events),
        }

    def get_reflection_history(self, limit: int = 20) -> list[dict[str, Any]]:
        events = [event for event in self._learning_events() if event.solved]
        reflections = []
        for event in events[:limit]:
            reflections.append(
                {
                    "learning_event_id": event.id,
                    "problem_title": event.external_problem_title,
                    "problem_url": event.external_problem_url,
                    "topic": event.topic,
                    "difficulty": event.difficulty,
                    "created_at": event.created_at.isoformat(),
                    "reflection": self._loads_dict(event.reflection_json),
                }
            )
        return reflections

    def get_learning_scores(self) -> dict[str, Any]:
        events = self._learning_events()[: self.config.recent_window_limit]
        if not events:
            return {
                "learning_score": 0,
                "thinking_score": 0,
                "independence_score": 0,
                "review_readiness": 0,
            }

        avg_confidence = self._average(event.confidence for event in events)
        avg_thinking = self._average(event.thinking_progress for event in events)
        avg_hints = self._average(event.hints_used for event in events)
        mistake_pressure = self._mistake_pressure(events)
        pending_reviews = len(self.get_review_queue(status="pending"))
        completed_reviews = len(self.get_review_queue(status="completed"))
        review_total = pending_reviews + completed_reviews
        review_completion = completed_reviews / review_total if review_total else 0.5

        thinking_score = self._score((avg_thinking or avg_confidence) - mistake_pressure)
        independence_score = self._score(1 - min(avg_hints / 4, 1) - (mistake_pressure / 2))
        review_readiness = self._score((avg_confidence * 0.5) + (review_completion * 0.5) - (mistake_pressure / 2))
        learning_score = self._score((thinking_score + independence_score + review_readiness) / 300)
        return {
            "learning_score": learning_score,
            "thinking_score": thinking_score,
            "independence_score": independence_score,
            "review_readiness": review_readiness,
        }

    def get_exam_summary(self) -> dict[str, Any]:
        exam_events = self._exam_events()
        return {
            "attempts": len(exam_events),
            "average_score": self._average(event.exam_final_score for event in exam_events),
            "average_time_seconds": self._average(event.solving_time_seconds for event in exam_events),
            "latest_exam_report": self._loads_dict(exam_events[0].exam_report_json) if exam_events else {},
        }

    def generate_adaptive_coach_report(self) -> dict[str, Any]:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_events = [event for event in self._learning_events() if event.created_at >= today_start]
        if not today_events:
            return {
                "today_strengths": [],
                "today_weaknesses": [],
                "topics_improving": [],
                "topics_declining": [],
                "tomorrow_focus": self._default_focus(),
            }

        return {
            "today_strengths": self._strengths(today_events),
            "today_weaknesses": self._weaknesses(today_events),
            "topics_improving": self._topic_direction(improving=True),
            "topics_declining": self._topic_direction(improving=False),
            "tomorrow_focus": self._tomorrow_focus(today_events),
        }

    def generate_weekly_reflection(self) -> dict[str, Any]:
        week_start = datetime.utcnow() - timedelta(days=7)
        week_events = [event for event in self._learning_events() if event.created_at >= week_start]
        topic_mastery = self._topic_mastery(week_events)
        weakest_topic = self._weakest_topic(topic_mastery)
        best_topic = self._best_topic(topic_mastery)
        reviews = self.get_review_queue(status=None)
        completed_reviews = [item for item in reviews if item["status"] == "completed"]
        return {
            "weekly_summary": self._weekly_summary(week_events),
            "best_improvement": best_topic,
            "weakest_topic": weakest_topic,
            "longest_streak": self._longest_daily_streak(week_events),
            "review_completion": {
                "completed": len(completed_reviews),
                "total": len(reviews),
                "rate": round(len(completed_reviews) / len(reviews), 2) if reviews else 0.0,
            },
            "suggested_roadmap": self.generate_roadmap("7-day"),
        }

    def generate_roadmap(self, roadmap_type: str = "7-day", content_module: str = "coding") -> dict[str, Any]:
        normalized_type = roadmap_type if roadmap_type in self.config.roadmap_lengths else "7-day"
        length = self.config.roadmap_lengths[normalized_type]
        normalized_module = self._normalize_content_module(content_module)
        focus_topics = self._roadmap_focus_topics(content_module=normalized_module)
        difficulty = self.get_adaptive_difficulty()["recommended_difficulty"]
        days = []
        for index in range(length):
            topic = focus_topics[index % len(focus_topics)]
            days.append(
                {
                    "day": index + 1,
                    "focus": topic,
                    "difficulty": difficulty,
                    "practice": self._roadmap_practice(normalized_type, topic),
                    "review": index in {0, 2, 6} or (normalized_type == "30-day" and index % 7 == 0),
                }
            )
        return {"type": normalized_type, "content_module": normalized_module, "days": days}

    def get_review_queue(self, status: str | None = "pending") -> list[dict[str, Any]]:
        query = self.session.query(ReviewSchedule)
        if status is not None:
            query = query.filter(ReviewSchedule.status == status)
        records = query.order_by(ReviewSchedule.scheduled_for.asc()).all()
        return [self._review_to_dict(record) for record in records]

    def complete_review(self, review_id: int, confidence: float | None = None) -> dict[str, Any] | None:
        review = self.session.query(ReviewSchedule).filter(ReviewSchedule.id == review_id).one_or_none()
        if review is None:
            return None
        review.status = "completed"
        review.completed_at = datetime.utcnow()
        if confidence is not None:
            review.confidence = self._clamp_confidence(confidence)
        self.session.commit()
        return self._review_to_dict(review)

    def get_adaptive_difficulty(self) -> dict[str, Any]:
        events = self._learning_events()[: self.config.recent_window_limit]
        if not events:
            return {"recommended_difficulty": self.config.difficulty_order[0], "reason": "No learning history yet."}

        solved_rate = sum(1 for event in events if event.solved) / len(events)
        avg_confidence = self._average(event.confidence for event in events)
        avg_hints = self._average(event.hints_used for event in events)
        current = self._most_common_difficulty(events)
        current_index = self.config.difficulty_order.index(current) if current in self.config.difficulty_order else 0

        if solved_rate >= 0.75 and avg_confidence >= self.config.mastery_confidence_threshold and avg_hints < 2:
            recommended_index = min(current_index + 1, len(self.config.difficulty_order) - 1)
            reason = "Mastery is improving with low hint dependency."
        elif solved_rate < 0.5 or avg_hints >= self.config.high_hint_dependency_threshold:
            recommended_index = max(current_index - 1, 0)
            reason = "Recent failures or hint dependency are high."
        else:
            recommended_index = current_index
            reason = "Current difficulty is appropriate."

        return {"recommended_difficulty": self.config.difficulty_order[recommended_index], "reason": reason}

    def _schedule_reviews(self, event: LearningEvent) -> None:
        now = datetime.utcnow()
        for interval in self.config.review_intervals_days:
            self.session.add(
                ReviewSchedule(
                    learning_event_id=event.id,
                    content_module=event.content_module,
                    content_id=event.content_id,
                    problem_id=event.problem_id,
                    external_problem_title=event.external_problem_title,
                    external_problem_url=event.external_problem_url,
                    topic=event.topic,
                    difficulty=event.difficulty,
                    confidence=event.confidence,
                    interval_days=interval,
                    scheduled_for=now + timedelta(days=interval),
                    status="pending",
                )
            )

    def _events(self) -> list[LearningEvent]:
        return self.session.query(LearningEvent).order_by(desc(LearningEvent.created_at), desc(LearningEvent.id)).all()

    def _learning_events(self) -> list[LearningEvent]:
        return [event for event in self._events() if self._normalize_mode(event.mode) == "learning"]

    def _exam_events(self) -> list[LearningEvent]:
        return [event for event in self._events() if self._normalize_mode(event.mode) == "exam"]

    def _learning_mode_card(self) -> dict[str, Any]:
        events = self._learning_events()
        return {
            "mode": "Learning Mode",
            "default": True,
            "message": "Hints are learning tools. XP is never reduced because of hint usage.",
            "solved_count": sum(1 for event in events if event.solved),
            "hint_dependency": self.get_profile()["hint_dependency"],
            "learning_scores": self.get_learning_scores(),
        }

    def _exam_mode_card(self) -> dict[str, Any]:
        summary = self.get_exam_summary()
        return {
            "mode": "Exam Mode",
            "default": False,
            "message": "Use timer, hint availability, optional hint score penalties, and final assessment reports.",
            **summary,
        }

    def _build_reflection(self, payload: dict[str, Any], *, hints_used: int, hint_level_used: int) -> dict[str, str]:
        trace_summary = self._execution_trace_summary(payload.get("execution_trace"))
        concept = self._first_item(payload.get("conceptual_mistakes")) or self._clean(payload.get("topic")) or "the core idea"
        implementation = self._first_item(payload.get("implementation_mistakes"))
        insight = self._first_item(payload.get("insights"))
        topic = self._clean(payload.get("topic")) or "this topic"
        if hints_used == 0:
            hint_reason = "You solved this without needing a hint."
        elif hint_level_used <= 1:
            hint_reason = "You used one strategic hint to confirm the key idea."
        else:
            hint_reason = f"You used hints up to level {hint_level_used} to move from idea selection into implementation."

        return {
            "why_did_you_need_the_hint": hint_reason,
            "what_concept_was_missing": concept,
            "what_should_you_remember": insight or implementation or trace_summary or f"Name the invariant or decision rule before coding {topic} problems.",
            "what_similar_problem_should_you_solve_next": f"Solve another {topic} problem with the first hint hidden for 10 minutes.",
        }

    def _execution_trace_summary(self, trace: Any) -> str:
        if not isinstance(trace, dict) or not trace:
            return ""
        if trace.get("status") == "error":
            return "Use the execution trace to identify the first failing line before changing the algorithm."
        step_count = len(trace.get("steps") or [])
        if step_count:
            return f"Review the {step_count} recorded execution step(s) and explain why each state change was expected."
        return ""

    def _build_exam_report(self, payload: dict[str, Any], *, hints_used: int, confidence: float | None) -> dict[str, Any]:
        score = self._calculate_exam_score(payload, hints_used=hints_used)
        confidence_text = "steady" if (confidence or 0) >= 0.7 else "uncertain"
        hints_available = bool(payload.get("exam_hints_available", True))
        return {
            "final_score": score,
            "confidence": confidence_text,
            "timer_seconds": payload.get("exam_timer_seconds"),
            "hints_available": hints_available,
            "hint_penalty_applied": bool(payload.get("exam_hint_penalty_enabled", False)) and hints_used > 0,
            "report": (
                "You completed a realistic assessment attempt. "
                f"Your confidence looked {confidence_text}, and your hint usage was {self._hint_dependency_label(hints_used)}."
            ),
        }

    def _calculate_exam_score(self, payload: dict[str, Any], *, hints_used: int) -> float:
        base_score = float(payload.get("exam_base_score", 100) or 100)
        if not bool(payload.get("solved", True)):
            base_score *= 0.5
        if bool(payload.get("exam_hint_penalty_enabled", False)):
            penalty = float(payload.get("exam_hint_penalty_points", 0) or 0) * hints_used
            base_score -= penalty
        return round(max(0.0, min(base_score, 100.0)), 2)

    def _hint_improvement_over_time(self, events: list[LearningEvent]) -> list[dict[str, Any]]:
        ordered = list(reversed(events))
        if len(ordered) < 2:
            return []
        midpoint = len(ordered) // 2
        early = ordered[:midpoint]
        recent = ordered[midpoint:]
        early_hints = self._average(event.hints_used for event in early)
        recent_hints = self._average(event.hints_used for event in recent)
        return [
            {
                "metric": "average_hints_used",
                "earlier": early_hints,
                "recent": recent_hints,
                "direction": "decreased" if recent_hints < early_hints else "increased" if recent_hints > early_hints else "stable",
            }
        ]

    def _hint_coach_language(self, events: list[LearningEvent]) -> str:
        recent = events[: self.config.recent_window_limit]
        avg_hints = self._average(event.hints_used for event in recent)
        trend = self._hint_improvement_over_time(events)
        declining_topics = self._topic_direction(improving=True)
        if avg_hints == 0:
            return "You are solving independently right now."
        if trend and trend[0]["direction"] == "decreased":
            return "You needed less help than before."
        if declining_topics:
            return f"Your dependence on hints for {declining_topics[0]} problems has decreased."
        if avg_hints <= 1:
            return "You solved recent problems with one strategic hint."
        return "Your hint use is giving us useful signals about what to review next."

    def _mistake_pressure(self, events: list[LearningEvent]) -> float:
        if not events:
            return 0.0
        mistake_count = sum(
            len(self._loads_list(event.implementation_mistakes)) + len(self._loads_list(event.conceptual_mistakes))
            for event in events
        )
        return min(mistake_count / (len(events) * 4), 1.0)

    def _score(self, value: float) -> int:
        return int(round(max(0.0, min(value, 1.0)) * 100))

    def _normalize_mode(self, value: Any) -> str:
        mode = self._clean(value).lower()
        return "exam" if mode == "exam" else "learning"

    def _normalize_content_module(self, value: Any) -> str:
        return self._clean(value).lower().replace(" ", "_") or "coding"

    def _first_item(self, value: Any) -> str:
        if isinstance(value, list) and value:
            return self._clean(value[0])
        if isinstance(value, tuple) and value:
            return self._clean(value[0])
        return self._clean(value)

    def _upsert_memory(self, memory_type: str, key: str, value: dict[str, Any]) -> None:
        record = (
            self.session.query(LearningMemory)
            .filter(LearningMemory.memory_type == memory_type, LearningMemory.key == key)
            .one_or_none()
        )
        payload = json.dumps(value, ensure_ascii=False, default=str)
        if record is None:
            self.session.add(LearningMemory(memory_type=memory_type, key=key, value_json=payload))
        else:
            record.value_json = payload

    def _store_trend_snapshot(self, period: str, summary: dict[str, Any]) -> None:
        self.session.add(
            LearningTrendSnapshot(
                period=period,
                summary_json=json.dumps(summary, ensure_ascii=False, default=str),
            )
        )

    def _trend_history(self, limit: int = 10) -> list[dict[str, Any]]:
        records = (
            self.session.query(LearningTrendSnapshot)
            .order_by(desc(LearningTrendSnapshot.created_at), desc(LearningTrendSnapshot.id))
            .limit(limit)
            .all()
        )
        return [
            {
                "period": record.period,
                "created_at": record.created_at.isoformat(),
                "summary": self._loads_dict(record.summary_json),
            }
            for record in records
        ]

    def _topic_mastery(self, events: list[LearningEvent]) -> dict[str, dict[str, Any]]:
        grouped: dict[str, list[LearningEvent]] = defaultdict(list)
        for event in events:
            grouped[self._clean(event.topic) or "General"].append(event)

        mastery = {}
        for topic, topic_events in grouped.items():
            solved_rate = sum(1 for event in topic_events if event.solved) / len(topic_events)
            avg_confidence = self._average(event.confidence for event in topic_events)
            avg_hints = self._average(event.hints_used for event in topic_events)
            mastery[topic] = {
                "attempts": len(topic_events),
                "solved_rate": round(solved_rate, 2),
                "average_confidence": avg_confidence,
                "average_hints_used": avg_hints,
                "mastery": round((solved_rate + avg_confidence + max(0.0, 1 - (avg_hints / 4))) / 3, 2),
            }
        return mastery

    def _strengths(self, events: list[LearningEvent]) -> list[str]:
        strengths = []
        for topic, data in self._topic_mastery(events).items():
            if data["mastery"] >= self.config.mastery_confidence_threshold:
                strengths.append(f"{topic}: strong solve rate and confidence")
        if not strengths and self._average(event.confidence for event in events) >= self.config.mastery_confidence_threshold:
            strengths.append("Confidence stayed strong today")
        return strengths

    def _weaknesses(self, events: list[LearningEvent]) -> list[str]:
        mistakes = Counter(mistake for event in events for mistake in self._loads_list(event.conceptual_mistakes))
        mistakes.update(mistake for event in events for mistake in self._loads_list(event.implementation_mistakes))
        weaknesses = [f"Repeated mistake: {name}" for name, _ in mistakes.most_common(3)]
        if self._average(event.hints_used for event in events) >= self.config.high_hint_dependency_threshold:
            weaknesses.append("Hint dependency was high today")
        return weaknesses

    def _topic_direction(self, *, improving: bool) -> list[str]:
        events = list(reversed(self._learning_events()))
        grouped: dict[str, list[LearningEvent]] = defaultdict(list)
        for event in events:
            grouped[self._clean(event.topic) or "General"].append(event)

        directions = []
        for topic, topic_events in grouped.items():
            if len(topic_events) < 4:
                continue
            midpoint = len(topic_events) // 2
            old_mastery = self._topic_mastery(topic_events[:midpoint])[topic]["mastery"]
            new_mastery = self._topic_mastery(topic_events[midpoint:])[topic]["mastery"]
            if improving and new_mastery > old_mastery:
                directions.append(topic)
            if not improving and new_mastery < old_mastery:
                directions.append(topic)
        return directions

    def _tomorrow_focus(self, events: list[LearningEvent]) -> list[str]:
        weaknesses = self._weaknesses(events)
        if weaknesses:
            return weaknesses[:3]
        return self._default_focus()

    def _default_focus(self) -> list[str]:
        memory = self.get_profile()
        mistakes = list(memory["repeated_conceptual_mistakes"].keys()) + list(memory["repeated_implementation_mistakes"].keys())
        return mistakes[:3] or ["Solve one problem, write the invariant, then review the first hint only if stuck."]

    def _weekly_summary(self, events: list[LearningEvent]) -> str:
        solved = sum(1 for event in events if event.solved)
        hints = self._average(event.hints_used for event in events)
        confidence = self._average(event.confidence for event in events)
        return f"Solved {solved} problem(s), averaging {hints} hints and {confidence} confidence."

    def _roadmap_focus_topics(self, *, content_module: str = "coding") -> list[str]:
        profile = self.get_profile()
        declining = self._topic_direction(improving=False)
        weak_topics = [
            topic
            for topic, data in sorted(profile["topic_mastery"].items(), key=lambda item: item[1]["mastery"])
            if topic
        ]
        defaults = list(self.config.default_roadmap_topics)
        if content_module != "coding":
            defaults = ["Foundation", "Core Concepts", "Practice", "Review"]
        return declining + weak_topics + defaults

    def _roadmap_practice(self, roadmap_type: str, topic: str) -> str:
        if roadmap_type == "contest":
            return f"Timed practice on {topic}, then post-solve error review."
        if roadmap_type == "interview":
            return f"Explain {topic} aloud, solve, and write complexity before coding."
        return f"Practice {topic} and log mistakes, confidence, and hints used."

    def _algorithm_selection_speed(self, events: list[LearningEvent]) -> str:
        avg_time = self._average(event.solving_time_seconds for event in events)
        if avg_time == 0:
            return "unknown"
        if avg_time <= self.config.long_solve_time_seconds / 2:
            return "fast"
        if avg_time <= self.config.long_solve_time_seconds:
            return "steady"
        return "slow"

    def _debugging_behaviour(self, events: list[LearningEvent]) -> str:
        mistake_count = sum(
            len(self._loads_list(event.implementation_mistakes)) + len(self._loads_list(event.conceptual_mistakes))
            for event in events
        )
        avg_hints = self._average(event.hints_used for event in events)
        if mistake_count == 0 and avg_hints < 1:
            return "independent"
        if avg_hints >= self.config.high_hint_dependency_threshold:
            return "hint-led"
        return "iterative"

    def _weakest_topic(self, mastery: dict[str, dict[str, Any]]) -> str | None:
        if not mastery:
            return None
        return min(mastery.items(), key=lambda item: item[1]["mastery"])[0]

    def _best_topic(self, mastery: dict[str, dict[str, Any]]) -> str | None:
        if not mastery:
            return None
        return max(mastery.items(), key=lambda item: item[1]["mastery"])[0]

    def _longest_daily_streak(self, events: list[LearningEvent]) -> int:
        days = sorted({event.created_at.date() for event in events if event.solved})
        if not days:
            return 0
        longest = current = 1
        for previous, current_day in zip(days, days[1:]):
            if current_day == previous + timedelta(days=1):
                current += 1
            else:
                current = 1
            longest = max(longest, current)
        return longest

    def _most_common_difficulty(self, events: list[LearningEvent]) -> str:
        counts = Counter(self._clean(event.difficulty) for event in events if self._clean(event.difficulty))
        if not counts:
            return self.config.difficulty_order[0]
        return counts.most_common(1)[0][0]

    def _review_to_dict(self, record: ReviewSchedule) -> dict[str, Any]:
        return {
            "id": record.id,
            "learning_event_id": record.learning_event_id,
            "content_module": record.content_module,
            "content_id": record.content_id,
            "problem_id": record.problem_id,
            "external_problem_title": record.external_problem_title,
            "external_problem_url": record.external_problem_url,
            "topic": record.topic,
            "difficulty": record.difficulty,
            "confidence": record.confidence,
            "interval_days": record.interval_days,
            "scheduled_for": record.scheduled_for.isoformat(),
            "status": record.status,
            "completed_at": record.completed_at.isoformat() if record.completed_at else None,
        }

    def _hint_dependency_label(self, average_hints: float) -> str:
        if average_hints == 0:
            return "independent"
        if average_hints < self.config.high_hint_dependency_threshold:
            return "balanced"
        return "high"

    def _average(self, values: Iterable[int | float | None]) -> float:
        clean_values = [float(value) for value in values if value is not None]
        if not clean_values:
            return 0.0
        return round(sum(clean_values) / len(clean_values), 2)

    def _clamp_confidence(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return max(0.0, min(float(value), 1.0))
        except (TypeError, ValueError):
            return None

    def _json_list(self, value: Any) -> str:
        if value is None:
            return "[]"
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            value = list(value) if isinstance(value, tuple) else [value]
        return json.dumps([str(item) for item in value if str(item).strip()], ensure_ascii=False)

    def _loads_list(self, value: str | None) -> list[str]:
        if not value:
            return []
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return []
        return [str(item) for item in loaded] if isinstance(loaded, list) else []

    def _loads_dict(self, value: str | None) -> dict[str, Any]:
        if not value:
            return {}
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return loaded if isinstance(loaded, dict) else {}

    def _clean(self, value: Any) -> str:
        return str(value).strip() if value is not None and str(value).strip() else ""

    def _top_two(self, counts: Counter) -> tuple[tuple[str, int] | None, tuple[str, int] | None]:
        common = counts.most_common(2)
        first = common[0] if common else None
        second = common[1] if len(common) > 1 else None
        return first, second
