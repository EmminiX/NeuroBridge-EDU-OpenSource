/**
 * Optimized Audio Worklet Processor for Educational Content
 * Enhanced WebAudio processing for classroom acoustics and real-time preprocessing
 */

class OptimizedAudioProcessor extends AudioWorkletProcessor {
    constructor(options) {
        super();
        
        // Configuration from options
        const config = options.processorOptions || {};
        this.sampleRate = sampleRate;
        this.bufferSize = config.bufferSize || 4096;
        this.enablePreprocessing = config.enablePreprocessing !== false;
        this.educationalMode = config.educationalMode !== false;
        
        // Educational environment parameters
        this.classroomParams = {
            hvacFreqLow: 40,      // HVAC noise frequency range
            hvacFreqHigh: 120,
            speechFreqLow: 300,   // Primary speech frequency range
            speechFreqHigh: 3400,
            preEmphasisAlpha: 0.97, // Pre-emphasis filter coefficient
            noiseGateThreshold: 0.01, // Noise gate threshold
            adaptiveGainTarget: 0.3   // Target RMS level
        };
        
        // Processing buffers and state
        this.inputBuffer = [];
        this.outputBuffer = [];
        this.previousSample = 0.0;
        
        // Adaptive filters
        this.noiseFloor = 0.001;
        this.speechPresenceHistory = [];
        this.gainHistory = [];
        this.maxGainHistorySize = 100;
        
        // High-pass filter for HVAC noise (Butterworth, 2nd order)
        this.highPassFilter = this.createButterworthHighPass(80, this.sampleRate);
        
        // Low-pass filter for high-frequency noise (Butterworth, 2nd order)
        this.lowPassFilter = this.createButterworthLowPass(8000, this.sampleRate);
        
        // DC blocking filter
        this.dcBlocker = {
            x1: 0.0,
            y1: 0.0,
            alpha: 0.995
        };
        
        // Performance monitoring
        this.processedSamples = 0;
        this.performanceStats = {
            inputLevels: [],
            outputLevels: [],
            gainAdjustments: [],
            processingTime: 0
        };
        
        // Notify main thread of initialization
        this.port.postMessage({
            type: 'worklet-initialized',
            config: {
                sampleRate: this.sampleRate,
                bufferSize: this.bufferSize,
                enablePreprocessing: this.enablePreprocessing,
                educationalMode: this.educationalMode
            }
        });
        
        console.log('Optimized Audio Worklet initialized for educational content processing');
    }
    
    process(inputs, outputs, parameters) {
        const input = inputs[0];
        const output = outputs[0];
        
        if (!input || !input[0] || input[0].length === 0) {
            return true;
        }
        
        const inputSamples = input[0];
        const outputSamples = output[0];
        const frameLength = inputSamples.length;
        
        const startTime = performance.now();
        
        try {
            if (this.enablePreprocessing) {
                // Apply educational audio processing pipeline
                this.processEducationalAudio(inputSamples, outputSamples, frameLength);
            } else {
                // Pass-through mode
                for (let i = 0; i < frameLength; i++) {
                    outputSamples[i] = inputSamples[i];
                }
            }
            
            // Update performance statistics
            const processingTime = performance.now() - startTime;
            this.updatePerformanceStats(inputSamples, outputSamples, processingTime);
            
            // Accumulate samples for chunked processing
            this.accumulateForChunking(outputSamples);
            
            this.processedSamples += frameLength;
            
            return true;
            
        } catch (error) {
            console.error('Audio worklet processing error:', error);
            // Fallback to pass-through
            for (let i = 0; i < frameLength; i++) {
                outputSamples[i] = inputSamples[i] || 0;
            }
            return true;
        }
    }
    
