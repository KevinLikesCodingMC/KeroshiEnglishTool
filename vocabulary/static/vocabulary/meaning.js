(() => {
	"use strict";

	const elements = Object.fromEntries([
		"quiz", "status", "retry", "question", "word", "phonetic",
		"choices", "next", "empty", "practice", "practice-tab", "mistakes-tab",
		"mistakes-count", "mistakes-list", "review-start", "review-back", "review-host", "storage-status",
	].map((id) => [id, document.getElementById(id)]));
	const queue = [];
	let current = null;
	let answered = false;
	let loading = false;
	let exhausted = false;
	let reviewing = false;
	let generation = 0;
	let reviewWords = [];
	let activeTab = "practice";
	const storageKey = "keroshi.english.vocabulary.meaning.mistakes.v1";
	const mistakes = Object.create(null);

	try {
		const saved = JSON.parse(localStorage.getItem(storageKey)
			?? localStorage.getItem("keroshi.vocabulary.mistakes.v1") ?? "{}");
		for (const [word, item] of Object.entries(saved || {})) {
			if (/^[a-z]{2,30}$/.test(word) && item && typeof item.definition === "string"
				&& typeof item.phonetic === "string" && Number.isSafeInteger(item.wrongCount)
				&& item.wrongCount > 0 && Number.isFinite(item.lastWrongAt)) {
				mistakes[word] = { definition: item.definition, phonetic: item.phonetic,
					wrongCount: item.wrongCount, lastWrongAt: item.lastWrongAt };
			}
		}
	} catch {
		elements["storage-status"].textContent = "无法读取本地错题，当前可临时使用。";
	}

	function saveMistakes() {
		try {
			localStorage.setItem(storageKey, JSON.stringify(mistakes));
			elements["storage-status"].textContent = "";
		} catch {
			elements["storage-status"].textContent = "保存失败，刷新后可能丢失本次改动。";
		}
		renderMistakes();
	}

	function renderMistakes() {
		const words = Object.keys(mistakes).sort((a, b) => mistakes[b].lastWrongAt - mistakes[a].lastWrongAt);
		elements["mistakes-count"].textContent = words.length ? `${words.length} 个词待复习` : "还没有错题";
		elements["review-start"].hidden = !words.length;
		elements["review-start"].textContent = reviewing ? "重新复习" : "开始复习";
		elements["mistakes-list"].replaceChildren();
		for (const word of words) {
			const row = document.createElement("div");
			row.className = "list-group-item px-0 d-flex align-items-start justify-content-between gap-3";
			const content = document.createElement("div");
			const title = document.createElement("div");
			title.textContent = word;
			const definition = document.createElement("div");
			definition.className = "small text-body-secondary";
			definition.textContent = mistakes[word].definition;
			content.append(title, definition);
			const remove = document.createElement("button");
			remove.type = "button";
			remove.className = "btn btn-sm btn-link text-body-secondary flex-shrink-0";
			remove.textContent = "移出";
			remove.addEventListener("click", () => {
				delete mistakes[word];
				saveMistakes();
			});
			row.append(content, remove);
			elements["mistakes-list"].append(row);
		}
	}

	function resetPractice(review) {
		generation++;
		reviewing = review;
		queue.length = 0;
		current = null;
		answered = false;
		loading = false;
		exhausted = false;
		elements.question.hidden = true;
		elements.empty.hidden = true;
		elements.retry.hidden = true;
		elements.status.textContent = "";
		const host = elements[review ? "review-host" : "practice"];
		for (const id of ["status", "retry", "question", "empty"]) host.append(elements[id]);
		elements["mistakes-list"].hidden = review;
		elements["review-back"].hidden = !review;
		renderMistakes();
	}


	function renderQuestion(question) {
		current = question;
		answered = false;
		elements.question.hidden = false;
		elements.empty.hidden = true;
		elements.next.hidden = true;
		elements.word.textContent = question.word;
		elements.phonetic.textContent = question.phonetic ? `/${question.phonetic}/` : "";
		elements.choices.replaceChildren();
		question.choices.forEach((choice) => {
			const column = document.createElement("div");
			column.className = "col-12 col-md-6";
			const button = document.createElement("button");
			button.type = "button";
			button.className = "btn btn-outline-secondary w-100 h-100 text-start";
			button.style.whiteSpace = "pre-line";
			button.textContent = choice.definition;
			button.dataset.id = choice.id;
			button.addEventListener("click", () => answer(choice.id));
			column.append(button);
			elements.choices.append(column);
		});

		if (reviewing || activeTab === "practice") {
			elements.word.focus({ preventScroll: true });
		}
	}

	function answer(selectedId) {
		if (!current || answered) return;
		answered = true;
		elements.choices.querySelectorAll("button").forEach((button) => {
			const id = Number(button.dataset.id);
			const color = id === current.answer_id ? "btn-success"
				: id === selectedId ? "btn-danger" : "btn-outline-secondary";
			button.className = `btn ${color} w-100 h-100 text-start`;
			button.disabled = true;
		});
		if (selectedId !== current.answer_id) {
			const previous = mistakes[current.word];
			mistakes[current.word] = {
				phonetic: current.phonetic,
				definition: current.choices.find((choice) => choice.id === current.answer_id).definition,
				wrongCount: (previous?.wrongCount || 0) + 1,
				lastWrongAt: Date.now(),
			};
			saveMistakes();
		} else if (reviewing && mistakes[current.word]) {
			delete mistakes[current.word];
			saveMistakes();
		}
		elements.next.hidden = false;
		elements.next.focus();
	}

	function validQuestion(question) {
		return question && typeof question.word === "string" && /^[a-z]{2,30}$/.test(question.word)
			&& typeof question.phonetic === "string"
			&& Array.isArray(question.choices) && question.choices.length === 4
			&& question.choices.every((choice) => Number.isInteger(choice.id) && typeof choice.definition === "string")
			&& new Set(question.choices.map((choice) => choice.id)).size === 4
			&& question.choices.some((choice) => choice.id === question.answer_id);
	}

	async function refill() {
		if (loading || exhausted) return;
		loading = true;
		const requestGeneration = generation;
		const batch = reviewing ? reviewWords.slice(0, 50) : [];
		elements.retry.hidden = true;
		elements.status.textContent = current ? "" : "正在加载题目……";
		let phase = "request";
		try {
			const query = reviewing ? "?" + batch.map((word) => "word=" + encodeURIComponent(word)).join("&") : "";
			const response = await fetch(elements.quiz.dataset.questionsUrl + query, {
				headers: { Accept: "application/json" }, cache: "no-store",
			});
			phase = "json";
			const data = await response.json();
			if (requestGeneration !== generation) return;
			phase = "response";
			if (!response.ok) throw new Error(data.error || "题目加载失败，请稍后重试。");
			if (!Array.isArray(data.questions) || !data.questions.every(validQuestion)) {
				throw new Error("题目数据不完整，请重新加载。");
			}
			phase = "render";
			queue.push(...data.questions);
			if (reviewing) reviewWords.splice(0, batch.length);
			exhausted = reviewing ? reviewWords.length === 0 : data.questions.length === 0;
			elements.status.textContent = "";
			if (!current) {
				if (queue.length) renderQuestion(queue.shift());
				else if (reviewing && !exhausted) {
					loading = false;
					await refill();
				} else {
					elements.empty.hidden = false;
					if (reviewing) elements.empty.textContent = "本轮没有可复习的题目，词库可能已更新。";
				}
			}
		} catch (error) {
			if (requestGeneration !== generation) return;
			if (phase === "render") {
				current = null;
				elements.question.hidden = true;
				elements.status.textContent = "题目显示失败，请刷新页面后重试。";
			} else if (phase === "request") {
				elements.status.textContent = "题目加载失败，请检查网络后重试。";
			} else if (phase === "json") {
				elements.status.textContent = "题目接口返回异常，请稍后重试。";
			} else {
				elements.status.textContent = error.message;
			}
			console.error("词义选择题加载失败", error);
			elements.retry.hidden = false;
		} finally {
			if (requestGeneration === generation) loading = false;
		}
	}

	elements.next.addEventListener("click", () => {
		if (!answered) return;
		if (queue.length) {
			renderQuestion(queue.shift());
			if (queue.length <= 3) void refill();
		} else {
			current = null;
			answered = false;
			elements.question.hidden = true;
			if (exhausted) {
				elements.empty.hidden = false;
				if (reviewing) elements.empty.textContent = "本轮复习完成";
			}
			else void refill();
		}
	});
	elements.retry.addEventListener("click", () => void refill());
	elements["review-back"].addEventListener("click", () => {
		resetPractice(false);
		elements.empty.textContent = "暂时没有足够的题目";
		void refill();
	});
	elements["review-start"].addEventListener("click", () => {
		resetPractice(true);
		reviewWords = Object.keys(mistakes).sort((a, b) => mistakes[b].wrongCount - mistakes[a].wrongCount);
		void refill();
	});
	elements["practice-tab"].addEventListener("shown.bs.tab", () => {
		activeTab = "practice";
		if (reviewing) {
			resetPractice(false);
			elements.empty.textContent = "暂时没有足够的题目";
			void refill();
		}
	});
	elements["mistakes-tab"].addEventListener("shown.bs.tab", () => {
		activeTab = "mistakes";
		if (reviewing) resetPractice(false);
		renderMistakes();
	});
	renderMistakes();
	void refill();
})();
