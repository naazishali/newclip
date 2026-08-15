const form = document.getElementById("form");
const submitBtn = document.getElementById("submitBtn");
const statusEl = document.getElementById("progress");
const statusText = document.getElementById("statusText");
const progressPercent = document.getElementById("progressPercent");
const progressBar = document.getElementById("progressBar");
const errorEl = document.getElementById("error");
const resultsEl = document.getElementById("results");
const clipGrid = document.getElementById("clipGrid");
const resultsCount = document.getElementById("resultsCount");

let pollInterval = null;
let abortController = null;

// Format selection handling
document.querySelectorAll(".shape").forEach(shape => {
  shape.addEventListener("click", () => {
    const checkbox = shape.querySelector("input");
    checkbox.checked = !checkbox.checked;
    shape.classList.toggle("active", checkbox.checked);
  });
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  // Reset state
  errorEl.classList.add("hidden");
  resultsEl.classList.add("hidden");
  clipGrid.innerHTML = "";

  // Clear any existing polling
  if (pollInterval) clearInterval(pollInterval);
  if (abortController) abortController.abort();
  abortController = new AbortController();

  const url = document.getElementById("url").value.trim();
  const clips = parseInt(document.getElementById("clips").value, 10);
  const duration = parseInt(document.getElementById("duration").value, 10);
  const quality = document.getElementById("quality").value;
  const formats = Array.from(document.querySelectorAll(".shapes input:checked")).map(i => i.value);

  // Validation
  if (!isValidYouTubeURL(url)) {
    showError("Please enter a valid YouTube URL. Example: https://youtube.com/watch?v=...");
    return;
  }

  if (!formats.length) {
    showError("Kam az kam ek export shape select karein.");
    return;
  }

  submitBtn.disabled = true;
  statusEl.classList.remove("hidden");
  resetSteps();
  updateStep("download", "waiting");
  statusText.textContent = "Shuru ho raha hai...";
  progressPercent.textContent = "0%";
  progressBar.style.width = "0%";

  try {
    const res = await fetch("/api/process", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, clips, duration, formats, quality }),
      signal: abortController.signal,
    });

    const data = await res.json();
    if (!res.ok) {
      const errorMsg = data.detail?.[0]?.msg || data.error || "Validation failed";
      throw new Error(errorMsg);
    }

    pollStatus(data.job_id);
  } catch (err) {
    if (err.name === "AbortError") return;
    showError(err.message);
    resetButton();
  }
});

function isValidYouTubeURL(url) {
  const patterns = [
    /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+/,
    /^(https?:\/\/)?(www\.)?youtube\.com\/watch\?v=[\w-]+/,
    /^(https?:\/\/)?(www\.)?youtu\.be\/[\w-]+/,
  ];
  return patterns.some(p => p.test(url));
}

function pollStatus(jobId) {
  pollInterval = setInterval(async () => {
    try {
      const res = await fetch(`/api/status/${jobId}`, { signal: abortController.signal });
      const job = await res.json();

      if (job.status === "running") {
        statusText.textContent = job.message || "Working...";
        if (job.progress !== undefined) {
          progressPercent.textContent = `${job.progress}%`;
          progressBar.style.width = `${job.progress}%`;
        }
        if (job.step) {
          updateStep(job.step, "active");
          // Mark previous steps as done
          const steps = ["download", "audio", "analyze", "render", "complete"];
          const currentIdx = steps.indexOf(job.step);
          for (let i = 0; i < currentIdx; i++) {
            updateStep(steps[i], "done");
          }
        }
      } else if (job.status === "done") {
        clearInterval(pollInterval);
        updateStep("complete", "done");
        statusEl.classList.add("hidden");
        renderResults(job.results);
        resetButton();
      } else if (job.status === "error") {
        clearInterval(pollInterval);
        updateStep(job.step || "render", "error");
        showError(job.error || "Processing fail ho gayi.");
        resetButton();
      }
    } catch (err) {
      if (err.name === "AbortError") return;
      clearInterval(pollInterval);
      showError("Status check nahi ho saka.");
      resetButton();
    }
  }, 1500);
}

function updateStep(stepName, state) {
  const step = document.querySelector(`.step[data-step="${stepName}"]`);
  if (!step) return;

  step.classList.remove("waiting", "active", "done", "error");
  step.classList.add(state);

  const icon = step.querySelector(".step-icon");
  switch (state) {
    case "waiting":
      icon.textContent = "⏳";
      break;
    case "active":
      icon.textContent = "▶";
      break;
    case "done":
      icon.textContent = "✓";
      break;
    case "error":
      icon.textContent = "✗";
      break;
  }
}

function resetSteps() {
  document.querySelectorAll(".step").forEach(step => {
    step.classList.remove("active", "done", "error");
    step.classList.add("waiting");
    step.querySelector(".step-icon").textContent = "⏳";
  });
}

function renderResults(results) {
  resultsEl.classList.remove("hidden");
  resultsCount.textContent = `${results.length} clip${results.length !== 1 ? "s" : ""}`;

  results.forEach(clip => {
    const card = document.createElement("div");
    card.className = "clip-card";

    const aspectRatio = clip.format === "vertical" ? "9/16" : 
                        clip.format === "square" ? "1/1" : "16/9";
    const platform = clip.format === "vertical" ? "TikTok · Reels · Shorts" :
                     clip.format === "square" ? "Instagram Feed" :
                     "YouTube · Facebook";

    card.innerHTML = `
      <div class="clip-preview" style="aspect-ratio: ${aspectRatio}">
        <video controls preload="metadata" src="/clips/${clip.filename}"></video>
      </div>
      <div class="clip-meta">
        <div class="clip-header">
          <span class="clip-fmt">${clip.format} · ${clip.quality}</span>
          <span class="clip-time">${clip.timestamp}</span>
        </div>
        <div class="clip-platform">${platform}</div>
        <a class="clip-dl" href="/api/download/${clip.filename}" download="${clip.filename}">
          <span>Download MP4</span>
          <span>↓</span>
        </a>
      </div>
    `;
    clipGrid.appendChild(card);
  });
}

function showError(msg) {
  errorEl.textContent = msg;
  errorEl.classList.remove("hidden");
}

function resetButton() {
  submitBtn.disabled = false;
}

// Cleanup on page unload
window.addEventListener("beforeunload", () => {
  if (pollInterval) clearInterval(pollInterval);
  if (abortController) abortController.abort();
});
