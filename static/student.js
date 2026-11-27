const feedback = document.querySelector("#feedback");
const activities = document.querySelector("#activities");
const csrf = document.querySelector('meta[name="csrf"]').content;
const join = document.querySelector("#join");
const membership = document.querySelector("#membership");
const answerForm = document.querySelector("#answer");
const selectedPrompt = document.querySelector("#selected-prompt");
const questions = document.querySelector("#questions");
let joinedActivity = "";
let previousView = "";
let pending = null;
let viewRequest = 0;
let worksheetVersion = null;
let joinedTeam = null;
let membershipVersion = null;
let groupSignature = "";

function openQuestion(question, card) {
    if (answerForm.elements.number.value !== question.number) {
        answerForm.elements.answer.value = question.mine?.answer ?? "";
    }
    answerForm.elements.number.value = question.number;
    document.querySelector("#answer-title").textContent = `提交答案 · ${question.number}`;
    selectedPrompt.textContent = question.prompt ?? "";
    selectedPrompt.hidden = !selectedPrompt.textContent;
    answerForm.hidden = false;
    card.append(answerForm);
    markSelectedQuestion();
    answerForm.elements.answer.focus();
}

function markSelectedQuestion() {
    for (const button of questions.querySelectorAll("[data-question]")) {
        button.setAttribute("aria-expanded", String(button.dataset.question === answerForm.elements.number.value && !answerForm.hidden));
    }
}

async function api(path, data) {
    try {
        const response = await fetch(path, data === undefined ? {cache: "no-store", signal: AbortSignal.timeout(8000)} : {
            method: "POST",
            headers: {"Content-Type": "application/json", "X-CSRF-Token": csrf},
            body: JSON.stringify(data),
        });
        const result = await response.json();
        if (!response.ok) throw Object.assign(new Error(result.message), {code: result.code});
        return result;
    } catch (error) {
        if (error.name === "TimeoutError") {
            throw Object.assign(new Error("同步逾時，正在重新取得最新題目與活動狀態。"), {code: "sync_timeout"});
        }
        throw error;
    }
}

async function refreshGroups() {
    const activity = activities.value;
    joinedActivity = "";
    joinedTeam = null;
    membershipVersion = null;
    groupSignature = "";
    answerForm.hidden = true;
    answerForm.reset();
    answerForm.elements.number.value = "";
    questions.before(answerForm);
    document.querySelector("#phase").textContent = "";
    questions.replaceChildren();
    previousView = "";
    worksheetVersion = null;
    pending = null;
    if (!activity) {
        join.hidden = true;
        return;
    }
    const data = await api(`/api/activities/${activity}/groups`);
    if (activity !== activities.value) return;
    join.elements.group.replaceChildren(...data.groups.map(row => new Option(row.name, row.id)));
    join.hidden = false;
    if (data.joined) join.elements.group.value = data.joined;
    join.querySelector("button").textContent = data.joined ? "重新選組" : "加入";
    membership.textContent = data.joined ? `已加入 ${data.groups.find(row => row.id === data.joined).name}` : "";
    joinedActivity = data.joined ? activity : "";
    if (joinedActivity) await refreshView();
}

const phaseLabels = {ready: "準備中", open: "搶答開放", closed: "搶答結束"};


