let selectedFiles = [];

document.addEventListener("alpine:init", () => {});

function switchTab(tab) {
  const sessionsTab = document.getElementById("sessionsTab");
  const filesTab = document.getElementById("filesTab");
  const sessionsContent = document.getElementById("sessionsContent");
  const filesContent = document.getElementById("filesContent");

  if (tab === "sessions") {
    sessionsTab.classList.add("border-teal-600", "text-teal-600");
    sessionsTab.classList.remove("border-transparent", "text-gray-500");
    filesTab.classList.add("border-transparent", "text-gray-500");
    filesTab.classList.remove("border-teal-600", "text-teal-600");
    sessionsContent.classList.remove("hidden");
    filesContent.classList.add("hidden");
  } else {
    filesTab.classList.add("border-teal-600", "text-teal-600");
    filesTab.classList.remove("border-transparent", "text-gray-500");
    sessionsTab.classList.add("border-transparent", "text-gray-500");
    sessionsTab.classList.remove("border-teal-600", "text-teal-600");
    filesContent.classList.remove("hidden");
    sessionsContent.classList.add("hidden");
  }
}

function handleFileSelection(event) {
  const files = Array.from(event.target.files);
  const duplicates = [];

  files.forEach((file) => {
    const isDuplicateInSelection = selectedFiles.some(
      (f) =>
        f.name === file.name &&
        f.size === file.size &&
        f.lastModified === file.lastModified
    );

    const isDuplicateInDatabase = DJANGO_DATA.existingFiles.includes(file.name);

    if (isDuplicateInDatabase) {
      duplicates.push(file.name);
    } else if (!isDuplicateInSelection) {
      selectedFiles.push(file);
    }
  });

  if (duplicates.length > 0) {
    alert(
      `⚠️ The following file(s) have already been uploaded:\n\n${duplicates.join(
        "\n"
      )}\n\nThey will not be added to the upload list.`
    );
  }

  updateFileList();
  event.target.value = "";
}

function removeFile(index) {
  selectedFiles.splice(index, 1);
  updateFileList();
}

function clearAllFiles() {
  selectedFiles = [];
  updateFileList();
}

function updateFileList() {
  const fileListContainer = document.getElementById("fileListContainer");
  const clearAllBtn = document.getElementById("clearAllBtn");

  if (selectedFiles.length === 0) {
    fileListContainer.innerHTML =
      '<div class="text-gray-500 text-center">No files selected</div>';
    clearAllBtn.classList.add("hidden");
    return;
  }

  clearAllBtn.classList.remove("hidden");

  let html = "";
  let totalSize = 0;
  let validCount = 0;

  selectedFiles.forEach((file, index) => {
    const isValid = file.name.toLowerCase().endsWith(".xlsb");
    if (isValid) validCount++;

    const iconClass = isValid ? "text-green-500" : "text-red-500";
    const icon = isValid ? "✓" : "✗";
    const sizeInMB = (file.size / (1024 * 1024)).toFixed(2);
    totalSize += file.size;

    html += `
      <div class="flex items-center justify-between p-3 mb-2 bg-white rounded-lg border ${
        isValid ? "border-green-200" : "border-red-200"
      }">
        <div class="flex items-center gap-3 flex-1 min-w-0">
          <span class="${iconClass} font-bold text-lg">${icon}</span>
          <div class="flex-1 min-w-0">
            <div class="${
              isValid ? "text-gray-700" : "text-red-600"
            } font-medium truncate" title="${file.name}">
              ${index + 1}. ${file.name}
            </div>
            <div class="text-xs text-gray-500">${sizeInMB} MB</div>
          </div>
        </div>
        <div class="flex items-center gap-2">
          ${
            !isValid
              ? '<span class="text-red-500 text-xs whitespace-nowrap mr-2">Invalid</span>'
              : ""
          }
          <button 
            type="button"
            onclick="removeFile(${index})"
            class="p-1 text-red-600 hover:bg-red-50 rounded transition"
            title="Remove file">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    `;
  });

  const totalSizeInMB = (totalSize / (1024 * 1024)).toFixed(2);

  html += `
    <div class="mt-3 pt-3 border-t border-gray-300">
      <div class="flex justify-between text-sm">
        <span class="text-gray-600">
          <strong>${validCount}</strong> of <strong>${selectedFiles.length}</strong> files valid
        </span>
        <span class="text-gray-600">
          Total: <strong>${totalSizeInMB} MB</strong>
        </span>
      </div>
    </div>
  `;

  fileListContainer.innerHTML = html;
}

function closeUploadModal() {
  document.getElementById("uploadModal").classList.add("hidden");
}

