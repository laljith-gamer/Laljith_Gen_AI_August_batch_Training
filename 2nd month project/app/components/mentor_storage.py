"""
Browser IndexedDB Storage Engine & Component for SmartHire AI Career Mentor.
Persists multi-turn conversations, career insights, and candidate memory directly
in the user's browser using HTML5 IndexedDB API via Streamlit Custom Components v2.
"""

import json
import logging
from typing import Dict, Any, List, Optional
import streamlit as st

logger = logging.getLogger(__name__)

# CCv2 HTML structure for browser IndexedDB toolbar
_INDEXEDDB_HTML = """
<div id="sh-idb-container" class="sh-idb-root">
  <div class="sh-idb-header">
    <div class="sh-idb-status-pill">
      <span class="sh-idb-indicator" id="idb-indicator"></span>
      <span class="sh-idb-title">Browser IndexedDB</span>
      <span class="sh-idb-count-badge" id="idb-session-count">0 saved</span>
    </div>
    <div class="sh-idb-sync-msg" id="idb-sync-status">Ready</div>
  </div>

  <div class="sh-idb-controls">
    <div class="sh-idb-select-wrap">
      <select id="idb-session-dropdown" class="sh-idb-select">
        <option value="" disabled selected>Select saved conversation...</option>
      </select>
    </div>
    <div class="sh-idb-btn-group">
      <button id="idb-btn-load" class="sh-idb-btn primary" title="Load selected conversation from IndexedDB">Load</button>
      <button id="idb-btn-export" class="sh-idb-btn secondary" title="Export conversation as JSON">Export</button>
      <button id="idb-btn-clear" class="sh-idb-btn danger" title="Clear saved conversations from IndexedDB">Clear</button>
    </div>
  </div>
</div>
"""

# CCv2 CSS styles adapted to Streamlit theme tokens
_INDEXEDDB_CSS = """
.sh-idb-root {
  display: none !important;
}

.sh-idb-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.sh-idb-status-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--st-text-color, #1e293b);
}

.sh-idb-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #10b981;
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.7);
  display: inline-block;
  animation: idbPulse 2s infinite ease-in-out;
}

@keyframes idbPulse {
  0% { transform: scale(0.95); opacity: 0.8; }
  50% { transform: scale(1.15); opacity: 1; }
  100% { transform: scale(0.95); opacity: 0.8; }
}

.sh-idb-count-badge {
  background: rgba(16, 185, 129, 0.12);
  color: #059669;
  border: 1px solid rgba(16, 185, 129, 0.25);
  padding: 2px 7px;
  border-radius: 9999px;
  font-size: 0.72rem;
  font-weight: 600;
}

.sh-idb-sync-msg {
  font-size: 0.76rem;
  color: var(--st-text-color, #64748b);
  opacity: 0.85;
}

.sh-idb-controls {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.sh-idb-select-wrap {
  flex: 1;
  min-width: 220px;
}

.sh-idb-select {
  width: 100%;
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid var(--st-border-color, rgba(148, 163, 184, 0.3));
  background: var(--st-background-color, #ffffff);
  color: var(--st-text-color, #1e293b);
  font-size: 0.82rem;
  outline: none;
  cursor: pointer;
}

.sh-idb-btn-group {
  display: flex;
  gap: 6px;
}

.sh-idb-btn {
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.sh-idb-btn.primary {
  background: #2563eb;
  color: #ffffff;
}
.sh-idb-btn.primary:hover {
  background: #1d4ed8;
}

.sh-idb-btn.secondary {
  background: transparent;
  border-color: var(--st-border-color, rgba(148, 163, 184, 0.4));
  color: var(--st-text-color, #334155);
}
.sh-idb-btn.secondary:hover {
  background: rgba(148, 163, 184, 0.12);
}

.sh-idb-btn.danger {
  background: transparent;
  border-color: rgba(239, 68, 68, 0.3);
  color: #ef4444;
}
.sh-idb-btn.danger:hover {
  background: rgba(239, 68, 68, 0.1);
}
"""

