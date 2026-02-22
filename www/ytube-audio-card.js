/**
 * yt-dlp Audio Queue Card for Home Assistant
 * A custom Lovelace card for managing the ytube_audio queue
 */

class YtubeAudioCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._queue = [];
    this._currentIndex = -1;
  }

  set hass(hass) {
    const firstSet = !this._hass;
    this._hass = hass;
    this._updateQueue();
    this._render();
    
    // Subscribe to queue update events on first hass set
    if (firstSet && hass.connection) {
      this._subscribeToEvents();
    }
  }

  _subscribeToEvents() {
    // Subscribe to ytube_audio_queue_updated events
    this._hass.connection.subscribeEvents((event) => {
      if (event.data.entity_id === this._config.entity) {
        this._queue = event.data.items || [];
        this._currentIndex = event.data.current_index ?? -1;
        this._render();
      }
    }, 'ytube_audio_queue_updated');
  }

  setConfig(config) {
    this._config = {
      entity: config.entity || null,
      name: config.name || 'yt-dlp Audio',
      max_visible: config.max_visible || 5,
      show_thumbnail: config.show_thumbnail !== false,
      show_seek: config.show_seek !== false,
      ...config
    };
    this._selectedEntity = config.entity || null;
    this._mediaPosition = 0;
    this._mediaDuration = 0;
    this._seeking = false;
  }

  _updateQueue() {
    // Get queue from service response or sensor
    if (!this._hass || !this._selectedEntity) return;
    
    // Try to get queue sensor if it exists
    const sensorId = `sensor.ytube_audio_queue_${this._selectedEntity.replace('media_player.', '')}`;
    const sensor = this._hass.states[sensorId];
    
    if (sensor && sensor.attributes) {
      this._queue = sensor.attributes.items || [];
      this._currentIndex = sensor.attributes.current_index || -1;
    }

    // Get media player position/duration
    const playerState = this._hass.states[this._selectedEntity];
    if (playerState && !this._seeking) {
      this._mediaPosition = playerState.attributes.media_position || 0;
      this._mediaDuration = playerState.attributes.media_duration || 0;
      this._mediaState = playerState.state;
      
      // Update position based on time elapsed since last update
      if (playerState.state === 'playing' && playerState.attributes.media_position_updated_at) {
        const lastUpdate = new Date(playerState.attributes.media_position_updated_at).getTime();
        const elapsed = (Date.now() - lastUpdate) / 1000;
        this._mediaPosition = Math.min(
          this._mediaPosition + elapsed,
          this._mediaDuration
        );
      }
    }
  }

  _getMediaPlayers() {
    if (!this._hass) return [];
    return Object.keys(this._hass.states)
      .filter(id => id.startsWith('media_player.'))
      .map(id => ({
        id,
        name: this._hass.states[id].attributes.friendly_name || id.replace('media_player.', '')
      }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }

  _render() {
    if (!this._config || !this._hass) return;

    const maxVisible = this._config.max_visible;
    const mediaPlayers = this._getMediaPlayers();
    const hasEntity = !!this._selectedEntity;

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          --card-bg: var(--ha-card-background, var(--card-background-color, #fff));
          --primary-color: var(--primary-color, #03a9f4);
          --text-primary: var(--primary-text-color, #212121);
          --text-secondary: var(--secondary-text-color, #727272);
          --divider: var(--divider-color, rgba(0,0,0,0.12));
        }
        
        ha-card {
          padding: 16px;
          background: var(--card-bg);
        }
        
        .header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 12px;
        }
        
        .title {
          font-size: 1.1em;
          font-weight: 500;
          color: var(--text-primary);
        }
        
        .entity-selector {
          margin-bottom: 16px;
        }
        
        .entity-select {
          width: 100%;
          padding: 10px 12px;
          border: 1px solid var(--divider);
          border-radius: 8px;
          font-size: 14px;
          background: var(--card-bg);
          color: var(--text-primary);
          outline: none;
          cursor: pointer;
          transition: border-color 0.2s;
        }
        
        .entity-select:focus {
          border-color: var(--primary-color);
        }
        
        .input-section {
          display: flex;
          gap: 8px;
          margin-bottom: 16px;
        }
        
        .url-input {
          flex: 1;
          padding: 10px 12px;
          border: 1px solid var(--divider);
          border-radius: 8px;
          font-size: 14px;
          background: var(--card-bg);
          color: var(--text-primary);
          outline: none;
          transition: border-color 0.2s;
        }
        
        .url-input:focus {
          border-color: var(--primary-color);
        }
        
        .url-input::placeholder {
          color: var(--text-secondary);
        }
        
        .btn {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 40px;
          height: 40px;
          border: none;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.2s;
          background: var(--primary-color);
          color: white;
        }
        
        .btn:hover {
          opacity: 0.85;
          transform: scale(1.05);
        }
        
        .btn:active {
          transform: scale(0.95);
        }
        
        .btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
          transform: none;
        }
        
        .btn-secondary {
          background: var(--divider);
          color: var(--text-primary);
        }
        
        .btn ha-icon {
          --mdc-icon-size: 20px;
        }
        
        .queue-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 8px 0;
          border-bottom: 1px solid var(--divider);
          margin-bottom: 8px;
        }
        
        .queue-title {
          font-size: 0.9em;
          font-weight: 500;
          color: var(--text-secondary);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        
        .queue-controls {
          display: flex;
          gap: 4px;
        }
        
        .queue-controls .btn {
          width: 32px;
          height: 32px;
          background: transparent;
          color: var(--text-secondary);
        }
        
        .queue-controls .btn:hover:not(:disabled) {
          color: var(--primary-color);
          background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.1);
        }
        
        .queue-list {
          max-height: ${maxVisible * 56}px;
          overflow-y: auto;
          scrollbar-width: thin;
        }
        
        .queue-list::-webkit-scrollbar {
          width: 4px;
        }
        
        .queue-list::-webkit-scrollbar-thumb {
          background: var(--divider);
          border-radius: 2px;
        }
        
        .queue-item {
          display: flex;
          align-items: center;
          padding: 8px;
          border-radius: 8px;
          cursor: pointer;
          transition: background 0.2s;
          gap: 12px;
        }
        
        .queue-item:hover {
          background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.08);
        }
        
        .queue-item.active {
          background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.15);
        }
        
        .queue-item-index {
          width: 24px;
          text-align: center;
          font-size: 12px;
          color: var(--text-secondary);
        }
        
        .queue-item.active .queue-item-index {
          color: var(--primary-color);
        }
        
        .queue-item-info {
          flex: 1;
          min-width: 0;
        }
        
        .queue-item-title {
          font-size: 14px;
          color: var(--text-primary);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        
        .queue-item-url {
          font-size: 11px;
          color: var(--text-secondary);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        
        .queue-item-remove {
          opacity: 0;
          transition: opacity 0.2s;
          background: transparent;
          border: none;
          color: var(--text-secondary);
          cursor: pointer;
          padding: 4px;
          border-radius: 4px;
        }
        
        .queue-item:hover .queue-item-remove {
          opacity: 1;
        }
        
        .queue-item-remove:hover {
          color: #f44336;
          background: rgba(244, 67, 54, 0.1);
        }
        
        .empty-queue {
          text-align: center;
          padding: 24px;
          color: var(--text-secondary);
          font-size: 14px;
        }
        
        .empty-queue ha-icon {
          --mdc-icon-size: 48px;
          opacity: 0.3;
          margin-bottom: 8px;
        }
        
        .no-entity {
          text-align: center;
          padding: 16px;
          color: var(--text-secondary);
        }
        
        .seek-section {
          margin-bottom: 16px;
          padding: 0 4px;
        }
        
        .seek-slider-container {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        
        .seek-time {
          font-size: 11px;
          color: var(--text-secondary);
          min-width: 40px;
          font-variant-numeric: tabular-nums;
        }
        
        .seek-time.end {
          text-align: right;
        }
        
        .seek-slider {
          flex: 1;
          -webkit-appearance: none;
          appearance: none;
          height: 4px;
          border-radius: 2px;
          background: var(--divider);
          outline: none;
          cursor: pointer;
        }
        
        .seek-slider::-webkit-slider-thumb {
          -webkit-appearance: none;
          appearance: none;
          width: 14px;
          height: 14px;
          border-radius: 50%;
          background: var(--primary-color);
          cursor: pointer;
          transition: transform 0.1s;
        }
        
        .seek-slider::-webkit-slider-thumb:hover {
          transform: scale(1.2);
        }
        
        .seek-slider::-moz-range-thumb {
          width: 14px;
          height: 14px;
          border-radius: 50%;
          background: var(--primary-color);
          cursor: pointer;
          border: none;
        }
        
        .seek-slider:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        
        .seek-slider:disabled::-webkit-slider-thumb {
          cursor: not-allowed;
        }
      </style>
      
      <ha-card>
        <div class="header">
          <span class="title">${this._config.name}</span>
        </div>
        
        ${!this._config.entity ? `
          <div class="entity-selector">
            <select class="entity-select" id="entitySelect">
              <option value="">Select a media player...</option>
              ${mediaPlayers.map(p => `
                <option value="${p.id}" ${this._selectedEntity === p.id ? 'selected' : ''}>
                  ${p.name}
                </option>
              `).join('')}
            </select>
          </div>
        ` : ''}
        
        <div class="input-section">
          <input 
            type="text" 
            class="url-input" 
            placeholder="Paste URL or playlist..."
            id="urlInput"
            ${!hasEntity ? 'disabled' : ''}
          >
          <button class="btn btn-secondary" id="addBtn" title="Add to queue" ${!hasEntity ? 'disabled' : ''}>
            <ha-icon icon="mdi:playlist-plus"></ha-icon>
          </button>
          <button class="btn" id="playBtn" title="Play now" ${!hasEntity ? 'disabled' : ''}>
            <ha-icon icon="mdi:play"></ha-icon>
          </button>
        </div>
        
        ${hasEntity && this._config.show_seek ? `
          <div class="seek-section">
            <div class="seek-slider-container">
              <span class="seek-time">${this._formatTime(this._mediaPosition)}</span>
              <input 
                type="range" 
                class="seek-slider" 
                id="seekSlider"
                min="0" 
                max="${this._mediaDuration || 100}" 
                value="${this._mediaPosition}"
                ${!this._mediaDuration ? 'disabled' : ''}
              >
              <span class="seek-time end">${this._formatTime(this._mediaDuration)}</span>
            </div>
          </div>
        ` : ''}
        
        ${hasEntity ? `
          <div class="queue-header">
            <span class="queue-title">Queue (${this._queue.length} items)</span>
            <div class="queue-controls">
              <button class="btn" id="prevBtn" title="Previous">
                <ha-icon icon="mdi:skip-previous"></ha-icon>
              </button>
              <button class="btn" id="nextBtn" title="Next">
                <ha-icon icon="mdi:skip-next"></ha-icon>
              </button>
              <button class="btn" id="clearBtn" title="Clear queue">
                <ha-icon icon="mdi:playlist-remove"></ha-icon>
              </button>
            </div>
          </div>
          
          <div class="queue-list">
            ${this._queue.length === 0 ? `
              <div class="empty-queue">
                <ha-icon icon="mdi:playlist-music"></ha-icon>
                <div>Queue is empty</div>
                <div>Add a URL above to get started</div>
              </div>
            ` : this._queue.map((item, index) => `
              <div class="queue-item ${index === this._currentIndex ? 'active' : ''}" data-index="${index}">
                <span class="queue-item-index">${index === this._currentIndex ? '▶' : index + 1}</span>
                <div class="queue-item-info">
                  <div class="queue-item-title">${item.title || 'Unknown'}</div>
                  <div class="queue-item-url">${this._truncateUrl(item.url)}</div>
                </div>
                <button class="queue-item-remove" data-index="${index}">
                  <ha-icon icon="mdi:close"></ha-icon>
                </button>
              </div>
            `).join('')}
          </div>
        ` : `
          <div class="no-entity">
            Select a media player above to manage the queue
          </div>
        `}
      </ha-card>
    `;

    this._attachEventListeners();
  }

  _truncateUrl(url) {
    if (!url) return '';
    try {
      const parsed = new URL(url);
      return parsed.hostname + parsed.pathname.substring(0, 30) + '...';
    } catch {
      return url.substring(0, 40) + '...';
    }
  }

  _formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  _attachEventListeners() {
    const entitySelect = this.shadowRoot.getElementById('entitySelect');
    const urlInput = this.shadowRoot.getElementById('urlInput');
    const addBtn = this.shadowRoot.getElementById('addBtn');
    const playBtn = this.shadowRoot.getElementById('playBtn');
    const prevBtn = this.shadowRoot.getElementById('prevBtn');
    const nextBtn = this.shadowRoot.getElementById('nextBtn');
    const clearBtn = this.shadowRoot.getElementById('clearBtn');
    const seekSlider = this.shadowRoot.getElementById('seekSlider');

    // Entity selector change handler
    entitySelect?.addEventListener('change', (e) => {
      this._selectedEntity = e.target.value || null;
      this._queue = [];
      this._currentIndex = -1;
      this._render();
    });

    // Seek slider handlers
    seekSlider?.addEventListener('input', (e) => {
      this._seeking = true;
      this._mediaPosition = parseFloat(e.target.value);
      // Update time display without full re-render
      const timeDisplay = this.shadowRoot.querySelector('.seek-time');
      if (timeDisplay) {
        timeDisplay.textContent = this._formatTime(this._mediaPosition);
      }
    });

    seekSlider?.addEventListener('change', (e) => {
      const position = parseFloat(e.target.value);
      this._seeking = false;
      
      if (this._selectedEntity) {
        this._hass.callService('ytube_audio', 'seek', {
          media_player: this._selectedEntity,
          timestamp: position
        });
      }
    });

    const addToQueue = (playNow) => {
      const url = urlInput.value.trim();
      if (!url || !this._selectedEntity) return;
      
      this._hass.callService('ytube_audio', 'add_to_queue', {
        url: url,
        media_player: this._selectedEntity,
        play_now: playNow
      });
      urlInput.value = '';
    };

    addBtn?.addEventListener('click', () => addToQueue(false));
    playBtn?.addEventListener('click', () => addToQueue(true));
    urlInput?.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') addToQueue(true);
    });

    prevBtn?.addEventListener('click', () => {
      if (!this._selectedEntity) return;
      this._hass.callService('ytube_audio', 'previous_track', {
        media_player: this._selectedEntity
      });
    });

    nextBtn?.addEventListener('click', () => {
      if (!this._selectedEntity) return;
      this._hass.callService('ytube_audio', 'next_track', {
        media_player: this._selectedEntity
      });
    });

    clearBtn?.addEventListener('click', () => {
      if (!this._selectedEntity) return;
      this._hass.callService('ytube_audio', 'clear_queue', {
        media_player: this._selectedEntity
      });
    });

    // Queue item click handlers
    this.shadowRoot.querySelectorAll('.queue-item-remove').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        if (!this._selectedEntity) return;
        const index = parseInt(btn.dataset.index);
        this._hass.callService('ytube_audio', 'remove_from_queue', {
          media_player: this._selectedEntity,
          index: index
        });
      });
    });
  }

  getCardSize() {
    return 3;
  }

  static getConfigElement() {
    return document.createElement('ytube-audio-card-editor');
  }

  static getStubConfig() {
    return {
      entity: 'media_player.example',
      name: 'yt-dlp Audio',
      max_visible: 5
    };
  }
}

// Card Editor
class YtubeAudioCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  set hass(hass) {
    this._hass = hass;
  }

  setConfig(config) {
    this._config = config;
    this._render();
  }

  _render() {
    this.shadowRoot.innerHTML = `
      <style>
        .form-row {
          margin-bottom: 16px;
        }
        label {
          display: block;
          margin-bottom: 4px;
          font-weight: 500;
        }
        input, select {
          width: 100%;
          padding: 8px;
          border: 1px solid var(--divider-color);
          border-radius: 4px;
        }
      </style>
      
      <div class="form-row">
        <label>Media Player Entity</label>
        <input type="text" id="entity" value="${this._config.entity || ''}">
      </div>
      
      <div class="form-row">
        <label>Card Name</label>
        <input type="text" id="name" value="${this._config.name || 'yt-dlp Audio'}">
      </div>
      
      <div class="form-row">
        <label>Max Visible Queue Items</label>
        <input type="number" id="max_visible" min="3" max="15" value="${this._config.max_visible || 5}">
      </div>
    `;

    this.shadowRoot.querySelectorAll('input').forEach(input => {
      input.addEventListener('change', () => this._valueChanged());
    });
  }

  _valueChanged() {
    const config = {
      ...this._config,
      entity: this.shadowRoot.getElementById('entity').value,
      name: this.shadowRoot.getElementById('name').value,
      max_visible: parseInt(this.shadowRoot.getElementById('max_visible').value) || 5
    };
    
    const event = new CustomEvent('config-changed', {
      detail: { config },
      bubbles: true,
      composed: true
    });
    this.dispatchEvent(event);
  }
}

customElements.define('ytube-audio-card', YtubeAudioCard);
customElements.define('ytube-audio-card-editor', YtubeAudioCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: 'ytube-audio-card',
  name: 'yt-dlp Audio Queue',
  description: 'A card for managing the yt-dlp audio queue with URL input',
  preview: true
});

console.info('%c yt-dlp Audio Card %c v1.0.0 ', 
  'background: #03a9f4; color: white; font-weight: bold;',
  'background: #333; color: white;'
);
