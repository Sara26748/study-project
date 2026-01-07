// Global flag to ensure event delegation is only set up once
let eventListenersAttached = false;

// Global function to attach event listeners - can be called multiple times
function attachEventListeners() {
  console.log("Attaching event listeners...");

  // Only attach delegated event listeners once
  if (!eventListenersAttached) {
    // Version selector change event - use event delegation
    document.addEventListener("change", function (e) {
      if (e.target.classList.contains("version-selector")) {
        const reqId = e.target.getAttribute("data-req-id");
        const versionIndex = e.target.value;
        updateRowWithVersionData(reqId, versionIndex);
      }
    });

    // Edit requirement button click - use event delegation
    document.addEventListener("click", function (e) {
      if (
        e.target.classList.contains("edit-requirement-btn") ||
        e.target.closest(".edit-requirement-btn")
      ) {
        e.stopPropagation(); // Prevent event bubbling
        const button = e.target.classList.contains("edit-requirement-btn")
          ? e.target
          : e.target.closest(".edit-requirement-btn");

        if (button && !button.disabled) {
          e.preventDefault();
          const reqId = button.getAttribute("data-req-id");
          const versionId = button.getAttribute("data-version-id");
          console.log(
            "Edit button clicked - reqId:",
            reqId,
            "versionId:",
            versionId
          );
          if (reqId && versionId && typeof openEditModal === "function") {
            openEditModal(reqId, versionId);
          } else {
            console.error("openEditModal not available or missing data:", {
              reqId,
              versionId,
              openEditModal,
            });
          }
        }
      }
    });

    eventListenersAttached = true;
  }

  // Edit form submission
  const editForm = document.getElementById("editRequirementForm");
  if (editForm && !editForm.dataset.listenerAttached) {
    editForm.addEventListener("submit", function (e) {
      const versionId = document.getElementById("editVersionId").value;
      this.action = `/requirement_version/${versionId}/update`;
    });
    editForm.dataset.listenerAttached = "true";
  }

  // Apply filters button
  const applyBtn = document.getElementById("applyFilters");
  if (applyBtn && !applyBtn.dataset.listenerAttached) {
    applyBtn.addEventListener("click", applyFilters);
    applyBtn.dataset.listenerAttached = "true";
  }

  // Reset filters button
  const resetBtn = document.getElementById("resetFilters");
  if (resetBtn && !resetBtn.dataset.listenerAttached) {
    resetBtn.addEventListener("click", function () {
      document.getElementById("filterText").value = "";
      document.getElementById("filterStatus").value = "";
      document.getElementById("filterCategory").value = "";
      document.querySelectorAll("[data-filter-column]").forEach((select) => {
        select.value = "";
      });
      applyFilters();
    });
    resetBtn.dataset.listenerAttached = "true";
  }

  // Add change listeners to dynamic filters
  document.querySelectorAll("[data-filter-column]").forEach((select) => {
    if (!select.dataset.listenerAttached) {
      select.addEventListener("change", applyFilters);
      select.dataset.listenerAttached = "true";
    }
  });

  // Filter on Input (Instant Search)
  const filterText = document.getElementById("filterText");
  if (filterText && !filterText.dataset.listenerAttached) {
    filterText.addEventListener("input", function () {
      applyFilters();
    });
    filterText.dataset.listenerAttached = "true";
  }

  // Filter Dropdowns Change
  const filterStatus = document.getElementById("filterStatus");
  if (filterStatus && !filterStatus.dataset.listenerAttached) {
    filterStatus.addEventListener("change", applyFilters);
    filterStatus.dataset.listenerAttached = "true";
  }

  const filterCategory = document.getElementById("filterCategory");
  if (filterCategory && !filterCategory.dataset.listenerAttached) {
    filterCategory.addEventListener("change", applyFilters);
    filterCategory.dataset.listenerAttached = "true";
  }

  console.log("Event listeners attached");
}

// Global function to update custom columns
function updateCustomColumns(newColumns) {
  console.log("Updating custom columns:", newColumns);
  window.PROJECT_CUSTOM_COLUMNS = newColumns;
  // Reinitialize filters with new columns
  initializeFilters();
}

