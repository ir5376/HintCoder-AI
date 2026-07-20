"""Session-backed MVP UI for profiles and learner dashboard views."""

from __future__ import annotations

import calendar
from datetime import date
from html import escape

import streamlit as st


def render_profile_selector() -> None:
    profiles = list(st.session_state.get("profiles", []))
    if profiles:
        labels = {profile["id"]: profile["display_name"] for profile in profiles}
        selected = st.selectbox("Active profile", list(labels), format_func=labels.get, key="profile_selector")
        st.session_state["active_profile_id"] = selected
        st.caption(f"Active profile: {labels[selected]}")
    else:
        st.caption("No active profile")
    with st.expander("Create profile"):
        name = st.text_input("Display name", key="new_profile_name", placeholder="e.g. Alex")
        if st.button("Create profile", key="create_profile"):
            if not name.strip():
                st.warning("Enter a display name.")
            else:
                profile = {"id": f"profile-{len(profiles) + 1}", "display_name": name.strip()}
                st.session_state["profiles"] = [*profiles, profile]
                st.session_state["active_profile_id"] = profile["id"]
                st.rerun()


def _active_profile() -> dict | None:
    return next((item for item in st.session_state.get("profiles", []) if item["id"] == st.session_state.get("active_profile_id")), None)


def _metrics() -> dict | None:
    payload = st.session_state.get("learner_metrics")
    return payload if isinstance(payload, dict) else None


def render_home_dashboard() -> None:
    metrics = _metrics()
    profile = _active_profile()
    st.markdown("#### Learning status")
    st.caption(f"Showing learning data for {profile['display_name']}" if profile else "Create or choose a profile to connect learner data.")
    if not metrics:
        st.markdown('<div class="hc-card"><b>Learning data is not available yet</b><p class="hc-muted">XP, attendance, reviews, and completed-item totals will appear when the learner progress service is connected.</p></div>', unsafe_allow_html=True)
        return
    values = [("Current XP", metrics.get("current_xp")), ("Current streak", metrics.get("current_streak")), ("Longest streak", metrics.get("longest_streak")), ("Active today", "Yes" if metrics.get("active_today") else "No"), ("Pending reviews", metrics.get("pending_reviews")), ("Completed items", metrics.get("learning_items_completed"))]
    for row in (values[:3], values[3:]):
        columns = st.columns(3)
        for column, (label, value) in zip(columns, row):
            with column:
                st.markdown(f'<div class="hc-card"><div class="hc-label">{label}</div><div class="hc-value">{escape(str(value if value is not None else "Not available"))}</div></div>', unsafe_allow_html=True)


def render_attendance() -> None:
    metrics = _metrics() or {}
    today = date.today()
    active_days = {str(day) for day in metrics.get("active_days", [])}
    st.markdown('<div class="hc-eyebrow">Attendance</div><div class="hc-title">Show up with intention.</div>', unsafe_allow_html=True)
    st.caption("Opening HintCode does not count as attendance. A completed learning activity is required.")
    st.markdown(f"#### {calendar.month_name[today.month]} {today.year}")
    headers = st.columns(7)
    for column, name in zip(headers, ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
        column.caption(name)
    for week in calendar.monthcalendar(today.year, today.month):
        columns = st.columns(7)
        for column, day in zip(columns, week):
            if day:
                marker = "Active" if date(today.year, today.month, day).isoformat() in active_days else "-"
                column.markdown(f"{day}<br><small>{marker}</small>", unsafe_allow_html=True)
            else:
                column.caption(" ")
    activity = metrics.get("today_activity") or "No qualifying activity recorded."
    st.markdown(f'<div class="hc-card"><div class="hc-label">Meaningful activity today</div><div class="hc-muted">{escape(str(activity))}</div></div>', unsafe_allow_html=True)
    left, right = st.columns(2)
    left.metric("Current streak", metrics.get("current_streak", "Not available"))
    right.metric("Longest streak", metrics.get("longest_streak", "Not available"))


def render_leaderboard() -> None:
    profile = _active_profile()
    metric = st.selectbox("Leaderboard", ["Weekly XP", "All-time XP", "Streak", "Reviews"], key="leaderboard_metric")
    rows = st.session_state.get("leaderboard", {}).get(metric, [])
    st.markdown('<div class="hc-eyebrow">Leaderboard</div><div class="hc-title">Learning momentum.</div>', unsafe_allow_html=True)
    if not rows:
        message = "Create a profile to appear here." if not profile else "Only your profile is active. Rankings will appear when leaderboard data is connected."
        st.markdown(f'<div class="hc-card"><b>No rankings yet</b><p class="hc-muted">{escape(message)}</p></div>', unsafe_allow_html=True)
        return
    for rank, row in enumerate(rows, start=1):
        active = profile and row.get("profile_id") == profile["id"]
        streak = f" - Streak {escape(str(row.get('streak')))}" if metric == "Streak" and row.get("streak") is not None else ""
        marker = " <b>(You)</b>" if active else ""
        st.markdown(f'<div class="hc-card"><b>#{rank} {escape(str(row.get("display_name", "Learner")))}{marker}</b><span class="hc-muted">{streak}</span><div class="hc-value">{escape(str(row.get("score", "Not available")))}</div></div>', unsafe_allow_html=True)


def render_review_queue() -> None:
    ready = [item_id for item_id, status in st.session_state.get("review_statuses", {}).items() if status == "Ready for review"]
    st.markdown('<div class="hc-eyebrow">Review Queue</div><div class="hc-title">Return to what matters.</div>', unsafe_allow_html=True)
    if ready:
        st.markdown(f'<div class="hc-card"><b>{len(ready)} item(s) ready for review</b><p class="hc-muted">Open a learning item from your library to review it.</p></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="hc-card"><b>No pending reviews</b><p class="hc-muted">Schedule a learning item for review to see it here.</p></div>', unsafe_allow_html=True)