document.getElementById("uploadForm").addEventListener("submit", function (e) {
  e.preventDefault();

  if (selectedFiles.length === 0) {
    alert("Please select at least one file to upload.");
    return false;
  }

  const invalidFiles = selectedFiles.filter(
    (f) => !f.name.toLowerCase().endsWith(".xlsb")
  );
  if (invalidFiles.length > 0) {
    alert(
      `Please remove invalid files before uploading. ${
        invalidFiles.length
      } invalid file(s) detected:\n\n${invalidFiles
        .map((f) => f.name)
        .join("\n")}`
    );
    return false;
  }

  const formData = new FormData();
  const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;
  formData.append("csrfmiddlewaretoken", csrfToken);

  const autoParse = document.querySelector("[name=auto_parse]").checked;
  if (autoParse) {
    formData.append("auto_parse", "on");
  }

  selectedFiles.forEach((file) => {
    formData.append("files", file);
  });

  const submitBtn = document.getElementById("uploadSubmitBtn");
  submitBtn.disabled = true;
  submitBtn.innerHTML = "⏳ Uploading...";
  submitBtn.classList.add("opacity-50", "cursor-not-allowed");

  fetch(this.action, {
    method: "POST",
    body: formData,
  })
    .then((response) => {
      if (response.ok) {
        window.location.reload();
      } else {
        throw new Error("Upload failed");
      }
    })
    .catch((error) => {
      alert("Upload failed. Please try again.");
      submitBtn.disabled = false;
      submitBtn.innerHTML = "📤 Upload Files";
      submitBtn.classList.remove("opacity-50", "cursor-not-allowed");
    });
});

function toggleSelectAll(checkbox) {
  const checkboxes = document.querySelectorAll(".session-checkbox");
  checkboxes.forEach((cb) => {
    cb.checked = checkbox.checked;
  });
  updateSelectedCount();
}

function updateSelectedCount() {
  const checkboxes = document.querySelectorAll(".session-checkbox:checked");
  const count = checkboxes.length;
  const selectedCount = document.getElementById("selectedCount");
  const selectedNumber = document.getElementById("selectedNumber");
  const bulkDeleteBtn = document.getElementById("bulkDeleteBtn");
  const selectAll = document.getElementById("selectAll");

  selectedNumber.textContent = count;

  if (count > 0) {
    selectedCount.style.display = "inline";
    bulkDeleteBtn.style.display = "flex";
  } else {
    selectedCount.style.display = "none";
    bulkDeleteBtn.style.display = "none";
  }

  const allCheckboxes = document.querySelectorAll(".session-checkbox");
  selectAll.checked =
    allCheckboxes.length > 0 && count === allCheckboxes.length;
  selectAll.indeterminate = count > 0 && count < allCheckboxes.length;

  updateStats();
  updateDownloadLinks();
}

function updateStats() {
  const checkboxes = document.querySelectorAll(".session-checkbox:checked");
  const count = checkboxes.length;

  if (count === 0) {
    document.getElementById("statsTitleSessions").textContent =
      "Total Sessions";
    document.getElementById("statsTitleHours").textContent = "Total Hours";
    document.getElementById("statsTitleAvg").textContent = "Avg per Session";

    document.getElementById("statsValueSessions").textContent =
      DJANGO_DATA.originalStats.totalSessions;
    document.getElementById("statsValueHours").textContent =
      DJANGO_DATA.originalStats.totalHours + "h";
    document.getElementById("statsValueAvg").textContent =
      DJANGO_DATA.originalStats.avgPerSession + "h";
  } else {
    let totalMinutes = 0;
    checkboxes.forEach((cb) => {
      const minutes = parseInt(cb.getAttribute("data-minutes") || 0);
      totalMinutes += minutes;
    });

    const totalHours = (totalMinutes / 60).toFixed(2);
    const avgPerSession = (totalMinutes / count / 60).toFixed(2);

    document.getElementById("statsTitleSessions").textContent =
      "Selected Sessions";
    document.getElementById("statsTitleHours").textContent = "Selected Hours";
    document.getElementById("statsTitleAvg").textContent = "Avg (Selected)";

    document.getElementById("statsValueSessions").textContent = count;
    document.getElementById("statsValueHours").textContent = totalHours + "h";
    document.getElementById("statsValueAvg").textContent = avgPerSession + "h";
  }
}

