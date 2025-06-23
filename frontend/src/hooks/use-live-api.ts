/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  Dispatch,
  SetStateAction,
} from "react";
import { MultimodalLiveClient } from "../utils/multimodal-live-client";
import { AudioStreamer } from "../utils/audio-streamer";
import { audioContext } from "../utils/utils";
import VolMeterWorket from "../utils/worklets/vol-meter";
import { AudioRecorder } from "../utils/audio-recorder";

export type UseLiveAPIResults = {
  client: MultimodalLiveClient;
  connected: boolean;
  connect: () => Promise<void>;
  disconnect: () => Promise<void>;
  volume: number;
  inVolume: number; // Volume from the user's microphone
  muted: boolean;
  setMuted: Dispatch<SetStateAction<boolean>>;
  toolImage: { url: string; alt?: string | undefined; } | null;
  setToolImage: Dispatch<SetStateAction<{ url: string; alt?: string | undefined; } | null>>;
  currentSectionMarkdown: string;
  setCurrentSectionMarkdown: Dispatch<SetStateAction<string>>;
  feedbackMessage: { status: string; message: string; } | null;
};

export type UseLiveAPIProps = {
  url?: string;
  userId?: string;
  onRunIdChange?: Dispatch<SetStateAction<string>>;
};

export function useLiveAPI({
  url,
  userId,
}: UseLiveAPIProps): UseLiveAPIResults {
  const client = useMemo(
    () => new MultimodalLiveClient({ url, userId }),
    [url, userId],
  );
  const audioStreamerRef = useRef<AudioStreamer | null>(null);
  const audioRecorderRef = useRef<AudioRecorder | null>(null);

  const [connected, setConnected] = useState(false);
  const [volume, setVolume] = useState(0);
  const [inVolume, setInVolume] = useState(0);
  const [muted, setMuted] = useState(false);

  const [toolImage, setToolImage] = useState<{ url: string; alt?: string } | null>(null);
  const [feedbackMessage, setFeedbackMessage] = useState<{ status: string; message: string } | null>(null);

  const [currentSectionMarkdown, setCurrentSectionMarkdown] = useState<string>('');


  // register audio for streaming server -> speakers
  useEffect(() => {
    if (!audioStreamerRef.current) {
      audioContext({ id: "audio-out" }).then((audioCtx: AudioContext) => {
        audioStreamerRef.current = new AudioStreamer(audioCtx);
        audioStreamerRef.current
          .addWorklet<any>("vumeter-out", VolMeterWorket, (ev: any) => {
            setVolume(ev.data.volume);
          })
          .then(() => {
            // Successfully added worklet
          });
      });
    }
    if (!audioRecorderRef.current) {
      audioRecorderRef.current = new AudioRecorder();
    }
  }, [audioStreamerRef, audioRecorderRef]);

  // This effect handles the microphone input recording and streaming
  useEffect(() => {
    const onData = (base64: string) => {
      client.sendRealtimeInput([
        {
          mimeType: "audio/pcm;rate=16000",
          data: base64,
        },
      ]);
    };
    if (connected && !muted && audioRecorderRef.current) {
      audioRecorderRef.current.on("data", onData).on("volume", setInVolume).start();
    } else {
      audioRecorderRef.current?.stop();
    }
    return () => {
      audioRecorderRef.current?.off("data", onData).off("volume", setInVolume);
    };
  }, [connected, client, muted, audioRecorderRef]);

  useEffect(() => {
    const onClose = () => {
      setConnected(false);
    };

    const stopAudioStreamer = () => audioStreamerRef.current?.stop();

    const onAudio = (data: ArrayBuffer) =>
      audioStreamerRef.current?.addPCM16(new Uint8Array(data));

    const onImage = (imageData: { url: string; alt?: string }) => {
      console.log("useLiveAPI: Received 'image' event:", imageData);
      setToolImage(imageData);
      setFeedbackMessage(null);
    };

    const onUIFeedback = (data: { status: string; message: string }) => {
      console.log("useLiveAPI: Received 'ui_feedback' event:", data);
      setFeedbackMessage(data);
    };

    const onTurnComplete = () => {
      console.log("useLiveAPI: Turn complete, clearing feedback.");
      setFeedbackMessage(null);
    };

    const onMarkdown = (content: string) => {
      console.log("useLiveAPI: Received 'markdown' event:", content);
      setCurrentSectionMarkdown(content);
    };

    client
      .on("close", onClose)
      .on("interrupted", stopAudioStreamer)
      .on("audio", onAudio)
      .on("image", onImage)
      .on("markdown", onMarkdown)
      .on("ui_feedback", onUIFeedback)
      .on("turncomplete", onTurnComplete);

    return () => {
      client
        .off("close", onClose)
        .off("interrupted", stopAudioStreamer)
        .off("image", onImage)
        .off("markdown", onMarkdown)
        .off("audio", onAudio)
        .off("ui_feedback", onUIFeedback)
        .off("turncomplete", onTurnComplete);
    };
  }, [client]);
  

  const connect = useCallback(async () => {
    client.disconnect();
    await client.connect();
    setConnected(true);
  }, [client, setConnected]);

  const disconnect = useCallback(async () => {
    client.disconnect();
    setConnected(false);
  }, [setConnected, client]);

  return {
    client,
    connected,
    connect,
    disconnect,
    volume,
    inVolume,
    muted,
    setMuted,
    toolImage,
    setToolImage,
    currentSectionMarkdown,
    setCurrentSectionMarkdown,
    feedbackMessage,
  };
}
