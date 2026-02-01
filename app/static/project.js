// Global flag to ensure event delegation is only set up once
let eventListenersAttached = false;

// Snapshot of the edit form to detect changes in revision mode
let editFormInitialData = null;

// Cache for revision snapshots per requirement version
const revisionCache = {};

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
            versionId,
          );
          if (reqId && versionId && typeof openEditModal === "function") {
            const selectedRevision = getSelectedRevisionSnapshot(reqId);
            openEditModal(reqId, versionId, "edit", selectedRevision);
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

    // Revision button click - use event delegation
    document.addEventListener("click", function (e) {
      if (
        e.target.classList.contains("revision-requirement-btn") ||
        e.target.closest(".revision-requirement-btn")
      ) {
        e.stopPropagation();
        const button = e.target.classList.contains("revision-requirement-btn")
          ? e.target
          : e.target.closest(".revision-requirement-btn");

        if (button && !button.disabled) {
          e.preventDefault();
          const reqId = button.getAttribute("data-req-id");
          const versionId = button.getAttribute("data-version-id");
          if (reqId && versionId && typeof openRevisionModal === "function") {
            const selectedRevision = getSelectedRevisionSnapshot(reqId);
            openRevisionModal(reqId, versionId, selectedRevision);
          }
        }
      }
    });

    // Revision selector change - use event delegation
    document.addEventListener("change", function (e) {
      if (e.target.classList.contains("revision-selector")) {
        const selector = e.target;
        const reqId = selector.getAttribute("data-req-id");
        const selectedValue = selector.value;

        const row = document.getElementById(`req-row-${reqId}`);
        const versionSelector = row?.querySelector(".version-selector");
        const versionIndex = versionSelector?.value;
        const versionData = versionIndex
          ? row.querySelector(
              `.version-data[data-version-index="${versionIndex}"]`,
            )
          : null;
        const versionId = versionData?.getAttribute("data-version-id");
        const cacheKey = `${reqId}:${versionId || ""}`;

        if (selectedValue === "current") {
          // Revert to current version selection and clear stored snapshot
          const row = document.getElementById(`req-row-${reqId}`);
          if (row) {
            delete row.dataset.selectedRevisionJson;
            delete row.dataset.selectedRevisionNumber;
          }
          if (versionSelector) {
            updateRowWithVersionData(reqId, versionSelector.value);
          }
          return;
        }

        const revisions = revisionCache[cacheKey] || [];
        const match = revisions.find(
          (rev) => `${rev.revision_number}` === selectedValue,
        );
        const applyMatch = (rev) => {
          if (rev) {
            const row = document.getElementById(`req-row-${reqId}`);
            if (row) {
              row.dataset.selectedRevisionJson = JSON.stringify(rev);
              row.dataset.selectedRevisionNumber = `${rev.revision_number || ""}`;
            }
            applyRevisionSnapshot(reqId, rev);
          }
        };
        if (match) {
          applyMatch(match);
        } else if (versionId) {
          loadRevisions(reqId, versionId).then((loaded) => {
            const matchLoaded = loaded.find(
              (rev) => `${rev.revision_number}` === selectedValue,
            );
            applyMatch(matchLoaded);
          });
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
      const mode = document.getElementById("editMode").value || "edit";
      const revisionNumber =
        document.getElementById("editRevisionNumber")?.value || "";

      // If a specific revision is selected, always route to the revise endpoint
      if (revisionNumber) {
        this.action = `/requirement_version/${versionId}/revise`;
        document.getElementById("editSaveType").value = "revision";
        document.getElementById("editMode").value = "revision";
      } else if (mode === "revision") {
        this.action = `/requirement_version/${versionId}/revise`;
        document.getElementById("editSaveType").value = "revision";
      } else {
        this.action = `/requirement_version/${versionId}/update`;
      }
    });
    editForm.dataset.listenerAttached = "true";
  }

  // Track form changes to enable the revision submit button only when there are edits
  if (editForm && !editForm.dataset.changeListenerAttached) {
    const changeHandler = function () {
      if (document.getElementById("editMode").value === "revision") {
        updateRevisionButtonState();
      }
    };

    editForm.addEventListener("input", changeHandler);
    editForm.addEventListener("change", changeHandler);

    editForm.dataset.changeListenerAttached = "true";
  }

  // Enforce status based on action buttons (Bearbeitet/Revidiert -> In Bearbeitung, Freigegeben -> Freigabe)
  const statusSelect = document.getElementById("editStatus");
  const intermediateBtn = document.getElementById("editSaveIntermediateBtn");
  const finalBtn = document.getElementById("editSaveFinalBtn");
  const revisionBtn = document.getElementById("revisionSubmit");

  if (
    intermediateBtn &&
    statusSelect &&
    !intermediateBtn.dataset.listenerAttached
  ) {
    intermediateBtn.addEventListener("click", () => {
      statusSelect.value = "In Bearbeitung";
    });
    intermediateBtn.dataset.listenerAttached = "true";
  }

  if (finalBtn && statusSelect && !finalBtn.dataset.listenerAttached) {
    finalBtn.addEventListener("click", () => {
      statusSelect.value = "Freigabe";
    });
    finalBtn.dataset.listenerAttached = "true";
  }

  if (revisionBtn && statusSelect && !revisionBtn.dataset.listenerAttached) {
    revisionBtn.addEventListener("click", () => {
      statusSelect.value = "In Bearbeitung";
    });
    revisionBtn.dataset.listenerAttached = "true";
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

// Fetch revision snapshots for a requirement version (cached)
async function loadRevisions(reqId, versionId) {
  if (!versionId) return [];
  const cacheKey = `${reqId}:${versionId}`;
  if (revisionCache[cacheKey]) return revisionCache[cacheKey];
  try {
    const res = await fetch(
      `/requirement/${reqId}/revisions_json?version_id=${versionId}`,
    );
    if (!res.ok) return [];
    const data = await res.json();
    revisionCache[cacheKey] = data || [];
    return revisionCache[cacheKey];
  } catch (err) {
    console.error("Failed to load revisions", err);
    return [];
  }
}

function populateRevisionSelector(reqId, row, revisions) {
  const selector = row.querySelector(".revision-selector");
  if (!selector) return;

  // Prefer an explicit value, fall back to the existing option text or Entwurf
  const currentRevision =
    selector.dataset.currentRevision ||
    (selector.options[0]?.textContent || "").trim() ||
    "Entwurf";
  selector.innerHTML = "";

  const currentOption = document.createElement("option");
  currentOption.value = "current";
  currentOption.textContent = `${currentRevision || "Entwurf"}`;
  selector.appendChild(currentOption);

  const sortedRevs = [...revisions].sort(
    (a, b) => (a.revision_number || 0) - (b.revision_number || 0),
  );

  sortedRevs.forEach((rev) => {
    const opt = document.createElement("option");
    opt.value = `${rev.revision_number}`;
    const revLabel = rev.revision_label || rev.revision_number || "";
    opt.textContent = `${revLabel || "Entwurf"}`;
    selector.appendChild(opt);
  });

  // Default to current version to avoid overwriting the live view
  selector.value = "current";
}

function applyRevisionSnapshot(reqId, revisionData) {
  const row = document.getElementById(`req-row-${reqId}`);
  if (!row || !revisionData) return;

  row.querySelector(".title-cell").textContent = revisionData.title || "–";
  const descCell = row.querySelector(".description-cell");
  const descPreview = row.querySelector(".description-preview");
  const description = revisionData.description || "";
  if (descCell) descCell.textContent = description;
  if (descPreview) refreshDescriptionPopover(descPreview, description);

  const categoryCell = row.querySelector(".category-cell");
  if (categoryCell) {
    categoryCell.innerHTML = `<span class="badge bg-light text-secondary border">${revisionData.category || "–"}</span>`;
  }

  const statusCell = row.querySelector(".status-cell");
  if (statusCell) {
    const color = revisionData.status_color || "secondary";
    const status = revisionData.status || "–";
    statusCell.innerHTML = `<span class="badge rounded-pill bg-${color}">${status}</span>`;
  }

  const customData = revisionData.custom_data || {};
  row.querySelectorAll(".custom-data-cell").forEach((cell) => {
    const column = cell.getAttribute("data-column");
    cell.textContent = customData[column] || "–";
  });

  // Quantifiable icon update
  const quantifiableCell = row.querySelector(".quantifiable-cell");
  if (quantifiableCell) {
    const isQuant = !!revisionData.is_quantifiable;
    const form = quantifiableCell.querySelector(".toggle-quantifiable-form");
    if (form) {
      const button = form.querySelector("button");
      const icon = form.querySelector("i");
      if (icon) {
        if (isQuant) {
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

  // Revision label display in the cell header
  const revisionSelect = row.querySelector(".revision-selector");
  if (revisionSelect) {
    revisionSelect.value = `${revisionData.revision_number}`;
  }
}

function getSelectedRevisionSnapshot(reqId) {
  const row = document.getElementById(`req-row-${reqId}`);
  if (!row || !row.dataset.selectedRevisionJson) return null;
  try {
    return JSON.parse(row.dataset.selectedRevisionJson);
  } catch (err) {
    console.error("Failed to parse stored revision snapshot", err);
    return null;
  }
}

function refreshDescriptionPopover(element, description) {
  if (!element) return;
  const safeDescription = description || "";
  element.textContent = safeDescription;
  element.setAttribute("data-description-full", safeDescription);
  element.setAttribute("data-bs-toggle", "popover");
  element.setAttribute("data-bs-trigger", "hover focus");
  element.setAttribute("data-bs-placement", "top");

  const existing = bootstrap.Popover.getInstance(element);
  if (existing) {
    existing.dispose();
  }

  new bootstrap.Popover(element, {
    trigger: "hover focus",
    html: false,
    placement: "top",
    content: safeDescription,
    title: "Vollständige Beschreibung",
  });
}

// Capture current edit form values for change detection
function captureEditFormSnapshot() {
  const form = document.getElementById("editRequirementForm");
  if (!form) return {};
  const formData = new FormData(form);
  const snapshot = {};
  formData.forEach((value, key) => {
    snapshot[key] = value ?? "";
  });

  // Explicitly capture checkbox state for quantifiable
  const quantCheckbox = document.getElementById("editQuantifiable");
  snapshot.is_quantifiable = quantCheckbox && quantCheckbox.checked ? "on" : "";

  return snapshot;
}

function hasRevisionChanges() {
  if (!editFormInitialData) return false;
  const current = captureEditFormSnapshot();
  const keys = new Set([
    ...Object.keys(editFormInitialData),
    ...Object.keys(current),
  ]);
  for (const key of keys) {
    if ((current[key] || "") !== (editFormInitialData[key] || "")) {
      return true;
    }
  }
  return false;
}

function updateRevisionButtonState() {
  const revisionButton = document.getElementById("revisionSubmit");
  const mode = document.getElementById("editMode")?.value || "edit";
  if (!revisionButton || mode !== "revision") return;
  revisionButton.disabled = !hasRevisionChanges();
}

// Functions
function updateRowWithVersionData(reqId, versionIndex) {
  const row = document.getElementById(`req-row-${reqId}`);
  if (row) {
    delete row.dataset.selectedRevisionJson;
    delete row.dataset.selectedRevisionNumber;
  }
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
      refreshDescriptionPopover(descriptionCell, description);
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

    const revisionCell = row.querySelector(".revision-cell");
    if (revisionCell) {
      const revisionValue = selectedVersion.getAttribute("data-revision");
      const selector = revisionCell.querySelector(".revision-selector");
      if (selector) {
        selector.dataset.currentRevision = revisionValue || "Entwurf";
        selector.innerHTML = "";
        const opt = document.createElement("option");
        opt.value = "current";
        opt.textContent = `${revisionValue || "Entwurf"}`;
        selector.appendChild(opt);
        selector.value = "current";
      } else {
        revisionCell.textContent =
          revisionValue && revisionValue !== "" ? revisionValue : "–";
      }
    }

    const revisionButton = row.querySelector(".revision-requirement-btn");
    if (revisionButton) {
      revisionButton.setAttribute("data-version-id", versionId);
    }

    // Populate revision selector asynchronously (uses cache if available)
    loadRevisions(reqId, versionId).then((revs) => {
      populateRevisionSelector(reqId, row, revs);
    });
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
    "dynamicFiltersContainer",
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
          `.custom-data-cell[data-column="${column}"]`,
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

function openEditModal(
  reqId,
  versionId,
  mode = "edit",
  revisionOverride = null,
) {
  console.log("Opening edit modal for req:", reqId, "version:", versionId);

  document.getElementById("editVersionId").value = versionId;

  const modeInput = document.getElementById("editMode");
  const saveTypeInput = document.getElementById("editSaveType");
  const revisionNumberInput = document.getElementById("editRevisionNumber");
  const editButtons = document.getElementById("editActionButtons");
  const revisionButtonWrap = document.getElementById("revisionActionButton");
  const revisionButton = document.getElementById("revisionSubmit");
  const modalTitle = document.querySelector(
    "#editRequirementModal .modal-title",
  );

  if (modeInput) modeInput.value = mode;
  if (modalTitle)
    modalTitle.textContent =
      mode === "revision" ? "Anforderung revidieren" : "Anforderung bearbeiten";

  if (mode === "revision") {
    if (saveTypeInput) saveTypeInput.value = "revision";
    if (editButtons) editButtons.classList.add("d-none");
    if (revisionButtonWrap) revisionButtonWrap.classList.remove("d-none");
    if (revisionButton) revisionButton.disabled = true;
  } else {
    if (saveTypeInput) saveTypeInput.value = "intermediate";
    if (editButtons) editButtons.classList.remove("d-none");
    if (revisionButtonWrap) revisionButtonWrap.classList.add("d-none");
  }

  const versionsData = document.getElementById(`versions-data-${reqId}`);
  const versionElements = versionsData.querySelectorAll(".version-data");

  let selectedVersion = null;
  versionElements.forEach((el) => {
    if (el.getAttribute("data-version-id") === versionId) {
      selectedVersion = el;
    }
  });

  if (selectedVersion) {
    const revisionData = revisionOverride || getSelectedRevisionSnapshot(reqId);

    if (revisionNumberInput) {
      revisionNumberInput.value = revisionData?.revision_number
        ? `${revisionData.revision_number}`
        : "";
    }

    // Determine form source: selected revision snapshot (if any) otherwise the current version data
    let customData = {};
    let formSource = revisionData || {};
    let status = null;

    if (!revisionData) {
      formSource = {
        title: selectedVersion.getAttribute("data-title"),
        description: selectedVersion.getAttribute("data-description"),
        category: selectedVersion.getAttribute("data-category"),
        status: selectedVersion.getAttribute("data-status"),
        custom_data: null,
        is_quantifiable: selectedVersion.getAttribute("data-is-quantifiable"),
      };
    }

    // Parse custom data from the chosen source
    if (revisionData && revisionData.custom_data) {
      customData = revisionData.custom_data || {};
      status = revisionData.status;
    } else {
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
        customData = {};
      }
      status = formSource.status;
    }

    document.getElementById("editTitle").value = formSource.title || "";
    document.getElementById("editDescription").value =
      formSource.description || "";
    document.getElementById("editCategory").value = formSource.category || "";

    // Set status
    const editStatus = document.getElementById("editStatus");
    if (editStatus) {
      editStatus.value = status || "Entwurf";
    }

    // Set quantifiable checkbox
    const editQuantifiable = document.getElementById("editQuantifiable");
    if (editQuantifiable) {
      const quantFlag =
        (revisionData && revisionData.is_quantifiable) ||
        formSource.is_quantifiable ||
        customData.is_quantifiable;
      const isQuantifiable = quantFlag === true || quantFlag === "true";
      editQuantifiable.checked = isQuantifiable;
    }

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

    // Capture initial state for change detection in revision mode
    editFormInitialData = captureEditFormSnapshot();
    updateRevisionButtonState();

    // Preload revisions for this requirement version to enable quick switching in the table
    loadRevisions(reqId, versionId).then((revs) => {
      const row = document.getElementById(`req-row-${reqId}`);
      if (row) {
        populateRevisionSelector(reqId, row, revs);
      }
    });

    const modal = new bootstrap.Modal(
      document.getElementById("editRequirementModal"),
    );
    modal.show();
  }
}

function openRevisionModal(reqId, versionId, revisionOverride = null) {
  openEditModal(reqId, versionId, "revision", revisionOverride);
}

// Initialize on DOMContentLoaded
document.addEventListener("DOMContentLoaded", function () {
  console.log("Project.js loaded");
  console.log("Custom columns:", window.PROJECT_CUSTOM_COLUMNS);

  // Ensure all description previews have an active popover on load
  document.querySelectorAll(".description-preview").forEach((el) => {
    const full = el.getAttribute("data-description-full") || el.textContent;
    refreshDescriptionPopover(el, full);
  });

  // Attach event listeners
  attachEventListeners();

  // Force-select the preferred version (server-provided) to avoid falling back to latest
  const preferredVersionId = window.SELECTED_VERSION_ID || null;
  if (preferredVersionId) {
    document.querySelectorAll("[data-req-id]").forEach((row) => {
      const reqId = row.getAttribute("data-req-id");
      const versionSelector = row.querySelector(".version-selector");
      if (!versionSelector) return;

      const match = row.querySelector(
        `.version-data[data-version-id="${preferredVersionId}"]`,
      );
      if (match) {
        const targetIndex = match.getAttribute("data-version-index");
        if (targetIndex) {
          versionSelector.value = targetIndex;
          updateRowWithVersionData(reqId, targetIndex);
        }
      }
    });
  }

  // Initialize filters
  initializeFilters();

  // Preload revision selectors for visible rows
  document.querySelectorAll(".revision-selector").forEach((selector) => {
    const reqId = selector.getAttribute("data-req-id");
    if (!reqId) return;
    const row = document.getElementById(`req-row-${reqId}`);
    const versionSelector = row?.querySelector(".version-selector");
    const versionIndex = versionSelector?.value;
    const versionData = versionIndex
      ? row.querySelector(`.version-data[data-version-index="${versionIndex}"]`)
      : null;
    const versionId = versionData?.getAttribute("data-version-id");
    loadRevisions(reqId, versionId).then((revs) => {
      if (row) {
        populateRevisionSelector(reqId, row, revs);
      }
    });
  });

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
          `.edit-requirement-btn[data-version-id="${item.version_id}"]`,
        );
        const deleteBtn = row.querySelector(`.delete-version-form button`);
        const blockBtn = row.querySelector(
          `form[action*="/toggle_block"] button`,
        ); // Approximation
        const toggleForm = row.querySelector(
          `form[action*="/requirement_version/${item.version_id}/toggle_block"]`,
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
('console.log("TEST-LOADED-PROJECT.JS");');