    processEducationalAudio(inputSamples, outputSamples, frameLength) {
        for (let i = 0; i < frameLength; i++) {
            let sample = inputSamples[i];
            
            // Step 1: DC blocking filter
            sample = this.applyDCBlocker(sample);
            
            // Step 2: High-pass filter for HVAC noise reduction
            sample = this.applyHighPassFilter(sample);
            
            // Step 3: Pre-emphasis filter for consonant enhancement
            if (this.educationalMode) {
                sample = this.applyPreEmphasis(sample);
            }
            
            // Step 4: Adaptive noise gate
            sample = this.applyNoiseGate(sample);
            
            // Step 5: Adaptive gain control
            sample = this.applyAdaptiveGain(sample, i, frameLength);
            
            // Step 6: Low-pass filter for high-frequency noise
            sample = this.applyLowPassFilter(sample);
            
            // Step 7: Soft limiting to prevent clipping
            sample = this.applySoftLimiter(sample);
            
            outputSamples[i] = sample;
        }
    }
    
    applyDCBlocker(sample) {
        // High-pass filter to remove DC offset: y[n] = α(y[n-1] + x[n] - x[n-1])
        const output = this.dcBlocker.alpha * (this.dcBlocker.y1 + sample - this.dcBlocker.x1);
        
        this.dcBlocker.x1 = sample;
        this.dcBlocker.y1 = output;
        
        return output;
    }
    
    applyHighPassFilter(sample) {
        // Apply Butterworth high-pass filter for HVAC noise reduction
        return this.processButterworthFilter(sample, this.highPassFilter);
    }
    
    applyLowPassFilter(sample) {
        // Apply Butterworth low-pass filter for high-frequency noise
        return this.processButterworthFilter(sample, this.lowPassFilter);
    }
    
    applyPreEmphasis(sample) {
        // Pre-emphasis filter: y[n] = x[n] - α*x[n-1]
        const output = sample - this.classroomParams.preEmphasisAlpha * this.previousSample;
        this.previousSample = sample;
        return output;
    }
    
    applyNoiseGate(sample) {
        // Simple noise gate for classroom environments
        const magnitude = Math.abs(sample);
        
        if (magnitude < this.classroomParams.noiseGateThreshold) {
            // Gentle gating - don't completely silence, just reduce
            return sample * 0.1;
        }
        
        return sample;
    }
    
    applyAdaptiveGain(sample, sampleIndex, frameLength) {
        // Calculate frame RMS every 256 samples for gain adaptation
        const analysisInterval = 256;
        
        if (sampleIndex % analysisInterval === 0) {
            this.updateAdaptiveGain();
        }
        
        // Apply current gain
        const currentGain = this.getCurrentGain();
        return sample * currentGain;
    }
    
    applySoftLimiter(sample) {
        // Soft limiter to prevent harsh clipping
        const threshold = 0.95;
        const knee = 0.1;
        
        const magnitude = Math.abs(sample);
        
        if (magnitude > threshold - knee) {
            const excess = magnitude - (threshold - knee);
            const compressedExcess = excess * (1 / (1 + excess / knee));
            const limitedMagnitude = (threshold - knee) + compressedExcess;
            
            return sample >= 0 ? limitedMagnitude : -limitedMagnitude;
        }
        
        return sample;
    }
    
    updateAdaptiveGain() {
        // Calculate recent RMS level
        const recentSamples = Math.min(512, this.inputBuffer.length);
        if (recentSamples === 0) return;
        
        let rmsSum = 0;
        for (let i = this.inputBuffer.length - recentSamples; i < this.inputBuffer.length; i++) {
            const sample = this.inputBuffer[i] || 0;
            rmsSum += sample * sample;
        }
        
        const currentRMS = Math.sqrt(rmsSum / recentSamples);
        const targetRMS = this.classroomParams.adaptiveGainTarget;
        
        if (currentRMS > 0.001) { // Avoid division by zero
            let requiredGain = targetRMS / currentRMS;
            
            // Limit gain adjustments for stability
            const maxGain = 10.0; // 20dB max boost
            const minGain = 0.1;  // -20dB max cut
            
            requiredGain = Math.max(minGain, Math.min(maxGain, requiredGain));
            
            // Smooth gain changes
            const gainSmoothingFactor = 0.1;
            const previousGain = this.getCurrentGain();
            const smoothedGain = previousGain + gainSmoothingFactor * (requiredGain - previousGain);
            
            this.gainHistory.push(smoothedGain);
            
            // Limit history size
            if (this.gainHistory.length > this.maxGainHistorySize) {
                this.gainHistory.shift();
            }
        }
    }
    
