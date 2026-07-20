"""Habit-building learning surfaces for HintCode.

The data in this module is deliberately presentation-ready and local.  It gives
each screen a stable contract while the product analytics and gamification APIs
are introduced behind it.
"""

from __future__ import annotations

import streamlit as st


LEVELS = [
    ("01", "Syntax Explorer", "Learn the language of code"),
    ("02", "Pattern Hunter", "Recognize useful shapes"),
    ("03", "Algorithm Apprentice", "Build reliable approaches"),
    ("04", "Problem Solver", "Handle unfamiliar challenges"),
    ("05", "Interview Ready", "Explain decisions with clarity"),
    ("06", "Coding Master", "Keep growing through practice"),
]


def inject_learning_styles() -> None:
    st.markdown(
        """<style>
        .block-container {max-width: 1240px; padding-top: 2rem; padding-bottom: 3rem;}
        [data-testid="stSidebar"] {background: #0d1224;}
        [data-testid="stSidebar"] * {color: #e8edff !important;}
        .hc-kicker {color:#7667ff;font-weight:700;font-size:.78rem;letter-spacing:.12em;text-transform:uppercase;}
        .hc-title {font-size:2.35rem;font-weight:800;line-height:1.05;margin:.25rem 0 .4rem;color:#17213b;}
        .hc-sub {color:#69738c;font-size:1rem;margin-bottom:1.4rem;}
        .hc-card {background:linear-gradient(145deg,#fff,#f8f9ff); border:1px solid #e8eaf4; border-radius:18px;padding:1.1rem 1.2rem;margin:.25rem 0 .8rem; box-shadow:0 5px 16px rgba(29,38,78,.045);}
        .hc-metric {font-size:1.7rem;font-weight:800;color:#17213b;margin:.15rem 0;}.hc-label{font-size:.82rem;color:#737d94;font-weight:600;}
        .hc-tag {display:inline-block;background:#eeecff;color:#5646d8;border-radius:999px;padding:.22rem .58rem;font-size:.76rem;font-weight:700;margin-right:.3rem;}
        .hc-mission {border-left:4px solid #7667ff;background:#f7f6ff;border-radius:0 15px 15px 0;padding:1rem 1.1rem;margin:.55rem 0;}
        .hc-done {border-left-color:#26b984;background:#f1fbf7;}.hc-soon {opacity:.72;}
        .hc-hero {background:linear-gradient(120deg,#1b2140,#5546c9 60%,#876cf1);color:#fff;border-radius:22px;padding:1.7rem 1.8rem;margin:.4rem 0 1.1rem;}
        .hc-hero h2,.hc-hero p {color:#fff!important;margin:.1rem 0 .6rem;}.hc-row {display:flex;justify-content:space-between;gap:1rem;align-items:center;}
        .hc-ring {width:58px;height:58px;border:6px solid #a99eff;border-top-color:#fff;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:800;}
        .hc-calendar {display:grid;grid-template-columns:repeat(7,1fr);gap:7px;margin-top:.65rem;}.hc-day {border-radius:9px;background:#f0f1f8;text-align:center;padding:.48rem 0;color:#737d94;font-size:.8rem;}.hc-active {background:#7667ff;color:#fff;font-weight:800;}.hc-today{outline:2px solid #ffbd4a;}
        .hc-bar {height:9px;background:#ebedf5;border-radius:9px;overflow:hidden;margin:.55rem 0;}.hc-fill {height:100%;border-radius:9px;background:linear-gradient(90deg,#7667ff,#9d83ff);}
        .hc-list {padding:.65rem 0;border-bottom:1px solid #eceef5;}.hc-list:last-child{border-bottom:0;}
        .hc-badge {background:#fff8e7;border:1px solid #ffe1a0;border-radius:18px;padding:1rem;margin:.3rem 0;text-align:left;min-height:118px;}
        </style>""",
        unsafe_allow_html=True,
    )


def _heading(kicker: str, title: str, subtitle: str) -> None:
    st.markdown(f'<div class="hc-kicker">{kicker}</div><div class="hc-title">{title}</div><div class="hc-sub">{subtitle}</div>', unsafe_allow_html=True)


def _metric(label: str, value: str, note: str = "") -> None:
    st.markdown(f'<div class="hc-card"><div class="hc-label">{label}</div><div class="hc-metric">{value}</div><small>{note}</small></div>', unsafe_allow_html=True)