async function refreshView() {
    const activity = joinedActivity;
    if (!activity) return;
    const request = ++viewRequest;
    let view;
    try {
        view = await api(`/api/activities/${activity}/view?audience=student`);
    } catch (error) {
        if (activity !== joinedActivity || request !== viewRequest) return;
        if (error.code === "activity_missing") {
            activities.value = "";
            localStorage.removeItem("buzzer-activity");
            await refreshGroups();
        } else if (error.code === "group_required") {
            await refreshGroups();
        }
        throw error;
    }
    if (activity !== joinedActivity || request !== viewRequest) return;
    if (feedback.dataset.syncError === "true") {
        feedback.textContent = "";
        delete feedback.dataset.syncError;
    }
    if (worksheetVersion !== view.worksheet_version || joinedTeam !== view.group.id || membershipVersion !== view.membership_version) {
        worksheetVersion = view.worksheet_version;
        if (joinedTeam !== null && (joinedTeam !== view.group.id || membershipVersion !== view.membership_version)) {
            feedback.textContent = "組別已在其他分頁變更，已清除未送出的答案，請確認目前組別後再作答。";
            groupSignature = "";
        }
        joinedTeam = view.group.id;
        membershipVersion = view.membership_version;
        answerForm.reset();
        answerForm.elements.number.value = "";
        answerForm.hidden = true;
        selectedPrompt.textContent = "";
        selectedPrompt.hidden = true;
        questions.before(answerForm);
        pending = null;
    }
    membership.textContent = `已加入 ${view.group.name}`;
    join.hidden = false;
    join.querySelector("button").textContent = "重新選組";
    const groupsSignature = JSON.stringify(view.groups);
    if (groupsSignature !== groupSignature) {
        join.elements.group.replaceChildren(...view.groups.map(row => new Option(row.name, row.id)));
        join.elements.group.value = view.group.id;
        groupSignature = groupsSignature;
    }
    const phase = document.querySelector("#phase");
    phase.textContent = phaseLabels[view.phase];
    phase.dataset.phase = view.phase;
    if (view.phase !== "open") {
        answerForm.hidden = true;
        answerForm.elements.number.value = "";
    }
    const signature = JSON.stringify(view);
    if (signature === previousView) return;
    previousView = signature;
    const focused = answerForm.contains(document.activeElement) ? document.activeElement : null;
    const sections = view.questions.map(question => {
        const section = document.createElement("section");
        const title = document.createElement("h2");
        title.textContent = question.number;
        const status = document.createElement("span");
        status.className = question.mine ? "question-status submitted" : "question-status";
        status.textContent = question.mine ? "已作答" : "未作答";
        const header = document.createElement("div");
        header.className = "question-heading";
        header.append(title, status);
        const mine = document.createElement("p");
        section.append(header);
        if (question.prompt) {
            const prompt = document.createElement("p");
            prompt.textContent = question.prompt;
            section.append(prompt);
        }
        if (question.mine) {
            mine.className = "submitted-preview";
            mine.textContent = `上一次作答：${question.mine.answer}`;
            section.append(mine);
        }
        if (view.phase === "open") {
            const button = document.createElement("button");
            button.type = "button";
            button.dataset.question = question.number;
            button.textContent = question.mine ? "修改答案" : "開始作答";
            button.setAttribute("aria-label", `${button.textContent} ${question.number}`);
            button.setAttribute("aria-controls", "answer");
            button.addEventListener("click", () => openQuestion(question, section));
            section.append(button);
            if (answerForm.elements.number.value === question.number) section.append(answerForm);
        }
        if (view.phase === "closed") {
            const position = document.createElement("p");
            position.className = "own-rank";
            position.textContent = question.own_rank ? `本組第 ${question.own_rank} 名` : "本組未提交";
            section.append(position);
            const result = document.createElement("p");
            result.className = "review-result";
            result.dataset.result = question.status;
            result.textContent = question.winner ? `搶答成功組別：${question.winner.name}` : "無有效提交";
            section.append(result);
        }
        return section;
    });
    if (answerForm.hidden) questions.before(answerForm);
    questions.replaceChildren(...sections);
    markSelectedQuestion();
    focused?.focus({preventScroll: true});
}

function showError(error) {
    feedback.textContent = error.message;
    feedback.dataset.syncError = String(error.code === "sync_timeout");
}

document.querySelector("#select-activity").addEventListener("submit", async event => {
    event.preventDefault();
    const value = event.target.elements.activity.value.trim();
    if (!/^[1-9][0-9]{0,18}$/.test(value) || BigInt(value) >= 2n ** 63n) {
        showError(new Error("請輸入有效的活動識別碼。")); return;
    }
    activities.value = value;
    localStorage.setItem("buzzer-activity", value);
    try { await refreshGroups(); } catch (error) { showError(error); }
});
join.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
        const data = Object.fromEntries(new FormData(join));
        data.group = Number(data.group);
        await api(`/api/activities/${activities.value}/join`, data);
        join.reset();
        feedback.textContent = "";
        await refreshGroups();
    } catch (error) {
        showError(error);
    }
});
answerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = answerForm.querySelector("button");
    button.disabled = true;
    const data = Object.fromEntries(new FormData(answerForm));
    data.worksheet_version = worksheetVersion;
    data.group = joinedTeam;
    data.membership_version = membershipVersion;
    const path = `/api/activities/${joinedActivity}/answers`;
    const key = JSON.stringify([path, data]);
    if (pending?.key !== key) pending = {key, receipt: crypto.randomUUID()};
    try {
        await api(path, {...data, receipt: pending.receipt});
        pending = null;
        if (path === `/api/activities/${joinedActivity}/answers` &&
            answerForm.elements.number.value === data.number &&
            answerForm.elements.answer.value === data.answer) {
            answerForm.hidden = true;
            answerForm.elements.number.value = "";
            questions.before(answerForm);
        }
        feedback.textContent = "答案已送出。";
        await refreshView();
    } catch (error) {
        showError(error);
    } finally {
        button.disabled = false;
    }
});
async function poll() {
    try {
        await refreshView();
    } catch (error) {
        showError(error);
    } finally {
        setTimeout(poll, 1000);
    }
}
setTimeout(poll, 1000);
function refreshWhenVisible() {
    if (document.visibilityState === "visible") refreshView().catch(showError);
}
window.addEventListener("focus", refreshWhenVisible);
document.addEventListener("visibilitychange", refreshWhenVisible);
const savedActivity = localStorage.getItem("buzzer-activity");
if (savedActivity && /^[1-9][0-9]{0,18}$/.test(savedActivity)) {
    activities.value = savedActivity;
    document.querySelector('#select-activity').elements.activity.value = savedActivity;
    refreshGroups().catch(showError);
}
