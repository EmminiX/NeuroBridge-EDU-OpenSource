/**
 * Audio Worklet Processor for Real-time Audio Processing
 * Replaces the deprecated ScriptProcessorNode
 */

class AudioRecorderWorkletProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.isRecording = false;
    this.targetSampleRate = 16000; // Target sample rate for transcription
    this.nativeSampleRate = 48000; // Default - will be updated when we receive actual rate
    this.buffer = new Float32Array(0); // FIXED: Use Float32Array instead of regular array
    this.bufferLength = 0; // Track actual length
    this.maxBufferSize = 48000 * 5; // 5 seconds max buffer
    this.lastSendTime = 0;
    this.sendInterval = 100; // Send every 100ms for stability
    this.optimalChunkSize = 8192; // ~170ms at 48kHz
    
    console.log('🎵 Audio worklet processor initialized:', {
      targetSampleRate: this.targetSampleRate,
      nativeSampleRate: this.nativeSampleRate,
      ratio: this.nativeSampleRate / this.targetSampleRate
    });
    
    // Listen for messages from main thread
    this.port.onmessage = (event) => {
      const { type, data } = event.data;
      
      switch (type) {
        case 'start':
          this.isRecording = true;
          if (data) {
            if (data.sampleRate) {
              this.nativeSampleRate = data.sampleRate; // Actual browser context rate (48000)
              console.log('🎵 Updated native sample rate to:', this.nativeSampleRate);
            }
            if (data.targetSampleRate) {
              this.targetSampleRate = data.targetSampleRate; // Target for transcription (16000)
              console.log('🎵 Updated target sample rate to:', this.targetSampleRate);
            }
          }
          console.log('🎵 Audio worklet recording started with rates:', {
            native: this.nativeSampleRate,
            target: this.targetSampleRate,
            ratio: this.nativeSampleRate / this.targetSampleRate
          });
          break;
        case 'stop':
          this.isRecording = false;
          console.log('🎵 Audio worklet recording stopped');
          break;
        case 'pause':
          this.isRecording = false;
          break;
        case 'resume':
          this.isRecording = true;
          break;
      }
    };
  }

  // Audio preprocessing for better speech recognition
  preprocessAudio(buffer) {
    if (buffer.length === 0) return buffer;
    
    console.log('🎧 Minimal preprocessing ENABLED - basic normalization only');
    
    // FIXED: Use Float32Array for consistent data types
    const processedBuffer = new Float32Array(buffer.length);
    for (let i = 0; i < buffer.length; i++) {
      // Clamp to valid Float32 range and copy
      processedBuffer[i] = Math.max(-1.0, Math.min(1.0, buffer[i]));
    }
    
    return processedBuffer;
    
    // ORIGINAL CODE (disabled for debugging):
    // 1. Calculate RMS for gain normalization
    // const rms = Math.sqrt(
    //   buffer.reduce((sum, sample) => sum + sample * sample, 0) / buffer.length
    // );
    // 
    // 2. Apply automatic gain control if signal is too quiet
    // let processedBufferOriginal = buffer.slice(); // Copy buffer
    
    // if (rms > 0 && rms < 0.01) { // Very quiet signal
    //   const gainFactor = Math.min(3.0, 0.01 / rms); // Boost up to 3x
    //   processedBufferOriginal = processedBufferOriginal.map(sample => 
    //     Math.max(-1, Math.min(1, sample * gainFactor))
    //   );
    // }
    // 
    // // 3. Apply high-pass filter to remove low-frequency noise
    // processedBufferOriginal = this.highPassFilter(processedBufferOriginal);
    // 
    // return processedBufferOriginal;
  }

  // Simple high-pass filter to remove low-frequency noise
  highPassFilter(buffer) {
    if (buffer.length < 2) return buffer;
    
    // FIXED: Use Float32Array for consistent data types
    const filtered = new Float32Array(buffer.length);
    const alpha = 0.95; // High-pass filter coefficient
    
    filtered[0] = buffer[0];
    for (let i = 1; i < buffer.length; i++) {
      filtered[i] = alpha * (filtered[i-1] + buffer[i] - buffer[i-1]);
    }
    
    return filtered;
  }

  // Resample audio from native sample rate to target sample rate
  resampleAudio(buffer) {
    // CRITICAL: Always check the actual rates, not just assume they're the same
    if (Math.abs(this.nativeSampleRate - this.targetSampleRate) < 1) {
      console.log('🎧 No resampling needed - same sample rates');
      return buffer; // No resampling needed
    }
    
    const ratio = this.nativeSampleRate / this.targetSampleRate;
    const outputLength = Math.floor(buffer.length / ratio);
    const resampled = new Float32Array(outputLength);
    
    // Calculate some stats before resampling
    let maxInput = 0;
    let rmsInput = 0;
    for (let i = 0; i < Math.min(buffer.length, 1000); i++) {
      maxInput = Math.max(maxInput, Math.abs(buffer[i]));
      rmsInput += buffer[i] * buffer[i];
    }
    rmsInput = Math.sqrt(rmsInput / Math.min(buffer.length, 1000));
    
    // Improved linear interpolation resampling
    for (let i = 0; i < outputLength; i++) {
      const sourceIndex = i * ratio;
      const index = Math.floor(sourceIndex);
      const fraction = sourceIndex - index;
      
      if (index + 1 < buffer.length) {
        resampled[i] = buffer[index] * (1 - fraction) + buffer[index + 1] * fraction;
      } else {
        resampled[i] = buffer[index] || 0;
      }
    }
    
    // Calculate output stats
    let maxOutput = 0;
    let rmsOutput = 0;
    for (let i = 0; i < Math.min(resampled.length, 1000); i++) {
      maxOutput = Math.max(maxOutput, Math.abs(resampled[i]));
      rmsOutput += resampled[i] * resampled[i];
    }
    rmsOutput = Math.sqrt(rmsOutput / Math.min(resampled.length, 1000));
    
    console.log('🎧 Resampling completed:', {
      inputLength: buffer.length,
      outputLength: resampled.length,
      ratio: ratio.toFixed(3),
      inputMaxLevel: maxInput.toFixed(4),
      outputMaxLevel: maxOutput.toFixed(4),
      inputRMS: rmsInput.toFixed(4),
      outputRMS: rmsOutput.toFixed(4),
      fromRate: this.nativeSampleRate,
      toRate: this.targetSampleRate
    });
    
    return resampled;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    
    if (!input || !input[0] || !this.isRecording) {
      return true;
    }

    const inputChannelData = input[0];
    
    // DEBUG: Enhanced logging to track audio data flow
    if (Math.random() < 0.05) { // Log ~5% of chunks for better debugging
      let maxRaw = 0;
      let rmsRaw = 0;
      let nonZeroCount = 0;
      
      for (let i = 0; i < inputChannelData.length; i++) {
        const sample = inputChannelData[i];
        maxRaw = Math.max(maxRaw, Math.abs(sample));
        rmsRaw += sample * sample;
        if (Math.abs(sample) > 0.001) nonZeroCount++;
      }
      
      rmsRaw = Math.sqrt(rmsRaw / inputChannelData.length);
      
      console.log('🎤 RAW MICROPHONE INPUT:', {
        samples: inputChannelData.length,
        maxLevel: maxRaw.toFixed(4),
        rms: rmsRaw.toFixed(4),
        nonZeroSamples: nonZeroCount,
        silencePercentage: ((inputChannelData.length - nonZeroCount) / inputChannelData.length * 100).toFixed(1) + '%',
        firstFew: Array.from(inputChannelData.slice(0, 5)).map(x => x.toFixed(6)),
        contextRate: this.nativeSampleRate,
        bufferType: inputChannelData.constructor.name,
        isRecording: this.isRecording,
        bufferSize: this.bufferLength
      });
    }
    
    // CRITICAL FIX: Efficiently append audio data to Float32Array buffer
    // Avoid using push() which is inefficient for large amounts of audio data
    const newLength = this.bufferLength + inputChannelData.length;
    
    // Ensure buffer capacity
    if (newLength > this.buffer.length) {
      // Grow buffer efficiently - double size or add what we need, whichever is larger
      const newCapacity = Math.max(this.buffer.length * 2, newLength);
      const newBuffer = new Float32Array(Math.min(newCapacity, this.maxBufferSize));
      newBuffer.set(this.buffer.subarray(0, this.bufferLength));
      this.buffer = newBuffer;
    }
    
    // Copy new audio data efficiently
    if (newLength <= this.buffer.length) {
      this.buffer.set(inputChannelData, this.bufferLength);
      this.bufferLength = newLength;
    } else {
      // Buffer full - keep most recent data
      const keepSamples = this.buffer.length - inputChannelData.length;
      this.buffer.copyWithin(0, this.bufferLength - keepSamples);
      this.buffer.set(inputChannelData, keepSamples);
      this.bufferLength = this.buffer.length;
    }
    
    // Process buffer when it reaches optimal size OR when timeout is reached
    const currentTime = Date.now();
    const timeSinceLastSend = currentTime - this.lastSendTime;
    const bufferSizeBytes = this.bufferLength * 2; // 2 bytes per sample
    
    const shouldSend = bufferSizeBytes >= this.optimalChunkSize || 
                      (bufferSizeBytes > 0 && timeSinceLastSend >= this.sendInterval);
    
    if (shouldSend) {
      // Extract actual audio data from buffer
      const audioData = this.buffer.subarray(0, this.bufferLength);
      
      // 1. Apply audio preprocessing for better transcription
      const processedBuffer = this.preprocessAudio(audioData);
      
      // 2. CRITICAL: Resample to target sample rate (16kHz) for Deepgram
      const resampledBuffer = this.resampleAudio(processedBuffer);
      
      this.lastSendTime = currentTime;
      
      // Calculate audio level (RMS) from resampled data
      const rms = Math.sqrt(
        resampledBuffer.reduce((sum, sample) => sum + sample * sample, 0) / resampledBuffer.length
      );
      const audioLevel = Math.min(1, rms * 10); // Scale for UI
      
      console.log('🎵 Audio worklet processing:', {
        originalSamples: this.bufferLength,
        processedSamples: processedBuffer.length,
        resampledSamples: resampledBuffer.length,
        nativeRate: this.nativeSampleRate,
        targetRate: this.targetSampleRate,
        audioLevel: audioLevel.toFixed(3),
        bufferDurationMs: (resampledBuffer.length / this.targetSampleRate * 1000).toFixed(0),
        firstFewSamples: Array.from(resampledBuffer.slice(0, 5)).map(x => x.toFixed(6))
      });
      
      // CRITICAL FIX: Send Float32Array data directly, not ArrayBuffer
      // Create a proper copy of the resampled data to prevent corruption
      const audioDataCopy = new Float32Array(resampledBuffer.length);
      for (let i = 0; i < resampledBuffer.length; i++) {
        audioDataCopy[i] = resampledBuffer[i];
      }
      
      // Send processed and resampled audio data to main thread
      this.port.postMessage({
        type: 'audioData',
        data: {
          audioBuffer: audioDataCopy, // Send Float32Array directly
          audioLevel: audioLevel,
          sampleRate: this.targetSampleRate,
          timestamp: Date.now()
        }
      });
      
      // Clear buffer
      this.bufferLength = 0;
    }
    
    return true; // Keep processor alive
  }
}

registerProcessor('audio-recorder-worklet-processor', AudioRecorderWorkletProcessor);