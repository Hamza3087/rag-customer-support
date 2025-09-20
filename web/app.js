(() => {
  const byId = (id) => document.getElementById(id);
  const pretty = (obj) => JSON.stringify(obj, null, 2);
  const setPre = (id, data) => { const el = byId(id); if (el) el.textContent = pretty(data); };
  const showToast = (msg, type = 'info') => {
    const d = document.createElement('div');
    d.className = 'toast-lite';
    d.textContent = msg;
    document.body.appendChild(d);
    setTimeout(() => { d.remove(); }, 2200);
  };
  const setLoading = (btn, isLoading, labelHtml) => {
    if (!btn) return;
    if (isLoading) {
      btn.disabled = true;
      btn.dataset._label = btn.innerHTML;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>' + (labelHtml || 'Working...');
    } else {
      btn.disabled = false;
      btn.innerHTML = btn.dataset._label || 'Done';
    }
  };

  const api = {
    async health() { const r = await fetch('/api/health'); if (!r.ok) throw new Error('API down'); return r.json(); },
    async query({ query, top_k = 6, rebuild_index = false }) {
      const r = await fetch('/api/query', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query, top_k, rebuild_index }) });
      if (!r.ok) throw new Error((await r.text()) || 'query failed');
      return r.json();
    },
    async eval({ rebuild_index = false }) { const r = await fetch(`/api/eval?rebuild_index=${rebuild_index ? 'true' : 'false'}`); if (!r.ok) throw new Error('eval failed'); return r.json(); },
    async dbStats() { const r = await fetch('/api/db/stats'); if (!r.ok) throw new Error('db stats failed'); return r.json(); },
    async dbList({ limit = 5, where = '' }) { const u = new URL('/api/db/list', location.origin); u.searchParams.set('limit', String(limit)); if (where) u.searchParams.set('where', where); const r = await fetch(u); if (!r.ok) throw new Error('db list failed'); return r.json(); },
    async dbShow(id) { const u = new URL('/api/db/show', location.origin); u.searchParams.set('id', id); const r = await fetch(u); if (!r.ok) throw new Error('db show failed'); return r.json(); },
    async trace({ query, top_k = 6 }) { const r = await fetch('/api/trace', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query, top_k }) }); if (!r.ok) throw new Error('trace failed'); return r.json(); }
  };

  const initHealth = async () => {
    const el = byId('health-indicator');
    const update = async () => {
      try {
        const h = await api.health();
        el.classList.remove('bg-secondary', 'bg-danger');
        el.classList.add('bg-success', 'pulse');
        el.textContent = 'API: OK';
      } catch (e) {
        el.classList.remove('bg-secondary', 'bg-success', 'pulse');
        el.classList.add('bg-danger');
        el.textContent = 'API: DOWN';
      }
    };
    update();
    setInterval(update, 6000);
  };

  // Persist active tab between reloads
  const activateTab = (selector) => {
    const panes = document.querySelectorAll('.tab-pane');
    panes.forEach(p => p.classList.remove('show', 'active'));
    const target = document.querySelector(selector);
    if (target) { target.classList.add('show', 'active'); }
    document.querySelectorAll('a.nav-link[data-bs-toggle="tab"]').forEach(l => {
      l.classList.toggle('active', l.getAttribute('href') === selector);
    });
  };
  const restoreTab = () => {
    const last = localStorage.getItem('active-tab') || '#tab-query';
    activateTab(last);
  };
  document.querySelectorAll('a[data-bs-toggle="tab"]').forEach(a => {
    a.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const href = a.getAttribute('href');
      localStorage.setItem('active-tab', href);
      activateTab(href);
    });
  });

  // Copy any PRE content on click
  document.addEventListener('click', (e) => {
    const pre = e.target.closest('pre.pretty');
    if (!pre) return;
    navigator.clipboard.writeText(pre.textContent).then(() => showToast('Copied to clipboard'));
  });

  // Buttons
  const btnAsk = byId('btn-ask');
  if (btnAsk) btnAsk.addEventListener('click', async () => {
    const q = (byId('q-text')?.value || '').trim();
    const top_k = Number(byId('q-topk')?.value || '6');
    const rebuild_index = !!byId('q-rebuild')?.checked;
    if (!q) { showToast('Enter a question'); return; }
    setPre('q-output', { status: 'running...' });
    setLoading(btnAsk, true, 'Asking');
    try {
      const data = await api.query({ query: q, top_k, rebuild_index });
      setPre('q-output', data);
    } catch (err) {
      setPre('q-output', { error: String(err) }); showToast('Query failed', 'error');
    } finally { setLoading(btnAsk, false); }
  });

  const btnDbStats = byId('btn-db-stats');
  const refreshDbStats = async () => { try { setPre('db-stats', { loading: true }); const s = await api.dbStats(); setPre('db-stats', s); } catch (e) { setPre('db-stats', { error: String(e) }); } };
  if (btnDbStats) btnDbStats.addEventListener('click', refreshDbStats);

  const btnDbList = byId('btn-db-list');
  if (btnDbList) btnDbList.addEventListener('click', async () => {
    const limit = Number(byId('db-limit')?.value || '5');
    const where = (byId('db-where')?.value || '').trim();
    setLoading(btnDbList, true, 'Listing');
    try { const data = await api.dbList({ limit, where }); setPre('db-list', data); }
    catch (e) { setPre('db-list', { error: String(e) }); showToast('List failed', 'error'); }
    finally { setLoading(btnDbList, false); }
  });

  const btnDbShow = byId('btn-db-show');
  if (btnDbShow) btnDbShow.addEventListener('click', async () => {
    const id = (byId('db-id')?.value || '').trim();
    if (!id) { showToast('Enter a chunk ID'); return; }
    setLoading(btnDbShow, true, 'Loading');
    try { const data = await api.dbShow(id); setPre('db-show', data); }
    catch (e) { setPre('db-show', { error: String(e) }); showToast('Show failed', 'error'); }
    finally { setLoading(btnDbShow, false); }
  });

  const btnTrace = byId('btn-trace');
  if (btnTrace) btnTrace.addEventListener('click', async () => {
    const q = (byId('t-text')?.value || '').trim();
    const top_k = Number(byId('t-topk')?.value || '6');
    if (!q) { showToast('Enter a query to trace'); return; }
    setLoading(btnTrace, true, 'Tracing');
    try {
      const data = await api.trace({ query: q, top_k });
      setPre('t-sem', data.semantic || []);
      setPre('t-bm25', data.bm25 || []);
      setPre('t-combined', data.combined || []);
    } catch (e) { showToast('Trace failed', 'error'); }
    finally { setLoading(btnTrace, false); }
  });

  const btnEval = byId('btn-eval');
  if (btnEval) btnEval.addEventListener('click', async () => {
    const rebuild_index = !!byId('e-rebuild')?.checked;
    setPre('eval-out', { status: 'running...' });
    setLoading(btnEval, true, 'Evaluating');
    try { const data = await api.eval({ rebuild_index }); setPre('eval-out', data); }
    catch (e) { setPre('eval-out', { error: String(e) }); showToast('Evaluation failed', 'error'); }
    finally { setLoading(btnEval, false); }
  });

  // Initialize
  initHealth();
  refreshDbStats();
  restoreTab();
})();