// Functions
function updateRowWithVersionData(reqId, versionIndex) {
  const row = document.getElementById(`req-row-${reqId}`);
  const versionsData = document.getElementById(`versions-data-${reqId}`);
  const versionElements = versionsData.querySelectorAll(".version-data");

  let selectedVersion = null;
  versionElements.forEach((el) => {
    if (el.getAttribute("data-version-index") === versionIndex) {
      selectedVersion = el;
    }
  });

  if (selectedVersion) {
    const versionId = selectedVersion.getAttribute("data-version-id");
    row.querySelector(".title-cell").textContent =
      selectedVersion.getAttribute("data-title");
    row.querySelector(".description-cell").textContent =
      selectedVersion.getAttribute("data-description");
    row.querySelector(".category-cell").textContent =
      selectedVersion.getAttribute("data-category") || "–";

    const statusCell = row.querySelector(".status-cell");
    const status = selectedVersion.getAttribute("data-status");
    const statusColor = selectedVersion.getAttribute("data-status-color");
    statusCell.innerHTML = `<span class="badge bg-${statusColor}">${status}</span>`;

    // Update description with popover
    const descriptionCell = row.querySelector(".description-preview");
    if (descriptionCell) {
      const description = selectedVersion.getAttribute("data-description");
      descriptionCell.textContent = description;
      descriptionCell.setAttribute("data-description-full", description);

      // Update or create popover
      const existingPopover = bootstrap.Popover.getInstance(descriptionCell);
      if (existingPopover) {
        existingPopover.setContent({ ".popover-body": description });
      } else {
        new bootstrap.Popover(descriptionCell, {
          trigger: "hover focus",
          html: false,
          placement: "top",
          content: description,
          title: "Vollständige Beschreibung",
        });
      }
    }

    // Update quantifiable icon
    const quantifiableCell = row.querySelector(".quantifiable-cell");
    if (quantifiableCell) {
      const isQuantifiable =
        selectedVersion.getAttribute("data-is-quantifiable") === "true";
      const form = quantifiableCell.querySelector(".toggle-quantifiable-form");
      if (form) {
        const button = form.querySelector("button");
        const icon = form.querySelector("i");

        if (icon) {
          if (isQuantifiable) {
            icon.className = "bi bi-check-circle-fill text-success";
            icon.style.fontSize = "1.3rem";
            if (button)
              button.title = "Quantifizierbar - Klicken zum Deaktivieren";
          } else {
            icon.className = "bi bi-circle text-muted";
            icon.style.fontSize = "1.3rem";
            if (button)
              button.title = "Nicht quantifizierbar - Klicken zum Aktivieren";
          }
        }
      }
    }

    let customData = {};
    try {
      const customDataStr = selectedVersion.getAttribute("data-custom-data");
      if (customDataStr && customDataStr.trim() !== "") {
        customData = JSON.parse(customDataStr);
      }
    } catch (e) {
      console.error("Error parsing custom data:", e);
      customData = {};
    }
    const customDataCells = row.querySelectorAll(".custom-data-cell");
    customDataCells.forEach((cell) => {
      const column = cell.getAttribute("data-column");
      cell.textContent = customData[column] || "–";
    });

    const editButton = row.querySelector(".edit-requirement-btn");
    editButton.setAttribute("data-version-id", versionId);

    const deleteForm = row.querySelector(".delete-version-form");
    if (deleteForm) {
      deleteForm.action = `/requirement_version/${versionId}/delete`;
    }
  }
}

function initializeFilters() {
  console.log("Initializing filters...");

  // Populate category filter
  const categories = new Set();
  document.querySelectorAll(".category-cell").forEach((cell) => {
    const category = cell.textContent.trim();
    if (category && category !== "–") {
      categories.add(category);
    }
  });

  const categoryFilter = document.getElementById("filterCategory");
  if (categoryFilter) {
    // Clear existing options except the first "Alle" option
    while (categoryFilter.options.length > 1) {
      categoryFilter.remove(1);
    }

    categories.forEach((category) => {
      const option = document.createElement("option");
      option.value = category;
      option.textContent = category;
      categoryFilter.appendChild(option);
    });
  }

  // Create dynamic column filters - show ALL custom columns, even if empty
  const customColumns = window.PROJECT_CUSTOM_COLUMNS || [];
  const dynamicFiltersContainer = document.getElementById(
    "dynamicFiltersContainer"
  );

  if (dynamicFiltersContainer) {
    // Clear existing dynamic filters
    dynamicFiltersContainer.innerHTML = "";

    customColumns.forEach((column) => {
      const values = new Set();
      document
        .querySelectorAll(`.custom-data-cell[data-column="${column}"]`)
        .forEach((cell) => {
          const value = cell.textContent.trim();
          if (value && value !== "–" && value !== "") {
            values.add(value);
          }
        });

      // Always show filter, even if no values yet
      const filterDiv = document.createElement("div");
      filterDiv.className = "col-md-2";

      const select = document.createElement("select");
      select.className = "form-select border-0 bg-light";
      select.setAttribute("data-filter-column", column);
      select.id = `filter_${column.replace(/\s+/g, "_")}`;

      const allOption = document.createElement("option");
      allOption.value = "";
      allOption.textContent = `${column}: Alle`;
      select.appendChild(allOption);

      // Sort values for better UX
      const sortedValues = Array.from(values).sort();
      sortedValues.forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        select.appendChild(option);
      });

      // Add change event listener
      if (!select.dataset.listenerAttached) {
        select.addEventListener("change", applyFilters);
        select.dataset.listenerAttached = "true";
      }

      filterDiv.appendChild(select);
      dynamicFiltersContainer.appendChild(filterDiv);
    });
  }

  console.log("Filters initialized");
}

