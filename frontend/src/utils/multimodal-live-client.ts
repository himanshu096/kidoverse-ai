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

import { Content, GenerativeContentBlob, Part } from "@google/generative-ai";
import { EventEmitter } from "eventemitter3";
import { difference } from "lodash";
import {
  ClientContentMessage,
  isInterrupted,
  isModelTurn,
  isServerContenteMessage,
  isSetupCompleteMessage,
  isToolCallCancellationMessage,
  isToolCallMessage,
  isToolResponseMessage,
  isTurnComplete,
  LiveIncomingMessage,
  ModelTurn,
  RealtimeInputMessage,
  ServerContent,
  StreamingLog,
  ToolCall,
  ToolCallCancellation,
  ToolResponseMessage,
  LiveFunctionResponse,
  isImageMessage,
  isMarkdownMessage,
  ImageMessage,
  MarkdownMessage,
  isUIFeedbackMessage,
  UIFeedbackMessage,
  type LiveConfig,
} from "../multimodal-live-types";
import { blobToJSON, base64ToArrayBuffer } from "./utils";

/**
 * the events that this client will emit
 */
interface MultimodalLiveClientEventTypes {
  open: () => void;
  log: (log: StreamingLog) => void;
  close: (event: CloseEvent) => void;
  audio: (data: ArrayBuffer) => void;
  content: (data: ServerContent) => void;
  interrupted: () => void;
  setupcomplete: () => void;
  status: (status: string) => void;
  turncomplete: () => void;
  toolcall: (toolCall: ToolCall) => void;
  toolcallcancellation: (toolcallCancellation: ToolCallCancellation) => void;
  image: (data: { url: string; alt?: string }) => void;
  toolresponse: (toolResponse: LiveFunctionResponse) => void;
  markdown: (content: string) => void;
  ui_feedback: (data: { status: string; message: string }) => void;
}

export type MultimodalLiveAPIClientConnection = {
  url?: string;
  runId?: string;
  userId?: string;
};

/**
 * A event-emitting class that manages the connection to the websocket and emits
 * events to the rest of the application.
 * If you dont want to use react you can still use this.
 */
export class MultimodalLiveClient extends EventEmitter<MultimodalLiveClientEventTypes> {
  public ws: WebSocket | null = null;
  protected config: LiveConfig | null = null;
  public url: string = "";
  private runId: string;
  private userId?: string;
  constructor({ url, userId, runId }: MultimodalLiveAPIClientConnection) {
    super();
    if (window.location.hostname === 'localhost') {
      this.url = "ws://localhost:8000/ws" ;
    } else {
      this.url = process.env.REACT_APP_WEBSOCKET_URL ?? "";
    }
    this.userId = userId;
    this.runId = runId || crypto.randomUUID();
    this.send = this.send.bind(this);
  }

  log(type: string, message: StreamingLog["message"]) {
    const log: StreamingLog = {
      date: new Date(),
      type,
      message,
    };
    this.emit("log", log);
  }

  connect(newRunId?: string): Promise<boolean> {
    const ws = new WebSocket(this.url);

    // Update runId if provided
    if (newRunId) {
      this.runId = newRunId;
    }

    ws.addEventListener("message", async (evt: MessageEvent) => {
      if (evt.data instanceof Blob) {
        this.receive(evt.data); // Pass the Blob directly
      } else if (typeof evt.data === "string") {
        // Now that receive() handles strings, pass it directly
        this.receive(evt.data); 
      } else {
        console.log("Unhandled message type:", evt);
        this.log("receive.unhandled", `Unhandled message type: ${evt.type}`);
      }
    });

    return new Promise((resolve, reject) => {
      const onError = (ev: Event) => {
        this.disconnect(ws);
        const message = `Could not connect to "${this.url}"`;
        this.log(`server.${ev.type}`, message);
        reject(new Error(message));
      };
      ws.addEventListener("error", onError);
      ws.addEventListener("open", (ev: Event) => {
        this.log(`client.${ev.type}`, `connected to socket`);
        this.emit("open");

        this.ws = ws;
        // Send initial setup message with runId
        const setupMessage = {
          setup: {
            run_id: this.runId,
            user_id: this.userId,
          },
        };
        this._sendDirect(setupMessage);
        ws.removeEventListener("error", onError);
        ws.addEventListener("close", (ev: CloseEvent) => {
          console.log(ev);
          this.disconnect(ws);
          let reason = ev.reason || "";
          if (reason.toLowerCase().includes("error")) {
            const prelude = "ERROR]";
            const preludeIndex = reason.indexOf(prelude);
            if (preludeIndex > 0) {
              reason = reason.slice(
                preludeIndex + prelude.length + 1,
                Infinity,
              );
            }
          }
          this.log(
            `server.${ev.type}`,
            `disconnected ${reason ? `with reason: ${reason}` : ``}`,
          );
          this.emit("close", ev);
        });
        resolve(true);
      });
    });
  }

