/**
 * Popup script for extension status display
 */

const BACKEND_URL = 'http://localhost:8000';

/**
 * Check if backend is running
 */
async function checkBackendStatus() {
  const indicator = document.getElementById('indicator');
  const statusText = document.getElementById('status-text');
  const statusDiv = document.getElementById('status');

  try {
    const response = await fetch(`${BACKEND_URL}/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(2000)
    });

    if (response.ok) {
      indicator.className = 'indicator active';
      statusText.textContent = 'Backend connected';
      statusDiv.className = 'status';
    } else {
      throw new Error('Backend not healthy');
    }
  } catch (error) {
    indicator.className = 'indicator inactive';
    statusText.textContent = 'Backend offline - run: python backend/app.py';
    statusDiv.className = 'status error';
  }
}

/**
 * Initialize popup
 */
document.addEventListener('DOMContentLoaded', () => {
  checkBackendStatus();

  // Check backend button
  document.getElementById('check-backend').addEventListener('click', (e) => {
    e.preventDefault();
    checkBackendStatus();
  });

  // Settings button (placeholder)
  document.getElementById('open-settings').addEventListener('click', (e) => {
    e.preventDefault();
    alert('Settings page coming soon!');
  });
});
