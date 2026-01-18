document.addEventListener("alpine:init", () => {});

// Tab switching functionality with URL management
function switchTab(tab) {
  const sessionsTab = document.getElementById("sessionsTab");
  const filesTab = document.getElementById("filesTab");
  const sessionsContent = document.getElementById("sessionsContent");
  const filesContent = document.getElementById("filesContent");

  if (tab === "sessions") {
    // Update tabs
    sessionsTab.classList.add("border-teal-600", "text-teal-600", "dark:text-teal-400", "dark:border-teal-400");
    sessionsTab.classList.remove("border-transparent", "text-gray-500", "dark:text-gray-400");
    
    filesTab.classList.add("border-transparent", "text-gray-500", "dark:text-gray-400");
    filesTab.classList.remove("border-teal-600", "text-teal-600", "dark:text-teal-400", "dark:border-teal-400");
    
    // Update content
    sessionsContent.classList.remove("hidden");
    filesContent.classList.add("hidden");

    // Update URL without reload
    const url = new URL(window.location);
    url.searchParams.delete("tab");
    window.history.replaceState({}, "", url);
  } else {
    // Update tabs
    filesTab.classList.add("border-teal-600", "text-teal-600", "dark:text-teal-400", "dark:border-teal-400");
    filesTab.classList.remove("border-transparent", "text-gray-500", "dark:text-gray-400");
    
    sessionsTab.classList.add("border-transparent", "text-gray-500", "dark:text-gray-400");
    sessionsTab.classList.remove("border-teal-600", "text-teal-600", "dark:text-teal-400", "dark:border-teal-400");
    
    // Update content
    filesContent.classList.remove("hidden");
    sessionsContent.classList.add("hidden");

    // Update URL without reload
    const url = new URL(window.location);
    url.searchParams.set("tab", "files");
    window.history.replaceState({}, "", url);
  }
}

function closeUploadModal() {
  document.getElementById("uploadModal").classList.add("hidden");
}

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
  updateDownloadButtonText(); // Update download text when selection changes
}

// UPDATED: Fixed stats calculation to use data-hours from row with DEBUGGING
function updateStats() {
  const checkboxes = document.querySelectorAll(".session-checkbox:checked");
  const count = checkboxes.length;

  console.log("=== STATS UPDATE DEBUG ===");
  console.log("Selected sessions:", count);

  if (count === 0) {
    // Reset to original stats
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
    // Calculate total hours from data-hours attribute on rows
    let totalHours = 0;
    checkboxes.forEach((cb, index) => {
      const row = cb.closest(".session-row");
      if (row) {
        const hoursAttr = row.getAttribute("data-hours");
        const hours = parseFloat(hoursAttr) || 0;
        console.log(
          `  Session ${index + 1}: data-hours="${hoursAttr}" -> parsed=${hours}`
        );
        totalHours += hours;
      } else {
        console.warn(`  Session ${index + 1}: No .session-row found!`);
      }
    });

    console.log("Total hours calculated:", totalHours);

    const avgPerSession = count > 0 ? totalHours / count : 0;
    console.log("Average per session:", avgPerSession);

    // Update stats cards with selected values
    document.getElementById("statsTitleSessions").textContent =
      "Selected Sessions";
    document.getElementById("statsTitleHours").textContent = "Selected Hours";
    document.getElementById("statsTitleAvg").textContent = "Avg (Selected)";

    document.getElementById("statsValueSessions").textContent = count;
    document.getElementById("statsValueHours").textContent =
      totalHours.toFixed(2) + "h";
    document.getElementById("statsValueAvg").textContent =
      avgPerSession.toFixed(2) + "h";
  }

  console.log("=== END STATS DEBUG ===");
}

// Download records function - simplified for new UI
function downloadRecords(format, scope) {
  const baseUrl = DJANGO_DATA.baseUrl;
  let url = `${baseUrl}?format=${format}&scope=${scope}`;

  // Add filter params if applicable
  if (DJANGO_DATA.filterParams.search) {
    url += `&search=${encodeURIComponent(DJANGO_DATA.filterParams.search)}`;
  }
  if (DJANGO_DATA.filterParams.subject) {
    url += `&subject=${DJANGO_DATA.filterParams.subject}`;
  }
  if (DJANGO_DATA.filterParams.dateFrom) {
    url += `&date_from=${DJANGO_DATA.filterParams.dateFrom}`;
  }
  if (DJANGO_DATA.filterParams.dateTo) {
    url += `&date_to=${DJANGO_DATA.filterParams.dateTo}`;
  }
  if (DJANGO_DATA.filterParams.timeFrom) {
    url += `&time_from=${DJANGO_DATA.filterParams.timeFrom}`;
  }
  if (DJANGO_DATA.filterParams.timeTo) {
    url += `&time_to=${DJANGO_DATA.filterParams.timeTo}`;
  }

  // Add selected session IDs if scope is 'selected'
  if (scope === "selected") {
    const checkboxes = document.querySelectorAll(".session-checkbox:checked");
    if (checkboxes.length === 0) {
      alert("Please select sessions to download");
      return;
    }
    checkboxes.forEach((checkbox) => {
      url += `&session_ids=${checkbox.value}`;
    });
  }

  // Trigger download
  window.location.href = url;
}