function applyFilters() {
  console.log("Applying filters...");

  const textFilter = document.getElementById("filterText").value.toLowerCase();
  const statusFilter = document.getElementById("filterStatus").value;
  const categoryFilter = document.getElementById("filterCategory").value;

  const dynamicFilters = {};
  document.querySelectorAll("[data-filter-column]").forEach((select) => {
    const column = select.getAttribute("data-filter-column");
    const value = select.value;
    if (value) {
      dynamicFilters[column] = value;
    }
  });

  let visibleCount = 0;
  let totalCount = 0;

  document.querySelectorAll("tbody tr[data-req-id]").forEach((row) => {
    totalCount++;
    let visible = true;

    if (textFilter) {
      const title = row.querySelector(".title-cell").textContent.toLowerCase();
      const description = row
        .querySelector(".description-cell")
        .textContent.toLowerCase();
      if (!title.includes(textFilter) && !description.includes(textFilter)) {
        visible = false;
      }
    }

    if (statusFilter && visible) {
      const status = row.querySelector(".status-cell").textContent.trim();
      if (status !== statusFilter) {
        visible = false;
      }
    }

    if (categoryFilter && visible) {
      const category = row.querySelector(".category-cell").textContent.trim();
      if (category !== categoryFilter) {
        visible = false;
      }
    }

    if (visible && Object.keys(dynamicFilters).length > 0) {
      for (const [column, value] of Object.entries(dynamicFilters)) {
        const cell = row.querySelector(
          `.custom-data-cell[data-column="${column}"]`
        );
        if (cell) {
          const cellValue = cell.textContent.trim();
          if (cellValue !== value) {
            visible = false;
            break;
          }
        }
      }
    }

    if (visible) {
      row.style.display = "";
      visibleCount++;
    } else {
      row.style.display = "none";
    }
  });

  const resultText = `${visibleCount} von ${totalCount} angezeigt`;
  const resultCount = document.getElementById("filterResultCount");
  if (resultCount) {
    resultCount.textContent = resultText;
  }

  console.log(`Filter applied: ${visibleCount}/${totalCount} visible`);
}

function openEditModal(reqId, versionId) {
  console.log("Opening edit modal for req:", reqId, "version:", versionId);

  document.getElementById("editVersionId").value = versionId;

  const versionsData = document.getElementById(`versions-data-${reqId}`);
  const versionElements = versionsData.querySelectorAll(".version-data");

  let selectedVersion = null;
  versionElements.forEach((el) => {
    if (el.getAttribute("data-version-id") === versionId) {
      selectedVersion = el;
    }
  });

  if (selectedVersion) {
    document.getElementById("editTitle").value =
      selectedVersion.getAttribute("data-title");
    document.getElementById("editDescription").value =
      selectedVersion.getAttribute("data-description");
    document.getElementById("editCategory").value =
      selectedVersion.getAttribute("data-category");

    // Set status
    const status = selectedVersion.getAttribute("data-status");
    const editStatus = document.getElementById("editStatus");
    if (editStatus) {
      editStatus.value = status || "Offen";
    }

    // Set quantifiable checkbox
    let customData = {};
    try {
      const customDataStr = selectedVersion.getAttribute("data-custom-data");
      if (
        customDataStr &&
        customDataStr.trim() !== "" &&
        customDataStr !== "null"
      ) {
        customData = JSON.parse(customDataStr);
      }
    } catch (e) {
      console.error("Error parsing custom data:", e);
    }

    const editQuantifiable = document.getElementById("editQuantifiable");
    if (editQuantifiable) {
      const isQuantifiable =
        customData.is_quantifiable === "true" ||
        customData.is_quantifiable === true;
      editQuantifiable.checked = isQuantifiable;
    }

    // Parse custom data (already done above, reuse it)

    const dynamicContainer = document.getElementById("dynamicColumnsContainer");
    dynamicContainer.innerHTML = "";

    // USE GLOBAL VARIABLE INSTEAD OF JINJA2
    const customColumns = window.PROJECT_CUSTOM_COLUMNS || [];
    console.log("Custom columns for edit:", customColumns);
    console.log("Custom data object:", customData);

    customColumns.forEach((column) => {
      const fieldDiv = document.createElement("div");
      fieldDiv.className = "mb-3";

      const label = document.createElement("label");
      label.className = "form-label";
      label.textContent = column;

      const input = document.createElement("input");
      input.type = "text";
      input.className = "form-control";
      input.name = `custom_${column}`;
      input.value = customData[column] || "";

      fieldDiv.appendChild(label);
      fieldDiv.appendChild(input);
      dynamicContainer.appendChild(fieldDiv);
    });

    const modal = new bootstrap.Modal(
      document.getElementById("editRequirementModal")
    );
    modal.show();
  }
}

