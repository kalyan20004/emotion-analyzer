document.addEventListener("DOMContentLoaded", () => {
  const analyzeBtn = document.getElementById("analyzeBtn");
  const clearBtn = document.getElementById("clearBtn");
  const inputText = document.getElementById("inputText");
  const result = document.getElementById("result");
  const loadingIndicator = document.getElementById("loadingIndicator");
  const resultContainer = document.getElementById("resultContainer");
  const initialState = document.getElementById("initialState");

  // Add focus to textarea when the page loads
  setTimeout(() => {
    inputText.focus();
  }, 500);

  // Show input character count
  let charCountEl = document.createElement("div");
  charCountEl.className = "char-count";
  charCountEl.innerHTML = "0 characters";
  inputText.parentNode.insertBefore(charCountEl, inputText.nextSibling);

  inputText.addEventListener("input", () => {
    const length = inputText.value.length;
    charCountEl.innerHTML = `${length} character${length !== 1 ? "s" : ""}`;

    // Change color based on character count
    if (length > 200) {
      charCountEl.style.color = "var(--neon-tertiary)";
      charCountEl.style.textShadow = "0 0 5px var(--neon-tertiary)";
    } else if (length > 0) {
      charCountEl.style.color = "var(--muted-text)";
      charCountEl.style.textShadow = "none";
    } else {
      charCountEl.style.color = "var(--muted-text)";
      charCountEl.style.textShadow = "none";
    }
  });

  analyzeBtn.addEventListener("click", async () => {
    const text = inputText.value.trim();

    if (!text) {
      showToast("Please enter some text to analyze.", "warning");
      inputText.focus();
      return;
    }

    // Show loading indicator
    result.classList.add("hidden");
    initialState.classList.add("hidden");
    loadingIndicator.classList.remove("hidden");

    try {
      console.log("Sending request to Flask API...");
      // Updated to use Flask endpoint at port 5000
      const response = await fetch("/predict", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ text }),
      });

      console.log("Response status:", response.status);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.error ||
            `Server error: ${response.status} ${response.statusText}`
        );
      }

      const data = await response.json();
      console.log("Data received:", data);

      // Display the results
      displayResults(data);

      // Smoothly scroll to results
      resultContainer.scrollIntoView({ behavior: "smooth", block: "start" });

      // Show success toast
      showToast("Analysis complete!", "success");
    } catch (err) {
      console.error("Error:", err);
      result.innerHTML = `
        <div class="error-message">
          <h3><i class="fas fa-exclamation-triangle"></i> Error</h3>
          <p>${err.message}</p>
          <p>Please try again or check if the server is running properly.</p>
        </div>
      `;
      result.classList.remove("hidden");
      showToast("Analysis failed. Please try again.", "error");
    } finally {
      loadingIndicator.classList.add("hidden");
    }
  });

  clearBtn.addEventListener("click", () => {
    inputText.value = "";
    result.innerHTML = "";
    result.classList.add("hidden");
    initialState.classList.remove("hidden");
    charCountEl.innerHTML = "0 characters";
    charCountEl.style.color = "var(--muted-text)";
    charCountEl.style.textShadow = "none";
    inputText.focus();
  });

  function displayResults(data) {
    if (!data.emotions || Object.keys(data.emotions).length === 0) {
      result.innerHTML = `
        <div class="no-emotions">
          <h3><i class="fas fa-search"></i> No strong emotions detected</h3>
          <p>Try a different text with more emotional content.</p>
        </div>
      `;
      result.classList.remove("hidden");
      initialState.classList.add("hidden");
      return;
    }

    let html = `<h3><i class="fas fa-heart-pulse"></i> Detected Emotions:</h3>`;
    html += `<div class="emotions-summary">Analyzing text: "${truncateText(
      inputText.value.trim(),
      60
    )}"</div>`;
    html += "<div class='emotions-list'>";

    // Get emotions and sort by probability (highest first)
    const emotions = Object.entries(data.emotions).sort((a, b) => b[1] - a[1]);

    // Calculate the dominant emotion for highlighting
    const dominantEmotion = emotions[0][0];
    console.log("Dominant emotion:", dominantEmotion);

    // Process each emotion
    emotions.forEach(([emotion, probability], index) => {
      const percentage = (probability * 100).toFixed(1);
      const color = getColorForEmotion(emotion);
      const isMainEmotion = index === 0; // Highlight the strongest emotion

      const barClass = isMainEmotion
        ? "emotion-bar main-emotion"
        : "emotion-bar";
      const delay = index * 0.1;

      html += `
        <div class="${barClass}" style="animation-delay: ${delay}s">
          <div class="emotion-label">${capitalize(emotion)}</div>
          <div class="emotion-progress">
            <div class="progress-fill" 
                 style="width: ${percentage}%; background-color: ${color}; box-shadow: 0 0 10px ${color};">
            </div>
          </div>
          <div class="emotion-value">${percentage}%</div>
        </div>
      `;
    });

    // Add summary of dominant emotions
    if (emotions.length > 1) {
      const topEmotions = emotions
        .slice(0, 3)
        .map(([emotion]) => capitalize(emotion))
        .join(", ");
      html += `<div class="emotions-summary-footer">Primary emotions: ${topEmotions}</div>`;
    }

    html += "</div>";
    result.innerHTML = html;
    result.classList.remove("hidden");
    initialState.classList.add("hidden");
  }

  function capitalize(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
  }

  function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substr(0, maxLength) + "...";
  }

  function getColorForEmotion(emotion) {
    // Neon colors for emotions
    const colors = {
      joy: "#00ff9f", // Neon Green
      happiness: "#00ff9f", // Neon Green
      sadness: "#00f3ff", // Neon Blue
      anger: "#fd00ff", // Neon Magenta
      fear: "#b300ff", // Neon Purple
      disgust: "#d4ff00", // Neon Lime
      surprise: "#ff79c6", // Neon Pink
      anticipation: "#ff8000", // Neon Orange
      trust: "#00f3ff", // Neon Blue
      love: "#fd00ff", // Neon Magenta
      optimism: "#00f3ff", // Neon Blue
      pessimism: "#b8b8ff", // Neon Lavender
      neutral: "#a8b3cf", // Muted Blue
      excitement: "#ff8000", // Neon Orange
      gratitude: "#d4ff00", // Neon Lime
      pride: "#ffff00", // Neon Yellow
      confusion: "#b300ff", // Neon Purple
      embarrassment: "#fd00ff", // Neon Magenta
      guilt: "#ff8000", // Neon Orange
      shame: "#fd00ff", // Neon Magenta
      anxiety: "#b300ff", // Neon Purple
      desire: "#fd00ff", // Neon Magenta
      jealousy: "#00ff9f", // Neon Green
      disappointment: "#b8b8ff", // Neon Lavender
      amusement: "#00f3ff", // Neon Blue
      contentment: "#00f3ff", // Neon Blue
      relief: "#00ff9f", // Neon Green
      boredom: "#b8b8ff", // Neon Lavender
      frustration: "#fd00ff", // Neon Magenta
    };

    return colors[emotion.toLowerCase()] || "#00f3ff"; // Default to neon blue
  }

  // Toast notification system
  function showToast(message, type = "info") {
    // Remove existing toast if any
    const existingToast = document.querySelector(".toast-notification");
    if (existingToast) {
      existingToast.remove();
    }

    // Create new toast
    const toast = document.createElement("div");
    toast.className = `toast-notification toast-${type}`;

    let icon;
    switch (type) {
      case "success":
        icon = `<i class="fas fa-check-circle"></i>`;
        break;
      case "error":
        icon = `<i class="fas fa-exclamation-circle"></i>`;
        break;
      case "warning":
        icon = `<i class="fas fa-exclamation-triangle"></i>`;
        break;
      default:
        icon = `<i class="fas fa-info-circle"></i>`;
    }

    toast.innerHTML = `
      ${icon}
      <span>${message}</span>
    `;

    document.body.appendChild(toast);

    // Show the toast
    setTimeout(() => {
      toast.classList.add("show");
    }, 10);

    // Auto hide after 3 seconds
    setTimeout(() => {
      toast.classList.remove("show");
      setTimeout(() => {
        toast.remove();
      }, 300);
    }, 3000);
  }

  // Add keyboard shortcut - Ctrl+Enter or Cmd+Enter to analyze
  inputText.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      analyzeBtn.click();
      e.preventDefault();
    }
  });

  // Example usage if you want to add some sample text for easy testing
  document.addEventListener("keydown", (e) => {
    // Alt+S to add sample text (hidden feature)
    if (e.altKey && e.key === "s") {
      inputText.value =
        "I'm feeling really happy and excited about this new project! It's been a challenging journey, but I'm proud of what we've accomplished so far.";
      inputText.dispatchEvent(new Event("input"));
      e.preventDefault();
    }
  });

  // Add neon particle animation effect
  function animateParticles() {
    const particles = document.querySelectorAll(".neon-particles span");
    particles.forEach((particle) => {
      // Reset particle position once it's animated out
      particle.addEventListener("animationiteration", () => {
        particle.style.left = Math.random() * 100 + "%";
        particle.style.top = Math.random() * 100 + "%";
      });
    });
  }

  animateParticles();
});
