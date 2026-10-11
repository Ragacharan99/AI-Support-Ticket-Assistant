const state = { queue: [], selectedId: null, retry: null, newTicketId: null };

const elements = {
  acceptanceRate: document.querySelector("#acceptance-rate"),
  averageReviewTime: document.querySelector("#average-review-time"),
  ticketsWaiting: document.querySelector("#tickets-waiting"),
  queueCount: document.querySelector("#queue-count"),
  queueList: document.querySelector("#queue-list"),
  emptyReview: document.querySelector("#empty-review"),
  ticketReview: document.querySelector("#ticket-review"),
  subject: document.querySelector("#ticket-subject"),
  body: document.querySelector("#ticket-body"),
  summary: document.querySelector("#ticket-summary"),
  ticketUrgency: document.querySelector("#ticket-urgency"),
  category: document.querySelector("#category-select"),
  urgency: document.querySelector("#urgency-select"),
  reviewer: document.querySelector("#reviewer-input"),
  reply: document.querySelector("#reply-input"),
  approve: document.querySelector("#approve-button"),
  edited: document.querySelector("#edited-button"),
  reject: document.querySelector("#reject-button"),
  errorBanner: document.querySelector("#error-banner"),
  errorMessage: document.querySelector("#error-message"),
  retry: document.querySelector("#retry-button"),
  dismissError: document.querySelector("#dismiss-error"),
  newForm: document.querySelector("#new-ticket-form"),
  newSubject: document.querySelector("#new-subject"),
  newBody: document.querySelector("#new-body"),
  analyze: document.querySelector("#analyze-button"),
  newStatus: document.querySelector("#new-ticket-status"),
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    if (response.status === 502) throw new Error("AI analysis could not complete. Please try again shortly.");
    if (response.status >= 500) throw new Error("The server could not complete that request. Please try again.");
    throw new Error("The request could not be completed. Please check the ticket and try again.");
  }
  return response.json();
}

function showError(message, retry = null) {
  state.retry = retry;
  elements.errorMessage.textContent = message;
  elements.retry.hidden = !retry;
  elements.errorBanner.hidden = false;
}

function clearError() {
  state.retry = null;
  elements.errorBanner.hidden = true;
}

function formatSeconds(seconds) {
  if (seconds === null || seconds === undefined) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const minutes = Math.floor(seconds / 60);
  const remaining = Math.round(seconds % 60);
  return `${minutes}m ${remaining}s`;
}

function urgencyClass(value) {
  return `badge urgency-${value || "low"}`;
}

function selectedTicket() {
  return state.queue.find((ticket) => ticket.id === state.selectedId) || null;
}

function renderMetrics(metrics) {
  elements.acceptanceRate.textContent = `${metrics.review_actions.approved.percentage}%`;
  elements.averageReviewTime.textContent = formatSeconds(metrics.timing.human_review_time.avg_seconds);
  elements.ticketsWaiting.textContent = String(metrics.counts.by_status.analyzed);
}

function renderQueue() {
  elements.queueCount.textContent = String(state.queue.length);
  elements.queueList.replaceChildren();
  if (!state.queue.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "No analyzed tickets are waiting.";
    elements.queueList.append(empty);
    return;
  }
  for (const ticket of state.queue) {
    const item = document.createElement("button");
    item.type = "button";
    item.className = `queue-item${ticket.id === state.selectedId ? " selected" : ""}`;
    item.addEventListener("click", () => { state.selectedId = ticket.id; renderQueue(); renderTicket(); });

    const top = document.createElement("span");
    top.className = "queue-item-top";
    const subject = document.createElement("span");
    subject.className = "queue-subject";
    subject.textContent = ticket.subject;
    const urgency = document.createElement("span");
    urgency.className = urgencyClass(ticket.urgency);
    urgency.textContent = ticket.urgency || "unrated";
    const category = document.createElement("span");
    category.className = "queue-category";
    category.textContent = (ticket.category || "other").replaceAll("_", " ");
    top.append(subject, urgency);
    item.append(top, category);
    elements.queueList.append(item);
  }
}

function updateEditedButton() {
  const ticket = selectedTicket();
  const unchanged = !ticket || elements.reply.value.trim() === (ticket.ai_suggested_reply || "").trim();
  elements.edited.disabled = unchanged || !elements.reply.value.trim();
}