def _progress(label: str, value: int, note: str) -> None:
    st.markdown(f'<div class="hc-list"><b>{label}</b><span style="float:right;color:#69738c">{note}</span><div class="hc-bar"><div class="hc-fill" style="width:{value}%"></div></div></div>', unsafe_allow_html=True)


def _calendar() -> None:
    st.markdown('<div class="hc-calendar">', unsafe_allow_html=True)
    for day in range(1, 29):
        state = "hc-active" if day in {1, 2, 3, 5, 6, 7, 8, 10, 11, 12, 14, 15, 16, 17, 19, 20} else ""
        today = "hc-today" if day == 20 else ""
        st.markdown(f'<div class="hc-day {state} {today}">{day}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def render_home() -> None:
    _heading("Your learning space", "Good evening, Mina.", "A few focused steps today make tomorrow’s problems feel lighter.")
    a, b, c, d = st.columns(4)
    with a: _metric("🔥 DAILY STREAK", "12 days", "Personal best: 18")
    with b: _metric("⭐ LEVEL", "Pattern Hunter", "Level 2 · 68% complete")
    with c: _metric("⚡ XP", "1,840", "+120 this week")
    with d: _metric("🎯 TODAY", "2 / 4", "Missions completed")
    left, right = st.columns([1.45, 1])
    with left:
        st.markdown('<div class="hc-hero"><div class="hc-row"><div><p>YOUR NEXT FOCUS</p><h2>Think in graphs, not paths.</h2><p>One small warm-up unlocks today’s Graph mission.</p></div><div class="hc-ring">68%</div></div></div>', unsafe_allow_html=True)
        st.markdown("#### 🎯 Today’s mission")
        st.markdown('<div class="hc-mission hc-done"><b>✓ Warm-up: spot a duplicate</b><br><small>Arrays · completed · +15 XP</small></div>', unsafe_allow_html=True)
        st.markdown('<div class="hc-mission"><b>Graph: find connected components</b><br><small>25–35 min · +60 XP · Recommended next</small></div>', unsafe_allow_html=True)
        if st.button("Start today’s path", type="primary", key="home_start"):
            st.session_state["pending_learning_page"] = "Today"
            st.rerun()
        st.markdown("#### 📚 Review queue")
        for title, due in [("Two Sum", "Due today"), ("Valid Parentheses", "Due today"), ("Number of Islands", "Tomorrow")]:
            st.markdown(f'<div class="hc-list"><b>{title}</b><span style="float:right;color:#7667ff">{due}</span></div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="hc-card"><div class="hc-label">📅 ATTENDANCE · JULY</div><b>12-day active rhythm</b>', unsafe_allow_html=True)
        _calendar(); st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("#### 🧠 Weakest topic")
        st.markdown('<div class="hc-card"><b>Graph traversal</b><br><small>You often find the right data structure after the first hint. Try drawing the visited set before coding.</small></div>', unsafe_allow_html=True)
        st.markdown("#### 💡 AI tip of the day")
        st.info("Before writing a loop, name the invariant: what must remain true after every iteration?")
        st.markdown("#### 📈 Weekly progress")
        for label, pct, note in [("Practice", 78, "7 / 9 sessions"), ("Review", 60, "6 / 10 cards"), ("Hint-free solves", 45, "5 / 11")]: _progress(label, pct, note)


def render_today() -> None:
    _heading("A deliberate session", "Today’s path", "Four short chapters, one clearer way of thinking.")
    steps = [("01", "Warm-up", "Find the first repeated value", "5 min · Arrays · +15 XP", True), ("02", "Main mission", "Connected components", "30 min · Graph · +60 XP", False), ("03", "Review mission", "Refresh 3 previous patterns", "10 min · Spaced review · +30 XP", False), ("04", "Reflection", "Capture what clicked", "2 min · Builds your Thought Profile", False)]
    for n, name, task, detail, complete in steps:
        state = "hc-done" if complete else ""
        st.markdown(f'<div class="hc-mission {state}"><span class="hc-tag">{n}</span> <b>{name}</b><h4 style="margin:.5rem 0 .15rem">{task}</h4><small>{detail}</small></div>', unsafe_allow_html=True)
    if st.button("Begin main mission", type="primary"):
        st.query_params["page"] = "detail"
        st.query_params["problem_id"] = "1"
        st.rerun()


def render_attendance() -> None:
    _heading("Show up, gently", "Attendance", "Consistency is a signal—not a scorecard.")
    a, b, c = st.columns(3)
    with a: _metric("CURRENT RHYTHM", "12 days", "You’re one day from a new best")
    with b: _metric("JULY CHECK-INS", "20", "71% of the month")
    with c: _metric("NEXT REWARD", "3 days", "Unlock the Focus Flame")
    st.markdown('<div class="hc-card"><div class="hc-label">MONTHLY ATTENDANCE CALENDAR</div>', unsafe_allow_html=True); _calendar(); st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("#### Attendance rewards")
    for reward, status in [("7-day rhythm · 50 XP", "Claimed"), ("14-day rhythm · Focus Flame", "2 days to go"), ("30-day rhythm · Deep Work badge", "10 days to go")]:
        st.markdown(f'<div class="hc-list"><b>{reward}</b><span style="float:right;color:#7667ff">{status}</span></div>', unsafe_allow_html=True)


def render_xp() -> None:
    _heading("Every attempt counts", "XP & momentum", "Progress is earned in small, visible moments.")
    st.markdown('<div class="hc-hero"><p>LEVEL 2 · PATTERN HUNTER</p><h2>1,840 / 2,700 XP</h2><div class="hc-bar"><div class="hc-fill" style="width:68%"></div></div><p>860 XP until Algorithm Apprentice</p></div>', unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        st.markdown("#### Today’s XP")
        for item, xp in [("Warm-up solved", "+15"), ("Helpful reflection", "+10"), ("Main mission", "+60"), ("Review queue", "+30")]: st.markdown(f'<div class="hc-list"><b>{item}</b><span style="float:right;color:#26a778">{xp} XP</span></div>', unsafe_allow_html=True)
    with right:
        st.markdown("#### Recent momentum")
        for label, pct, note in [("Mon", 85, "+95 XP"), ("Tue", 55, "+60 XP"), ("Wed", 100, "+140 XP"), ("Thu", 70, "+75 XP")]: _progress(label, pct, note)


def render_levels() -> None:
    _heading("A path with texture", "Levels", "Each level changes what you notice in a problem.")
    for code, title, description in LEVELS:
        current = title == "Pattern Hunter"
        status = '<span style="color:#7667ff">· Current</span>' if current else ""
        st.markdown(f'<div class="hc-card"><span class="hc-tag">{code}</span> <b>{title}</b>{status}<br><small>{description}</small></div>', unsafe_allow_html=True)


def render_achievements() -> None:
    _heading("Proof of practice", "Achievements", "Collect the moments that changed your approach.")
    badges = [("✓", "First Solve", "Your first independent answer"), ("🔥", "7-Day Streak", "Showed up for a full week"), ("🔒", "30-Day Streak", "Keep your rhythm going"), ("100", "100 Problems", "74 / 100 solved"), ("✦", "Hint-Free ×20", "12 / 20 clear solves"), ("◎", "Graph Master", "Practice traversal next"), ("◇", "DP Explorer", "Unlock dynamic programming"), ("↻", "Review Master", "8 / 20 reviews")]
    cols = st.columns(4)
    for i, (icon, title, note) in enumerate(badges):
        with cols[i % 4]: st.markdown(f'<div class="hc-badge"><b style="font-size:1.4rem">{icon}</b><br><b>{title}</b><br><small>{note}</small></div>', unsafe_allow_html=True)


def render_leaderboard() -> None:
    _heading("Learn alongside people", "Leaderboard", "A friendly signal of shared momentum.")
    scope = st.radio("Rankings", ["Weekly", "Monthly", "Friends", "University", "Future Global"], horizontal=True)
    names = [("1", "Jisoo Park", "1,340 XP"), ("2", "Arin Lee", "1,225 XP"), ("3", "You", "1,180 XP"), ("4", "Minho Kim", "1,075 XP"), ("5", "Sora Choi", "980 XP")]
    st.markdown(f"#### {scope} standings")
    for rank, name, xp in names:
        highlight = "background:#f1efff;" if name == "You" else ""
        st.markdown(f'<div class="hc-card" style="{highlight}"><b>#{rank}</b> &nbsp; {name}<span style="float:right;color:#7667ff;font-weight:700">{xp}</span></div>', unsafe_allow_html=True)


def render_missions() -> None:
    _heading("Choose your commitments", "Missions", "Useful prompts that fit around real life.")
    tabs = st.tabs(["Daily", "Weekly", "Monthly"])
    content = [[("Solve 3 problems", "2 / 3", 67), ("No hints today", "In progress", 45), ("Finish review queue", "2 / 3", 66)], [("Solve one Graph problem", "0 / 1", 10), ("Practice 4 days", "3 / 4", 75), ("Earn 400 XP", "280 / 400", 70)], [("Complete 15 reviews", "8 / 15", 53), ("Solve 20 problems", "14 / 20", 70), ("Build a 14-day rhythm", "12 / 14", 86)]]
    for tab, missions in zip(tabs, content):
        with tab:
            for label, note, pct in missions: _progress(label, pct, note)


def render_skill_tree() -> None:
    _heading("Make skills visible", "Skill tree", "Follow the concepts that unlock your next move.")
    skills = [("Arrays", 88, "Strong"), ("HashMap", 76, "Growing"), ("Graph", 42, "Focus here"), ("Tree", 54, "Growing"), ("DP", 25, "Locked next"), ("Greedy", 61, "Growing")]
    for label, value, note in skills: _progress(label, value, note)


def render_thought_profile() -> None:
    _heading("A mirror for your reasoning", "Thought profile", "Patterns from your practice, explained in human language.")
    left, right = st.columns(2)
    with left:
        st.markdown("#### Strengths")
        for text in ["You identify array patterns quickly.", "You verify edge cases before submitting.", "You improve after a single progressive hint."]: st.markdown(f'<div class="hc-card">✦ {text}</div>', unsafe_allow_html=True)
    with right:
        st.markdown("#### Growth opportunities")
        for text in ["State the graph traversal strategy before coding.", "Pause before choosing recursion by default.", "Build confidence with two medium Graph problems."]: st.markdown(f'<div class="hc-card">→ {text}</div>', unsafe_allow_html=True)
    st.markdown("#### Thinking habits")
    st.info("You tend to explore through examples first. That is a strength—add a one-line invariant before you implement to reduce rewrites.")


def render_coding_dna() -> None:
    _heading("Your evolving signature", "Coding DNA", "A lightweight portrait of how you solve—not a label you have to live up to.")
    a, b, c = st.columns(3)
    with a: _metric("PREFERRED TOOL", "HashMap", "Used in 31% of solves")
    with b: _metric("SOLVING STYLE", "Example-led", "You learn by testing shape")
    with c: _metric("GROWTH SIGNAL", "+24%", "More hint-free attempts")
    st.markdown("#### Improvement timeline")
    for label, value, note in [("May · Fundamentals", 38, "Arrays started"), ("June · Patterns", 62, "HashMaps clicked"), ("July · Exploration", 78, "Graph practice underway")]: _progress(label, value, note)


def render_review_queue() -> None:
    _heading("Let insight stick", "Review queue", "Small returns at the right time turn practice into recall.")
    cols = st.columns(4)
    groups = [("Today", ["Two Sum", "Valid Parentheses"]), ("Tomorrow", ["Number of Islands", "Binary Search"]), ("Upcoming", ["Climbing Stairs", "Merge Intervals"]), ("Overdue", ["Contains Duplicate"])]
    for col, (label, items) in zip(cols, groups):
        with col:
            st.markdown(f"#### {label}")
            for item in items: st.markdown(f'<div class="hc-card"><b>{item}</b><br><small>Recall the core pattern</small></div>', unsafe_allow_html=True)


def render_weekly_report() -> None:
    _heading("A week in perspective", "Weekly report", "July 14–20 · Your practice was more consistent and more independent.")
    a, b, c, d = st.columns(4)
    with a: _metric("XP", "+480", "+18% from last week")
    with b: _metric("ATTENDANCE", "6 / 7", "Strong rhythm")
    with c: _metric("SOLVED", "9", "3 hint-free")
    with d: _metric("REVIEW", "8", "80% completed")
    left, right = st.columns(2)
    with left:
        st.markdown("#### Topic movement")
        for label, pct, note in [("Arrays", 88, "+4 points"), ("HashMap", 76, "+8 points"), ("Graph", 42, "+12 points")]: _progress(label, pct, note)
    with right:
        st.markdown("#### Best improvement")
        st.markdown('<div class="hc-hero"><p>GRAPH THINKING</p><h2>You started planning before coding.</h2><p>Your time to first useful approach dropped by 22%.</p></div>', unsafe_allow_html=True)


PAGES = {
    "Home": render_home, "Today": render_today, "Attendance": render_attendance,
    "XP": render_xp, "Levels": render_levels, "Achievements": render_achievements,
    "Leaderboard": render_leaderboard, "Missions": render_missions, "Skill Tree": render_skill_tree,
    "Thought Profile": render_thought_profile, "Coding DNA": render_coding_dna,
    "Review Queue": render_review_queue, "Weekly Report": render_weekly_report,
}


def render_learning_page(page: str) -> None:
    inject_learning_styles()
    PAGES.get(page, render_home)()
