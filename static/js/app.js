(() => {
  "use strict";

  /** @type {any} */
  let appData = null;

  const $ = (id) => document.getElementById(id);

  function setStatus(msg, type = "") {
    const el = $("status-msg");
    el.textContent = msg || "";
    el.className = "status" + (type ? ` ${type}` : "");
  }

  function chips(container, people) {
    container.innerHTML = "";
    (people || []).forEach((p) => {
      const li = document.createElement("li");
      li.className = "chip";
      li.textContent = p.name || p;
      container.appendChild(li);
    });
  }

  function spotLabel(type, config) {
    const spot = (config.spots || []).find((s) => s.type === type);
    return spot ? spot.label : type === "campus" ? "园区车位" : "公园车位";
  }

  function renderPeople(config) {
    chips($("people-list"), config.people);
  }

  function renderRules(config) {
    $("rules-text").textContent = config.rules_text || "";
  }

  function renderSpots(state, config) {
    const board = $("spot-board");
    board.innerHTML = "";
    const current = state && state.current;
    const assignments = current && current.assignments ? current.assignments : {};

    const campusIds = Object.keys(assignments).filter(
      (id) => assignments[id].spot === "campus"
    );
    const parkIds = Object.keys(assignments).filter(
      (id) => assignments[id].spot === "park"
    );

    for (let i = 0; i < 2; i++) {
      const div = document.createElement("div");
      div.className = "spot campus";
      const pid = campusIds[i];
      const name = pid ? assignments[pid].name : null;
      div.innerHTML = `<div class="spot-type">${spotLabel("campus", config)} ${i + 1}</div>
        <div class="occupant ${name ? "" : "empty"}">${name || "待分配"}</div>`;
      board.appendChild(div);
    }

    const parkDiv = document.createElement("div");
    parkDiv.className = "spot park";
    const parkId = parkIds[0];
    const parkName = parkId ? assignments[parkId].name : null;
    parkDiv.innerHTML = `<div class="spot-type">${spotLabel("park", config)}</div>
      <div class="occupant ${parkName ? "" : "empty"}">${parkName || "待分配"}</div>`;
    board.appendChild(parkDiv);
  }

  function renderPlates(state) {
    const current = state && state.current;
    if (!current) {
      chips($("campus-plates"), []);
      chips($("park-holder"), []);
      return;
    }
    chips($("campus-plates"), current.campus_plate_holders || []);
    chips($("park-holder"), current.park_holder ? [current.park_holder] : []);
  }

  function renderPools(pools, nextPeriod) {
    chips($("pool-must"), pools.must_win);
    chips($("pool-bye"), pools.bye);
    chips($("pool-candidate"), pools.candidate);
    $("next-period-hint").textContent = `即将进行第 ${nextPeriod} 次抽签（周期名将含当天日期与次数）`;
  }

  function renderDialogPools(pools, nextPeriod) {
    chips($("dialog-must"), pools.must_win);
    chips($("dialog-bye"), pools.bye);
    chips($("dialog-candidate"), pools.candidate);
    $("dialog-period").textContent = `确认后将产生第 ${nextPeriod} 次分配结果`;
  }

  function formatAssignments(result, config) {
    const rows = [];
    const assignments = result.assignments || {};
    Object.keys(assignments).forEach((id) => {
      const a = assignments[id];
      const label = spotLabel(a.spot, config);
      rows.push(`<div class="assign-row"><span>${a.name}</span><strong>${label}</strong></div>`);
    });
    return rows.join("");
  }

  function renderHistory(history, config) {
    const root = $("history-list");
    root.innerHTML = "";
    if (!history || !history.length) {
      root.innerHTML = '<p class="hint">暂无历史记录</p>';
      return;
    }
    [...history].reverse().forEach((entry) => {
      const details = document.createElement("details");
      details.className = "history-item";
      const summary = document.createElement("summary");
      summary.textContent = `${entry.period_label} · ${entry.drawn_at || ""}`;
      details.appendChild(summary);

      const detail = document.createElement("div");
      detail.className = "detail";
      const before = entry.pools_before || {};
      const after = entry.pools_after || {};
      const result = entry.result || {};
      detail.innerHTML = `
        <div>
          <h3>分配结果</h3>
          <div class="assign-list">${formatAssignments(result, config)}</div>
          <p class="meta-row">园区录牌：${(result.campus_plate_holders || []).map((p) => p.name).join("、") || "—"}</p>
          <p class="meta-row">公园位：${result.park_holder ? result.park_holder.name : "—"}</p>
        </div>
        <div class="pool-grid">
          <div class="pool pool-must"><h3>抽签前 · 必中</h3><ul class="chip-list" data-k="b-must"></ul></div>
          <div class="pool pool-bye"><h3>抽签前 · 轮空</h3><ul class="chip-list" data-k="b-bye"></ul></div>
          <div class="pool pool-candidate"><h3>抽签前 · 候选</h3><ul class="chip-list" data-k="b-cand"></ul></div>
        </div>
        <div class="pool-grid">
          <div class="pool pool-must"><h3>抽签后 · 必中</h3><ul class="chip-list" data-k="a-must"></ul></div>
          <div class="pool pool-bye"><h3>抽签后 · 轮空</h3><ul class="chip-list" data-k="a-bye"></ul></div>
          <div class="pool pool-candidate"><h3>抽签后 · 候选</h3><ul class="chip-list" data-k="a-cand"></ul></div>
        </div>
      `;
      details.appendChild(detail);
      root.appendChild(details);
      chips(detail.querySelector('[data-k="b-must"]'), before.must_win);
      chips(detail.querySelector('[data-k="b-bye"]'), before.bye);
      chips(detail.querySelector('[data-k="b-cand"]'), before.candidate);
      chips(detail.querySelector('[data-k="a-must"]'), after.must_win);
      chips(detail.querySelector('[data-k="a-bye"]'), after.bye);
      chips(detail.querySelector('[data-k="a-cand"]'), after.candidate);
    });
  }

  function renderSettings(config) {
    const wrap = $("settings-people");
    wrap.innerHTML = "";
    config.people.forEach((p) => {
      const label = document.createElement("label");
      label.className = "field";
      label.innerHTML = `${p.id}
        <input type="text" name="person-${p.id}" data-id="${p.id}" value="${escapeAttr(p.name)}" required />`;
      wrap.appendChild(label);
    });
    const campus = config.spots.find((s) => s.type === "campus");
    const park = config.spots.find((s) => s.type === "park");
    $("label-campus").value = campus ? campus.label : "园区车位";
    $("label-park").value = park ? park.label : "公园车位";
    $("rules-edit").value = config.rules_text || "";
  }

  function escapeAttr(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;");
  }

  function applyBootstrap(data) {
    appData = data;
    renderRules(data.config);
    renderPeople(data.config);
    renderSpots(data.state, data.config);
    renderPlates(data.state);
    renderPools(data.pools, data.next_period_number);
    renderHistory(data.history, data.config);
    renderSettings(data.config);
    $("btn-undo").disabled = !(data.history && data.history.length);
  }

  async function api(path, options = {}) {
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.error || `请求失败 (${res.status})`);
    }
    return data;
  }

  async function load() {
    setStatus("加载中…");
    try {
      const data = await api("/api/bootstrap");
      applyBootstrap(data);
      setStatus("已就绪", "ok");
    } catch (e) {
      setStatus(e.message, "error");
    }
  }

  function showResult(entry, config) {
    $("result-period").textContent = entry.period_label;
    const result = entry.result || {};
    $("result-body").innerHTML = `
      <div class="assign-list">${formatAssignments(result, config)}</div>
      <p class="meta-row">园区录牌：${(result.campus_plate_holders || []).map((p) => p.name).join("、")}</p>
      <p class="meta-row">公园位：${result.park_holder ? result.park_holder.name : "—"}</p>
    `;
    $("result-dialog").showModal();
  }

  $("btn-open-draw").addEventListener("click", async () => {
    try {
      const preview = await api("/api/pools");
      renderDialogPools(preview.pools, preview.next_period_number);
      $("draw-dialog").showModal();
    } catch (e) {
      setStatus(e.message, "error");
    }
  });

  $("btn-cancel-draw").addEventListener("click", () => {
    $("draw-dialog").close();
  });

  $("draw-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    $("draw-dialog").close();
    setStatus("抽签中…");
    try {
      const data = await api("/api/draw", { method: "POST", body: "{}" });
      applyBootstrap({
        config: data.config,
        state: data.state,
        history: data.history,
        pools: data.pools,
        next_period_number: data.next_period_number,
      });
      setStatus(`已完成 ${data.entry.period_label}`, "ok");
      showResult(data.entry, data.config);
    } catch (e) {
      setStatus(e.message, "error");
    }
  });

  $("btn-close-result").addEventListener("click", () => {
    $("result-dialog").close();
  });

  $("btn-undo").addEventListener("click", async () => {
    if (!confirm("确定撤销最近一次抽签？状态将回滚到该次之前。")) return;
    setStatus("撤销中…");
    try {
      const data = await api("/api/history/undo", { method: "POST", body: "{}" });
      applyBootstrap({
        config: data.config,
        state: data.state,
        history: data.history,
        pools: data.pools,
        next_period_number: data.next_period_number,
      });
      setStatus("已撤销最近一次抽签", "ok");
    } catch (e) {
      setStatus(e.message, "error");
    }
  });

  $("settings-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (!appData) return;
    const people = appData.config.people.map((p) => {
      const input = document.querySelector(`input[data-id="${p.id}"]`);
      return { id: p.id, name: (input && input.value.trim()) || p.name };
    });
    const payload = {
      people,
      spots: [
        { type: "campus", label: $("label-campus").value.trim(), count: 2 },
        { type: "park", label: $("label-park").value.trim(), count: 1 },
      ],
      rules_text: $("rules-edit").value,
    };
    setStatus("保存设置…");
    try {
      const data = await api("/api/config", {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      applyBootstrap(data);
      setStatus("设置已保存", "ok");
    } catch (e) {
      setStatus(e.message, "error");
    }
  });

  load();
})();