# CCv2 JavaScript client logic with IndexedDB API
_INDEXEDDB_JS = """
export default function(component) {
  const { parentElement, data, setStateValue, setTriggerValue } = component;
  if (!parentElement) return;

  const DB_NAME = "SmartHireMentorDB";
  const DB_VERSION = 1;
  const STORE_CONV = "conversations";
  const STORE_MEM = "mentor_memory";

  const dropdown = parentElement.querySelector("#idb-session-dropdown");
  const countBadge = parentElement.querySelector("#idb-session-count");
  const syncMsg = parentElement.querySelector("#idb-sync-status");
  const btnLoad = parentElement.querySelector("#idb-btn-load");
  const btnExport = parentElement.querySelector("#idb-btn-export");
  const btnClear = parentElement.querySelector("#idb-btn-clear");
  const indicator = parentElement.querySelector("#idb-indicator");

  function openDatabase() {
    return new Promise((resolve, reject) => {
      if (typeof window === "undefined" || !window.indexedDB) {
        reject(new Error("IndexedDB not supported"));
        return;
      }
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      request.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains(STORE_CONV)) {
          const store = db.createObjectStore(STORE_CONV, { keyPath: "id" });
          store.createIndex("updated_at", "updated_at", { unique: false });
          store.createIndex("title", "title", { unique: false });
        }
        if (!db.objectStoreNames.contains(STORE_MEM)) {
          db.createObjectStore(STORE_MEM, { keyPath: "key" });
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async function getAllConversations() {
    try {
      const db = await openDatabase();
      return new Promise((resolve, reject) => {
        const tx = db.transaction(STORE_CONV, "readonly");
        const store = tx.objectStore(STORE_CONV);
        const req = store.getAll();
        req.onsuccess = () => {
          const items = req.result || [];
          items.sort((a, b) => new Date(b.updated_at || 0) - new Date(a.updated_at || 0));
          resolve(items);
        };
        req.onerror = () => reject(req.error);
      });
    } catch (err) {
      console.warn("[IndexedDB] Error fetching conversations:", err);
      return [];
    }
  }

  async function saveConversation(sessionData) {
    if (!sessionData || !sessionData.id || !sessionData.messages || sessionData.messages.length === 0) {
      return;
    }
    try {
      const db = await openDatabase();
      const tx = db.transaction([STORE_CONV, STORE_MEM], "readwrite");
      const convStore = tx.objectStore(STORE_CONV);
      const memStore = tx.objectStore(STORE_MEM);

      const record = {
        id: sessionData.id,
        title: sessionData.title || (sessionData.messages[0]?.content || "Career Mentoring").substring(0, 45),
        candidate_name: sessionData.candidate_name || "Candidate",
        target_role: sessionData.target_role || "Engineering / Tech",
        updated_at: new Date().toISOString(),
        created_at: sessionData.created_at || new Date().toISOString(),
        message_count: sessionData.messages.length,
        messages: sessionData.messages,
      };

      convStore.put(record);

      if (sessionData.candidate_summary) {
        memStore.put({
          key: "last_candidate_dossier",
          updated_at: new Date().toISOString(),
          dossier: sessionData.candidate_summary,
        });
      }

      await new Promise((res, rej) => {
        tx.oncomplete = res;
        tx.onerror = rej;
      });

      if (syncMsg) syncMsg.textContent = `Auto-saved (${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})})`;
      await refreshDropdown();
    } catch (err) {
      console.warn("[IndexedDB] Error saving conversation:", err);
    }
  }

  async function getAllMemories() {
    try {
      const db = await openDatabase();
      return new Promise((resolve, reject) => {
        const tx = db.transaction(STORE_MEM, "readonly");
        const store = tx.objectStore(STORE_MEM);
        const req = store.getAll();
        req.onsuccess = () => resolve(req.result || []);
        req.onerror = () => reject(req.error);
      });
    } catch (err) {
      console.warn("[IndexedDB] Error fetching memories:", err);
      return [];
    }
  }

  async function refreshDropdown() {
    const sessions = await getAllConversations();
    const memories = await getAllMemories();

    if (countBadge) {
      countBadge.textContent = `${sessions.length} saved`;
    }

    if (setStateValue) {
      setStateValue("saved_sessions", sessions.map(s => ({
        id: s.id,
        title: s.title,
        updated_at: s.updated_at,
        message_count: s.message_count,
        candidate_name: s.candidate_name,
        target_role: s.target_role,
      })));
      setStateValue("stored_memories", memories);
    }

    if (dropdown) {
      const currentSelected = dropdown.value;
      dropdown.innerHTML = "";

      if (sessions.length === 0) {
        const opt = document.createElement("option");
        opt.value = "";
        opt.textContent = "No saved conversations yet";
        dropdown.appendChild(opt);
      } else {
        const promptOpt = document.createElement("option");
        promptOpt.value = "";
        promptOpt.disabled = true;
        promptOpt.selected = !currentSelected;
        promptOpt.textContent = `Browse ${sessions.length} saved session${sessions.length > 1 ? 's' : ''}...`;
        dropdown.appendChild(promptOpt);

        sessions.forEach((s) => {
          const opt = document.createElement("option");
          opt.value = s.id;
          const dateStr = s.updated_at ? new Date(s.updated_at).toLocaleDateString() : "";
          opt.textContent = `[${dateStr}] ${s.title} (${s.message_count} msgs)`;
          if (s.id === currentSelected) opt.selected = true;
          dropdown.appendChild(opt);
        });
      }
    }
  }

  async function handleLoad() {
    if (!dropdown || !dropdown.value) return;
    const sessionId = dropdown.value;
    try {
      const db = await openDatabase();
      const tx = db.transaction(STORE_CONV, "readonly");
      const store = tx.objectStore(STORE_CONV);
      const req = store.get(sessionId);
      req.onsuccess = () => {
        const item = req.result;
        if (item && item.messages) {
          if (syncMsg) syncMsg.textContent = `Loaded "${item.title.substring(0, 20)}..."`;
          setTriggerValue("restore_session_payload", item);
        }
      };
    } catch (err) {
      console.warn("[IndexedDB] Error loading session:", err);
    }
  }

  async function handleExport() {
    const sessions = await getAllConversations();
    if (sessions.length === 0) {
      alert("No saved conversations in IndexedDB to export.");
      return;
    }
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(sessions, null, 2));
    const dlAnchor = document.createElement("a");
    dlAnchor.setAttribute("href", dataStr);
    dlAnchor.setAttribute("download", `smarthire_mentor_history_${Date.now()}.json`);
    dlAnchor.click();
  }

  async function handleClear() {
    if (!confirm("Are you sure you want to delete all saved conversations from your browser IndexedDB?")) {
      return;
    }
    try {
      const db = await openDatabase();
      const tx = db.transaction([STORE_CONV, STORE_MEM], "readwrite");
      tx.objectStore(STORE_CONV).clear();
      tx.objectStore(STORE_MEM).clear();
      await new Promise((res, rej) => {
        tx.oncomplete = res;
        tx.onerror = rej;
      });
      if (syncMsg) syncMsg.textContent = "Browser storage cleared.";
      await refreshDropdown();
      setTriggerValue("cleared_storage_trigger", true);
    } catch (err) {
      console.warn("[IndexedDB] Error clearing database:", err);
    }
  }

  // Bind event listeners
  if (btnLoad) btnLoad.onclick = handleLoad;
  if (btnExport) btnExport.onclick = handleExport;
  if (btnClear) btnClear.onclick = handleClear;

  // Process data actions
  refreshDropdown().then(async () => {
    if (!data) return;
    if (data.action === "save" && data.session) {
      await saveConversation(data.session);
    } else if (data.action === "delete_session" && data.session_id) {
      try {
        const db = await openDatabase();
        const tx = db.transaction(STORE_CONV, "readwrite");
        tx.objectStore(STORE_CONV).delete(data.session_id);
        await new Promise(r => { tx.oncomplete = r; });
        await refreshDropdown();
      } catch (err) {
        console.warn("[IndexedDB] Error deleting session:", err);
      }
    } else if (data.action === "load_session" && data.session_id) {
      try {
        const db = await openDatabase();
        const tx = db.transaction(STORE_CONV, "readonly");
        const req = tx.objectStore(STORE_CONV).get(data.session_id);
        req.onsuccess = () => {
          if (req.result && req.result.messages) {
            setTriggerValue("restore_session_payload", req.result);
          }
        };
      } catch (err) {
        console.warn("[IndexedDB] Error loading session:", err);
      }
    } else if (data.action === "save_memory" && data.memory_item) {
      try {
        const db = await openDatabase();
        const tx = db.transaction(STORE_MEM, "readwrite");
        tx.objectStore(STORE_MEM).put(data.memory_item);
        await new Promise(r => { tx.oncomplete = r; });
        await refreshDropdown();
      } catch (err) {
        console.warn("[IndexedDB] Error saving memory:", err);
      }
    }
  });

}
"""

