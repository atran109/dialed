/**
 * Content script that tracks keypresses on the page.
 * Sends count to background script every 2 seconds.
 */

let keypressCount = 0;
let lastReportTime = Date.now();

const REPORT_INTERVAL = 2000; // 2 seconds

/**
 * Track keydown events
 */
document.addEventListener('keydown', (event) => {
  keypressCount++;
}, { passive: true });

/**
 * Send keypress count to background script
 */
function reportKeypressCount() {
  const now = Date.now();

  if (now - lastReportTime >= REPORT_INTERVAL) {
    // Send to background script
    chrome.runtime.sendMessage({
      type: 'keypress_count',
      count: keypressCount
    }).catch(() => {
      // Extension context invalidated, ignore
    });

    // Reset counter and timer
    keypressCount = 0;
    lastReportTime = now;
  }

  // Schedule next report
  requestAnimationFrame(reportKeypressCount);
}

/**
 * Start reporting
 */
reportKeypressCount();
