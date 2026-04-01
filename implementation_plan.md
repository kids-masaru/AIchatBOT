# Implementation Plan - Fix Duplicate Reminders & Profiler

## Goal Description
Resolve critical issues identified in production logs:
1.  **Duplicate Reminders**: Prevent users from receiving the same daily reminder twice.
2.  **Incorrect Date (Yesterday's Schedule)**: Ensure the AI uses Japan Standard Time (JST) for "today".
3.  **Profiler Crash**: Fix `Zero Vector` error in Pinecone and improve JSON parsing.

## Proposed Changes

### 1. Fix Schedule Date Mismatch (Timezone)

#### [MODIFY] [app.py](file:///c:/Users/HP/OneDrive/ドキュメント/mottora/AIchatBOT/app.py)
- Update `process_user_reminders`:
    - Define `JST` explicitly.
    - Calculate `now` in JST.
    - Pass current date/time (in JST) explicitly to `send_reminder`.
- Update `send_reminder`:
    - Add JST date context to the AI prompt: `「現在は日本時間で 2026年1月16日 07:00 です」`

### 2. Implement Duplicate Prevention

#### [MODIFY] [app.py](file:///c:/Users/HP/OneDrive/ドキュメント/mottora/AIchatBOT/app.py)
- Introduce a simple in-memory tracking or Sheet-based tracking for "last sent date".
- Given the single-worker environment appropriate for `BackgroundScheduler`, in-memory tracking (global dict) is the simplest and fastest solution for now.
    - `last_reminder_sent = {'user_id': '2026-01-16'}`
- In `process_user_reminders`, check if `last_reminder_sent[user_id] == today_jst`. If so, skip.

### 3. Fix Profiler Error

#### [MODIFY] [utils/vector_store.py](file:///c:/Users/HP/OneDrive/ドキュメント/mottora/AIchatBOT/utils/vector_store.py)
- Update `save_user_profile`:
    - Change `dummy_vector` from all zeros to `[0.1] * DIMENSION`.

#### [MODIFY] [core/profiler.py](file:///c:/Users/HP/OneDrive/ドキュメント/mottora/AIchatBOT/core/profiler.py)
- Update `_analyze_and_merge`:
    - Improve JSON extraction logic (handle cases where Gemini returns text before/after JSON code block).

## Verification Plan

### Automated Verification
- None (Logic is heavily dependent on Gemini API and Scheduler timing)

### Manual Verification
1.  **Profiler Fix**:
    - Run `POST /debug/run-profiler` (via CURL or Browser Console if available, or just wait for logs).
    - Check Railway logs: Ensure `Profiler: Profile updated successfully.` appears without errors.

2.  **Date & Duplicate Fix**:
    - Temporarily change `check_reminders` cron schedule to run every minute (or trigger manually via `/cron`).
    - Verify logs show "Sent reminder" only *once* per day per user.
    - Check the content of the reminder (via Push message) to ensure it says "Today is [Correct Date]".
