import React, { useRef, useEffect, useState, useCallback } from 'react';
import clsx from 'clsx';
import {
  PlayIcon,
  PauseIcon,
  SpeakerWaveIcon,
  SpeakerXMarkIcon,
  ArrowPathIcon,
  ForwardIcon,
  BackwardIcon,
} from '@heroicons/react/24/solid';

/**
 * AudioPlayer Component - Audio player with waveform visualization
 *
 * @param {Object} props
 * @param {string} props.src - Audio file URL
 * @param {string} props.title - Track title
 * @param {string} props.artist - Artist name
 * @param {string} props.coverArt - Cover art URL
 * @param {boolean} props.showWaveform - Show waveform visualization
 * @param {string} props.waveformColor - Waveform color
 * @param {string} props.progressColor - Progress color
 * @param {string} props.className - Additional CSS classes
 */
export function AudioPlayer({
  src,
  title,
  artist,
  coverArt,
  showWaveform = true,
  waveformColor = '#94a3b8',
  progressColor = '#3b82f6',
  className,
}) {
  const waveformRef = useRef(null);
  const wavesurferRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(0.8);
  const [isMuted, setIsMuted] = useState(false);
  const [error, setError] = useState(null);

  // Initialize WaveSurfer
  useEffect(() => {
    if (!showWaveform || !waveformRef.current || !src) return;

    let wavesurfer = null;

    const initWaveSurfer = async () => {
      try {
        const WaveSurfer = (await import('wavesurfer.js')).default;

        wavesurfer = WaveSurfer.create({
          container: waveformRef.current,
          waveColor: waveformColor,
          progressColor: progressColor,
          cursorColor: progressColor,
          cursorWidth: 2,
          barWidth: 2,
          barGap: 1,
          barRadius: 2,
          height: 64,
          normalize: true,
          responsive: true,
        });

        wavesurfer.load(src);

        wavesurfer.on('ready', () => {
          setIsReady(true);
          setIsLoading(false);
          setDuration(wavesurfer.getDuration());
          wavesurfer.setVolume(volume);
        });

        wavesurfer.on('audioprocess', () => {
          setCurrentTime(wavesurfer.getCurrentTime());
        });

        wavesurfer.on('play', () => setIsPlaying(true));
        wavesurfer.on('pause', () => setIsPlaying(false));
        wavesurfer.on('finish', () => setIsPlaying(false));
        wavesurfer.on('error', (err) => {
          setError('Failed to load audio');
          setIsLoading(false);
          console.error('WaveSurfer error:', err);
        });

        wavesurferRef.current = wavesurfer;
      } catch (err) {
        setError('Failed to initialize audio player');
        setIsLoading(false);
        console.error('WaveSurfer init error:', err);
      }
    };

    initWaveSurfer();

    return () => {
      if (wavesurfer) {
        wavesurfer.destroy();
      }
    };
  }, [src, showWaveform, waveformColor, progressColor]);

  // Format time helper
  const formatTime = (seconds) => {
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Playback controls
  const togglePlay = useCallback(() => {
    if (wavesurferRef.current) {
      wavesurferRef.current.playPause();
    }
  }, []);

  const skipForward = useCallback(() => {
    if (wavesurferRef.current) {
      wavesurferRef.current.skip(10);
    }
  }, []);

  const skipBackward = useCallback(() => {
    if (wavesurferRef.current) {
      wavesurferRef.current.skip(-10);
    }
  }, []);

  const handleVolumeChange = useCallback((e) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    setIsMuted(newVolume === 0);
    if (wavesurferRef.current) {
      wavesurferRef.current.setVolume(newVolume);
    }
  }, []);

  const toggleMute = useCallback(() => {
    if (wavesurferRef.current) {
      const newMuted = !isMuted;
      setIsMuted(newMuted);
      wavesurferRef.current.setVolume(newMuted ? 0 : volume);
    }
  }, [isMuted, volume]);

  // Simple audio fallback (when waveform is disabled)
  if (!showWaveform) {
    return (
      <div className={clsx('aria-audio-player', className)}>
        <div className="flex items-center gap-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          {coverArt && (
            <img
              src={coverArt}
              alt={title || 'Cover art'}
              className="w-16 h-16 rounded object-cover"
            />
          )}
          <div className="flex-1">
            {title && (
              <h4 className="font-medium text-gray-900 dark:text-gray-100">{title}</h4>
            )}
            {artist && (
              <p className="text-sm text-gray-600 dark:text-gray-400">{artist}</p>
            )}
            <audio
              src={src}
              controls
              className="w-full mt-2"
            />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={clsx('aria-audio-player', className)}>
      <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        {/* Header with cover art and info */}
        <div className="flex items-center gap-4 mb-4">
          {coverArt && (
            <img
              src={coverArt}
              alt={title || 'Cover art'}
              className="w-16 h-16 rounded-lg object-cover shadow-md"
            />
          )}
          <div className="flex-1 min-w-0">
            {title && (
              <h4 className="font-medium text-gray-900 dark:text-gray-100 truncate">
                {title}
              </h4>
            )}
            {artist && (
              <p className="text-sm text-gray-600 dark:text-gray-400 truncate">
                {artist}
              </p>
            )}
          </div>
        </div>

        {/* Error state */}
        {error && (
          <div className="p-3 mb-4 bg-red-50 dark:bg-red-900/20 rounded text-red-600 dark:text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Loading state */}
        {isLoading && !error && (
          <div className="flex items-center justify-center h-16 mb-4">
            <ArrowPathIcon className="w-6 h-6 animate-spin text-gray-400" />
            <span className="ml-2 text-gray-500 dark:text-gray-400">Loading audio...</span>
          </div>
        )}

        {/* Waveform */}
        <div
          ref={waveformRef}
          className={clsx('mb-4', isLoading && 'hidden')}
        />

        {/* Time display */}
        <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mb-2">
          <span>{formatTime(currentTime)}</span>
          <span>{formatTime(duration)}</span>
        </div>

        {/* Controls */}
        <div className="flex items-center justify-between">
          {/* Playback controls */}
          <div className="flex items-center gap-2">
            <button
              onClick={skipBackward}
              disabled={!isReady}
              className="p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700
                         text-gray-600 dark:text-gray-400 disabled:opacity-50"
              title="Skip back 10s"
            >
              <BackwardIcon className="w-5 h-5" />
            </button>
            <button
              onClick={togglePlay}
              disabled={!isReady}
              className="p-3 rounded-full bg-blue-500 hover:bg-blue-600
                         text-white disabled:opacity-50 disabled:cursor-not-allowed
                         transition-colors"
            >
              {isPlaying ? (
                <PauseIcon className="w-6 h-6" />
              ) : (
                <PlayIcon className="w-6 h-6" />
              )}
            </button>
            <button
              onClick={skipForward}
              disabled={!isReady}
              className="p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700
                         text-gray-600 dark:text-gray-400 disabled:opacity-50"
              title="Skip forward 10s"
            >
              <ForwardIcon className="w-5 h-5" />
            </button>
          </div>

          {/* Volume controls */}
          <div className="flex items-center gap-2">
            <button
              onClick={toggleMute}
              className="p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700
                         text-gray-600 dark:text-gray-400"
            >
              {isMuted || volume === 0 ? (
                <SpeakerXMarkIcon className="w-5 h-5" />
              ) : (
                <SpeakerWaveIcon className="w-5 h-5" />
              )}
            </button>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={isMuted ? 0 : volume}
              onChange={handleVolumeChange}
              className="w-20 h-1 bg-gray-300 dark:bg-gray-600 rounded-full
                         appearance-none cursor-pointer
                         [&::-webkit-slider-thumb]:appearance-none
                         [&::-webkit-slider-thumb]:w-3
                         [&::-webkit-slider-thumb]:h-3
                         [&::-webkit-slider-thumb]:rounded-full
                         [&::-webkit-slider-thumb]:bg-blue-500"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * AudioPlaylist Component - Multiple audio tracks
 */
export function AudioPlaylist({
  tracks = [],
  className,
  title,
}) {
  const [currentTrack, setCurrentTrack] = useState(0);

  if (tracks.length === 0) {
    return null;
  }

  return (
    <div className={clsx('aria-audio-playlist', className)}>
      {title && (
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          {title}
        </h3>
      )}

      <AudioPlayer
        key={currentTrack}
        src={tracks[currentTrack].src}
        title={tracks[currentTrack].title}
        artist={tracks[currentTrack].artist}
        coverArt={tracks[currentTrack].coverArt}
      />

      {/* Track list */}
      {tracks.length > 1 && (
        <div className="mt-4 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
          {tracks.map((track, index) => (
            <button
              key={index}
              onClick={() => setCurrentTrack(index)}
              className={clsx(
                'w-full flex items-center gap-3 px-4 py-3 text-left',
                'border-b border-gray-200 dark:border-gray-700 last:border-b-0',
                currentTrack === index
                  ? 'bg-blue-50 dark:bg-blue-900/30'
                  : 'hover:bg-gray-50 dark:hover:bg-gray-800'
              )}
            >
              <span className="w-6 h-6 flex items-center justify-center text-sm text-gray-500 dark:text-gray-400">
                {currentTrack === index && isPlaying ? (
                  <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                ) : (
                  index + 1
                )}
              </span>
              <div className="flex-1 min-w-0">
                <p className={clsx(
                  'font-medium truncate',
                  currentTrack === index
                    ? 'text-blue-600 dark:text-blue-400'
                    : 'text-gray-900 dark:text-gray-100'
                )}>
                  {track.title || `Track ${index + 1}`}
                </p>
                {track.artist && (
                  <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
                    {track.artist}
                  </p>
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default AudioPlayer;
