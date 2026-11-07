const form = document.getElementById("material-form");
const status = document.getElementById("material-status");
const generateButton = document.getElementById("generate-button");
const materialText = document.getElementById("material-text");

form.addEventListener("submit", async (event) => {
	event.preventDefault();
	generateButton.disabled = true;
	status.textContent = "正在生成材料，请稍候……";
	try {
		const response = await fetch(form.dataset.createUrl, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				"X-CSRFToken": form.querySelector("[name=csrfmiddlewaretoken]").value,
			},
			body: JSON.stringify({
				topic: document.getElementById("topic").value,
				level: document.getElementById("level").value,
				word_count: Number(document.getElementById("word-count").value),
			}),
		});
		if (response.redirected) throw new Error("登录已失效，请刷新页面重新登录。");
		const data = await response.json().catch(() => { throw new Error("服务暂时不可用，请稍后重试。"); });
		if (!response.ok) throw new Error(data.error || "生成失败，请重试。");
		materialText.value = data.text;
		document.getElementById("material-result").classList.remove("d-none");
		status.textContent = "材料已生成。";
	} catch (error) {
		status.textContent = error.message;
	} finally {
		generateButton.disabled = false;
	}
});

