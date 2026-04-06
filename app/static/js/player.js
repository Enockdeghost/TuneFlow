class TuneFlowPlayer {
    constructor() {
        // DOM elements (same as before)
        this.cover = document.getElementById('playerCover');
        this.titleEl = document.getElementById('playerTitle');
        this.artistEl = document.getElementById('playerArtist');
        this.playPauseBtn = document.getElementById('playerPlayPause');
        this.prevBtn = document.getElementById('playerPrev');
        this.nextBtn = document.getElementById('playerNext');
        this.seekSlider = document.getElementById('playerSeek');
        this.progressBar = document.getElementById('playerProgressBar');
        this.currentTimeEl = document.getElementById('playerCurrentTime');
        this.durationEl = document.getElementById('playerDuration');
        this.volumeSlider = document.getElementById('playerVolume');
        this.volumeBtn = document.getElementById('playerVolumeBtn');
        this.shuffleBtn = document.getElementById('playerShuffle');
        this.repeatBtn = document.getElementById('playerRepeat');
        this.likeBtn = document.getElementById('playerFavorite');
        this.speedBtn = document.getElementById('playerSpeedBtn');
        this.queueBtn = document.getElementById('playerQueueBtn');
        this.eqBtn = document.getElementById('playerEqBtn');
        this.fullPlayer = document.getElementById('fullPlayer');
        this.fullCover = document.getElementById('fullPlayerCover');
        this.fullTitle = document.getElementById('fullPlayerTitle');
        this.fullArtist = document.getElementById('fullPlayerArtist');
        this.fullPlayPause = document.getElementById('fullPlayPause');
        this.fullPrev = document.getElementById('fullPrev');
        this.fullNext = document.getElementById('fullNext');

        // Audio & state
        this.audio = new Audio();
        this.currentTrack = null;
        this.queue = [];
        this.currentIndex = -1;
        this.repeatMode = 'off';
        this.shuffleMode = false;
        this.speed = 1.0;
        this.isPlaying = false;
        this.isSeeking = false;
        this.volume = 0.8;

        // Equalizer – will be created once
        this.audioContext = null;
        this.sourceNode = null;
        this.eqNodes = [];
        this.eqEnabled = false;
        this.frequencies = [32, 64, 125, 250, 500, 1000, 2000, 4000, 8000, 16000];
        this.gainValues = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
        this.eqPanel = document.getElementById('eqPanel');
        this.closeEqBtn = document.getElementById('closeEqBtn');
        this.eqToggle = document.getElementById('eqToggle');
        this.eqBandsContainer = document.getElementById('eqBands');

        // Queue panel
        this.queuePanel = document.getElementById('queuePanel');
        this.closeQueueBtn = document.getElementById('closeQueueBtn');
        this.queueList = document.querySelector('.queue-list');

        this.init();
    }

    init() {
        // Audio events
        this.audio.addEventListener('timeupdate', () => this.updateTimeDisplay());
        this.audio.addEventListener('ended', () => this.next());
        this.audio.addEventListener('loadedmetadata', () => {
            this.durationEl.textContent = this.formatTime(this.audio.duration);
            this.seekSlider.max = 100;
        });

        // Button events
        this.playPauseBtn.addEventListener('click', () => this.togglePlayPause());
        this.prevBtn.addEventListener('click', () => this.prev());
        this.nextBtn.addEventListener('click', () => this.next());
        this.seekSlider.addEventListener('input', (e) => this.seek(e.target.value));
        this.volumeSlider.addEventListener('input', (e) => this.setVolume(e.target.value));
        this.shuffleBtn.addEventListener('click', () => this.toggleShuffle());
        this.repeatBtn.addEventListener('click', () => this.toggleRepeat());
        this.likeBtn.addEventListener('click', () => this.toggleLike());
        this.speedBtn.addEventListener('click', () => this.cycleSpeed());
        this.queueBtn.addEventListener('click', () => this.toggleQueue());
        this.eqBtn.addEventListener('click', () => this.toggleEqPanel());

        if (this.closeEqBtn) this.closeEqBtn.addEventListener('click', () => this.hideEqPanel());
        if (this.closeQueueBtn) this.closeQueueBtn.addEventListener('click', () => this.hideQueue());

        // Full‑player sync
        if (this.fullPlayPause) this.fullPlayPause.addEventListener('click', () => this.togglePlayPause());
        if (this.fullPrev) this.fullPrev.addEventListener('click', () => this.prev());
        if (this.fullNext) this.fullNext.addEventListener('click', () => this.next());

        // Initial UI
        this.updateVolumeIcon();
        this.updateRepeatButton();
        this.updateShuffleButton();
        this.updateSpeedButton();
        this.disableControls();

        // Equalizer setup – create UI but not the audio context yet
        this.createEqBands();
        this.loadEqSettings();
        this.eqToggle.addEventListener('change', (e) => this.setEqEnabled(e.target.checked));
        document.querySelectorAll('.eq-preset').forEach(btn => {
            btn.addEventListener('click', () => this.applyPreset(btn.getAttribute('data-preset')));
        });

        // Persistence – restore track but DO NOT auto‑play
        window.addEventListener('beforeunload', () => this.saveState());
        this.restoreState(false);

        window.player = this;
        console.log('Player ready');
    }

    // ---------- Persistence ----------
    saveState() {
        const state = {
            currentTrack: this.currentTrack,
            currentTime: this.audio.currentTime,
            isPlaying: false,
            queue: this.queue,
            currentIndex: this.currentIndex,
            repeatMode: this.repeatMode,
            shuffleMode: this.shuffleMode,
            speed: this.speed,
            volume: this.volume,
            eqEnabled: this.eqEnabled,
            gainValues: this.gainValues
        };
        localStorage.setItem('tuneflow_player_state', JSON.stringify(state));
    }

    restoreState(autoPlay = false) {
        const saved = localStorage.getItem('tuneflow_player_state');
        if (saved) {
            try {
                const state = JSON.parse(saved);
                this.queue = state.queue || [];
                this.currentIndex = state.currentIndex !== undefined ? state.currentIndex : -1;
                this.repeatMode = state.repeatMode || 'off';
                this.shuffleMode = state.shuffleMode || false;
                this.speed = state.speed || 1.0;
                this.volume = state.volume !== undefined ? state.volume : 0.8;
                this.eqEnabled = state.eqEnabled || false;
                this.gainValues = state.gainValues || [0,0,0,0,0,0,0,0,0,0];
                if (state.currentTrack) {
                    setTimeout(() => {
                        this.playTrack(state.currentTrack.id, state.currentTrack)
                            .then(() => {
                                this.audio.currentTime = state.currentTime || 0;
                                this.isPlaying = false;
                                this.updatePlayPauseIcon();
                                this.updateUI();
                            });
                    }, 500);
                }
            } catch(e) { console.error(e); }
        }
    }

    // ---------- Playback ----------
    async playTrack(trackId, trackData = null) {
        try {
            let track = trackData;
            if (!track) {
                if (typeof trackId === 'string' && trackId.startsWith('local_')) {
                    const local = window.localTracks?.find(t => t.id === trackId);
                    if (local) return this.playLocalTrack(local);
                    return;
                }
                const resp = await fetch(`/api/tracks/${trackId}`);
                if (!resp.ok) throw new Error(`Failed to fetch track: ${resp.status}`);
                track = await resp.json();
            }
            if (track.is_local) return this.playLocalTrack(track);

            this.currentTrack = track;
            this.currentIndex = this.queue.findIndex(t => t.id == trackId);
            if (this.currentIndex === -1) {
                this.queue = [track];
                this.currentIndex = 0;
            }

            const streamResp = await fetch(`/api/tracks/${trackId}/stream`);
            if (!streamResp.ok) throw new Error(`Stream endpoint error: ${streamResp.status}`);
            const data = await streamResp.json();
            if (!data.stream_url) throw new Error('No stream URL returned');

            // Set audio source
            this.audio.src = data.stream_url;
            this.audio.load();

            // Create AudioContext and source node only once (on first play)
            if (!this.audioContext) {
                this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
                // Wait for user interaction to resume (will be done in play button click)
            }
            if (!this.sourceNode && this.audioContext && this.audio.src) {
                // Create source node now that audio has a src
                this.sourceNode = this.audioContext.createMediaElementSource(this.audio);
                this.createEqChain();
            }

            // Do NOT auto-play – user must click play
            this.isPlaying = false;
            this.updateUI();
            this.enableControls();
            this.checkLikeStatus();
            this.renderQueue();
        } catch (error) {
            console.error('Play error:', error);
            alert('Cannot play track: ' + error.message);
        }
    }

    playLocalTrack(localTrack) {
        if (!localTrack) return;
        const trackObj = {
            id: localTrack.id,
            title: localTrack.name,
            artist: localTrack.artist || 'Local File',
            cover_url: null,
            is_local: true,
            blobUrl: localTrack.blobUrl
        };
        this.currentTrack = trackObj;
        this.audio.src = trackObj.blobUrl;
        this.audio.load();

        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (!this.sourceNode && this.audioContext && this.audio.src) {
            this.sourceNode = this.audioContext.createMediaElementSource(this.audio);
            this.createEqChain();
        }

        this.isPlaying = false;
        this.updateUI();
        this.enableControls();
        this.likeBtn.disabled = true;
    }

    createEqChain() {
        if (!this.audioContext || !this.sourceNode) return;
        // Disconnect any existing EQ nodes
        if (this.eqNodes.length) {
            let last = this.sourceNode;
            for (let i = 0; i < this.eqNodes.length; i++) {
                try { last.disconnect(this.eqNodes[i]); } catch(e) {}
                last = this.eqNodes[i];
            }
            try { last.disconnect(this.audioContext.destination); } catch(e) {}
        }
        // Build new chain
        let lastNode = this.sourceNode;
        this.eqNodes = [];
        for (let i = 0; i < this.frequencies.length; i++) {
            const filter = this.audioContext.createBiquadFilter();
            filter.type = 'peaking';
            filter.frequency.value = this.frequencies[i];
            filter.Q.value = 1;
            filter.gain.value = this.eqEnabled ? this.gainValues[i] : 0;
            lastNode.connect(filter);
            lastNode = filter;
            this.eqNodes.push(filter);
        }
        lastNode.connect(this.audioContext.destination);
    }

    resumeAudioContext() {
        if (this.audioContext && this.audioContext.state === 'suspended') {
            this.audioContext.resume();
        }
    }

    updateUI() {
        if (!this.currentTrack) return;
        this.titleEl.textContent = this.currentTrack.title || 'Unknown';
        this.artistEl.textContent = this.currentTrack.artist || 'Unknown Artist';
        this.cover.src = this.currentTrack.cover_url || '/static/img/default-cover.png';
        if (this.fullTitle) this.fullTitle.textContent = this.currentTrack.title;
        if (this.fullArtist) this.fullArtist.textContent = this.currentTrack.artist;
        if (this.fullCover) this.fullCover.src = this.currentTrack.cover_url || '/static/img/default-cover.png';
        this.updatePlayPauseIcon();
    }

    updateTimeDisplay() {
        if (this.isSeeking) return;
        const current = this.audio.currentTime;
        const duration = this.audio.duration || 0;
        const percent = (current / duration) * 100;
        this.progressBar.style.width = `${percent}%`;
        this.seekSlider.value = percent;
        this.currentTimeEl.textContent = this.formatTime(current);
        this.durationEl.textContent = this.formatTime(duration);
    }

    seek(value) {
        if (!this.audio.duration) return;
        this.isSeeking = true;
        const newTime = (value / 100) * this.audio.duration;
        this.audio.currentTime = newTime;
        const percent = (newTime / this.audio.duration) * 100;
        this.progressBar.style.width = `${percent}%`;
        this.seekSlider.value = percent;
        this.currentTimeEl.textContent = this.formatTime(newTime);
        setTimeout(() => { this.isSeeking = false; }, 100);
    }

    setVolume(value) {
        this.volume = parseFloat(value);
        this.audio.volume = this.volume;
        this.volumeSlider.value = this.volume;
        this.updateVolumeIcon();
    }

    updateVolumeIcon() {
        const icon = this.volumeBtn.querySelector('i');
        if (this.volume === 0) icon.className = 'fas fa-volume-mute';
        else if (this.volume < 0.5) icon.className = 'fas fa-volume-down';
        else icon.className = 'fas fa-volume-up';
    }

    togglePlayPause() {
        if (!this.currentTrack) return;
        if (this.isPlaying) {
            this.audio.pause();
            this.isPlaying = false;
        } else {
            // User gesture – play audio and resume AudioContext
            this.audio.play().catch(e => console.warn(e));
            this.isPlaying = true;
            this.resumeAudioContext();
        }
        this.updatePlayPauseIcon();
    }

    updatePlayPauseIcon() {
        const icon = this.playPauseBtn.querySelector('i');
        icon.className = this.isPlaying ? 'fas fa-pause' : 'fas fa-play';
        if (this.fullPlayPause) {
            const fullIcon = this.fullPlayPause.querySelector('i');
            fullIcon.className = this.isPlaying ? 'fas fa-pause' : 'fas fa-play';
        }
    }

    prev() {
        if (!this.currentTrack) return;
        if (this.shuffleMode && this.queue.length > 1) {
            let newIndex;
            do { newIndex = Math.floor(Math.random() * this.queue.length); }
            while (newIndex === this.currentIndex && this.queue.length > 1);
            this.currentIndex = newIndex;
            this.playTrack(this.queue[this.currentIndex].id, this.queue[this.currentIndex]);
        } else if (this.currentIndex > 0) {
            this.currentIndex--;
            this.playTrack(this.queue[this.currentIndex].id, this.queue[this.currentIndex]);
        } else if (this.repeatMode === 'all' && this.queue.length) {
            this.currentIndex = this.queue.length - 1;
            this.playTrack(this.queue[this.currentIndex].id, this.queue[this.currentIndex]);
        }
    }

    next() {
        if (!this.currentTrack) return;
        if (this.shuffleMode && this.queue.length > 1) {
            let newIndex;
            do { newIndex = Math.floor(Math.random() * this.queue.length); }
            while (newIndex === this.currentIndex && this.queue.length > 1);
            this.currentIndex = newIndex;
            this.playTrack(this.queue[this.currentIndex].id, this.queue[this.currentIndex]);
        } else if (this.currentIndex + 1 < this.queue.length) {
            this.currentIndex++;
            this.playTrack(this.queue[this.currentIndex].id, this.queue[this.currentIndex]);
        } else if (this.repeatMode === 'all' && this.queue.length) {
            this.currentIndex = 0;
            this.playTrack(this.queue[this.currentIndex].id, this.queue[this.currentIndex]);
        }
    }

    cycleSpeed() {
        const speeds = [0.5, 0.75, 1, 1.25, 1.5, 2];
        let idx = speeds.indexOf(this.speed);
        idx = (idx + 1) % speeds.length;
        this.speed = speeds[idx];
        this.audio.playbackRate = this.speed;
        this.updateSpeedButton();
    }

    updateSpeedButton() {
        this.speedBtn.textContent = `${this.speed}x`;
    }

    toggleShuffle() {
        this.shuffleMode = !this.shuffleMode;
        this.updateShuffleButton();
    }

    updateShuffleButton() {
        if (this.shuffleMode) this.shuffleBtn.classList.add('active');
        else this.shuffleBtn.classList.remove('active');
    }

    toggleRepeat() {
        const modes = ['off', 'one', 'all'];
        let idx = modes.indexOf(this.repeatMode);
        idx = (idx + 1) % modes.length;
        this.repeatMode = modes[idx];
        this.updateRepeatButton();
    }

    updateRepeatButton() {
        const active = this.repeatMode !== 'off';
        if (active) this.repeatBtn.classList.add('active');
        else this.repeatBtn.classList.remove('active');
    }

    async toggleLike() {
        if (!this.currentTrack || this.currentTrack.is_local) return;
        const wasLiked = this.likeBtn.classList.contains('active');
        const method = wasLiked ? 'DELETE' : 'POST';
        try {
            const resp = await fetch(`/api/tracks/${this.currentTrack.id}/like`, { method });
            if (resp.ok) this.likeBtn.classList.toggle('active');
        } catch (err) { console.error(err); }
    }

    async checkLikeStatus() {
        if (!this.currentTrack || this.currentTrack.is_local) return;
        try {
            const resp = await fetch(`/api/tracks/${this.currentTrack.id}/like-status`);
            const data = await resp.json();
            if (data.liked) this.likeBtn.classList.add('active');
            else this.likeBtn.classList.remove('active');
        } catch (err) { console.error(err); }
    }

    setQueue(tracks, startIndex = 0) {
        this.queue = [...tracks];
        if (startIndex >= 0 && startIndex < this.queue.length) {
            this.currentIndex = startIndex;
            this.playTrack(this.queue[this.currentIndex].id, this.queue[this.currentIndex]);
        }
        this.renderQueue();
    }

    // ---------- Queue ----------
    toggleQueue() {
        if (this.queuePanel.style.display === 'flex') this.hideQueue();
        else this.showQueue();
    }
    showQueue() {
        this.renderQueue();
        this.queuePanel.style.display = 'flex';
    }
    hideQueue() {
        this.queuePanel.style.display = 'none';
    }
    renderQueue() {
        if (!this.queueList) return;
        if (this.queue.length === 0) {
            this.queueList.innerHTML = '<div class="queue-empty">Queue is empty</div>';
            return;
        }
        this.queueList.innerHTML = this.queue.map((track, idx) => `
            <div class="queue-item ${idx === this.currentIndex ? 'active' : ''}" data-index="${idx}">
                <div class="queue-cover"><img src="${track.cover_url || '/static/img/default-cover.png'}"></div>
                <div class="queue-info">
                    <div class="queue-title">${escapeHtml(track.title)}</div>
                    <div class="queue-artist">${escapeHtml(track.artist || 'Unknown')}</div>
                </div>
                <button class="queue-play-btn" data-index="${idx}"><i class="fas fa-play"></i></button>
                <button class="queue-remove-btn" data-index="${idx}"><i class="fas fa-trash"></i></button>
            </div>
        `).join('');
        this.queueList.querySelectorAll('.queue-play-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const idx = parseInt(btn.getAttribute('data-index'));
                this.playFromQueue(idx);
            });
        });
        this.queueList.querySelectorAll('.queue-remove-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const idx = parseInt(btn.getAttribute('data-index'));
                this.removeFromQueue(idx);
            });
        });
        this.queueList.querySelectorAll('.queue-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (e.target.closest('.queue-play-btn') || e.target.closest('.queue-remove-btn')) return;
                const idx = parseInt(item.getAttribute('data-index'));
                this.playFromQueue(idx);
            });
        });
    }
    playFromQueue(index) {
        if (index >= 0 && index < this.queue.length) {
            this.currentIndex = index;
            this.playTrack(this.queue[this.currentIndex].id, this.queue[this.currentIndex]);
            this.renderQueue();
        }
    }
    removeFromQueue(index) {
        if (index >= 0 && index < this.queue.length) {
            this.queue.splice(index, 1);
            if (index < this.currentIndex) this.currentIndex--;
            else if (index === this.currentIndex) {
                if (this.queue.length > 0) {
                    this.currentIndex = Math.min(this.currentIndex, this.queue.length - 1);
                    this.playTrack(this.queue[this.currentIndex].id, this.queue[this.currentIndex]);
                } else {
                    this.currentTrack = null;
                    this.disableControls();
                    this.updateUI();
                }
            }
            this.renderQueue();
        }
    }

    // ---------- Equalizer ----------
    createEqBands() {
        if (!this.eqBandsContainer) return;
        this.eqBandsContainer.innerHTML = '';
        this.frequencies.forEach((freq, idx) => {
            const bandDiv = document.createElement('div');
            bandDiv.className = 'eq-band';
            const label = document.createElement('label');
            label.innerHTML = `<span>${freq} Hz</span><span id="eqVal${idx}">0 dB</span>`;
            const slider = document.createElement('input');
            slider.type = 'range';
            slider.min = -12;
            slider.max = 12;
            slider.step = 0.5;
            slider.value = this.gainValues[idx];
            slider.addEventListener('input', (e) => {
                const val = parseFloat(e.target.value);
                this.gainValues[idx] = val;
                document.getElementById(`eqVal${idx}`).innerText = `${val} dB`;
                if (this.eqEnabled && this.eqNodes[idx]) this.eqNodes[idx].gain.value = val;
                this.saveEqSettings();
            });
            bandDiv.appendChild(label);
            bandDiv.appendChild(slider);
            this.eqBandsContainer.appendChild(bandDiv);
        });
    }

    loadEqSettings() {
        const saved = localStorage.getItem('tuneflow_eq');
        if (saved) {
            const data = JSON.parse(saved);
            this.eqEnabled = data.enabled;
            this.gainValues = data.gains;
            this.eqToggle.checked = this.eqEnabled;
        } else {
            this.eqEnabled = false;
            this.gainValues = [0,0,0,0,0,0,0,0,0,0];
            this.eqToggle.checked = false;
        }
        if (this.eqBandsContainer) {
            for (let i = 0; i < this.gainValues.length; i++) {
                const slider = this.eqBandsContainer.querySelectorAll('input')[i];
                if (slider) slider.value = this.gainValues[i];
                const span = document.getElementById(`eqVal${i}`);
                if (span) span.innerText = `${this.gainValues[i]} dB`;
            }
        }
    }

    saveEqSettings() {
        localStorage.setItem('tuneflow_eq', JSON.stringify({ enabled: this.eqEnabled, gains: this.gainValues }));
    }

    setEqEnabled(enabled) {
        this.eqEnabled = enabled;
        if (this.eqNodes.length) {
            for (let i = 0; i < this.eqNodes.length; i++) {
                this.eqNodes[i].gain.value = enabled ? this.gainValues[i] : 0;
            }
        }
        this.saveEqSettings();
    }

    applyPreset(preset) {
        const presets = {
            flat: [0,0,0,0,0,0,0,0,0,0],
            pop: [2,3,4,3,1,0,-1,-1,-1,-2],
            rock: [4,3,2,1,0,-1,-2,-2,-1,0],
            jazz: [1,2,3,2,1,0,0,1,2,3],
            classical: [0,0,0,0,0,0,0,0,0,0],
            bass: [6,5,4,3,1,0,0,0,0,0],
            treble: [0,0,0,0,0,1,3,5,6,6]
        };
        const gains = presets[preset] || presets.flat;
        this.gainValues = gains.slice();
        for (let i = 0; i < this.gainValues.length; i++) {
            const slider = this.eqBandsContainer.querySelectorAll('input')[i];
            if (slider) slider.value = this.gainValues[i];
            const span = document.getElementById(`eqVal${i}`);
            if (span) span.innerText = `${this.gainValues[i]} dB`;
            if (this.eqEnabled && this.eqNodes[i]) this.eqNodes[i].gain.value = this.gainValues[i];
        }
        this.saveEqSettings();
    }

    toggleEqPanel() {
        if (this.eqPanel.style.display === 'flex') this.hideEqPanel();
        else this.showEqPanel();
    }
    showEqPanel() { this.eqPanel.style.display = 'flex'; }
    hideEqPanel() { this.eqPanel.style.display = 'none'; }

    // ---------- Utilities ----------
    enableControls() {
        this.playPauseBtn.disabled = false;
        this.prevBtn.disabled = false;
        this.nextBtn.disabled = false;
        this.seekSlider.disabled = false;
        this.shuffleBtn.disabled = false;
        this.repeatBtn.disabled = false;
        this.likeBtn.disabled = !this.currentTrack?.is_local ? false : true;
        this.volumeSlider.disabled = false;
        this.speedBtn.disabled = false;
        this.queueBtn.disabled = false;
        this.eqBtn.disabled = false;
    }

    disableControls() {
        this.playPauseBtn.disabled = true;
        this.prevBtn.disabled = true;
        this.nextBtn.disabled = true;
        this.seekSlider.disabled = true;
        this.shuffleBtn.disabled = true;
        this.repeatBtn.disabled = true;
        this.likeBtn.disabled = true;
        this.volumeSlider.disabled = true;
        this.speedBtn.disabled = true;
        this.queueBtn.disabled = true;
        this.eqBtn.disabled = true;
    }

    formatTime(seconds) {
        if (isNaN(seconds)) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>]/g, m => m === '&' ? '&amp;' : m === '<' ? '&lt;' : '&gt;');
}

let player;
document.addEventListener('DOMContentLoaded', () => {
    player = new TuneFlowPlayer();
    const globalSearch = document.getElementById('globalSearch');
    if (globalSearch) {
        globalSearch.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                window.location.href = `/search?q=${encodeURIComponent(globalSearch.value)}`;
            }
        });
    }
});