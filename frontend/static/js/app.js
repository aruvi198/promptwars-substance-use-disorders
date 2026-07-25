document.addEventListener('DOMContentLoaded', () => {
    // 1. Role Selection Styling for Login Page
    const roleOptions = document.querySelectorAll('.role-option');
    const roleInput = document.getElementById('selected-role');
    
    if (roleOptions.length > 0 && roleInput) {
        roleOptions.forEach(option => {
            option.addEventListener('click', () => {
                roleOptions.forEach(opt => opt.classList.remove('selected'));
                option.classList.add('selected');
                const role = option.getAttribute('data-role');
                roleInput.value = role;
            });
        });
    }

    // 2. Audio Capture & API Integrations
    const recordBtn = document.getElementById('record-btn');
    const recordStatus = document.getElementById('record-status');
    const speechText = document.getElementById('speech-text');
    const aiResponseText = document.getElementById('ai-response-text');
    const speakerBtn = document.getElementById('speaker-btn');
    const severityBtns = document.querySelectorAll('.severity-btn');
    const emergencyBtn = document.querySelector('.emergency-btn');
    
    // Simple inline WAV encoder class for recording audio/wav format natively in the browser
    class WavAudioRecorder {
        constructor(stream) {
            this.stream = stream;
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.sampleRate = this.audioContext.sampleRate;
            this.source = this.audioContext.createMediaStreamSource(stream);
            this.node = this.audioContext.createScriptProcessor(4096, 1, 1);
            this.buffers = [];
            
            this.node.onaudioprocess = (e) => {
                const channelData = e.inputBuffer.getChannelData(0);
                this.buffers.push(new Float32Array(channelData));
            };
        }

        start() {
            this.source.connect(this.node);
            this.node.connect(this.audioContext.destination);
        }

        stop() {
            this.node.disconnect();
            this.source.disconnect();
            if (this.audioContext.state !== 'closed') {
                this.audioContext.close();
            }

            const mergedBuffer = this.mergeBuffers(this.buffers);
            const wavBuffer = this.encodeWAV(mergedBuffer, this.sampleRate);
            return new Blob([wavBuffer], { type: 'audio/wav' });
        }

        mergeBuffers(buffers) {
            let totalLength = 0;
            for (let i = 0; i < buffers.length; i++) {
                totalLength += buffers[i].length;
            }
            const result = new Float32Array(totalLength);
            let offset = 0;
            for (let i = 0; i < buffers.length; i++) {
                result.set(buffers[i], offset);
                offset += buffers[i].length;
            }
            return result;
        }

        encodeWAV(samples, sampleRate) {
            const buffer = new ArrayBuffer(44 + samples.length * 2);
            const view = new DataView(buffer);

            this.writeString(view, 0, 'RIFF');
            view.setUint32(4, 36 + samples.length * 2, true);
            this.writeString(view, 8, 'WAVE');
            this.writeString(view, 12, 'fmt ');
            view.setUint32(16, 16, true);
            view.setUint16(20, 1, true);
            view.setUint16(22, 1, true);
            view.setUint32(24, sampleRate, true);
            view.setUint32(28, sampleRate * 2, true);
            view.setUint16(32, 2, true);
            view.setUint16(34, 16, true);
            this.writeString(view, 36, 'data');
            view.setUint32(40, samples.length * 2, true);

            this.floatTo16BitPCM(view, 44, samples);
            return buffer;
        }

        floatTo16BitPCM(output, offset, input) {
            for (let i = 0; i < input.length; i++, offset += 2) {
                let s = Math.max(-1, Math.min(1, input[i]));
                output.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
            }
        }

        writeString(view, offset, string) {
            for (let i = 0; i < string.length; i++) {
                view.setUint8(offset + i, string.charCodeAt(i));
            }
        }
    }

    let activeStream = null;
    let wavRecorder = null;
    let isRecording = false;
    let isProcessing = false;
    let currentSeverity = 'general_wellness';
    let lastGeneratedResponse = '';

    // Severity toggles
    if (severityBtns.length > 0) {
        severityBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                severityBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentSeverity = btn.getAttribute('data-severity');
                console.log(`Severity updated to: ${currentSeverity}`);
            });
        });
    }

    if (emergencyBtn) {
        emergencyBtn.addEventListener('click', async () => {
            try {
                await fetch('/api/emergency', { method: 'POST' });
                recordStatus.textContent = 'Caretaker alert sent';
            } catch (err) {
                console.error('Emergency alert failed:', err);
            }
        });
    }

    // Mic recording trigger
    if (recordBtn) {
        recordBtn.addEventListener('click', async () => {
            if (isProcessing) {
                return;
            }

            if (!isRecording) {
                try {
                    activeStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    startRecording(activeStream);
                } catch (err) {
                    console.error('Error accessing microphone:', err);
                    recordStatus.textContent = 'Microphone access is required to use speech-to-text.';
                    alert('Microphone access is required to use speech-to-text. Please enable it in browser settings.');
                }
            } else {
                await stopRecording();
            }
        });
    }

    function startRecording(stream) {
        wavRecorder = new WavAudioRecorder(stream);
        wavRecorder.start();
        
        isRecording = true;
        recordBtn.classList.add('recording');
        recordStatus.textContent = 'Listening... Tap to stop';
        console.log('Recording started...');
    }

    async function stopRecording() {
        if (!wavRecorder || !isRecording) {
            return;
        }

        isProcessing = true;
        const audioBlob = wavRecorder.stop();
        
        if (activeStream) {
            activeStream.getTracks().forEach(track => track.stop());
            activeStream = null;
        }
        
        isRecording = false;
        wavRecorder = null;
        recordBtn.classList.remove('recording');
        recordStatus.textContent = 'Processing speech...';
        console.log('Recording stopped...');
        
        try {
            await handleAudioUpload(audioBlob);
        } finally {
            isProcessing = false;
        }
    }

    // Upload audio blob to Flask STT endpoint
    async function handleAudioUpload(blob) {
        const formData = new FormData();
        formData.append('audio', blob, 'recording.wav');

        try {
            const response = await fetch('/api/transcribe', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) throw new Error('Transcription failed');
            
            const data = await response.json();
            const transcribedText = data.text || '';
            
            if (speechText) {
                speechText.textContent = transcribedText;
            }
            
            // Auto generate response
            await fetchAIResponse(transcribedText);
            
        } catch (err) {
            console.error('STT API Error:', err);
            recordStatus.textContent = 'Error during transcription. Please try again.';
            if (speechText) {
                speechText.textContent = '[Transcription error occurred. Please type or re-record.]';
            }
        }
    }

    // Call LLM API with context prompt wrappers
    async function fetchAIResponse(text) {
        recordStatus.textContent = 'Generating guidance...';
        
        try {
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: text,
                    severity: currentSeverity
                })
            });

            if (!response.ok) throw new Error('Response generation failed');
            
            const data = await response.json();
            lastGeneratedResponse = data.response;
            
            if (aiResponseText) {
                aiResponseText.textContent = lastGeneratedResponse;
            }
            
            recordStatus.textContent = 'Tap to talk';
            
            // Automatically play back using TTS
            speakResponse(lastGeneratedResponse);

        } catch (err) {
            console.error('LLM API Error:', err);
            recordStatus.textContent = 'Error generating response';
            if (aiResponseText) {
                aiResponseText.textContent = 'We are currently encountering connectivity issues. Please contact your support network.';
            }
        }
    }

    // Multi-modal TTS synthesis
    function speakResponse(text) {
        if (!text) return;

        // Try standard browser SpeechSynthesis first
        if ('speechSynthesis' in window) {
            // Cancel current speaking
            window.speechSynthesis.cancel();
            
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 1.0;
            utterance.pitch = 1.0;
            
            utterance.onerror = (e) => {
                console.warn('Web Speech API failed or interrupted. Trying backend TTS endpoint...', e);
                speakViaBackend(text);
            };

            window.speechSynthesis.speak(utterance);
        } else {
            speakViaBackend(text);
        }
    }

    // Playback fallback using Flask TTS audio stream
    function speakViaBackend(text) {
        const audioUrl = `/api/tts?text=${encodeURIComponent(text)}`;
        const audio = new Audio(audioUrl);
        audio.play().catch(e => {
            console.error('Backend audio playback failed:', e);
        });
    }

    // Manual speaker button trigger
    if (speakerBtn) {
        speakerBtn.addEventListener('click', () => {
            if (lastGeneratedResponse) {
                speakResponse(lastGeneratedResponse);
            } else {
                speakResponse(aiResponseText ? aiResponseText.textContent : '');
            }
        });
    }
});
