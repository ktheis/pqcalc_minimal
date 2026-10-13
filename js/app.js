// js/app.js - Main Application Controller for Offline PQcalc
(function () {
    'use strict';

    // Application State
    var appState = new Calculator.State();
    var inputLogHistory = [];
    var briefLogHistory = [];
    var historyStack = [];
    var historyStep = 0;
    var suppressPopstateCount = 0;

    // DOM Elements
    var commandsTextarea = document.getElementById('commands');
    var outputContainer = document.getElementById('output-container');
    var welcomeBox = document.getElementById('welcome-box');
    var knownChipsContainer = document.getElementById('known-chips');
    var selectUnits = document.getElementById('select-units');
    var selectFunctions = document.getElementById('select-functions');
    var selectSymbols = document.getElementById('select-symbols');
    var selectConstants = document.getElementById('select-constants');

    var btnCalculate = document.getElementById('btn-calculate');
    var btnUndo = document.getElementById('btn-undo');
    var btnReset = document.getElementById('btn-reset');
    var btnResubmit = document.getElementById('btn-resubmit');
    var btnExport = document.getElementById('btn-export');
    var btnHelp = document.getElementById('btn-help');

    var exportModal = document.getElementById('export-modal');
    var helpModal = document.getElementById('help-modal');

    // 1. insertAtCaret - Global function for inserting text at textarea caret
    window.insertAtCaret = function (areaId, text, backup) {
        backup = backup || 0;
        var txtarea = document.getElementById(areaId);
        if (!txtarea) return;

        var scrollPos = txtarea.scrollTop;
        var startPos = txtarea.selectionStart;
        var endPos = txtarea.selectionEnd;

        if (typeof startPos !== 'number') {
            startPos = txtarea.value.length;
            endPos = txtarea.value.length;
        }

        var front = txtarea.value.substring(0, startPos);
        var back = txtarea.value.substring(endPos, txtarea.value.length);
        txtarea.value = front + text + back;

        var newPos = startPos + text.length - backup;
        txtarea.selectionStart = newPos;
        txtarea.selectionEnd = newPos;
        txtarea.focus();
        txtarea.scrollTop = scrollPos;
    };

    // 2. Populate Dropdowns
    function initSelectors() {
        // Units
        if (selectUnits && Quantities && Quantities.known_units) {
            var unitList = Object.keys(Quantities.known_units).concat(['°ΔC', '°aC']);
            unitList.sort(function (a, b) {
                return a.toLowerCase().localeCompare(b.toLowerCase());
            });
            for (var i = 0; i < unitList.length; i++) {
                var opt = document.createElement('option');
                opt.value = unitList[i];
                opt.textContent = unitList[i];
                selectUnits.appendChild(opt);
            }
            selectUnits.addEventListener('change', function () {
                if (this.value) {
                    window.insertAtCaret('commands', this.value, 0);
                    this.selectedIndex = 0;
                }
            });
        }

        // Functions
        if (selectFunctions && Quantities && Quantities.functions) {
            var funcList = Object.keys(Quantities.functions).map(function (f) {
                return f + '()';
            });
            funcList.push('using  ');
            funcList.push('in  ');
            for (var j = 0; j < funcList.length; j++) {
                var fOpt = document.createElement('option');
                fOpt.value = funcList[j];
                fOpt.textContent = funcList[j];
                selectFunctions.appendChild(fOpt);
            }
            selectFunctions.addEventListener('change', function () {
                if (this.value) {
                    var backup = this.value.endsWith('()') || this.value.endsWith('  ') ? 1 : 0;
                    window.insertAtCaret('commands', this.value, backup);
                    this.selectedIndex = 0;
                }
            });
        }

        // Symbols
        if (selectSymbols) {
            var symbolList = ["°", "μ", "ΔHf°", " ％", "ν", "Δ", "ℎνλ", "ΔᵣG°", "ρ", "∞", "ΦΨ"];
            for (var k = 0; k < symbolList.length; k++) {
                var sOpt = document.createElement('option');
                sOpt.value = symbolList[k];
                sOpt.textContent = symbolList[k];
                selectSymbols.appendChild(sOpt);
            }
            selectSymbols.addEventListener('change', function () {
                if (this.value) {
                    window.insertAtCaret('commands', this.value, 0);
                    this.selectedIndex = 0;
                }
            });
        }

        // Constants
        if (selectConstants) {
            var constList = [
                { label: 'Speed of light (c0)', value: 'c0 = 299792458 m/s\n' },
                { label: 'Planck constant (ℎ)', value: 'ℎ = 6.62607015E-34 J s\n' },
                { label: 'Avogadro constant (N_A)', value: 'N_A = 6.02214076E23 /mol\n' },
                { label: 'Boltzmann constant (k_B)', value: 'k_B = 1.380649E-23 J/K\n' },
                { label: 'Gas constant (R)', value: 'R = 8.314463 J/(K mol)\n' },
                { label: 'Elementary charge (e)', value: 'e = 1.602176634E-19 C\n' },
                { label: 'Faraday constant (ℱ)', value: 'ℱ = 9.64853321e4 C/mol\n' }
            ];
            for (var m = 0; m < constList.length; m++) {
                var cOpt = document.createElement('option');
                cOpt.value = constList[m].value;
                cOpt.textContent = constList[m].label;
                selectConstants.appendChild(cOpt);
            }
            selectConstants.addEventListener('change', function () {
                if (this.value) {
                    window.insertAtCaret('commands', this.value, 0);
                    this.selectedIndex = 0;
                }
            });
        }
    }

    // 3. Initialize Touch Chips Bar
    function initTouchBar() {
        var chips = document.querySelectorAll('.chip-btn');
        chips.forEach(function (chip) {
            chip.addEventListener('click', function (e) {
                e.preventDefault();
                var text = chip.getAttribute('data-insert');
                var backup = parseInt(chip.getAttribute('data-backup') || '0', 10);
                if (text) {
                    window.insertAtCaret('commands', text, backup);
                }
            });
        });
    }

    // 4. Render KaTeX inside an element
    function renderMath(element) {
        if (window.renderMathInElement) {
            renderMathInElement(element, {
                delimiters: [
                    { left: "$$", right: "$$", display: true },
                    { left: "\\[", right: "\\]", display: true },
                    { left: "\\(", right: "\\)", display: false }
                ],
                throwOnError: false
            });
        }
    }

    // 5. Update Known Quantities Panel
    function updateKnownQuantities(knownList) {
        if (!knownChipsContainer) return;
        knownChipsContainer.innerHTML = '';
        if (!knownList || knownList.length === 0) {
            knownChipsContainer.innerHTML = '<span class="empty-known">None defined yet</span>';
            return;
        }

        for (var i = 0; i < knownList.length; i++) {
            var item = knownList[i];
            var chip = document.createElement('span');
            chip.className = 'known-chip';
            chip.textContent = item;
            var varName = item.split('=')[0].trim();
            chip.title = 'Click to insert ' + varName;
            (function (name) {
                chip.addEventListener('click', function () {
                    window.insertAtCaret('commands', name, 0);
                });
            })(varName);
            knownChipsContainer.appendChild(chip);
        }
    }

    // 6. Strip HTML tags for LibreTexts export
    function stripHtml(text) {
        var result = [];
        var html = false;
        var c_old = ' ';
        for (var i = 0; i < text.length; i++) {
            var c = text[i];
            if (c === '<') {
                html = true;
            } else if (c === '>' && c_old !== '-' && c_old !== '=') {
                html = false;
            } else if (!html) {
                result.push(c);
            }
            c_old = c;
        }
        var r = result.join('')
            .replace(/\\\)\s*\\\(/g, '')
            .replace(/}\\\)\\\(\\ce{/g, '')
            .replace(/\r\n\r\n\r\n/g, '\r\n');
        return r;
    }

    // 7. Execute Calculation
    function runCalculation() {
        var input = commandsTextarea.value;
        if (!input || !input.trim()) return;

        // Snapshot state prior to this calculation
        var snapshot = {
            state: new Calculator.State(appState),
            inputLogHistory: inputLogHistory.slice(),
            briefLogHistory: briefLogHistory.slice(),
            commandText: input
        };

        try {
            var res = Calculator.calc(appState, input);
            appState = res.state;

            // Commit snapshot to history and update browser navigation
            historyStack.push(snapshot);
            historyStep++;
            try {
                history.pushState({ step: historyStep }, document.title);
            } catch (e) {
                // Ignore if history API is restricted in sandbox
            }
            updateUndoButtonState();

            if (welcomeBox) {
                welcomeBox.style.display = 'none';
            }

            // Create step wrapper
            var stepElem = document.createElement('div');
            stepElem.className = 'calc-step';
            stepElem.innerHTML = res.verbose_work;
            outputContainer.appendChild(stepElem);

            // Render KaTeX
            renderMath(stepElem);

            // Accumulate logs
            if (res.input_log) {
                inputLogHistory.push(res.input_log);
            }
            if (res.brief_work) {
                briefLogHistory.push(res.brief_work);
            }

            // Update Known list
            updateKnownQuantities(res.known);

            // Save to localStorage
            saveState();

            // Clear input and focus
            commandsTextarea.value = '';
            commandsTextarea.focus();

            // Scroll to bottom smoothly
            outputContainer.scrollTop = outputContainer.scrollHeight;
        } catch (err) {
            console.error('Calculation error:', err);
            var errElem = document.createElement('div');
            errElem.style.color = 'red';
            errElem.innerHTML = '<strong>Error:</strong> ' + err.message;
            outputContainer.appendChild(errElem);
        }
    }

    // 8. Undo Calculation Step
    function updateUndoButtonState() {
        if (btnUndo) {
            btnUndo.disabled = (historyStack.length === 0);
        }
    }

    function undoStep() {
        if (historyStack.length === 0) return false;
        var snapshot = historyStack.pop();

        // Restore state
        appState = snapshot.state;
        inputLogHistory = snapshot.inputLogHistory;
        briefLogHistory = snapshot.briefLogHistory;

        // Remove last calculation card from DOM
        var steps = outputContainer.querySelectorAll('.calc-step');
        if (steps.length > 0) {
            steps[steps.length - 1].remove();
        }

        // Restore welcome box if no calculation steps remain
        if (outputContainer.querySelectorAll('.calc-step').length === 0 && welcomeBox) {
            welcomeBox.style.display = 'block';
        }

        // Re-render known quantities
        var knownList = [];
        for (var k in appState.variables) {
            knownList.push(k + " = " + Quantities.ascii_qvalue(appState.variables[k]));
        }
        updateKnownQuantities(knownList);

        // Put the undone command back into the editor
        if (typeof snapshot.commandText === 'string') {
            commandsTextarea.value = snapshot.commandText;
            commandsTextarea.focus();
            commandsTextarea.selectionStart = commandsTextarea.value.length;
            commandsTextarea.selectionEnd = commandsTextarea.value.length;
        }

        // Save to localStorage
        saveState();

        // Update Undo button state
        updateUndoButtonState();

        return true;
    }

    function handleUndoClick() {
        if (historyStack.length === 0) return;
        undoStep();
        if (historyStep > 0) {
            historyStep--;
        }
        suppressPopstateCount++;
        try {
            history.back();
        } catch (e) {
            suppressPopstateCount--;
        }
    }

    // 9. Reset Session
    function resetSession() {
        if (inputLogHistory.length > 0 && !confirm('Are you sure you want to reset all calculations?')) {
            return;
        }
        appState = new Calculator.State();
        inputLogHistory = [];
        briefLogHistory = [];
        historyStack = [];
        historyStep = 0;
        try {
            history.replaceState({ step: 0 }, document.title);
        } catch (e) {
            // Ignore
        }
        updateUndoButtonState();

        outputContainer.innerHTML = '';
        if (welcomeBox) {
            outputContainer.appendChild(welcomeBox);
            welcomeBox.style.display = 'block';
        }
        updateKnownQuantities([]);
        commandsTextarea.value = '';
        localStorage.removeItem('pqcalc_session');
        commandsTextarea.focus();
    }

    // 9. Resubmit Input History
    function resubmitHistory() {
        var allInput = inputLogHistory.join('');
        if (!allInput.trim()) {
            alert('No previous calculation commands to resubmit.');
            return;
        }
        commandsTextarea.value = allInput;
        commandsTextarea.focus();
        commandsTextarea.selectionStart = commandsTextarea.value.length;
        commandsTextarea.selectionEnd = commandsTextarea.value.length;
    }

    // 10. LocalStorage Session Persistence
    function saveState() {
        try {
            var data = {
                inputLog: inputLogHistory.join(''),
                timestamp: Date.now()
            };
            localStorage.setItem('pqcalc_session', JSON.stringify(data));
        } catch (e) {
            // Ignore if localStorage is disabled
        }
    }

    function loadSavedState() {
        try {
            var raw = localStorage.getItem('pqcalc_session');
            if (raw) {
                var data = JSON.parse(raw);
                if (data && data.inputLog && data.inputLog.trim()) {
                    commandsTextarea.value = data.inputLog;
                    runCalculation();
                }
            }
        } catch (e) {
            // Ignore
        }
    }

    // 11. Export Modal Handling
    function openExportModal() {
        var inputPre = document.getElementById('export-input-log');
        var knownPre = document.getElementById('export-known');
        var logbookDiv = document.getElementById('export-logbook');
        var libreDiv = document.getElementById('export-libretexts');
        var shareLink = document.getElementById('export-share-link');

        var fullInput = inputLogHistory.join('');
        var fullBriefLog = briefLogHistory.join('\n');
        var knownList = [];
        for (var k in appState.variables) {
            knownList.push(k + " = " + Quantities.ascii_qvalue(appState.variables[k]));
        }

        if (inputPre) inputPre.textContent = fullInput || '(No inputs yet)';
        if (knownPre) knownPre.textContent = knownList.join('\n') || '(No quantities defined yet)';
        if (logbookDiv) {
            logbookDiv.innerHTML = fullBriefLog || '<p><em>No calculation log</em></p>';
            renderMath(logbookDiv);
        }
        if (libreDiv) {
            libreDiv.textContent = stripHtml(fullBriefLog);
        }
        if (shareLink) {
            var encoded = encodeURIComponent(fullInput);
            var url = window.location.origin + window.location.pathname + '?prefill=' + encoded;
            shareLink.value = url;
        }

        exportModal.classList.add('active');
    }

    function closeExportModal() {
        exportModal.classList.remove('active');
    }

    // 12. Help Modal Handling
    function openHelpModal() {
        helpModal.classList.add('active');
    }

    function closeHelpModal() {
        helpModal.classList.remove('active');
    }

    // Setup Event Listeners
    function setupEvents() {
        btnCalculate.addEventListener('click', runCalculation);
        if (btnUndo) {
            btnUndo.addEventListener('click', handleUndoClick);
        }
        btnReset.addEventListener('click', resetSession);
        btnResubmit.addEventListener('click', resubmitHistory);
        btnExport.addEventListener('click', openExportModal);
        btnHelp.addEventListener('click', openHelpModal);

        // Popstate handler for browser Back / Forward buttons
        window.addEventListener('popstate', function (e) {
            if (suppressPopstateCount > 0) {
                suppressPopstateCount--;
                return;
            }

            var targetStep = (e.state && typeof e.state.step === 'number') ? e.state.step : 0;
            if (targetStep < historyStep) {
                while (historyStep > targetStep && historyStack.length > 0) {
                    historyStep--;
                    undoStep();
                }
            }
        });

        // Global Ctrl+Z shortcut when not inside the textarea
        document.addEventListener('keydown', function (e) {
            if ((e.ctrlKey || e.metaKey) && (e.key === 'z' || e.key === 'Z') && !e.shiftKey) {
                if (document.activeElement !== commandsTextarea && historyStack.length > 0) {
                    e.preventDefault();
                    handleUndoClick();
                }
            }
        });

        // Enter key handling (Enter = Calculate, Shift+Enter = Newline)
        commandsTextarea.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                runCalculation();
            } else if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                runCalculation();
            }
        });

        // Close modals on overlay or close button click
        document.querySelectorAll('.modal-close-btn, .modal-close-action').forEach(function (btn) {
            btn.addEventListener('click', function () {
                closeExportModal();
                closeHelpModal();
            });
        });

        document.querySelectorAll('.modal-overlay').forEach(function (overlay) {
            overlay.addEventListener('click', function (e) {
                if (e.target === overlay) {
                    closeExportModal();
                    closeHelpModal();
                }
            });
        });

        // Copy LibreTexts button
        var btnCopyLibre = document.getElementById('btn-copy-libre');
        if (btnCopyLibre) {
            btnCopyLibre.addEventListener('click', function () {
                var libreDiv = document.getElementById('export-libretexts');
                if (libreDiv) {
                    navigator.clipboard.writeText(libreDiv.textContent).then(function () {
                        btnCopyLibre.textContent = 'Copied!';
                        setTimeout(function () {
                            btnCopyLibre.textContent = 'Copy LibreTexts';
                        }, 2000);
                    });
                }
            });
        }

        // Print button
        var btnPrintExport = document.getElementById('btn-print-export');
        if (btnPrintExport) {
            btnPrintExport.addEventListener('click', function () {
                window.print();
            });
        }

        // Help examples click-to-try
        document.querySelectorAll('.btn-try-example').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var code = this.getAttribute('data-code');
                if (code) {
                    commandsTextarea.value = code;
                    closeHelpModal();
                    commandsTextarea.focus();
                }
            });
        });

        // Welcome examples
        document.querySelectorAll('.welcome-try-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var code = this.getAttribute('data-code');
                if (code) {
                    commandsTextarea.value = code;
                    runCalculation();
                }
            });
        });
    }

    // Check URL parameters (?prefill=... or ?switch=...)
    function checkUrlParams() {
        var params = new URLSearchParams(window.location.search);
        if (params.has('prefill')) {
            var prefill = params.get('prefill');
            if (prefill) {
                commandsTextarea.value = prefill;
                runCalculation();
                return true;
            }
        }
        if (params.has('switch')) {
            var switches = params.get('switch').split('*');
            var cmds = switches.map(function (s) {
                return '__' + s + '__ = 1';
            }).join('\n');
            commandsTextarea.value = cmds;
            runCalculation();
            return true;
        }
        return false;
    }

    // Initialize App
    function init() {
        initSelectors();
        initTouchBar();
        setupEvents();

        try {
            history.replaceState({ step: 0 }, document.title);
        } catch (e) {
            // Ignore if in restricted environment
        }
        updateUndoButtonState();

        var loadedFromUrl = checkUrlParams();
        if (!loadedFromUrl) {
            loadSavedState();
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