# Register CCv2 component once at module import
_INDEXEDDB_COMPONENT = st.components.v2.component(
    "mentor_indexeddb_storage",
    html=_INDEXEDDB_HTML,
    css=_INDEXEDDB_CSS,
    js=_INDEXEDDB_JS,
)


class MentorIndexedDBManager:
    """Manages reactive bidirectional integration between Streamlit and Browser IndexedDB."""

    @classmethod
    def render_storage_toolbar(
        cls,
        active_session_id: str,
        messages: List[Dict[str, Any]],
        candidate_summary: Dict[str, Any],
        action_override: Optional[str] = None,
        action_payload: Optional[Dict[str, Any]] = None,
        key: str = "mentor_idb_sync",
    ) -> Optional[Any]:
        """
        Renders the browser IndexedDB synchronization toolbar.
        Auto-persists current chat messages to client-side IndexedDB and detects restoration events.
        """
        title = "Career Mentoring"
        if messages and len(messages) > 0:
            first_user_msg = next((m.get("content", "") for m in messages if m.get("role") == "user"), "")
            if first_user_msg:
                title = first_user_msg[:50].strip()

        session_payload = None
        action = "idle"
        if messages and len(messages) > 0:
            action = "save"
            session_payload = {
                "id": active_session_id,
                "title": title,
                "candidate_name": candidate_summary.get("name", "Candidate"),
                "target_role": candidate_summary.get("target_role", "Engineering / Tech"),
                "candidate_summary": candidate_summary,
                "messages": messages,
            }

        component_data: Dict[str, Any] = {
            "action": action_override or action,
            "session": session_payload,
        }
        if action_payload:
            component_data.update(action_payload)

        try:
            result = _INDEXEDDB_COMPONENT(
                key=key,
                data=component_data,
            )
            return result
        except Exception as exc:
            logger.warning(f"Could not mount IndexedDB CCv2 component: {exc}")
            return None



__all__ = ["MentorIndexedDBManager"]
