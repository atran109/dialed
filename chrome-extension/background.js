/**
 * Background service worker for tracking active tab and idle state.
 * Sends data to backend every 2 seconds.
 */

const BACKEND_URL = 'http://localhost:8000/log/tab';
const LOG_INTERVAL = 2000; // 2 seconds

// Track keypress counts from content scripts
let keypressCountByTab = {};

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'keypress_count' && sender.tab) {
    keypressCountByTab[sender.tab.id] = message.count;
  }
});

// Remove keypress count when tab is closed
chrome.tabs.onRemoved.addListener((tabId) => {
  delete keypressCountByTab[tabId];
});

/**
 * Extract domain from URL
 */
function extractDomain(url) {
  try {
    const urlObj = new URL(url);
    return urlObj.hostname;
  } catch (e) {
    return 'unknown';
  }
}

/**
 * Get current active tab info
 */
async function getActiveTabInfo() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    if (!tab) {
      return null;
    }

    // Get idle state (active, idle, or locked)
    const idleState = await chrome.idle.queryState(15); // 15 seconds threshold

    // Get keypress count for this tab
    const keypressCount = keypressCountByTab[tab.id] || 0;

    return {
      timestamp: Date.now() / 1000, // Unix timestamp in seconds
      domain: extractDomain(tab.url),
      title: tab.title || 'No Title',
      idle_state: idleState,
      keypress_count: keypressCount
    };

  } catch (error) {
    console.error('Error getting active tab info:', error);
    return null;
  }
}

/**
 * Send tab log to backend
 */
async function sendTabLog(data) {
  try {
    const response = await fetch(BACKEND_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data)
    });

    if (!response.ok) {
      console.error('Failed to send tab log:', response.status, response.statusText);
    }

  } catch (error) {
    // Backend might not be running, fail silently
    if (error.message.includes('Failed to fetch')) {
      // Backend not running, this is expected sometimes
      return;
    }
    console.error('Error sending tab log:', error);
  }
}

/**
 * Main logging loop
 */
async function logActiveTab() {
  const tabInfo = await getActiveTabInfo();

  if (tabInfo) {
    await sendTabLog(tabInfo);
  }

  // Schedule next log
  setTimeout(logActiveTab, LOG_INTERVAL);
}

/**
 * Start logging when extension loads
 */
console.log('Dialed extension loaded');
logActiveTab();

/**
 * Extension icon click handler
 */
chrome.action.onClicked.addListener(() => {
  console.log('Extension icon clicked');
});
