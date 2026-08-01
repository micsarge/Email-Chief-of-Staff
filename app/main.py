import os
import sys
from pathlib import Path

from datetime import date, datetime, timedelta

from flask import Flask, jsonify, render_template_string

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_proton_bridge_config
from src.mailbox import MailboxReader
from src.proton_bridge import ProtonBridgeClient
from src.review import ReviewItem, ReviewQueue
from src.rules import RuleEngine, load_rules_from_yaml

app = Flask(__name__)
STATE_PATH = Path(__file__).resolve().parent / "review_state.json"

HTML = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Email Chief of Staff</title>
    <style>
      body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; background: #f3f6fb; color: #20304a; }
      .shell { max-width: 1120px; margin: 0 auto; padding: 2rem; }
      .hero { background: linear-gradient(135deg, #355c7d, #6c5ce7); color: white; border-radius: 16px; padding: 1.5rem 1.75rem; box-shadow: 0 10px 30px rgba(0,0,0,0.12); }
      .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin: 1.25rem 0 1.5rem; }
      .stat { background: white; padding: 1rem; border-radius: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.06); }
      .card { background: white; border: 1px solid #e3e8f1; border-radius: 12px; padding: 1rem; margin-bottom: 1rem; box-shadow: 0 4px 16px rgba(0,0,0,0.06); }
      .pill { display: inline-block; padding: 0.25rem 0.6rem; border-radius: 999px; font-size: 0.8rem; font-weight: 700; margin-bottom: 0.6rem; }
      .pill-delete { background: #ffe7e7; color: #a42b2b; }
      .pill-archive { background: #eaf4ff; color: #2457a3; }
      .pill-respond { background: #eaf8ee; color: #2f7545; }
      button { margin-right: 0.5rem; border: none; cursor: pointer; padding: 0.45rem 0.8rem; border-radius: 999px; font-weight: 600; }
      .btn-approve { background: #2f7545; color: white; }
      .btn-reject { background: #e3e8f1; color: #20304a; }
      .meta { color: #5f6c82; font-size: 0.95rem; margin-top: 0.35rem; }
      .status { margin-top: 0.75rem; color: #0f172a; font-weight: 600; display: inline-block; padding: 0.4rem 0.7rem; border-radius: 999px; background: rgba(255,255,255,0.9); }
      .status.running { color: #7c2d12; background: #fef3c7; }
      .status.error { color: #7f1d1d; background: #fee2e2; }
      .summary-list { margin-top: 0.4rem; color: #20304a; }
      h2 { margin-top: 0; }
    </style>
  </head>
  <body>
    <div class="shell">
      <div class="hero">
        <h1>Email Chief of Staff</h1>
        <p>Review your inbox in a calm, decision-first dashboard with suggested next steps.</p>
        <div style="margin-top: 1rem;">
          <button class="btn-approve" onclick="cleanupInbox()">Clean matching inbox items</button>
          <div class="status" id="status"></div>
        </div>
      </div>
      <div class="stats" id="stats"></div>
      <div id="items"></div>
    </div>
    <script>
      async function loadItems() {
        const response = await fetch('/api/review');
        const data = await response.json();
        const stats = document.getElementById('stats');
        const items = document.getElementById('items');
        stats.innerHTML = '';
        items.innerHTML = '';

        const total = data.totalMessages;
        const sinceYesterday = data.messagesSinceYesterday;
        const deleteCount = data.categories.delete;
        const archiveCount = data.categories.archive;
        const respondCount = data.categories.respond;

        const statMarkup = `
          <div class="stat"><strong>${total}</strong><div>Messages still in INBOX</div></div>
          <div class="stat"><strong>${sinceYesterday}</strong><div>Messages in current scan</div></div>
          <div class="stat"><strong>${deleteCount}</strong><div>Delete suggestions</div></div>
          <div class="stat"><strong>${archiveCount}</strong><div>Archive suggestions</div></div>
          <div class="stat"><strong>${respondCount}</strong><div>Respond suggestions</div></div>
        `;
        stats.innerHTML = statMarkup;

        if (!data.recommendations.length) {
          items.innerHTML = '<div class="card"><p>No recommendations right now.</p></div>';
          return;
        }

        data.recommendations.forEach(item => {
          const card = document.createElement('div');
          card.className = 'card';
          const pillClass = item.action === 'delete' ? 'pill-delete' : item.action === 'archive' ? 'pill-archive' : 'pill-respond';
          const pillLabel = item.action === 'delete' ? 'Delete' : item.action === 'archive' ? 'Archive' : 'Respond';
          card.innerHTML = `
            <div class="pill ${pillClass}">${pillLabel}</div>
            <strong>${item.subject}</strong><br/>
            <div class="meta">From: ${item.sender}</div>
            <div class="meta">Date: ${item.date || 'Unknown'}</div>
            <div class="meta">Reason: ${item.reason}</div>
            <div class="meta">Status: ${item.status}</div>
            <div style="margin-top: 0.75rem;">
              <button class="btn-approve" onclick="approve('${item.id}')">Approve</button>
              <button class="btn-reject" onclick="reject('${item.id}')">Reject</button>
            </div>
          `;
          items.appendChild(card);
        });
      }

      async function approve(id) {
        await fetch('/api/review/' + id + '/approve', { method: 'POST' });
        loadItems();
      }

      async function reject(id) {
        await fetch('/api/review/' + id + '/reject', { method: 'POST' });
        loadItems();
      }

      async function cleanupInbox() {
        const statusEl = document.getElementById('status');
        statusEl.textContent = 'Cleaning matching messages...';
        statusEl.className = 'status running';
        try {
          const response = await fetch('/api/review/cleanup', { method: 'POST' });
          const data = await response.json();
          const summary = [];
          if (data.counts.delete) summary.push(data.counts.delete + ' deleted');
          if (data.counts.archive) summary.push(data.counts.archive + ' archived');
          if (data.counts.respond) summary.push(data.counts.respond + ' responded');
          statusEl.innerHTML = '<div>' + data.applied + ' matching messages were cleaned.</div><div class="summary-list">' + summary.join(', ') + '</div>';
          statusEl.className = 'status';
          loadItems();
        } catch (error) {
          statusEl.textContent = 'Cleanup failed. Check the server logs for details.';
          statusEl.className = 'status error';
        }
      }

      loadItems();
    </script>
  </body>
</html>
"""


@app.get("/")
def index():
    return render_template_string(HTML)


def build_review_queue():
    cfg = load_proton_bridge_config()
    client = ProtonBridgeClient(cfg)
    reader = MailboxReader(client)
    engine = RuleEngine(load_rules_from_yaml())

    messages = reader.fetch_all_messages()
    queue = ReviewQueue(state_path=str(STATE_PATH))
    for message in messages:
        existing = [item for item in queue.items if item.message.id == message.id]
        if existing:
            continue
        queue.add(ReviewItem(message=message, result=engine.evaluate(message)))
    queue.save_state()
    return queue, messages


@app.get("/api/review")
def review_api():
    queue, messages = build_review_queue()

    recommendations = [item for item in queue.to_summary() if item["action"] != "none"]

    categories = {"delete": 0, "archive": 0, "respond": 0}
    for item in recommendations:
        if item["action"] == "delete":
            categories["delete"] += 1
        elif item["action"] == "archive":
            categories["archive"] += 1
        else:
            categories["respond"] += 1

    return jsonify(
        {
            "totalMessages": len(messages),
            "messagesSinceYesterday": len(messages),
            "categories": categories,
            "recommendations": recommendations,
        }
    )


@app.post("/api/review/<message_id>/approve")
def approve_item(message_id: str):
    queue = ReviewQueue(state_path=str(STATE_PATH))
    queue.load_state()
    ok = queue.approve(message_id)
    if ok:
        item = next((entry for entry in queue.items if entry.message.id == message_id), None)
        if item and item.result.action:
            cfg = load_proton_bridge_config()
            client = ProtonBridgeClient(cfg)
            client.apply_action(message_id, item.result.action.action)
    return jsonify({"ok": ok, "message_id": message_id})


@app.post("/api/review/cleanup")
def cleanup_all_items():
    queue, messages = build_review_queue()
    cfg = load_proton_bridge_config()
    client = ProtonBridgeClient(cfg)

    counts = {"delete": 0, "archive": 0, "respond": 0}
    applied = 0
    for item in queue.items:
        if item.approved is not None:
            continue
        if item.result.action is None:
            continue
        action = item.result.action.action
        if action not in counts:
            counts[action] = 0
        if client.apply_action(item.message.id, action):
            item.approved = True
            applied += 1
            counts[action] += 1
        else:
            item.approved = False

    queue.save_state()
    return jsonify({"ok": True, "applied": applied, "counts": counts, "totalMessages": len(messages)})


@app.post("/api/review/<message_id>/reject")
def reject_item(message_id: str):
    queue = ReviewQueue(state_path=str(STATE_PATH))
    queue.load_state()
    ok = queue.reject(message_id)
    return jsonify({"ok": ok, "message_id": message_id})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
