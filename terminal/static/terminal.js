/* WarSignal Terminal — plain JS, no dependencies. */
(function () {
  "use strict";

  var S = window.__STATE__ || null;
  var SNAPSHOT = !!window.__STATE__;
  var pane = 0;                    // 0 active,1 queue,2 history,3 leaderboard,4 log
  var sel = 0;                     // selected row in current pane
  var filter = "";
  var histSort = { key: "folder", asc: false };
  var detailOpen = false;

  var PANES = ["ACTIVE", "QUEUE", "HISTORY", "LEADERBOARD", "LOG"];

  var elTicker = document.getElementById("ticker");
  var elTabs = document.getElementById("tabs");
  var elPane = document.getElementById("pane");
  var elDetail = document.getElementById("detail");
  var elFilter = document.getElementById("filter");

  function esc(v) {
    return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function num(v, d) {
    if (v === null || v === undefined || v === "" || isNaN(v)) return '<span class="dim">·</span>';
    return esc(Number(v).toFixed(d === undefined ? 3 : d));
  }
  function pnum(v) { return num(v, 4); }
  function trunc(v, n) {
    v = v == null ? "" : String(v);
    return v.length > n ? v.slice(0, n - 1) + "…" : v;
  }
  function mmss(sec) {
    sec = Math.max(0, Math.floor(sec || 0));
    var m = Math.floor(sec / 60), s = sec % 60;
    return (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
  }
  function hhmmssz(iso) {
    if (!iso) return "--:--:--";
    var d = new Date(iso);
    if (isNaN(d)) return "--:--:--";
    function p(x) { return (x < 10 ? "0" : "") + x; }
    return p(d.getUTCHours()) + ":" + p(d.getUTCMinutes()) + ":" + p(d.getUTCSeconds()) + "Z";
  }
  function sigColor(sig) {
    if (sig === null || sig === undefined) return "#5a6270";
    var r = Math.round(248 + (63 - 248) * sig);
    var g = Math.round(81 + (185 - 81) * sig);
    var b = Math.round(73 + (80 - 73) * sig);
    return "rgb(" + r + "," + g + "," + b + ")";
  }
  function bar(progress, signal, label) {
    var w = Math.round(Math.max(0, Math.min(1, progress || 0)) * 100);
    return '<span class="pbar"><i style="width:' + w + '%;background:' + sigColor(signal) + '"></i></span>' +
      '<span class="pct">' + esc(label == null ? w + "%" : label) + "</span>";
  }
  function isFiniteNum(v) { return v !== null && v !== undefined && v !== "" && !isNaN(v); }

  /* ---------- ticker ---------- */
  function tick() {
    if (!S) { elTicker.textContent = "WARSIGNAL TERMINAL — connecting…"; return; }
    var c = S.counts || {};
    var g = S.git || {};
    var maxA = (S.config && S.config.max_agents) || 0;
    var parts = [
      "WARSIGNAL TERMINAL" + (SNAPSHOT ? " [SNAPSHOT]" : ""),
      "RUN " + (c.running || 0) + "/" + maxA,
      "QUEUE " + (c.queued || 0),
      "DONE " + (c.done || 0),
      "FAIL " + (c.failed || 0),
      "HEAD " + (g.head || "?") + " " + (g.branch || "")
    ];
    if (SNAPSHOT) {
      // static export: nothing pulls
    } else if (!S.pull_enabled) {
      parts.push("PULL OFF");
    } else {
      parts.push("PULL " + (g.last_pull_at
        ? hhmmssz(g.last_pull_at) + " " + (g.last_pull_ok === false ? "FAIL" : "OK")
        : "pending"));
      var since = g.last_pull_at ? (Date.now() - Date.parse(g.last_pull_at)) / 1000 : 1e9;
      var next = Math.max(0, Math.round((S.pull_interval || 60) - since));
      parts.push("NEXT " + next + "s");
    }
    elTicker.textContent = parts.join(" │ ");
  }

  /* ---------- rows ---------- */
  function brainLinks(s) {
    var out = [];
    if (s.agent_session_url) out.push('<a href="' + esc(s.agent_session_url) + '" target="_blank">agent</a>');
    (s.brain_sessions || []).forEach(function (b, i) {
      if (b.session_url) out.push('<a href="' + esc(b.session_url) + '" target="_blank">' + esc(b.purpose || "brain" + (i + 1)) + "</a>");
    });
    return out.join(" ");
  }
  function elapsedNow(s) {
    var e = s.elapsed_s || 0;
    if (s.state === "running" && S.generated_ts)
      e += Math.max(0, Date.now() / 1000 - S.generated_ts);
    return e;
  }

  function rowsActive() {
    return (S.active || []).map(function (s) {
      var title = s.title || trunc(s.hypothesis, 60);
      return {
        folder: s.run_folder ? s.run_folder.split("/").pop() : null,
        text: [s.mission_id, title, s.stage, s.message].join(" "),
        html: "<td>" + esc(s.mission_id) + "</td><td>" + esc(trunc(title, 52)) + "</td><td>" +
          esc(s.stage || "") + "</td><td>" + mmss(elapsedNow(s)) + "</td><td>" +
          bar(s.progress, s.signal) + "</td><td class='wrap'>" + esc(trunc(s.message, 60)) +
          "</td><td>" + brainLinks(s) + "</td>"
      };
    });
  }
  function rowsQueue() {
    return (S.queue || []).map(function (q) {
      return {
        text: [q.position, q.round, q.parent_id, q.hypothesis].join(" "),
        html: "<td>" + esc(q.position) + "</td><td>" + esc(q.round) + "</td><td>" +
          esc(q.parent_id) + "</td><td class='wrap'>" + esc(q.hypothesis) + "</td>"
      };
    });
  }
  var HIST_COLS = [
    ["folder", "FOLDER"], ["status", "STATUS"], ["n", "N"], ["r", "R"],
    ["perm_p", "PERM_P"], ["bonferroni_ok", "BONF"], ["validity", "VALID"],
    ["interestingness", "INTEREST"], ["unexpectedness", "UNEXPECT"],
    ["actionability", "ACTION"], ["hypothesis", "HYPOTHESIS"]
  ];
  function sortedRuns() {
    var runs = (S.runs || []).slice();
    var k = histSort.key, asc = histSort.asc ? 1 : -1;
    runs.sort(function (a, b) {
      var x = a[k], y = b[k];
      if (x === null || x === undefined) x = "";
      if (y === null || y === undefined) y = "";
      if (typeof x === "number" && typeof y === "number") return (x - y) * asc;
      return String(x).localeCompare(String(y)) * asc;
    });
    return runs;
  }
  function rowsHistory() {
    return sortedRuns().map(function (r) {
      var st = r.status === "ok" ? '<span class="good">ok</span>' :
        (r.status === "failed" ? '<span class="bad">fail</span>' : esc(r.status));
      return {
        folder: r.folder,
        text: [r.folder, r.status, r.hypothesis].join(" "),
        html: '<td title="' + esc(r.folder) + '">' + esc(String(r.folder || "").slice(0, 12)) + "</td><td>" + st + "</td><td>" + num(r.n, 0) +
          "</td><td>" + num(r.r) + "</td><td>" + pnum(r.perm_p) + "</td><td>" +
          (r.bonferroni_ok ? '<span class="good">✓</span>' : '<span class="dim">·</span>') +
          "</td><td>" + num(r.validity, 2) + "</td><td>" + num(r.interestingness, 2) +
          "</td><td>" + num(r.unexpectedness, 2) + "</td><td>" + num(r.actionability, 2) +
          "</td><td class='wrap'>" + esc(trunc(r.hypothesis, 70)) + "</td>"
      };
    });
  }
  function tradeSummary(t) {
    if (!t || typeof t !== "object") return "";
    var bits = [];
    if (t.instrument) bits.push(t.instrument);
    if (t.direction) bits.push(t.direction);
    if (isFiniteNum(t.holding_days)) bits.push(t.holding_days + "d");
    return bits.join(" ");
  }
  function rowsLeaderboard() {
    return (S.leaderboard || []).map(function (r) {
      return {
        folder: r.folder,
        text: [r.mission_id, r.hypothesis, tradeSummary(r.trade_idea)].join(" "),
        html: "<td>" + esc(r.rank) + "</td><td>" + esc(r.mission_id || trunc(r.folder, 16)) +
          "</td><td>" + num(r.validity, 2) + "</td><td>" + num(r.effect) + "</td><td>" +
          num(r.n, 0) + "</td><td>" + pnum(r.perm_p) + "</td><td>" +
          (r.bonferroni_ok ? '<span class="good">✓</span>' : '<span class="dim">·</span>') +
          "</td><td>" + num(r.actionability, 2) + "</td><td>" + esc(trunc(tradeSummary(r.trade_idea), 24)) +
          "</td><td class='wrap'>" + esc(trunc(r.hypothesis, 60)) + "</td>"
      };
    });
  }
  function rowsLog() {
    return (S.log || []).map(function (e) {
      var change = e.field ? esc(e.old) + " → " + esc(e.new) : esc(e.new || e.old || "");
      return {
        text: [e.at, e.mission_id, e.kind, e.field, e.old, e.new, e.message].join(" "),
        html: "<td>" + esc((e.at || "").slice(11, 19)) + "</td><td>" + esc(e.mission_id) +
          "</td><td>" + esc(e.kind) + "</td><td>" + esc(e.field || "") + "</td><td>" + change +
          "</td><td class='wrap'>" + esc(trunc(e.message, 60)) + "</td>"
      };
    });
  }

  var HEADERS = [
    "<tr><th>ID</th><th>TITLE</th><th>STAGE</th><th>ELAPSED</th><th>PROGRESS</th><th>LAST MESSAGE</th><th>LINKS</th></tr>",
    "<tr><th>POS</th><th>ROUND</th><th>PARENT</th><th>HYPOTHESIS</th></tr>",
    null,
    "<tr><th>RANK</th><th>MISSION</th><th>VALID</th><th>EFFECT</th><th>N</th><th>PERM_P</th><th>BONF</th><th>ACTION</th><th>TRADE</th><th>HYPOTHESIS</th></tr>",
    "<tr><th>TIME</th><th>MISSION</th><th>KIND</th><th>FIELD</th><th>OLD→NEW</th><th>MESSAGE</th></tr>"
  ];
  var ROWFNS = [rowsActive, rowsQueue, rowsHistory, rowsLeaderboard, rowsLog];
  var EMPTY = [
    "NO ACTIVE AGENTS — waiting for missions/status/*.json",
    "QUEUE EMPTY", "NO RUNS", "NO SCORED RUNS", "NO EVENTS"
  ];

  function historyHeader() {
    var h = "<tr>";
    HIST_COLS.forEach(function (c) {
      var arrow = histSort.key === c[0] ? (histSort.asc ? " ▲" : " ▼") : "";
      h += '<th data-col="' + c[0] + '">' + c[1] + arrow + "</th>";
    });
    return h + "</tr>";
  }

  function render() {
    if (!S) return;
    var rows = ROWFNS[pane]();
    if (filter) {
      var f = filter.toLowerCase();
      rows = rows.filter(function (r) { return r.text.toLowerCase().indexOf(f) >= 0; });
    }
    if (sel >= rows.length) sel = Math.max(0, rows.length - 1);
    if (!rows.length) {
      elPane.innerHTML = '<div class="empty">' + esc(EMPTY[pane]) + "</div>";
      return;
    }
    var head = pane === 2 ? historyHeader() : HEADERS[pane];
    var body = rows.map(function (r, i) {
      return '<tr class="' + (i === sel ? "sel" : "") + '" data-folder="' + esc(r.folder || "") + '">' + r.html + "</tr>";
    }).join("");
    elPane.innerHTML = "<table>" + head + body + "</table>";
    if (pane === 2) {
      Array.prototype.forEach.call(elPane.querySelectorAll("th[data-col]"), function (th) {
        th.addEventListener("click", function () {
          var col = th.getAttribute("data-col");
          if (histSort.key === col) histSort.asc = !histSort.asc;
          else { histSort.key = col; histSort.asc = col === "folder" ? false : true; }
          render();
        });
      });
    }
    Array.prototype.forEach.call(elPane.querySelectorAll("tr[data-folder]"), function (tr) {
      tr.addEventListener("click", function () {
        var f = tr.getAttribute("data-folder");
        if (f) openDetail(f);
      });
    });
  }

  /* ---------- minimal markdown ---------- */
  function md(src) {
    var lines = String(src || "").split("\n");
    var out = [], inTable = false, para = [];
    function inline(t) {
      t = esc(t);
      t = t.replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
      t = t.replace(/`([^`]+)`/g, "<code>$1</code>");
      return t;
    }
    function flushPara() {
      if (para.length) { out.push("<p>" + para.map(inline).join(" ") + "</p>"); para = []; }
    }
    function flushTable() { if (inTable) { out.push("</table>"); inTable = false; } }
    lines.forEach(function (line) {
      var t = line.trim();
      if (/^\|.*\|$/.test(t)) {
        flushPara();
        var cells = t.slice(1, -1).split("|").map(function (c) { return c.trim(); });
        if (cells.every(function (c) { return /^:?-{2,}:?$/.test(c); })) return;
        if (!inTable) { out.push("<table>"); inTable = true; }
        out.push("<tr>" + cells.map(function (c) { return "<td>" + inline(c) + "</td>"; }).join("") + "</tr>");
        return;
      }
      flushTable();
      if (/^#{1,6}\s/.test(t)) { flushPara(); out.push("<h3>" + inline(t.replace(/^#+\s*/, "")) + "</h3>"); }
      else if (!t) flushPara();
      else para.push(t);
    });
    flushPara(); flushTable();
    return out.join("\n");
  }

  /* ---------- detail pane ---------- */
  function kvTable(obj) {
    if (!obj || typeof obj !== "object") return '<span class="dim">·</span>';
    var rows = Object.keys(obj).map(function (k) {
      var v = obj[k];
      if (v && typeof v === "object") v = JSON.stringify(v);
      return "<tr><td>" + esc(k) + "</td><td>" + esc(v == null ? "" : v) + "</td></tr>";
    }).join("");
    return '<table class="kv">' + rows + "</table>";
  }
  function openDetail(folder) {
    var get;
    if (SNAPSHOT) {
      get = new Promise(function (res, rej) {
        var d = (S.run_details || {})[folder];
        d ? res(d) : rej(new Error("no detail"));
      });
    } else {
      get = fetch("/api/run/" + encodeURIComponent(folder)).then(function (r) {
        if (!r.ok) throw new Error("404");
        return r.json();
      });
    }
    get.then(function (d) {
      detailOpen = true;
      var h = "<h2>" + esc(d.folder) + "</h2>";
      h += '<div class="meta">' + esc(d.mission_id || "") + " · " + esc(d.status || "") +
        " · " + esc((d.coverage_start || "") + " → " + (d.coverage_end || "")) + "</div>";
      var st = (S.statuses || []).filter(function (s) {
        return s.mission_id === d.mission_id || (s.run_folder || "").split("/").pop() === d.folder;
      })[0];
      var links = st ? brainLinks(st) : "";
      if (links) h += '<div class="meta links">' + links + "</div>";
      if (d.hypothesis) h += "<p>" + esc(d.hypothesis) + "</p>";
      h += "<h3>Stats</h3><table>" +
        "<tr><th>n_obs</th><th>pearson_r</th><th>spearman_r</th><th>best_lag</th><th>best_r</th><th>perm_p</th><th>bonferroni_p</th><th>lags</th><th>window</th></tr>" +
        "<tr><td>" + num(d.n_obs, 0) + "</td><td>" + num(d.pearson_r) + "</td><td>" + num(d.spearman_r) +
        "</td><td>" + num(d.best_lag, 0) + "</td><td>" + num(d.best_r) + "</td><td>" + pnum(d.perm_p) +
        "</td><td>" + pnum(d.bonferroni_p) + "</td><td>" + num(d.n_lags_tested, 0) + "</td><td>" + esc(d.window || "") + "</td></tr></table>";
      if (d.scores) {
        h += "<h3>Scores</h3><table><tr><th>validity</th><th>interesting</th><th>unexpected</th><th>actionable</th><th>supported_p</th><th>model</th></tr><tr><td>" +
          num(d.scores.validity, 2) + "</td><td>" + num(d.scores.interestingness, 2) + "</td><td>" +
          num(d.scores.unexpectedness, 2) + "</td><td>" + num(d.scores.actionability, 2) + "</td><td>" +
          num(d.scores.supported_prob, 2) + "</td><td>" + esc(d.scores.judge_model || "") + "</td></tr></table>";
      }
      if (d.trade_idea) h += "<h3>Trade idea</h3>" + kvTable(d.trade_idea);
      if (d.has_viz) {
        h += SNAPSHOT ? '<h3>Viz</h3><p class="dim">viz.png not embedded in snapshot</p>'
          : '<h3>Viz</h3><img src="/runs/' + encodeURIComponent(d.folder) + '/viz.png">';
      }
      if (d.note_md) h += '<h3>Note</h3><div class="note">' + md(d.note_md) + "</div>";
      elDetail.innerHTML = h;
      elDetail.classList.remove("hidden");
    }).catch(function () { });
  }
  function closeDetail() { detailOpen = false; elDetail.classList.add("hidden"); }

  /* ---------- tabs ---------- */
  function renderTabs() {
    elTabs.innerHTML = PANES.map(function (name, i) {
      return '<span class="tab' + (i === pane ? " active" : "") + '" data-i="' + i + '">' +
        (i + 1) + " " + name + "</span>";
    }).join("");
    Array.prototype.forEach.call(elTabs.querySelectorAll(".tab"), function (t) {
      t.addEventListener("click", function () {
        pane = parseInt(t.getAttribute("data-i"), 10); sel = 0; renderTabs(); render();
      });
    });
  }

  /* ---------- keys ---------- */
  document.addEventListener("keydown", function (e) {
    if (e.target === elFilter) {
      if (e.key === "Escape") { elFilter.value = ""; filter = ""; elFilter.blur(); render(); }
      return;
    }
    var k = e.key;
    if (k === "Escape") {
      if (detailOpen) closeDetail();
      else if (filter) { elFilter.value = ""; filter = ""; render(); }
      return;
    }
    if (k === "/") { e.preventDefault(); elFilter.focus(); return; }
    if (k === "r" || k === "F5") {
      if (!SNAPSHOT) {
        e.preventDefault();
        fetch("/api/state?refresh=1").then(function (r) { return r.json(); }).then(function (x) { S = x; render(); });
      }
      return;
    }
    if (k >= "1" && k <= "5") { pane = parseInt(k, 10) - 1; sel = 0; renderTabs(); render(); return; }
    if (k === "j" || k === "ArrowDown") { sel++; render(); e.preventDefault(); return; }
    if (k === "k" || k === "ArrowUp") { sel = Math.max(0, sel - 1); render(); e.preventDefault(); return; }
    if (k === "Enter") {
      var tr = elPane.querySelector("tr.sel");
      if (tr && tr.getAttribute("data-folder")) openDetail(tr.getAttribute("data-folder"));
    }
  });
  elFilter.addEventListener("input", function () { filter = elFilter.value; sel = 0; render(); });

  /* ---------- boot ---------- */
  renderTabs();
  if (SNAPSHOT) { render(); tick(); }
  else {
    fetch("/api/state").then(function (r) { return r.json(); }).then(function (x) {
      S = x; render(); tick();
      setInterval(function () {
        fetch("/api/state").then(function (r) { return r.json(); }).then(function (x) { S = x; render(); });
      }, 5000);
    });
  }
  setInterval(function () {
    tick();
    if (pane === 0 && S) render();   // tick elapsed times
  }, 1000);
})();