// Initialize on DOMContentLoaded
document.addEventListener("DOMContentLoaded", function () {
  console.log("Project.js loaded");
  console.log("Custom columns:", window.PROJECT_CUSTOM_COLUMNS);

  // Attach event listeners
  attachEventListeners();

  // Initialize filters
  initializeFilters();

  // Start polling if we are in a project view
  if (typeof window.PROJECT_ID !== "undefined") {
    console.log("Starting polling for project", window.PROJECT_ID);
    setInterval(pollRequirementsStatus, 5000);

    // Send heartbeat every 10 seconds
    sendHeartbeat();
    setInterval(sendHeartbeat, 10000);

    // Poll active users every 5 seconds
    pollActiveUsers();
    setInterval(pollActiveUsers, 5000);
  }
});

function pollRequirementsStatus() {
  fetch(`/project/${window.PROJECT_ID}/requirements_status`)
    .then((response) => response.json())
    .then((data) => {
      // Update lock icons and buttons
      data.forEach((item) => {
        // Find row
        const row = document.querySelector(`tr[data-req-id="${item.req_id}"]`);
        if (!row) return; // Might be filtered out or pagination

        // Check active version in UI
        const versionSelector = row.querySelector(".version-selector");
        const currentVersionIndex = versionSelector
          ? parseInt(versionSelector.value)
          : -1;

        // We only update if the blocked version is the currently displayed one?
        // Actually the API returns status for the LATEST version usually.
        // But the table might show older versions.
        // Let's assume we mainly care about the latest version which is usually shown.

        // Find drag/drop status (Kanban) or list blocking

        // Update Lock Button
        // We need to find the specific version button.
        // The lock button is inside a form.

        // The button has logic based on 'versions[-1]' which is the latest.
        // If the user is viewing an old version, the polling might be confusing if we update it based on latest.
        // But typically locking applies to the "latest" tip.

        // Let's update the "Bearbeiten" button and "Blockieren" button for the SPECIFIC version ID
        // The Edit button has data-version-id

        const editBtn = row.querySelector(
          `.edit-requirement-btn[data-version-id="${item.version_id}"]`
        );
        const deleteBtn = row.querySelector(`.delete-version-form button`);
        const blockBtn = row.querySelector(
          `form[action*="/toggle_block"] button`
        ); // Approximation
        const toggleForm = row.querySelector(
          `form[action*="/requirement_version/${item.version_id}/toggle_block"]`
        );

        if (editBtn) {
          editBtn.disabled = item.is_blocked;
        }

        if (toggleForm) {
          const btn = toggleForm.querySelector("button");
          if (btn) {
            if (item.is_blocked) {
              // Locked: Red filled lock
              btn.innerHTML = '<i class="bi bi-lock-fill"></i>';
              btn.className = "btn btn-sm btn-icon rounded-circle text-danger";
              btn.title = "Freigeben";
            } else {
              // Unlocked: Green open lock
              btn.innerHTML = '<i class="bi bi-unlock"></i>';
              btn.className = "btn btn-sm btn-icon rounded-circle text-success";
              btn.title = "Blockieren";
            }
          }
        }
      });
    })
    .catch((err) => console.error("Polling error:", err));
}