  disconnect(ws?: WebSocket) {
    // could be that this is an old websocket and there's already a new instance
    // only close it if its still the correct reference
    if ((!ws || this.ws === ws) && this.ws) {
      this.ws.close();
      this.ws = null;
      this.log("client.close", `Disconnected`);
      return true;
    }
    return false;
  }
  protected async receive(data: Blob | string) {
  let response: LiveIncomingMessage;
  if (data instanceof Blob) {
    response = (await blobToJSON(data)) as LiveIncomingMessage;
  } else {
       try {
      response = JSON.parse(data) as LiveIncomingMessage;
    } catch (error) {
      console.error("Error parsing string message as JSON:", error);
      this.log("server.error", `Failed to parse JSON string: ${error instanceof Error ? error.message : String(error)}`);
      return; 
    }
  }
    console.log("Parsed response:", response);

    if (isToolCallMessage(response)) {
      this.log("server.toolCall", response);
      this.emit("toolcall", response.toolCall);
      return;
    }

    if (isImageMessage(response)) {
      this.log("server.image", response);
      this.emit("image", response.image); // Emit the custom 'image' event
      return; // Return because this is a top-level message type
    }

    if (isUIFeedbackMessage(response)) {
      this.log("server.ui_feedback", response);
      this.emit("ui_feedback", response.ui_feedback);
      return;
    }

    if (isMarkdownMessage(response)) {
      const md = typeof response.markdown === "string" ? response.markdown : response.markdown.content;
      this.log("server.markdown", md);
      this.emit("markdown", md);
      return;
    }

    if (response && 'functionResponses' in response && Array.isArray((response as any).functionResponses)) {
        this.log("server.toolCall (direct functionResponses)", response);

        console.log("server.toolCall (direct functionResponses)", response);
        const functionResponses = response.functionResponses as LiveFunctionResponse[];
        const markdown = functionResponses
          .map((fr) => {
            if (
              fr &&
              typeof fr === "object" &&
              "response" in fr &&
              fr.response &&
              typeof fr.response === "object" &&
              "markdown_content" in fr.response
            ) {
              return (fr.response as { markdown_content?: string }).markdown_content ?? "";
            }
            return "";
          })
          .join("\n");
        this.emit("markdown", markdown);
        return; // Processed this type of message
    }


    if(isToolResponseMessage(response)){
      this.log("server.toolCall", response);
      for (const r of response.toolResponse.functionResponses) {
      // this.emit("toolresponse", r);
      if (r.response && typeof r.response === "object" && "markdown_content" in r.response) {
        const markdownContent = (r.response as { markdown_content?: string }).markdown_content;
        if (markdownContent) {
          this.emit("markdown", markdownContent);
          this.log("server.markdown", markdownContent);
        }
      }
  }
    }
    
    if (isToolCallCancellationMessage(response)) {
      this.log("receive.toolCallCancellation", response);
      this.emit("toolcallcancellation", response.toolCallCancellation);
      return;
    }

    if (isSetupCompleteMessage(response)) {
      this.log("server.send", "setupComplete");
      this.emit("setupcomplete");
      return;
    }

    // this json also might be `contentUpdate { interrupted: true }`
    // or contentUpdate { end_of_turn: true }
    if (isServerContenteMessage(response)) {
      const { serverContent } = response;
      if (isInterrupted(serverContent)) {
        this.log("receive.serverContent", "interrupted");
        this.emit("interrupted");
        return;
      }
      if (isTurnComplete(serverContent)) {
        this.log("server.send", "turnComplete");
        this.emit("turncomplete");
        //plausible there's more to the message, continue
      }

      if (isModelTurn(serverContent)) {
        let parts: Part[] = serverContent.modelTurn.parts;

        console.log("serverContent.modelTurn", parts);

        // when its audio that is returned for modelTurn
        const audioParts = parts.filter(
          (p) => p.inlineData && p.inlineData.mimeType.startsWith("audio/pcm"),
        );
        const base64s = audioParts.map((p) => p.inlineData?.data);

        const otherParts = difference(parts, audioParts);

        base64s.forEach((b64) => {
          if (b64) {
            const data = base64ToArrayBuffer(b64);
            this.emit("audio", data);
            this.log(`server.audio`, `buffer (${data.byteLength})`);
          }
        });

        if (!otherParts.length) {
          return;
        }

        const content: ModelTurn = { modelTurn: { parts: otherParts } };
        this.emit("content", content);
        this.log(`server.content`, response);
      }
    } else {
      console.log("received unmatched message", response);
      this.log("received unmatched message", response);
    }
  }

  /**
   * send realtimeInput, this is base64 chunks of "audio/pcm" and/or "image/jpg"
   */
  sendRealtimeInput(chunks: GenerativeContentBlob[]) {
    let hasAudio = false;
    let hasVideo = false;
    for (let i = 0; i < chunks.length; i++) {
      const ch = chunks[i];
      if (ch.mimeType.includes("audio")) {
        hasAudio = true;
      }
      if (ch.mimeType.includes("image")) {
        hasVideo = true;
      }
      if (hasAudio && hasVideo) {
        break;
      }
    }
    const message =
      hasAudio && hasVideo
        ? "audio + video"
        : hasAudio
          ? "audio"
          : hasVideo
            ? "video"
            : "unknown";

    const data: RealtimeInputMessage = {
      realtimeInput: {
        mediaChunks: chunks,
      },
    };
    this._sendDirect(data);
    this.log(`client.realtimeInput`, message);
  }

  /**
   *  send a response to a function call and provide the id of the functions you are responding to
   */
  sendToolResponse(toolResponse: ToolResponseMessage["toolResponse"]) {
    const message: ToolResponseMessage = {
      toolResponse,
    };

    this._sendDirect(message);
    this.log(`client.toolResponse`, message);
  }

  /**
   * send normal content parts such as { text }
   */
  send(parts: Part | Part[], turnComplete: boolean = true) {
    parts = Array.isArray(parts) ? parts : [parts];
    const content: Content = {
      role: "user",
      parts,
    };

    const clientContentRequest: ClientContentMessage = {
      clientContent: {
        turns: [content],
        turnComplete,
      },
    };

    this._sendDirect(clientContentRequest);
    this.log(`client.send`, clientContentRequest);
  }

  /**
   *  used internally to send all messages
   *  don't use directly unless trying to send an unsupported message type
   */
  _sendDirect(request: object) {
    if (!this.ws) {
      throw new Error("WebSocket is not connected");
    }
    const str = JSON.stringify(request);
    this.ws.send(str);
  }
}
