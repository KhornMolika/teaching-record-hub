let selectedFiles = [];

document.addEventListener("alpine:init", () => {});

// Tab switching functionality with URL management
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

    // Update URL without reload
    const url = new URL(window.location);
    url.searchParams.delete("tab");
    window.history.replaceState({}, "", url);
  } else {
    filesTab.classList.add("border-teal-600", "text-teal-600");
    filesTab.classList.remove("border-transparent", "text-gray-500");
    sessionsTab.classList.add("border-transparent", "text-gray-500");
    sessionsTab.classList.remove("border-teal-600", "text-teal-600");
    filesContent.classList.remove("hidden");
    sessionsContent.classList.add("hidden");

    // Update URL without reload
    const url = new URL(window.location);
    url.searchParams.set("tab", "files");
    window.history.replaceState({}, "", url);
  }
}

function handleFileSelection(event) {
  const files = Array.from(event.target.files);

  files.forEach((file) => {
    const isDuplicateInSelection = selectedFiles.some(
      (f) =>
        f.name === file.name &&
        f.size === file.size &&
        f.lastModified === file.lastModified
    );

    if (!isDuplicateInSelection) {
      // Check if file is valid format (XLSB or ZIP)
      const fileName = file.name.toLowerCase();
      const isXlsb = fileName.endsWith(".xlsb");
      const isZip = fileName.endsWith(".zip");
      const isValidFormat = isXlsb || isZip;

      // Only check database duplicates for XLSB files, not ZIP files
      const isDuplicateInDatabase =
        isXlsb && DJANGO_DATA.existingFiles.includes(file.name);

      selectedFiles.push({
        file: file,
        name: file.name,
        size: file.size,
        lastModified: file.lastModified,
        isDuplicate: isDuplicateInDatabase,
        isValid: isValidFormat,
        isZip: isZip,
      });
    }
  });

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
      '<div class="text-gray-500 text-center py-4">No files selected</div>';
    clearAllBtn.classList.add("hidden");
    return;
  }

  clearAllBtn.classList.remove("hidden");

  let html = "";
  let totalSize = 0;
  let validCount = 0;
  let duplicateCount = 0;

  selectedFiles.forEach((fileObj, index) => {
    const { file, name, size, isDuplicate, isValid, isZip } = fileObj;

    if (isValid && !isDuplicate) validCount++;
    if (isDuplicate) duplicateCount++;

    let statusIcon, statusClass, borderClass, statusLabel, fileIcon;

    if (isDuplicate) {
      statusIcon = "⚠️";
      statusClass = "text-orange-600";
      borderClass = "border-orange-300 bg-orange-50";
      statusLabel =
        '<span class="text-orange-600 text-xs font-semibold whitespace-nowrap mr-2">Already Uploaded</span>';
    } else if (!isValid) {
      statusIcon = "✗";
      statusClass = "text-red-600";
      borderClass = "border-red-300 bg-red-50";
      statusLabel =
        '<span class="text-red-600 text-xs font-semibold whitespace-nowrap mr-2">Invalid Format</span>';
    } else {
      statusIcon = "✓";
      statusClass = "text-green-600";
      borderClass = "border-green-200 bg-white";
      statusLabel = "";
    }

    // Different icon for ZIP files
    if (isZip && isValid) {
      fileIcon = "📦"; // Package emoji for ZIP
      statusLabel =
        '<span class="text-blue-600 text-xs font-semibold whitespace-nowrap mr-2">ZIP Archive</span>';
    } else {
      fileIcon = statusIcon;
    }

    const sizeInMB = (size / (1024 * 1024)).toFixed(2);
    totalSize += size;

    html += `
      <div class="flex items-center justify-between p-3 mb-2 rounded-lg border ${borderClass} transition-all">
        <div class="flex items-center gap-3 flex-1 min-w-0">
          <span class="${statusClass} font-bold text-lg">${fileIcon}</span>
          <div class="flex-1 min-w-0">
            <div class="${
              isDuplicate
                ? "text-orange-700"
                : isValid
                ? "text-gray-700"
                : "text-red-600"
            } font-medium truncate" title="${name}">
              ${index + 1}. ${name}
            </div>
            <div class="text-xs text-gray-500">${sizeInMB} MB</div>
          </div>
        </div>
        <div class="flex items-center gap-2">
          ${statusLabel}
          <button 
            type="button"
            onclick="removeFile(${index})"
            class="p-1.5 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded transition"
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
  const invalidCount = selectedFiles.length - validCount - duplicateCount;

  html += `
    <div class="mt-4 pt-4 border-t border-gray-300 space-y-2">
      <div class="flex justify-between text-sm">
        <div class="space-y-1">
          <div class="text-gray-700">
            <span class="inline-flex items-center gap-1">
              <span class="text-green-600 font-bold">✓</span>
              <strong class="text-green-700">${validCount}</strong> ready to upload
            </span>
          </div>
          ${
            duplicateCount > 0
              ? `
            <div class="text-orange-600">
              <span class="inline-flex items-center gap-1">
                <span class="font-bold">⚠️</span>
                <strong>${duplicateCount}</strong> already uploaded
              </span>
            </div>
          `
              : ""
          }
          ${
            invalidCount > 0
              ? `
            <div class="text-red-600">
              <span class="inline-flex items-center gap-1">
                <span class="font-bold">✗</span>
                <strong>${invalidCount}</strong> invalid format
              </span>
            </div>
          `
              : ""
          }
        </div>
        <div class="text-right">
          <div class="text-gray-600">
            Total: <strong>${totalSizeInMB} MB</strong>
          </div>
          <div class="text-gray-500 text-xs">
            ${selectedFiles.length} file${
    selectedFiles.length !== 1 ? "s" : ""
  } selected
          </div>
        </div>
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

  const validFiles = selectedFiles.filter((f) => f.isValid && !f.isDuplicate);
  const duplicateFiles = selectedFiles.filter((f) => f.isDuplicate);
  const invalidFiles = selectedFiles.filter((f) => !f.isValid);

  if (validFiles.length === 0) {
    let message = "No valid files to upload.\n\n";
    if (duplicateFiles.length > 0) {
      message += `${duplicateFiles.length} file(s) already uploaded.\n`;
    }
    if (invalidFiles.length > 0) {
      message += `${invalidFiles.length} file(s) have invalid format.\n`;
    }
    message +=
      "\nPlease add new XLSB or ZIP files or remove invalid/duplicate files.";
    alert(message);
    return false;
  }

  if (duplicateFiles.length > 0 || invalidFiles.length > 0) {
    let message = `Uploading ${validFiles.length} valid file(s).\n\n`;
    if (duplicateFiles.length > 0) {
      message += `⚠️ Skipping ${duplicateFiles.length} duplicate file(s):\n`;
      message += duplicateFiles.map((f) => `  • ${f.name}`).join("\n") + "\n\n";
    }
    if (invalidFiles.length > 0) {
      message += `✗ Skipping ${invalidFiles.length} invalid file(s):\n`;
      message += invalidFiles.map((f) => `  • ${f.name}`).join("\n") + "\n\n";
    }
    message += "Continue with upload?";

    if (!confirm(message)) {
      return false;
    }
  }

  const formData = new FormData();
  const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;
  formData.append("csrfmiddlewaretoken", csrfToken);

  const autoParse = document.querySelector("[name=auto_parse]").checked;
  if (autoParse) {
    formData.append("auto_parse", "on");
  }

  validFiles.forEach((fileObj) => {
    formData.append("files", fileObj.file);
  });

  const submitBtn = document.getElementById("uploadSubmitBtn");
  submitBtn.disabled = true;
  submitBtn.innerHTML = `⏳ Uploading ${validFiles.length} file(s)...`;
  submitBtn.classList.add("opacity-50", "cursor-not-allowed");

  fetch(this.action, {
    method: "POST",
    body: formData,
  })
    .then((response) => {
      if (response.ok) {
        // Reload to current tab (files tab since upload is from files tab)
        const url = new URL(window.location);
        url.searchParams.set("tab", "files");
        window.location.href = url.toString();
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

// Bulk file selection and deletion functions
function toggleSelectAllFiles(checkbox) {
  const checkboxes = document.querySelectorAll(".file-checkbox");
  checkboxes.forEach((cb) => {
    cb.checked = checkbox.checked;
  });
  updateSelectedFilesCount();
}

function updateSelectedFilesCount() {
  const checkboxes = document.querySelectorAll(".file-checkbox:checked");
  const count = checkboxes.length;
  const selectedFilesCount = document.getElementById("selectedFilesCount");
  const selectedFilesNumber = document.getElementById("selectedFilesNumber");
  const bulkDeleteFilesBtn = document.getElementById("bulkDeleteFilesBtn");
  const selectAllFiles = document.getElementById("selectAllFiles");

  selectedFilesNumber.textContent = count;

  if (count > 0) {
    selectedFilesCount.style.display = "inline";
    bulkDeleteFilesBtn.style.display = "flex";
  } else {
    selectedFilesCount.style.display = "none";
    bulkDeleteFilesBtn.style.display = "none";
  }

  const allCheckboxes = document.querySelectorAll(".file-checkbox");
  selectAllFiles.checked =
    allCheckboxes.length > 0 && count === allCheckboxes.length;
  selectAllFiles.indeterminate = count > 0 && count < allCheckboxes.length;
}

function bulkDeleteFiles() {
  const checkboxes = document.querySelectorAll(".file-checkbox:checked");
  const fileIds = Array.from(checkboxes).map((cb) => cb.value);

  if (fileIds.length === 0) {
    alert("Please select files to delete");
    return;
  }

  const confirmMessage =
    fileIds.length === 1
      ? "Are you sure you want to delete this file and all its sessions?"
      : `Are you sure you want to delete ${fileIds.length} files and all their sessions?`;

  if (confirm(confirmMessage)) {
    // Delete files sequentially
    deleteFilesSequentially(fileIds);
  }
}

async function deleteFilesSequentially(fileIds) {
  const bulkDeleteBtn = document.getElementById("bulkDeleteFilesBtn");
  const originalHTML = bulkDeleteBtn.innerHTML;

  bulkDeleteBtn.disabled = true;
  bulkDeleteBtn.innerHTML = `
    <svg class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
    Deleting...
  `;
  bulkDeleteBtn.classList.add("opacity-50", "cursor-not-allowed");

  try {
    let successCount = 0;

    for (const fileId of fileIds) {
      const deleteForm = document.querySelector(`.delete-file-form-${fileId}`);
      if (deleteForm) {
        const formData = new FormData(deleteForm);

        try {
          const response = await fetch(deleteForm.action, {
            method: "POST",
            body: formData,
          });

          if (response.ok) {
            successCount++;
            // Fade out the row
            const row = document.querySelector(`[data-file-id="${fileId}"]`);
            if (row) {
              row.style.opacity = "0.3";
            }
          }
        } catch (error) {
          console.error(`Failed to delete file ${fileId}:`, error);
        }
      }
    }

    if (successCount > 0) {
      const message =
        successCount === 1
          ? "1 file deleted successfully!"
          : `${successCount} files deleted successfully!`;
      alert(message);

      // Reload to current tab (files tab)
      const url = new URL(window.location);
      url.searchParams.set("tab", "files");
      window.location.href = url.toString();
    } else {
      alert("Failed to delete files. Please try again.");
      bulkDeleteBtn.disabled = false;
      bulkDeleteBtn.innerHTML = originalHTML;
      bulkDeleteBtn.classList.remove("opacity-50", "cursor-not-allowed");
    }
  } catch (error) {
    console.error("Error deleting files:", error);
    alert("An error occurred while deleting files.");
    bulkDeleteBtn.disabled = false;
    bulkDeleteBtn.innerHTML = originalHTML;
    bulkDeleteBtn.classList.remove("opacity-50", "cursor-not-allowed");
  }
}

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

    files.forEach((file) => {
      const isDuplicateInSelection = selectedFiles.some(
        (f) =>
          f.name === file.name &&
          f.size === file.size &&
          f.lastModified === file.lastModified
      );

      if (!isDuplicateInSelection) {
        // Check if file is valid format (XLSB or ZIP)
        const fileName = file.name.toLowerCase();
        const isXlsb = fileName.endsWith(".xlsb");
        const isZip = fileName.endsWith(".zip");
        const isValidFormat = isXlsb || isZip;

        // Only check database duplicates for XLSB files, not ZIP files
        const isDuplicateInDatabase =
          isXlsb && DJANGO_DATA.existingFiles.includes(file.name);

        selectedFiles.push({
          file: file,
          name: file.name,
          size: file.size,
          lastModified: file.lastModified,
          isDuplicate: isDuplicateInDatabase,
          isValid: isValidFormat,
          isZip: isZip,
        });
      }
    });

    updateFileList();
  },
  false
);

// Store files with no data for the modal
let emptyFiles = [];

// Check for files with 0 sessions
function checkForEmptyFiles() {
  emptyFiles = [];
  const fileRows = document.querySelectorAll("[data-file-id]");

  fileRows.forEach((row) => {
    const fileId = row.getAttribute("data-file-id");
    const sessionCountElement = row.querySelector(`.session-count-${fileId}`);

    if (sessionCountElement) {
      const sessionCount = parseInt(sessionCountElement.textContent.trim());
      if (sessionCount === 0) {
        const fileName = row
          .querySelector("td:first-child span.text-sm")
          .textContent.trim();
        emptyFiles.push({
          id: fileId,
          name: fileName,
        });
      }
    }
  });

  // Show modal if there are empty files
  if (emptyFiles.length > 0) {
    showNoDataModal();
  }
}

// Show the no data modal
function showNoDataModal() {
  const modal = document.getElementById("noDataModal");
  const fileList = document.getElementById("noDataFileList");

  // Build the file list HTML
  let html = '<div class="space-y-2">';
  emptyFiles.forEach((file) => {
    html += `
      <div class="flex items-center gap-2 p-2 bg-white rounded border border-gray-200">
        <svg class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span class="text-sm text-gray-700 font-medium">${file.name}</span>
        <span class="ml-auto text-xs text-red-600 font-semibold">0 sessions</span>
      </div>
    `;
  });
  html += "</div>";

  fileList.innerHTML = html;
  modal.classList.remove("hidden");
}

// Keep the empty files (close modal)
function keepEmptyFiles() {
  const modal = document.getElementById("noDataModal");
  modal.classList.add("hidden");
  emptyFiles = [];
}

// Remove the empty files
async function removeEmptyFiles() {
  if (emptyFiles.length === 0) {
    keepEmptyFiles();
    return;
  }

  const fileIds = emptyFiles.map((f) => f.id);

  // Close modal first
  const modal = document.getElementById("noDataModal");
  modal.classList.add("hidden");

  // Use the bulk delete function
  await deleteFilesSequentially(fileIds);
}

document.addEventListener("DOMContentLoaded", function () {
  // Use the active tab from backend (passed via DJANGO_DATA)
  // This ensures the tab state is preserved across all operations
  if (DJANGO_DATA.activeTab === "files") {
    switchTab("files");
  } else {
    switchTab("sessions");
  }

  // Initialize download links and stats
  updateDownloadLinks();
  updateStats();

  // Check for empty files ONLY if triggered by parse action
  if (DJANGO_DATA.checkEmptyFiles) {
    setTimeout(() => {
      checkForEmptyFiles();
    }, 500);
  }
});