function renderTicket() {
  const ticket = selectedTicket();
  const hasTicket = Boolean(ticket);
  elements.emptyReview.hidden = hasTicket;
  elements.ticketReview.hidden = !hasTicket;
  if (!ticket) return;

  elements.subject.textContent = ticket.subject;
  elements.body.textContent = ticket.body;
  elements.summary.textContent = ticket.ai_summary || "No AI summary was returned.";
  elements.ticketUrgency.className = urgencyClass(ticket.ai_urgency || ticket.urgency);
  elements.ticketUrgency.textContent = ticket.ai_urgency || ticket.urgency || "unrated";
  elements.category.value = ticket.ai_category || "other";
  elements.urgency.value = ticket.ai_urgency || "low";
  elements.reply.value = ticket.ai_suggested_reply || "";
  updateEditedButton();
}

async function loadQueue(selectId = state.selectedId) {
  const queue = await api("/tickets/queue");
  state.queue = queue;
  state.selectedId = queue.some((ticket) => ticket.id === selectId) ? selectId : queue[0]?.id ?? null;
  renderQueue();
  renderTicket();
}

async function loadMetrics() {
  renderMetrics(await api("/metrics"));
}

async function loadDashboard() {
  try {
    await Promise.all([loadQueue(), loadMetrics()]);
    clearError();
  } catch (error) {
    showError(error.message, loadDashboard);
  }
}

function reviewerName() {
  const name = elements.reviewer.value.trim();
  if (!name) {
    showError("Enter your reviewer name before recording a decision.");
    return null;
  }
  localStorage.setItem("ticket-assistant-reviewer", name);
  return name;
}

function setReviewBusy(busy) {
  elements.approve.disabled = busy;
  elements.reject.disabled = busy;
  if (!busy) updateEditedButton();
}

async function submitReview(action) {
  const ticket = selectedTicket();
  const reviewer = reviewerName();
  if (!ticket || !reviewer) return;
  if (action === "edited" && (elements.reply.value.trim() === "" || elements.edited.disabled)) return;

  const payload = {
    action,
    reviewer,
    category: elements.category.value,
    urgency: elements.urgency.value,
  };
  if (action === "edited") payload.final_reply = elements.reply.value.trim();
  setReviewBusy(true);
  try {
    await api(`/tickets/${ticket.id}/review`, { method: "POST", body: JSON.stringify(payload) });
    await Promise.all([loadQueue(), loadMetrics()]);
    clearError();
  } catch (error) {
    showError(error.message, () => submitReview(action));
  } finally {
    setReviewBusy(false);
  }
}

async function analyzeExistingTicket(ticketId) {
  elements.analyze.disabled = true;
  elements.newStatus.textContent = "Analyzing ticket… this can take up to 30 seconds.";
  try {
    await api(`/tickets/${ticketId}/analyze`, { method: "POST" });
    await Promise.all([loadQueue(ticketId), loadMetrics()]);
    elements.newForm.reset();
    elements.newStatus.textContent = "Ticket analyzed and added to the review queue.";
    state.newTicketId = null;
    clearError();
  } catch (error) {
    showError(error.message, () => analyzeExistingTicket(ticketId));
    elements.newStatus.textContent = "Analysis did not complete.";
  } finally {
    elements.analyze.disabled = false;
  }
}

async function createAndAnalyze() {
  if (!elements.newForm.reportValidity()) return;
  elements.analyze.disabled = true;
  elements.newStatus.textContent = "Creating ticket…";
  try {
    const ticket = await api("/tickets", {
      method: "POST",
      body: JSON.stringify({ subject: elements.newSubject.value.trim(), body: elements.newBody.value.trim() }),
    });
    state.newTicketId = ticket.id;
    await analyzeExistingTicket(ticket.id);
  } catch (error) {
    showError(error.message, createAndAnalyze);
    elements.newStatus.textContent = "Ticket could not be created.";
    elements.analyze.disabled = false;
  }
}

elements.reply.addEventListener("input", updateEditedButton);
elements.approve.addEventListener("click", () => submitReview("approved"));
elements.edited.addEventListener("click", () => submitReview("edited"));
elements.reject.addEventListener("click", () => submitReview("rejected"));
elements.newForm.addEventListener("submit", (event) => { event.preventDefault(); createAndAnalyze(); });
elements.dismissError.addEventListener("click", clearError);
elements.retry.addEventListener("click", () => { if (state.retry) state.retry(); });
elements.reviewer.value = localStorage.getItem("ticket-assistant-reviewer") || "";

loadDashboard();
