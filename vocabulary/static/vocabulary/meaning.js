(() => {
	"use strict";

	const elements = Object.fromEntries([
		"quiz", "status", "retry", "login", "question", "word", "phonetic",
		"choices", "next", "empty",
	].map((id) => [id, document.getElementById(id)]));
	const queue = [];
	let current = null;
	let answered = false;
	let loading = false;
	let exhausted = false;

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

		elements.word.focus({ preventScroll: true });
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
		elements.next.hidden = false;
		elements.next.focus();
	}

	function validQuestion(question) {
		return question && typeof question.word === "string" && typeof question.phonetic === "string"
			&& Array.isArray(question.choices) && question.choices.length === 4
			&& question.choices.every((choice) => Number.isInteger(choice.id) && typeof choice.definition === "string")
			&& new Set(question.choices.map((choice) => choice.id)).size === 4
			&& question.choices.some((choice) => choice.id === question.answer_id);
	}

	async function refill() {
		if (loading || exhausted) return;
		loading = true;
		elements.retry.hidden = true;
		elements.login.hidden = true;
		elements.status.textContent = current ? "" : "正在加载题目……";
		let phase = "request";
		try {
			const response = await fetch(elements.quiz.dataset.questionsUrl, {
				headers: { Accept: "application/json" }, cache: "no-store",
			});
			phase = "response";
			if (response.redirected || response.status === 403) {
				elements.status.textContent = "登录已过期，请重新登录后继续练习。";
				elements.login.hidden = false;
				return;
			}
			phase = "json";
			const data = await response.json();
			phase = "response";
			if (!response.ok) throw new Error(data.error || "题目加载失败，请稍后重试。");
			if (!Array.isArray(data.questions) || !data.questions.every(validQuestion)) {
				throw new Error("题目数据不完整，请重新加载。");
			}
			phase = "render";
			queue.push(...data.questions);
			exhausted = data.questions.length === 0;
			elements.status.textContent = "";
			if (!current) {
				if (queue.length) renderQuestion(queue.shift());
				else elements.empty.hidden = false;
			}
		} catch (error) {
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
			loading = false;
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
			if (exhausted) elements.empty.hidden = false;
			else void refill();
		}
	});
	elements.retry.addEventListener("click", () => void refill());
	void refill();
})();
