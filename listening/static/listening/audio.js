const form = document.getElementById("tts-form");
const textInput = document.getElementById("text");
const voiceInput = document.getElementById("voice");
const speedInput = document.getElementById("speed");
speedInput.addEventListener("input", () => {
	document.getElementById("speed-value").textContent = Number(speedInput.value).toFixed(1) + "\u00D7";
});
const submitButton = document.getElementById("submit-button");
const statusMessage = document.getElementById("status-message");
const audioPlayer = document.getElementById("audio-player");
const csrfToken = form.querySelector("[name=csrfmiddlewaretoken]").value;
let pollTimeout = null;

function showStatus(message, type) {
	statusMessage.textContent = message;
	statusMessage.className = `alert alert-${type} mt-4 mb-0`;
}

function stopPolling() {
	if (pollTimeout !== null) {
		clearTimeout(pollTimeout);
		pollTimeout = null;
	}
}

async function pollJob(statusUrl) {
	try {
		const response = await fetch(statusUrl, {
			headers: {"Accept": "application/json"},
		});
		const data = await response.json();

		if (! response.ok) {
			throw new Error(data.error || "查询任务失败。");
		}

		if (data.status === "completed") {
			showStatus("完成。", "success");
			audioPlayer.src = data.audio_url;
			audioPlayer.classList.remove("d-none");
			submitButton.disabled = false;
			return;
		}

		if (data.status === "failed") {
			showStatus(`生成失败：${data.error_message}`, "danger");
			submitButton.disabled = false;
			return;
		}

		showStatus("生成中……", "info");
		pollTimeout = setTimeout(() => pollJob(statusUrl), 2000);
	} catch (error) {
		showStatus(error.message, "danger");
		submitButton.disabled = false;
	}
}

form.addEventListener("submit", async (event) => {
	event.preventDefault();
	stopPolling();
	submitButton.disabled = true;
	audioPlayer.pause();
	audioPlayer.removeAttribute("src");
	audioPlayer.classList.add("d-none");

	try {
		const response = await fetch(form.dataset.createUrl, {
			method: "POST",
			headers: {
				"Accept": "application/json",
				"Content-Type": "application/json",
				"X-CSRFToken": csrfToken,
			},
			body: JSON.stringify({
				text: textInput.value,
				voice: voiceInput.value,
				speed: Number(speedInput.value),
			}),
		});
		const data = await response.json();

		if (!response.ok) {
			throw new Error(data.error || "创建任务失败。");
		}

		showStatus("生成中……", "info");
		pollTimeout = setTimeout(() => pollJob(data.status_url), 2000);
	} catch (error) {
		showStatus(error.message, "danger");
		submitButton.disabled = false;
	}
});