function updateDownloadLinks() {
  const selectedCheckboxes = document.querySelectorAll(
    ".session-checkbox:checked"
  );
  const selectedCount = selectedCheckboxes.length;
  const selectedIds = Array.from(selectedCheckboxes).map((cb) => cb.value);

  const hasFilters = DJANGO_DATA.hasFilters;
  const filterCount = DJANGO_DATA.filterCount;
  const baseUrl = DJANGO_DATA.baseUrl;

  let labelText = "All sessions";
  let csvUrl, xlsxUrl, pdfUrl;

  if (selectedCount > 0) {
    labelText = `Selected (${selectedCount})`;
    const sessionIdsParam = selectedIds
      .map((id) => `session_ids=${id}`)
      .join("&");
    csvUrl = `${baseUrl}?format=csv&scope=selected&${sessionIdsParam}`;
    xlsxUrl = `${baseUrl}?format=xlsx&scope=selected&${sessionIdsParam}`;
    pdfUrl = `${baseUrl}?format=pdf&scope=selected&${sessionIdsParam}`;
  } else if (hasFilters) {
    labelText = `Filtered (${filterCount})`;

    let filterParams = "";
    if (DJANGO_DATA.filterParams.search) {
      filterParams += `search=${encodeURIComponent(
        DJANGO_DATA.filterParams.search
      )}&`;
    }
    if (DJANGO_DATA.filterParams.subject) {
      filterParams += `subject=${DJANGO_DATA.filterParams.subject}&`;
    }
    if (DJANGO_DATA.filterParams.dateFrom) {
      filterParams += `date_from=${DJANGO_DATA.filterParams.dateFrom}&`;
    }
    if (DJANGO_DATA.filterParams.dateTo) {
      filterParams += `date_to=${DJANGO_DATA.filterParams.dateTo}&`;
    }
    if (DJANGO_DATA.filterParams.timeFrom) {
      filterParams += `time_from=${DJANGO_DATA.filterParams.timeFrom}&`;
    }
    if (DJANGO_DATA.filterParams.timeTo) {
      filterParams += `time_to=${DJANGO_DATA.filterParams.timeTo}&`;
    }

    filterParams = filterParams.replace(/&$/, "");

    csvUrl = `${baseUrl}?format=csv&scope=filtered&${filterParams}`;
    xlsxUrl = `${baseUrl}?format=xlsx&scope=filtered&${filterParams}`;
    pdfUrl = `${baseUrl}?format=pdf&scope=filtered&${filterParams}`;
  } else {
    labelText = "All sessions";
    csvUrl = `${baseUrl}?format=csv&scope=all`;
    xlsxUrl = `${baseUrl}?format=xlsx&scope=all`;
    pdfUrl = `${baseUrl}?format=pdf&scope=all`;
  }

  document.getElementById("csvLabel").textContent = labelText;
  document.getElementById("xlsxLabel").textContent = labelText;
  document.getElementById("pdfLabel").textContent = labelText;

  document.getElementById("csvDownloadLink").href = csvUrl;
  document.getElementById("xlsxDownloadLink").href = xlsxUrl;
  document.getElementById("pdfDownloadLink").href = pdfUrl;
}

function bulkDeleteSessions() {
  const checkboxes = document.querySelectorAll(".session-checkbox:checked");
  const sessionIds = Array.from(checkboxes).map((cb) => cb.value);

  if (sessionIds.length === 0) {
    alert("Please select sessions to delete");
    return;
  }

  if (
    confirm(`Are you sure you want to delete ${sessionIds.length} session(s)?`)
  ) {
    const form = document.createElement("form");
    form.method = "POST";
    form.action = '{% url "delete_sessions" %}';

    const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]");
    if (csrfToken) {
      const csrfInput = document.createElement("input");
      csrfInput.type = "hidden";
      csrfInput.name = "csrfmiddlewaretoken";
      csrfInput.value = csrfToken.value;
      form.appendChild(csrfInput);
    }

    sessionIds.forEach((id) => {
      const input = document.createElement("input");
      input.type = "hidden";
      input.name = "session_ids";
      input.value = id;
      form.appendChild(input);
    });

    document.body.appendChild(form);
    form.submit();
  }
}

function deleteSingleSession(sessionId) {
  if (confirm("Are you sure you want to delete this session?")) {
    const form = document.createElement("form");
    form.method = "POST";
    form.action = `{% url "delete_session" 0 %}`.replace("0", sessionId);

    const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]");
    if (csrfToken) {
      const csrfInput = document.createElement("input");
      csrfInput.type = "hidden";
      csrfInput.name = "csrfmiddlewaretoken";
      csrfInput.value = csrfToken.value;
      form.appendChild(csrfInput);
    }

    document.body.appendChild(form);
    form.submit();
  }
}

const uploadModal = document.getElementById("uploadModal");
const dropZone = document.getElementById("dropZone");

["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
  dropZone.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
  e.preventDefault();
  e.stopPropagation();
}

["dragenter", "dragover"].forEach((eventName) => {
  dropZone.addEventListener(
    eventName,
    () => {
      dropZone.classList.add("border-teal-500", "bg-teal-50");
    },
    false
  );
});

["dragleave", "drop"].forEach((eventName) => {
  dropZone.addEventListener(
    eventName,
    () => {
      dropZone.classList.remove("border-teal-500", "bg-teal-50");
    },
    false
  );
});

dropZone.addEventListener(
  "drop",
  (e) => {
    const dt = e.dataTransfer;
    const files = Array.from(dt.files);
    const duplicates = [];

    files.forEach((file) => {
      const isDuplicateInSelection = selectedFiles.some(
        (f) =>
          f.name === file.name &&
          f.size === file.size &&
          f.lastModified === file.lastModified
      );

      const isDuplicateInDatabase = DJANGO_DATA.existingFiles.includes(
        file.name
      );

      if (isDuplicateInDatabase) {
        duplicates.push(file.name);
      } else if (!isDuplicateInSelection) {
        selectedFiles.push(file);
      }
    });

    if (duplicates.length > 0) {
      alert(
        `⚠️ The following file(s) have already been uploaded:\n\n${duplicates.join(
          "\n"
        )}\n\nThey will not be added to the upload list.`
      );
    }

    updateFileList();
  },
  false
);

document.addEventListener("DOMContentLoaded", function () {
  updateDownloadLinks();
  updateStats();
});
