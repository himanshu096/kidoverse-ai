import { useState, useEffect, useRef } from 'react';

const VAD_THRESHOLD = 0.05;
const AI_VAD_THRESHOLD = 0.01;
const THROTTLE_INTERVAL = 1000; // ms

type UseAgentStateProps = {
  connected: boolean;
  inVolume: number;
  volume: number;
};

export function useAgentState({ connected, inVolume, volume }: UseAgentStateProps): string {
  const [agentState, setAgentState] = useState('waving');
  const lastUpdateRef = useRef(0);

  useEffect(() => {
    const now = Date.now();
    if (now - lastUpdateRef.current < THROTTLE_INTERVAL) {
      return; // Throttle updates
    }
    lastUpdateRef.current = now;

    let newState = 'idle';
    if (!connected) {
      newState = 'waving';
    } else if (inVolume > VAD_THRESHOLD) {
      newState = 'listening';
    } else if (volume > AI_VAD_THRESHOLD) {
      newState = 'talking';
    }
    
    setAgentState(newState);
    
  }, [connected, inVolume, volume]);

  switch (agentState) {
    case 'waving':
      return "/ai_animation_waving.gif";
    case 'listening':
      return "/ai_animation_listening.gif";
    case 'talking':
      return "/ai_animation_talking.gif";
    case 'idle':
    default:
      return "/ai_animation.gif";
  }
} 