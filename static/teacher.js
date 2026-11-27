const feedback = document.querySelector('#feedback');
const activities = document.querySelector('#activities');
const csrf = document.querySelector('meta[name="csrf"]').content;
const notes = document.querySelector('#notes');
let importPreview = null, exportPreview = null, viewRequest = 0, lastView = '';
let importRequest = 0, exportRequest = 0;
let deletingActivity = false;
async function api(path, data, method = 'POST') {
    const response = await fetch(path, {cache: 'no-store', signal: AbortSignal.timeout(25000),
        ...(data === undefined ? {} : {method, headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf}, body: JSON.stringify(data)})});
    const result = await response.json();
    if (!response.ok) throw new Error(result.message ?? '操作失敗，請重新載入後再試。');
    return result;
}
function report(error) { feedback.textContent = error.name === 'TimeoutError' ? '連線逾時，請重試以核對結果。' : error.message; }
function submit(id, action) {
    document.querySelector(id)?.addEventListener('submit', async event => {
        event.preventDefault(); const button = event.target.querySelector('button'); button.disabled = true;
        try { await action(Object.fromEntries(new FormData(event.target))); }
        catch (error) { report(error); }
        finally { button.disabled = false; await refreshView().catch(report); }
    });
}
function table(container, headings, rows) {
    const result = document.createElement('table'), head = result.createTHead().insertRow();
    for (const label of headings) { const cell = document.createElement('th'); cell.scope = 'col'; cell.textContent = label; head.append(cell); }
    const body = result.createTBody();
    for (const row of rows) { const line = body.insertRow(); for (const value of row) line.insertCell().textContent = value ?? '（空白）'; }
    container.replaceChildren(result);
}
function cancelImport() { importRequest++; importPreview = null; document.querySelector('#import-preview').hidden = true; }
function cancelExport() { exportRequest++; exportPreview = null; document.querySelector('#export-preview').hidden = true; }
async function selectActivity() {
    cancelImport(); cancelExport(); lastView = '';
    history.replaceState({}, '', activities.value ? `/teacher/activities/${activities.value}` : '/teacher');
    await refreshView();
}
async function loadActivities(selected = '') {
    const result = await api('/api/activities');
    activities.replaceChildren(new Option('建立新活動', ''), ...result.activities.map(row => new Option(row.name, row.id)));
    if (selected && result.activities.some(row => String(row.id) === String(selected))) activities.value = selected;
    await selectActivity();
}
activities?.addEventListener('change', () => selectActivity().catch(report));
submit('#login', async data => { await api('/api/teacher/session', data); location.reload(); });
submit('#group', async data => { await api(`/api/activities/${activities.value}/groups`, data); feedback.textContent = '已建立組別。'; });
submit('#batch-groups', async data => {
    if (document.querySelectorAll('#group-codes li').length && !window.confirm('整批建立會取代目前組別，確定繼續？')) return;
    await api(`/api/activities/${activities.value}/groups`, {count: Number(data.count)}, 'PUT'); feedback.textContent = '已批次建立組別。';
});
notes?.addEventListener('input', cancelImport);
notes?.elements.sheet.addEventListener('change', cancelImport);
notes?.elements.url.addEventListener('input', () => { notes.elements.sheet.replaceChildren(new Option('自動選擇單一工作表', '')); });
document.querySelector('#inspect')?.addEventListener('click', async event => {
    const button = event.currentTarget; button.disabled = true; cancelImport();
    const request = importRequest;
    try {
        const result = await api('/api/guided-notes/inspect', {url: notes.elements.url.value});
        if (request !== importRequest || activities.value) return;
        notes.elements.sheet.replaceChildren(...result.sheets.map(row => new Option(row.name, row.id)));
        feedback.textContent = `已讀取 ${result.sheets.length} 張工作表，請選擇並預覽。`;
    } catch (error) { report(error); } finally { button.disabled = false; }
});
submit('#notes', async data => {
    cancelImport();
    const request = importRequest;
    const result = await api('/api/guided-notes/preview', {url: data.url, sheet: data.sheet ? Number(data.sheet) : null});
    if (request !== importRequest || activities.value) {
        feedback.textContent = '匯入資料已變更，請重新預覽。'; return;
    }
    importPreview = {token: result.preview, name: data.name};
    table(document.querySelector('#import-preview-content'), ['題號', '題目', '答案格'], result.questions.map(row => [row.number, row.prompt ?? '（標記格式未提供題目敘述）', row.answer_cell]));
    document.querySelector('#import-preview').hidden = false; document.querySelector('#confirm-import').focus();
    feedback.textContent = `已預覽 ${result.questions.length} 題，確認後才建立活動。`;
});
document.querySelector('#cancel-import')?.addEventListener('click', () => { cancelImport(); feedback.textContent = '已取消匯入，未建立活動。'; });
document.querySelector('#confirm-import')?.addEventListener('click', async event => {
    const button = event.currentTarget, saved = importPreview; if (!saved) return; button.disabled = true;
    try {
        const row = await api('/api/activities', {name: saved.name, preview: saved.token}); await loadActivities(row.id);
        feedback.textContent = '已確認匯入並建立活動，請設定至少兩組。';
    } catch (error) { report(error); } finally { button.disabled = false; }
});
for (const action of ['open', 'close']) {
    document.getElementById(action)?.addEventListener('click', async event => {
        const selected = activities.value; if (!selected) return;
        if (action === 'close' && !window.confirm('結束後所有答案與順位將固定，不能重新開放。確定結束？')) return;
        const button = event.currentTarget; button.disabled = true;
        try {
            await api(`/api/activities/${selected}/${action}`, {});
            feedback.textContent = action === 'open' ? '搶答已開放。' : '搶答已結束，第一名取得搶答成功資格。';
        } catch (error) { report(error); } finally { await refreshView().catch(report); }
    });
}
document.querySelector('#copy-url')?.addEventListener('click', async () => {
    const input = document.querySelector('#activity-url');
    try { await navigator.clipboard.writeText(input.value); feedback.textContent = '已複製活動網址。'; }
    catch { input.select(); feedback.textContent = '請按 Ctrl+C 複製已選取的活動網址。'; }
});
document.querySelector('#export')?.addEventListener('click', async event => {
    const selected = activities.value, button = event.currentTarget; button.disabled = true; cancelExport();
    const request = exportRequest;
    try {
        const result = await api(`/api/activities/${selected}/export/preview`, {}); if (selected !== activities.value || request !== exportRequest) return;
        exportPreview = {activity: selected, token: result.preview};
        document.querySelector('#export-target').textContent = `試算表：${result.spreadsheet} · 工作表 ID：${result.sheet}`;
        table(document.querySelector('#export-preview-content'), ['題號', '答案格', '原值', '搶答成功答案'], result.changes.map(row => [row.number, row.cell, row.before, row.answer]));
        document.querySelector('#export-preview').hidden = false; document.querySelector('#confirm-export').focus();
        feedback.textContent = result.changes.length ? '請檢查回填預覽，確認後才寫入。' : '沒有需要回填的作答。';
    } catch (error) { report(error); } finally { await refreshView().catch(report); }
});
document.querySelector('#cancel-export')?.addEventListener('click', () => { cancelExport(); feedback.textContent = '已取消回填，未寫入原表。'; });
document.querySelector('#confirm-export')?.addEventListener('click', async event => {
    const saved = exportPreview, button = event.currentTarget; if (!saved) return; button.disabled = true;
    try {
        const result = await api(`/api/activities/${saved.activity}/export`, {preview: saved.token}); cancelExport();
        feedback.textContent = result.written ? `已回填 ${result.written} 格。` : '原表無需更新。';
    } catch (error) { cancelExport(); report(error); } finally { button.disabled = false; }
});
async function refreshView() {
    if (!activities || deletingActivity) return;
    const selected = activities.value, request = ++viewRequest;
    const view = selected ? await api(`/api/activities/${selected}/view?audience=teacher`) : null;
    if (selected !== activities.value || request !== viewRequest || deletingActivity) return;
    document.querySelector('#delete-activity').disabled = !view || view.phase === 'open';
    const ready = view?.phase === 'ready';
    document.querySelector('#phase').textContent = {ready: '準備中', open: '搶答開放', closed: '搶答結束'}[view?.phase] ?? '';
    document.querySelector('#phase').dataset.phase = view?.phase ?? '';
    document.querySelector('#open').disabled = !ready; document.querySelector('#close').disabled = view?.phase !== 'open'; document.querySelector('#export').disabled = !view?.can_export;
    for (const control of document.querySelectorAll('#group input, #group button, #batch-groups input, #batch-groups button')) control.disabled = !ready;
    for (const control of document.querySelectorAll('#batch-groups input, #batch-groups button')) control.disabled = !ready || view.groups_locked;
    document.querySelector('#groups-lock-hint').textContent = view?.groups_locked ? '已有學生加入，整批重建已鎖定；準備階段仍可逐組建立或刪除。' : '';
    for (const control of notes.querySelectorAll('input,select,button')) control.disabled = Boolean(selected);
    document.querySelector('#activity-code').textContent = selected ? `活動識別碼：${selected}` : '請先預覽學習單以建立活動。';
    document.querySelector('#activity-url').value = selected ? `${location.origin}/teacher/activities/${selected}` : ''; document.querySelector('#copy-url').disabled = !selected;
    const signature = JSON.stringify([selected, view]); if (signature === lastView) return; lastView = signature;
    document.querySelector('#group-codes').replaceChildren(...(view?.groups ?? []).map(group => {
        const row = document.createElement('li'), label = document.createElement('span'); label.textContent = group.name; row.append(label);
        if (ready) {
            const button = document.createElement('button'); button.type = 'button'; button.className = 'danger'; button.textContent = '刪除組別'; button.setAttribute('aria-label', `刪除組別 ${group.name}`);
            button.addEventListener('click', async () => {
                if (!window.confirm(`刪除「${group.name}」？該組成員將需要重新選組。`)) return;
                try { await api(`/api/activities/${selected}/groups/${group.id}`, {}, 'DELETE'); await refreshView(); } catch (error) { report(error); }
            }); row.append(button);
        } return row;
    }));
    document.querySelector('#questions').replaceChildren(...(view?.questions ?? []).map(question => {
        const card = document.createElement('section'), title = document.createElement('h2'); title.textContent = question.number; card.append(title);
        const prompt = document.createElement('p'); prompt.textContent = question.prompt ?? ''; card.append(prompt);
        if (view.phase === 'closed' || !question.submissions.length) {
            const result = document.createElement('p'); result.className = 'review-result'; result.textContent = question.winner ? `搶答成功組別：${question.winner.name}` : '無有效提交'; card.append(result);
        }
        for (const submission of question.ranking ?? question.submissions) {
            const row = document.createElement('div'); row.className = 'review-row'; const heading = document.createElement('strong'); heading.textContent = `${submission.rank ? `第 ${submission.rank} 名 · ` : ''}${submission.name}`;
            const answer = document.createElement('p'); answer.textContent = submission.answer;
            const time = document.createElement('time'); time.className = 'submission-time'; time.dateTime = submission.received_at; time.textContent = `提交時間（台灣）：${submission.received_at.slice(0, 23).replace('T', ' ')}`;
            row.append(heading, answer, time); card.append(row);
        } return card;
    }));
}
if (activities) {
    loadActivities(document.querySelector('[data-activity]').dataset.activity).catch(report);
    async function poll() { try { await refreshView(); } catch (error) { report(error); } finally { setTimeout(poll, 1000); } }
    setTimeout(poll, 1000);
}

document.querySelector('#delete-activity')?.addEventListener('click', async event => {
    const selected = activities.value;
    const name = activities.selectedOptions[0]?.textContent;
    if (!selected || deletingActivity || !window.confirm(`永久刪除「${name}」？組別、作答及相關紀錄將一併刪除，無法復原。Google Sheets 已寫入內容會保留。`)) return;
    deletingActivity = true; viewRequest++;
    event.currentTarget.disabled = true;
    cancelImport(); cancelExport();
    try {
        await api(`/api/activities/${selected}`, {confirm: true}, 'DELETE');
        deletingActivity = false;
        await loadActivities();
        feedback.textContent = '已刪除活動；Google Sheets 內容保留。';
    } catch (error) { report(error); }
    finally { deletingActivity = false; await refreshView().catch(report); }
});