    getCurrentGain() {
        return this.gainHistory.length > 0 ? this.gainHistory[this.gainHistory.length - 1] : 1.0;
    }
    
    createButterworthHighPass(cutoffFreq, sampleRate) {
        // 2nd order Butterworth high-pass filter coefficients
        const nyquist = sampleRate * 0.5;
        const normalizedCutoff = cutoffFreq / nyquist;
        
        // Pre-warp frequency for bilinear transform
        const omega = Math.tan(Math.PI * normalizedCutoff);
        const omega2 = omega * omega;
        const sqrt2 = Math.sqrt(2);
        
        // Calculate coefficients
        const k1 = sqrt2 * omega;
        const k2 = omega2;
        const a0 = k2 + k1 + 1;
        
        return {
            // Direct form II coefficients
            b0: 1 / a0,
            b1: -2 / a0,
            b2: 1 / a0,
            a1: (2 * (k2 - 1)) / a0,
            a2: (k2 - k1 + 1) / a0,
            // State variables
            x1: 0, x2: 0,
            y1: 0, y2: 0
        };
    }
    
    createButterworthLowPass(cutoffFreq, sampleRate) {
        // 2nd order Butterworth low-pass filter coefficients
        const nyquist = sampleRate * 0.5;
        const normalizedCutoff = cutoffFreq / nyquist;
        
        // Pre-warp frequency for bilinear transform
        const omega = Math.tan(Math.PI * normalizedCutoff);
        const omega2 = omega * omega;
        const sqrt2 = Math.sqrt(2);
        
        // Calculate coefficients
        const k1 = sqrt2 * omega;
        const k2 = omega2;
        const a0 = k2 + k1 + 1;
        
        return {
            // Direct form II coefficients
            b0: k2 / a0,
            b1: 2 * k2 / a0,
            b2: k2 / a0,
            a1: (2 * (k2 - 1)) / a0,
            a2: (k2 - k1 + 1) / a0,
            // State variables
            x1: 0, x2: 0,
            y1: 0, y2: 0
        };
    }
    
    processButterworthFilter(input, filter) {
        // Direct form II implementation
        const output = filter.b0 * input + filter.b1 * filter.x1 + filter.b2 * filter.x2
                      - filter.a1 * filter.y1 - filter.a2 * filter.y2;
        
        // Update state
        filter.x2 = filter.x1;
        filter.x1 = input;
        filter.y2 = filter.y1;
        filter.y1 = output;
        
        return output;
    }
    
    accumulateForChunking(samples) {
        // Add samples to buffer for chunked processing
        for (let i = 0; i < samples.length; i++) {
            this.outputBuffer.push(samples[i]);
        }
        
        // Send chunk when buffer is full
        if (this.outputBuffer.length >= this.bufferSize) {
            const chunk = this.outputBuffer.slice(0, this.bufferSize);
            this.outputBuffer = this.outputBuffer.slice(this.bufferSize);
            
            // Convert to PCM16 for compatibility
            const pcm16Array = new Int16Array(chunk.length);
            for (let i = 0; i < chunk.length; i++) {
                // Clamp and convert to 16-bit PCM
                const clampedSample = Math.max(-1, Math.min(1, chunk[i]));
                pcm16Array[i] = Math.round(clampedSample * 32767);
            }
            
            // Post processed chunk to main thread
            this.port.postMessage({
                type: 'audio-chunk',
                data: pcm16Array,
                timestamp: currentTime,
                sampleRate: this.sampleRate,
                channelCount: 1,
                processingStats: this.getProcessingStats()
            });
        }
    }
    
