/**
 * Crescendo PRD Multi-Turn Jailbreak Defense Testbench
 * Client-Side Controller & Telemetry Visualization
 */

(function () {
  'use strict';

  // Application State
  const state = {
    sessionId: 'session-' + Math.random().toString(36).substring(2, 9),
    scenarios: [],
    selectedScenario: null,
    scenarioTurnIndex: 0,
    isAutoPlaying: false,
    autoPlayTimer: null,
    history: [], // Array of turn records
    isProcessing: false
  };

  // DOM Elements
  const el = {
    systemStatusPill: document.getElementById('systemStatusPill'),
    systemStatusText: document.getElementById('systemStatusText'),
    resetSessionBtn: document.getElementById('resetSessionBtn'),
    scenarioSelect: document.getElementById('scenarioSelect'),
    loadScenarioBtn: document.getElementById('loadScenarioBtn'),
    stepTurnBtn: document.getElementById('stepTurnBtn'),
    autoRunBtn: document.getElementById('autoRunBtn'),
    scenarioCategoryTag: document.getElementById('scenarioCategoryTag'),
    scenarioTurnsCount: document.getElementById('scenarioTurnsCount'),
    activeSessionId: document.getElementById('activeSessionId'),
    currentTurnBadge: document.getElementById('currentTurnBadge').querySelector('span'),
    chatViewport: document.getElementById('chatViewport'),
    emptyChatState: document.getElementById('emptyChatState'),
    messagesList: document.getElementById('messagesList'),
    promptInput: document.getElementById('promptInput'),
    sendPromptBtn: document.getElementById('sendPromptBtn'),

    // Verdict Banner
    verdictBanner: document.getElementById('verdictBanner'),
    verdictIcon: document.getElementById('verdictIcon'),
    verdictTitle: document.getElementById('verdictTitle'),
    valCrs: document.getElementById('valCrs'),
    valMemory: document.getElementById('valMemory'),
    valThreshold: document.getElementById('valThreshold'),

    // Gauges
    gaugeValH: document.getElementById('gaugeValH'),
    gaugeBarH: document.getElementById('gaugeBarH'),
    gaugeValE: document.getElementById('gaugeValE'),
    gaugeBarE: document.getElementById('gaugeBarE'),
    gaugeValS: document.getElementById('gaugeValS'),
    gaugeBarS: document.getElementById('gaugeBarS'),
    gaugeValB: document.getElementById('gaugeValB'),
    gaugeBarB: document.getElementById('gaugeBarB'),

    // Trajectory Chart
    trajectoryCanvas: document.getElementById('trajectoryCanvas'),

    // Explainability & Latency
    explainConsole: document.getElementById('explainConsole'),
    totalLatencyText: document.getElementById('totalLatencyText'),
    segDrift: document.getElementById('segDrift'),
    segHarm: document.getElementById('segHarm'),
    segIntent: document.getElementById('segIntent'),
    segBypass: document.getElementById('segBypass')
  };

  // Canvas context
  let ctxChart = null;

  // Initialize
  function init() {
    el.activeSessionId.textContent = state.sessionId;
    if (el.trajectoryCanvas) {
      ctxChart = el.trajectoryCanvas.getContext('2d');
      drawTrajectoryChart();
    }

    bindEvents();
    fetchScenarios();
    fetchStatus();
  }

  function bindEvents() {
    // Reset Session
    el.resetSessionBtn.addEventListener('click', () => {
      resetSession();
    });

    // Scenario Selection
    el.scenarioSelect.addEventListener('change', onScenarioSelectChanged);
    el.loadScenarioBtn.addEventListener('click', loadSelectedScenario);
    el.stepTurnBtn.addEventListener('click', stepNextScenarioTurn);
    el.autoRunBtn.addEventListener('click', toggleAutoPlay);

    // Send Prompt
    el.sendPromptBtn.addEventListener('click', () => {
      const prompt = el.promptInput.value.trim();
      if (prompt) {
        processUserTurn(prompt);
      }
    });

    el.promptInput.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        const prompt = el.promptInput.value.trim();
        if (prompt) {
          processUserTurn(prompt);
        }
      }
    });

    // Handle Window Resize for Canvas
    window.addEventListener('resize', () => {
      drawTrajectoryChart();
    });
  }

  // API Calls
  async function fetchScenarios() {
    try {
      const res = await fetch('/api/scenarios');
      const data = await res.json();
      if (data.scenarios) {
        state.scenarios = data.scenarios;
        renderScenarioDropdown();
      }
    } catch (err) {
      console.warn('Failed to load preset scenarios:', err);
    }
  }

  async function fetchStatus() {
    try {
      const res = await fetch('/api/status');
      const data = await res.json();
      if (data.status === 'healthy') {
        el.systemStatusText.textContent = `PRD Active (λ=${data.config.memory_decay}, T₀=${data.config.restrict_threshold})`;
      }
    } catch (err) {
      el.systemStatusText.textContent = 'Server Offline';
      el.systemStatusPill.className = 'status-pill tag-attack';
    }
  }

  function renderScenarioDropdown() {
    el.scenarioSelect.innerHTML = '<option value="">-- Choose a Preset Attack or Benign Conversation --</option>';

    const attackGroup = document.createElement('optgroup');
    attackGroup.label = '⚡ Multi-Turn Crescendo Attacks';

    const benignGroup = document.createElement('optgroup');
    benignGroup.label = '🟢 Benign Reference Dialogues';

    state.scenarios.forEach((sc, idx) => {
      const opt = document.createElement('option');
      opt.value = idx;
      opt.textContent = `[${sc.id}] ${sc.name} (${sc.turns.length} turns)`;
      if (sc.type === 'attack') {
        attackGroup.appendChild(opt);
      } else {
        benignGroup.appendChild(opt);
      }
    });

    el.scenarioSelect.appendChild(attackGroup);
    el.scenarioSelect.appendChild(benignGroup);
  }

  function onScenarioSelectChanged() {
    const idx = el.scenarioSelect.value;
    if (idx !== '') {
      state.selectedScenario = state.scenarios[idx];
      el.loadScenarioBtn.disabled = false;
      el.scenarioCategoryTag.textContent = state.selectedScenario.category;
      el.scenarioCategoryTag.className = 'meta-tag ' + (state.selectedScenario.type === 'attack' ? 'tag-attack' : 'tag-benign');
    } else {
      state.selectedScenario = null;
      el.loadScenarioBtn.disabled = true;
      el.stepTurnBtn.disabled = true;
      el.autoRunBtn.disabled = true;
      el.scenarioCategoryTag.textContent = 'Custom Session';
      el.scenarioCategoryTag.className = 'meta-tag tag-neutral';
    }
  }

  async function loadSelectedScenario() {
    if (!state.selectedScenario) return;
    await resetSession();
    state.scenarioTurnIndex = 0;
    updateScenarioMeta();
    el.stepTurnBtn.disabled = false;
    el.autoRunBtn.disabled = false;

    // Prefill first prompt in textarea
    if (state.selectedScenario.turns.length > 0) {
      el.promptInput.value = state.selectedScenario.turns[0];
    }
  }

  function updateScenarioMeta() {
    if (!state.selectedScenario) {
      el.scenarioTurnsCount.textContent = `${state.history.length} turns played`;
      return;
    }
    const total = state.selectedScenario.turns.length;
    el.scenarioTurnsCount.textContent = `${state.scenarioTurnIndex} / ${total} turns played`;
  }

  async function stepNextScenarioTurn() {
    if (!state.selectedScenario) return;
    if (state.scenarioTurnIndex >= state.selectedScenario.turns.length) {
      alert('All turns of this scenario have been executed.');
      return;
    }

    const nextPrompt = state.selectedScenario.turns[state.scenarioTurnIndex];
    state.scenarioTurnIndex++;
    updateScenarioMeta();

    await processUserTurn(nextPrompt);

    // Prefill next prompt if available
    if (state.scenarioTurnIndex < state.selectedScenario.turns.length) {
      el.promptInput.value = state.selectedScenario.turns[state.scenarioTurnIndex];
    } else {
      el.promptInput.value = '';
      el.stepTurnBtn.disabled = true;
      stopAutoPlay();
    }
  }

  function toggleAutoPlay() {
    if (state.isAutoPlaying) {
      stopAutoPlay();
    } else {
      startAutoPlay();
    }
  }

  function startAutoPlay() {
    if (!state.selectedScenario) return;
    state.isAutoPlaying = true;
    el.autoRunBtn.innerHTML = '<span class="btn-icon">⏸</span> Pause Auto-Play';
    el.autoRunBtn.className = 'btn btn-secondary btn-sm';
    runAutoPlayStep();
  }

  function stopAutoPlay() {
    state.isAutoPlaying = false;
    if (state.autoPlayTimer) {
      clearTimeout(state.autoPlayTimer);
      state.autoPlayTimer = null;
    }
    el.autoRunBtn.innerHTML = '<span class="btn-icon">⚡</span> Auto-Play Scenario';
    el.autoRunBtn.className = 'btn btn-accent btn-sm';
  }

  async function runAutoPlayStep() {
    if (!state.isAutoPlaying) return;
    if (state.scenarioTurnIndex >= state.selectedScenario.turns.length) {
      stopAutoPlay();
      return;
    }

    await stepNextScenarioTurn();

    // Check if the last turn was BLOCKED; if so, highlight interception and halt autoplay
    const lastTurn = state.history[state.history.length - 1];
    if (lastTurn && lastTurn.decision === 'BLOCK') {
      stopAutoPlay();
      return;
    }

    if (state.isAutoPlaying && state.scenarioTurnIndex < state.selectedScenario.turns.length) {
      state.autoPlayTimer = setTimeout(runAutoPlayStep, 1800);
    } else {
      stopAutoPlay();
    }
  }

  // Turn Processing
  async function processUserTurn(prompt) {
    if (state.isProcessing) return;
    state.isProcessing = true;
    setControlsLoading(true);

    try {
      const res = await fetch('/api/turn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: state.sessionId,
          prompt: prompt
        })
      });

      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }

      const turnData = await res.json();
      handleTurnSuccess(turnData);
    } catch (err) {
      alert(`Error processing turn: ${err.message}`);
      console.error(err);
    } finally {
      state.isProcessing = false;
      setControlsLoading(false);
    }
  }

  function handleTurnSuccess(turnData) {
    state.history.push(turnData);

    // Hide empty placeholder if visible
    if (el.emptyChatState) {
      el.emptyChatState.style.display = 'none';
    }

    // Append message to conversation stream
    appendTurnToChat(turnData);

    // Update Telemetry Displays
    updateVerdictBanner(turnData);
    updateGauges(turnData.signals);
    updateExplainability(turnData);
    updateLatency(turnData.latency_ms);
    drawTrajectoryChart();

    // Update Turn Badge
    el.currentTurnBadge.textContent = turnData.turn_number;

    // Scroll chat to bottom
    el.chatViewport.scrollTo({
      top: el.chatViewport.scrollHeight,
      behavior: 'smooth'
    });

    // Clear user input
    el.promptInput.value = '';
  }

  function appendTurnToChat(turnData) {
    const card = document.createElement('div');
    card.className = 'message-turn-card';

    const decisionClass = `verdict-${turnData.decision.toLowerCase()}-badge`;
    const isBlocked = turnData.decision === 'BLOCK';

    card.innerHTML = `
      <div class="turn-header">
        <span class="turn-tag">TURN ${turnData.turn_number}</span>
        <span class="turn-verdict ${decisionClass}">${turnData.decision}</span>
      </div>
      <div class="bubble-user">
        <div class="bubble-role">USER</div>
        <div class="bubble-content">${escapeHtml(turnData.prompt)}</div>
      </div>
      <div class="bubble-assistant ${isBlocked ? 'blocked' : ''}">
        <div class="bubble-role">${isBlocked ? '🛡️ DEFENSE SYSTEM INTERCEPT' : 'ASSISTANT'}</div>
        <div class="bubble-content">${escapeHtml(turnData.response)}</div>
      </div>
    `;

    el.messagesList.appendChild(card);
  }

  function updateVerdictBanner(turnData) {
    const dec = turnData.decision;
    el.verdictBanner.className = `verdict-banner verdict-${dec.toLowerCase()}`;
    el.verdictTitle.textContent = dec;

    if (dec === 'BLOCK') {
      el.verdictIcon.textContent = '⛔';
    } else if (dec === 'RESTRICT') {
      el.verdictIcon.textContent = '⚠️';
    } else if (dec === 'WARN') {
      el.verdictIcon.textContent = '👁️';
    } else {
      el.verdictIcon.textContent = '✅';
    }

    el.valCrs.textContent = turnData.signals.CRS.toFixed(3);
    el.valMemory.textContent = turnData.signals.C_t.toFixed(3);
    el.valThreshold.textContent = turnData.signals.T_t.toFixed(3);
  }

  function updateGauges(signals) {
    // H
    el.gaugeValH.textContent = signals.H.toFixed(3);
    el.gaugeBarH.style.width = Math.min(100, signals.H * 100) + '%';

    // E
    el.gaugeValE.textContent = signals.E.toFixed(3);
    el.gaugeBarE.style.width = Math.min(100, signals.E * 100) + '%';

    // S
    el.gaugeValS.textContent = signals.S.toFixed(3);
    el.gaugeBarS.style.width = Math.min(100, signals.S * 100) + '%';

    // B
    el.gaugeValB.textContent = signals.B.toFixed(3);
    el.gaugeBarB.style.width = Math.min(100, signals.B * 100) + '%';
  }

  function updateExplainability(turnData) {
    if (turnData.explanation) {
      el.explainConsole.textContent = turnData.explanation.trim();
    }
  }

  function updateLatency(latencies) {
    if (!latencies) return;
    const total = latencies.total_turn_latency_ms || 0.0;
    el.totalLatencyText.textContent = `${total.toFixed(1)} ms`;

    const d = latencies.semantic_drift_s_ms || 0.1;
    const h = latencies.harmfulness_h_ms || 0.1;
    const e = latencies.intent_escalation_e_ms || 0.1;
    const b = latencies.bypass_detection_b_ms || latencies.refusal_bypass_b_ms || 0.1;

    const sum = d + h + e + b || 1.0;
    el.segDrift.style.width = ((d / sum) * 100).toFixed(1) + '%';
    el.segHarm.style.width = ((h / sum) * 100).toFixed(1) + '%';
    el.segIntent.style.width = ((e / sum) * 100).toFixed(1) + '%';
    el.segBypass.style.width = ((b / sum) * 100).toFixed(1) + '%';
  }

  // Draw Multi-Turn Trajectory Graph
  function drawTrajectoryChart() {
    if (!ctxChart || !el.trajectoryCanvas) return;

    const canvas = el.trajectoryCanvas;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * (window.devicePixelRatio || 1);
    canvas.height = rect.height * (window.devicePixelRatio || 1);

    const ctx = ctxChart;
    const w = canvas.width;
    const h = canvas.height;

    ctx.clearRect(0, 0, w, h);

    const padLeft = 45 * (window.devicePixelRatio || 1);
    const padRight = 20 * (window.devicePixelRatio || 1);
    const padTop = 20 * (window.devicePixelRatio || 1);
    const padBottom = 30 * (window.devicePixelRatio || 1);

    const plotW = w - padLeft - padRight;
    const plotH = h - padTop - padBottom;

    // Grid & Y-Axis (0.0 to 1.0)
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
    ctx.lineWidth = 1;
    ctx.font = `${10 * (window.devicePixelRatio || 1)}px JetBrains Mono, monospace`;
    ctx.fillStyle = '#64748b';

    for (let level = 0; level <= 1.0; level += 0.25) {
      const y = padTop + plotH * (1 - level);
      ctx.beginPath();
      ctx.moveTo(padLeft, y);
      ctx.lineTo(w - padRight, y);
      ctx.stroke();

      ctx.fillText(level.toFixed(2), padLeft - (34 * (window.devicePixelRatio || 1)), y + (4 * (window.devicePixelRatio || 1)));
    }

    if (state.history.length === 0) {
      ctx.fillStyle = '#475569';
      ctx.textAlign = 'center';
      ctx.fillText('Trajectory lines will plot here as turns progress...', w / 2, h / 2);
      ctx.textAlign = 'left';
      return;
    }

    const n = Math.max(state.history.length, 5);
    const xStep = plotW / (n > 1 ? n - 1 : 1);

    // Helper to map (turnIndex, value) to pixel (x, y)
    function getCoords(turnIdx, val) {
      const clampedVal = Math.max(0, Math.min(1.0, val));
      const x = padLeft + turnIdx * xStep;
      const y = padTop + plotH * (1 - clampedVal);
      return { x, y };
    }

    // X-Axis Turn Labels
    ctx.fillStyle = '#64748b';
    for (let i = 0; i < state.history.length; i++) {
      const pt = getCoords(i, 0);
      ctx.fillText(`T${i + 1}`, pt.x - (8 * (window.devicePixelRatio || 1)), h - (10 * (window.devicePixelRatio || 1)));
    }

    // 1. Draw Dynamic Threshold Line (Crimson Dashed)
    ctx.save();
    ctx.strokeStyle = '#ef4444';
    ctx.lineWidth = 2 * (window.devicePixelRatio || 1);
    ctx.setLineDash([4 * (window.devicePixelRatio || 1), 4 * (window.devicePixelRatio || 1)]);
    ctx.beginPath();
    state.history.forEach((turn, idx) => {
      const { x, y } = getCoords(idx, turn.signals.T_t || 0.75);
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.restore();

    // 2. Draw CRS Line (Cyan)
    ctx.strokeStyle = '#38bdf8';
    ctx.lineWidth = 2.2 * (window.devicePixelRatio || 1);
    ctx.beginPath();
    state.history.forEach((turn, idx) => {
      const { x, y } = getCoords(idx, turn.signals.CRS);
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // 3. Draw Contextual Memory Line (Amber Glowing)
    ctx.strokeStyle = '#f59e0b';
    ctx.lineWidth = 2.8 * (window.devicePixelRatio || 1);
    ctx.beginPath();
    state.history.forEach((turn, idx) => {
      const { x, y } = getCoords(idx, turn.signals.C_t);
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Draw Data Dots & Interception Beacons
    state.history.forEach((turn, idx) => {
      // Memory dot
      const ptMem = getCoords(idx, turn.signals.C_t);
      ctx.fillStyle = '#f59e0b';
      ctx.beginPath();
      ctx.arc(ptMem.x, ptMem.y, 4 * (window.devicePixelRatio || 1), 0, Math.PI * 2);
      ctx.fill();

      // If BLOCKED, draw interception beacon halo
      if (turn.decision === 'BLOCK') {
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 3 * (window.devicePixelRatio || 1);
        ctx.beginPath();
        ctx.arc(ptMem.x, ptMem.y, 9 * (window.devicePixelRatio || 1), 0, Math.PI * 2);
        ctx.stroke();

        ctx.fillStyle = '#ef4444';
        ctx.font = `bold ${10 * (window.devicePixelRatio || 1)}px JetBrains Mono, monospace`;
        ctx.fillText('⚡ INTERCEPTED', ptMem.x - (38 * (window.devicePixelRatio || 1)), ptMem.y - (14 * (window.devicePixelRatio || 1)));
      }
    });
  }

  async function resetSession() {
    stopAutoPlay();
    state.sessionId = 'session-' + Math.random().toString(36).substring(2, 9);
    el.activeSessionId.textContent = state.sessionId;
    state.history = [];
    state.scenarioTurnIndex = 0;

    try {
      await fetch('/api/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: state.sessionId })
      });
    } catch (e) {
      console.warn('Reset error:', e);
    }

    // Reset UI Elements
    el.messagesList.innerHTML = '';
    if (el.emptyChatState) {
      el.emptyChatState.style.display = 'flex';
    }

    el.verdictBanner.className = 'verdict-banner verdict-idle';
    el.verdictIcon.textContent = '⚡';
    el.verdictTitle.textContent = 'IDLE / READY';
    el.valCrs.textContent = '0.000';
    el.valMemory.textContent = '0.000';
    el.valThreshold.textContent = '0.750';

    updateGauges({ H: 0, E: 0, S: 0, B: 0 });
    el.explainConsole.textContent = 'Awaiting conversation turn input...';
    el.totalLatencyText.textContent = '0.0 ms';
    el.currentTurnBadge.textContent = '0';
    updateScenarioMeta();

    drawTrajectoryChart();
  }

  function setControlsLoading(isLoading) {
    el.sendPromptBtn.disabled = isLoading;
    el.stepTurnBtn.disabled = isLoading || !state.selectedScenario;
    if (isLoading) {
      el.sendPromptBtn.innerHTML = '<span>Processing...</span>';
    } else {
      el.sendPromptBtn.innerHTML = '<span>Send Turn</span><span class="btn-arrow">→</span>';
    }
  }

  function escapeHtml(str) {
    return (str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
