(() => {
	const root = document.getElementById("practice");
	const materialForm = document.getElementById("practice-material-form");
	const generateButton = document.getElementById("material-generate");
	const audioSection = document.getElementById("practice-audio");
	const settings = document.getElementById("audio-settings");
	const materialFeedback = document.getElementById("material-feedback");
	const audioFeedback = document.getElementById("audio-feedback");
	const retryButton = document.getElementById("retry-audio");
	const progress = document.getElementById("audio-progress");
	const player = document.getElementById("practice-player");
	const speedInput = document.getElementById("practice-speed");
	const speedValue = document.getElementById("practice-speed-value");

	speedInput.addEventListener("input", () => {
		speedValue.textContent = Number(speedInput.value).toFixed(1) + "\u00D7";
	});
	const csrfToken = materialForm.querySelector("[name=csrfmiddlewaretoken]").value;
	const roleNames = {woman: "女声角色", man: "男声角色", narrator: "旁白"};
	let material = null;
	let statusUrl = "";
	let retryUrl = "";
	let retryMode = "query";
	let pollTimer = null;

	async function request(url, payload) {
		const options = {headers: {Accept: "application/json"}};
		if (payload !== undefined) {
			options.method = "POST";
			options.headers["Content-Type"] = "application/json";
			options.headers["X-CSRFToken"] = csrfToken;
			options.body = JSON.stringify(payload);
		}
		const response = await fetch(url, options);
		if (response.redirected) throw new Error("登录已失效，请刷新页面重新登录。");
		const data = await response.json().catch(() => { throw new Error("服务暂时不可用，请稍后重试。"); });
		if (!response.ok) throw new Error(data.error || "请求失败，请重试。");
		return data;
	}

	function setBusy(busy) {
		generateButton.disabled = busy;
		settings.disabled = busy || !material;
	}

	function clearAudio() {
		player.pause();
		player.removeAttribute("src");
		player.load();
		document.getElementById("audio-result").hidden = true;
		retryButton.hidden = true;
		progress.hidden = true;
	}

	function renderMaterial(value) {
		material = value;
		document.getElementById("practice-title").textContent = value.title;
		document.getElementById("playback-rule").textContent = value.section === "A"
			? "Section A：短对话与问题均读一次。"
			: "Section B：正文读两次，问题各读一次。";
		const script = document.getElementById("script-segments");
		script.replaceChildren();
		value.segments.forEach((segment, index) => {
			const label = document.createElement("label");
			label.className = "form-label small";
			label.htmlFor = `segment-${index}`;
			label.textContent = `${index + 1}. ${roleNames[segment.speaker]}`;
			const input = document.createElement("textarea");
			input.id = label.htmlFor;
			input.className = "form-control mb-3";
			input.rows = segment.text.length > 200 ? 5 : 2;
			input.maxLength = 4000;
			input.value = segment.text;
			input.addEventListener("input", () => { segment.text = input.value; });
			script.append(label, input);
		});
		const questions = document.getElementById("practice-questions");
		questions.replaceChildren();
		const answerOptions = document.getElementById("practice-answer-options");
		answerOptions.replaceChildren();
		const answerResults = document.getElementById("practice-answer-results");
		answerResults.replaceChildren();
		value.questions.forEach((question, index) => {
			const group = document.createElement("div");
			group.className = "mb-4";
			const label = document.createElement("label");
			label.className = "form-label";
			label.htmlFor = `question-${index}`;
			label.textContent = `第 ${index + 1} 题`;
			const input = document.createElement("textarea");
			input.id = label.htmlFor;
			input.className = "form-control mb-2";
			input.rows = 2;
			input.maxLength = 500;
			input.value = question.text;
			input.addEventListener("input", () => { question.text = input.value; });
			group.append(label, input);

			const choices = document.createElement("fieldset");
			choices.className = "mb-3";
			const legend = document.createElement("legend");
			legend.className = "fs-6 fw-semibold mb-2";
			legend.textContent = label.textContent;
			choices.append(legend);
			for (const letter of ["A", "B", "C", "D"]) {
				const option = document.createElement("p");
				option.className = "small mb-1";
				option.textContent = `${letter}. ${question.options[letter]}`;
				group.append(option);

				const row = document.createElement("label");
				row.className = "form-check d-block py-1";
				const radio = document.createElement("input");
				radio.className = "form-check-input";
				radio.type = "radio";
				radio.name = `practice-choice-${index}`;
				radio.value = letter;
				row.append(radio, option.textContent);
				choices.append(row);
			}
			answerOptions.append(choices);
			const correctOption = document.createElement("li");
			correctOption.textContent = question.answer;
			answerResults.append(correctOption);
			const details = document.createElement("details");
			details.className = "small mt-2";
			const summary = document.createElement("summary");
			summary.textContent = "查看答案与解析";
			const answer = document.createElement("p");
			answer.className = "mt-2";
			answer.textContent = `${question.answer} · ${question.explanation}`;
			details.append(summary, answer);
			group.append(details);
			questions.append(group);
		});
		document.getElementById("practice-material-details").open = false;
		document.getElementById("practice-answer-key").open = false;
		document.getElementById("practice-preview").hidden = false;
		document.getElementById("practice-answer-sheet").hidden = false;
		audioSection.hidden = false;
		settings.disabled = false;
	}

	async function poll(restoreMaterial = false) {
		clearTimeout(pollTimer);
		try {
			const data = await request(statusUrl);
			retryUrl = data.retry_url;
			if (restoreMaterial) renderMaterial(data.material);
			progress.hidden = false;
			progress.max = Math.max(data.total, 1);
			progress.value = data.completed;
			if (data.status === "completed") {
				if (!data.audio_url) throw new Error("任务已结束，但音频文件不可用。");
				player.src = data.audio_url;
				document.getElementById("download-audio").href = data.audio_url;
				document.getElementById("audio-result").hidden = false;
				audioFeedback.textContent = `任务 #${data.id} 已完成，可以播放或下载。`;
				setBusy(false);
				return;
			}
			if (data.status === "failed") {
				audioFeedback.textContent = data.error;
				retryMode = "retry";
				retryButton.textContent = "重试失败任务";
				retryButton.hidden = false;
				setBusy(false);
				return;
			}
			setBusy(true);
			audioFeedback.textContent = data.status === "assembling"
				? `任务 #${data.id} 正在拼接音频……`
				: `任务 #${data.id}：已完成 ${data.completed} / ${data.total} 个片段，等待处理或生成中……`;
			pollTimer = setTimeout(() => poll(), 2000);
		} catch (error) {
			audioSection.hidden = false;
			audioFeedback.textContent = error.message;
			retryMode = "query";
			retryButton.textContent = "重新查询进度";
			retryButton.hidden = false;
			setBusy(false);
		}
	}

	materialForm.addEventListener("submit", async (event) => {
		event.preventDefault();
		clearTimeout(pollTimer);
		setBusy(true);
		materialFeedback.textContent = "正在生成材料，请稍候……";
		try {
			const kind = document.getElementById("exercise-kind").value;
			const data = await request(root.dataset.materialUrl, {
				topic: document.getElementById("practice-topic").value,
				section: kind === "short_conversation" ? "A" : "B", kind,
			});
			clearAudio();
			statusUrl = "";
			history.replaceState(null, "", location.pathname);
			renderMaterial(data.material);
			materialFeedback.textContent = "材料已生成。";
			audioFeedback.textContent = "材料尚未保存，提交音频任务后会自动保存。";
		} catch (error) {
			materialFeedback.textContent = error.message;
		} finally {
			setBusy(false);
		}
	});

	document.getElementById("practice-audio-form").addEventListener("submit", async (event) => {
		event.preventDefault();
		if (!material) return;
		clearTimeout(pollTimer);
		clearAudio();
		setBusy(true);
		audioFeedback.textContent = "正在提交音频任务……";
		try {
			const voices = Object.fromEntries([...root.querySelectorAll("[data-speaker]")].map(input => [input.dataset.speaker, input.value]));
			const data = await request(root.dataset.createUrl, {
				material, voices, speed: Number(speedInput.value),
			});
			statusUrl = data.status_url;
			history.replaceState(null, "", `${location.pathname}?job=${data.id}`);
			await poll();
		} catch (error) {
			audioFeedback.textContent = error.message;
			setBusy(false);
		}
	});

	retryButton.addEventListener("click", async () => {
		retryButton.hidden = true;
		setBusy(true);
		try {
			if (retryMode === "retry") await request(retryUrl, {});
			await poll(!material);
		} catch (error) {
			audioFeedback.textContent = error.message;
			retryButton.hidden = false;
			setBusy(false);
		}
	});

	window.addEventListener("pagehide", () => clearTimeout(pollTimer));
	if (root.dataset.initialStatusUrl) {
		statusUrl = root.dataset.initialStatusUrl;
		setBusy(true);
		poll(true);
	}
})();