    updatePerformanceStats(inputSamples, outputSamples, processingTime) {
        // Calculate input and output levels
        let inputLevel = 0;
        let outputLevel = 0;
        
        for (let i = 0; i < inputSamples.length; i++) {
            inputLevel += inputSamples[i] * inputSamples[i];
            outputLevel += outputSamples[i] * outputSamples[i];
        }
        
        inputLevel = Math.sqrt(inputLevel / inputSamples.length);
        outputLevel = Math.sqrt(outputLevel / outputSamples.length);
        
        this.performanceStats.inputLevels.push(inputLevel);
        this.performanceStats.outputLevels.push(outputLevel);
        this.performanceStats.processingTime += processingTime;
        
        // Limit stats arrays size
        const maxStatsSize = 100;
        if (this.performanceStats.inputLevels.length > maxStatsSize) {
            this.performanceStats.inputLevels.shift();
            this.performanceStats.outputLevels.shift();
        }
        
        // Calculate gain adjustment
        if (inputLevel > 0.001) {
            const gainAdjustment = outputLevel / inputLevel;
            this.performanceStats.gainAdjustments.push(gainAdjustment);
            
            if (this.performanceStats.gainAdjustments.length > maxStatsSize) {
                this.performanceStats.gainAdjustments.shift();
            }
        }
    }
    
    getProcessingStats() {
        const stats = this.performanceStats;
        
        const avgInputLevel = stats.inputLevels.reduce((a, b) => a + b, 0) / Math.max(1, stats.inputLevels.length);
        const avgOutputLevel = stats.outputLevels.reduce((a, b) => a + b, 0) / Math.max(1, stats.outputLevels.length);
        const avgGainAdjustment = stats.gainAdjustments.reduce((a, b) => a + b, 0) / Math.max(1, stats.gainAdjustments.length);
        
        return {
            averageInputLevel: avgInputLevel,
            averageOutputLevel: avgOutputLevel,
            averageGainAdjustment: avgGainAdjustment,
            currentGain: this.getCurrentGain(),
            processedSamples: this.processedSamples,
            totalProcessingTime: stats.processingTime
        };
    }
    
    // Message handling for runtime configuration
    handleMessage(event) {
        const { type, data } = event.data;
        
        switch (type) {
            case 'update-config':
                this.updateConfiguration(data);
                break;
            case 'reset-filters':
                this.resetFilterStates();
                break;
            case 'get-stats':
                this.port.postMessage({
                    type: 'stats-response',
                    data: this.getProcessingStats()
                });
                break;
            default:
                console.warn('Unknown message type:', type);
        }
    }
    
    updateConfiguration(config) {
        if (config.enablePreprocessing !== undefined) {
            this.enablePreprocessing = config.enablePreprocessing;
        }
        
        if (config.educationalMode !== undefined) {
            this.educationalMode = config.educationalMode;
        }
        
        if (config.classroomParams) {
            Object.assign(this.classroomParams, config.classroomParams);
        }
        
        this.port.postMessage({
            type: 'config-updated',
            config: {
                enablePreprocessing: this.enablePreprocessing,
                educationalMode: this.educationalMode,
                classroomParams: this.classroomParams
            }
        });
    }
    
    resetFilterStates() {
        // Reset all filter states
        this.previousSample = 0.0;
        this.dcBlocker = { x1: 0.0, y1: 0.0, alpha: 0.995 };
        
        // Reset Butterworth filter states
        if (this.highPassFilter) {
            this.highPassFilter.x1 = this.highPassFilter.x2 = 0;
            this.highPassFilter.y1 = this.highPassFilter.y2 = 0;
        }
        
        if (this.lowPassFilter) {
            this.lowPassFilter.x1 = this.lowPassFilter.x2 = 0;
            this.lowPassFilter.y1 = this.lowPassFilter.y2 = 0;
        }
        
        // Reset adaptive gain
        this.gainHistory = [];
        this.speechPresenceHistory = [];
        
        // Reset buffers
        this.inputBuffer = [];
        this.outputBuffer = [];
        
        console.log('Audio worklet filters reset');
    }
}

// Register the processor
registerProcessor('optimized-audio-processor', OptimizedAudioProcessor);