// NEW: Auto-detect whether to download selected or all sessions
function downloadRecordsAuto(format) {
  const checkboxes = document.querySelectorAll(".session-checkbox:checked");
  const scope = checkboxes.length > 0 ? "selected" : "all";
  downloadRecords(format, scope);
}

// NEW: Update download button descriptions based on selection
function updateDownloadButtonText() {
  const checkboxes = document.querySelectorAll(".session-checkbox:checked");
  const count = checkboxes.length;

  const csvText = document.getElementById("csv-scope-text");
  const xlsxText = document.getElementById("xlsx-scope-text");
  const pdfText = document.getElementById("pdf-scope-text");

  if (count > 0) {
    const text = `Download ${count} selected session${count !== 1 ? "s" : ""}`;
    if (csvText) csvText.textContent = text;
    if (xlsxText) xlsxText.textContent = text;
    if (pdfText) pdfText.textContent = text;
  } else {
    if (csvText) csvText.textContent = "Download all sessions";
    if (xlsxText) xlsxText.textContent = "Download all sessions";
    if (pdfText) pdfText.textContent = "Download all sessions";
  }
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
    form.action = "/teaching-records/delete-sessions/";

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
    form.action = `teaching-records/delete-session/${sessionId}/`;

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
  const bulkFileInput = document.getElementById('bulkFileInput');
  if (bulkFileInput) {
    bulkFileInput.addEventListener('change', handleFileSelection);
  }

  function handleFileSelection(event) {
    const fileInput = event.target;
    const fileListContainer = document.getElementById('fileListContainer');
    const clearAllBtn = document.getElementById('clearAllBtn');
    
    const files = fileInput.files;

    if (!files || files.length === 0) {
      fileListContainer.innerHTML = '<div class="text-gray-500 dark:text-gray-400 text-center">No files selected</div>';
      clearAllBtn.classList.add('hidden');
      return;
    }

    fileListContainer.innerHTML = '';
    clearAllBtn.classList.remove('hidden');

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const fileSize = (file.size / 1024 / 1024).toFixed(2); // in MB
      
      const fileElement = document.createElement('div');
      fileElement.className = 'flex items-center justify-between bg-white dark:bg-gray-800 p-2 rounded-lg mb-2';
      
      fileElement.innerHTML = `
        <div class="flex items-center gap-2">
          <svg class="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
          <span class="text-sm font-medium text-gray-900 dark:text-gray-100">${file.name}</span>
        </div>
        <span class="text-sm text-gray-500 dark:text-gray-400">${fileSize} MB</span>
      `;
      
      fileListContainer.appendChild(fileElement);
    }
  }

  const clearAllBtn = document.getElementById('clearAllBtn');
  if(clearAllBtn) {
    clearAllBtn.addEventListener('click', clearAllFiles);
  }

  function clearAllFiles() {
    const fileInput = document.getElementById('bulkFileInput');
    const fileListContainer = document.getElementById('fileListContainer');
    const clearAllBtn = document.getElementById('clearAllBtn');

    fileInput.value = '';
    fileListContainer.innerHTML = '<div class="text-gray-500 dark:text-gray-400 text-center">No files selected</div>';
    clearAllBtn.classList.add('hidden');
  }

  // Use the active tab from backend (passed via DJANGO_DATA)
  // This ensures the tab state is preserved across all operations
  if (DJANGO_DATA.activeTab === "files") {
    switchTab("files");
  } else {
    switchTab("sessions");
  }

  // Initialize stats and download button text
  updateStats();
  updateDownloadButtonText();

  // Check for empty files ONLY if triggered by parse action
  if (DJANGO_DATA.checkEmptyFiles) {
    setTimeout(() => {
      checkForEmptyFiles();
    }, 500);
  }

  // DEBUG: Log all session rows on page load
  console.log("=== PAGE LOAD DEBUG ===");
  console.log(
    "Total session rows:",
    document.querySelectorAll(".session-row").length
  );
  document.querySelectorAll(".session-row").forEach((row, index) => {
    const sessionId = row.getAttribute("data-session-id");
    const hours = row.getAttribute("data-hours");
    console.log(`  Row ${index + 1}: ID=${sessionId}, data-hours="${hours}"`);
  });
  console.log("=== END PAGE LOAD DEBUG ===");
});